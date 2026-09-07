"""
Multi-format Book Exporter (EPUB, Bilingual EPUB, DOCX, HTML, Markdown, TXT).
Preserves book styling, generates table of contents, and produces publication-ready files.
"""
import os
import re
import zipfile
import tempfile
import shutil
import unicodedata
import io
import html
import hashlib
import base64
from typing import Optional, List
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from core.parser import BookProject, BookChapter, BookParagraph


def normalize_text(text: str) -> str:
    """Normalize Unicode to NFC (precomposed) and fix escaped dollar signs."""
    if not text:
        return ""
    text = unicodedata.normalize('NFC', text)
    text = text.replace(r'\$', '$')
    return text


def unicode_math_fallback(latex: str) -> str:
    """Fallback converter that maps LaTeX symbols to clean HTML / Unicode."""
    res = latex
    replacements = [
        (r'\times', '×'), (r'\cdot', '·'), (r'\in', '∈'), (r'\notin', '∉'),
        (r'\subset', '⊂'), (r'\subseteq', '⊆'), (r'\cup', '∪'), (r'\cap', '∩'),
        (r'\forall', '∀'), (r'\exists', '∃'), (r'\rightarrow', '→'), (r'\to', '→'),
        (r'\leftarrow', '←'), (r'\Rightarrow', '⇒'), (r'\Leftarrow', '⇐'),
        (r'\leq', '≤'), (r'\le', '≤'), (r'\geq', '≥'), (r'\ge', '≥'),
        (r'\neq', '≠'), (r'\ne', '≠'), (r'\approx', '≈'), (r'\sim', '∼'),
        (r'\infty', '∞'), (r'\pm', '±'), (r'\alpha', 'α'), (r'\beta', 'β'),
        (r'\gamma', 'γ'), (r'\delta', 'δ'), (r'\epsilon', 'ε'), (r'\theta', 'θ'),
        (r'\lambda', 'λ'), (r'\mu', 'μ'), (r'\sigma', 'σ'), (r'\tau', 'τ'),
        (r'\phi', 'φ'), (r'\omega', 'ω'), (r'\Delta', 'Δ'), (r'\Sigma', 'Σ'),
        (r'\Omega', 'Ω'), (r'\mathbb{R}', 'ℝ'), (r'\mathbb{N}', 'ℕ'), (r'\mathbb{Z}', 'ℤ'),
        (r'\sum', '∑'), (r'\prod', '∏'), (r'\int', '∫'),
    ]
    for k, v in replacements:
        res = res.replace(k, v)
    res = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1 / \2)', res)
    res = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', res)
    res = re.sub(r'\\text\{([^}]+)\}', r'\1', res)
    res = re.sub(r'_\{([^}]+)\}', r'<sub>\1</sub>', res)
    res = re.sub(r'_([a-zA-Z0-9])', r'<sub>\1</sub>', res)
    res = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', res)
    res = re.sub(r'\^([a-zA-Z0-9])', r'<sup>\1</sup>', res)
    return f'<span class="math-fallback">{res}</span>'


def latex_to_mathml(latex_str: str, display: bool = False) -> str:
    """Converts a LaTeX mathematical string to valid MathML XML."""
    clean_latex = latex_str.strip()
    if not clean_latex:
        return ""
    try:
        import latex2mathml.converter
        mathml = latex2mathml.converter.convert(clean_latex)
        if display and 'display="inline"' in mathml:
            mathml = mathml.replace('display="inline"', 'display="block"')
        return mathml
    except Exception:
        return unicode_math_fallback(clean_latex)


_MATH_IMG_CACHE = {}  # {md5_hash: png_bytes}


def render_latex_to_png(latex_str: str, dpi: int = 250) -> tuple[str, bytes]:
    """
    Renders LaTeX formula to a high-resolution transparent PNG image.
    Returns (img_filename, png_bytes).
    Uses caching to render each unique formula only once.
    """
    clean_latex = latex_str.strip()
    if clean_latex.startswith('$') and clean_latex.endswith('$'):
        clean_latex = clean_latex[1:-1].strip()
    if clean_latex.startswith('$$') and clean_latex.endswith('$$'):
        clean_latex = clean_latex[2:-2].strip()

    # Pre-clean known macros for mathtext compatibility
    clean_latex = clean_latex.replace(r'\bm{', r'\mathbf{')
    clean_latex = clean_latex.replace(r'\boldsymbol{', r'\mathbf{')
    clean_latex = clean_latex.replace(r'\bold{', r'\mathbf{')

    hash_key = hashlib.md5(f"{clean_latex}_{dpi}".encode('utf-8')).hexdigest()[:12]
    img_filename = f"math_{hash_key}.png"

    if hash_key in _MATH_IMG_CACHE:
        return img_filename, _MATH_IMG_CACHE[hash_key]

    try:
        import matplotlib.mathtext as mathtext
        buf = io.BytesIO()
        mathtext.math_to_image(clean_latex, buf, dpi=dpi, format='png')
        png_bytes = buf.getvalue()
        _MATH_IMG_CACHE[hash_key] = png_bytes
        return img_filename, png_bytes
    except Exception:
        return "", b""


def format_math_for_epub(text: str, math_store: dict) -> tuple[str, bool]:
    """
    Parses LaTeX formulas from text and converts them to <img> tags referencing
    crisp math PNG images embedded in the EPUB (100% Kindle compatible).
    Returns (formatted_html, has_math).
    """
    text = normalize_text(text)
    has_math = False

    # 1. Numbered standalone equation at start: e.g. Attention(...) = ... (1) Rest of paragraph
    eq_match = re.match(r'^(.*?\\frac\{[^}]+\}\{[^}]+\}[^\n]*?)\s*\((\d+)\)\s+([A-Z\u00C0-\u1EF9].*)$', text, re.DOTALL)
    extra_block = ""
    if eq_match:
        eq_part = eq_match.group(1).strip()
        eq_num = eq_match.group(2)
        text = eq_match.group(3).strip()
        has_math = True
        fn, img_bytes = render_latex_to_png(eq_part, dpi=250)
        if fn and img_bytes:
            math_store[fn] = img_bytes
            safe_alt = html.escape(eq_part, quote=True)
            extra_block = f'<div class="math-block math-equation"><div class="math-formula"><img src="images/{fn}" class="math-display-img" alt="{safe_alt}" /></div><div class="eq-num">({eq_num})</div></div>\n'
        else:
            extra_block = f'<div class="math-block math-equation"><div class="math-formula">{unicode_math_fallback(eq_part)}</div><div class="eq-num">({eq_num})</div></div>\n'

    # 2. Display math $$...$$
    def rep_display(m):
        nonlocal has_math
        has_math = True
        content = m.group(1).strip()
        tag_m = re.search(r'\\tag\{(\d+)\}\s*$', content)
        eq_num = ""
        if tag_m:
            eq_num = tag_m.group(1)
            content = content[:tag_m.start()].strip()
        fn, img_bytes = render_latex_to_png(content, dpi=250)
        if fn and img_bytes:
            math_store[fn] = img_bytes
            safe_alt = html.escape(content, quote=True)
            formula_html = f'<img src="images/{fn}" class="math-display-img" alt="{safe_alt}" />'
        else:
            formula_html = unicode_math_fallback(content)

        if eq_num:
            return f'<div class="math-block math-equation"><div class="math-formula">{formula_html}</div><div class="eq-num">({eq_num})</div></div>'
        return f'<div class="math-block">{formula_html}</div>'

    text = re.sub(r'\$\$([^\$]+)\$\$', rep_display, text)
    # Merge adjacent math-blocks into a single clean card
    text = re.sub(r'</div>\s*<div class="math-block">', '<div style="margin-top: 8px;"></div>', text)

    # 3. Inline math $...$
    def rep_inline(m):
        nonlocal has_math
        content = m.group(1).strip()
        if re.match(r'^\d+(\.\d+)?$', content):
            return f"${content}$"
        has_math = True
        fn, img_bytes = render_latex_to_png(content, dpi=250)
        if fn and img_bytes:
            math_store[fn] = img_bytes
            safe_alt = html.escape(content, quote=True)
            return f'<img src="images/{fn}" class="math-inline-img" alt="{safe_alt}" />'
        else:
            return unicode_math_fallback(content)

    text = re.sub(r'\$([^\$]+)\$', rep_inline, text)

    # 4. Residual bare LaTeX expressions like \frac{...}{...}
    def rep_bare_frac(m):
        nonlocal has_math
        has_math = True
        content = m.group(0).strip()
        fn, img_bytes = render_latex_to_png(content, dpi=250)
        if fn and img_bytes:
            math_store[fn] = img_bytes
            safe_alt = html.escape(content, quote=True)
            return f'<img src="images/{fn}" class="math-inline-img" alt="{safe_alt}" />'
        else:
            return unicode_math_fallback(content)

    text = re.sub(r'\\frac\{[^{}]*\}\{[^{}]*\}', rep_bare_frac, text)

    final_html = extra_block + text if extra_block else text
    return final_html, has_math


def format_math_in_html(text: str) -> tuple[str, bool]:
    """
    Parses LaTeX formulas from text and converts them to MathML with academic styling.
    Returns (formatted_html, has_math).
    """
    text = normalize_text(text)
    has_math = False

    # 1. Check for standalone equation with number at start: e.g. Attention(...) = ... (1) Rest of paragraph
    eq_match = re.match(r'^(.*?\\frac\{[^}]+\}\{[^}]+\}[^\n]*?)\s*\((\d+)\)\s+([A-Z\u00C0-\u1EF9].*)$', text, re.DOTALL)
    extra_block = ""
    if eq_match:
        eq_part = eq_match.group(1).strip()
        eq_num = eq_match.group(2)
        text = eq_match.group(3).strip()
        has_math = True
        eq_mathml = latex_to_mathml(eq_part, display=True)
        extra_block = f'<div class="math-block math-equation"><div class="math-formula">{eq_mathml}</div><div class="eq-num">({eq_num})</div></div>\n'

    # 2. Display math $$...$$
    def rep_display(m):
        nonlocal has_math
        has_math = True
        content = m.group(1).strip()
        tag_m = re.search(r'\\tag\{(\d+)\}\s*$', content)
        eq_num = ""
        if tag_m:
            eq_num = tag_m.group(1)
            content = content[:tag_m.start()].strip()
        mathml = latex_to_mathml(content, display=True)
        if eq_num:
            return f'<div class="math-block math-equation"><div class="math-formula">{mathml}</div><div class="eq-num">({eq_num})</div></div>'
        return f'<div class="math-block">{mathml}</div>'

    text = re.sub(r'\$\$([^\$]+)\$\$', rep_display, text)
    # Merge adjacent math-blocks into a single clean card
    text = re.sub(r'</div>\s*<div class="math-block">', '<div style="margin-top: 8px;"></div>', text)

    # 3. Inline math $...$
    def rep_inline(m):
        nonlocal has_math
        content = m.group(1).strip()
        if re.match(r'^\d+(\.\d+)?$', content):
            return f"${content}$"
        has_math = True
        return latex_to_mathml(content, display=False)
    text = re.sub(r'\$([^\$]+)\$', rep_inline, text)

    # 4. Residual bare LaTeX expressions like \frac{...}{...}
    def rep_bare_frac(m):
        nonlocal has_math
        has_math = True
        return latex_to_mathml(m.group(0), display=False)
    text = re.sub(r'\\frac\{[^{}]*\}\{[^{}]*\}', rep_bare_frac, text)

    final_html = extra_block + text if extra_block else text
    return final_html, has_math


def format_math_for_docx(text: str) -> str:
    """Formats LaTeX math into clean Unicode text suitable for Word documents."""
    text = normalize_text(text)
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1 / \2)', text)
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', text)
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    replacements = [
        (r'\times', '×'), (r'\cdot', '·'), (r'\in', '∈'), (r'\notin', '∉'),
        (r'\leq', '≤'), (r'\geq', '≥'), (r'\neq', '≠'), (r'\approx', '≈'),
        (r'\infty', '∞'), (r'\pm', '±'), (r'\alpha', 'α'), (r'\beta', 'β'),
        (r'\gamma', 'γ'), (r'\delta', 'δ'), (r'\epsilon', 'ε'), (r'\theta', 'θ'),
        (r'\lambda', 'λ'), (r'\mu', 'μ'), (r'\sigma', 'σ'), (r'\tau', 'τ'),
        (r'\phi', 'φ'), (r'\omega', 'ω'), (r'\Delta', 'Δ'), (r'\Sigma', 'Σ'),
        (r'\Omega', 'Ω'), (r'\mathbb{R}', 'ℝ'), (r'\mathbb{N}', 'ℕ'), (r'\mathbb{Z}', 'ℤ'),
        (r'\sum', '∑'), (r'\prod', '∏'), (r'\int', '∫'),
    ]
    for k, v in replacements:
        text = text.replace(k, v)
    text = re.sub(r'\$([^\$]+)\$', r'\1', text)
    return text


def is_caption_para(p: BookParagraph) -> bool:
    """Checks if paragraph is a table or figure caption."""
    if not p:
        return False
    if getattr(p, 'tag', '') == 'caption':
        return True
    orig = p.original_text.strip()
    trans = p.translated_text.strip()
    pat = r'^(?:Figure|Fig\.?|Hình|Table|Bảng)\s*[\d\.\-]+[:\.\-–]'
    return bool(re.match(pat, orig, re.I) or re.match(pat, trans, re.I))


def format_caption_text(text: str) -> tuple[str, str]:
    """Splits caption into (label, content), e.g. ('Hình 1:', 'Sơ đồ kiến trúc...')"""
    text = normalize_text(text)
    m = re.match(r'^(Figure\s*[\d\.\-]+[:\.\-–]|Fig\.?\s*[\d\.\-]+[:\.\-–]|Hình\s*[\d\.\-]+[:\.\-–]|Table\s*[\d\.\-]+[:\.\-–]|Bảng\s*[\d\.\-]+[:\.\-–])\s*(.*)$', text, re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", text


def is_academic_paper(project: BookProject) -> bool:
    """Checks if project appears to be a scientific paper."""
    if project.source_format == "pdf":
        return any(c.title.strip().lower() in ("abstract", "tóm tắt", "phần mở đầu / tiêu đề") for c in project.chapters)
    return any(c.title.strip().lower() in ("abstract", "tóm tắt") for c in project.chapters)


class BookExporter:
    """Exports translated or bilingual books to various formats."""

    @classmethod
    def export_epub(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """
        Exports as EPUB.
        If original source was EPUB, updates original XHTML documents in-place to preserve all images and styles!
        Otherwise, builds a clean new EPUB using ebooklib.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if project.source_format == "epub" and os.path.exists(project.source_file_path):
            return cls._export_epub_inplace(project, output_path, bilingual)
        else:
            return cls._export_epub_fresh(project, output_path, bilingual)

    @classmethod
    def _export_epub_inplace(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """
        Modifies the original EPUB zip archive by substituting translated text in XHTML files.
        Guarantees 100% preservation of images, CSS, fonts, and cover.
        """
        # Map paragraph IDs to their translations
        para_map = {}
        for chap in project.chapters:
            for p in chap.paragraphs:
                para_map[p.id] = p

        # Map document names to chapters
        doc_chap_map = {c.doc_name: c for c in project.chapters if c.doc_name}

        temp_dir = tempfile.mkdtemp(prefix="epub_export_")
        try:
            with zipfile.ZipFile(project.source_file_path, 'r') as zin:
                zin.extractall(temp_dir)

            # Update XHTML files
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ('.xhtml', '.html', '.htm'):
                        rel_path = os.path.relpath(os.path.join(root, f), temp_dir).replace('\\', '/')
                        # Check matching document
                        target_chap = None
                        for chap in project.chapters:
                            if chap.doc_name and (chap.doc_name in rel_path or rel_path.endswith(chap.doc_name)):
                                target_chap = chap
                                break

                        if target_chap:
                            file_full = os.path.join(root, f)
                            with open(file_full, 'r', encoding='utf-8', errors='ignore') as xf:
                                content = xf.read()

                            soup = BeautifulSoup(content, 'html.parser')
                            raw_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote', 'li', 'div'])
                            tags = [t for t in raw_tags if not (t.name == 'div' and t.find(['p', 'div', 'blockquote']))]

                            for p in target_chap.paragraphs:
                                trans = p.translated_text.strip()
                                if not trans:
                                    continue

                                # Match tag by text
                                for t in tags:
                                    if t.get_text(strip=True) == p.original_text.strip():
                                        if bilingual:
                                            # Bilingual: original in smaller italic or gray, followed by translated
                                            t.clear()
                                            en_span = soup.new_tag("div")
                                            en_span['style'] = "color: #718096; font-size: 0.9em; margin-bottom: 4px; font-style: italic;"
                                            en_span.string = p.original_text
                                            vi_span = soup.new_tag("div")
                                            vi_span.string = trans
                                            t.append(en_span)
                                            t.append(vi_span)
                                        else:
                                            t.string = trans
                                        break

                            with open(file_full, 'w', encoding='utf-8') as xf:
                                xf.write(str(soup))

            # Repack zip as EPUB
            if os.path.exists(output_path):
                os.remove(output_path)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                # mimetype must be first and uncompressed per EPUB spec
                mimetype_path = os.path.join(temp_dir, 'mimetype')
                if os.path.exists(mimetype_path):
                    zout.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        full = os.path.join(root, file)
                        rel = os.path.relpath(full, temp_dir)
                        if rel == 'mimetype':
                            continue
                        zout.write(full, rel)

            return output_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _export_epub_fresh(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """Constructs a new EPUB book from scratch using ebooklib with MathML and Vietnamese font support."""
        book = epub.EpubBook()
        book.set_identifier(f"ai-book-{project.id}")
        book_title = normalize_text(f"{project.title} (Bản Dịch Tiếng Việt)" if not bilingual else f"{project.title} (Song Ngữ Anh - Việt)")
        book.set_title(book_title)
        book.set_language('vi')
        book.add_author(normalize_text(project.author))

        epub_chapters = []
        toc = []

        # Vietnamese-optimized typography with MathML and Kindle Math Image support
        style = '''
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Times New Roman", "Palatino Linotype", Arial, sans-serif;
            line-height: 1.7;
            margin: 5%;
            color: #1a202c;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
        }
        h1, h2, h3, h4 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #2b6cb0;
            font-weight: 700;
        }
        h1 {
            text-align: center;
        }
        h2 {
            font-size: 1.45em;
            text-align: left;
            border-bottom: 1.5px solid #cbd5e1;
            padding-bottom: 6px;
            margin-top: 1.8em;
            margin-bottom: 0.8em;
        }
        h3 {
            font-size: 1.22em;
            margin-top: 1.4em;
            margin-bottom: 0.5em;
            text-align: left;
        }
        h4 {
            font-size: 1.08em;
            margin-top: 1.2em;
            margin-bottom: 0.4em;
            color: #475569;
            text-align: left;
        }
        p {
            text-indent: 1.5em;
            margin-bottom: 0.8em;
            text-align: justify;
        }
        .bilingual-en {
            color: #718096;
            font-size: 0.88em;
            font-style: italic;
            margin-bottom: 3px;
            text-indent: 0;
        }
        .bilingual-vi {
            color: #1a202c;
            margin-bottom: 14px;
        }
        .academic-figure, .academic-table-block {
            margin: 22px auto;
            text-align: center;
            max-width: 98%;
        }
        .figure-caption, .table-caption {
            font-size: 0.9em;
            color: #4a5568;
            line-height: 1.5;
            margin-top: 6px;
            margin-bottom: 6px;
            text-indent: 0;
            text-align: left;
        }
        .caption-label {
            font-weight: bold;
            color: #2b6cb0;
        }
        .caption-pair {
            margin-top: 4px;
        }
        .caption-en {
            color: #718096;
            font-style: italic;
            font-size: 0.88em;
            margin-bottom: 4px;
        }
        .caption-vi {
            color: #1a202c;
            font-size: 0.95em;
        }
        .academic-footnotes {
            margin-top: 24px;
            padding-top: 12px;
            border-top: 1px solid #e2e8f0;
            font-size: 0.85em;
            color: #718096;
        }
        .academic-footnote {
            margin-bottom: 6px;
            text-indent: 0;
            text-align: left;
        }
        .math-inline-img {
            display: inline-block;
            vertical-align: -0.22em;
            max-height: 1.45em;
            width: auto;
            height: auto;
        }
        .math-display-img {
            display: block;
            margin: 8px auto;
            max-width: 95%;
            max-height: 5.5em;
            width: auto;
            height: auto;
        }
        .math-block {
            text-align: center;
            margin: 1.4em 0;
            padding: 10px 14px;
            background: #f8fafc;
            border-radius: 6px;
            overflow-x: auto;
        }
        .math-equation {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .math-formula {
            display: inline-block;
            margin: 0 auto;
        }
        .eq-num {
            float: right;
            color: #64748b;
            font-size: 0.9em;
        }
        math {
            font-family: "Cambria Math", "Latin Modern Math", "STIX Two Math", serif;
            font-size: 1.05em;
        }
        .math-fallback {
            font-family: "Cambria Math", "Latin Modern Math", "Times New Roman", serif;
            font-style: italic;
        }
        .math-inline-img {
            display: inline-block;
            vertical-align: -0.22em;
            max-height: 1.45em;
            width: auto;
            height: auto;
        }
        .math-display-img {
            display: block;
            margin: 8px auto;
            max-width: 95%;
            max-height: 5.5em;
            width: auto;
            height: auto;
        }
        @media (prefers-color-scheme: dark) {
            .math-inline-img, .math-display-img {
                filter: invert(1);
            }
            .math-block {
                background: #1e293b;
            }
        }
        '''
        default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style)
        book.add_item(default_css)

        added_images = set()
        math_store = {}

        for i, chap in enumerate(project.chapters):
            chap_title = normalize_text(chap.title)
            c_item = epub.EpubHtml(title=chap_title, file_name=f"chap_{i}.xhtml", lang="vi")
            c_item.add_item(default_css)

            if chap_title in ("Phần mở đầu / Tiêu đề", "Title", "Header"):
                html_parts = []
            else:
                html_parts = [f"<h2>{chap_title}</h2>"]
            chap_has_math = False

            paras = chap.paragraphs
            p_idx = 0
            while p_idx < len(paras):
                p = paras[p_idx]

                # Check if image paragraph
                if (p.tag == "img" or getattr(p, "image_path", "")) and p.image_path and os.path.exists(p.image_path):
                    img_filename = f"img_{os.path.basename(p.image_path)}"
                    try:
                        if img_filename not in added_images:
                            with open(p.image_path, "rb") as f_img:
                                epub_img = epub.EpubItem(
                                    uid=f"img_{i}_{p.id}",
                                    file_name=f"images/{img_filename}",
                                    media_type="image/png" if p.image_path.lower().endswith(".png") else "image/jpeg",
                                    content=f_img.read()
                                )
                                book.add_item(epub_img)
                                added_images.add(img_filename)
                    except Exception:
                        pass

                    caption_para = None
                    if p_idx + 1 < len(paras) and is_caption_para(paras[p_idx + 1]):
                        caption_para = paras[p_idx + 1]

                    img_tag = f'<div style="text-align: center; margin: 8px 0;"><img src="images/{img_filename}" style="max-width: 100%; height: auto;" /></div>'

                    if caption_para:
                        cap_orig, _ = format_math_for_epub(caption_para.original_text.strip(), math_store)
                        cap_trans_raw = caption_para.translated_text.strip() if caption_para.translated_text.strip() else caption_para.original_text.strip()
                        cap_trans, _ = format_math_for_epub(cap_trans_raw, math_store)
                        is_table = bool(re.search(r'^(?:Table|Bảng)\b', caption_para.original_text, re.I) or re.search(r'^(?:Table|Bảng)\b', caption_para.translated_text, re.I) or 'tab' in p.id)

                        if bilingual:
                            en_lbl, en_content = format_caption_text(cap_orig)
                            vi_lbl, vi_content = format_caption_text(cap_trans)
                            cap_block = f'''<div class="caption-pair">
                                <div class="caption-en"><strong>{en_lbl}</strong> {en_content}</div>
                                <div class="caption-vi"><strong>{vi_lbl}</strong> {vi_content}</div>
                            </div>'''
                        else:
                            lbl, content = format_caption_text(cap_trans)
                            if lbl:
                                cap_block = f'<span class="caption-label">{lbl}</span> {content}'
                            else:
                                cap_block = cap_trans

                        if is_table:
                            html_parts.append(f'<div class="academic-table-block"><div class="table-caption">{cap_block}</div>{img_tag}</div>')
                        else:
                            html_parts.append(f'<figure class="academic-figure">{img_tag}<figcaption class="figure-caption">{cap_block}</figcaption></figure>')
                        p_idx += 2
                        continue
                    else:
                        html_parts.append(f'<div style="text-align: center; margin: 18px 0;"><img src="images/{img_filename}" style="max-width: 100%; height: auto;" /></div>')
                        p_idx += 1
                        continue

                # Standalone caption
                if is_caption_para(p):
                    trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                    trans_html, _ = format_math_for_epub(trans, math_store)
                    lbl, content = format_caption_text(trans_html)
                    if lbl:
                        html_parts.append(f'<div class="table-caption"><span class="caption-label">{lbl}</span> {content}</div>')
                    else:
                        html_parts.append(f'<div class="table-caption">{trans_html}</div>')
                    p_idx += 1
                    continue

                # Footnote
                is_footnote = p.original_text.strip().startswith(('∗', '†', '‡', '*'))
                trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                trans_html, has_m = format_math_for_epub(trans, math_store)
                if has_m:
                    chap_has_math = True

                if is_footnote:
                    if bilingual:
                        orig_html, _ = format_math_for_epub(p.original_text, math_store)
                        html_parts.append(f'<div class="academic-footnote"><div class="bilingual-en">{orig_html}</div><div class="bilingual-vi">{trans_html}</div></div>')
                    else:
                        html_parts.append(f'<div class="academic-footnote">{trans_html}</div>')
                    p_idx += 1
                    continue

                if bilingual:
                    orig_html, _ = format_math_for_epub(p.original_text, math_store)
                    html_parts.append(f'<div class="bilingual-en">{orig_html}</div>')
                    html_parts.append(f'<p class="bilingual-vi">{trans_html}</p>')
                else:
                    tag = p.tag if p.tag in ('h1', 'h2', 'h3', 'h4', 'blockquote') else 'p'
                    if trans_html.startswith('<div class="math-block'):
                        parts = trans_html.split('\n', 1)
                        if len(parts) == 2 and parts[1].strip():
                            html_parts.append(parts[0])
                            html_parts.append(f'<{tag}>{parts[1].strip()}</{tag}>')
                        else:
                            html_parts.append(trans_html)
                    else:
                        html_parts.append(f'<{tag}>{trans_html}</{tag}>')
                p_idx += 1

            if chap_has_math:
                c_item.properties.append("mathml")

            c_item.content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="vi" lang="vi">
<head>
  <meta charset="utf-8" />
  <title>{normalize_text(chap.title)}</title>
  <link rel="stylesheet" type="text/css" href="style/default.css" />
</head>
<body>
{''.join(html_parts)}
</body>
</html>""".encode('utf-8')
            book.add_item(c_item)
            epub_chapters.append(c_item)
            toc.append(c_item)

        # Add all generated math images to the EPUB archive
        for fn, img_bytes in math_store.items():
            if fn not in added_images and img_bytes:
                math_item = epub.EpubItem(
                    uid=f"math_{fn.replace('.', '_')}",
                    file_name=f"images/{fn}",
                    media_type="image/png",
                    content=img_bytes
                )
                book.add_item(math_item)
                added_images.add(fn)

        book.toc = tuple(toc)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + epub_chapters

        epub.write_epub(output_path, book)
        return output_path

    @classmethod
    def export_docx(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """Exports book as a polished Microsoft Word (.docx) document with clean math typography."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = docx.Document()

        is_paper = is_academic_paper(project)

        # Title Page / Header
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_p.paragraph_format.space_before = Pt(12)
        title_p.paragraph_format.space_after = Pt(6)
        run = title_p.add_run(normalize_text(project.title))
        run.font.name = "Times New Roman"
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 41, 59)

        subtitle_p = doc.add_paragraph()
        subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle_p.paragraph_format.space_before = Pt(2)
        subtitle_p.paragraph_format.space_after = Pt(4)
        if is_paper:
            sub_text = "Bản dịch Học Thuật Tiếng Việt (AI Academic Edition)" if not bilingual else "Bản dịch Song Ngữ Anh - Việt (Academic Edition)"
        else:
            sub_text = "Bản dịch Tiếng Việt (AI Literary Edition)" if not bilingual else "Bản dịch Song Ngữ Anh - Việt"
        sub_run = subtitle_p.add_run(normalize_text(sub_text))
        sub_run.font.name = "Times New Roman"
        sub_run.font.size = Pt(13)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 116, 139)

        author_p = doc.add_paragraph()
        author_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_p.paragraph_format.space_before = Pt(2)
        author_p.paragraph_format.space_after = Pt(18)
        author_run = author_p.add_run(f"Tác giả: {normalize_text(project.author)}")
        author_run.font.name = "Times New Roman"
        author_run.font.size = Pt(11.5)
        author_run.font.color.rgb = RGBColor(71, 85, 105)

        # Non-paper books get a full title page break
        if not is_paper:
            doc.add_page_break()

        for chap in project.chapters:
            chap_title = normalize_text(chap.title)

            # Chapter heading (left-aligned for all academic and modern documents)
            if chap_title not in ("Phần mở đầu / Tiêu đề", "Title", "Header"):
                heading = doc.add_heading(chap_title, level=1)
                heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
                heading.paragraph_format.space_before = Pt(22)
                heading.paragraph_format.space_after = Pt(8)
                for run in heading.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(15.5)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(43, 108, 176)

            paras = chap.paragraphs
            p_idx = 0
            while p_idx < len(paras):
                p = paras[p_idx]

                # Check if image paragraph
                if (p.tag == "img" or getattr(p, "image_path", "")) and p.image_path and os.path.exists(p.image_path):
                    caption_para = None
                    if p_idx + 1 < len(paras) and is_caption_para(paras[p_idx + 1]):
                        caption_para = paras[p_idx + 1]

                    is_table = False
                    if caption_para:
                        is_table = bool(re.search(r'^(?:Table|Bảng)\b', caption_para.original_text, re.I) or re.search(r'^(?:Table|Bảng)\b', caption_para.translated_text, re.I) or 'tab' in p.id)

                    def add_docx_caption(cap_p):
                        trans_cap = format_math_for_docx(cap_p.translated_text.strip() if cap_p.translated_text.strip() else cap_p.original_text.strip())
                        orig_cap = format_math_for_docx(cap_p.original_text.strip())
                        if bilingual:
                            en_p = doc.add_paragraph()
                            en_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            en_p.paragraph_format.space_before = Pt(8)
                            en_p.paragraph_format.space_after = Pt(2)
                            r_en = en_p.add_run(orig_cap)
                            r_en.font.name = "Times New Roman"
                            r_en.font.size = Pt(9.5)
                            r_en.font.italic = True
                            r_en.font.color.rgb = RGBColor(100, 116, 139)

                            vi_p = doc.add_paragraph()
                            vi_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            vi_p.paragraph_format.space_before = Pt(2)
                            vi_p.paragraph_format.space_after = Pt(12)
                            lbl, content = format_caption_text(trans_cap)
                            if lbl:
                                r_lbl = vi_p.add_run(lbl + " ")
                                r_lbl.font.name = "Times New Roman"
                                r_lbl.font.size = Pt(10.5)
                                r_lbl.font.bold = True
                                r_lbl.font.color.rgb = RGBColor(43, 108, 176)
                            r_vi = vi_p.add_run(content if lbl else trans_cap)
                            r_vi.font.name = "Times New Roman"
                            r_vi.font.size = Pt(10.5)
                        else:
                            vi_p = doc.add_paragraph()
                            vi_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            vi_p.paragraph_format.space_before = Pt(8)
                            vi_p.paragraph_format.space_after = Pt(10)
                            lbl, content = format_caption_text(trans_cap)
                            if lbl:
                                r_lbl = vi_p.add_run(lbl + " ")
                                r_lbl.font.name = "Times New Roman"
                                r_lbl.font.size = Pt(10.5)
                                r_lbl.font.bold = True
                                r_lbl.font.color.rgb = RGBColor(43, 108, 176)
                            r_vi = vi_p.add_run(content if lbl else trans_cap)
                            r_vi.font.name = "Times New Roman"
                            r_vi.font.size = Pt(10.5)

                    def add_docx_image(img_path):
                        try:
                            p_img = doc.add_paragraph()
                            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            p_img.paragraph_format.space_before = Pt(6)
                            p_img.paragraph_format.space_after = Pt(6)
                            p_img.add_run().add_picture(img_path, width=Inches(5.5))
                        except Exception:
                            pass

                    if is_table:
                        # Table: Caption FIRST, Image NEXT
                        if caption_para:
                            add_docx_caption(caption_para)
                        add_docx_image(p.image_path)
                    else:
                        # Figure: Image FIRST, Caption NEXT
                        add_docx_image(p.image_path)
                        if caption_para:
                            add_docx_caption(caption_para)

                    p_idx += (2 if caption_para else 1)
                    continue

                # Standalone caption without image
                if is_caption_para(p):
                    trans_cap = format_math_for_docx(p.translated_text.strip() if p.translated_text.strip() else p.original_text.strip())
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_cap.paragraph_format.space_before = Pt(8)
                    p_cap.paragraph_format.space_after = Pt(8)
                    lbl, content = format_caption_text(trans_cap)
                    if lbl:
                        r_lbl = p_cap.add_run(lbl + " ")
                        r_lbl.font.name = "Times New Roman"
                        r_lbl.font.size = Pt(10.5)
                        r_lbl.font.bold = True
                        r_lbl.font.color.rgb = RGBColor(43, 108, 176)
                    r_txt = p_cap.add_run(content if lbl else trans_cap)
                    r_txt.font.name = "Times New Roman"
                    r_txt.font.size = Pt(10.5)
                    p_idx += 1
                    continue

                # Footnote paragraph (starts with ∗, †, ‡)
                is_footnote = p.original_text.strip().startswith(('∗', '†', '‡', '*'))
                trans = format_math_for_docx(p.translated_text.strip() if p.translated_text.strip() else p.original_text)

                if is_footnote:
                    fn_p = doc.add_paragraph()
                    fn_p.paragraph_format.space_before = Pt(2)
                    fn_p.paragraph_format.space_after = Pt(4)
                    if bilingual:
                        en_fn = format_math_for_docx(p.original_text)
                        r1 = fn_p.add_run(en_fn + "\n")
                        r1.font.name = "Times New Roman"
                        r1.font.size = Pt(9)
                        r1.font.italic = True
                        r1.font.color.rgb = RGBColor(120, 130, 140)
                    r2 = fn_p.add_run(trans)
                    r2.font.name = "Times New Roman"
                    r2.font.size = Pt(9.5)
                    p_idx += 1
                    continue

                # Subheadings (h3, h4)
                if p.tag == 'h3':
                    h3_p = doc.add_paragraph()
                    h3_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    h3_p.paragraph_format.space_before = Pt(14)
                    h3_p.paragraph_format.space_after = Pt(4)
                    if bilingual:
                        en_h = format_math_for_docx(p.original_text)
                        r_en = h3_p.add_run(en_h + "\n")
                        r_en.font.name = "Times New Roman"
                        r_en.font.size = Pt(10)
                        r_en.font.italic = True
                        r_en.font.color.rgb = RGBColor(100, 116, 139)
                    r_vi = h3_p.add_run(trans)
                    r_vi.font.name = "Times New Roman"
                    r_vi.font.size = Pt(13)
                    r_vi.font.bold = True
                    r_vi.font.color.rgb = RGBColor(30, 41, 59)
                    p_idx += 1
                    continue
                elif p.tag == 'h4':
                    h4_p = doc.add_paragraph()
                    h4_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    h4_p.paragraph_format.space_before = Pt(10)
                    h4_p.paragraph_format.space_after = Pt(2)
                    if bilingual:
                        en_h = format_math_for_docx(p.original_text)
                        r_en = h4_p.add_run(en_h + "\n")
                        r_en.font.name = "Times New Roman"
                        r_en.font.size = Pt(9.5)
                        r_en.font.italic = True
                        r_en.font.color.rgb = RGBColor(100, 116, 139)
                    r_vi = h4_p.add_run(trans)
                    r_vi.font.name = "Times New Roman"
                    r_vi.font.size = Pt(11.5)
                    r_vi.font.bold = True
                    r_vi.font.color.rgb = RGBColor(71, 85, 105)
                    p_idx += 1
                    continue

                if bilingual:
                    # English original
                    en_text = format_math_for_docx(p.original_text)
                    en_p = doc.add_paragraph()
                    en_run = en_p.add_run(en_text)
                    en_run.font.name = "Times New Roman"
                    en_run.font.size = Pt(10)
                    en_run.font.italic = True
                    en_run.font.color.rgb = RGBColor(110, 120, 135)

                    # Vietnamese translation
                    vi_p = doc.add_paragraph()
                    vi_run = vi_p.add_run(trans)
                    vi_run.font.name = "Times New Roman"
                    vi_run.font.size = Pt(11.5)
                    vi_p.paragraph_format.space_after = Pt(8)
                else:
                    para = doc.add_paragraph()
                    run = para.add_run(trans)
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(12)
                    para.paragraph_format.line_spacing = 1.3
                    para.paragraph_format.space_after = Pt(6)

                p_idx += 1

            if not is_paper:
                doc.add_page_break()

        doc.save(output_path)
        return output_path

    @classmethod
    def export_html(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """Exports as a standalone, printable, elegant HTML reader with MathML and Vietnamese typography."""
        import base64
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        is_paper = is_academic_paper(project)
        chapters_html = []
        for chap in project.chapters:
            chap_title = normalize_text(chap.title)
            chap_body = []
            paras = chap.paragraphs
            p_idx = 0
            while p_idx < len(paras):
                p = paras[p_idx]

                # Handle image paragraph (embed base64 so HTML is 100% standalone and printable to PDF)
                if (p.tag == "img" or getattr(p, "image_path", "")) and p.image_path and os.path.exists(p.image_path):
                    b64 = ""
                    mime = "image/png" if p.image_path.lower().endswith(".png") else "image/jpeg"
                    try:
                        with open(p.image_path, "rb") as f_img:
                            b64 = base64.b64encode(f_img.read()).decode("utf-8")
                    except Exception:
                        pass

                    caption_para = None
                    if p_idx + 1 < len(paras) and is_caption_para(paras[p_idx + 1]):
                        caption_para = paras[p_idx + 1]

                    if b64:
                        img_html = f'<img src="data:{mime};base64,{b64}" alt="Minh họa / Bảng biểu" />'
                        if caption_para:
                            cap_orig = format_math_in_html(caption_para.original_text.strip())[0]
                            cap_trans_raw = caption_para.translated_text.strip() if caption_para.translated_text.strip() else caption_para.original_text.strip()
                            cap_trans = format_math_in_html(cap_trans_raw)[0]
                            is_table = bool(re.search(r'^(?:Table|Bảng)\b', caption_para.original_text, re.I) or re.search(r'^(?:Table|Bảng)\b', caption_para.translated_text, re.I) or 'tab' in p.id)

                            if bilingual:
                                en_lbl, en_content = format_caption_text(cap_orig)
                                vi_lbl, vi_content = format_caption_text(cap_trans)
                                cap_html = f'''<div class="caption-pair">
                                    <div class="caption-en"><span class="cap-badge en">EN</span> <strong>{en_lbl}</strong> {en_content}</div>
                                    <div class="caption-vi"><span class="cap-badge vi">VI</span> <strong>{vi_lbl}</strong> {vi_content}</div>
                                </div>'''
                            else:
                                lbl, content = format_caption_text(cap_trans)
                                if lbl:
                                    cap_html = f'<span class="caption-label">{lbl}</span> <span class="caption-content">{content}</span>'
                                else:
                                    cap_html = cap_trans

                            if is_table:
                                chap_body.append(f'''
                                <div class="academic-table-block" id="{p.id}">
                                    <div class="table-caption">{cap_html}</div>
                                    <div class="table-image-wrapper">{img_html}</div>
                                </div>''')
                            else:
                                chap_body.append(f'''
                                <figure class="academic-figure" id="{p.id}">
                                    <div class="figure-image-wrapper">{img_html}</div>
                                    <figcaption class="figure-caption">{cap_html}</figcaption>
                                </figure>''')
                            p_idx += 2
                            continue
                        else:
                            chap_body.append(f'''
                            <div class="figure-wrapper" style="text-align: center; margin: 24px auto;">
                                <div class="figure-image-wrapper">{img_html}</div>
                            </div>''')
                            p_idx += 1
                            continue

                # Standalone caption without image
                if is_caption_para(p):
                    trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                    trans_html, _ = format_math_in_html(trans)
                    if bilingual:
                        orig_html, _ = format_math_in_html(p.original_text)
                        en_lbl, en_content = format_caption_text(orig_html)
                        vi_lbl, vi_content = format_caption_text(trans_html)
                        chap_body.append(f'''
                        <div class="table-caption" style="margin: 16px 0;">
                            <div class="caption-pair">
                                <div class="caption-en"><span class="cap-badge en">EN</span> <strong>{en_lbl}</strong> {en_content}</div>
                                <div class="caption-vi"><span class="cap-badge vi">VI</span> <strong>{vi_lbl}</strong> {vi_content}</div>
                            </div>
                        </div>''')
                    else:
                        lbl, content = format_caption_text(trans_html)
                        if lbl:
                            chap_body.append(f'<div class="table-caption" style="margin: 16px 0;"><span class="caption-label">{lbl}</span> {content}</div>')
                        else:
                            chap_body.append(f'<div class="table-caption" style="margin: 16px 0;">{trans_html}</div>')
                    p_idx += 1
                    continue

                # Footnote paragraph (starts with ∗, †, ‡, *)
                is_footnote = p.original_text.strip().startswith(('∗', '†', '‡', '*'))
                trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                trans_html, _ = format_math_in_html(trans)

                if is_footnote:
                    if bilingual:
                        orig_html, _ = format_math_in_html(p.original_text)
                        chap_body.append(f'''
                        <div class="academic-footnote">
                            <div style="color: var(--muted-color); font-size: 0.88em; font-style: italic; margin-bottom: 3px;">{orig_html}</div>
                            <div style="font-size: 0.95em;">{trans_html}</div>
                        </div>''')
                    else:
                        chap_body.append(f'<div class="academic-footnote">{trans_html}</div>')
                    p_idx += 1
                    continue

                if bilingual:
                    orig_html, _ = format_math_in_html(p.original_text)
                    is_h = p.tag in ('h1', 'h2', 'h3', 'h4')
                    if is_h:
                        chap_body.append(f'''
                        <div class="heading-pair {p.tag}-pair" style="margin-top: 1.6em; margin-bottom: 0.6em;">
                            <div class="en-heading" style="color: var(--muted-color); font-size: 0.85em; font-style: italic;">{orig_html}</div>
                            <{p.tag} class="vi-heading" style="margin-top: 2px;">{trans_html}</{p.tag}>
                        </div>''')
                    else:
                        chap_body.append(f'''
                        <div class="para-pair">
                            <div class="en">{orig_html}</div>
                            <div class="vi">{trans_html}</div>
                        </div>''')
                else:
                    tag = p.tag if p.tag in ('h1', 'h2', 'h3', 'h4', 'blockquote') else 'p'
                    if trans_html.startswith('<div class="math-block'):
                        parts = trans_html.split('\n', 1)
                        if len(parts) == 2 and parts[1].strip():
                            chap_body.append(parts[0])
                            chap_body.append(f'<{tag}>{parts[1].strip()}</{tag}>')
                        else:
                            chap_body.append(trans_html)
                    else:
                        chap_body.append(f'<{tag}>{trans_html}</{tag}>')

                p_idx += 1

            # Chapter heading (left-aligned; suppress generic preamble title)
            if chap_title in ("Phần mở đầu / Tiêu đề", "Title", "Header"):
                h2_tag = ""
            else:
                h2_tag = f"<h2>{chap_title}</h2>"

            chapters_html.append(f'''
            <section class="chapter-section" id="{chap.id}">
                {h2_tag}
                <div class="chapter-content">
                    {"".join(chap_body)}
                </div>
            </section>
            ''')

        if is_paper:
            sub_text_html = "Bản dịch Song Ngữ Anh - Việt (Academic Edition)" if bilingual else "Bản dịch Học Thuật Tiếng Việt (AI Academic Edition)"
            section_margin_css = "margin-bottom: 48px;"
            page_break_css = "page-break-after: auto;"
        else:
            sub_text_html = "Bản dịch Song Ngữ Anh - Việt" if bilingual else "Bản dịch Tiếng Việt (AI Literary Translation)"
            section_margin_css = "margin-bottom: 80px;"
            page_break_css = "page-break-after: always;"

        full_html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{normalize_text(project.title)} - Bản Dịch</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #fcfbf9;
            --text-color: #1a202c;
            --accent-color: #2b6cb0;
            --muted-color: #64748b;
            --border-color: #e2e8f0;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #12141a;
                --text-color: #e2e8f0;
                --accent-color: #818cf8;
                --muted-color: #94a3b8;
                --border-color: #2d3748;
            }}
        }}
        body {{
            background: var(--bg-color);
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Times New Roman", "Palatino Linotype", Arial, sans-serif;
            line-height: 1.85;
            margin: 0;
            padding: 40px 20px;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
        }}
        .book-container {{
            max-width: 820px;
            margin: 0 auto;
        }}
        header.book-header {{
            text-align: center;
            padding: 40px 0 30px;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 40px;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        h1.book-title {{
            font-size: 2.3rem;
            margin-bottom: 12px;
            font-weight: 700;
            color: var(--text-color);
            line-height: 1.3;
        }}
        .book-author {{
            font-size: 1.15rem;
            color: var(--muted-color);
        }}
        .chapter-section {{
            {section_margin_css}
            {page_break_css}
        }}
        h2 {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 1.65rem;
            color: var(--accent-color);
            margin-top: 2.2em;
            margin-bottom: 0.8em;
            text-align: left;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border-color);
            letter-spacing: -0.01em;
            font-weight: 700;
        }}
        h3 {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 1.25rem;
            color: var(--text-color);
            margin-top: 1.8em;
            margin-bottom: 0.6em;
            font-weight: 700;
            text-align: left;
        }}
        h4 {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 1.08rem;
            color: var(--muted-color);
            margin-top: 1.4em;
            margin-bottom: 0.4em;
            font-weight: 600;
            text-align: left;
        }}
        p {{
            margin-bottom: 1.2em;
            text-indent: 1.8em;
            text-align: justify;
        }}
        .para-pair {{
            margin-bottom: 24px;
            padding: 12px 16px;
            background: rgba(125, 125, 125, 0.05);
            border-radius: 8px;
            border-left: 3px solid var(--accent-color);
        }}
        .para-pair .en {{
            color: var(--muted-color);
            font-size: 0.9em;
            font-style: italic;
            margin-bottom: 8px;
            text-indent: 0;
        }}
        .para-pair .vi {{
            font-size: 1.05em;
            text-indent: 0;
        }}
        .academic-figure {{
            margin: 32px auto;
            max-width: 100%;
            text-align: center;
            background: rgba(0, 0, 0, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
        }}
        @media (prefers-color-scheme: dark) {{
            .academic-figure, .academic-table-block {{
                background: rgba(255, 255, 255, 0.02);
            }}
        }}
        .figure-image-wrapper img, .table-image-wrapper img {{
            max-width: 98%;
            height: auto;
            border-radius: 4px;
            display: inline-block;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
        }}
        .figure-caption, .table-caption {{
            margin-top: 14px;
            font-size: 0.92rem;
            line-height: 1.55;
            color: var(--text-color);
            text-indent: 0;
            text-align: left;
            padding: 10px 14px;
            background: rgba(125, 125, 125, 0.05);
            border-radius: 6px;
        }}
        .academic-table-block {{
            margin: 32px auto;
            max-width: 100%;
            background: rgba(0, 0, 0, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
            text-align: center;
        }}
        .academic-table-block .table-caption {{
            margin-top: 0;
            margin-bottom: 14px;
        }}
        .caption-label {{
            font-weight: 700;
            color: var(--accent-color);
            margin-right: 6px;
        }}
        .caption-pair {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .caption-en {{
            font-size: 0.88rem;
            color: var(--muted-color);
            font-style: italic;
        }}
        .caption-vi {{
            font-size: 0.94rem;
            color: var(--text-color);
        }}
        .cap-badge {{
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            margin-right: 6px;
            vertical-align: middle;
            font-style: normal;
        }}
        .cap-badge.en {{
            background: rgba(100, 116, 139, 0.15);
            color: var(--muted-color);
        }}
        .cap-badge.vi {{
            background: rgba(43, 108, 176, 0.15);
            color: var(--accent-color);
        }}
        .academic-footnotes {{
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
            font-size: 0.88rem;
            color: var(--muted-color);
            line-height: 1.6;
        }}
        .academic-footnote {{
            margin-bottom: 8px;
            text-indent: 0;
            text-align: left;
            font-size: 0.88rem;
            color: var(--muted-color);
            padding: 6px 10px;
            background: rgba(125, 125, 125, 0.03);
            border-radius: 4px;
        }}
        .math-block {{
            text-align: center;
            margin: 1.4em 0;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.03);
            border-radius: 6px;
            overflow-x: auto;
        }}
        .math-equation {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .math-formula {{
            display: inline-block;
            margin: 0 auto;
        }}
        .eq-num {{
            float: right;
            color: var(--muted-color);
            font-size: 0.9em;
        }}
        math {{
            font-family: "Cambria Math", "Latin Modern Math", "STIX Two Math", serif;
            font-size: 1.05em;
        }}
        .math-fallback {{
            font-family: "Cambria Math", "Latin Modern Math", "Times New Roman", serif;
            font-style: italic;
        }}
        .math-inline-img {{
            display: inline-block;
            vertical-align: -0.22em;
            max-height: 1.45em;
            width: auto;
            height: auto;
        }}
        .math-display-img {{
            display: block;
            margin: 8px auto;
            max-width: 95%;
            max-height: 5.5em;
            width: auto;
            height: auto;
        }}
        @media (prefers-color-scheme: dark) {{
            .math-inline-img, .math-display-img {{
                filter: invert(1);
            }}
        }}
        @media print {{
            body {{ padding: 0; background: #fff; color: #000; }}
            .chapter-section {{ {page_break_css} }}
            .para-pair {{ background: transparent; border-left: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="book-container">
        <header class="book-header">
            <h1 class="book-title">{normalize_text(project.title)}</h1>
            <div class="book-author">Tác giả: {normalize_text(project.author)}</div>
            <div style="margin-top: 10px; color: var(--muted-color); font-size: 0.9em;">
                {sub_text_html}
            </div>
        </header>
        {"".join(chapters_html)}
    </div>
</body>
</html>'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        return output_path

    @classmethod
    def export_txt(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """Exports as plain UTF-8 text."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        lines = [
            f"=== {project.title} ===",
            f"Tác giả: {project.author}",
            "=" * 40,
            ""
        ]

        for chap in project.chapters:
            lines.append(f"\n\n--- {chap.title} ---\n")
            for p in chap.paragraphs:
                trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                if bilingual:
                    lines.append(f"[EN] {p.original_text}")
                    lines.append(f"[VI] {trans}\n")
                else:
                    lines.append(f"{trans}\n")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        return output_path
