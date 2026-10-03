"""
PDF paper section detection and reading-order helpers.

Provides heading classification, running-header detection, and
conservative two-column reading-order for pymupdf text blocks.
Designed for integration with core/parser.py.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    import pymupdf
except ImportError:
    pymupdf = None

# ── Regex patterns ───────────────────────────────────────────────────────

_ANCHORED_SECTIONS: Set[str] = {
    "abstract", "introduction", "background",
    "related work", "related works",
    "methodology", "methods", "method",
    "materials and methods", "experimental setup",
    "experiments", "experiment",
    "results", "results and discussion", "discussion",
    "analysis", "evaluation",
    "conclusion", "conclusions", "summary",
    "future work", "future directions", "limitations",
    "acknowledgements", "acknowledgments",
    "acknowledgement", "acknowledgment",
    "references", "bibliography", "appendix",
    "supplementary material", "supplementary materials",
    "data availability", "competing interests",
    "author contributions", "funding",
    "ethics statement", "declarations",
}

_NUMBERED_HEADING_RE = re.compile(
    r"^(\d{1,3})\.?\s+([A-Z][\w\s\-/,()&:]{1,90})$"
)
_SUBSECTION_RE = re.compile(
    r"^((?:\d+\.)+\d+)\.?\s+([A-Z][\w\s\-/,()&:]{1,90})$"
)
_CHAPTER_RE = re.compile(
    r"^(?:Chapter|Part|Section)\s+(\d+|[IVXLC]+)[:\s.\-]*(.*)$",
    re.IGNORECASE,
)
_ROMAN_HEADING_RE = re.compile(
    r"^([IVXLC]{1,6})\.?\s+([A-Z][\w\s\-/,()&:]{1,90})$"
)
_TOC_LINE_RE = re.compile(r"\.{3,}\s*\d+\s*$|\s{2,}\d{1,4}\s*$")
_NUMBERED_LIST_SENTENCE_RE = re.compile(r"^\d{1,3}\.\s+[A-Z].*[.!?;:]\s*$")

_FLAG_BOLD = 1 << 4  # 16


# ── Data containers ──────────────────────────────────────────────────────

@dataclass
class _SpanInfo:
    text: str
    font_size: float
    flags: int
    font_name: str
    bbox: Tuple[float, float, float, float]
    page: int

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & _FLAG_BOLD) or "bold" in self.font_name.lower()


@dataclass
class _LineInfo:
    text: str
    spans: List[_SpanInfo]
    bbox: Tuple[float, float, float, float]
    page: int

    @property
    def font_size(self) -> float:
        if not self.spans:
            return 0.0
        total = sum(len(s.text) for s in self.spans)
        if total == 0:
            return self.spans[0].font_size
        return sum(s.font_size * len(s.text) for s in self.spans) / total

    @property
    def is_bold(self) -> bool:
        if not self.spans:
            return False
        bold = sum(len(s.text) for s in self.spans if s.is_bold)
        return bold > 0.5 * sum(len(s.text) for s in self.spans)


@dataclass
class _OutlineEntry:
    title: str
    level: int
    page: int
    title_normalised: str = ""

    def __post_init__(self):
        self.title_normalised = _normalise(self.title)


@dataclass
class _PageStats:
    lines: List[_LineInfo] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0


# ── Helpers ──────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    t = re.sub(r"\s+", " ", text.strip().lower())
    t = re.sub(r"^[\d.]+\s*", "", t)
    return t.strip()


def _strip_leading_number(text: str) -> str:
    return re.sub(r"^(?:\d+\.)*\d+\.?\s*", "", text).strip()


def _is_anchored_section(text: str) -> bool:
    core = _strip_leading_number(text).lower().strip()
    if core in _ANCHORED_SECTIONS:
        return True
    if re.match(r"^appendix\s+[a-z0-9]", core, re.IGNORECASE):
        return True
    return False


def _looks_like_prose(text: str) -> bool:
    if len(text) > 120:
        return True
    if text.rstrip().endswith((".", ",", ";", "!", "?")):
        return True
    return False


def _is_toc_line(text: str) -> bool:
    return bool(_TOC_LINE_RE.search(text))


def _is_numbered_list_sentence(text: str) -> bool:
    return bool(_NUMBERED_LIST_SENTENCE_RE.match(text)) and len(text) > 60


def _has_typographic_heading_signal(line: Optional[_LineInfo], body_size: float) -> bool:
    """True when the line is bold or notably larger than body text."""
    if line is None:
        return False
    if line.is_bold:
        return True
    if body_size > 0 and line.font_size > body_size * 1.10:
        return True
    return False


# ── Main class ───────────────────────────────────────────────────────────

class PaperStructure:
    """
    Analyses a PDF document's typographic structure to classify text lines
    and identify running headers.

    Parameters
    ----------
    doc : pymupdf.Document
        An opened PyMuPDF document.
    """

    def __init__(self, doc) -> None:
        if pymupdf is None:
            raise RuntimeError("pymupdf is required for PaperStructure")
        self._doc = doc
        self._num_pages: int = len(doc)
        self._page_stats: Dict[int, _PageStats] = {}
        self._outline_entries: List[_OutlineEntry] = []
        self._outline_titles_by_page: Dict[int, List[_OutlineEntry]] = {}
        self._body_font_size: float = 0.0
        self._body_font_name: str = ""
        # margin tracking: normalised text → set of page numbers
        self._top_margin_pages: Dict[str, Set[int]] = defaultdict(set)
        self._bottom_margin_pages: Dict[str, Set[int]] = defaultdict(set)
        self._margin_texts_repeated: Set[str] = set()
        self._scan()

    def _scan(self) -> None:
        self._extract_outline()
        self._extract_pages()
        self._compute_body_stats()
        self._detect_margin_repetition()

    def _extract_outline(self) -> None:
        try:
            toc = self._doc.get_toc(simple=True)
        except Exception:
            toc = []
        for entry in toc:
            if len(entry) >= 3:
                lvl, title, page_1based = entry[0], entry[1], entry[2]
                page_0 = max(0, page_1based - 1)
                oe = _OutlineEntry(title=title.strip(), level=lvl, page=page_0)
                self._outline_entries.append(oe)
                self._outline_titles_by_page.setdefault(page_0, []).append(oe)

    def _extract_pages(self) -> None:
        for page_num in range(self._num_pages):
            page = self._doc[page_num]
            ps = _PageStats(width=page.rect.width, height=page.rect.height)
            try:
                d = page.get_text("dict")
            except Exception:
                self._page_stats[page_num] = ps
                continue

            for block in d.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line_data in block.get("lines", []):
                    spans_raw = line_data.get("spans", [])
                    if not spans_raw:
                        continue
                    line_spans: List[_SpanInfo] = []
                    for s in spans_raw:
                        txt = s.get("text", "")
                        if not txt.strip():
                            continue
                        line_spans.append(_SpanInfo(
                            text=txt,
                            font_size=round(s.get("size", 10.0), 1),
                            flags=s.get("flags", 0),
                            font_name=s.get("font", ""),
                            bbox=tuple(s.get("bbox", (0, 0, 0, 0))),
                            page=page_num,
                        ))
                    if not line_spans:
                        continue
                    full_text = " ".join(s.text for s in line_spans).strip()
                    if not full_text:
                        continue
                    bbox_line = (
                        min(s.bbox[0] for s in line_spans),
                        min(s.bbox[1] for s in line_spans),
                        max(s.bbox[2] for s in line_spans),
                        max(s.bbox[3] for s in line_spans),
                    )
                    ps.lines.append(_LineInfo(
                        text=full_text, spans=line_spans,
                        bbox=bbox_line, page=page_num,
                    ))

            self._page_stats[page_num] = ps

            for li in ps.lines:
                y0, y1 = li.bbox[1], li.bbox[3]
                h = y1 - y0
                norm = _normalise(li.text)
                if not norm or len(norm) < 2:
                    continue
                if y0 < 80 and h < 25:
                    self._top_margin_pages[norm].add(page_num)
                if y0 > ps.height - 60 and h < 25:
                    self._bottom_margin_pages[norm].add(page_num)

    def _compute_body_stats(self) -> None:
        size_counter: Counter = Counter()
        font_counter: Counter = Counter()
        for ps in self._page_stats.values():
            for li in ps.lines:
                if len(li.text) < 40:
                    continue
                for sp in li.spans:
                    w = len(sp.text)
                    size_counter[sp.font_size] += w
                    font_counter[sp.font_name] += w
        self._body_font_size = size_counter.most_common(1)[0][0] if size_counter else 10.0
        self._body_font_name = font_counter.most_common(1)[0][0] if font_counter else ""

    def _detect_margin_repetition(self) -> None:
        threshold = max(3, int(self._num_pages * 0.15))
        for text, pages in self._top_margin_pages.items():
            if len(pages) >= threshold:
                self._margin_texts_repeated.add(text)
        for text, pages in self._bottom_margin_pages.items():
            if len(pages) >= threshold:
                self._margin_texts_repeated.add(text)

    # ── Internal lookups ─────────────────────────────────────────────

    def _find_line(
        self, text: str, page_number: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[_LineInfo]:
        ps = self._page_stats.get(page_number)
        if ps is None:
            return None
        text_norm = _normalise(text)
        candidates = [li for li in ps.lines if _normalise(li.text) == text_norm]
        if not candidates:
            candidates = [
                li for li in ps.lines
                if text_norm in _normalise(li.text) or _normalise(li.text) in text_norm
            ]
        if not candidates:
            return None
        if bbox is not None and len(candidates) > 1:
            candidates.sort(key=lambda li: abs(li.bbox[0] - bbox[0]) + abs(li.bbox[1] - bbox[1]))
        return candidates[0]

    def _matches_outline(self, text: str, page_number: int) -> Optional[int]:
        text_norm = _normalise(text)
        if not text_norm:
            return None
        stripped = _normalise(_strip_leading_number(text))
        for delta in (0, -1, 1):
            for oe in self._outline_titles_by_page.get(page_number + delta, []):
                if oe.title_normalised == text_norm:
                    return oe.level
                if stripped and oe.title_normalised == stripped:
                    return oe.level
                oe_stripped = _normalise(_strip_leading_number(oe.title))
                if oe_stripped and oe_stripped == stripped:
                    return oe.level
        return None

    def _classify_by_typography(self, line: _LineInfo) -> Optional[int]:
        body = self._body_font_size
        if body <= 0:
            return None
        ratio = line.font_size / body
        if ratio >= 1.35:
            return 1 if (line.is_bold or ratio >= 1.6) else 2
        if ratio >= 1.10 and line.is_bold:
            return 1
        if ratio >= 0.95 and line.is_bold and len(line.text) < 80 and not _looks_like_prose(line.text):
            return 2
        return None

    def _is_standalone_line(
        self, text: str, page_number: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> bool:
        ps = self._page_stats.get(page_number)
        if ps is None:
            return False
        line = self._find_line(text, page_number, bbox)
        if line is None:
            return False
        above, below = [], []
        for li in ps.lines:
            if li is line:
                continue
            if abs((li.bbox[1] + li.bbox[3]) / 2 - (line.bbox[1] + line.bbox[3]) / 2) > 40:
                continue
            if li.bbox[3] < line.bbox[1] + 5:
                above.append(li)
            elif li.bbox[1] > line.bbox[3] - 5:
                below.append(li)
        if above and below:
            gap_above = line.bbox[1] - max(above, key=lambda l: l.bbox[3]).bbox[3]
            gap_below = min(below, key=lambda l: l.bbox[1]).bbox[1] - line.bbox[3]
            body_h = self._body_font_size * 1.3
            return gap_above > body_h * 0.5 or gap_below > body_h * 0.5
        # No tight neighbors on both sides → isolated, counts as standalone
        return True

    def _in_margin(
        self, text: str, page_number: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> bool:
        """True when the text is positioned inside a page margin zone."""
        y0, y1 = None, None
        page_height = 792.0
        ps = self._page_stats.get(page_number)
        if ps is not None:
            page_height = ps.height
        if bbox is not None:
            y0, y1 = bbox[1], bbox[3]
        else:
            line = self._find_line(text, page_number)
            if line is not None:
                y0, y1 = line.bbox[1], line.bbox[3]
        if y0 is None:
            return False
        h = (y1 or y0 + 15) - y0
        return (y0 < 80 and h < 25) or (y0 > page_height - 60 and h < 25)

    # ── Public API ───────────────────────────────────────────────────

    def classify(
        self, text: str, page_number: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> int:
        """
        Classify a text line from the PDF.

        Returns
        -------
        int
            0 = body, 1 = major section, 2 = subheading, 3+ = deeper.
        """
        text = text.strip()
        if not text or len(text) < 2:
            return 0

        # Quick rejections
        if _is_toc_line(text):
            return 0
        if self.is_running_header(text, page_number, bbox):
            return 0
        if len(text) > 120 and not _is_anchored_section(_strip_leading_number(text)):
            return 0

        # ── Outline match (preferred when available) ─────────────────
        outline_level = self._matches_outline(text, page_number)
        if outline_level is not None and not _looks_like_prose(text):
            return 1 if outline_level == 1 else 2

        # ── Subsection numbered heading (before anchored check) ──────
        m_sub = _SUBSECTION_RE.match(text)
        if m_sub and not _is_numbered_list_sentence(text) and len(text) < 80:
            line = self._find_line(text, page_number, bbox)
            if line is not None:
                typo = self._classify_by_typography(line)
                if typo is not None:
                    return max(2, typo)
                if _has_typographic_heading_signal(line, self._body_font_size) and self._is_standalone_line(text, page_number, bbox):
                    return 2
                if _is_anchored_section(text):
                    return 2
            else:
                if _is_anchored_section(text) or not _looks_like_prose(text):
                    return 2

        # ── Chapter/Part prefix ──────────────────────────────────────
        if _CHAPTER_RE.match(text) and len(text) < 100:
            return 1

        # ── Anchored section names ───────────────────────────────────
        if _is_anchored_section(text) and not _looks_like_prose(text):
            # Only if not already handled as subsection above
            if not m_sub:
                return 1

        # ── Numbered top-level heading ───────────────────────────────
        m_num = _NUMBERED_HEADING_RE.match(text)
        if m_num and not _is_numbered_list_sentence(text) and len(text) < 75:
            line = self._find_line(text, page_number, bbox)
            # Require bold/larger OR anchored name for numbered headings
            if _is_anchored_section(text):
                return 1
            if _has_typographic_heading_signal(line, self._body_font_size):
                return 1
            # No typography data at all → conservative: reject
            return 0

        # ── Roman numeral top-level heading ──────────────────────────
        m_roman = _ROMAN_HEADING_RE.match(text)
        if m_roman and not _is_numbered_list_sentence(text) and len(text) < 80:
            line = self._find_line(text, page_number, bbox)
            if _is_anchored_section(text):
                return 1
            if _has_typographic_heading_signal(line, self._body_font_size):
                return 1
            if line is not None and self._is_standalone_line(text, page_number, bbox):
                return 1
            if line is None:
                return 1

        # ── Unnumbered bold/larger isolated heading ──────────────────
        line = self._find_line(text, page_number, bbox)
        if line is not None and not _looks_like_prose(text) and len(text) < 80:
            typo = self._classify_by_typography(line)
            if typo is not None and self._is_standalone_line(text, page_number, bbox):
                if line.font_size > self._body_font_size * 1.15 or (
                    line.is_bold and line.font_size >= self._body_font_size
                ):
                    if typo <= 1 and line.font_size > self._body_font_size * 1.25:
                        return 1
                    return 2

        return 0

    def is_running_header(
        self, text: str, page_number: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> bool:
        """
        True when text is a running header/footer: repeated margin text
        appearing on multiple distinct pages AND the current instance
        is positioned in a margin zone.
        """
        text = text.strip()
        if not text:
            return False

        # Must be in a margin position to be a running header
        if not self._in_margin(text, page_number, bbox):
            return False

        norm = _normalise(text)

        # Fast path: already identified as repeated
        if norm in self._margin_texts_repeated:
            return True

        # Count unique pages this text appears in margins
        unique_pages = len(self._top_margin_pages.get(norm, set()) |
                          self._bottom_margin_pages.get(norm, set()))
        if unique_pages >= 2:
            return True

        # Bare page numbers in margin
        if re.match(r"^\s*\d{1,4}\s*$", text):
            return True

        return False

    # ── Reading-order helper ─────────────────────────────────────────

    @staticmethod
    def ordered_text_blocks(page) -> List:
        """
        Return text-type blocks from *page* in conservative reading order.

        Detects two-column layout by finding blocks separated near the page
        midline. Full-width blocks delimit vertical bands; within each band
        left-column blocks are read top-to-bottom, then right-column, then
        next band. Single-column pages are returned sorted by (y0, x0).

        Parameters
        ----------
        page : pymupdf.Page

        Returns
        -------
        list
            Block tuples as returned by ``page.get_text("blocks")``,
            filtered to text type (``b[6] == 0``), reordered.
        """
        all_blocks = page.get_text("blocks")
        text_blocks = [b for b in all_blocks if b[6] == 0]
        pw = page.rect.width
        mid = pw / 2

        # MuPDF can merge left/right lines at the same height into one block.
        # Recover their column bounds before ordering, without breaking normal
        # multiline paragraphs or full-width headings.
        details = {b.get('number'): b for b in page.get_text('dict').get('blocks', [])
                   if b.get('type') == 0}
        recovered = []
        for block in text_blocks:
            lines = details.get(block[5], {}).get('lines', [])
            left = [line for line in lines if line['bbox'][2] <= mid]
            right = [line for line in lines if line['bbox'][0] >= mid]
            if left and right and len(left) + len(right) == len(lines):
                for group in (left, right):
                    bounds = (min(line['bbox'][0] for line in group),
                              min(line['bbox'][1] for line in group),
                              max(line['bbox'][2] for line in group),
                              max(line['bbox'][3] for line in group))
                    text = '\n'.join(''.join(span.get('text', '') for span in line.get('spans', []))
                                     for line in sorted(group, key=lambda line: line['bbox'][1])) + '\n'
                    recovered.append((*bounds, text, block[5], 0))
            else:
                recovered.append(block)
        text_blocks = recovered
        if len(text_blocks) <= 1:
            return text_blocks
        gap_tolerance = pw * 0.08  # blocks within 8% of midline may be column-split

        # Classify each block as left, right, or full-width
        LEFT, RIGHT, FULL = 0, 1, 2

        def _side(b):
            x0, x1 = b[0], b[2]
            w = x1 - x0
            # Full-width: spans most of the page
            if w > pw * 0.62:
                return FULL
            # Sits entirely in left half (with tolerance)
            if x1 < mid + gap_tolerance:
                return LEFT
            # Sits entirely in right half
            if x0 > mid - gap_tolerance:
                return RIGHT
            return FULL  # straddles midline → treat as full-width

        sides = [_side(b) for b in text_blocks]

        # Detect whether this page actually uses two columns
        has_left = any(s == LEFT for s in sides)
        has_right = any(s == RIGHT for s in sides)
        is_two_col = has_left and has_right

        if not is_two_col:
            # Single-column: sort by vertical position then horizontal
            return sorted(text_blocks, key=lambda b: (b[1], b[0]))

        # Two-column layout: split into vertical bands delimited by
        # full-width blocks, then within each band left-col then right-col.
        # Pair blocks with their side classification and original y0.
        tagged = list(zip(text_blocks, sides))
        tagged.sort(key=lambda pair: pair[0][1])  # sort by y0

        bands: List[List] = []
        current_band: List = []

        for block, side in tagged:
            if side == FULL:
                # Flush current band, emit full-width block as its own band
                if current_band:
                    bands.append(current_band)
                    current_band = []
                bands.append([(block, FULL)])
            else:
                current_band.append((block, side))

        if current_band:
            bands.append(current_band)

        result: List = []
        for band in bands:
            lefts = sorted([b for b, s in band if s == LEFT], key=lambda b: (b[1], b[0]))
            rights = sorted([b for b, s in band if s == RIGHT], key=lambda b: (b[1], b[0]))
            fulls = [b for b, s in band if s == FULL]
            result.extend(lefts)
            result.extend(rights)
            result.extend(fulls)

        return result


# ── Plain-text fallback ──────────────────────────────────────────────────

def classify_plain_heading(text: str) -> Optional[int]:
    """
    Conservative heading classification for pypdf fallback (no typography).

    Returns 1 (major), 2 (subsection), or None (not a heading).
    Rejects prose, numbered list sentences, TOC lines, and lines > 90 chars.
    """
    text = text.strip()
    if not text or len(text) < 2:
        return None
    if _is_toc_line(text):
        return None
    if len(text) > 90:
        return None
    if _is_numbered_list_sentence(text):
        return None

    # Subsection before anchored: "2.1 Methods" → 2, not 1
    m_sub = _SUBSECTION_RE.match(text)
    if m_sub and not _looks_like_prose(text) and len(text) < 80:
        remainder = m_sub.group(2).strip()
        if len(remainder) < 70 and not remainder.endswith((".", ",", ";", "!", "?")):
            return 2

    # Anchored section names (only for non-subsection patterns)
    if _is_anchored_section(text) and not _looks_like_prose(text):
        return 1

    # Chapter/Part prefix
    if _CHAPTER_RE.match(text) and len(text) < 100:
        return 1

    # Numbered heading: "1 Introduction", "2. Methods"
    m_num = _NUMBERED_HEADING_RE.match(text)
    if m_num and not _looks_like_prose(text):
        remainder = m_num.group(2).strip()
        if len(remainder) < 70 and not remainder.endswith((".", ",", ";", "!", "?")):
            return 1

    # Roman numeral heading
    m_roman = _ROMAN_HEADING_RE.match(text)
    if m_roman and not _looks_like_prose(text) and len(text) < 80:
        return 1

    return None
