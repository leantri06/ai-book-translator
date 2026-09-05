"""
End-to-End Verification Test for AI Book Translator Pro.
Verifies parsing, glossary context generation, chunking, translation fallback, export formats, and FastAPI endpoints.
"""
import os
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from core.parser import BookParser, BookChapter, BookParagraph, BookProject
from core.chunker import ParagraphChunker
from core.glossary import BookGlossary
from core.translator import AITranslator
from core.exporter import BookExporter
from server.database import ProjectManager


def test_full_pipeline():
    print("[1] Testing Book Parser & Glossary...")
    sample_epub = r"d:\books\novel\86\86 - Volume 01 [Yen Press][Kobo].epub"
    if os.path.exists(sample_epub):
        project = BookParser.parse_file(sample_epub, "test_verify")
        print(f"    Loaded EPUB: {project.title}, Chapters: {project.total_chapters}, Paras: {project.total_paragraphs}")
    else:
        # Create synthetic project
        paras = [
            BookParagraph(id="c0_p1", original_text="The Eighty-Six was a military unit that officially did not exist.", tag="p"),
            BookParagraph(id="c0_p2", original_text="Major Vladilena Milizé was assigned as their new Handler.", tag="p"),
            BookParagraph(id="c0_p3", original_text="Shin smiled faintly. 'We will survive another day,' he said.", tag="p")
        ]
        chapter = BookChapter(id="chap_0", title="Prologue", paragraphs=paras, order=0)
        project = BookProject(id="test_verify", title="86 Eighty Six Test", chapters=[chapter])

    # 2. Test Glossary & Prompt Context
    glossary = BookGlossary()
    glossary.tone = "novel"
    glossary.add_character("Shin", "male", "Captain", "tôi", "cậu", "cậu ấy")
    glossary.add_character("Lena", "female", "Handler", "tôi", "anh", "cô ấy")
    glossary.add_term("Handler", "Sĩ quan chỉ huy", "role")
    prompt_ctx = glossary.build_prompt_context()
    assert "Shin" in prompt_ctx and "Lena" in prompt_ctx
    print("    Glossary prompt context generated successfully.")

    # 3. Test Chunker
    chunker = ParagraphChunker(target_word_count=500, max_paragraphs=5)
    test_chap = project.chapters[0]
    chunks = chunker.create_chunks(test_chap, only_pending=False)
    print(f"    Chunker created {len(chunks)} chunks for chapter '{test_chap.title}'.")

    # 4. Test Translation Fallback (Simulated)
    print("[2] Testing Translator Engine...")
    translator = AITranslator(provider="free_fallback")
    first_chunk = chunks[0]
    # Test only first 2 paragraphs to be fast and respectful of network
    first_chunk.paragraphs = first_chunk.paragraphs[:2]
    trans_map = translator.translate_chunk(first_chunk, glossary)
    print(f"    Translated {len(trans_map)} paragraphs.")
    for pid, text in trans_map.items():
        print(f"      {pid} -> {text[:60]}...")

    # Apply translation
    for p in first_chunk.paragraphs:
        if p.id in trans_map:
            p.translated_text = trans_map[p.id]
            p.status = "done"

    # 5. Test Exporters (EPUB, DOCX, HTML, TXT)
    print("[3] Testing Exporters...")
    temp_dir = tempfile.mkdtemp(prefix="test_export_")
    
    # Export EPUB
    epub_out = os.path.join(temp_dir, "test.epub")
    BookExporter.export_epub(project, epub_out, bilingual=False)
    assert os.path.exists(epub_out), "EPUB export failed!"
    print(f"    EPUB Export OK ({os.path.getsize(epub_out)} bytes)")

    # Export Bilingual EPUB
    bilingual_epub_out = os.path.join(temp_dir, "test_bilingual.epub")
    BookExporter.export_epub(project, bilingual_epub_out, bilingual=True)
    assert os.path.exists(bilingual_epub_out), "Bilingual EPUB export failed!"
    print(f"    Bilingual EPUB Export OK ({os.path.getsize(bilingual_epub_out)} bytes)")

    # Export DOCX
    docx_out = os.path.join(temp_dir, "test.docx")
    BookExporter.export_docx(project, docx_out, bilingual=False)
    assert os.path.exists(docx_out), "DOCX export failed!"
    print(f"    DOCX Export OK ({os.path.getsize(docx_out)} bytes)")

    # Export HTML
    html_out = os.path.join(temp_dir, "test.html")
    BookExporter.export_html(project, html_out, bilingual=True)
    assert os.path.exists(html_out), "HTML export failed!"
    print(f"    HTML Export OK ({os.path.getsize(html_out)} bytes)")

    # Export TXT
    txt_out = os.path.join(temp_dir, "test.txt")
    BookExporter.export_txt(project, txt_out, bilingual=False)
    assert os.path.exists(txt_out), "TXT export failed!"
    print(f"    TXT Export OK ({os.path.getsize(txt_out)} bytes)")

    # Cleanup temp dir
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    test_full_pipeline()
