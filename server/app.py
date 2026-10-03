"""
FastAPI Server for AI Book Translator Pro.
Provides RESTful APIs, SSE streaming, file upload/export, and serves modern SPA Web UI.
"""
import os
import shutil
import tempfile
import asyncio
import json
import requests
from typing import Optional, List
import re
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.parser import BookParser, BookProject, BookChapter, BookParagraph
from core.glossary import BookGlossary, CharacterPronoun, TerminologyItem
from core.exporter import BookExporter
from core.textbook_parser import TextbookParser
from server.database import ProjectManager, PROJECTS_DIR, SETTINGS_FILE, project_path, atomic_write_json
from server.translator_worker import worker_instance

app = FastAPI(title="AI Book Translator Pro", version="2.0")

@app.middleware("http")
async def validate_project_path(request: Request, call_next):
    parts = request.url.path.split("/")
    if len(parts) > 3 and parts[1:3] == ["api", "projects"]:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", parts[3]):
            return JSONResponse(status_code=400, content={"detail": "Invalid project identifier"})
        if len(parts) > 5 and parts[4] in ("chapters", "images"):
            try:
                project_path(parts[3], parts[4], parts[5])
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid resource path"})
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)


# Models
class SettingsModel(BaseModel):
    provider: str
    api_key: str
    model: str
    base_url: str = ""
    temperature: float = 0.3


class ParagraphUpdateModel(BaseModel):
    translated_text: str


class GlossaryUpdateModel(BaseModel):
    tone: str = "novel"
    custom_instructions: str = ""
    characters: List[dict] = []
    terms: List[dict] = []


class CheckQuotaModel(BaseModel):
    provider: str = "gemini"
    api_key: str = ""
    base_url: str = ""


class ProjectMetaUpdateModel(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None


# --- API Routes ---

@app.get("/api/settings")
def get_settings():
    return ProjectManager.get_settings()


@app.post("/api/settings")
def save_settings(settings: SettingsModel):
    ProjectManager.save_settings(settings.model_dump())
    return {"status": "ok", "message": "Cấu hình API đã được lưu thành công."}


@app.post("/api/settings/check-quota")
def check_quota(data: CheckQuotaModel):
    """Pings and evaluates quota, rate-limits, and health across all submitted API keys in parallel."""
    import concurrent.futures
    provider = data.provider.lower()
    raw_keys = data.api_key.replace('\r', '\n').replace(';', ',').replace('\n', ',')
    api_keys = [k.strip() for k in raw_keys.split(',') if k.strip()]
    if not api_keys:
        return {"status": "empty", "keys": [], "message": "Chưa nhập API Key nào."}

    test_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]

    def test_single_key(item):
        idx, key = item
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        res = {
            "key_index": idx + 1,
            "masked_key": masked,
            "status": "ok",
            "summary": "",
            "models": []
        }

        if provider == "gemini":
            has_ok = False
            has_daily = False
            has_rpm = False
            all_invalid = True

            for m in test_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
                try:
                    r = requests.post(url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=10)
                    if r.status_code == 200:
                        has_ok = True
                        all_invalid = False
                        res["models"].append({"model": m, "status": "ok", "text": "Sẵn sàng (Còn Quota)"})
                    elif r.status_code == 429:
                        all_invalid = False
                        err = r.json().get("error", {}).get("message", "")
                        if "perday" in err.lower() or "per_day" in err.lower() or "generaterequestsperday" in err.lower():
                            has_daily = True
                            res["models"].append({"model": m, "status": "daily_limit", "text": "Hết lượt ngày (24h Quota)"})
                        else:
                            has_rpm = True
                            res["models"].append({"model": m, "status": "rpm_wait", "text": "Chờ hồi lượt (15 RPM)"})
                    elif r.status_code in (400, 403):
                        res["models"].append({"model": m, "status": "invalid", "text": f"Key không hợp lệ ({r.status_code})"})
                    else:
                        res["models"].append({"model": m, "status": "other", "text": f"Mã lỗi {r.status_code}"})
                except Exception as ex:
                    res["models"].append({"model": m, "status": "error", "text": f"Lỗi: {str(ex)}"})

            if all_invalid:
                res["status"] = "error"
                res["summary"] = "Key không hợp lệ hoặc bị khóa"
            elif has_ok:
                res["status"] = "ok"
                res["summary"] = "Hoạt động tốt (Sẵn sàng dịch)"
            elif has_daily:
                res["status"] = "daily_limit"
                res["summary"] = "Hết hạn mức 24h trên một số model"
            elif has_rpm:
                res["status"] = "rpm_wait"
                res["summary"] = "Đang tạm chờ hồi lượt (15 RPM)"
            else:
                res["status"] = "warning"
                res["summary"] = "Tạm thời không khả dụng"

        elif provider in ("deepseek", "openai_compatible", "openrouter", "ollama", "openai"):
            base_url = data.base_url.rstrip("/") if data.base_url else ("https://api.deepseek.com/v1" if provider == "deepseek" else "https://api.openai.com/v1")
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {key}"}
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    res["status"] = "ok"
                    res["summary"] = "Kết nối thành công (Key hợp lệ)"
                elif r.status_code == 401:
                    res["status"] = "error"
                    res["summary"] = "API Key không hợp lệ (401)"
                elif r.status_code == 429:
                    res["status"] = "daily_limit"
                    res["summary"] = "Hết số dư / Quota (429)"
                else:
                    res["status"] = "warning"
                    res["summary"] = f"Phản hồi mã {r.status_code}"
            except Exception:
                res["status"] = "error"
                res["summary"] = "Không thể kết nối đến server"

        else:
            res["status"] = "ok"
            res["summary"] = "Chế độ dùng thử miễn phí (Không cần key)"

        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(api_keys), 8)) as executor:
        results = list(executor.map(test_single_key, enumerate(api_keys)))

    return {"status": "ok", "keys": results}


@app.get("/api/projects")
def list_projects():
    return ProjectManager.list_projects()


@app.post("/api/projects/upload")
def upload_book(file: UploadFile = File(...), document_type: Optional[str] = Form(None)):
    """Uploads a book file, parses it, and creates a new project."""
    filename = os.path.basename((file.filename or "").replace("\\", "/"))
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".epub", ".pdf", ".docx", ".txt", ".md"):
        raise HTTPException(status_code=400, detail="Định dạng file không hỗ trợ. Vui lòng tải file EPUB, PDF, DOCX, TXT.")

    # Validate document_type vs extension BEFORE saving the file
    mode = None
    if document_type and document_type.strip():
        mode = document_type.strip().lower()
        allowed_ext_map = {
            "paper": {".pdf"},
            "novel": {".epub", ".docx", ".txt", ".md"},
        }
        if mode not in allowed_ext_map:
            raise HTTPException(status_code=400, detail="Chọn Paper hoặc Novel; chuyển giáo trình dùng chức năng riêng.")
        if ext not in allowed_ext_map[mode]:
            raise HTTPException(
                status_code=400,
                detail=f"Document type '{mode}' is not compatible with file extension '{ext}'."
            )

    import uuid
    project_id = uuid.uuid4().hex
    save_path = os.path.join(UPLOADS_DIR, f"{project_id}{ext}")

    try:
        total_bytes = 0
        with open(save_path, "wb") as buffer:
            while block := file.file.read(1024 * 1024):
                total_bytes += len(block)
                if total_bytes > 100 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="File exceeds 100 MiB limit")
                buffer.write(block)
        if not total_bytes:
            raise HTTPException(status_code=400, detail="Empty upload")
        if mode:
            project = BookParser.parse_file(save_path, project_id, document_type=mode)
        else:
            project = BookParser.parse_file(save_path, project_id)
        if ext in (".txt", ".md"):
            project.title = os.path.splitext(filename)[0]
        # Pre-seed glossary: academic tone for paper, novel for everything else
        glossary = BookGlossary()
        if project.document_type == "paper":
            glossary.tone = "academic"
        else:
            glossary.tone = "novel"
        ProjectManager.save_new_project(project, glossary)
        return {
            "status": "ok",
            "project_id": project.id,
            "title": project.title,
            "author": project.author,
            "chapters_count": project.total_chapters,
            "paragraphs_count": project.total_paragraphs,
            "words_count": project.total_words,
            "document_type": project.document_type,
            "structure_warnings": list(project.structure_warnings),
        }
    except Exception as e:
        if os.path.isfile(save_path):
            os.remove(save_path)
        partial_project = project_path(project_id)
        if os.path.isdir(partial_project):
            shutil.rmtree(partial_project)
        if isinstance(e, HTTPException):
            raise
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=f"Lỗi khi đọc file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc file: {str(e)}")
    finally:
        file.file.close()


@app.get("/api/projects/{project_id}")
def get_project_details(project_id: str):
    project = ProjectManager.load_project(project_id, load_all_paragraphs=False)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")

    chapters_summary = [
        {
            "id": c.id,
            "title": c.title,
            "total_paragraphs": c.total_paragraphs,
            "translated_paragraphs": c.translated_paragraphs,
            "progress_percent": c.progress_percent,
            "order": c.order
        }
        for c in project.chapters
    ]

    return {
        "id": project.id,
        "title": project.title,
        "author": project.author,
        "source_format": project.source_format,
        "total_chapters": project.total_chapters,
        "total_paragraphs": project.total_paragraphs,
        "translated_paragraphs": project.translated_paragraphs,
        "progress_percent": project.progress_percent,
        "total_words": project.total_words,
        "chapters": chapters_summary,
        "is_translating": worker_instance.is_running(project_id),
        "document_type": project.document_type,
        "structure_warnings": list(project.structure_warnings),
    }


@app.put("/api/projects/{project_id}/meta")
def update_project_metadata(project_id: str, data: ProjectMetaUpdateModel):
    proj_dir = project_path(project_id)
    meta_file = os.path.join(proj_dir, "meta.json")
    if not os.path.exists(meta_file):
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    if data.title is not None and data.title.strip():
        meta["title"] = data.title.strip()
    if data.author is not None:
        meta["author"] = data.author.strip()
    atomic_write_json(meta_file, meta)
    return {"status": "ok", "message": "Đã cập nhật thông tin dự án.", "title": meta["title"], "author": meta["author"]}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    if worker_instance.is_running(project_id):
        raise HTTPException(status_code=409, detail="Stop translation and wait before deleting")
    worker_instance.stop_translation(project_id)
    proj_dir = project_path(project_id)
    if os.path.exists(proj_dir):
        shutil.rmtree(proj_dir, ignore_errors=True)
    try:
        if os.path.exists(UPLOADS_DIR):
            for fname in os.listdir(UPLOADS_DIR):
                if fname.startswith(f"{project_id}_") or os.path.splitext(fname)[0] == project_id:
                    fpath = os.path.join(UPLOADS_DIR, fname)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
    except Exception:
        pass
    return {"status": "ok", "message": "Đã xóa dự án."}


@app.get("/api/projects/{project_id}/chapters/{chapter_id}")
def get_chapter(project_id: str, chapter_id: str):
    chapter = ProjectManager.load_chapter(project_id, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Không tìm thấy chương sách")

    return {
        "id": chapter.id,
        "title": chapter.title,
        "order": chapter.order,
        "total_paragraphs": chapter.total_paragraphs,
        "translated_paragraphs": chapter.translated_paragraphs,
        "progress_percent": chapter.progress_percent,
        "paragraphs": [
            {
                "id": p.id,
                "original_text": p.original_text,
                "translated_text": p.translated_text,
                "status": p.status,
                "tag": p.tag,
                "index": p.index,
                "image_path": getattr(p, "image_path", "")
            }
            for p in chapter.paragraphs
        ]
    }


@app.get("/api/projects/{project_id}/images/{image_name}")
def get_project_image(project_id: str, image_name: str):
    from fastapi.responses import FileResponse
    img_path = project_path(project_id, "images", image_name)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy hình ảnh")
    return FileResponse(img_path)


@app.put("/api/projects/{project_id}/chapters/{chapter_id}/paragraphs/{para_id}")
def update_paragraph(project_id: str, chapter_id: str, para_id: str, payload: ParagraphUpdateModel):
    if worker_instance.is_running(project_id):
        raise HTTPException(status_code=409, detail="Stop translation before editing")
    success = ProjectManager.update_paragraph(project_id, chapter_id, para_id, payload.translated_text, status="edited")
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy đoạn văn bản")
    return {"status": "ok", "message": "Đã cập nhật đoạn văn"}


@app.post("/api/projects/{project_id}/translate/start")
def start_translation(project_id: str, chapter_id: Optional[str] = None, force: bool = False):
    if not ProjectManager.load_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if chapter_id and not ProjectManager.load_chapter(project_id, chapter_id):
        raise HTTPException(status_code=404, detail="Chapter not found")
    success = worker_instance.start_translation(project_id, chapter_id, force_retranslate=force)
    if not success:
        return {"status": "already_running", "message": "Tiến trình dịch đang chạy sẵn."}
    return {"status": "ok", "message": "Đã khởi động tiến trình dịch."}


@app.post("/api/projects/{project_id}/translate/stop")
def stop_translation(project_id: str):
    worker_instance.stop_translation(project_id)
    return {"status": "ok", "message": "Đã gửi lệnh tạm dừng."}


@app.get("/api/projects/{project_id}/translate/status")
def translation_status(project_id: str):
    return {"is_running": worker_instance.is_running(project_id)}


@app.get("/api/projects/{project_id}/glossary")
def get_glossary(project_id: str):
    project = ProjectManager.load_project(project_id, load_all_paragraphs=False)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    glossary = ProjectManager.load_glossary(project_id)
    # Normalize tone by project type
    if project.document_type == "paper" and glossary.tone != "academic":
        glossary.tone = "academic"
    elif project.document_type == "novel" and glossary.tone == "academic":
        glossary.tone = "novel"
    return glossary.to_dict()


@app.post("/api/projects/{project_id}/glossary")
def save_glossary(project_id: str, data: GlossaryUpdateModel):
    project = ProjectManager.load_project(project_id, load_all_paragraphs=False)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    glossary = BookGlossary.from_dict(data.model_dump())
    # Normalize tone by project type
    if project.document_type == "paper":
        glossary.tone = "academic"
    elif project.document_type == "novel" and glossary.tone == "academic":
        glossary.tone = "novel"
    ProjectManager.save_glossary(project_id, glossary)
    return {"status": "ok", "message": "Đã lưu bảng thuật ngữ và quy tắc xưng hô."}


@app.post("/api/projects/{project_id}/glossary/auto_detect")
def auto_detect_characters(project_id: str):
    """
    Uses AI (Gemini / LLM) and text analysis to automatically identify characters,
    their genders, roles, and Vietnamese literary pronouns (xưng hô).
    """
    import re
    import requests
    from collections import Counter

    project = ProjectManager.load_project(project_id, load_all_paragraphs=False)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")

    # Paper/academic projects should not use literature-style character auto-detection
    if project.document_type == "paper":
        raise HTTPException(
            status_code=400,
            detail="Auto-detect characters is not available for academic paper projects."
        )

    settings = ProjectManager.get_settings()
    api_key = settings.get("api_key", "")
    provider = settings.get("provider", "gemini")

    # Try AI extraction first if API key is present
    if provider == "gemini" and api_key:
        try:
            model = settings.get("model", "gemini-3.6-flash")
            if model in ("gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"):
                model = "gemini-3.6-flash"

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            prompt = f"""Bạn là một chuyên gia nghiên cứu văn học và dịch thuật sách chuyên nghiệp.
Hãy phân tích cuốn sách sau:
- Tựa đề: {project.title}
- Tác giả: {project.author}

Nhiệm vụ: Trích xuất danh sách 8-15 nhân vật chính và quan trọng nhất trong tác phẩm này, đồng thời thiết lập quy tắc đại từ xưng hô trong tiếng Việt văn học mượt mà nhất.
BẮT BUỘC trả về duy nhất định dạng JSON (mảng các object):
[
  {{
    "name": "Tên nhân vật (tiếng Anh chuẩn)",
    "gender": "male hoặc female",
    "role": "Vai trò / miêu tả ngắn trong truyện (tiếng Việt)",
    "first_person": "đại từ ngôi 1 khi nói chuyện (ví dụ: tôi / ta / mình / em)",
    "second_person": "đại từ ngôi 2 khi gọi đối phương (ví dụ: cậu / nàng / em / anh / ngài / thầy)",
    "third_person": "đại từ ngôi 3 khi kể chuyện (ví dụ: chàng / nàng / cậu ấy / cô ấy / hắn)",
    "notes": "Ghi chú quan hệ xưng hô với các nhân vật khác (rất quan trọng)"
  }}
]"""

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }

            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                text_out = data['candidates'][0]['content']['parts'][0]['text']
                ai_chars = json.loads(text_out)

                existing_glossary = ProjectManager.load_glossary(project_id)
                existing_glossary.characters = {}  # Refresh with high-precision AI list

                added_names = []
                for c in ai_chars:
                    name = c.get("name", "").strip()
                    if name:
                        existing_glossary.add_character(
                            name=name,
                            gender=c.get("gender", "unknown"),
                            role=c.get("role", ""),
                            first_person=c.get("first_person", "tôi"),
                            second_person=c.get("second_person", "cậu"),
                            third_person=c.get("third_person", name),
                            notes=c.get("notes", "")
                        )
                        added_names.append(name)

                ProjectManager.save_glossary(project_id, existing_glossary)
                worker_instance.add_log(project_id, "success",
                    f"AI đã tự động phân tích thành công {len(added_names)} nhân vật và quy tắc xưng hô cho '{project.title}'!"
                )
                return {
                    "status": "ok",
                    "detected_count": len(added_names),
                    "names": added_names,
                    "method": "ai",
                    "glossary": existing_glossary.to_dict()
                }
        except Exception as e:
            # Fall through to heuristic scan if AI call fails
            pass

    # Fallback heuristic: Scan first chapters text for dialogue tags
    full_proj = ProjectManager.load_project(project_id, load_all_paragraphs=True)
    dialogue_verbs = r'(?:said|asked|replied|whispered|shouted|muttered|cried|sighed|nodded|gasped|yelled|grunted|called|answered)'
    pattern1 = re.compile(rf'{dialogue_verbs}\s+([A-Z][a-z]{{2,15}})', re.IGNORECASE)
    pattern2 = re.compile(rf'([A-Z][a-z]{{2,15}})\s+{dialogue_verbs}', re.IGNORECASE)

    name_counts = Counter()
    for chap in full_proj.chapters[:8]:
        for p in chap.paragraphs:
            text = p.original_text
            for m in pattern1.findall(text):
                name = m.capitalize()
                if name not in ("He", "She", "It", "They", "The", "One", "Someone", "Nobody", "Who", "What", "Then", "There"):
                    name_counts[name] += 1
            for m in pattern2.findall(text):
                name = m.capitalize()
                if name not in ("He", "She", "It", "They", "The", "One", "Someone", "Nobody", "Who", "What", "Then", "There"):
                    name_counts[name] += 1

    existing_glossary = ProjectManager.load_glossary(project_id)
    added_names = []
    for name, count in name_counts.most_common(12):
        if count >= 2 and not existing_glossary.get_character(name):
            existing_glossary.add_character(
                name=name,
                gender="unknown",
                role=f"Nhân vật (xuất hiện {count} lần)",
                first_person="tôi",
                second_person="cậu",
                third_person=name
            )
            added_names.append(name)

    ProjectManager.save_glossary(project_id, existing_glossary)
    return {
        "status": "ok",
        "detected_count": len(added_names),
        "names": added_names,
        "method": "heuristic",
        "glossary": existing_glossary.to_dict()
    }


@app.get("/api/projects/{project_id}/export/{export_format}")
def export_book(project_id: str, export_format: str):
    """Generates and downloads the translated book in the requested format."""
    project = ProjectManager.load_project(project_id, load_all_paragraphs=True)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")

    safe_title = "".join(c for c in project.title if c.isalnum() or c in (' ', '_', '-')).strip() or "book"
    format_lower = export_format.lower()

    bilingual = "bilingual" in format_lower

    if "epub" in format_lower:
        suffix = "_SongNgu.epub" if bilingual else "_BanDich.epub"
        out_file = os.path.join(EXPORTS_DIR, f"{safe_title}{suffix}")
        BookExporter.export_epub(project, out_file, bilingual=bilingual)
        return FileResponse(out_file, media_type="application/epub+zip", filename=f"{safe_title}{suffix}")

    elif "docx" in format_lower:
        suffix = "_SongNgu.docx" if bilingual else "_BanDich.docx"
        out_file = os.path.join(EXPORTS_DIR, f"{safe_title}{suffix}")
        BookExporter.export_docx(project, out_file, bilingual=bilingual)
        return FileResponse(out_file, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=f"{safe_title}{suffix}")

    elif "html" in format_lower or "pdf" in format_lower:
        suffix = "_SongNgu.html" if bilingual else "_BanDich.html"
        out_file = os.path.join(EXPORTS_DIR, f"{safe_title}{suffix}")
        BookExporter.export_html(project, out_file, bilingual=bilingual)
        return FileResponse(out_file, media_type="text/html", filename=f"{safe_title}{suffix}")

    elif "txt" in format_lower:
        suffix = "_SongNgu.txt" if bilingual else "_BanDich.txt"
        out_file = os.path.join(EXPORTS_DIR, f"{safe_title}{suffix}")
        BookExporter.export_txt(project, out_file, bilingual=bilingual)
        return FileResponse(out_file, media_type="text/plain; charset=utf-8", filename=f"{safe_title}{suffix}")

    else:
        raise HTTPException(status_code=400, detail=f"Định dạng xuất bản không hỗ trợ: {export_format}")


@app.get("/api/projects/{project_id}/status")
def get_project_status(project_id: str, since: float = 0.0):
    """Returns live translation progress, new logs, and updated paragraphs."""
    return worker_instance.get_state(project_id, since)


# --- Textbook PDF to EPUB Conversion Engine ---

textbook_tasks = {}

def _run_textbook_conversion(task_id: str, file_path: str):
    task = textbook_tasks[task_id]
    try:
        settings = ProjectManager.get_settings()
        raw_keys = settings.get("api_key", "").replace('\r', '\n').replace(';', ',').replace('\n', ',')
        api_keys = [k.strip() for k in raw_keys.split(',') if k.strip()]

        def progress_cb(current, total, msg):
            pct = round((current / max(1, total)) * 100, 1)
            task["progress"] = pct
            task["current_page"] = current
            task["total_pages"] = total
            task["message"] = msg

        safe_base = os.path.splitext(os.path.basename(file_path))[0]
        safe_name = re.sub(r'^[0-9a-f]{8}_', '', safe_base)
        clean_name = re.sub(r'[^\w\s\-_]', '', safe_name).strip() or "textbook"
        out_epub = os.path.join(EXPORTS_DIR, f"{clean_name}.epub")

        project, epub_path = TextbookParser.convert_pdf_to_epub(
            file_path=file_path,
            output_epub_path=out_epub,
            data_dir=DATA_DIR,
            api_keys=api_keys,
            progress_callback=progress_cb,
            max_workers=6,
            project_id=task_id
        )

        task["status"] = "done"
        task["project_id"] = project.id
        task["title"] = project.title
        task["author"] = project.author
        task["chapters_count"] = project.total_chapters
        task["paragraphs_count"] = project.total_paragraphs
        task["epub_path"] = epub_path
        task["message"] = f"Hoàn tất chuyển đổi giáo trình sang EPUB! ({project.total_chapters} chương)"
    except Exception as e:
        task["status"] = "error"
        task["message"] = f"Lỗi: {str(e)}"


@app.post("/api/textbook/convert")
async def start_textbook_conversion(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None)
):
    import uuid
    task_id = str(uuid.uuid4())[:8]

    if file:
        file_name = file.filename
        save_path = os.path.join(UPLOADS_DIR, f"{task_id}_{file_name}")
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif filename:
        save_path = os.path.join(UPLOADS_DIR, filename)
        if not os.path.exists(save_path):
            raise HTTPException(status_code=404, detail=f"Không tìm thấy file: {filename}")
    else:
        raise HTTPException(status_code=400, detail="Vui lòng tải lên file hoặc chỉ định tên file trong thư mục uploads.")

    textbook_tasks[task_id] = {
        "status": "processing",
        "progress": 0.0,
        "current_page": 0,
        "total_pages": 0,
        "message": "Đang khởi động phân tích giáo trình...",
        "file_path": save_path
    }

    background_tasks.add_task(_run_textbook_conversion, task_id, save_path)

    return {
        "status": "ok",
        "task_id": task_id,
        "message": "Đã khởi động tiến trình chuyển đổi giáo trình trong nền."
    }


@app.get("/api/textbook/status/{task_id}")
def get_textbook_status(task_id: str):
    task = textbook_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy tiến trình chuyển đổi")
    return task


@app.get("/api/textbook/export/{task_id}")
def export_textbook_epub(task_id: str):
    task = textbook_tasks.get(task_id)
    if not task or task.get("status") != "done":
        raise HTTPException(status_code=400, detail="Tiến trình chuyển đổi chưa hoàn thành")
    epub_path = task.get("epub_path")
    if not epub_path or not os.path.exists(epub_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy file EPUB")
    return FileResponse(epub_path, media_type="application/epub+zip", filename=os.path.basename(epub_path))


# Mount static web directory
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def serve_index():
    with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
