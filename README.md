# AI Book Translator Pro (V2.0)
**Phần mềm dịch sách tiếng Anh sang tiếng Việt chuyên sâu với chất lượng xuất bản cao cấp**

Phần mềm được thiết kế dành riêng cho dịch thuật sách (tiểu thuyết văn học, light novel, sách kỹ năng, khoa học, học thuật), giải quyết dứt điểm các nhược điểm của các công cụ dịch thông thường (câu văn cứng nhắc, lộn xộn đại từ xưng hô, đứt gãy cấu trúc và mất hình ảnh minh họa).

---

## 🌟 Các Tính Năng Nổi Bật

1. **Văn phong thuần Việt & Giàu cảm xúc ("Thật Hay")**:
   - Sử dụng các mô hình ngôn ngữ lớn (LLM) hàng đầu: **Google Gemini**, **DeepSeek V3/R1**, **GPT-4o**, **Claude 3.5 Sonnet**, hoặc **Ollama chạy Offline**.
   - Tùy chỉnh giọng điệu linh hoạt theo thể loại:
     - 📖 **Tiểu thuyết / Văn học**: Câu cú uyển chuyển, giàu chất thơ và sức gợi cảm.
     - ⚔️ **Kỳ ảo / Light Novel**: Sôi nổi, chuẩn bối cảnh quý tộc/quân sự.
     - 💡 **Kỹ năng / Self-Help**: Gãy gọn, truyền cảm hứng, khúc chiết.
     - 🔬 **Khoa học / Học thuật**: Chính xác tuyệt đối, chuẩn thuật ngữ.
     - 🏛️ **Cổ điển**: Uyên bác, tao nhã.

2. **Bảo tồn nhân vật & Quy tắc xưng hô (Character Pronoun Engine)**:
   - Tự động quét và phát hiện các nhân vật xuất hiện trong sách.
   - Cho phép định nghĩa bảng xưng hô (ví dụ: *Shin & Lena* xưng hô *tôi - cậu* hoặc *anh - em*).
   - Ngăn chặn triệt để tình trạng một nhân vật bị đổi vai lung tung giữa các chương sách.

3. **Bảo toàn 100% cấu trúc sách ("Hoàn Chỉnh")**:
   - Hỗ trợ đầy đủ định dạng: **EPUB**, **PDF**, **DOCX**, **TXT**, **Markdown**.
   - Giữ nguyên mục lục chương, ảnh minh họa, trang bìa và định dạng in đậm / in nghiêng.

4. **Giao diện Studio Song Ngữ Hiện Đại (Dual-View)**:
   - **Song ngữ đối chiếu**: Xem song song văn bản gốc tiếng Anh và bản dịch tiếng Việt, nhấp chuột để chỉnh sửa trực tiếp từng đoạn văn bản với tính năng tự động lưu.
   - **Chế độ đọc sách (Reader Mode)**: Giao diện đọc thanh lịch chuẩn Kindle/Apple Books với phông chữ Serif/Sans-serif và cỡ chữ tùy chỉnh.

5. **Xuất bản đa định dạng (Export Center)**:
   - 📱 **Sách EPUB Tiếng Việt**: Đọc trên Kindle, Kobo, Apple Books, Moon+ Reader.
   - 📖 **Sách EPUB Song Ngữ**: Đoạn tiếng Anh đi kèm tiếng Việt (cực kỳ hữu ích cho người học ngoại ngữ).
   - 📄 **Word (.DOCX)**: Đã căn lề, mục lục, sẵn sàng in ấn.
   - 🌐 **HTML Reader / In PDF**: Trực quan, hỗ trợ bấm `Ctrl + P` để lưu thành file PDF chuẩn in ấn.
   - 📝 **Plain Text (.TXT)**.

6. **Chế độ dùng thử không cần API Key**:
   - Tích hợp sẵn bộ dịch cơ bản miễn phí để trải nghiệm ngay mà không cần cài đặt API key.

---

## 🚀 Hướng Dẫn Khởi Chạy

### Cách 1: Click đúp chuột (Dành cho Windows)
- Vào thư mục `d:\ai_book_translator\` và nhấp đúp chuột vào file **`run.bat`**.
- Trình duyệt web sẽ tự động mở trang ứng dụng tại: `http://localhost:8000`.

### Cách 2: Bằng dòng lệnh terminal
```bash
cd d:\ai_book_translator
python main.py
```

---

## 🔑 Hướng Dẫn Cấu Hình API

1. Nhấp vào biểu tượng bánh răng **⚙️ (Cài đặt)** ở góc trên bên phải màn hình.
2. Chọn nhà cung cấp:
   - **Google Gemini (Khuyên dùng)**:
     - Lấy API Key miễn phí 100% tại: [Google AI Studio](https://aistudio.google.com/app/apikey).
     - Mô hình khuyên dùng: `gemini-2.5-flash` (nhanh, context lớn) hoặc `gemini-2.5-pro` (văn chương sâu sắc nhất).
   - **DeepSeek**:
     - Tạo key tại [DeepSeek Platform](https://platform.deepseek.com/).
     - Chi phí rẻ và dịch văn học cực kỳ mượt mà.
   - **OpenAI / OpenRouter / Ollama Local**:
     - Điền API Key và Base URL tương ứng.
   - **Dùng thử miễn phí**:
     - Chọn `Dùng thử miễn phí` nếu bạn chưa có API key nào.
3. Bấm **Lưu Cấu Hình**.

---

## 📖 Quy Trình Dịch Một Quyển Sách Mới

1. Bấm nút **"➕ Tải sách mới"** trên thanh tiêu đề và chọn file sách (EPUB, PDF, DOCX, TXT) từ máy tính của bạn.
2. Ứng dụng sẽ tự động phân tích mục lục và hiển thị danh sách các chương bên tay trái.
3. Bấm mở bảng **"👥 Nhân vật & Văn phong"** ở góc phải:
   - Bấm **"🔍 Tự quét tên"** để AI tự động tìm tên các nhân vật trong sách.
   - Thiết lập cách xưng hô (ví dụ: *Shin* xưng *tôi*, gọi người khác là *cậu*).
   - Thêm các thuật ngữ đặc biệt cần dịch cố định.
4. Bấm **"▶ Bắt đầu Dịch"** (hoặc chọn riêng một chương và bấm *"⚡ Dịch riêng chương này"*).
5. Bạn có thể tạm dừng (Pause) hoặc tiếp tục (Resume) bất cứ lúc nào. Tiến trình dịch được lưu tự động sau từng đoạn nên không bao giờ sợ mất dữ liệu.
6. Sau khi dịch xong, bấm **"📥 Xuất Bản Sách"** để tải về file sách EPUB, DOCX hoặc HTML.
