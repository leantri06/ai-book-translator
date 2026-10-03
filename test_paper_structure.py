"""
Unit tests for core/paper_structure.py

Synthetic PDFs via pymupdf. No network. No file I/O.
"""

import os
import sys
import unittest

import pymupdf

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.paper_structure import PaperStructure, classify_plain_heading


# ── Helpers ──────────────────────────────────────────────────────────────

def _create_pdf(pages_spec):
    """Build a synthetic PDF in memory from page specs."""
    doc = pymupdf.open()
    for ps in pages_spec:
        w, h = ps.get("width", 612), ps.get("height", 792)
        page = doc.new_page(width=w, height=h)
        for ls in ps.get("lines", []):
            bold = ls.get("bold", False)
            fn = ls.get("fontname", "hebo" if bold else "helv")
            page.insert_text(
                pymupdf.Point(ls.get("x", 72), ls.get("y", 100)),
                ls["text"],
                fontsize=ls.get("fontsize", 10),
                fontname=fn,
            )
    return doc


def _body(y_start=160, count=10, fontsize=10):
    """Generate body-text lines at sequential y positions."""
    return [
        {"text": f"This is body text line number {i+1} that continues for a while to simulate a real paragraph of academic prose in a paper.",
         "y": y_start + i * 14, "fontsize": fontsize}
        for i in range(count)
    ]


def _make_standard_doc():
    """Multi-page doc: title, headings, subheadings, anchored, body-only."""
    return _create_pdf([
        {"lines": [
            {"text": "A Novel Approach to Machine Learning", "y": 120, "fontsize": 18, "bold": True},
            *_body(y_start=200, count=8),
        ]},
        {"lines": [
            {"text": "1 Introduction", "y": 100, "fontsize": 14, "bold": True},
            *_body(y_start=140, count=8),
        ]},
        {"lines": [
            {"text": "2 Methods", "y": 100, "fontsize": 14, "bold": True},
            *_body(y_start=140, count=3),
            {"text": "2.1 Data Collection", "y": 200, "fontsize": 12, "bold": True},
            *_body(y_start=230, count=5),
        ]},
        {"lines": [
            {"text": "Abstract", "y": 100, "fontsize": 14, "bold": True},
            *_body(y_start=140, count=6),
        ]},
        {"lines": _body(y_start=100, count=10)},
    ])


# ── classify() tests ────────────────────────────────────────────────────

class TestClassify(unittest.TestCase):

    # Positive heading tests

    def test_numbered_heading_major(self):
        ps = PaperStructure(_make_standard_doc())
        self.assertEqual(ps.classify("1 Introduction", 1), 1)

    def test_numbered_heading_with_dot(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "3. Experiments", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("3. Experiments", 1), 1)

    def test_anchored_abstract(self):
        self.assertEqual(PaperStructure(_make_standard_doc()).classify("Abstract", 3), 1)

    def test_anchored_references(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "References", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("References", 1), 1)

    def test_anchored_conclusion(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Conclusion", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("Conclusion", 1), 1)

    def test_anchored_acknowledgements(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Acknowledgements", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("Acknowledgements", 1), 1)

    def test_subsection_heading(self):
        self.assertEqual(PaperStructure(_make_standard_doc()).classify("2.1 Data Collection", 2), 2)

    def test_subsection_methods_is_2_not_1(self):
        """'2.1 Methods' must be subheading (2), not promoted to major by anchored match."""
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "2 Background", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=3),
                {"text": "2.1 Methods", "y": 200, "fontsize": 12, "bold": True},
                *_body(y_start=230, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("2.1 Methods", 1), 2)

    def test_subsection_results_is_2_not_1(self):
        """'2.1 Results' must be subheading (2), not promoted by anchored 'results'."""
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "2 Evaluation", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=3),
                {"text": "2.1 Results", "y": 200, "fontsize": 12, "bold": True},
                *_body(y_start=230, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("2.1 Results", 1), 2)

    def test_roman_numeral_heading(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "III Experimental Results", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("III Experimental Results", 1), 1)

    def test_roman_numeral_with_dot(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "IV. Discussion", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("IV. Discussion", 1), 1)

    def test_chapter_prefix(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Chapter 3 The Architecture", "y": 100, "fontsize": 16, "bold": True},
                *_body(y_start=160, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("Chapter 3 The Architecture", 1), 1)

    def test_unnumbered_bold_larger_heading(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Experimental Setup", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=160, count=5),
            ]},
        ])
        self.assertIn(PaperStructure(doc).classify("Experimental Setup", 1), (1, 2))

    def test_anchored_with_leading_number(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "5 Conclusion", "y": 100, "fontsize": 14, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("5 Conclusion", 1), 1)

    def test_chapter_top_of_page_retained(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Chapter 5 Neural Networks", "y": 90, "fontsize": 16, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        self.assertEqual(PaperStructure(doc).classify("Chapter 5 Neural Networks", 1), 1)

    # Negative tests

    def test_body_text_is_zero(self):
        ps = PaperStructure(_make_standard_doc())
        body = "This is body text line number 1 that continues for a while to simulate a real paragraph of academic prose in a paper."
        self.assertEqual(ps.classify(body, 4), 0)

    def test_toc_dot_leader_rejected(self):
        doc = _create_pdf([{"lines": [
            {"text": "1 Introduction .................. 5", "y": 100, "fontsize": 10},
            {"text": "2 Methods ...................... 12", "y": 114, "fontsize": 10},
        ]}])
        ps = PaperStructure(doc)
        self.assertEqual(ps.classify("1 Introduction .................. 5", 0), 0)
        self.assertEqual(ps.classify("2 Methods ...................... 12", 0), 0)

    def test_numbered_list_sentence_rejected(self):
        doc = _create_pdf([{"lines": [
            {"text": "1. The model is trained on a large corpus of text data using standard backpropagation techniques.", "y": 100, "fontsize": 10},
        ]}])
        self.assertEqual(PaperStructure(doc).classify(
            "1. The model is trained on a large corpus of text data using standard backpropagation techniques.", 0
        ), 0)

    def test_long_prose_rejected(self):
        t = "This is a very long line of text that continues well beyond what any heading would be, discussing the methodology in great detail with many clauses."
        doc = _create_pdf([{"lines": [{"text": t, "y": 100, "fontsize": 10}]}])
        self.assertEqual(PaperStructure(doc).classify(t, 0), 0)

    def test_prose_ending_period_rejected(self):
        doc = _create_pdf([{"lines": [
            {"text": "We propose a novel method.", "y": 100, "fontsize": 10},
            *_body(y_start=120, count=5),
        ]}])
        self.assertEqual(PaperStructure(doc).classify("We propose a novel method.", 0), 0)

    def test_short_numbered_list_same_typography_rejected(self):
        """'1. Train model' in body font without bold/larger → body (0)."""
        doc = _create_pdf([
            {"lines": [
                *_body(y_start=100, count=3),
                {"text": "1. Train model", "y": 150, "fontsize": 10},  # same as body
                *_body(y_start=170, count=3),
            ]},
        ])
        # This should NOT be classified as heading because it lacks
        # bold/larger typography and is not a known anchored name.
        # Note: "1. Train model" doesn't match _NUMBERED_HEADING_RE (has dot+space before uppercase)
        # but even if it did, body-font + no bold → 0.
        self.assertEqual(PaperStructure(doc).classify("1. Train model", 0), 0)

    def test_numbered_regular_font_not_promoted(self):
        """Numbered text in regular font on sparse page must not become heading."""
        doc = _create_pdf([
            {"lines": [
                {"text": "1 Configure settings", "y": 200, "fontsize": 10},
            ]},
        ])
        # Regular font, not bold, not larger → should be 0
        self.assertEqual(PaperStructure(doc).classify("1 Configure settings", 0), 0)


# ── is_running_header() tests ───────────────────────────────────────────

class TestRunningHeader(unittest.TestCase):

    def test_repeated_top_margin_detected(self):
        pages = [{"lines": [
            {"text": "Smith et al.: Deep Learning Survey", "y": 30, "fontsize": 8},
            *_body(y_start=100, count=5),
        ]} for _ in range(8)]
        ps = PaperStructure(_create_pdf(pages))
        self.assertTrue(ps.is_running_header("Smith et al.: Deep Learning Survey", 3))

    def test_running_header_classify_zero(self):
        pages = [{"lines": [
            {"text": "Smith et al.: Deep Learning Survey", "y": 30, "fontsize": 8},
            *_body(y_start=100, count=5),
        ]} for _ in range(8)]
        self.assertEqual(PaperStructure(_create_pdf(pages)).classify(
            "Smith et al.: Deep Learning Survey", 3
        ), 0)

    def test_non_repeated_not_header(self):
        pages = [
            {"lines": [
                {"text": "Unique Title On This Page Only", "y": 30, "fontsize": 8},
                *_body(y_start=100, count=5),
            ]},
            {"lines": _body(y_start=100, count=5)},
            {"lines": _body(y_start=100, count=5)},
        ]
        self.assertFalse(PaperStructure(_create_pdf(pages)).is_running_header(
            "Unique Title On This Page Only", 0
        ))

    def test_page_number_in_margin(self):
        pages = [{"lines": [
            *_body(y_start=100, count=5),
            {"text": str(i+1), "y": 760, "fontsize": 9},
        ]} for i in range(5)]
        self.assertTrue(PaperStructure(_create_pdf(pages)).is_running_header(
            "3", 2, bbox=(280, 760, 295, 772)
        ))

    def test_running_header_text_in_body_not_flagged(self):
        """Same text as running header but placed in body area → NOT a header."""
        pages = [{"lines": [
            {"text": "Deep Learning Survey", "y": 30, "fontsize": 8},
            *_body(y_start=100, count=5),
        ]} for _ in range(8)]
        # Add one page with same text in the body area as a heading
        pages.append({"lines": [
            {"text": "Deep Learning Survey", "y": 200, "fontsize": 14, "bold": True},
            *_body(y_start=240, count=5),
        ]})
        ps = PaperStructure(_create_pdf(pages))
        # In margin → True
        self.assertTrue(ps.is_running_header("Deep Learning Survey", 3))
        # In body area on page 8 → False
        self.assertFalse(ps.is_running_header(
            "Deep Learning Survey", 8, bbox=(72, 200, 300, 214)
        ))

    def test_running_header_text_body_heading_still_classifies(self):
        """Text matching a running header but at body position still classifies as heading."""
        pages = [{"lines": [
            {"text": "Deep Learning Survey", "y": 30, "fontsize": 8},
            *_body(y_start=100, count=5),
        ]} for _ in range(8)]
        pages.append({"lines": [
            {"text": "Deep Learning Survey", "y": 200, "fontsize": 14, "bold": True},
            *_body(y_start=240, count=5),
        ]})
        ps = PaperStructure(_create_pdf(pages))
        # At body position with bold/larger → should classify as heading, not 0
        result = ps.classify("Deep Learning Survey", 8, bbox=(72, 200, 300, 214))
        self.assertIn(result, (1, 2), "Body-area heading should not be suppressed by running header")


# ── Outline tests ───────────────────────────────────────────────────────

class TestOutline(unittest.TestCase):

    def test_outline_level1_match(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Optimization Strategy", "y": 100, "fontsize": 12, "bold": True},
                *_body(y_start=140, count=5),
            ]},
        ])
        doc.set_toc([[1, "Optimization Strategy", 2]])
        self.assertEqual(PaperStructure(doc).classify("Optimization Strategy", 1), 1)

    def test_outline_level2_match(self):
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Learning Rate Schedule", "y": 200, "fontsize": 11, "bold": True},
                *_body(y_start=230, count=5),
            ]},
        ])
        doc.set_toc([
            [1, "Training Details", 1],
            [2, "Learning Rate Schedule", 2],
        ])
        self.assertEqual(PaperStructure(doc).classify("Learning Rate Schedule", 1), 2)

    def test_outline_overrides_anchored_level(self):
        """If outline says 'Methods' is level 2, it should be 2 not 1."""
        doc = _create_pdf([
            {"lines": _body(count=5)},
            {"lines": [
                {"text": "Methods", "y": 200, "fontsize": 12, "bold": True},
                *_body(y_start=230, count=5),
            ]},
        ])
        doc.set_toc([
            [1, "Experiments", 1],
            [2, "Methods", 2],
        ])
        self.assertEqual(PaperStructure(doc).classify("Methods", 1), 2)


# ── ordered_text_blocks() tests ─────────────────────────────────────────

class TestOrderedTextBlocks(unittest.TestCase):

    def test_single_column_sorted_by_y(self):
        """Single-column blocks returned top-to-bottom."""
        doc = _create_pdf([{"lines": [
            {"text": "Third block", "y": 300, "fontsize": 10},
            {"text": "First block", "y": 100, "fontsize": 10},
            {"text": "Second block", "y": 200, "fontsize": 10},
        ]}])
        blocks = PaperStructure.ordered_text_blocks(doc[0])
        texts = [b[4].strip() for b in blocks]
        self.assertEqual(texts, ["First block", "Second block", "Third block"])

    def test_reverse_insertion_single_col(self):
        """Blocks inserted in reverse order still come out sorted."""
        doc = _create_pdf([{"lines": [
            {"text": "Line C", "y": 400, "fontsize": 10},
            {"text": "Line B", "y": 250, "fontsize": 10},
            {"text": "Line A", "y": 100, "fontsize": 10},
        ]}])
        blocks = PaperStructure.ordered_text_blocks(doc[0])
        texts = [b[4].strip() for b in blocks]
        self.assertEqual(texts, ["Line A", "Line B", "Line C"])

    def test_two_column_left_then_right(self):
        """Two-column layout: left column read first, then right."""
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        # Right column first (simulates PDF creation order)
        page.insert_text(pymupdf.Point(330, 100), "Right col line 1", fontsize=10, fontname="helv")
        page.insert_text(pymupdf.Point(330, 200), "Right col line 2", fontsize=10, fontname="helv")
        # Left column second
        page.insert_text(pymupdf.Point(72, 100), "Left col line 1", fontsize=10, fontname="helv")
        page.insert_text(pymupdf.Point(72, 200), "Left col line 2", fontsize=10, fontname="helv")

        blocks = PaperStructure.ordered_text_blocks(page)
        texts = [b[4].strip() for b in blocks]
        # Left column should come before right
        left_indices = [i for i, t in enumerate(texts) if "Left" in t]
        right_indices = [i for i, t in enumerate(texts) if "Right" in t]
        self.assertTrue(all(l < r for l in left_indices for r in right_indices),
                        f"Left column should precede right column, got: {texts}")

    def test_two_column_with_full_width_delimiter(self):
        """Full-width block splits two-column bands."""
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        # Band 1: two columns (offset y slightly so pymupdf doesn't merge them)
        page.insert_text(pymupdf.Point(72, 100), "L1 left column first band text", fontsize=10, fontname="helv")
        page.insert_text(pymupdf.Point(330, 120), "R1 right column first band text", fontsize=10, fontname="helv")
        # Full-width separator
        page.insert_text(pymupdf.Point(72, 250),
                         "Full width heading that spans the entire page width area across both columns",
                         fontsize=14, fontname="hebo")
        # Band 2: two columns
        page.insert_text(pymupdf.Point(72, 350), "L2 left column second band text", fontsize=10, fontname="helv")
        page.insert_text(pymupdf.Point(330, 370), "R2 right column second band text", fontsize=10, fontname="helv")

        blocks = PaperStructure.ordered_text_blocks(page)
        texts = [b[4].strip() for b in blocks]
        # Find blocks containing our markers
        def find_idx(marker):
            for i, t in enumerate(texts):
                if marker in t:
                    return i
            self.fail(f"{marker!r} not found in {texts}")
        l1_idx = find_idx("L1")
        r1_idx = find_idx("R1")
        l2_idx = find_idx("L2")
        r2_idx = find_idx("R2")
        self.assertLess(l1_idx, r1_idx)
        self.assertLess(r1_idx, l2_idx)
        self.assertLess(l2_idx, r2_idx)

    def test_text_blocks_only(self):
        """Image blocks are excluded."""
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text(pymupdf.Point(72, 100), "Some text", fontsize=10, fontname="helv")
        blocks = PaperStructure.ordered_text_blocks(page)
        for b in blocks:
            self.assertEqual(b[6], 0, "Only text blocks should be returned")

    def test_empty_page(self):
        doc = pymupdf.open()
        doc.new_page()
        self.assertEqual(PaperStructure.ordered_text_blocks(doc[0]), [])


# ── classify_plain_heading() tests ──────────────────────────────────────

class TestPlainHeading(unittest.TestCase):

    # Positive
    def test_anchored_sections(self):
        for name in ("Abstract", "References", "Conclusion", "Introduction", "Acknowledgements"):
            self.assertEqual(classify_plain_heading(name), 1, name)

    def test_numbered_heading(self):
        self.assertEqual(classify_plain_heading("1 Introduction"), 1)
        self.assertEqual(classify_plain_heading("2. Methods"), 1)
        self.assertEqual(classify_plain_heading("10 Conclusion"), 1)

    def test_roman_heading(self):
        self.assertEqual(classify_plain_heading("III Experimental Results"), 1)
        self.assertEqual(classify_plain_heading("IV. Discussion"), 1)

    def test_chapter_prefix(self):
        self.assertEqual(classify_plain_heading("Chapter 3 The Architecture"), 1)
        self.assertEqual(classify_plain_heading("Part II Overview"), 1)

    def test_subsection(self):
        self.assertEqual(classify_plain_heading("2.1 Data Collection"), 2)
        self.assertEqual(classify_plain_heading("3.2.1 Feature Extraction"), 2)

    # Subsection precedence
    def test_subsection_methods_plain(self):
        self.assertEqual(classify_plain_heading("2.1 Methods"), 2)

    def test_subsection_results_plain(self):
        self.assertEqual(classify_plain_heading("2.1 Results"), 2)

    # Negative
    def test_body_prose(self):
        self.assertIsNone(classify_plain_heading("We propose a novel method for learning."))

    def test_long_line(self):
        self.assertIsNone(classify_plain_heading("A" * 95))

    def test_numbered_list_sentence(self):
        self.assertIsNone(classify_plain_heading(
            "1. The model is trained on a large corpus of text data and evaluated on standard benchmarks."
        ))

    def test_toc_line(self):
        self.assertIsNone(classify_plain_heading("1 Introduction .................. 5"))

    def test_empty_short(self):
        self.assertIsNone(classify_plain_heading(""))
        self.assertIsNone(classify_plain_heading("A"))

    def test_prose_period(self):
        self.assertIsNone(classify_plain_heading("The results are shown in Table 1."))

    def test_trailing_page_number(self):
        self.assertIsNone(classify_plain_heading("3 Results              20"))

    def test_comma_ending(self):
        self.assertIsNone(classify_plain_heading("In this section,"))


# ── Edge cases ──────────────────────────────────────────────────────────

class TestEdgeCases(unittest.TestCase):

    def test_appendix_variants(self):
        self.assertEqual(classify_plain_heading("Appendix A"), 1)
        self.assertEqual(classify_plain_heading("Appendix B"), 1)

    def test_numbered_anchored_combined(self):
        self.assertEqual(classify_plain_heading("5. Conclusion"), 1)

    def test_deep_subsection(self):
        self.assertEqual(classify_plain_heading("3.2.1 Feature Extraction"), 2)

    def test_no_hardcoded_encoder_decoder(self):
        self.assertIsNone(classify_plain_heading("Encoder"))
        self.assertIsNone(classify_plain_heading("Decoder"))

    def test_single_word_not_anchored(self):
        self.assertIsNone(classify_plain_heading("Furthermore"))
        self.assertIsNone(classify_plain_heading("However"))

    def test_classify_with_bbox(self):
        doc = _create_pdf([{"lines": [
            {"text": "1 Introduction", "y": 100, "fontsize": 14, "bold": True},
            *_body(y_start=140, count=5),
        ]}])
        self.assertEqual(PaperStructure(doc).classify("1 Introduction", 0, bbox=(72, 100, 300, 114)), 1)

    def test_empty_doc(self):
        doc = pymupdf.open()
        doc.new_page()
        ps = PaperStructure(doc)
        self.assertEqual(ps.classify("anything", 0), 0)
        self.assertFalse(ps.is_running_header("anything", 0))

    def test_multipage_body_only(self):
        pages = [{"lines": _body(count=10)} for _ in range(5)]
        ps = PaperStructure(_create_pdf(pages))
        body = "This is body text line number 1 that continues for a while to simulate a real paragraph of academic prose in a paper."
        self.assertEqual(ps.classify(body, 2), 0)


if __name__ == "__main__":
    unittest.main()
