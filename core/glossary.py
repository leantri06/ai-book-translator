"""
Glossary & Character Pronoun Management for Literary Translation.
Maintains consistent character names, pronouns (xưng hô), and domain terms across chapters.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import json
import re


@dataclass
class CharacterPronoun:
    name: str                       # Character name, e.g. "Shin", "Lena"
    gender: str = "male"            # male, female, neutral, other
    role: str = ""                  # e.g. "Đội trưởng Spearhead", "Sĩ quan chỉ huy"
    first_person: str = "tôi"       # Tôi / mình / ta / anh / em
    second_person: str = "cậu"      # Cậu / bạn / em / ngài / anh
    third_person: str = "cậu ấy"    # Anh ấy / cô ấy / chàng trai / thiếu nữ / hắn / gã
    notes: str = ""                 # Ghi chú thêm về xưng hô với người khác


@dataclass
class TerminologyItem:
    source_term: str                # e.g. "Juggernaut"
    target_term: str                # e.g. "Juggernaut" or "Cỗ máy tử thần Juggernaut"
    category: str = "general"       # weapon, location, organization, general
    description: str = ""           # e.g. "Phương tiện chiến đấu không người lái của Cộng hòa San Magnolia"


class BookGlossary:
    """Manages character pronouns and terms for a specific book translation project."""

    def __init__(self):
        self.characters: Dict[str, CharacterPronoun] = {}
        self.terms: Dict[str, TerminologyItem] = {}
        self.tone: str = "novel"  # novel, academic, selfhelp, classic, fantasy
        self.custom_instructions: str = ""

    def add_character(self, name: str, gender: str = "male", role: str = "",
                      first_person: str = "tôi", second_person: str = "cậu",
                      third_person: str = "cậu ấy", notes: str = "") -> CharacterPronoun:
        char = CharacterPronoun(
            name=name.strip(),
            gender=gender,
            role=role.strip(),
            first_person=first_person.strip(),
            second_person=second_person.strip(),
            third_person=third_person.strip(),
            notes=notes.strip()
        )
        self.characters[char.name.lower()] = char
        return char

    def add_term(self, source: str, target: str, category: str = "general", description: str = "") -> TerminologyItem:
        item = TerminologyItem(
            source_term=source.strip(),
            target_term=target.strip(),
            category=category.strip(),
            description=description.strip()
        )
        self.terms[item.source_term.lower()] = item
        return item

    def get_character(self, name: str) -> Optional[CharacterPronoun]:
        return self.characters.get(name.lower())

    def get_term(self, source: str) -> Optional[TerminologyItem]:
        return self.terms.get(source.lower())

    def build_prompt_context(self) -> str:
        """Constructs a compact glossary and style guide string to inject into LLM prompts."""
        lines = []

        # 1. TONE AND STYLE GUIDELINE
        tone_guides = {
            "novel": (
                "- THỂ LOẠI: Tiểu thuyết / Văn học (Fiction/Novel).\n"
                "- PHONG CÁCH: Văn phong mượt mà, thuần Việt, giàu cảm xúc, giàu sức gợi cảm và hình tượng.\n"
                "- CÂU VĂN: Tránh tuyệt đối dịch thô chữ-đối-chữ hoặc lối hành văn Tây hóa cứng nhắc. "
                "Biến đổi linh hoạt câu chủ động/bị động để câu văn tự nhiên nhất.\n"
                "- THOẠI: Lời thoại nhân vật tự nhiên, biểu cảm, đúng tính cách và tâm trạng."
            ),
            "selfhelp": (
                "- THỂ LOẠI: Sách Kỹ năng / Phát triển bản thân (Self-Help / Non-Fiction).\n"
                "- PHONG CÁCH: Truyền cảm hứng, gãy gọn, khúc chiết, thuyết phục, mạch lạc.\n"
                "- ĐẠI TỪ: Dùng xưng hô thân thiện, tạo sự gắn kết (thường là 'bạn' hoặc 'chúng ta')."
            ),
            "academic": (
                "- THỂ LOẠI: Học thuật / Nghiên cứu / Khoa học (Academic / Science).\n"
                "- PHONG CÁCH: Trang trọng, chính xác tuyệt đối, lập luận chặt chẽ, chuẩn thuật ngữ chuyên ngành."
            ),
            "fantasy": (
                "- THỂ LOẠI: Kỳ ảo / Light Novel / Kiếm hiệp / Giả tưởng (Fantasy / Sci-Fi).\n"
                "- PHONG CÁCH: Sôi nổi, kỳ ảo, xưng hô tôn trọng bối cảnh truyện (quý tộc, quân đội, hiệp sĩ)."
            ),
            "classic": (
                "- THỂ LOẠI: Văn học Cổ điển (Classic Literature).\n"
                "- PHONG CÁCH: Uyên bác, tao nhã, câu từ cổ kính, trau chuốt từng dấu phẩy và nhịp điệu."
            )
        }

        lines.append("=== QUY CHUẨN DỊCH THUẬT & PHONG CÁCH ===")
        lines.append(tone_guides.get(self.tone, tone_guides["novel"]))

        # 2. CHARACTER PRONOUN TABLE
        if self.characters:
            lines.append("\n=== BẢNG QUY TẮC XƯNG HÔ NHÂN VẬT (BẮT BUỘC TUÂN THỦ ĐỒNG NHẤT) ===")
            for char in self.characters.values():
                info = f"- {char.name} ({char.gender}, {char.role}): Ngôi 1: '{char.first_person}', Ngôi 2: '{char.second_person}', Ngôi 3: '{char.third_person}'."
                if char.notes:
                    info += f" Lưu ý: {char.notes}"
                lines.append(info)

        # 3. TERMINOLOGY TABLE
        if self.terms:
            lines.append("\n=== BẢNG THUẬT NGỮ & TÊN RIÊNG (GIỮ NGUYÊN HOẶC DỊCH CHUẨN) ===")
            for item in self.terms.values():
                desc = f" ({item.description})" if item.description else ""
                lines.append(f"- '{item.source_term}' -> '{item.target_term}'{desc}")

        # 4. CUSTOM USER INSTRUCTIONS
        if self.custom_instructions:
            lines.append(f"\n=== LƯU Ý ĐẶC BIỆT TỪ NGƯỜI BIÊN DỊCH ===\n{self.custom_instructions}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "tone": self.tone,
            "custom_instructions": self.custom_instructions,
            "characters": [asdict(c) for c in self.characters.values()],
            "terms": [asdict(t) for t in self.terms.values()]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BookGlossary":
        glossary = cls()
        glossary.tone = data.get("tone", "novel")
        glossary.custom_instructions = data.get("custom_instructions", "")
        for c in data.get("characters", []):
            glossary.add_character(**c)
        for t in data.get("terms", []):
            glossary.add_term(
                source=t.get("source_term", ""),
                target=t.get("target_term", ""),
                category=t.get("category", "general"),
                description=t.get("description", "")
            )
        return glossary
