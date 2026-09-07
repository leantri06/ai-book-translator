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
try:
    import pymupdf
except ImportError:
    pymupdf = None
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
    image_path: str = ""


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
        """Parses PDF into structured chapters, extracting high-res figures and tables."""
        if pymupdf is not None:
            try:
                return BookParser._parse_pdf_mupdf(file_path, project_id)
            except Exception as e:
                import traceback
                print(f"[PDF Parser] PyMuPDF parsing failed: {e}. Falling back to pypdf.")
        return BookParser._parse_pdf_pypdf(file_path, project_id)

    @staticmethod
    def _extract_pdf_title_and_author(doc, file_path: str) -> Tuple[str, str]:
        raw_name = os.path.splitext(os.path.basename(file_path))[0]
        clean_name = re.sub(r'^[0-9a-f]{8}_', '', raw_name)
        clean_name = clean_name.replace('_', ' ').strip()
        if len(doc) == 0:
            return clean_name, "Tác giả không rõ"

        meta = doc.metadata or {}
        meta_title = (meta.get("title") or "").strip()
        meta_author = (meta.get("author") or "").strip()

        invalid_titles = {'untitled', 'latex', 'tex', 'document', 'manuscript', 'draft', 'none', 'arxiv', 'unknown', 'default'}
        title = meta_title if (meta_title and not any(inv in meta_title.lower() for inv in invalid_titles) and len(meta_title) > 4) else ''
        invalid_authors = {'unknown', 'author', 'tex', 'latex', 'none', 'anonymous', 'user', 'admin'}
        author = meta_author if (meta_author and not any(inv in meta_author.lower() for inv in invalid_authors) and len(meta_author) > 2) else ''

        page = doc[0]
        pw, ph = page.rect.width, page.rect.height
        d = page.get_text("dict")
        spans = []
        for b in d.get("blocks", []):
            if b.get("type") != 0:
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    txt = s.get("text", "").strip()
                    if not txt:
                        continue
                    bbox = s.get("bbox", (0, 0, 0, 0))
                    # Skip margin stamps / watermarks
                    if bbox[0] < 35 and bbox[1] > ph * 0.25:
                        continue
                    if bbox[1] < 30 or bbox[3] > ph - 30:
                        continue
                    if "arxiv:" in txt.lower():
                        continue
                    spans.append({
                        "text": txt,
                        "size": round(s.get("size", 10.0), 1),
                        "flags": s.get("flags", 0),
                        "font": s.get("font", ""),
                        "bbox": bbox,
                        "y0": bbox[1],
                        "y1": bbox[3],
                        "x0": bbox[0],
                        "x1": bbox[2]
                    })

        # 1. EXTRACT TITLE
        top_spans = [s for s in spans if s["y0"] < ph * 0.40]
        if top_spans:
            valid_top_spans = [
                s for s in top_spans
                if not any(w in s["text"].lower() for w in ('permission', 'attribution', 'copyright', 'license', 'journalistic', 'reproduce the tables'))
            ]
            if valid_top_spans:
                max_size = max(s["size"] for s in valid_top_spans)
                title_spans = [s for s in valid_top_spans if s["size"] >= max_size - 1.5 and len(s["text"]) > 1]
                title_spans.sort(key=lambda s: (round(s["y0"] / 6) * 6, s["x0"]))
                extracted_title = " ".join(s["text"] for s in title_spans).strip()
                extracted_title = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', extracted_title)
                extracted_title = re.sub(r'\s+', ' ', extracted_title).strip()
                if len(extracted_title) >= 4:
                    title = extracted_title

        # 2. EXTRACT AUTHORS
        if not author:
            title_bottom = 0
            if title and top_spans:
                for s in top_spans:
                    if s["text"] in title:
                        title_bottom = max(title_bottom, s["y1"])

            abstract_top = ph * 0.75
            for s in spans:
                if re.match(r'^(abstract|tóm tắt)\b', s["text"], re.IGNORECASE):
                    abstract_top = min(abstract_top, s["y0"])
                    break

            if title_bottom > 0 and title_bottom < abstract_top:
                AFFIL_KEYWORDS = {
                    'university', 'institute', 'department', 'research', 'laborator', 'college',
                    'school', 'center', 'centre', 'campus', 'brain', 'technolog', 'corporation',
                    'inc.', 'ltd', 'dept', 'faculty', 'academy', 'group', 'team', 'sciences',
                    'mary', 'williamsburg', 'virginia', 'google', 'toronto'
                }
                LOCATION_KEYWORDS = {
                    'usa', 'vietnam', 'china', 'france', 'germany', 'japan', 'canada',
                    'united states', 'london', 'paris', 'california', 'new york', 'massachusetts',
                    'rio de janeiro', 'brazil', 'beijing', 'tokyo', 'singapore', 'korea', 'australia'
                }

                authors_found = []
                seen_names = set()

                for b in d.get("blocks", []):
                    if b.get("type") != 0:
                        continue
                    by0, by1 = b["bbox"][1], b["bbox"][3]
                    if by1 < title_bottom - 5 or by0 > abstract_top + 5:
                        continue
                    if b["bbox"][0] < 35:
                        continue

                    cur_name_parts = []
                    cur_font_size = None

                    for l in b.get("lines", []):
                        line_text = " ".join(s.get("text", "") for s in l.get("spans", [])).strip()
                        if not line_text:
                            continue
                        f_size = round(l["spans"][0].get("size", 10.0), 1)

                        cleaned_line = re.sub(r'[\*†‡§0-9#\(\)]+', '', line_text).strip()
                        lower_l = cleaned_line.lower()

                        if "@" in lower_l or "http" in lower_l or any(w in lower_l for w in AFFIL_KEYWORDS) or any(w in lower_l for w in LOCATION_KEYWORDS):
                            if cur_name_parts:
                                full_n = " ".join(cur_name_parts).strip()
                                for p in re.split(r'[,;]|\sand\s', full_n):
                                    name = re.sub(r'[\*\u2217†‡§0-9#\(\)]+', '', p).strip()
                                    words = name.split()
                                    if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if len(w) > 1):
                                        if name not in seen_names and not any(w in name.lower() for w in AFFIL_KEYWORDS):
                                            seen_names.add(name)
                                            authors_found.append(name)
                                cur_name_parts = []
                                cur_font_size = None
                            continue

                        if cur_font_size is not None and f_size < cur_font_size - 1.0:
                            break

                        cur_font_size = f_size
                        cur_name_parts.append(cleaned_line)

                    if cur_name_parts:
                        full_n = " ".join(cur_name_parts).strip()
                        for p in re.split(r'[,;]|\sand\s', full_n):
                            name = re.sub(r'[\*\u2217†‡§0-9#\(\)]+', '', p).strip()
                            words = name.split()
                            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if len(w) > 1):
                                if name not in seen_names and not any(w in name.lower() for w in AFFIL_KEYWORDS):
                                    seen_names.add(name)
                                    authors_found.append(name)

                if authors_found:
                    if len(authors_found) > 6:
                        author = ", ".join(authors_found[:5]) + f", và {len(authors_found)-5} tác giả khác"
                    else:
                        author = ", ".join(authors_found)

        if not title:
            title = clean_name
        if not author:
            author = "Tác giả không rõ"

        return title, author

    @staticmethod
    def _parse_pdf_mupdf(file_path: str, project_id: str) -> BookProject:
        doc = pymupdf.open(file_path)
        title, author = BookParser._extract_pdf_title_and_author(doc, file_path)

        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        img_dir = os.path.join(data_dir, "projects", project_id, "images")
        os.makedirs(img_dir, exist_ok=True)

        MAJOR_HEADING_PATTERN = re.compile(
            r'^(?:'
            r'(\d{1,2}\.?\s+[A-Z][\w\s\-/,\(\)]{2,})'
            r'|'
            r'(Abstract|Conclusion|Conclusions|References|Bibliography|Acknowledgements|Appendix(?:\s+[A-Z0-9]+)?)'
            r'|'
            r'((?:Chapter|Chương|Part|Phần|Section|Hồi|Mục)\s+([0-9ivxlc]+|[a-z]+)[:\s\.\-]*(.*))'
            r')$',
            re.IGNORECASE
        )
        SUB_HEADING_PATTERN = re.compile(
            r'^(?:\d+\.)+\d+\s+([A-Z][\w\s\-/,\(\)]{2,})$'
        )
        FIG_CAPTION_PATTERN = re.compile(
            r'^(?:Figure|Fig\.?)\s*([\d\.\-]+)[:\.]?\s*(.*)',
            re.IGNORECASE
        )
        TAB_CAPTION_PATTERN = re.compile(
            r'^(?:Table|Bảng)\s*([\d\.\-]+)[:\.]?\s*(.*)',
            re.IGNORECASE
        )

        chapters: List[BookChapter] = []
        p_global_idx = 0
        chap_idx = 0
        current_paras: List[BookParagraph] = []
        current_title = "Phần mở đầu / Tiêu đề"
        current_lines: List[str] = []

        def flush_para(tag: str = "p"):
            nonlocal current_lines, current_paras, p_global_idx
            if not current_lines:
                return
            text = ""
            for l in current_lines:
                l = l.strip()
                if not l:
                    continue
                if text.endswith("-"):
                    text = text[:-1] + l
                else:
                    text = (text + " " + l).strip() if text else l
            current_lines = []
            if len(text) >= 2:
                if chap_idx == 0 and any(p in text.lower() for p in (
                    "proper attribution is provided",
                    "permission to make digital or hard copies",
                    "reproduce the tables and figures in this paper solely for use in journalistic",
                    "this work is licensed under a creative commons",
                    "copyright held by the owner/author",
                )):
                    return
                p_global_idx += 1
                current_paras.append(BookParagraph(
                    id=f"c{chap_idx}_p{p_global_idx}",
                    original_text=text,
                    tag=tag,
                    index=p_global_idx
                ))

        def flush_chapter(next_title: str):
            nonlocal current_paras, chapters, current_title, chap_idx
            flush_para()
            if current_paras:
                chapters.append(BookChapter(
                    id=f"chap_{chap_idx}",
                    title=current_title,
                    paragraphs=current_paras,
                    doc_name=f"Section_{chap_idx}",
                    order=chap_idx
                ))
                chap_idx += 1
                current_paras = []
            current_title = next_title

        HEADING_NUM_RE = re.compile(r'^(\d{1,2}(?:\.\d{1,2})*)$')
        MAJOR_SINGLE_RE = re.compile(
            r'^(?:'
            r'(?:\d{1,2}\.?\s+[A-Z][\w\s\-/,\(\)]{2,})'
            r'|'
            r'(?:Abstract|Conclusion|Conclusions|References|Bibliography|Acknowledgements|Appendix(?:\s+[A-Z0-9]+)?|Attention Visualizations|Visualizations)'
            r'|'
            r'(?:(?:Chapter|Chương|Part|Phần|Section|Hồi|Mục)\s+([0-9ivxlc]+|[a-z]+)[:\s\.\-]*(.*))'
            r')$',
            re.IGNORECASE
        )
        SUB_SINGLE_RE = re.compile(
            r'^(?:\d+\.)+\d+\s+([A-Z][\w\s\-/,\(\)]{2,})$'
        )

        for page_num, page in enumerate(doc):
            drawings = page.get_drawings()
            blocks = page.get_text("blocks")

            # 1. Detect and render Tables ONLY if page contains a Table caption
            page_tab_captions = []
            for b in blocks:
                if b[6] != 0:
                    continue
                t_first = b[4].strip().splitlines()[0].strip() if b[4].strip() else ""
                m_tab = TAB_CAPTION_PATTERN.match(t_first)
                if m_tab:
                    page_tab_captions.append((pymupdf.Rect(b[:4]), t_first, m_tab.group(1)))

            table_records = []
            table_rects = []
            if page_tab_captions:
                tabs = page.find_tables()
                if tabs.tables:
                    for t_idx, tab in enumerate(tabs.tables):
                        t_rect = pymupdf.Rect(tab.bbox)
                        if t_rect.width > 60 and t_rect.height > 30:
                            if any(abs(t_rect.y0 - cap_r.y1) < 140 or abs(cap_r.y0 - t_rect.y1) < 140 for cap_r, _, _ in page_tab_captions):
                                img_name = f"p{page_num + 1}_tab_{t_idx + 1}.png"
                                img_path = os.path.join(img_dir, img_name)
                                pix = page.get_pixmap(clip=t_rect, dpi=250)
                                pix.save(img_path)
                                table_records.append({"rect": t_rect, "img_path": img_path, "consumed": False})
                                table_rects.append(t_rect)

                # Fallback for borderless tables under table caption
                for cap_r, cap_txt, tab_id in page_tab_captions:
                    if not any(cap_r.intersects(tr) or abs(tr.y0 - cap_r.y1) < 40 for tr in table_rects):
                        pw = page.rect.width
                        # Restrict y1 so it does not extend beyond another caption below in the same column
                        next_caps = [c[0] for c in page_tab_captions if c[0].y0 > cap_r.y1 and abs(c[0].x0 - cap_r.x0) < 120]
                        y_max = next_caps[0].y0 - 2 if next_caps else cap_r.y1 + 450

                        # Restrict drawings by column to avoid swallowing adjacent column text in 2-column papers
                        if cap_r.x0 > pw * 0.45:
                            candidates = [d for d in drawings if d['rect'].y0 >= cap_r.y1 - 5 and d['rect'].y1 <= y_max and d['rect'].x0 >= pw * 0.45]
                        elif cap_r.x1 < pw * 0.55:
                            candidates = [d for d in drawings if d['rect'].y0 >= cap_r.y1 - 5 and d['rect'].y1 <= y_max and d['rect'].x1 <= pw * 0.55]
                        else:
                            candidates = [d for d in drawings if d['rect'].y0 >= cap_r.y1 - 5 and d['rect'].y1 <= y_max]

                        # Filter candidates: Table rules are stroke lines, not tall filled callout boxes (height > 15 with fill)
                        line_drawings = []
                        for d in candidates:
                            r = d['rect']
                            is_fill = d.get('fill') is not None
                            if is_fill and r.height > 15:
                                continue
                            line_drawings.append(d)

                        line_drawings.sort(key=lambda d: d['rect'].y0)

                        # Cluster drawings with vertical continuity from caption (gap < 60 pt)
                        d_below = []
                        cur_y1 = cap_r.y1
                        for d in line_drawings:
                            dr = d['rect']
                            if dr.y0 - cur_y1 > 60:
                                break
                            d_below.append(d)
                            cur_y1 = max(cur_y1, dr.y1)

                        if len(d_below) >= 2:
                            x0 = max(0, min(d['rect'].x0 for d in d_below) - 6)
                            y0 = max(0, min(d['rect'].y0 for d in d_below) - 4)
                            x1 = min(page.rect.width, max(d['rect'].x1 for d in d_below) + 6)
                            y1 = min(page.rect.height, max(d['rect'].y1 for d in d_below) + 10)
                            derived_rect = pymupdf.Rect(x0, y0, x1, y1)
                            img_name = f"p{page_num + 1}_tab_{len(table_records) + 1}.png"
                            img_path = os.path.join(img_dir, img_name)
                            pix = page.get_pixmap(clip=derived_rect, dpi=250)
                            pix.save(img_path)
                            table_records.append({"rect": derived_rect, "img_path": img_path, "consumed": False})
                            table_rects.append(derived_rect)

            # 2. Extract Figures (Raster images and vector diagrams)
            raster_imgs = page.get_images()
            page_fig_captions = []
            for b in blocks:
                if b[6] != 0:
                    continue
                first_line = b[4].strip().splitlines()[0].strip() if b[4].strip() else ""
                m_fig = FIG_CAPTION_PATTERN.match(first_line)
                if m_fig:
                    page_fig_captions.append((pymupdf.Rect(b[:4]), first_line, m_fig.group(1)))

            figure_images = {}
            fig_boxes = []

            for cap_rect, cap_text, fig_id in page_fig_captions:
                matching_rects = []
                for img_info in raster_imgs:
                    xref = img_info[0]
                    for ir in page.get_image_rects(xref):
                        if ir.y1 <= cap_rect.y0 + 10 and ir.y0 >= max(0, cap_rect.y0 - 550):
                            matching_rects.append(ir)

                if matching_rects:
                    union_r = matching_rects[0]
                    for r in matching_rects[1:]:
                        union_r = union_r | r

                    # Include any text blocks directly above union_r (e.g. figure labels / sub-titles like "Scaled Dot-Product Attention")
                    for b in blocks:
                        if b[6] != 0:
                            continue
                        tb_r = pymupdf.Rect(b[:4])
                        if tb_r.y1 <= union_r.y0 + 5 and tb_r.y0 >= union_r.y0 - 35:
                            if tb_r.x1 > union_r.x0 - 50 and tb_r.x0 < union_r.x1 + 50:
                                union_r = union_r | tb_r

                    y0 = max(0, union_r.y0 - 8)
                    y1 = min(cap_rect.y0 - 3, union_r.y1 + 4) if cap_rect.y0 > union_r.y1 else min(page.rect.height, union_r.y1 + 6)
                    bbox = pymupdf.Rect(
                        max(0, union_r.x0 - 8),
                        y0,
                        min(page.rect.width, union_r.x1 + 8),
                        y1
                    )
                    pix = page.get_pixmap(clip=bbox, dpi=250)
                    out_f = os.path.join(img_dir, f"p{page_num+1}_fig_{fig_id}.png")
                    pix.save(out_f)
                    figure_images[fig_id] = out_f
                    fig_boxes.append(bbox)
                else:
                    d_above = [d['rect'] for d in drawings if d['rect'].y1 <= cap_rect.y0 + 5 and d['rect'].y0 >= max(0, cap_rect.y0 - 550)]
                    if len(d_above) >= 5:
                        x0 = max(0, min(r.x0 for r in d_above) - 6)
                        y0 = max(0, min(r.y0 for r in d_above) - 6)
                        x1 = min(page.rect.width, max(r.x1 for r in d_above) + 6)
                        y1 = min(page.rect.height, max(max(r.y1 for r in d_above) + 6, cap_rect.y0 - 4))
                        # Prevent vector figure box from clipping a major heading sitting above it
                        for b in blocks:
                            if b[6] != 0:
                                continue
                            b_first = b[4].strip().splitlines()[0].strip() if b[4].strip() else ""
                            if MAJOR_SINGLE_RE.match(b_first):
                                h_rect = pymupdf.Rect(b[:4])
                                if h_rect.y1 <= y0 + 15:
                                    y0 = max(y0, h_rect.y1 + 4)
                        bbox = pymupdf.Rect(x0, y0, x1, y1)
                        pix = page.get_pixmap(clip=bbox, dpi=250)
                        out_f = os.path.join(img_dir, f"p{page_num+1}_fig_{fig_id}.png")
                        pix.save(out_f)
                        figure_images[fig_id] = out_f
                        fig_boxes.append(bbox)

            # 3. Process text blocks with table & figure content filtering
            for b in blocks:
                if b[6] != 0:
                    continue
                b_rect = pymupdf.Rect(b[:4])

                # Skip vertical margin watermarks (e.g. arXiv timestamp on left margin)
                if b[0] < 45 and (b[3] - b[1] > 120 or 'arxiv:' in b[4].lower()):
                    continue
                # Skip running headers at the top of pages > 0
                if page_num > 0 and b[1] < 72 and (b[3] - b[1] < 20):
                    continue
                # Skip page numbers at bottom
                if b[1] > page.rect.height - 60 and re.match(r'^\s*\d{1,3}\s*$', b[4]):
                    continue
                # Skip bottom publication / equal contribution footnotes on page 0
                if page_num == 0 and b[1] > page.rect.height - 120 and any(w in b[4].lower() for w in ('conference on', 'proceedings', 'equal contribution', 'nips')):
                    continue
                # Skip axis tick token noise from attention heatmaps (<EOS>, <pad>)
                if any(t in b[4] for t in ('<EOS>', '<pad>')) and not any(w in b[4] for w in ('Figure', 'Table', 'Visual')):
                    continue

                # Exclude block if inside table bbox
                in_table = False
                for t in table_records:
                    if b_rect.intersects(t["rect"]):
                        inter = b_rect & t["rect"]
                        if inter.get_area() > 0.35 * b_rect.get_area():
                            in_table = True
                            break
                if in_table:
                    continue

                lines = [l.strip() for l in b[4].splitlines() if l.strip()]
                if not lines:
                    continue

                # Check for major heading BEFORE figure exclusion to never lose top section titles
                if MAJOR_SINGLE_RE.match(lines[0]) and len(lines[0]) < 75 and not lines[0].endswith(('.', ':', ';')):
                    flush_chapter(lines[0])
                    lines = lines[1:]
                    if not lines:
                        continue

                # Exclude block if inside figure diagram (e.g. attention matrix tokens)
                in_fig = False
                for fb in fig_boxes:
                    if b_rect.intersects(fb):
                        in_fig = True
                        break
                if in_fig:
                    continue

                # Check for Heading at the start of the block
                m_num = HEADING_NUM_RE.match(lines[0])
                if m_num and len(lines) >= 2 and lines[1][0].isupper() and len(lines[1]) < 65:
                    num_str = m_num.group(1)
                    heading = f"{num_str} {lines[1]}"
                    if '.' not in num_str:
                        flush_chapter(heading)
                    else:
                        flush_para()
                        current_lines.append(heading)
                        flush_para(tag="h3")
                    lines = lines[2:]
                    if not lines:
                        continue
                elif SUB_SINGLE_RE.match(lines[0]) and len(lines[0]) < 75 and not lines[0].endswith(('.', ':', ';')):
                    flush_para()
                    current_lines.append(lines[0])
                    flush_para(tag="h3")
                    lines = lines[1:]
                    if not lines:
                        continue
                elif re.match(r'^(?:Encoder|Decoder)[:\.]?$', lines[0]):
                    flush_para()
                    current_lines.append(lines[0])
                    flush_para(tag="h4")
                    lines = lines[1:]
                    if not lines:
                        continue

                for l_idx, line in enumerate(lines):
                    m_tab = TAB_CAPTION_PATTERN.match(line)
                    if m_tab:
                        flush_para()
                        for t in table_records:
                            if not t["consumed"]:
                                t["consumed"] = True
                                p_global_idx += 1
                                current_paras.append(BookParagraph(
                                    id=f"c{chap_idx}_tab{p_global_idx}",
                                    original_text=f"[{line[:100]}]",
                                    translated_text=f"[{line[:100]}]",
                                    status="done",
                                    tag="img",
                                    index=p_global_idx,
                                    image_path=t["img_path"]
                                ))
                                break
                        current_lines.append(line)
                        flush_para(tag="h3")
                        continue

                    m_fig = FIG_CAPTION_PATTERN.match(line)
                    if m_fig:
                        flush_para()
                        fig_key = m_fig.group(1)
                        if fig_key in figure_images:
                            p_global_idx += 1
                            current_paras.append(BookParagraph(
                                id=f"c{chap_idx}_fig{p_global_idx}",
                                original_text=f"[Minh họa: {line[:100]}]",
                                translated_text=f"[Minh họa: {line[:100]}]",
                                status="done",
                                tag="img",
                                index=p_global_idx,
                                image_path=figure_images.pop(fig_key)
                            ))
                        current_lines.append(line)
                        flush_para(tag="p")
                        continue

                    is_bullet = line.startswith(('•', '–', '- ', '* '))
                    is_ref_item = bool(re.match(r'^\[\d+\]\s+[A-Z]', line))
                    if is_bullet or is_ref_item:
                        flush_para()
                        current_lines.append(line)
                        continue

                    current_lines.append(line)
                    ends_sentence = line.endswith(('.', '!', '?', ':', '."'))
                    ends_equation = bool(re.search(r'\(\d+\)$', line))
                    if ends_sentence or ends_equation:
                        flush_para()

        flush_chapter("End")

        return BookProject(
            id=project_id,
            title=title,
            author=author,
            source_format="pdf",
            source_file_path=file_path,
            chapters=chapters
        )

    @staticmethod
    def _parse_pdf_pypdf(file_path: str, project_id: str) -> BookProject:
        reader = pypdf.PdfReader(file_path)
        meta = reader.metadata
        raw_name = os.path.splitext(os.path.basename(file_path))[0]
        clean_name = re.sub(r'^[0-9a-f]{8}_', '', raw_name)
        title = meta.title if (meta and meta.title and meta.title.strip()) else clean_name
        author = meta.author if (meta and meta.author and meta.author.strip()) else "Tác giả không rõ"

        MAJOR_HEADING_PATTERN = re.compile(
            r'^(?:'
            r'(\d{1,2}\.?\s+[A-Z][\w\s\-/,\(\)]{2,})'
            r'|'
            r'(Abstract|Conclusion|Conclusions|References|Bibliography|Acknowledgements|Appendix(?:\s+[A-Z0-9]+)?)'
            r'|'
            r'((?:Chapter|Chương|Part|Phần|Section|Hồi|Mục)\s+([0-9ivxlc]+|[a-z]+)[:\s\.\-]*(.*))'
            r')$',
            re.IGNORECASE
        )

        SUB_HEADING_PATTERN = re.compile(
            r'^(?:\d+\.)+\d+\s+([A-Z][\w\s\-/,\(\)]{2,})$'
        )

        chapters: List[BookChapter] = []
        p_global_idx = 0
        chap_idx = 0

        current_paras: List[BookParagraph] = []
        current_title = "Phần mở đầu / Tiêu đề"
        current_lines: List[str] = []

        def flush_para(tag: str = "p"):
            nonlocal current_lines, current_paras, p_global_idx
            if not current_lines:
                return
            text = ""
            for l in current_lines:
                l = l.strip()
                if not l:
                    continue
                if text.endswith("-"):
                    text = text[:-1] + l
                else:
                    text = (text + " " + l).strip() if text else l
            current_lines = []
            if len(text) >= 2:
                p_global_idx += 1
                current_paras.append(BookParagraph(
                    id=f"c{chap_idx}_p{p_global_idx}",
                    original_text=text,
                    tag=tag,
                    index=p_global_idx
                ))

        def flush_chapter(next_title: str):
            nonlocal current_paras, chapters, current_title, chap_idx
            flush_para()
            if current_paras:
                chapters.append(BookChapter(
                    id=f"chap_{chap_idx}",
                    title=current_title,
                    paragraphs=current_paras,
                    doc_name=f"Section_{chap_idx}",
                    order=chap_idx
                ))
                chap_idx += 1
                current_paras = []
            current_title = next_title

        # Check if first page contains paper title
        if reader.pages:
            first_page_text = reader.pages[0].extract_text() or ""
            f_lines = [l.strip() for l in first_page_text.splitlines() if l.strip()]
            for l in f_lines[:8]:
                if "attribution" in l.lower() or "permission" in l.lower() or "arxiv" in l.lower():
                    continue
                if 10 < len(l) < 80 and not l.endswith(('.', ':', ';', '@')):
                    if title == clean_name or title == "Tác giả không rõ":
                        title = l
                    break

        # Setup project images directory
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        img_dir = os.path.join(data_dir, "projects", project_id, "images")
        os.makedirs(img_dir, exist_ok=True)

        for page_num, page in enumerate(reader.pages):
            page_images: List[str] = []
            try:
                if hasattr(page, "images"):
                    for img_idx, img in enumerate(page.images):
                        img_filename = f"p{page_num + 1}_{img_idx + 1}_{img.name}"
                        img_path = os.path.join(img_dir, img_filename)
                        with open(img_path, "wb") as f_img:
                            f_img.write(img.data)
                        page_images.append(img_path)
            except Exception:
                pass

            page_raw = page.extract_text() or ""
            raw_lines = [l.strip() for l in page_raw.splitlines() if l.strip()]
            if not raw_lines and not page_images:
                continue

            if raw_lines and re.match(r'^\d+$', raw_lines[-1]):
                raw_lines.pop()

            long_lines = [len(l) for l in raw_lines if len(l) > 30 and not l.endswith(('.', ':', ';'))]
            avg_line_len = (sum(long_lines) / len(long_lines)) if long_lines else 80

            for l_idx, line in enumerate(raw_lines):
                m_major = MAJOR_HEADING_PATTERN.match(line)
                if m_major and len(line) < 75 and not line.endswith(('.', ',', ';')):
                    flush_chapter(line)
                    continue

                m_sub = SUB_HEADING_PATTERN.match(line)
                if m_sub and len(line) < 75 and not line.endswith(('.', ',', ';')):
                    flush_para()
                    current_lines.append(line)
                    flush_para(tag="h3")
                    continue

                is_bullet = line.startswith(('•', '–', '- ', '* '))
                is_caption = bool(re.match(r'^(?:Figure|Fig\.?|Table)\s*[\d\.\-]+[:\.]?', line, re.I))
                is_ref_item = bool(re.match(r'^\[\d+\]\s+[A-Z]', line))

                if is_caption and "figure" in line.lower() and page_images:
                    flush_para()
                    for img_p in page_images:
                        p_global_idx += 1
                        current_paras.append(BookParagraph(
                            id=f"c{chap_idx}_img{p_global_idx}",
                            original_text=f"[Minh họa: {line[:100]}]",
                            translated_text=f"[Minh họa: {line[:100]}]",
                            status="done",
                            tag="img",
                            index=p_global_idx,
                            image_path=img_p
                        ))
                    page_images = []

                if is_bullet or is_caption or is_ref_item:
                    flush_para()
                    current_lines.append(line)
                    continue

                current_lines.append(line)
                ends_sentence = line.endswith(('.', '!', '?', ':', '."'))
                is_short_line = len(line) < (avg_line_len * 0.78)

                next_starts_new_block = False
                if l_idx + 1 < len(raw_lines):
                    next_l = raw_lines[l_idx + 1]
                    if (MAJOR_HEADING_PATTERN.match(next_l) or 
                        SUB_HEADING_PATTERN.match(next_l) or 
                        next_l.startswith(('•', '–', '- ', '* ')) or 
                        re.match(r'^(?:Figure|Fig\.?|Table)\s*[\d\.\-]+[:\.]?', next_l, re.I) or
                        re.match(r'^\[\d+\]\s+[A-Z]', next_l)):
                        next_starts_new_block = True

                if ends_sentence and (is_short_line or next_starts_new_block):
                    flush_para()

            if page_images:
                flush_para()
                for img_p in page_images:
                    p_global_idx += 1
                    current_paras.append(BookParagraph(
                        id=f"c{chap_idx}_img{p_global_idx}",
                        original_text=f"[Minh họa trang {page_num + 1}]",
                        translated_text=f"[Minh họa trang {page_num + 1}]",
                        status="done",
                        tag="img",
                        index=p_global_idx,
                        image_path=img_p
                    ))
                page_images = []

        flush_chapter("End")

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
