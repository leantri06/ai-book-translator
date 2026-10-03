"""
Vietnamese Textbook Parser Engine (core/textbook_parser.py)
Specialized parser for Vietnamese university textbooks, political theory curricula,
and academic books in PDF format (supports both digital text and scanned image PDFs).
"""
import os
import re
import json
import base64
import time
import uuid
import unicodedata
import concurrent.futures
from typing import List, Dict, Tuple, Optional, Callable
import pymupdf
import requests

from core.parser import BookProject, BookChapter, BookParagraph


class TextbookParser:
    """
    Analyzes, OCRs (if scanned), structures, and parses Vietnamese textbooks into clean BookProject.
    """

    @staticmethod
    def is_scanned_pdf(doc: pymupdf.Document, sample_pages: int = 15) -> bool:
        """
        Determines whether the PDF is a scanned image document (requiring OCR)
        or a digital document with embedded text layer.
        """
        check_count = min(sample_pages, len(doc))
        text_count = 0
        for i in range(check_count):
            txt = doc[i].get_text().strip()
            if len(txt) > 60:
                text_count += 1
        # If less than 20% of sample pages contain digital text, it's scanned
        return (text_count / max(1, check_count)) < 0.2

    @staticmethod
    def extract_textbook_metadata(doc: pymupdf.Document, file_path: str) -> Tuple[str, str]:
        """Infers book title and author from metadata or filename."""
        raw_name = os.path.splitext(os.path.basename(file_path))[0]
        clean_name = re.sub(r'^[0-9a-f]{8}_', '', raw_name).strip()
        clean_name = unicodedata.normalize('NFC', clean_name)

        meta = doc.metadata or {}
        title = meta.get("title", "").strip() if meta.get("title") else ""
        author = meta.get("author", "").strip() if meta.get("author") else ""

        if not title:
            # Check for common textbook title patterns in filename
            clean_title = clean_name
            # e.g. "GIÁO TRÌNH CHỦ NGHĨA XÃ HỘI KHOA HỌC (K-2021)" -> "Giáo trình Chủ nghĩa xã hội khoa học"
            m = re.match(r'^(GI[AÁ]O\s+TR[IÌ]NH\s+[^(\n]+)', clean_name, re.IGNORECASE)
            if m:
                clean_title = m.group(1).strip()
            title = clean_title.title() if clean_title.isupper() else clean_title

        if not author:
            if "chu nghia xa hoi" in title.lower() or "triet hoc" in title.lower() or "giao trinh" in title.lower():
                author = "Bộ Giáo dục và Đào tạo"
            else:
                author = "Nhiều tác giả"

        return title, author

    @classmethod
    def ocr_page_gemini(
        cls,
        image_bytes: bytes,
        api_keys: List[str],
        page_num: int,
        total_pages: int,
        model: str = "gemini-3.5-flash-lite"
    ) -> str:
        """
        Calls Gemini Multimodal Vision API to perform high-precision Vietnamese OCR
        with markdown hierarchy formatting and header/footer stripping.
        Rotates through api_keys pool if any key encounters 429 rate limits.
        """
        if not api_keys:
            return ""

        img_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "Bạn là chuyên gia số hóa sách giáo trình đại học Việt Nam chuyên nghiệp.\n"
            "Nhiệm vụ: Hãy đọc và trích xuất nguyên văn toàn bộ chữ tiếng Việt trong bức ảnh trang sách này.\n\n"
            "YÊU CẦU QUAN TRỌNG VỀ ĐỊNH DẠNG:\n"
            "1. KHÔNG thêm bất kỳ lời dẫn, lời chào hay bình luận nào. Chỉ trả về nội dung của trang sách.\n"
            "2. Loại bỏ hoàn toàn dòng tiêu đề đầu trang lặp lại (running header như 'BỘ GIÁO DỤC VÀ ĐÀO TẠO', 'GIÁO TRÌNH...', tên chương ở đầu trang) và số trang ở chân trang.\n"
            "3. Sử dụng Markdown để đánh dấu đúng phân cấp tiêu đề:\n"
            "   - Tiêu đề Chương hoặc phần mở đầu: dùng '# Chương [X]: [Tên chương]' hoặc '# Lời Nhà xuất bản', '# Tài liệu tham khảo'\n"
            "   - Mục lớn (A. Mục tiêu, B. Nội dung, C. Câu hỏi ôn tập): dùng '## [Tiêu đề]'\n"
            "   - Đề mục La Mã (I-, II-, III- hoặc I., II.): dùng '### [Tiêu đề]'\n"
            "   - Tiểu mục chữ số (1., 2., 3.): dùng '#### [Tiêu đề]'\n"
            "   - Mục con (a), b), c)): dùng '##### [Tiêu đề]'\n"
            "4. Các đoạn trích dẫn tác phẩm kinh điển của Mác, Ăngghen, Lênin, Hồ Chí Minh: dùng cú pháp trích dẫn '> [nội dung trích dẫn]'.\n"
            "5. Đảm bảo chính xác từng dấu thanh tiếng Việt (sắc, huyền, hỏi, ngã, nặng), không tự ý sửa đổi từ ngữ."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1
            }
        }

        fallback_models = [model, "gemini-flash-latest"] if model != "gemini-flash-latest" else [model]

        # Try across keys and models with intelligent backoff
        for cur_model in fallback_models:
            for attempt in range(len(api_keys) * 2):
                key = api_keys[attempt % len(api_keys)]
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{cur_model}:generateContent?key={key}"
                try:
                    resp = requests.post(url, json=payload, timeout=(10, 35))
                    if resp.status_code == 200:
                        res_json = resp.json()
                        parts = res_json.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                        if parts:
                            return parts[0].get('text', '').strip()
                    elif resp.status_code == 429:
                        time.sleep(1.0 + (attempt * 0.3))
                    else:
                        time.sleep(0.5)
                except Exception:
                    time.sleep(1.0)

        return ""

    @classmethod
    def ocr_scanned_pdf(
        cls,
        doc: pymupdf.Document,
        project_id: str,
        api_keys: List[str],
        data_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_workers: int = 4,
        start_page: int = 1,
        end_page: Optional[int] = None
    ) -> List[Tuple[int, str]]:
        """
        Executes parallel OCR across pages using a pool of Gemini API keys.
        Caches page results to disk so the process is completely fault-tolerant and resumable.
        """
        cache_dir = os.path.join(data_dir, "projects", project_id, "ocr_cache")
        os.makedirs(cache_dir, exist_ok=True)

        total_pages = len(doc)
        last_p = min(end_page or total_pages, total_pages)
        first_p = max(1, start_page)
        pages_to_do = list(range(first_p, last_p + 1))

        # Check existing cache
        cached_results: Dict[int, str] = {}
        for p_idx in pages_to_do:
            c_path = os.path.join(cache_dir, f"page_{p_idx:04d}.json")
            if os.path.exists(c_path):
                try:
                    with open(c_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        txt = data.get("text", "").strip()
                        if txt:
                            cached_results[p_idx] = txt
                except Exception:
                    pass

        completed_count = len(cached_results)
        missing_pages = [p for p in pages_to_do if p not in cached_results]

        if progress_callback:
            progress_callback(completed_count, len(pages_to_do), f"Đã nạp {completed_count}/{len(pages_to_do)} trang từ bộ nhớ đệm.")

        if not missing_pages:
            return [(p, cached_results[p]) for p in pages_to_do]

        def process_page(p_idx: int) -> Tuple[int, str]:
            page = doc[p_idx - 1]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")

            text = cls.ocr_page_gemini(
                image_bytes=img_bytes,
                api_keys=api_keys,
                page_num=p_idx,
                total_pages=total_pages
            )

            if text and text.strip():
                c_path = os.path.join(cache_dir, f"page_{p_idx:04d}.json")
                try:
                    with open(c_path, "w", encoding="utf-8") as f:
                        json.dump({"page": p_idx, "text": text.strip()}, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            return p_idx, text

        # While loop to ensure 100% completion with pacing
        while missing_pages:
            num_threads = min(max_workers, len(missing_pages))
            batch = missing_pages[:num_threads * 4]  # Process in steady batches

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                future_to_page = {}
                for p in batch:
                    future_to_page[executor.submit(process_page, p)] = p
                    time.sleep(0.35)  # Pace requests smoothly (avoids 15 RPM spike)

                for future in concurrent.futures.as_completed(future_to_page):
                    p_idx = future_to_page[future]
                    try:
                        p_num, text = future.result()
                        if text and text.strip():
                            cached_results[p_num] = text
                            completed_count += 1
                            if progress_callback:
                                progress_callback(completed_count, len(pages_to_do), f"Đã quét OCR trang {completed_count}/{len(pages_to_do)}.")
                    except Exception:
                        pass

            missing_pages = [p for p in pages_to_do if p not in cached_results]
            if missing_pages:
                time.sleep(3.0)  # Rest before retrying any stubborn pages

        return [(p, cached_results.get(p, "")) for p in pages_to_do]

    @classmethod
    def structure_textbook(
        cls,
        pages_content: List[Tuple[int, str]],
        project_id: str,
        title: str,
        author: str,
        source_path: str
    ) -> BookProject:
        """
        Assembles page texts into a structured BookProject with well-defined chapters,
        sections, and clean paragraphs.
        """
        chapters: List[BookChapter] = []
        current_chap_title = "Lời mở đầu"
        current_paras: List[BookParagraph] = []
        chap_idx = 0
        p_global_idx = 0

        def flush_chap(new_title: str):
            nonlocal current_paras, current_chap_title, chap_idx, chapters
            if current_paras:
                chap_id = f"chap_{chap_idx}"
                chapters.append(BookChapter(
                    id=chap_id,
                    title=unicodedata.normalize('NFC', current_chap_title).strip(),
                    paragraphs=current_paras,
                    doc_name=f"{chap_id}.xhtml",
                    order=chap_idx
                ))
                chap_idx += 1
                current_paras = []
            current_chap_title = new_title

        # Combine all text with page tracking
        raw_blocks: List[str] = []
        for p_num, text in pages_content:
            if not text or not text.strip():
                continue
            # Split by markdown headers or double newlines
            lines = text.strip().split('\n')
            raw_blocks.extend(lines)

        # Regex for chapter boundaries
        CHAP_HEADER_PAT = re.compile(
            r'^(?:#\s+)?(Chương\s+[0-9IVXLCDMivxlcdm]+[:\.\-–\s]*.*|Lời\s+(?:Nhà\s+xuất\s+bản|nói\s+đầu|mở\s+đầu)|Tài\s+liệu\s+tham\s+khảo|Kết\s+luận)$',
            re.IGNORECASE
        )
        MAJOR_SEC_PAT = re.compile(r'^(?:##\s+)?([A-C]\.\s+.*)$', re.IGNORECASE)
        ROMAN_SEC_PAT = re.compile(r'^(?:###\s+)?([IVXLCDM]+[\.\-–\s]+.*)$', re.IGNORECASE)
        SUB_SEC_PAT = re.compile(r'^(?:####\s+)?(\d+\.\s+.*)$')

        pending_text_lines: List[str] = []

        def flush_paragraph(tag: str = "p", custom_text: Optional[str] = None):
            nonlocal pending_text_lines, current_paras, p_global_idx
            text = custom_text
            if text is None:
                if not pending_text_lines:
                    return
                # Join lines and fix hyphenation
                text = ""
                for l in pending_text_lines:
                    l = l.strip()
                    if not l:
                        continue
                    if text.endswith('-'):
                        # Vietnamese hyphenation fix
                        text = text[:-1] + l
                    else:
                        text = (text + " " + l).strip() if text else l
                pending_text_lines = []

            text = unicodedata.normalize('NFC', text.strip())
            if len(text) >= 2:
                # Remove stray markdown symbols for body
                clean_display = re.sub(r'^#{1,6}\s+', '', text).strip()
                p_id = f"c{chap_idx}_p{len(current_paras) + 1}"
                p_global_idx += 1
                current_paras.append(BookParagraph(
                    id=p_id,
                    original_text=clean_display,
                    translated_text=clean_display,  # Already in Vietnamese!
                    status="done",
                    tag=tag,
                    index=p_global_idx
                ))

        # Merge consecutive chapter number + title lines: e.g. "Chương 1" followed by "NHẬP MÔN..."
        idx = 0
        while idx < len(raw_blocks):
            line = raw_blocks[idx].strip()
            if not line:
                flush_paragraph("p")
                idx += 1
                continue

            # Check if this line is a standalone "Chương [X]"
            m_standalone_chap = re.match(r'^(?:#\s*)?(Chương\s+[0-9IVXLCDMivxlcdm]+)\s*$', line, re.IGNORECASE)
            if m_standalone_chap and idx + 1 < len(raw_blocks):
                next_line = raw_blocks[idx + 1].strip()
                if next_line and not next_line.startswith(('#', 'A.', 'B.', 'C.', 'I-', 'II-')):
                    line = f"{m_standalone_chap.group(1)}: {next_line}"
                    idx += 1  # Skip the next line as it's merged into chapter title

            # Check if this line is a Chapter title
            m_chap = CHAP_HEADER_PAT.match(line)
            if m_chap:
                flush_paragraph("p")
                clean_chap_title = re.sub(r'^#+\s*', '', m_chap.group(1)).strip()
                flush_chap(clean_chap_title)
                idx += 1
                continue

            # Check Major section (A. Mục tiêu, B. Nội dung, C. Câu hỏi ôn tập)
            m_major = MAJOR_SEC_PAT.match(line)
            if m_major:
                flush_paragraph("p")
                clean_major = re.sub(r'^#+\s*', '', m_major.group(1)).strip()
                flush_paragraph("h2", clean_major)
                idx += 1
                continue

            # Check Roman section (I-, II-, III-)
            m_roman = ROMAN_SEC_PAT.match(line)
            if m_roman:
                flush_paragraph("p")
                clean_roman = re.sub(r'^#+\s*', '', m_roman.group(1)).strip()
                flush_paragraph("h3", clean_roman)
                idx += 1
                continue

            # Check sub-section (1., 2., 3.)
            m_sub = SUB_SEC_PAT.match(line)
            if m_sub:
                flush_paragraph("p")
                clean_sub = re.sub(r'^#+\s*', '', m_sub.group(1)).strip()
                flush_paragraph("h4", clean_sub)
                idx += 1
                continue

            # Check quote block (> ...)
            if line.startswith('>'):
                flush_paragraph("p")
                quote_content = line.lstrip('> ').strip()
                flush_paragraph("blockquote", quote_content)
                idx += 1
                continue

            # Regular paragraph lines
            pending_text_lines.append(line)
            idx += 1

        # Flush final remaining content
        flush_paragraph("p")
        flush_chap("End")

        return BookProject(
            id=project_id,
            title=title,
            author=author,
            source_format="pdf",
            source_file_path=source_path,
            chapters=chapters
        )

    @classmethod
    def convert_pdf_to_epub(
        cls,
        file_path: str,
        output_epub_path: str,
        data_dir: str,
        api_keys: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_workers: int = 6,
        start_page: int = 1,
        end_page: Optional[int] = None,
        project_id: Optional[str] = None
    ) -> Tuple[BookProject, str]:
        """
        Full end-to-end converter from textbook PDF to publication-ready EPUB.
        """
        from core.exporter import BookExporter
        from core.glossary import BookGlossary

        doc = pymupdf.open(file_path)
        pid = project_id or str(uuid.uuid4())[:8]
        title, author = cls.extract_textbook_metadata(doc, file_path)

        is_scanned = cls.is_scanned_pdf(doc)

        if is_scanned:
            if progress_callback:
                progress_callback(0, len(doc), f"Phát hiện bản scan ({len(doc)} trang). Bắt đầu quét OCR AI...")
            pages_content = cls.ocr_scanned_pdf(
                doc=doc,
                project_id=pid,
                api_keys=api_keys,
                data_dir=data_dir,
                progress_callback=progress_callback,
                max_workers=max_workers,
                start_page=start_page,
                end_page=end_page
            )
        else:
            if progress_callback:
                progress_callback(0, len(doc), "Đang bóc tách văn bản số từ PDF...")
            pages_content = []
            for i in range(len(doc)):
                txt = doc[i].get_text()
                pages_content.append((i + 1, txt))
                if progress_callback and i % 20 == 0:
                    progress_callback(i + 1, len(doc), f"Đang xử lý trang {i + 1}/{len(doc)}")

        # Structure into BookProject
        if progress_callback:
            progress_callback(len(pages_content), len(pages_content), "Đang phân tích cấu trúc chương mục...")

        project = cls.structure_textbook(
            pages_content=pages_content,
            project_id=pid,
            title=title,
            author=author,
            source_path=file_path
        )
        # Mark project as textbook via the explicit document_type field
        project.document_type = "textbook"

        # Save project to data/projects/{pid}
        from server.database import ProjectManager
        ProjectManager.save_new_project(project, BookGlossary())

        # Generate EPUB
        if progress_callback:
            progress_callback(len(pages_content), len(pages_content), "Đang tạo và đóng gói file EPUB...")

        os.makedirs(os.path.dirname(os.path.abspath(output_epub_path)), exist_ok=True)
        BookExporter.export_epub(project, output_epub_path, bilingual=False)

        if progress_callback:
            progress_callback(len(pages_content), len(pages_content), f"Hoàn tất xuất file EPUB: {os.path.basename(output_epub_path)}")

        return project, output_epub_path
