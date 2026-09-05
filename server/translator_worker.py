"""
Asynchronous Translation Worker with Thread-Safe State & Buffer.
Handles background translation jobs, chunk-by-chunk auto-saving, pause/resume, and real-time polling state.
"""
import threading
import time
import logging
from typing import Dict, List, Optional
from dataclasses import asdict

from core.parser import BookProject, BookChapter, BookParagraph
from core.chunker import ParagraphChunker, TranslationChunk
from core.translator import AITranslator
from core.glossary import BookGlossary
from server.database import ProjectManager

logger = logging.getLogger("TranslatorWorker")


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

    def start_translation(self, project_id: str, chapter_id: Optional[str] = None) -> bool:
        with self._lock:
            if self.is_running(project_id):
                return False

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run_translation_loop,
                args=(project_id, chapter_id, stop_event),
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

    def _run_translation_loop(self, project_id: str, target_chapter_id: Optional[str], stop_event: threading.Event) -> None:
        """Background thread executing the translation work."""
        self.add_log(project_id, "info", "Khởi động phiên dịch...")

        try:
            # 1. Load settings & initialize AI Translator
            settings = ProjectManager.get_settings()
            translator = AITranslator(
                provider=settings.get("provider", "gemini"),
                api_key=settings.get("api_key", ""),
                model=settings.get("model", "gemini-3.6-flash"),
                base_url=settings.get("base_url", ""),
                temperature=settings.get("temperature", 0.3)
            )

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
                    chapters_to_process.append(chap)
            else:
                for c_meta in project.chapters:
                    c = ProjectManager.load_chapter(project_id, c_meta.id)
                    if c and c.progress_percent < 100.0:
                        chapters_to_process.append(c)

            if not chapters_to_process:
                self.add_log(project_id, "success", "Tất cả các chương đã được dịch hoàn tất!")
                return

            chunker = ParagraphChunker(target_word_count=500, max_paragraphs=6)

            for chap in chapters_to_process:
                if stop_event.is_set():
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

                for chunk_idx, chunk in enumerate(chunks):
                    if stop_event.is_set():
                        break

                    self.add_log(project_id, "info", f"[{chap.title[:20]}] Đang dịch đoạn {chunk_idx + 1}/{total_chunks} ({chunk.total_words} từ)...")

                    # Call AI Translation
                    try:
                        translated_map = translator.translate_chunk(chunk, glossary)
                    except Exception as e:
                        logger.error(f"Translation chunk error: {e}")
                        self.add_log(project_id, "error", f"Lỗi gọi AI: {str(e)}. Thử lại sau 2s...")
                        time.sleep(2)
                        if stop_event.is_set():
                            break
                        try:
                            translated_map = translator.translate_chunk(chunk, glossary)
                        except Exception as e2:
                            self.add_log(project_id, "error", f"Đoạn {chunk_idx + 1} gặp lỗi: {str(e2)}")
                            continue

                    # Update chapter paragraphs
                    now_ts = time.time()
                    updated_paras = []
                    for p in chunk.paragraphs:
                        if p.id in translated_map and translated_map[p.id]:
                            p.translated_text = translated_map[p.id]
                            p.status = "done"
                            updated_paras.append({"id": p.id, "text": p.translated_text, "chapter_id": chap.id, "timestamp": now_ts})

                    # Save chapter to disk immediately
                    ProjectManager.save_chapter(project_id, chap)

                    # Reload updated project metadata
                    updated_proj = ProjectManager.load_project(project_id, load_all_paragraphs=False)
                    overall_progress = updated_proj.progress_percent if updated_proj else 0.0

                    with self._lock:
                        st = self._project_states.setdefault(project_id, {})
                        st["chapter_id"] = chap.id
                        st["chapter_title"] = chap.title
                        st["chapter_progress"] = chap.progress_percent
                        st["overall_progress"] = overall_progress
                        st["status_text"] = f"Đang dịch: {chap.title[:25]} ({chap.progress_percent}%)"
                        # Keep recent updated paragraphs
                        st.setdefault("updated_paragraphs", []).extend(updated_paras)
                        if len(st["updated_paragraphs"]) > 200:
                            st["updated_paragraphs"] = st["updated_paragraphs"][-200:]

                    time.sleep(0.2)

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
