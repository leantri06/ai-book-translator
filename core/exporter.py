"""
Multi-format Book Exporter (EPUB, Bilingual EPUB, DOCX, HTML, Markdown, TXT).
Preserves book styling, generates table of contents, and produces publication-ready files.
"""
import os
import re
import zipfile
import tempfile
import shutil
from typing import Optional, List
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from core.parser import BookProject, BookChapter, BookParagraph


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
        """Constructs a new EPUB book from scratch using ebooklib."""
        book = epub.EpubBook()
        book.set_identifier(f"ai-book-{project.id}")
        book.set_title(f"{project.title} (Bản Dịch Tiếng Việt)" if not bilingual else f"{project.title} (Song Ngữ Anh - Việt)")
        book.set_language('vi')
        book.add_author(project.author)

        epub_chapters = []
        toc = []

        # Basic styling
        style = '''
        body { font-family: Merriweather, Georgia, serif; line-height: 1.7; margin: 5%; color: #1a202c; }
        h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #2b6cb0; text-align: center; }
        p { text-indent: 1.5em; margin-bottom: 0.8em; text-align: justify; }
        .bilingual-en { color: #718096; font-size: 0.88em; font-style: italic; margin-bottom: 3px; text-indent: 0; }
        .bilingual-vi { color: #1a202c; margin-bottom: 12px; }
        '''
        default_css = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=style)
        book.add_item(default_css)

        for i, chap in enumerate(project.chapters):
            c_item = epub.EpubHtml(title=chap.title, file_name=f"chap_{i}.xhtml", lang="vi")
            c_item.add_item(default_css)

            html_parts = [f"<h2>{chap.title}</h2>"]
            for p in chap.paragraphs:
                if (p.tag == "img" or getattr(p, "image_path", "")) and p.image_path and os.path.exists(p.image_path):
                    img_filename = f"img_{os.path.basename(p.image_path)}"
                    try:
                        with open(p.image_path, "rb") as f_img:
                            epub_img = epub.EpubItem(
                                uid=f"img_{i}_{p.id}",
                                file_name=f"images/{img_filename}",
                                media_type="image/png" if p.image_path.lower().endswith(".png") else "image/jpeg",
                                content=f_img.read()
                            )
                            book.add_item(epub_img)
                            html_parts.append(f'<div style="text-align: center; margin: 18px 0;"><img src="images/{img_filename}" style="max-width: 100%; height: auto;" /></div>')
                    except Exception:
                        pass
                    continue

                trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                if bilingual:
                    html_parts.append(f'<div class="bilingual-en">{p.original_text}</div>')
                    html_parts.append(f'<p class="bilingual-vi">{trans}</p>')
                else:
                    tag = p.tag if p.tag in ('h1', 'h2', 'h3', 'blockquote') else 'p'
                    html_parts.append(f'<{tag}>{trans}</{tag}>')

            c_item.content = f"<html><body>{''.join(html_parts)}</body></html>".encode('utf-8')
            book.add_item(c_item)
            epub_chapters.append(c_item)
            toc.append(c_item)

        book.toc = tuple(toc)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + epub_chapters

        epub.write_epub(output_path, book)
        return output_path

    @classmethod
    def export_docx(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """Exports book as a polished Microsoft Word (.docx) document."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = docx.Document()

        # Title Page
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_p.add_run(project.title)
        run.font.size = Pt(26)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 41, 59)

        subtitle_p = doc.add_paragraph()
        subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = subtitle_p.add_run("Bản dịch Tiếng Việt (AI Literary Edition)" if not bilingual else "Bản dịch Song Ngữ Anh - Việt")
        sub_run.font.size = Pt(14)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 116, 139)

        author_p = doc.add_paragraph()
        author_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_run = author_p.add_run(f"Tác giả: {project.author}")
        author_run.font.size = Pt(12)
        doc.add_page_break()

        for chap in project.chapters:
            # Chapter heading
            heading = doc.add_heading(chap.title, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

            for p in chap.paragraphs:
                # Handle image paragraph
                if (p.tag == "img" or getattr(p, "image_path", "")) and p.image_path and os.path.exists(p.image_path):
                    try:
                        p_img = doc.add_paragraph()
                        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_img.paragraph_format.space_before = Pt(14)
                        p_img.paragraph_format.space_after = Pt(6)
                        p_img.add_run().add_picture(p.image_path, width=Inches(5.5))
                    except Exception:
                        pass
                    continue

                trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                if bilingual:
                    # English original
                    en_p = doc.add_paragraph()
                    en_run = en_p.add_run(p.original_text)
                    en_run.font.size = Pt(10)
                    en_run.font.italic = True
                    en_run.font.color.rgb = RGBColor(110, 120, 135)

                    # Vietnamese translation
                    vi_p = doc.add_paragraph()
                    vi_run = vi_p.add_run(trans)
                    vi_run.font.size = Pt(11.5)
                    vi_p.paragraph_format.space_after = Pt(8)
                else:
                    para = doc.add_paragraph()
                    run = para.add_run(trans)
                    run.font.size = Pt(12)
                    para.paragraph_format.line_spacing = 1.3
                    para.paragraph_format.space_after = Pt(6)

            doc.add_page_break()

        doc.save(output_path)
        return output_path

    @classmethod
    def export_html(cls, project: BookProject, output_path: str, bilingual: bool = False) -> str:
        """Exports as a standalone, printable, elegant HTML reader (can be printed to PDF directly)."""
        import base64
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        chapters_html = []
        for chap in project.chapters:
            chap_body = []
            for p in chap.paragraphs:
                # Handle image paragraph (embed base64 so HTML is 100% standalone and printable to PDF)
                if (p.tag == "img" or getattr(p, "image_path", "")) and p.image_path and os.path.exists(p.image_path):
                    try:
                        with open(p.image_path, "rb") as f_img:
                            b64 = base64.b64encode(f_img.read()).decode("utf-8")
                        mime = "image/png" if p.image_path.lower().endswith(".png") else "image/jpeg"
                        chap_body.append(f'''
                        <div class="figure-wrapper" style="text-align: center; margin: 24px auto;">
                            <img src="data:{mime};base64,{b64}" style="max-width: 95%; height: auto; border-radius: 6px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);" />
                        </div>''')
                    except Exception:
                        pass
                    continue

                trans = p.translated_text.strip() if p.translated_text.strip() else p.original_text
                if bilingual:
                    chap_body.append(f'''
                    <div class="para-pair">
                        <div class="en">{p.original_text}</div>
                        <div class="vi">{trans}</div>
                    </div>''')
                else:
                    tag = p.tag if p.tag in ('h1', 'h2', 'h3', 'blockquote') else 'p'
                    chap_body.append(f'<{tag}>{trans}</{tag}>')

            chapters_html.append(f'''
            <section class="chapter-section" id="{chap.id}">
                <h2>{chap.title}</h2>
                <div class="chapter-content">
                    {"".join(chap_body)}
                </div>
            </section>
            ''')

        full_html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project.title} - Bản Dịch</title>
    <link href="https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;1,300;1,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #fcfbf9;
            --text-color: #24292f;
            --accent-color: #4f46e5;
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
            font-family: 'Merriweather', Georgia, serif;
            line-height: 1.85;
            margin: 0;
            padding: 40px 20px;
        }}
        .book-container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        header.book-header {{
            text-align: center;
            padding: 60px 0 40px;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 60px;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        h1.book-title {{
            font-size: 2.5rem;
            margin-bottom: 12px;
            font-weight: 700;
        }}
        .book-author {{
            font-size: 1.2rem;
            color: var(--muted-color);
        }}
        .chapter-section {{
            margin-bottom: 80px;
            page-break-after: always;
        }}
        h2 {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.8rem;
            color: var(--accent-color);
            margin-bottom: 30px;
            text-align: center;
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
        }}
        .para-pair .vi {{
            font-size: 1.05em;
        }}
        @media print {{
            body {{ padding: 0; background: #fff; color: #000; }}
            .chapter-section {{ page-break-after: always; }}
            .para-pair {{ background: transparent; border-left: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="book-container">
        <header class="book-header">
            <h1 class="book-title">{project.title}</h1>
            <div class="book-author">Tác giả: {project.author}</div>
            <div style="margin-top: 10px; color: var(--muted-color); font-size: 0.9em;">
                {"Bản dịch Song Ngữ Anh - Việt" if bilingual else "Bản dịch Tiếng Việt (AI Literary Translation)"}
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
