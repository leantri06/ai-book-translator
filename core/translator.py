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

ACADEMIC_SYSTEM_PROMPT = """Bạn là Chuyên gia Dịch thuật Khoa học & Biên tập viên Tài liệu Học thuật cao cấp chuyên ngữ Anh - Việt.
Nhiệm vụ của bạn là dịch văn bản bài báo nghiên cứu, tài liệu khoa học và kỹ thuật tiếng Anh sang tiếng Việt với chuẩn mực học thuật cao nhất:

1. VĂN PHONG HỌC THUẬT, CHÍNH XÁC & KHÁCH QUAN:
   - Hành văn mạch lạc, chặt chẽ, trang trọng, chuẩn xác về mặt logic và học thuật.
   - Sử dụng lối diễn đạt khách quan, chuẩn phong cách giới nghiên cứu (ví dụ: "chúng tôi đề xuất...", "kết quả thực nghiệm cho thấy...").

2. BẢO TOÀN CÔNG THỨC TOÁN HỌC & KÝ HIỆU KỸ THUẬT:
   - TUYỆT ĐỐI KHÔNG dịch hay làm biến dạng các công thức toán học, biểu thức LaTeX, ký hiệu biến số, ma trận (ví dụ: Q, K, V, d_k, d_model, FFN(x), W^Q, W^K).
   - Bảo toàn nguyên vẹn các mã trích dẫn tài liệu tham khảo (ví dụ: [1], [13], [35, 2, 5]) và định danh hình/bảng (ví dụ: Figure 1:, Table 2:).

3. XỬ LÝ THUẬT NGỮ CHUYÊN NGÀNH (AI, KHOA HỌC MÁY TÍNH):
   - Với các thuật ngữ chuyên môn quan trọng, hãy dịch nghĩa kèm thuật ngữ gốc tiếng Anh trong ngoặc đơn (ví dụ: "cơ chế tự chú ý (self-attention)", "mã hóa vị trí (positional encoding)", "kết nối phần dư (residual connection)").
   - Nếu thuật ngữ đã trở thành quy chuẩn quốc tế và phổ biến (như Attention, Transformer, Softmax, Dropout, BLEU score, Token), có thể giữ nguyên tiếng Anh để đảm bảo độ chính xác.
   - Nghiêm ngặt tuân thủ Bảng thuật ngữ chuyên ngành (nếu được cung cấp).

4. BẢO TOÀN ĐỊNH DẠNG CẤU TRÚC:
   - Mỗi đoạn văn bản đầu vào được đánh dấu bằng mã: [[[P_{id}]]]
   - BẮT BUỘC giữ nguyên mã [[[P_{id}]]] ngay phía trên bản dịch của từng đoạn tương ứng.
   - Không được bỏ sót bất kỳ đoạn nào. Không tự ý gộp đoạn hoặc thêm lời bình luận ngoài lề.
"""


class RateLimitError(RuntimeError):
    """Raised when an API provider returns HTTP 429 (Rate limit / Quota exceeded)."""
    def __init__(self, message: str, retry_after: float = 35.0):
        super().__init__(message)
        self.retry_after = retry_after


class DailyQuotaError(RuntimeError):
    """Raised when an API key has reached its 24-hour daily quota limit."""
    pass


class AITranslator:
    """Dispatches translation requests to the chosen provider."""

    def __init__(self, provider: str = "gemini", api_key: str = "", model: str = "",
                 base_url: str = "", temperature: float = 0.3):
        self.provider = provider.lower()
        self.base_url = base_url.strip()
        self.temperature = temperature

        # Multi-key support: parse comma, semicolon, or newline separated keys
        raw_keys = api_key.replace('\r', '\n').replace(';', ',').replace('\n', ',')
        self.api_keys = [k.strip() for k in raw_keys.split(',') if k.strip()]
        self.api_key = self.api_keys[0] if self.api_keys else ""

        # Default model selection & intelligent model aliasing
        if self.provider == "gemini":
            if not model or model in ("gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"):
                self.model = "gemini-3.5-flash"
            elif model in ("gemini-2.5-pro", "gemini-1.5-pro"):
                self.model = "gemini-3.1-pro-preview"
            else:
                self.model = model
        elif self.provider in ("deepseek", "openai_compatible"):
            self.model = model or "deepseek-chat"
        elif self.provider == "openai":
            self.model = model or "gpt-4o-mini"
        else:
            self.model = model or "free-fallback"

    def translate_chunk(self, chunk: TranslationChunk, glossary: Optional[BookGlossary] = None, api_key: Optional[str] = None) -> Dict[str, str]:
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

        active_key = (api_key or self.api_key).strip()

        # Determine system prompt based on glossary tone
        is_academic = bool(glossary and getattr(glossary, "tone", "") == "academic")
        active_sys_prompt = ACADEMIC_SYSTEM_PROMPT if is_academic else LITERARY_SYSTEM_PROMPT

        if self.provider == "gemini":
            return self._translate_gemini(user_content, chunk, active_key=active_key, system_prompt=active_sys_prompt)
        elif self.provider in ("openai", "deepseek", "openai_compatible", "openrouter", "ollama"):
            return self._translate_openai_compatible(user_content, chunk, active_key=active_key, system_prompt=active_sys_prompt)
        else:
            return self._translate_free_fallback(chunk)

    def _translate_gemini(self, prompt: str, chunk: TranslationChunk, active_key: Optional[str] = None,
                          system_prompt: str = LITERARY_SYSTEM_PROMPT) -> Dict[str, str]:
        """Calls Google Gemini API directly or via google-genai with auto-fallback between models."""
        import re

        key_to_use = (active_key or self.api_key).strip()

        # Fallback to direct REST API if no key is provided or for simplicity
        if not key_to_use:
            # If no API key, fall back to free translator
            return self._translate_free_fallback(chunk)

        # Multi-model quota pool: if current model hits quota, try other high-performance models
        candidate_models = [self.model]
        for alt in ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.7-flash"):
            if alt not in candidate_models:
                candidate_models.append(alt)

        last_err = None
        last_wait_sec = 35.0

        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key_to_use}"
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
                    "parts": [{"text": system_prompt}]
                },
                "generationConfig": {
                    "temperature": self.temperature,
                    "topP": 0.95,
                    "maxOutputTokens": 8192
                }
            }

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
            except Exception as ex:
                last_err = ex
                continue

            if resp.status_code == 200:
                # Success!
                data = resp.json()
                text_output = ""
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for p in parts:
                        text_output += p.get("text", "")

                    from core.chunker import ParagraphChunker
                    parsed = ParagraphChunker.parse_chunk_response(text_output, chunk)
                    if parsed and len(parsed) > 0:
                        return parsed

                # If Google safety filter blocked (PROHIBITED_CONTENT) or response parsed empty:
                # Fallback to Google Translate engine so no paragraphs are ever lost or skipped!
                fallback_res = self._translate_free_fallback(chunk)
                if fallback_res and len(fallback_res) > 0:
                    return fallback_res

            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                pass

            # Detect rate limits (429 or quota limits)
            if resp.status_code == 429 or "quota" in err_msg.lower():
                if "generaterequestsperday" in err_msg.lower() or "per_day" in err_msg.lower() or "perday" in err_msg.lower():
                    last_err = DailyQuotaError(f"Hết hạn mức ngày (Daily Quota) của model {model_name}: {err_msg}")
                    continue

                wait_sec = 35.0
                match = re.search(r'retry in ([0-9.]+)\s*s', err_msg, re.IGNORECASE)
                if match:
                    wait_sec = float(match.group(1)) + 2.0
                elif resp.headers.get("Retry-After"):
                    try:
                        wait_sec = float(resp.headers.get("Retry-After")) + 2.0
                    except Exception:
                        pass
                last_wait_sec = wait_sec
                last_err = RateLimitError(f"Lỗi Gemini API (429): {err_msg}", retry_after=wait_sec)
                # Try next model in candidate_models before giving up!
                continue

            last_err = RuntimeError(f"Lỗi Gemini API ({resp.status_code}): {err_msg}")

        # Safety net: If all AI models hit quota/errors, translate via free engine to guarantee 100% completion
        try:
            fallback_res = self._translate_free_fallback(chunk)
            if fallback_res and len(fallback_res) > 0:
                return fallback_res
        except Exception:
            pass

        if isinstance(last_err, (RateLimitError, DailyQuotaError)):
            raise last_err
        if last_err:
            raise last_err
        raise RuntimeError("Không thể nhận phản hồi từ Gemini API.")

    def _translate_openai_compatible(self, prompt: str, chunk: TranslationChunk, active_key: Optional[str] = None,
                                     system_prompt: str = LITERARY_SYSTEM_PROMPT) -> Dict[str, str]:
        """Calls any OpenAI-compatible API (DeepSeek, OpenRouter, OpenAI, Local Ollama)."""
        base_url = self.base_url.rstrip("/") if self.base_url else "https://api.deepseek.com/v1"
        url = f"{base_url}/chat/completions"

        key_to_use = (active_key or self.api_key).strip()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key_to_use}" if key_to_use else "Bearer none"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
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

            if resp.status_code == 429:
                wait_sec = 25.0
                if resp.headers.get("Retry-After"):
                    try:
                        wait_sec = float(resp.headers.get("Retry-After")) + 2.0
                    except Exception:
                        pass
                raise RateLimitError(f"Lỗi API (429): {err_msg}", retry_after=wait_sec)

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
