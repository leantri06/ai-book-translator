"""
AI Literary Translation Engine supporting Gemini, OpenAI-compatible APIs (DeepSeek, OpenRouter, Ollama),
and Free Fallback for instant testing.
"""
from typing import Dict, List, Optional, Any
import os
import json
import time
import requests
from core.chunker import TranslationChunk
from core.glossary import BookGlossary


LITERARY_SYSTEM_PROMPT = """Bạn là Dịch giả Văn học & Biên tập viên Sách cao cấp chuyên ngữ Anh - Việt.
Nhiệm vụ của bạn là dịch văn bản sách tiếng Anh sang tiếng Việt với chất lượng xuất bản cao nhất, thỏa mãn các tiêu chí khắt khe:

1. VĂN PHONG MƯỢT MÀ, THUẦN VIỆT & GIÀU CẢM XÚC:
   - Tuyệt đối không dịch thô chữ-đối-chữ (word-by-word) hay hành văn Tây hóa gượng gạo.
   - Câu văn tiếng Việt cần uyển chuyển, giàu hình ảnh, nhịp điệu tự nhiên, câu cú thanh thoát.
   - Chuyển đổi linh hoạt thể bị động tiếng Anh sang thể chủ động hoặc lối diễn đạt tự nhiên trong tiếng Việt.

2. BẢO TOÀN XƯNG HÔ & TÍNH CÁCH NHÂN VẬT:
   - Nghiêm ngặt tuân theo Bảng quy tắc xưng hô nhân vật được cung cấp (nếu có).
   - Lời thoại nhân vật phải chân thực, đúng tâm trạng, bối cảnh thời đại và quan hệ giai cấp/tình cảm.

3. XỬ LÝ THÀNH NGỮ, ẨN DỤ & THUẬT NGỮ:
   - Chuyển ngữ thành ngữ, tiếng lóng, lối nói bóng gió sang thành ngữ hoặc cách nói tương đương trong tiếng Việt.
   - Giữ nguyên tên riêng nhân vật, địa danh hoặc chuyển đổi đúng chuẩn quy định trong bảng thuật ngữ.

4. BẢO TOÀN ĐỊNH DẠNG CẤU TRÚC:
   - Mỗi đoạn văn bản đầu vào được đánh dấu bằng mã: [[[P_{id}]]]
   - BẮT BUỘC giữ nguyên mã [[[P_{id}]]] ngay phía trên bản dịch của từng đoạn tương ứng.
   - Không được bỏ sót bất kỳ đoạn nào. Không tự ý gộp đoạn hoặc thêm lời bình luận ngoài lề.
"""


class AITranslator:
    """Dispatches translation requests to the chosen provider."""

    def __init__(self, provider: str = "gemini", api_key: str = "", model: str = "",
                 base_url: str = "", temperature: float = 0.3):
        self.provider = provider.lower()
        self.api_key = api_key.strip()
        self.base_url = base_url.strip()
        self.temperature = temperature

        # Default model selection & intelligent model aliasing
        if self.provider == "gemini":
            if not model or model in ("gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"):
                self.model = "gemini-3.6-flash"
            elif model in ("gemini-2.5-pro", "gemini-1.5-pro"):
                self.model = "gemini-3.6-pro"
            else:
                self.model = model
        elif self.provider in ("deepseek", "openai_compatible"):
            self.model = model or "deepseek-chat"
        elif self.provider == "openai":
            self.model = model or "gpt-4o-mini"
        else:
            self.model = model or "free-fallback"

    def translate_chunk(self, chunk: TranslationChunk, glossary: Optional[BookGlossary] = None) -> Dict[str, str]:
        """Translates a structured chunk and returns {para_id: translated_text}."""
        glossary_context = glossary.build_prompt_context() if glossary else ""

        # Context preceding paragraphs
        context_str = ""
        if chunk.context_before:
            context_str = "=== NGỮ CẢNH CÁC ĐOẠN LIỀN TRƯỚC (ĐỂ LIỀN MẠCH CẢM XÚC VÀ XƯNG HÔ) ===\n" + "\n".join(chunk.context_before) + "\n\n"

        user_content = (
            f"{glossary_context}\n\n"
            f"{context_str}"
            f"=== CÁC ĐOẠN CẦN DỊCH (HÃY DỊCH TỪNG ĐOẠN VÀ GIỮ MÃ ĐÁNH DẤU [[[P_id]]]) ===\n"
            f"{chunk.format_input_prompt()}"
        )

        if self.provider == "gemini":
            return self._translate_gemini(user_content, chunk)
        elif self.provider in ("openai", "deepseek", "openai_compatible", "openrouter", "ollama"):
            return self._translate_openai_compatible(user_content, chunk)
        else:
            return self._translate_free_fallback(chunk)

    def _translate_gemini(self, prompt: str, chunk: TranslationChunk) -> Dict[str, str]:
        """Calls Google Gemini API directly or via google-genai."""
        # Fallback to direct REST API if no key is provided or for simplicity
        if not self.api_key:
            # If no API key, fall back to free translator
            return self._translate_free_fallback(chunk)

        # Direct REST API to Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": LITERARY_SYSTEM_PROMPT}]
            },
            "generationConfig": {
                "temperature": self.temperature,
                "topP": 0.95,
                "maxOutputTokens": 8192
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                pass
            raise RuntimeError(f"Lỗi Gemini API ({resp.status_code}): {err_msg}")

        data = resp.json()
        text_output = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                text_output += p.get("text", "")

        from core.chunker import ParagraphChunker
        return ParagraphChunker.parse_chunk_response(text_output, chunk)

    def _translate_openai_compatible(self, prompt: str, chunk: TranslationChunk) -> Dict[str, str]:
        """Calls any OpenAI-compatible API (DeepSeek, OpenRouter, OpenAI, Local Ollama)."""
        base_url = self.base_url.rstrip("/") if self.base_url else "https://api.deepseek.com/v1"
        url = f"{base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "Bearer none"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": LITERARY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                pass
            raise RuntimeError(f"Lỗi API ({resp.status_code}): {err_msg}")

        data = resp.json()
        text_output = data["choices"][0]["message"]["content"]

        from core.chunker import ParagraphChunker
        return ParagraphChunker.parse_chunk_response(text_output, chunk)

    def _translate_free_fallback(self, chunk: TranslationChunk) -> Dict[str, str]:
        """
        Free translation fallback using public translation endpoint.
        Useful for zero-setup demo testing when no API key has been entered yet.
        """
        results: Dict[str, str] = {}
        for p in chunk.paragraphs:
            text = p.original_text.strip()
            if not text:
                results[p.id] = ""
                continue
            try:
                # Use Google Translate free endpoint
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    "client": "gtx",
                    "sl": "en",
                    "tl": "vi",
                    "dt": "t",
                    "q": text
                }
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    translated = "".join([segment[0] for segment in data[0] if segment[0]])
                    results[p.id] = translated
                else:
                    results[p.id] = f"[Dịch tự động tạm thời]: {text}"
            except Exception:
                results[p.id] = f"[Chưa dịch]: {text}"
            time.sleep(0.1)  # small pause to avoid rate limit

        return results
