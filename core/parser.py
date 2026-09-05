"""
Multi-format Book Parser (EPUB, PDF, DOCX, TXT, Markdown).
Extracts structured chapters, paragraphs, headings, and metadata while preserving formatting cues.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple
import os
import re
import uuid
from bs4 import BeautifulSoup, NavigableString, Tag
import ebooklib
from ebooklib import epub
import pypdf
import docx


@dataclass
class BookParagraph:
    id: str
    original_text: str
    translated_text: str = ""
    status: str = "pending"  # pending, translating, done, edited, error
    tag: str = "p"           # p, h1, h2, h3, blockquote, li, etc.
    index: int = 0
    css_class: str = ""
    notes: str = ""


@dataclass
class BookChapter:
    id: str
    title: str
    paragraphs: List[BookParagraph] = field(default_factory=list)
    doc_name: str = ""       # e.g., 'chapter1.xhtml' inside EPUB
    order: int = 0
    raw_html: str = ""

    @property
    def total_paragraphs(self) -> int:
        return len(self.paragraphs)

    @property
    def translated_paragraphs(self) -> int:
        return sum(1 for p in self.paragraphs if p.status in ("done", "edited"))

    @property
    def progress_percent(self) -> float:
        if not self.paragraphs:
            return 100.0
        return round((self.translated_paragraphs / len(self.paragraphs)) * 100, 1)

    @property
    def word_count(self) -> int:
        return sum(len(p.original_text.split()) for p in self.paragraphs)


@dataclass
class BookProject:
    id: str
    title: str
    author: str = "Unknown"
    source_format: str = "epub"
    source_file_path: str = ""
    cover_image_path: str = ""
    chapters: List[BookChapter] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)

    @property
    def total_paragraphs(self) -> int:
        return sum(c.total_paragraphs for c in self.chapters)

    @property
    def translated_paragraphs(self) -> int:
        return sum(c.translated_paragraphs for c in self.chapters)

    @property
    def total_words(self) -> int:
        return sum(c.word_count for c in self.chapters)

    @property
    def progress_percent(self) -> float:
        total = self.total_paragraphs
        if total == 0:
            return 0.0
        return round((self.translated_paragraphs / total) * 100, 1)


class BookParser:
    """Detects format and parses book files into structured chapters and paragraphs."""

    @staticmethod
    def parse_file(file_path: str, project_id: Optional[str] = None) -> BookProject:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        pid = project_id or str(uuid.uuid4())[:8]

        if ext == ".epub":
            return BookParser.parse_epub(file_path, pid)
        elif ext == ".pdf":
            return BookParser.parse_pdf(file_path, pid)
        elif ext in (".docx", ".doc"):
            return BookParser.parse_docx(file_path, pid)
        elif ext in (".txt", ".md"):
            return BookParser.parse_text(file_path, pid)
        else:
            raise ValueError(f"Định dạng file không được hỗ trợ: {ext}. Hãy tải lên file EPUB, PDF, DOCX, TXT.")

    @staticmethod
    def parse_epub(file_path: str, project_id: str) -> BookProject:
        book = epub.read_epub(file_path)

        # Extract title & author
        title_meta = book.get_metadata('DC', 'title')
        title = title_meta[0][0] if title_meta else os.path.splitext(os.path.basename(file_path))[0]
        creator_meta = book.get_metadata('DC', 'creator')
        author = creator_meta[0][0] if creator_meta else "Tác giả không rõ"

        # 1. Build Table of Contents (TOC) Map: {doc_name: chapter_title}
        toc_map: Dict[str, str] = {}

        def extract_toc(toc_list):
            for item in toc_list:
                if isinstance(item, tuple):
                    if hasattr(item[0], 'href') and hasattr(item[0], 'title'):
                        href = item[0].href.split('#')[0]
                        toc_map[href] = item[0].title.strip()
                    if len(item) > 1 and isinstance(item[1], (list, tuple)):
                        extract_toc(item[1])
                elif hasattr(item, 'href') and hasattr(item, 'title'):
                    href = item.href.split('#')[0]
                    toc_map[href] = item.title.strip()

        if hasattr(book, 'toc') and book.toc:
            extract_toc(book.toc)

        # Look for cover image
        cover_path = ""
        cache_dir = os.path.join(os.path.dirname(file_path), ".covers")
        os.makedirs(cache_dir, exist_ok=True)
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            name_lower = item.get_name().lower()
            if "cover" in name_lower or "front" in name_lower:
                cover_dest = os.path.join(cache_dir, f"{project_id}_cover.jpg")
                with open(cover_dest, "wb") as cf:
                    cf.write(item.get_content())
                cover_path = cover_dest
                break

        chapters: List[BookChapter] = []
        doc_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

        chap_idx = 0
        p_global_idx = 0

        for doc in doc_items:
            doc_name = doc.get_name()
            content_bytes = doc.get_content()
            try:
                html_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                html_str = content_bytes.decode('latin-1', errors='ignore')

            soup = BeautifulSoup(html_str, 'html.parser')

            # Extract paragraphs and headings, including <div> blocks used in Calibre books
            raw_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'li', 'div'])
            filtered_elements = []
            for el in raw_elements:
                # If it's a div, skip container divs that contain child paragraphs or child divs
                if el.name == 'div' and el.find(['p', 'div', 'blockquote']):
                    continue
                filtered_elements.append(el)

            chapter_paras: List[BookParagraph] = []
            in_doc_title = ""

            for t in filtered_elements:
                text = t.get_text(strip=True)
                # Clean stray replacement / diamond characters
                text = text.replace('\ufffd', '').strip()

                # Ignore empty elements, trivial single characters or pure ornament dots
                if not text or len(text) < 2 or text in ('* * *', '***', '• • •', '---'):
                    continue

                if t.name in ['h1', 'h2', 'h3'] and not in_doc_title:
                    in_doc_title = text

                p_global_idx += 1
                css_cls = " ".join(t.get('class', [])) if t.has_attr('class') else ""
                tag_name = t.name if t.name in ['h1', 'h2', 'h3', 'blockquote'] else 'p'
                chapter_paras.append(BookParagraph(
                    id=f"c{chap_idx}_p{p_global_idx}",
                    original_text=text,
                    tag=tag_name,
                    index=p_global_idx,
                    css_class=css_cls
                ))

            # Only add as a chapter if there is text
            if chapter_paras:
                # Determine best chapter title:
                # Priority 1: From authoritative EPUB Table of Contents (TOC)
                matched_toc = toc_map.get(doc_name) or toc_map.get(os.path.basename(doc_name))
                if matched_toc:
                    chap_title = matched_toc
                elif in_doc_title:
                    chap_title = in_doc_title
                else:
                    # Look at first paragraph: if it starts with "Chapter", "Prologue", etc.
                    first_text = chapter_paras[0].original_text
                    if re.match(r'^(?:chapter|part|prologue|epilogue|chương|hồi)\b', first_text, re.IGNORECASE) and len(first_text) < 100:
                        chap_title = first_text
                    elif len(first_text) <= 50:
                        chap_title = first_text
                    else:
                        chap_title = f"Phần {chap_idx + 1}: " + (first_text[:50] + "...")

                chapters.append(BookChapter(
                    id=f"chap_{chap_idx}",
                    title=chap_title,
                    paragraphs=chapter_paras,
                    doc_name=doc_name,
                    order=chap_idx,
                    raw_html=html_str
                ))
                chap_idx += 1

        return BookProject(
            id=project_id,
            title=title,
            author=author,
            source_format="epub",
            source_file_path=file_path,
            cover_image_path=cover_path,
            chapters=chapters
        )


    @staticmethod
    def parse_pdf(file_path: str, project_id: str) -> BookProject:
        reader = pypdf.PdfReader(file_path)
        meta = reader.metadata
        title = meta.title if (meta and meta.title) else os.path.splitext(os.path.basename(file_path))[0]
        author = meta.author if (meta and meta.author) else "Tác giả không rõ"

        chapters: List[BookChapter] = []
        p_global_idx = 0
        chap_idx = 0

        # Group pages into chapters: Look for "Chapter X" or group every ~10-15 pages
        current_paras: List[BookParagraph] = []
        current_title = f"Phần mở đầu / Chương 1"

        chapter_header_pattern = re.compile(
            r'^(?:chapter|part|section|chương|hồi|mục)\s+([0-9ivxlc]+|[a-z]+)[:\s\.\-]*(.*)$',
            re.IGNORECASE
        )

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue

            # Clean hyphenation (e.g. 'un- \n believable' -> 'unbelievable')
            cleaned_text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', page_text)

            # Split paragraphs by double newline or significant line breaks
            raw_blocks = re.split(r'\n\s*\n', cleaned_text)

            for block in raw_blocks:
                # Merge internal single linebreaks within a paragraph
                lines = [l.strip() for l in block.splitlines() if l.strip()]
                if not lines:
                    continue
                para_text = " ".join(lines)
                if len(para_text) < 3:
                    continue

                # Check if this paragraph is a chapter heading
                match = chapter_header_pattern.match(para_text)
                if match and len(para_text) < 120 and current_paras:
                    # Flush previous chapter
                    chapters.append(BookChapter(
                        id=f"chap_{chap_idx}",
                        title=current_title,
                        paragraphs=current_paras,
                        doc_name=f"Page_{page_num}",
                        order=chap_idx
                    ))
                    chap_idx += 1
                    current_paras = []
                    current_title = para_text

                p_global_idx += 1
                tag = "h2" if match or (len(para_text) < 60 and para_text.isupper()) else "p"
                current_paras.append(BookParagraph(
                    id=f"c{chap_idx}_p{p_global_idx}",
                    original_text=para_text,
                    tag=tag,
                    index=p_global_idx
                ))

        if current_paras:
            chapters.append(BookChapter(
                id=f"chap_{chap_idx}",
                title=current_title,
                paragraphs=current_paras,
                doc_name="End",
                order=chap_idx
            ))

        return BookProject(
            id=project_id,
            title=title,
            author=author,
            source_format="pdf",
            source_file_path=file_path,
            chapters=chapters
        )

    @staticmethod
    def parse_docx(file_path: str, project_id: str) -> BookProject:
        doc = docx.Document(file_path)
        title = os.path.splitext(os.path.basename(file_path))[0]
        author = "Tác giả không rõ"

        chapters: List[BookChapter] = []
        current_paras: List[BookParagraph] = []
        current_title = "Chương 1"
        chap_idx = 0
        p_global_idx = 0

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower() if p.style else ""
            is_heading = "heading 1" in style_name or "title" in style_name or re.match(r'^(?:chapter|chương)\s+\d+', text, re.I)

            if is_heading and current_paras:
                chapters.append(BookChapter(
                    id=f"chap_{chap_idx}",
                    title=current_title,
                    paragraphs=current_paras,
                    order=chap_idx
                ))
                chap_idx += 1
                current_paras = []
                current_title = text

            p_global_idx += 1
            tag = "h1" if is_heading else ("h2" if "heading" in style_name else "p")
            current_paras.append(BookParagraph(
                id=f"c{chap_idx}_p{p_global_idx}",
                original_text=text,
                tag=tag,
                index=p_global_idx
            ))

        if current_paras:
            chapters.append(BookChapter(
                id=f"chap_{chap_idx}",
                title=current_title,
                paragraphs=current_paras,
                order=chap_idx
            ))

        return BookProject(
            id=project_id,
            title=title,
            author=author,
            source_format="docx",
            source_file_path=file_path,
            chapters=chapters
        )

    @staticmethod
    def parse_text(file_path: str, project_id: str) -> BookProject:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            full_text = f.read()

        title = os.path.splitext(os.path.basename(file_path))[0]
        author = "Tác giả không rõ"

        chapter_header_pattern = re.compile(
            r'^(?:#+\s*|CHAPTER\s+|CHƯƠNG\s+|Part\s+)([0-9ivxlc]+|[a-z]+)[:\s\.\-]*(.*)$',
            re.IGNORECASE | re.MULTILINE
        )

        lines = full_text.splitlines()
        chapters: List[BookChapter] = []
        current_paras: List[BookParagraph] = []
        current_title = "Phần 1"
        chap_idx = 0
        p_global_idx = 0

        # Buffer for continuous paragraph lines
        buf = []

        def flush_buffer(target_tag="p"):
            nonlocal p_global_idx, buf
            if buf:
                p_text = " ".join(buf).strip()
                if p_text:
                    p_global_idx += 1
                    current_paras.append(BookParagraph(
                        id=f"c{chap_idx}_p{p_global_idx}",
                        original_text=p_text,
                        tag=target_tag,
                        index=p_global_idx
                    ))
                buf = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                flush_buffer()
                continue

            match = chapter_header_pattern.match(line_str)
            if match and len(line_str) < 100:
                flush_buffer()
                if current_paras:
                    chapters.append(BookChapter(
                        id=f"chap_{chap_idx}",
                        title=current_title,
                        paragraphs=current_paras,
                        order=chap_idx
                    ))
                    chap_idx += 1
                    current_paras = []
                current_title = line_str.lstrip('#').strip()
                p_global_idx += 1
                current_paras.append(BookParagraph(
                    id=f"c{chap_idx}_p{p_global_idx}",
                    original_text=current_title,
                    tag="h1",
                    index=p_global_idx
                ))
            else:
                buf.append(line_str)

        flush_buffer()
        if current_paras:
            chapters.append(BookChapter(
                id=f"chap_{chap_idx}",
                title=current_title,
                paragraphs=current_paras,
                order=chap_idx
            ))

        return BookProject(
            id=project_id,
            title=title,
            author=author,
            source_format="txt",
            source_file_path=file_path,
            chapters=chapters
        )
