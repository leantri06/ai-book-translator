"""
Project Database & State Persistence for Book Translation.
Saves chapters, paragraphs, progress, glossaries, and settings incrementally.
"""
import os
import json
import time
import re
import tempfile
from typing import List, Optional, Dict
from dataclasses import asdict
from core.parser import BookProject, BookChapter, BookParagraph
from core.glossary import BookGlossary


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

os.makedirs(PROJECTS_DIR, exist_ok=True)

def project_path(project_id: str, *parts: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", project_id):
        raise ValueError("Invalid project identifier")
    if any(not part or part in (".", "..") or "/" in part or "\\" in part or ":" in part for part in parts):
        raise ValueError("Invalid storage path component")
    root = os.path.realpath(PROJECTS_DIR)
    target = os.path.realpath(os.path.join(root, project_id, *parts))
    if os.path.commonpath([root, target]) != root or target == root:
        raise ValueError("Path escapes project storage")
    return target

def atomic_write_json(path: str, data) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


class ProjectManager:
    """Manages reading and writing project files."""

    @staticmethod
    def get_settings() -> dict:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "provider": "gemini",
            "api_key": "",
            "model": "gemini-2.5-flash",
            "base_url": "",
            "temperature": 0.3
        }

    @staticmethod
    def save_settings(settings: dict) -> None:
        atomic_write_json(SETTINGS_FILE, settings)

    @classmethod
    def list_projects(cls) -> List[dict]:
        projects = []
        if not os.path.exists(PROJECTS_DIR):
            return []

        for p_id in os.listdir(PROJECTS_DIR):
            proj_dir = os.path.join(PROJECTS_DIR, p_id)
            meta_file = os.path.join(proj_dir, "meta.json")
            if os.path.isdir(proj_dir) and os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    projects.append(meta)
                except Exception:
                    continue

        # Sort by updated_at descending
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return projects

    @classmethod
    def save_new_project(cls, project: BookProject, glossary: Optional[BookGlossary] = None) -> None:
        proj_dir = project_path(project.id)
        os.makedirs(proj_dir, exist_ok=True)
        chapters_dir = os.path.join(proj_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        project.created_at = now
        project.updated_at = now

        # Save chapters individually
        for chap in project.chapters:
            chap_file = project_path(project.id, "chapters", f"{chap.id}.json")
            atomic_write_json(chap_file, asdict(chap))

        # Save glossary
        if not glossary:
            glossary = BookGlossary()
        cls.save_glossary(project.id, glossary)

        # Save metadata
        cls.update_project_meta(project)

    @classmethod
    def update_project_meta(cls, project: BookProject) -> None:
        proj_dir = project_path(project.id)
        meta_file = os.path.join(proj_dir, "meta.json")

        meta = {
            "id": project.id,
            "title": project.title,
            "author": project.author,
            "source_format": project.source_format,
            "source_file_path": project.source_file_path,
            "cover_image_path": project.cover_image_path,
            "total_chapters": project.total_chapters,
            "total_paragraphs": project.total_paragraphs,
            "translated_paragraphs": project.translated_paragraphs,
            "total_words": project.total_words,
            "progress_percent": project.progress_percent,
            "created_at": project.created_at or time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        atomic_write_json(meta_file, meta)

    @classmethod
    def load_project(cls, project_id: str, load_all_paragraphs: bool = False) -> Optional[BookProject]:
        proj_dir = project_path(project_id)
        meta_file = os.path.join(proj_dir, "meta.json")
        if not os.path.exists(meta_file):
            return None

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        chapters_dir = os.path.join(proj_dir, "chapters")
        chapters: List[BookChapter] = []

        if os.path.exists(chapters_dir):
            chap_files = sorted(os.listdir(chapters_dir), key=lambda x: int(x.replace("chap_", "").replace(".json", "")) if x.replace("chap_", "").replace(".json", "").isdigit() else 9999)
            for cf in chap_files:
                if cf.endswith(".json"):
                    with open(os.path.join(chapters_dir, cf), "r", encoding="utf-8") as f:
                        c_data = json.load(f)

                    if load_all_paragraphs:
                        paras = [BookParagraph(**p) for p in c_data.get("paragraphs", [])]
                    else:
                        paras = [BookParagraph(id=p["id"], original_text=p.get("original_text", ""), status=p.get("status", "pending")) for p in c_data.get("paragraphs", [])]

                    chap = BookChapter(
                        id=c_data["id"],
                        title=c_data["title"],
                        paragraphs=paras,
                        doc_name=c_data.get("doc_name", ""),
                        order=c_data.get("order", 0),
                        raw_html=c_data.get("raw_html", "")
                    )
                    chapters.append(chap)

        return BookProject(
            id=meta["id"],
            title=meta["title"],
            author=meta.get("author", "Tác giả"),
            source_format=meta.get("source_format", "epub"),
            source_file_path=meta.get("source_file_path", ""),
            cover_image_path=meta.get("cover_image_path", ""),
            chapters=chapters,
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", "")
        )

    @classmethod
    def load_chapter(cls, project_id: str, chapter_id: str) -> Optional[BookChapter]:
        chap_file = project_path(project_id, "chapters", f"{chapter_id}.json")
        if not os.path.exists(chap_file):
            return None

        with open(chap_file, "r", encoding="utf-8") as f:
            c_data = json.load(f)

        paras = [BookParagraph(**p) for p in c_data.get("paragraphs", [])]
        return BookChapter(
            id=c_data["id"],
            title=c_data["title"],
            paragraphs=paras,
            doc_name=c_data.get("doc_name", ""),
            order=c_data.get("order", 0),
            raw_html=c_data.get("raw_html", "")
        )

    @classmethod
    def save_chapter(cls, project_id: str, chapter: BookChapter) -> None:
        chap_file = project_path(project_id, "chapters", f"{chapter.id}.json")
        atomic_write_json(chap_file, asdict(chapter))

        # Update meta
        project = cls.load_project(project_id, load_all_paragraphs=False)
        if project:
            cls.update_project_meta(project)

    @classmethod
    def update_paragraph(cls, project_id: str, chapter_id: str, para_id: str, translated_text: str, status: str = "edited") -> bool:
        chapter = cls.load_chapter(project_id, chapter_id)
        if not chapter:
            return False

        updated = False
        for p in chapter.paragraphs:
            if p.id == para_id:
                p.translated_text = translated_text
                p.status = status
                updated = True
                break

        if updated:
            cls.save_chapter(project_id, chapter)
        return updated

    @classmethod
    def load_glossary(cls, project_id: str) -> BookGlossary:
        g_file = project_path(project_id, "glossary.json")
        if os.path.exists(g_file):
            try:
                with open(g_file, "r", encoding="utf-8") as f:
                    return BookGlossary.from_dict(json.load(f))
            except Exception:
                pass
        return BookGlossary()

    @classmethod
    def save_glossary(cls, project_id: str, glossary: BookGlossary) -> None:
        g_file = project_path(project_id, "glossary.json")
        atomic_write_json(g_file, glossary.to_dict())
