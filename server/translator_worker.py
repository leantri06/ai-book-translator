"""
Asynchronous Translation Worker with Thread-Safe State & Buffer.
Handles background translation jobs, chunk-by-chunk auto-saving, pause/resume, and real-time polling state.
"""
import threading
import time
import math
import re
import logging
import queue
import collections
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from core.parser import BookProject, BookChapter, BookParagraph
from core.chunker import ParagraphChunker, TranslationChunk
from core.translator import AITranslator, RateLimitError, DailyQuotaError
from core.glossary import BookGlossary
from server.database import ProjectManager

logger = logging.getLogger("TranslatorWorker")


class KeyPool:
    """Thread-safe pool managing multiple API keys, cooldowns, pacing delays, and daily limits."""

    def __init__(self, keys: List[str], provider: str = "gemini"):
        self.keys = keys if keys else [""]
        self.provider = provider
        self.lock = threading.Lock()
        self.cooldowns: Dict[str, float] = {}  # key -> ready_at timestamp
        self.last_used: Dict[str, float] = {}  # key -> timestamp when call finished
        self.in_use: set = set()               # keys currently executing an API call
        self.key_indices: Dict[str, int] = {k: i + 1 for i, k in enumerate(self.keys)}
        self.daily_exhausted: set = set()
        self._next_idx = 0
        self.pacing_gap = 3.5 if provider == "gemini" else 0.8

    def acquire_key(self, timeout: float = 60.0, stop_event: Optional[threading.Event] = None) -> Optional[Tuple[int, str]]:
        """Acquires an exclusive, ready API key."""
        start_t = time.time()
        while time.time() - start_t < timeout:
            if stop_event and stop_event.is_set():
                return None

            sleep_time = 0.0
            with self.lock:
                now = time.time()
                valid_keys = [k for k in self.keys if k not in self.daily_exhausted]
                if not valid_keys:
                    return None

                # Must not be currently executing and not in cooldown
                available = [
                    k for k in valid_keys
                    if k not in self.in_use and self.cooldowns.get(k, 0.0) <= now
                ]

                if available:
                    chosen = available[self._next_idx % len(available)]
                    self._next_idx += 1

                    elapsed = now - self.last_used.get(chosen, 0.0)
                    needed_gap = self.pacing_gap - elapsed
                    if needed_gap > 0.05:
                        sleep_time = min(needed_gap, 1.0)
                    else:
                        self.in_use.add(chosen)
                        return (self.key_indices[chosen], chosen)

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                time.sleep(0.3)

        return None

    def release_key(self, key: str):
        """Releases the key back to the pool."""
        with self.lock:
            self.in_use.discard(key)
            self.last_used[key] = time.time()

    def mark_cooldown(self, key: str, wait_seconds: float, is_daily: bool = False):
        with self.lock:
            self.in_use.discard(key)
            if is_daily:
                self.daily_exhausted.add(key)
            else:
                self.cooldowns[key] = time.time() + wait_seconds

    def has_available_keys(self) -> bool:
        with self.lock:
            return any(k not in self.daily_exhausted for k in self.keys)


class TranslationWorker:
    """Manages active background translation jobs with thread-safe polling buffers."""

    def __init__(self):
        self._active_jobs: Dict[str, dict] = {}
        # Buffer of logs and paragraph updates for fast, reliable polling
        self._project_states: Dict[str, dict] = {}
        self._lock = threading.RLock()

    def get_state(self, project_id: str, since_timestamp: float = 0.0) -> dict:
        """Returns the current state and any new logs/paragraph updates since timestamp."""
        with self._lock:
            state = self._project_states.get(project_id)
            is_running = bool(project_id in self._active_jobs and self._active_jobs[project_id]["status"] == "running")

            if not state:
                return {
                    "is_running": is_running,
                    "status_text": "Đang chạy..." if is_running else "Sẵn sàng",
                    "chapter_id": "",
                    "chapter_title": "",
                    "chapter_progress": 0.0,
                    "overall_progress": 0.0,
                    "logs": [],
                    "updated_paragraphs": [],
                    "timestamp": time.time()
                }

            # Filter new logs
            new_logs = [l for l in state.get("logs", []) if l.get("timestamp", 0) > since_timestamp]
            new_paras = [p for p in state.get("updated_paragraphs", []) if p.get("timestamp", 0) > since_timestamp]

            return {
                "is_running": is_running,
                "status_text": state.get("status_text", "Đang dịch..."),
                "chapter_id": state.get("chapter_id", ""),
                "chapter_title": state.get("chapter_title", ""),
                "chapter_progress": state.get("chapter_progress", 0.0),
                "overall_progress": state.get("overall_progress", 0.0),
                "logs": new_logs,
                "updated_paragraphs": new_paras,
                "timestamp": time.time()
            }

    def add_log(self, project_id: str, level: str, text: str) -> None:
        with self._lock:
            if project_id not in self._project_states:
                self._project_states[project_id] = {"logs": [], "updated_paragraphs": []}
            state = self._project_states[project_id]
            log_entry = {"level": level, "text": text, "timestamp": time.time()}
            state.setdefault("logs", []).append(log_entry)
            # Keep only last 100 logs
            if len(state["logs"]) > 100:
                state["logs"] = state["logs"][-100:]

    def is_running(self, project_id: str) -> bool:
        with self._lock:
            job = self._active_jobs.get(project_id)
            return bool(job and job["status"] == "running")

    def stop_translation(self, project_id: str) -> None:
        with self._lock:
            job = self._active_jobs.get(project_id)
            if job:
                job["stop_event"].set()
                job["status"] = "stopping"
                if project_id in self._project_states:
                    self._project_states[project_id]["status_text"] = "Đang tạm dừng..."

    def start_translation(self, project_id: str, chapter_id: Optional[str] = None, force_retranslate: bool = False) -> bool:
        with self._lock:
            if self.is_running(project_id):
                return False

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run_translation_loop,
                args=(project_id, chapter_id, stop_event, force_retranslate),
                daemon=True
            )
            self._active_jobs[project_id] = {
                "thread": thread,
                "stop_event": stop_event,
                "status": "running"
            }
            if project_id not in self._project_states:
                self._project_states[project_id] = {"logs": [], "updated_paragraphs": []}
            self._project_states[project_id]["status_text"] = "Bắt đầu dịch..."
            thread.start()
            return True

    def _run_translation_loop(self, project_id: str, target_chapter_id: Optional[str], stop_event: threading.Event, force_retranslate: bool = False) -> None:
        """Background thread executing the translation work."""
        self.add_log(project_id, "info", "Khởi động phiên dịch...")

        try:
            # 1. Load settings & initialize AI Translator
            settings = ProjectManager.get_settings()
            translator = AITranslator(
                provider=settings.get("provider", "gemini"),
                api_key=settings.get("api_key", ""),
                model=settings.get("model", "gemini-3.5-flash"),
                base_url=settings.get("base_url", ""),
                temperature=settings.get("temperature", 0.3)
            )

            # Key pool setup
            key_pool = KeyPool(translator.api_keys, provider=translator.provider)
            num_keys = len(key_pool.keys)

            if num_keys > 1:
                self.add_log(project_id, "info",
                    f"⚡ Kích hoạt chế độ Dịch Song Song: Nhận diện {num_keys} API Keys ({min(num_keys, 6)} luồng chạy đồng thời)!")
            else:
                self.add_log(project_id, "info", "Khởi động phiên dịch chuẩn (1 API Key / Luồng đơn)...")

            # 2. Load Glossary
            glossary = ProjectManager.load_glossary(project_id)

            # 3. Load Project
            project = ProjectManager.load_project(project_id, load_all_paragraphs=False)
            if not project:
                self.add_log(project_id, "error", f"Không tìm thấy dự án {project_id}")
                return

            # Determine chapters to translate
            chapters_to_process = []
            if target_chapter_id:
                chap = ProjectManager.load_chapter(project_id, target_chapter_id)
                if chap:
                    if force_retranslate:
                        for p in chap.paragraphs:
                            p.status = "pending"
                            p.translated_text = ""
                        ProjectManager.save_chapter(project_id, chap)
                    chapters_to_process.append(chap)
            else:
                for c_meta in project.chapters:
                    c = ProjectManager.load_chapter(project_id, c_meta.id)
                    if c:
                        if force_retranslate:
                            for p in c.paragraphs:
                                p.status = "pending"
                                p.translated_text = ""
                            ProjectManager.save_chapter(project_id, c)
                            chapters_to_process.append(c)
                        elif c.progress_percent < 100.0:
                            chapters_to_process.append(c)

            if not chapters_to_process:
                self.add_log(project_id, "success", "Tất cả các chương đã được dịch hoàn tất!")
                return

            chunker = ParagraphChunker(target_word_count=1000, max_paragraphs=12)

            for chap in chapters_to_process:
                if stop_event.is_set():
                    break

                if not key_pool.has_available_keys():
                    self.add_log(project_id, "error", "Tất cả API Key đã dùng hết hạn mức (Quota). Dừng phiên dịch.")
                    break

                with self._lock:
                    st = self._project_states.setdefault(project_id, {})
                    st["chapter_id"] = chap.id
                    st["chapter_title"] = chap.title
                    st["chapter_progress"] = chap.progress_percent
                    st["status_text"] = f"Đang dịch: {chap.title[:30]}..."

                self.add_log(project_id, "info", f"Bắt đầu chương: {chap.title} ({chap.total_paragraphs} đoạn)")

                chunks = chunker.create_chunks(chap, only_pending=True)
                total_chunks = len(chunks)

                if not chunks:
                    self.add_log(project_id, "info", f"Chương '{chap.title}' đã hoàn tất (không còn đoạn nào cần dịch).")
                    continue

                chunk_queue = queue.Queue()
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_queue.put((chunk_idx, chunk))

                completed_chunks = set()
                chunk_lock = threading.Lock()
                save_lock = threading.Lock()
                chunk_attempts = collections.defaultdict(int)
                max_attempts = 4

                # Concurrency level: min(keys, chunks, 6)
                num_workers = min(max(1, num_keys), min(total_chunks, 6))

                def worker_fn():
                    while not stop_event.is_set():
                        if not key_pool.has_available_keys():
                            break

                        with chunk_lock:
                            if len(completed_chunks) >= total_chunks or chunk_queue.empty():
                                break

                        try:
                            item = chunk_queue.get(timeout=0.8)
                        except queue.Empty:
                            continue

                        chunk_idx, chunk = item

                        with chunk_lock:
                            if chunk_idx in completed_chunks:
                                chunk_queue.task_done()
                                continue
                            chunk_attempts[chunk_idx] += 1
                            attempt = chunk_attempts[chunk_idx]

                        # Acquire a ready key exclusively
                        key_tuple = key_pool.acquire_key(timeout=45.0, stop_event=stop_event)
                        if not key_tuple:
                            with chunk_lock:
                                if chunk_idx not in completed_chunks:
                                    chunk_queue.put((chunk_idx, chunk))
                            chunk_queue.task_done()
                            if stop_event.is_set():
                                break
                            time.sleep(0.5)
                            continue

                        worker_id, worker_key = key_tuple
                        key_tag = f"Key #{worker_id}" if num_keys > 1 else "AI"
                        self.add_log(project_id, "info",
                            f"[{chap.title[:15]}] 🚀 [{key_tag}] Đang dịch đoạn {chunk_idx + 1}/{total_chunks} ({chunk.total_words} từ)...")

                        translated_map = None
                        hit_quota = False
                        hit_daily = False
                        wait_s = 35.0

                        try:
                            translated_map = translator.translate_chunk(chunk, glossary, api_key=worker_key)
                        except DailyQuotaError as dqe:
                            hit_daily = True
                            logger.warning(f"Key #{worker_id} daily quota exhausted: {dqe}")
                        except RateLimitError as rle:
                            hit_quota = True
                            wait_s = max(5, int(math.ceil(rle.retry_after)))
                        except Exception as e:
                            err_str = str(e)
                            match = re.search(r'retry in ([0-9.]+)\s*s', err_str, re.IGNORECASE)
                            if "generaterequestsperday" in err_str.lower() or "per_day" in err_str.lower():
                                hit_daily = True
                            elif "429" in err_str or match or "quota" in err_str.lower():
                                hit_quota = True
                                wait_s = int(math.ceil(float(match.group(1)))) + 2 if match else 35
                            else:
                                logger.error(f"Translation chunk error: {e}")
                                self.add_log(project_id, "error", f"[{key_tag}] Lỗi đoạn {chunk_idx + 1} (lần {attempt}/{max_attempts}): {err_str}")

                        if translated_map:
                            key_pool.release_key(worker_key)
                            now_ts = time.time()
                            updated_paras = []
                            with save_lock:
                                for p in chunk.paragraphs:
                                    if p.id in translated_map and translated_map[p.id]:
                                        p.translated_text = translated_map[p.id]
                                        p.status = "done"
                                        updated_paras.append({"id": p.id, "text": p.translated_text, "chapter_id": chap.id, "timestamp": now_ts})

                                ProjectManager.save_chapter(project_id, chap)
                                updated_proj = ProjectManager.load_project(project_id, load_all_paragraphs=False)
                                overall_progress = updated_proj.progress_percent if updated_proj else 0.0

                                with self._lock:
                                    st = self._project_states.setdefault(project_id, {})
                                    st["chapter_id"] = chap.id
                                    st["chapter_title"] = chap.title
                                    st["chapter_progress"] = chap.progress_percent
                                    st["overall_progress"] = overall_progress
                                    st["status_text"] = f"Đang dịch: {chap.title[:25]} ({chap.progress_percent}%)"
                                    st.setdefault("updated_paragraphs", []).extend(updated_paras)
                                    if len(st["updated_paragraphs"]) > 200:
                                        st["updated_paragraphs"] = st["updated_paragraphs"][-200:]

                                with chunk_lock:
                                    completed_chunks.add(chunk_idx)

                            self.add_log(project_id, "success",
                                f"[{chap.title[:15]}] ✅ [{key_tag}] Đã xong đoạn {chunk_idx + 1}/{total_chunks} ({len(chunk.paragraphs)} đoạn con)")
                            chunk_queue.task_done()

                        elif hit_daily:
                            key_pool.mark_cooldown(worker_key, 0, is_daily=True)
                            self.add_log(project_id, "warning",
                                f"⚠️ [{key_tag}] Đã đạt giới hạn 24h của Google AI Studio. Tự động chuyển giao các đoạn còn lại cho các Key khác!")
                            with chunk_lock:
                                if attempt < max_attempts and chunk_idx not in completed_chunks:
                                    chunk_queue.put((chunk_idx, chunk))
                                else:
                                    self.add_log(project_id, "error", f"Đoạn {chunk_idx + 1} không thể dịch do thiếu Key khả dụng.")
                                    completed_chunks.add(chunk_idx)
                            chunk_queue.task_done()

                        elif hit_quota:
                            key_pool.mark_cooldown(worker_key, wait_s, is_daily=False)
                            self.add_log(project_id, "warning",
                                f"⏳ [{key_tag}] Đạt giới hạn 15 RPM. Tạm nghỉ key này {wait_s}s. Đoạn {chunk_idx + 1} sẽ được chuyển cho Key khác...")
                            with chunk_lock:
                                if attempt < max_attempts and chunk_idx not in completed_chunks:
                                    chunk_queue.put((chunk_idx, chunk))
                                else:
                                    self.add_log(project_id, "error", f"Đoạn {chunk_idx + 1} vượt quá số lần thử quota ({attempt}).")
                                    completed_chunks.add(chunk_idx)
                            chunk_queue.task_done()

                        else:
                            key_pool.release_key(worker_key)
                            with chunk_lock:
                                if attempt < max_attempts and chunk_idx not in completed_chunks:
                                    time.sleep(1.5)
                                    chunk_queue.put((chunk_idx, chunk))
                                else:
                                    self.add_log(project_id, "error", f"Đoạn {chunk_idx + 1} tạm bỏ qua sau {attempt} lần lỗi.")
                                    completed_chunks.add(chunk_idx)
                            chunk_queue.task_done()

                # Launch concurrent workers
                threads = []
                for _ in range(num_workers):
                    t = threading.Thread(target=worker_fn, daemon=True)
                    threads.append(t)
                    t.start()

                # Monitor until completion or stop
                while not stop_event.is_set():
                    with chunk_lock:
                        if len(completed_chunks) >= total_chunks:
                            break
                    if not key_pool.has_available_keys():
                        break
                    time.sleep(0.5)

                if stop_event.is_set():
                    while not chunk_queue.empty():
                        try:
                            chunk_queue.get_nowait()
                            chunk_queue.task_done()
                        except Exception:
                            break

                for t in threads:
                    t.join(timeout=3.0)

                if not stop_event.is_set() and len(completed_chunks) >= total_chunks:
                    self.add_log(project_id, "success", f"Hoàn thành chương: {chap.title} ({chap.progress_percent}%)")

            if not stop_event.is_set():
                self.add_log(project_id, "success", "Tất cả các chương yêu cầu đã được dịch xong!")

        except Exception as e:
            logger.exception("Fatal in translation loop")
            self.add_log(project_id, "error", f"Lỗi hệ thống: {str(e)}")

        finally:
            with self._lock:
                if project_id in self._active_jobs:
                    self._active_jobs[project_id]["status"] = "idle"
                if project_id in self._project_states:
                    self._project_states[project_id]["status_text"] = "Sẵn sàng"
            self.add_log(project_id, "info", "Đã kết thúc phiên dịch.")


worker_instance = TranslationWorker()
