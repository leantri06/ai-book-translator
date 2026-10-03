"""
EPUB Structure Parser — spine-ordered, TOC-aware chapter extraction.

Builds a BookProject from an EPUB file using the spine (reading order),
recursive TOC (NCX or EPUB3 nav), and anchor-based chapter splitting.

Public helpers:
    parse_epub_structure(file_path, project_id) -> BookProject
    epub_text_elements(soup) -> list[Tag]
"""
from __future__ import annotations

import os
import posixpath
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag
import ebooklib
from ebooklib import epub


# ---------------------------------------------------------------------------
#  Shared helper — canonical text-element extraction used by parser & exporter
# ---------------------------------------------------------------------------

_TEXT_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote', 'li', 'div', 'hr']

_TEXT_TAG_SET = frozenset(_TEXT_TAGS)


def epub_text_elements(soup: BeautifulSoup) -> List[Tag]:
    """Return the ordered, non-overlapping list of *leaf* text elements in
    an XHTML document.

    An element is kept only when none of its descendants are also text
    elements (i.e. it is a leaf in the text-element tree).  This prevents
    duplication from container ``<div>`` wrapping ``<p>``, ``<li>``
    wrapping ``<p>``, ``<div>`` wrapping ``<h1>+<li>``, etc.

    Direct text runs in mixed containers are wrapped deterministically
    before selecting leaves, so prose surrounding nested blocks is retained.

    This is the single source of truth shared between the parser and
    the in-place EPUB exporter for element-index alignment.
    """
    # Give direct text around child blocks its own stable source element.
    # Apply the same deterministic normalization again during in-place export.
    for container in list(soup.find_all(['div', 'blockquote', 'li'])):
        if not container.find(_TEXT_TAGS):
            continue
        run = []

        def wrap_run():
            if run and any((str(node).strip() if isinstance(node, NavigableString)
                            else node.get_text().strip()) for node in run):
                wrapper = soup.new_tag('p')
                run[0].insert_before(wrapper)
                for node in run:
                    wrapper.append(node.extract())
            run.clear()

        for child in list(container.contents):
            if isinstance(child, Tag) and (child.name in _TEXT_TAG_SET or child.find(_TEXT_TAGS)):
                wrap_run()
            else:
                run.append(child)
        wrap_run()

    raw = soup.find_all(_TEXT_TAGS)
    raw_id_set = frozenset(id(el) for el in raw)

    result: List[Tag] = []
    for el in raw:
        # Keep this element only if it has NO descendant that is also
        # a text-tag element in the candidate set (ancestor-descendant
        # non-overlap check).
        has_text_child = False
        for child in el.descendants:
            if isinstance(child, Tag) and child.name in _TEXT_TAG_SET and id(child) in raw_id_set:
                has_text_child = True
                break
        if not has_text_child:
            result.append(el)
    return result


# ---------------------------------------------------------------------------
#  Internal TOC data structure
# ---------------------------------------------------------------------------

@dataclass
class _TocEntry:
    """A single entry in the flattened table of contents."""
    title: str
    href: str          # full relative href including fragment, e.g. "ch01.xhtml#sec2"
    doc_path: str      # normalized doc path without fragment
    fragment: str      # anchor fragment (empty string if none)
    depth: int         # 0 = top-level, 1 = child, …
    children: List[_TocEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
#  TOC extraction helpers
# ---------------------------------------------------------------------------

def _normalize_href(href: str) -> Tuple[str, str]:
    """Split *href* into ``(doc_path, fragment)`` with normalized path.

    Handles URL-encoded characters and back-slashes from Windows-based
    EPUB producers.
    """
    href = urllib.parse.unquote(href)
    href = href.replace('\\', '/')
    doc, _, frag = href.partition('#')
    # Collapse ".." and "." segments
    doc = posixpath.normpath(doc) if doc else ""
    return doc, frag


def _extract_toc_ebooklib(toc_list, depth: int = 0) -> List[_TocEntry]:
    """Recursively extract TOC entries from ebooklib's ``book.toc``.

    ebooklib represents the TOC as a list of:
      • ``Link(href, title, uid)``                   — leaf entry
      • ``(Section(title, href), [children…])``       — nested section
    """
    entries: List[_TocEntry] = []
    for item in toc_list:
        if isinstance(item, tuple):
            section, children = item[0], item[1] if len(item) > 1 else []
            href = getattr(section, 'href', '') or ''
            title = getattr(section, 'title', '') or ''
            doc_path, fragment = _normalize_href(href)
            entry = _TocEntry(
                title=title.strip(),
                href=href,
                doc_path=doc_path,
                fragment=fragment,
                depth=depth,
            )
            if isinstance(children, (list, tuple)):
                entry.children = _extract_toc_ebooklib(children, depth + 1)
            entries.append(entry)
        elif hasattr(item, 'href') and hasattr(item, 'title'):
            # ebooklib.epub.Link
            href = item.href or ''
            title = item.title or ''
            doc_path, fragment = _normalize_href(href)
            entries.append(_TocEntry(
                title=title.strip(),
                href=href,
                doc_path=doc_path,
                fragment=fragment,
                depth=depth,
            ))
    return entries


def _flatten_toc(entries: List[_TocEntry]) -> List[_TocEntry]:
    """Flatten a nested TOC tree into reading order, preserving depth."""
    result: List[_TocEntry] = []
    for e in entries:
        result.append(e)
        if e.children:
            result.extend(_flatten_toc(e.children))
    return result


def _top_level_toc(entries: List[_TocEntry]) -> List[_TocEntry]:
    """Return the effective chapter-level entries for splitting.

    Normally these are the shallowest-depth entries.  However, when the
    shallowest entries are purely grouping nodes — Sections whose ``href``
    is empty, points to ``'.'``, or duplicates their first child's doc —
    *and* they have children with real hrefs, the children are promoted to
    be the chapter entries instead.

    This handles common patterns:
      • ``(Section('Book', href=''), [Chapter 1, Chapter 2])``
      • ``(Section('Part I', href='ch01.xhtml'), [Chapter 1, Chapter 2])``
        where Part I's href == Chapter 1's href (grouping node).
    """
    flat = _flatten_toc(entries)
    if not flat:
        return []
    min_depth = min(e.depth for e in flat)
    shallowest = [e for e in flat if e.depth == min_depth]

    # Promote grouping nodes individually, preserving adjacent leaf chapters.
    promoted: List[_TocEntry] = []
    for entry in shallowest:
        if not entry.children:
            promoted.append(entry)
            continue
        # A grouping node has no meaningful href of its own, or its href
        # points to the same document as its first child.
        entry_doc = entry.doc_path
        first_child_doc = entry.children[0].doc_path if entry.children else ''
        is_grouping = (
            not entry_doc
            or entry_doc == '.'
            or (re.match(r'^(?:part|book|volume|phần|quyển)\b', entry.title, re.I)
                and first_child_doc and entry_doc == first_child_doc)
        )
        if is_grouping:
            promoted.extend(_top_level_toc(entry.children))
        else:
            promoted.append(entry)
    return promoted


# ---------------------------------------------------------------------------
#  Fallback: detect strongest heading level
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r'^h([1-6])$', re.IGNORECASE)


def _detect_strongest_heading(soups: List[Tuple[str, BeautifulSoup]]) -> Optional[str]:
    """Scan all documents and return the tag name of the strongest (lowest
    numbered) heading that appears, e.g. ``'h1'``.  Returns *None* when no
    headings are found at all.
    """
    best = 7
    for _, soup in soups:
        for tag in soup.find_all(re.compile(r'^h[1-6]$', re.IGNORECASE)):
            m = _HEADING_RE.match(tag.name)
            if m:
                level = int(m.group(1))
                if level < best:
                    best = level
    return f'h{best}' if best < 7 else None


# ---------------------------------------------------------------------------
#  Nav epub:type=toc detection
# ---------------------------------------------------------------------------

def _is_nav_toc_doc(soup: BeautifulSoup) -> bool:
    """Return True if the document contains ``<nav epub:type="toc">``."""
    # The epub:type attribute lives in the EPUB namespace, but many parsers
    # expose it as a plain attribute.  Check both.
    EPUB_NS = 'http://www.idpf.org/2007/ops'
    for nav in soup.find_all('nav'):
        etype = nav.get('epub:type') or nav.get(f'{{{EPUB_NS}}}type') or ''
        if 'toc' in etype.split():
            return True
    return False


# ---------------------------------------------------------------------------
#  Element-to-paragraph extraction (preserving scene breaks, tags, etc.)
# ---------------------------------------------------------------------------

def _extract_element_text(el: Tag) -> str:
    """Extract visible text from *el* by walking raw text nodes.

    Unlike ``get_text(strip=True)`` this preserves whitespace between
    inline elements (``<b>``, ``<em>``, ``<span>``, …) so that
    ``'Hello <b>world</b> today'`` becomes ``'Hello world today'``
    instead of ``'Helloworldtoday'``.

    ``<br>`` / ``<br/>`` tags are replaced by a single space (or newline
    context is collapsed to a space in the final normalisation pass).
    """
    parts: List[str] = []
    for node in el.descendants:
        if isinstance(node, NavigableString):
            parts.append(str(node))
        elif isinstance(node, Tag) and node.name == 'br':
            parts.append(' ')
    raw = ''.join(parts)
    # Collapse all whitespace runs (including newlines) to a single space
    text = re.sub(r'\s+', ' ', raw).strip()
    # Remove stray replacement characters
    text = text.replace('�', '').strip()
    return text


def _extract_paragraph_text(el: Tag) -> Tuple[str, str]:
    """Extract (text, tag_name) from a BeautifulSoup element.

    Returns ``('', tag)`` for empty / trivial elements so the caller can
    decide whether to keep them.
    """
    tag_name = el.name.lower()

    # Map detailed heading tags; keep blockquote and li
    if tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'li'):
        tag_out = tag_name
    else:
        tag_out = 'p'

    text = _extract_element_text(el)
    return text, tag_out


_SCENE_BREAK_MARKERS = frozenset({
    '* * *', '***', '• • •', '---', '—', '⁂', '* * * *',
    '~ ~ ~', '~~~', '- - -', '•   •   •', '♦', '§', '# # #',
})


def _is_scene_break(el: Tag) -> bool:
    """Detect scene-break elements: ``<hr>`` or ``<p>``-like tags whose
    visible text is purely decorative separators.
    """
    if el.name == 'hr':
        return True
    text = _extract_element_text(el)
    if text in _SCENE_BREAK_MARKERS:
        return True
    # All-whitespace-or-ornament
    if text and all(c in '·*•—–-~#§♦⁂ \t' for c in text):
        return True
    return False


# ---------------------------------------------------------------------------
#  Anchor locator — find element index for a fragment id
# ---------------------------------------------------------------------------

def _find_anchor_element_index(elements: List[Tag], fragment: str, soup: BeautifulSoup) -> int:
    """Return the index into *elements* that corresponds to *fragment*.

    Strategy:
    1. Find the anchor target in the document (any element whose ``id``
       matches *fragment*).
    2. Walk forward from that anchor to find the first element in
       *elements* at or after the anchor's position in the document tree.

    Returns -1 if the fragment cannot be located.
    """
    if not fragment:
        return 0

    # Find the target element by id
    target = soup.find(id=fragment)
    if target is None:
        # Try name attribute (older EPUBs use <a name="...">)
        target = soup.find('a', attrs={'name': fragment})
    if target is None:
        return -1

    # If the target itself is one of our text elements, return its index
    for idx, el in enumerate(elements):
        if el is target:
            return idx

    # Otherwise find the first text element that comes *after* the anchor
    # in document order.
    all_tags = list(soup.find_all(True))
    target_idx_in_doc = next((idx for idx, tag in enumerate(all_tags) if tag is target), -1)
    if target_idx_in_doc < 0:
        return -1

    # Build a set for O(1) lookup
    element_set = set(id(el) for el in elements)
    for doc_idx in range(target_idx_in_doc, len(all_tags)):
        if id(all_tags[doc_idx]) in element_set:
            for el_idx, el in enumerate(elements):
                if el is all_tags[doc_idx]:
                    return el_idx
    return -1


# ---------------------------------------------------------------------------
#  Main parse function
# ---------------------------------------------------------------------------

def parse_epub_structure(file_path: str, project_id: str) -> 'BookProject':
    """Parse an EPUB into a :class:`BookProject` using spine reading order
    and recursive TOC-based chapter splitting.

    Parameters
    ----------
    file_path : str
        Path to the ``.epub`` file.
    project_id : str
        Unique identifier for the project (used in paragraph / chapter ids
        and cover caching).

    Returns
    -------
    BookProject
        Fully populated project with ``document_type='novel'``,
        ``source_format='epub'``, and ``structure_warnings`` list.
    """
    # Lazy import to avoid circular dependency with core.parser
    from core.parser import BookProject, BookChapter, BookParagraph

    warnings: List[str] = []

    book = epub.read_epub(file_path, {'ignore_ncx': False})

    # ---- Metadata --------------------------------------------------------
    title_meta = book.get_metadata('DC', 'title')
    title = title_meta[0][0] if title_meta else os.path.splitext(os.path.basename(file_path))[0]
    creator_meta = book.get_metadata('DC', 'creator')
    author = creator_meta[0][0] if creator_meta else "Unknown"

    # ---- Cover -----------------------------------------------------------
    cover_path = ""
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(file_path)), ".covers")
    os.makedirs(cache_dir, exist_ok=True)
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        name_lower = item.get_name().lower()
        if 'cover' in name_lower or 'front' in name_lower:
            cover_dest = os.path.join(cache_dir, f"{project_id}_cover.jpg")
            with open(cover_dest, 'wb') as cf:
                cf.write(item.get_content())
            cover_path = cover_dest
            break

    # ---- Spine reading order ---------------------------------------------
    spine_items: List[Tuple[epub.EpubHtml, bool]] = []  # (item, is_linear)
    has_spine = bool(book.spine)

    if has_spine:
        for entry in book.spine:
            if isinstance(entry, tuple):
                idref, linear = entry[0], entry[1] if len(entry) > 1 else 'yes'
            else:
                idref, linear = entry, 'yes'

            item = book.get_item_with_id(idref)
            if item is None:
                warnings.append(f"Spine idref '{idref}' not found in manifest")
                continue

            is_linear = str(linear).lower() != 'no'

            # Exclude EpubNav items
            if isinstance(item, epub.EpubNav):
                continue

            # Exclude nav documents with epub:type=toc
            if isinstance(item, epub.EpubHtml):
                try:
                    content = item.get_content().decode('utf-8', errors='replace')
                    nav_soup = BeautifulSoup(content, 'html.parser')
                    if _is_nav_toc_doc(nav_soup):
                        continue
                except Exception:
                    pass

            if not is_linear:
                continue

            if isinstance(item, epub.EpubHtml):
                spine_items.append((item, is_linear))
    else:
        # Fallback: use all ITEM_DOCUMENT items from manifest
        warnings.append("No spine found; falling back to manifest document order")
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            if isinstance(item, epub.EpubNav):
                continue
            if isinstance(item, epub.EpubHtml):
                try:
                    content = item.get_content().decode('utf-8', errors='replace')
                    nav_soup = BeautifulSoup(content, 'html.parser')
                    if _is_nav_toc_doc(nav_soup):
                        continue
                except Exception:
                    pass
                spine_items.append((item, True))

    if not spine_items:
        warnings.append("No usable content documents found in EPUB")
        project = BookProject(
            id=project_id, title=title, author=author,
            source_format='epub', source_file_path=file_path,
            cover_image_path=cover_path, chapters=[],
        )
        project.structure_warnings = warnings  # type: ignore[attr-defined]
        project.document_type = 'novel'  # type: ignore[attr-defined]
        return project

    # ---- Parse all spine documents ---------------------------------------
    doc_soups: Dict[str, BeautifulSoup] = {}
    doc_elements: Dict[str, List[Tag]] = {}
    doc_raw_html: Dict[str, str] = {}

    for item, _ in spine_items:
        doc_name = item.get_name()
        content = item.get_content()
        try:
            html_str = content.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            try:
                html_str = content.decode('latin-1', errors='ignore')
            except Exception:
                html_str = str(content)

        soup = BeautifulSoup(html_str, 'html.parser')
        doc_soups[doc_name] = soup
        doc_elements[doc_name] = epub_text_elements(soup)
        doc_raw_html[doc_name] = html_str

    # ---- TOC extraction --------------------------------------------------
    toc_entries: List[_TocEntry] = []
    raw_toc = getattr(book, 'toc', None)
    if raw_toc is not None:
        # ebooklib may return a single Link (e.g. for nav-only books with
        # empty user TOC) instead of a list — normalise to list.
        if not isinstance(raw_toc, (list, tuple)):
            raw_toc = [raw_toc]
        if raw_toc:
            toc_entries = _extract_toc_ebooklib(raw_toc)

    # Normalize TOC doc_paths to match spine doc_names
    spine_name_set = set(item.get_name() for item, _ in spine_items)
    spine_basename_map: Dict[str, List[str]] = {}
    for name in spine_name_set:
        bn = posixpath.basename(name)
        spine_basename_map.setdefault(bn, []).append(name)

    def _resolve_toc_doc(doc_path: str) -> str:
        """Resolve a TOC doc_path to a spine document name."""
        if doc_path in spine_name_set:
            return doc_path
        bn = posixpath.basename(doc_path)
        matches = spine_basename_map.get(bn, [])
        if len(matches) == 1:
            return matches[0]
        normed = posixpath.normpath(doc_path)
        if normed in spine_name_set:
            return normed
        return doc_path

    # Fix up all TOC entries to use resolved doc paths
    all_toc_flat = _flatten_toc(toc_entries)
    for entry in all_toc_flat:
        entry.doc_path = _resolve_toc_doc(entry.doc_path)

    # ---- Build chapters from TOC -----------------------------------------
    top_entries = _top_level_toc(toc_entries)

    valid_toc: List[_TocEntry] = [
        e for e in top_entries if e.doc_path in spine_name_set
    ]

    chapters: List[BookChapter] = []
    chap_idx = 0
    p_global_idx = 0
    spine_doc_names = [item.get_name() for item, _ in spine_items]

    if valid_toc:
        # ------------------------------------------------------------------
        # TOC-based splitting
        # ------------------------------------------------------------------
        chapter_starts: List[Tuple[int, int, _TocEntry]] = []
        for entry in valid_toc:
            if entry.doc_path not in spine_name_set:
                continue
            try:
                spine_idx = spine_doc_names.index(entry.doc_path)
            except ValueError:
                warnings.append(f"TOC entry '{entry.title}' doc not in spine: {entry.doc_path}")
                continue

            elements = doc_elements.get(entry.doc_path, [])
            soup = doc_soups.get(entry.doc_path)
            if entry.fragment and elements and soup:
                el_idx = _find_anchor_element_index(elements, entry.fragment, soup)
                if el_idx < 0:
                    warnings.append(
                        f"Anchor '{entry.fragment}' not found in '{entry.doc_path}' "
                        f"for TOC entry '{entry.title}'; using document start"
                    )
                    el_idx = 0
            else:
                el_idx = 0

            chapter_starts.append((spine_idx, el_idx, entry))

        # Sort by spine index, then element index
        chapter_starts.sort(key=lambda x: (x[0], x[1]))

        # Deduplicate same-location entries
        deduped: List[Tuple[int, int, _TocEntry]] = []
        for cs in chapter_starts:
            if deduped and deduped[-1][0] == cs[0] and deduped[-1][1] == cs[1]:
                warnings.append(
                    f"Duplicate TOC location for '{cs[2].title}' and "
                    f"'{deduped[-1][2].title}'; keeping first"
                )
                continue
            deduped.append(cs)
        chapter_starts = deduped

        if not chapter_starts:
            warnings.append("All TOC entries reference documents outside the spine")
        else:
            # -- Preamble: content before first chapter --------------------
            first_spine_idx, first_el_idx, _ = chapter_starts[0]
            preamble_paras: List['BookParagraph'] = []

            for si in range(0, first_spine_idx):
                dn = spine_doc_names[si]
                elements = doc_elements.get(dn, [])
                for ei, el in enumerate(elements):
                    para = _element_to_paragraph(el, chap_idx, p_global_idx, dn, ei)
                    if para is not None:
                        p_global_idx += 1
                        para.index = p_global_idx
                        para.id = f"c{chap_idx}_p{p_global_idx}"
                        preamble_paras.append(para)

            if first_el_idx > 0:
                dn = spine_doc_names[first_spine_idx]
                elements = doc_elements.get(dn, [])
                for ei in range(0, first_el_idx):
                    el = elements[ei]
                    para = _element_to_paragraph(el, chap_idx, p_global_idx, dn, ei)
                    if para is not None:
                        p_global_idx += 1
                        para.index = p_global_idx
                        para.id = f"c{chap_idx}_p{p_global_idx}"
                        preamble_paras.append(para)

            if preamble_paras:
                from core.parser import BookChapter as _BC
                chapters.append(_BC(
                    id=f"chap_{chap_idx}",
                    title="Preamble",
                    paragraphs=preamble_paras,
                    doc_name=spine_doc_names[0],
                    order=chap_idx,
                    raw_html=doc_raw_html.get(spine_doc_names[0], ""),
                ))
                chap_idx += 1

            # -- Each chapter from TOC entries -----------------------------
            for ci, (s_idx, e_idx, toc_entry) in enumerate(chapter_starts):
                if ci + 1 < len(chapter_starts):
                    end_s_idx, end_e_idx, _ = chapter_starts[ci + 1]
                else:
                    end_s_idx = len(spine_doc_names)
                    end_e_idx = 0

                chapter_paras: List['BookParagraph'] = []
                chapter_doc_name = spine_doc_names[s_idx]

                for si in range(s_idx, min(end_s_idx + 1, len(spine_doc_names))):
                    dn = spine_doc_names[si]
                    elements = doc_elements.get(dn, [])

                    start_ei = e_idx if si == s_idx else 0
                    if si == end_s_idx and ci + 1 < len(chapter_starts):
                        stop_ei = end_e_idx
                    else:
                        stop_ei = len(elements)

                    if si > end_s_idx:
                        break

                    for ei in range(start_ei, stop_ei):
                        el = elements[ei]
                        para = _element_to_paragraph(el, chap_idx, p_global_idx, dn, ei)
                        if para is not None:
                            p_global_idx += 1
                            para.index = p_global_idx
                            para.id = f"c{chap_idx}_p{p_global_idx}"
                            chapter_paras.append(para)

                if chapter_paras:
                    chapters.append(BookChapter(
                        id=f"chap_{chap_idx}",
                        title=toc_entry.title or f"Chapter {chap_idx + 1}",
                        paragraphs=chapter_paras,
                        doc_name=chapter_doc_name,
                        order=chap_idx,
                        raw_html=doc_raw_html.get(chapter_doc_name, ""),
                    ))
                    chap_idx += 1

    # ------------------------------------------------------------------
    # Fallback: heading-based splitting when TOC is not usable
    # ------------------------------------------------------------------
    if not chapters:
        if valid_toc:
            pass  # Warning already added
        else:
            if toc_entries:
                warnings.append("TOC entries could not be resolved to spine documents; "
                                "falling back to heading-based chapter detection")
            else:
                warnings.append("No TOC found; falling back to heading-based chapter detection")

        ordered_soups = [(dn, doc_soups[dn]) for dn in spine_doc_names if dn in doc_soups]
        strongest = _detect_strongest_heading(ordered_soups)

        if strongest is None:
            warnings.append("No headings found; treating entire book as a single chapter")
            all_paras: List['BookParagraph'] = []
            for dn in spine_doc_names:
                elements = doc_elements.get(dn, [])
                for ei, el in enumerate(elements):
                    para = _element_to_paragraph(el, chap_idx, p_global_idx, dn, ei)
                    if para is not None:
                        p_global_idx += 1
                        para.index = p_global_idx
                        para.id = f"c{chap_idx}_p{p_global_idx}"
                        all_paras.append(para)
            if all_paras:
                chapters.append(BookChapter(
                    id=f"chap_{chap_idx}",
                    title=title,
                    paragraphs=all_paras,
                    doc_name=spine_doc_names[0] if spine_doc_names else "",
                    order=chap_idx,
                ))
                chap_idx += 1
        else:
            # Split on strongest heading level only
            current_paras: List['BookParagraph'] = []
            current_title = "Preamble"
            current_doc_name = spine_doc_names[0] if spine_doc_names else ""

            for dn in spine_doc_names:
                elements = doc_elements.get(dn, [])
                for ei, el in enumerate(elements):
                    if el.name == strongest:
                        if current_paras:
                            chapters.append(BookChapter(
                                id=f"chap_{chap_idx}",
                                title=current_title,
                                paragraphs=current_paras,
                                doc_name=current_doc_name,
                                order=chap_idx,
                                raw_html=doc_raw_html.get(current_doc_name, ""),
                            ))
                            chap_idx += 1
                            current_paras = []

                        heading_text = _extract_element_text(el)
                        current_title = heading_text or f"Chapter {chap_idx + 1}"
                        current_doc_name = dn

                    para = _element_to_paragraph(el, chap_idx, p_global_idx, dn, ei)
                    if para is not None:
                        p_global_idx += 1
                        para.index = p_global_idx
                        para.id = f"c{chap_idx}_p{p_global_idx}"
                        current_paras.append(para)

            if current_paras:
                chapters.append(BookChapter(
                    id=f"chap_{chap_idx}",
                    title=current_title,
                    paragraphs=current_paras,
                    doc_name=current_doc_name,
                    order=chap_idx,
                    raw_html=doc_raw_html.get(current_doc_name, ""),
                ))
                chap_idx += 1

    # ---- Assemble project ------------------------------------------------
    project = BookProject(
        id=project_id,
        title=title,
        author=author,
        source_format='epub',
        source_file_path=file_path,
        cover_image_path=cover_path,
        chapters=chapters,
    )
    project.structure_warnings = warnings  # type: ignore[attr-defined]
    project.document_type = 'novel'  # type: ignore[attr-defined]
    return project


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------

def _element_to_paragraph(
    el: Tag,
    chap_idx: int,
    p_global_idx: int,
    doc_name: str,
    element_index: int,
) -> Optional['BookParagraph']:
    """Convert a BeautifulSoup Tag to a BookParagraph, or return None if
    the element should be skipped (empty content).

    Scene breaks (``<hr>`` tags or separator paragraphs like ``* * *``)
    are preserved with tag ``'hr'``.
    """
    from core.parser import BookParagraph

    # Handle <hr> elements (scene breaks)
    if el.name == 'hr':
        return BookParagraph(
            id=f"c{chap_idx}_p{p_global_idx}",
            original_text="* * *",
            tag='hr',
            index=p_global_idx,
            source_doc=doc_name,
            source_element_index=element_index,
        )

    # Handle scene-break paragraphs
    if _is_scene_break(el):
        text = _extract_element_text(el) or "* * *"
        return BookParagraph(
            id=f"c{chap_idx}_p{p_global_idx}",
            original_text=text,
            tag='hr',
            index=p_global_idx,
            source_doc=doc_name,
            source_element_index=element_index,
        )

    text, tag_name = _extract_paragraph_text(el)
    if not text:
        return None

    css_cls = " ".join(el.get('class', [])) if el.has_attr('class') else ""

    return BookParagraph(
        id=f"c{chap_idx}_p{p_global_idx}",
        original_text=text,
        tag=tag_name,
        index=p_global_idx,
        css_class=css_cls,
        source_doc=doc_name,
        source_element_index=element_index,
    )
