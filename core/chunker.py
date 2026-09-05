"""
Context-Aware Paragraph Chunker for Literary Translation.
Groups paragraphs into optimal context windows with sliding history and structured delimiters.
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple
from core.parser import BookParagraph, BookChapter


@dataclass
class TranslationChunk:
    chunk_id: str
    chapter_id: str
    paragraphs: List[BookParagraph]
    context_before: List[str]  # The previous 2-3 translated/original paragraphs for tone/pronoun continuity

    @property
    def total_words(self) -> int:
        return sum(len(p.original_text.split()) for p in self.paragraphs)

    def format_input_prompt(self) -> str:
        """Formats the paragraphs into a structured block with clear paragraph markers."""
        formatted_paras = []
        for p in self.paragraphs:
            formatted_paras.append(f"[[[P_{p.id}]]]\n{p.original_text}")
        return "\n\n".join(formatted_paras)


class ParagraphChunker:
    """Splits a chapter's paragraphs into manageable chunks for LLM processing."""

    def __init__(self, target_word_count: int = 750, max_paragraphs: int = 10, context_window_size: int = 3):
        self.target_word_count = target_word_count
        self.max_paragraphs = max_paragraphs
        self.context_window_size = context_window_size

    def create_chunks(self, chapter: BookChapter, only_pending: bool = True) -> List[TranslationChunk]:
        paras_to_translate = []
        for p in chapter.paragraphs:
            if only_pending and p.status in ("done", "edited"):
                continue
            paras_to_translate.append(p)

        if not paras_to_translate:
            return []

        chunks: List[TranslationChunk] = []
        current_chunk_paras: List[BookParagraph] = []
        current_words = 0
        chunk_counter = 0

        # Maintain a rolling window of recent translations for context
        all_paras = chapter.paragraphs
        para_id_to_idx = {p.id: i for i, p in enumerate(all_paras)}

        for p in paras_to_translate:
            p_words = len(p.original_text.split())
            if current_chunk_paras and (current_words + p_words > self.target_word_count or len(current_chunk_paras) >= self.max_paragraphs):
                # Finalize current chunk
                first_p_idx = para_id_to_idx[current_chunk_paras[0].id]
                context_slice = all_paras[max(0, first_p_idx - self.context_window_size):first_p_idx]
                context_texts = [
                    f"[Đoạn trước]: {cp.translated_text if cp.translated_text else cp.original_text}"
                    for cp in context_slice
                ]

                chunks.append(TranslationChunk(
                    chunk_id=f"{chapter.id}_chunk_{chunk_counter}",
                    chapter_id=chapter.id,
                    paragraphs=current_chunk_paras,
                    context_before=context_texts
                ))
                chunk_counter += 1
                current_chunk_paras = [p]
                current_words = p_words
            else:
                current_chunk_paras.append(p)
                current_words += p_words

        if current_chunk_paras:
            first_p_idx = para_id_to_idx[current_chunk_paras[0].id]
            context_slice = all_paras[max(0, first_p_idx - self.context_window_size):first_p_idx]
            context_texts = [
                f"[Đoạn trước]: {cp.translated_text if cp.translated_text else cp.original_text}"
                for cp in context_slice
            ]

            chunks.append(TranslationChunk(
                chunk_id=f"{chapter.id}_chunk_{chunk_counter}",
                chapter_id=chapter.id,
                paragraphs=current_chunk_paras,
                context_before=context_texts
            ))

        return chunks

    @staticmethod
    def parse_chunk_response(response_text: str, chunk: TranslationChunk) -> Dict[str, str]:
        """
        Parses LLM output demarcated by [[[P_id]]] into a map of {paragraph_id: translated_text}.
        Includes smart fallback if LLM omitted markers.
        """
        import re

        result: Dict[str, str] = {}
        pattern = re.compile(r'\[\[\[P_([a-zA-Z0-9_\-]+)\]\]\]\s*\n?(.*?)(?=(?:\[\[\[P_|\Z))', re.DOTALL)
        matches = pattern.findall(response_text)

        if matches:
            for p_id, trans in matches:
                clean_trans = trans.strip()
                if clean_trans:
                    result[p_id] = clean_trans

        # If some or all delimiters were lost or missed:
        if len(result) < len(chunk.paragraphs):
            # Fallback: split by double newlines and match sequentially
            blocks = [b.strip() for b in re.split(r'\n\s*\n', response_text) if b.strip()]
            # Remove any stray marker tags from blocks
            clean_blocks = [re.sub(r'\[\[\[P_.*?\]\]\]', '', b).strip() for b in blocks if b.strip()]
            clean_blocks = [b for b in clean_blocks if b]

            if len(clean_blocks) == len(chunk.paragraphs):
                for p, block in zip(chunk.paragraphs, clean_blocks):
                    if p.id not in result:
                        result[p.id] = block

        return result
