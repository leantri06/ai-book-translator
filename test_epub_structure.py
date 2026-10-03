"""
Tests for core.epub_structure — synthetic ebooklib EPUBs.

No network, no disk EPUB files.  All test EPUBs are built in memory with
ebooklib and written to a temporary directory.

Coverage:
  1. Spine ordering (manifest ≠ spine)
  2. Anchor-based multi-chapter splitting within one XHTML
  3. TOC hierarchy (children are NOT split points)
  4. Duplicate text locator (same text appears in two chapters)
  5. Nested markup (bold/italic inside paragraphs — no word concatenation)
  6. Malformed anchor fallback
  7. Single-character and scene-break preservation
  8. Heading-level fallback when no TOC
  9. Preamble preservation
  10. Non-linear spine items excluded
  11. EpubNav / nav epub:type=toc exclusion
  12. epub_text_elements shared helper
  13. source_doc and source_element_index fields
  14. Consecutive spine docs joined to same chapter
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

# Ensure project root is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bs4 import BeautifulSoup
from ebooklib import epub

from core.epub_structure import parse_epub_structure, epub_text_elements


# ---------------------------------------------------------------------------
#  Helpers for building synthetic EPUBs
# ---------------------------------------------------------------------------

def _make_xhtml(body_html: str, title: str = "Test") -> str:
    """Wrap body HTML in a minimal XHTML document."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        f'<head><title>{title}</title></head>\n'
        f'<body>\n{body_html}\n</body>\n</html>'
    )


def _add_chapter(book: epub.EpubBook, file_name: str, item_id: str,
                 body_html: str, title: str = "Test") -> epub.EpubHtml:
    """Create an EpubHtml chapter, add it to the book, and return it."""
    ch = epub.EpubHtml(title=title, file_name=file_name, lang='en')
    ch.id = item_id
    ch.set_content(_make_xhtml(body_html, title).encode('utf-8'))
    book.add_item(ch)
    return ch


def _write_epub(book: epub.EpubBook, tmp_dir: str, name: str = "test.epub") -> str:
    """Write the book to *tmp_dir* and return the file path."""
    path = os.path.join(tmp_dir, name)
    epub.write_epub(path, book)
    return path


def _build_simple_book(tmp_dir: str) -> str:
    """Build a minimal two-chapter EPUB and return its path."""
    book = epub.EpubBook()
    book.set_identifier('test-simple')
    book.set_title('Simple Book')
    book.set_language('en')
    book.add_author('Test Author')

    ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                       '<h1>Chapter One</h1><p>First paragraph.</p><p>Second paragraph.</p>')
    ch2 = _add_chapter(book, 'ch02.xhtml', 'ch02',
                       '<h1>Chapter Two</h1><p>Third paragraph.</p>')

    book.toc = [
        epub.Link('ch01.xhtml', 'Chapter One', 'toc_ch01'),
        epub.Link('ch02.xhtml', 'Chapter Two', 'toc_ch02'),
    ]
    book.spine = [('ch01', 'yes'), ('ch02', 'yes')]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    return _write_epub(book, tmp_dir)


# ---------------------------------------------------------------------------
#  Test cases
# ---------------------------------------------------------------------------

class TestSpineOrder(unittest.TestCase):
    """Spine ordering takes precedence over manifest order."""

    def test_spine_not_manifest_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-order')
            book.set_title('Order Test')
            book.set_language('en')

            # Add in manifest order: A, B, C
            chA = _add_chapter(book, 'a.xhtml', 'a',
                               '<h1>Alpha</h1><p>Content A.</p>')
            chB = _add_chapter(book, 'b.xhtml', 'b',
                               '<h1>Beta</h1><p>Content B.</p>')
            chC = _add_chapter(book, 'c.xhtml', 'c',
                               '<h1>Gamma</h1><p>Content C.</p>')

            # Spine order: C, A, B  (different from manifest)
            book.spine = [('c', 'yes'), ('a', 'yes'), ('b', 'yes')]
            book.toc = [
                epub.Link('c.xhtml', 'Gamma', 'g'),
                epub.Link('a.xhtml', 'Alpha', 'a'),
                epub.Link('b.xhtml', 'Beta', 'b'),
            ]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'order_test')

            self.assertEqual(len(project.chapters), 3)
            self.assertEqual(project.chapters[0].title, 'Gamma')
            self.assertEqual(project.chapters[1].title, 'Alpha')
            self.assertEqual(project.chapters[2].title, 'Beta')


class TestAnchorMultiChapter(unittest.TestCase):
    """Multiple chapter anchors within a single XHTML file."""

    def test_split_on_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-anchors')
            book.set_title('Anchor Test')
            book.set_language('en')

            body = (
                '<h1 id="ch1">Chapter 1</h1>'
                '<p>Para in chapter 1.</p>'
                '<h1 id="ch2">Chapter 2</h1>'
                '<p>Para in chapter 2.</p>'
                '<p>Another para in chapter 2.</p>'
                '<h1 id="ch3">Chapter 3</h1>'
                '<p>Para in chapter 3.</p>'
            )
            ch = _add_chapter(book, 'content.xhtml', 'content', body)

            book.toc = [
                epub.Link('content.xhtml#ch1', 'Chapter 1', 'toc1'),
                epub.Link('content.xhtml#ch2', 'Chapter 2', 'toc2'),
                epub.Link('content.xhtml#ch3', 'Chapter 3', 'toc3'),
            ]
            book.spine = [('content', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'anchor_test')

            self.assertEqual(len(project.chapters), 3)
            self.assertEqual(project.chapters[0].title, 'Chapter 1')
            self.assertEqual(project.chapters[1].title, 'Chapter 2')
            self.assertEqual(project.chapters[2].title, 'Chapter 3')

            # Chapter 1: heading + 1 para
            ch1_texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('Chapter 1', ch1_texts)
            self.assertIn('Para in chapter 1.', ch1_texts)

            # Chapter 2: heading + 2 paras
            ch2_texts = [p.original_text for p in project.chapters[1].paragraphs]
            self.assertIn('Chapter 2', ch2_texts)
            self.assertIn('Para in chapter 2.', ch2_texts)
            self.assertIn('Another para in chapter 2.', ch2_texts)

            # Chapter 3: heading + 1 para
            ch3_texts = [p.original_text for p in project.chapters[2].paragraphs]
            self.assertIn('Chapter 3', ch3_texts)
            self.assertIn('Para in chapter 3.', ch3_texts)


class TestTocHierarchy(unittest.TestCase):
    """Child TOC entries (sub-headings) do NOT create chapter splits."""

    def test_children_not_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-hierarchy')
            book.set_title('Hierarchy Test')
            book.set_language('en')

            body1 = (
                '<h1 id="main">Main Chapter</h1>'
                '<p>Intro paragraph.</p>'
                '<h2 id="sub1">Sub-section 1</h2>'
                '<p>Sub-section 1 content.</p>'
                '<h2 id="sub2">Sub-section 2</h2>'
                '<p>Sub-section 2 content.</p>'
            )
            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01', body1)

            body2 = '<h1 id="ch2">Next Chapter</h1><p>Next content.</p>'
            ch2 = _add_chapter(book, 'ch02.xhtml', 'ch02', body2)

            # Nested TOC: Main Chapter has sub-sections as children
            book.toc = [
                (epub.Section('Main Chapter', 'ch01.xhtml#main'), [
                    epub.Link('ch01.xhtml#sub1', 'Sub-section 1', 's1'),
                    epub.Link('ch01.xhtml#sub2', 'Sub-section 2', 's2'),
                ]),
                epub.Link('ch02.xhtml#ch2', 'Next Chapter', 'toc_ch2'),
            ]
            book.spine = [('ch01', 'yes'), ('ch02', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'hierarchy_test')

            # Only 2 chapters, not 4 — sub-sections stay inside Main Chapter
            self.assertEqual(len(project.chapters), 2)
            self.assertEqual(project.chapters[0].title, 'Main Chapter')
            self.assertEqual(project.chapters[1].title, 'Next Chapter')

            # Main Chapter should contain all sub-section content
            ch1_texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('Sub-section 1', ch1_texts)
            self.assertIn('Sub-section 1 content.', ch1_texts)
            self.assertIn('Sub-section 2', ch1_texts)
            self.assertIn('Sub-section 2 content.', ch1_texts)


class TestDuplicateTextLocator(unittest.TestCase):
    """Same text appearing in different chapters should not cross-contaminate."""

    def test_duplicate_text_separate_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-dup')
            book.set_title('Duplicate Test')
            book.set_language('en')

            # Same paragraph text in two different XHTML files
            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Chapter 1</h1><p>The rain fell softly.</p>')
            ch2 = _add_chapter(book, 'ch02.xhtml', 'ch02',
                               '<h1>Chapter 2</h1><p>The rain fell softly.</p>')

            book.toc = [
                epub.Link('ch01.xhtml', 'Chapter 1', 'c1'),
                epub.Link('ch02.xhtml', 'Chapter 2', 'c2'),
            ]
            book.spine = [('ch01', 'yes'), ('ch02', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'dup_test')

            self.assertEqual(len(project.chapters), 2)
            # Each chapter has its own copy of the duplicated text
            for ch in project.chapters:
                texts = [p.original_text for p in ch.paragraphs]
                self.assertIn('The rain fell softly.', texts)

            # source_doc fields must differ
            p1 = [p for p in project.chapters[0].paragraphs
                  if p.original_text == 'The rain fell softly.'][0]
            p2 = [p for p in project.chapters[1].paragraphs
                  if p.original_text == 'The rain fell softly.'][0]
            self.assertNotEqual(p1.source_doc, p2.source_doc)


class TestNestedMarkup(unittest.TestCase):
    """Bold, italic, spans inside paragraphs — text must not be concatenated
    word-by-word (no missing spaces from inline elements)."""

    def test_inline_formatting_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-nested')
            book.set_title('Nested Markup')
            book.set_language('en')

            body = (
                '<h1>Chapter</h1>'
                '<p>She said <em>hello</em> and <strong>smiled</strong> warmly.</p>'
                '<p><span class="sc">Lord Byron</span> wrote poetry.</p>'
            )
            ch = _add_chapter(book, 'ch.xhtml', 'ch1', body)
            book.toc = [epub.Link('ch.xhtml', 'Chapter', 'c1')]
            book.spine = [('ch1', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'nested_test')

            texts = [p.original_text for p in project.chapters[0].paragraphs]
            # get_text(strip=True) on "She said <em>hello</em> and ..."
            # produces "She saidhelloandsmiled warmly." in some parsers.
            # Our requirement is to NOT concatenate inline words.
            # BeautifulSoup's get_text(strip=True) does strip whitespace
            # but preserves space between text nodes in most cases.
            # We verify the key content is present.
            combined = ' '.join(texts)
            self.assertIn('hello', combined)
            self.assertIn('smiled', combined)
            self.assertIn('Lord Byron', combined)


class TestMalformedAnchorFallback(unittest.TestCase):
    """When a TOC anchor doesn't exist in the document, fall back to
    document start with a warning."""

    def test_bad_anchor_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-badfrag')
            book.set_title('Bad Anchor')
            book.set_language('en')

            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Chapter 1</h1><p>Content here.</p>')

            # Reference a non-existent anchor
            book.toc = [
                epub.Link('ch01.xhtml#nonexistent', 'Chapter 1', 'c1'),
            ]
            book.spine = [('ch01', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'badfrag_test')

            # Content should still be parsed (fallback to doc start)
            self.assertTrue(len(project.chapters) >= 1)
            texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('Content here.', texts)

            # Warning should mention the bad anchor
            self.assertTrue(any('nonexistent' in w for w in project.structure_warnings))


class TestSceneBreakPreservation(unittest.TestCase):
    """Scene breaks (<hr> and separator <p>) are preserved, not discarded."""

    def test_hr_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-hr')
            book.set_title('Scene Break Test')
            book.set_language('en')

            body = (
                '<h1>Chapter</h1>'
                '<p>Before the break.</p>'
                '<hr/>'
                '<p>After the break.</p>'
                '<p>* * *</p>'
                '<p>After star break.</p>'
            )
            ch = _add_chapter(book, 'ch.xhtml', 'ch1', body)
            book.toc = [epub.Link('ch.xhtml', 'Chapter', 'c1')]
            book.spine = [('ch1', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'hr_test')

            tags = [p.tag for p in project.chapters[0].paragraphs]
            texts = [p.original_text for p in project.chapters[0].paragraphs]

            # hr tags should be present
            self.assertIn('hr', tags)
            # "* * *" should be present as scene break
            self.assertIn('* * *', texts)
            # Regular content preserved
            self.assertIn('Before the break.', texts)
            self.assertIn('After the break.', texts)
            self.assertIn('After star break.', texts)


class TestHeadingFallback(unittest.TestCase):
    """When there is no TOC, fall back to the strongest heading level only.
    If h1 is present, don't also split on h2."""

    def test_fallback_strongest_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-fallback')
            book.set_title('Fallback Test')
            book.set_language('en')

            body = (
                '<h1>Part One</h1>'
                '<p>Intro.</p>'
                '<h2>Section A</h2>'
                '<p>Section A content.</p>'
                '<h1>Part Two</h1>'
                '<p>Part two content.</p>'
                '<h2>Section B</h2>'
                '<p>Section B content.</p>'
            )
            ch = _add_chapter(book, 'content.xhtml', 'content', body)

            # NO TOC at all
            book.toc = []
            book.spine = [('content', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'fallback_test')

            # Should split on h1 only → 2 chapters (Part One, Part Two)
            # not 4 (which would happen if it also split on h2)
            self.assertEqual(len(project.chapters), 2)
            self.assertEqual(project.chapters[0].title, 'Part One')
            self.assertEqual(project.chapters[1].title, 'Part Two')

            # h2 content should be inside respective chapters, not lost
            ch1_texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('Section A', ch1_texts)
            self.assertIn('Section A content.', ch1_texts)

            # Warnings should indicate fallback
            self.assertTrue(any('heading' in w.lower() or 'fallback' in w.lower()
                                for w in project.structure_warnings))


class TestPreamblePreservation(unittest.TestCase):
    """Content before the first TOC chapter is kept in a preamble chapter."""

    def test_preamble_not_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-preamble')
            book.set_title('Preamble Test')
            book.set_language('en')

            # Preamble doc (not in TOC)
            pre = _add_chapter(book, 'preface.xhtml', 'preface',
                               '<p>This is the preface.</p><p>Important info here.</p>')

            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Chapter 1</h1><p>Chapter content.</p>')

            book.toc = [epub.Link('ch01.xhtml', 'Chapter 1', 'c1')]
            # Spine includes preface before chapter
            book.spine = [('preface', 'yes'), ('ch01', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'preamble_test')

            # Should have 2 items: preamble + Chapter 1
            self.assertEqual(len(project.chapters), 2)
            self.assertEqual(project.chapters[0].title, 'Preamble')

            pre_texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('This is the preface.', pre_texts)
            self.assertIn('Important info here.', pre_texts)


class TestNonLinearExcluded(unittest.TestCase):
    """Non-linear spine items (linear='no') are excluded."""

    def test_nonlinear_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-nonlinear')
            book.set_title('NonLinear Test')
            book.set_language('en')

            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Real Chapter</h1><p>Actual content.</p>')
            notes = _add_chapter(book, 'notes.xhtml', 'notes',
                                 '<h1>Endnotes</h1><p>Note 1.</p>')

            book.toc = [epub.Link('ch01.xhtml', 'Real Chapter', 'c1')]
            book.spine = [('ch01', 'yes'), ('notes', 'no')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'nonlinear_test')

            # Only 1 chapter — the non-linear notes are excluded
            self.assertEqual(len(project.chapters), 1)
            all_texts = [p.original_text for ch in project.chapters for p in ch.paragraphs]
            self.assertNotIn('Note 1.', all_texts)


class TestNavDocExcluded(unittest.TestCase):
    """EpubNav and nav epub:type=toc documents are not treated as content."""

    def test_nav_not_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-nav')
            book.set_title('Nav Exclusion Test')
            book.set_language('en')

            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Chapter</h1><p>Content.</p>')

            book.toc = [epub.Link('ch01.xhtml', 'Chapter', 'c1')]
            book.spine = [('ch01', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'nav_test')

            # The nav document should not appear as a chapter
            for ch in project.chapters:
                self.assertNotIn('Table of Contents', ch.title)


class TestEpubTextElementsHelper(unittest.TestCase):
    """The epub_text_elements() helper filters container divs correctly."""

    def test_container_div_filtered(self):
        html = '''
        <html><body>
          <div class="wrapper">
            <p>Inner paragraph.</p>
            <p>Second inner.</p>
          </div>
          <div class="leaf">Leaf div content.</div>
          <p>Top-level paragraph.</p>
        </body></html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        elements = epub_text_elements(soup)

        texts = [el.get_text(strip=True) for el in elements]
        # The wrapper div should be filtered out (contains <p>)
        # But its children <p> elements should be present
        self.assertIn('Inner paragraph.', texts)
        self.assertIn('Second inner.', texts)
        self.assertIn('Leaf div content.', texts)
        self.assertIn('Top-level paragraph.', texts)

        # The wrapper div text should NOT appear as a separate element
        # (it would show as "Inner paragraph.Second inner." if not filtered)
        tag_names = [el.name for el in elements]
        # Count — should not have the wrapper div
        div_elements = [el for el in elements if el.name == 'div']
        self.assertEqual(len(div_elements), 1)  # Only the leaf div


class TestSourceLocatorFields(unittest.TestCase):
    """source_doc and source_element_index are set on all paragraphs."""

    def test_source_fields_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_simple_book(tmp)
            project = parse_epub_structure(path, 'locator_test')

            for ch in project.chapters:
                for p in ch.paragraphs:
                    self.assertIsInstance(p.source_doc, str)
                    self.assertTrue(len(p.source_doc) > 0,
                                    f"source_doc empty for {p.id}")
                    self.assertIsInstance(p.source_element_index, int)
                    self.assertGreaterEqual(p.source_element_index, 0,
                                            f"source_element_index < 0 for {p.id}")


class TestConsecutiveSpineDocsJoined(unittest.TestCase):
    """Consecutive spine docs with no new chapter boundary are joined."""

    def test_joined_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-join')
            book.set_title('Join Test')
            book.set_language('en')

            # Chapter 1 spans two XHTML files
            ch1a = _add_chapter(book, 'ch01a.xhtml', 'ch01a',
                                '<p>Chapter 1 part A.</p>')
            ch1b = _add_chapter(book, 'ch01b.xhtml', 'ch01b',
                                '<p>Chapter 1 part B.</p>')
            ch2 = _add_chapter(book, 'ch02.xhtml', 'ch02',
                               '<h1>Chapter 2</h1><p>Chapter 2 content.</p>')

            # TOC only references ch01a and ch02 — ch01b has no TOC entry
            book.toc = [
                epub.Link('ch01a.xhtml', 'Chapter 1', 'c1'),
                epub.Link('ch02.xhtml', 'Chapter 2', 'c2'),
            ]
            book.spine = [('ch01a', 'yes'), ('ch01b', 'yes'), ('ch02', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'join_test')

            self.assertEqual(len(project.chapters), 2)
            self.assertEqual(project.chapters[0].title, 'Chapter 1')

            # Chapter 1 should contain content from both ch01a and ch01b
            ch1_texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('Chapter 1 part A.', ch1_texts)
            self.assertIn('Chapter 1 part B.', ch1_texts)

            # source_doc should differ for the two parts
            docs = set(p.source_doc for p in project.chapters[0].paragraphs)
            self.assertTrue(len(docs) >= 2, f"Expected multiple source docs, got {docs}")


class TestDocumentTypeAndWarnings(unittest.TestCase):
    """document_type='novel' and structure_warnings are set."""

    def test_metadata_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_simple_book(tmp)
            project = parse_epub_structure(path, 'meta_test')

            self.assertEqual(project.document_type, 'novel')
            self.assertIsInstance(project.structure_warnings, list)
            self.assertEqual(project.source_format, 'epub')
            self.assertEqual(project.title, 'Simple Book')
            self.assertEqual(project.author, 'Test Author')


class TestDivBlockquoteLiNoDuplication(unittest.TestCase):
    """Nested div/blockquote/li should not cause text duplication."""

    def test_no_duplicate_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-nodup')
            book.set_title('NoDup Test')
            book.set_language('en')

            body = (
                '<h1>Chapter</h1>'
                '<blockquote><p>Quoted paragraph inside blockquote.</p></blockquote>'
                '<div><p>Paragraph inside div wrapper.</p></div>'
                '<li>List item text.</li>'
            )
            ch = _add_chapter(book, 'ch.xhtml', 'ch1', body)
            book.toc = [epub.Link('ch.xhtml', 'Chapter', 'c1')]
            book.spine = [('ch1', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'nodup_test')

            texts = [p.original_text for p in project.chapters[0].paragraphs]
            # "Quoted paragraph inside blockquote." should appear exactly once
            self.assertEqual(texts.count('Quoted paragraph inside blockquote.'), 1)
            # "Paragraph inside div wrapper." should appear exactly once
            self.assertEqual(texts.count('Paragraph inside div wrapper.'), 1)
            # "List item text." should appear exactly once
            self.assertEqual(texts.count('List item text.'), 1)


class TestNoContentDropped(unittest.TestCase):
    """Verify no real content is silently dropped."""

    def test_all_paragraphs_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-nodrop')
            book.set_title('No Drop')
            book.set_language('en')

            body = (
                '<h1>Title</h1>'
                '<p>First real paragraph with important text.</p>'
                '<p>Second paragraph also important.</p>'
                '<p>Third paragraph should not be lost.</p>'
                '<hr/>'
                '<p>Fourth after scene break.</p>'
            )
            ch = _add_chapter(book, 'ch.xhtml', 'ch1', body)
            book.toc = [epub.Link('ch.xhtml', 'Title', 'c1')]
            book.spine = [('ch1', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'nodrop_test')

            texts = [p.original_text for p in project.chapters[0].paragraphs]
            self.assertIn('First real paragraph with important text.', texts)
            self.assertIn('Second paragraph also important.', texts)
            self.assertIn('Third paragraph should not be lost.', texts)
            self.assertIn('Fourth after scene break.', texts)


if __name__ == '__main__':
    unittest.main()


# =========================================================================
#  Regression tests — added after review
# =========================================================================

class TestInlineTextNotConcatenated(unittest.TestCase):
    """get_text(strip=True) concatenates 'Hello <b>world</b> today' into
    'Helloworldtoday'.  Our extractor must preserve inter-element spaces."""

    def test_bold_italic_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-inline')
            book.set_title('Inline Test')
            book.set_language('en')

            body = (
                '<h1>Chapter</h1>'
                '<p>Hello <b>world</b> today</p>'
                '<p>She said <em>hello</em> and <strong>smiled</strong> warmly.</p>'
            )
            ch = _add_chapter(book, 'ch.xhtml', 'ch1', body)
            book.toc = [epub.Link('ch.xhtml', 'Chapter', 'c1')]
            book.spine = [('ch1', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'inline_test')
            texts = [p.original_text for p in project.chapters[0].paragraphs]

            self.assertIn('Hello world today', texts)
            self.assertIn('She said hello and smiled warmly.', texts)
            # Must NOT contain the concatenated form
            for t in texts:
                self.assertNotIn('Helloworldtoday', t)
                self.assertNotIn('saidhello', t)


class TestBrTagHandling(unittest.TestCase):
    """<br> tags inside paragraphs should produce a space, not concatenate."""

    def test_br_produces_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-br')
            book.set_title('BR Test')
            book.set_language('en')

            body = (
                '<h1>Chapter</h1>'
                '<p>Line one<br/>Line two</p>'
                '<p>Before<br/><br/>After</p>'
            )
            ch = _add_chapter(book, 'ch.xhtml', 'ch1', body)
            book.toc = [epub.Link('ch.xhtml', 'Chapter', 'c1')]
            book.spine = [('ch1', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'br_test')
            texts = [p.original_text for p in project.chapters[0].paragraphs]

            self.assertIn('Line one Line two', texts)
            self.assertIn('Before After', texts)
            # Must NOT concatenate
            for t in texts:
                self.assertNotIn('Line oneLine two', t)


class TestDivWrappingH1Li(unittest.TestCase):
    """A <div> wrapping <h1> and <li> should not appear as a separate element
    alongside its children."""

    def test_div_h1_li_no_dup(self):
        html = '<html><body><div><h1>Title</h1><li>Item</li></div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        elements = epub_text_elements(soup)
        texts = [el.get_text(strip=True) for el in elements]

        # h1 and li should each appear once
        self.assertEqual(texts.count('Title'), 1)
        self.assertEqual(texts.count('Item'), 1)
        # The combined "TitleItem" from the container div must NOT appear
        self.assertNotIn('TitleItem', texts)
        # No div elements in result (the wrapper is filtered)
        self.assertEqual(len([e for e in elements if e.name == 'div']), 0)


class TestLiWrappingP(unittest.TestCase):
    """A <li> wrapping a <p> should not produce duplicate text."""

    def test_li_p_no_dup(self):
        html = '<html><body><li><p>List item content</p></li></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        elements = epub_text_elements(soup)
        texts = [el.get_text(strip=True) for el in elements]

        self.assertEqual(texts.count('List item content'), 1)
        # Only the inner <p> should survive, not the outer <li>
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].name, 'p')


class TestDivWrappingOnlyLi(unittest.TestCase):
    """A <div> wrapping only <li> children (no <p>) should be filtered
    in favour of the <li> elements."""

    def test_div_li_only(self):
        html = '<html><body><div><li>Item 1</li><li>Item 2</li></div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        elements = epub_text_elements(soup)
        texts = [el.get_text(strip=True) for el in elements]

        self.assertEqual(texts, ['Item 1', 'Item 2'])
        # No div in result
        self.assertEqual(len([e for e in elements if e.name == 'div']), 0)


class TestSectionWithoutHrefPromotesChildren(unittest.TestCase):
    """When TOC has Section('Book') without meaningful href and children are
    the actual chapters, children should be promoted as chapter entries."""

    def test_section_no_href_promotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-section-nohref')
            book.set_title('Section Promote Test')
            book.set_language('en')

            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Chapter 1</h1><p>Content 1.</p>')
            ch2 = _add_chapter(book, 'ch02.xhtml', 'ch02',
                               '<h1>Chapter 2</h1><p>Content 2.</p>')

            # Section('Book') with no useful href, children are real chapters
            book.toc = [
                (epub.Section('Book'), [
                    epub.Link('ch01.xhtml', 'Chapter 1', 'c1'),
                    epub.Link('ch02.xhtml', 'Chapter 2', 'c2'),
                ]),
            ]
            book.spine = [('ch01', 'yes'), ('ch02', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'section_test')

            # Should produce 2 chapters (promoted children), not 1 grouping
            self.assertEqual(len(project.chapters), 2)
            self.assertEqual(project.chapters[0].title, 'Chapter 1')
            self.assertEqual(project.chapters[1].title, 'Chapter 2')


class TestPartWithChapterChildrenPromotes(unittest.TestCase):
    """TOC with (Section('Part I', href=ch01.xhtml), [Chapter 1, Chapter 2])
    where Part I's href matches Chapter 1 → children promoted."""

    def test_part_chapter_promotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = epub.EpubBook()
            book.set_identifier('test-part-chapter')
            book.set_title('Part Chapter Test')
            book.set_language('en')

            ch1 = _add_chapter(book, 'ch01.xhtml', 'ch01',
                               '<h1>Chapter 1</h1><p>Content 1.</p>')
            ch2 = _add_chapter(book, 'ch02.xhtml', 'ch02',
                               '<h1>Chapter 2</h1><p>Content 2.</p>')
            ch3 = _add_chapter(book, 'ch03.xhtml', 'ch03',
                               '<h1>Chapter 3</h1><p>Content 3.</p>')

            # Part I groups ch1+ch2, Part II groups ch3
            # Part hrefs match first child href
            book.toc = [
                (epub.Section('Part I', 'ch01.xhtml'), [
                    epub.Link('ch01.xhtml', 'Chapter 1', 'c1'),
                    epub.Link('ch02.xhtml', 'Chapter 2', 'c2'),
                ]),
                (epub.Section('Part II', 'ch03.xhtml'), [
                    epub.Link('ch03.xhtml', 'Chapter 3', 'c3'),
                ]),
            ]
            book.spine = [('ch01', 'yes'), ('ch02', 'yes'), ('ch03', 'yes')]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            path = _write_epub(book, tmp)

            project = parse_epub_structure(path, 'part_test')

            # Should produce 3 chapters (promoted), not 2 parts
            self.assertEqual(len(project.chapters), 3)
            self.assertEqual(project.chapters[0].title, 'Chapter 1')
            self.assertEqual(project.chapters[1].title, 'Chapter 2')
            self.assertEqual(project.chapters[2].title, 'Chapter 3')


class TestMixedContainerDirectText(unittest.TestCase):
    """Mixed containers retain direct prose without duplicating child blocks."""

    def test_mixed_container(self):
        html = '<html><body><div>Wrapper text <p>Child paragraph.</p> trailing</div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        elements = epub_text_elements(soup)
        texts = [el.get_text(strip=True) for el in elements]

        # Child paragraph should be present
        self.assertIn('Child paragraph.', texts)
        # The wrapper div's combined text must NOT appear
        self.assertNotIn('Wrapper text Child paragraph. trailing', texts)
        self.assertEqual(texts, ['Wrapper text', 'Child paragraph.', 'trailing'])
