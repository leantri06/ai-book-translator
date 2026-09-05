"""
Asynchronous Translation Worker & Realtime Event Broadcaster.
Handles background translation jobs, chunk-by-chunk auto-saving, pause/resume, and SSE streams.
"""
import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Set
from dataclasses import asdict

from core.parser import BookProject, BookChapter, BookParagraph
from core.chunker import ParagraphChunker, TranslationChunk
from core.translator import AITranslator
from core.glossary import BookGlossary
from server.database import ProjectManager

logger = logging.getLogger("TranslatorWorker")


class TranslationWorker:
    """Manages active background translation jobs."""

    def __init__(self):
        self._active_jobs: Dict[str, dict] = {}  # {project_id: {"thread": Thread, "stop_event": Event, "status": "running"}}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}  # {project_id: set(queues)}
        self._lock = threading.Lock()

    def subscribe(self, project_id: str) -> asyncio.Queue:
        with self._lock:
            if project_id not in self._subscribers:
                self._subscribers[project_id] = set()
            q = asyncio.Queue(maxsize=100)
            self._subscribers[project_id].add(q)
            return q

    def unsubscribe(self, project_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            if project_id in self._subscribers:
                self._subscribers[project_id].discard(q)

    def broadcast(self, project_id: str, event_type: str, data: dict) -> None:
        """Sends an event payload to all active SSE listener queues for this project."""
        payload = {"event": event_type, "data": data, "timestamp": time.time()}
        with self._lock:
            queues = list(self._subscribers.get(project_id, []))

        for q in queues:
            try:
                q.put_nowait(payload)
            except Exception:
                pass

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
                self.broadcast(project_id, "status_change", {"status": "paused", "message": "Đang tạm dừng..."})

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
            thread.start()
            return True

    def _run_translation_loop(self, project_id: str, target_chapter_id: Optional[str], stop_event: threading.Event) -> None:
        """Background thread executing the translation work."""
        self.broadcast(project_id, "status_change", {"status": "running", "message": "Bắt đầu dịch..."})

        try:
            # 1. Load settings & initialize AI Translator
            settings = ProjectManager.get_settings()
            translator = AITranslator(
                provider=settings.get("provider", "gemini"),
                api_key=settings.get("api_key", ""),
                model=settings.get("model", ""),
                base_url=settings.get("base_url", ""),
                temperature=settings.get("temperature", 0.3)
            )

            # 2. Load Glossary
            glossary = ProjectManager.load_glossary(project_id)

            # 3. Load Project
            project = ProjectManager.load_project(project_id, load_all_paragraphs=False)
            if not project:
                self.broadcast(project_id, "error", {"message": f"Không tìm thấy dự án {project_id}"})
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
                self.broadcast(project_id, "complete", {"message": "Tất cả các chương đã được dịch hoàn tất!"})
                return

            chunker = ParagraphChunker(target_word_count=600, max_paragraphs=8)

            for chap in chapters_to_process:
                if stop_event.is_set():
                    break

                self.broadcast(project_id, "chapter_start", {
                    "chapter_id": chap.id,
                    "title": chap.title,
                    "total_paras": chap.total_paragraphs
                })

                chunks = chunker.create_chunks(chap, only_pending=True)
                total_chunks = len(chunks)

                for chunk_idx, chunk in enumerate(chunks):
                    if stop_event.is_set():
                        break

                    self.broadcast(project_id, "log", {
                        "level": "info",
                        "text": f"[{chap.title[:25]}] Đang dịch đoạn {chunk_idx + 1}/{total_chunks} ({chunk.total_words} từ)..."
                    })

                    # Call AI Translation
                    try:
                        translated_map = translator.translate_chunk(chunk, glossary)
                    except Exception as e:
                        logger.error(f"Translation chunk error: {e}")
                        self.broadcast(project_id, "log", {
                            "level": "error",
                            "text": f"Lỗi khi gọi AI: {str(e)}. Thử lại sau 3s..."
                        })
                        time.sleep(3)
                        if stop_event.is_set():
                            break
                        try:
                            translated_map = translator.translate_chunk(chunk, glossary)
                        except Exception as e2:
                            self.broadcast(project_id, "error", {
                                "message": f"Không thể dịch đoạn {chunk_idx + 1}: {str(e2)}"
                            })
                            continue

                    # Update chapter paragraphs
                    updated_paras = []
                    for p in chunk.paragraphs:
                        if p.id in translated_map and translated_map[p.id]:
                            p.translated_text = translated_map[p.id]
                            p.status = "done"
                            updated_paras.append({"id": p.id, "text": p.translated_text, "status": "done"})

                    # Save chapter to disk immediately
                    ProjectManager.save_chapter(project_id, chap)

                    # Reload updated project metadata
                    updated_proj = ProjectManager.load_project(project_id, load_all_paragraphs=False)
                    overall_progress = updated_proj.progress_percent if updated_proj else 0.0

                    self.broadcast(project_id, "chunk_done", {
                        "chapter_id": chap.id,
                        "chunk_index": chunk_idx + 1,
                        "total_chunks": total_chunks,
                        "chapter_progress": chap.progress_percent,
                        "overall_progress": overall_progress,
                        "updated_paragraphs": updated_paras
                    })

                    time.sleep(0.3)  # Gentle pacing

                self.broadcast(project_id, "chapter_done", {
                    "chapter_id": chap.id,
                    "title": chap.title,
                    "progress": chap.progress_percent
                })

            if not stop_event.is_set():
                self.broadcast(project_id, "complete", {
                    "message": "Quá trình dịch đã hoàn tất thành công!"
                })

        except Exception as e:
            logger.exception("Fatal in translation loop")
            self.broadcast(project_id, "error", {"message": f"Lỗi hệ thống: {str(e)}"})

        finally:
            with self._lock:
                if project_id in self._active_jobs:
                    self._active_jobs[project_id]["status"] = "idle"
            self.broadcast(project_id, "status_change", {"status": "idle", "message": "Đã dừng"})


# Global worker instance
worker_instance = TranslationWorker()
