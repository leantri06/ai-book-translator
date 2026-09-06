# 📚 AI Book & Research Paper Translator Pro (V3.1)

<p align="center">
  <strong>Phần mềm dịch sách & bài báo khoa học tiếng Anh sang tiếng Việt chuyên sâu với chất lượng xuất bản cao cấp</strong><br>
  <em>Hỗ trợ chạy song song đa luồng nhiều API Key, tự động bóc tách mục lục học thuật, bảo toàn công thức toán học, giữ ảnh minh họa, định nghĩa nhân vật & xưng hô đồng nhất.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Backend-green?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Multi--Key-Parallel_Engine-blueviolet?style=flat-square" alt="Multi-Key">
  <img src="https://img.shields.io/badge/Google_Gemini-3.5_Flash_%2F_Lite_%2F_Pro-orange?style=flat-square&logo=google" alt="Gemini">
  <img src="https://img.shields.io/badge/Ollama-Offline_AI_7B-purple?style=flat-square&logo=ollama" alt="Ollama">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License">
</p>

---

## 🌟 Tính Năng Nổi Bật

### 1. ⚡ Động Cơ Dịch Song Song Đa Luồng (Multi-Key Parallel Concurrency)
- **Tăng tốc theo cấp số nhân ($N \times$)**: Cho phép nhập nhiều Google Gemini API Key cùng lúc (từ nhiều tài khoản Gmail khác nhau). Mỗi key sẽ chạy trên 1 luồng độc lập:
  - 1 Key: Tốc độ chuẩn 15 RPM.
  - 3 Keys: Tốc độ nhân gấp **3 lần** (~45 RPM).
  - 6 Keys: Tốc độ nhân gấp **6 lần** (~90 RPM) — dịch xong cả cuốn tiểu thuyết 158 chương (hơn 400.000 từ) chỉ trong thời gian ngắn!
- **Cô lập Quota hoàn hảo (Isolated Key Cooldown)**: Nếu Key #1 bị chạm giới hạn 15 RPM, hệ thống chỉ tạm dừng riêng Key #1 (nghỉ 30s), trong khi **các key còn lại vẫn tiếp tục dịch liên tục**, không hề bị gián đoạn.
- **Tự động chuyển giao (Failover)**: Đoạn sách đang dịch dở trên key bị lỗi sẽ tự động được chuyển ngay cho key còn trống tiếp quản.
- **Nhận diện trực quan**: Giao diện tự động đếm số lượng key, gắn nhãn huy hiệu `🚀 N Keys (Song song)` và thông báo hệ số nhân tốc độ.

### 2. 🔍 Kiểm Tra Quota & Sức Khỏe Key 1-Chạm (1-Click Quota Health Check)
- **Nút "🔍 Kiểm tra Quota & Sức khỏe Key"** ngay trong bảng Cài đặt.
- **Kiểm tra song song trong 1-2 giây**: Quét đồng thời toàn bộ các key qua các mô hình (`gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.7-flash`).
- **Phân loại trạng thái rõ ràng**:
  - 🟢 **Sẵn sàng**: Key khỏe mạnh, còn nguyên quota để dịch ngay.
  - 🟡 **Chờ hồi lượt (15 RPM)**: Tạm nghỉ 20-30s để hồi quota phút.
  - 🟠 **Hết hạn mức 24h (Daily Quota)**: Báo rõ model đã chạm ngưỡng ngày và gợi ý model còn lượt.
  - 🔴 **Lỗi / Không hợp lệ**: Báo khi key sai định dạng hoặc bị khóa.

### 3. 🛡️ Cơ Chế Cứu Trợ Tự Động (Auto Safety-Filter Fallback)
- **Vượt qua bộ lọc kiểm duyệt quá khắt khe của Google**: Với các tác phẩm kỳ ảo/lãng mạn chứa từ ngữ nhạy cảm khiến AI từ chối phản hồi (`PROHIBITED_CONTENT`), hệ thống sẽ **tự động kích hoạt bộ dịch Google Translate thế chỗ ngay tức thì**.
- **Cam kết 100% không sót đoạn**: Không bao giờ xảy ra tình trạng bỏ sót hay để trống bất kỳ đoạn văn nào trong sách.
- **Kho mô hình dự phòng phong phú**: Tự động luân chuyển giữa `gemini-3.5-flash` ➔ `gemini-3.5-flash-lite` ➔ `gemini-3.1-flash-lite` ➔ `gemini-3.7-flash` ➔ `gemini-flash-lite-latest`.

### 4. ✍️ Văn Phong Thuần Việt & Giàu Chất Văn Học
- **Chấm dứt hoàn toàn dịch thô (word-by-word)**: Câu cú được biên tập uyển chuyển, giàu hình ảnh, nhịp điệu tự nhiên như sách xuất bản chuyên nghiệp.
- **Hỗ trợ đa dạng AI**:
  - **Google Gemini**: Dịch văn học cực hay, mát máy (0% GPU), hoàn toàn miễn phí.
  - **Ollama Offline**: Chạy 100% trên GPU cá nhân (GTX/RTX 8GB VRAM) với `qwen2.5:7b` — không cần internet, bảo mật tuyệt đối, vĩnh viễn không lo hết quota.
  - **DeepSeek (V3 / R1)**: Tốc độ cao, chi phí siêu rẻ, tiếng Việt xuất sắc.
  - **OpenAI & OpenRouter**: Hỗ trợ GPT-4o, Claude 3.5 Sonnet, v.v.

### 5. 👥 Tự Động Phân Tích Nhân Vật & Đại Từ Xưng Hô (Character Engine)
- **Nút "🤖 AI Tự phân tích nhân vật"**: Tự động quét bách khoa toàn thư tác phẩm để thiết lập danh sách nhân vật, vai trò và đại từ xưng hô phù hợp (*tôi - cậu, anh - em, chàng - nàng, sư phụ - đồ đệ*).
- **Ngăn ngừa loạn vai**: Bảo toàn xưng hô của từng cặp nhân vật từ chương đầu đến chương cuối.

### 6. 🔄 Linh Hoạt Dịch Lại ("Dịch lại từ đầu")
- Nút **`🔄 Dịch lại từ đầu`** giúp dễ dàng xóa sạch bản dịch cũ của một chương bất kỳ và dịch lại từ đầu bằng mô hình AI mới xịn hơn chỉ với 1 click.

### 7. 📖 Giao Diện Kép Hiện Đại (Studio & Reader)
- **Dual Studio (Song ngữ đối chiếu)**: Đối chiếu từng đoạn tiếng Anh và tiếng Việt, cho phép nhấp chuột sửa trực tiếp bản dịch với tính năng tự động lưu.
- **Kindle Reader Mode**: Chế độ đọc sách sang trọng, hỗ trợ tùy biến phông chữ (Merriweather Serif / Outfit Sans-serif), cỡ chữ và chế độ hiển thị:
  - *Chỉ tiếng Việt (kèm cảnh báo thông minh nếu chương chưa dịch)*
  - *Song ngữ đối chiếu từng đoạn*
  - *Chỉ tiếng Anh*

### 8. 📱 Bảo Toàn 100% Định Dạng & Xuất Bản Đa Dạng
- **Đọc đa định dạng**: Hỗ trợ **EPUB** (kể cả file sinh ra từ Calibre), **PDF**, **DOCX**, **TXT**.
- **Xuất bản chuyên nghiệp**:
  - 📕 **EPUB Tiếng Việt**: Giữ nguyên toàn bộ ảnh minh họa, trang bìa, mục lục (sẵn sàng đọc trên Kindle, Kobo, iPad).
  - 📗 **EPUB Song Ngữ**: Tuyệt vời để học tiếng Anh qua sách.
  - 📄 **Word (.DOCX)**: Đầy đủ mục lục, căn lề chuẩn in ấn.
  - 🌐 **HTML Reader / In PDF**: Trực quan, hỗ trợ bấm `Ctrl + P` lưu file PDF chuẩn sách in.

### 9. 🔬 Chuyên Sâu Dịch Bài Báo Khoa Học & Nghiên Cứu (Academic / AI Papers)
- **Tự động bóc tách mục lục chuẩn Paper**: Nhận diện thông minh các đề mục học thuật như `Abstract`, `1 Introduction`, `2 Background`, `3 Model Architecture`, `4 Why Self-Attention`, `5 Training`, `6 Results`, `7 Conclusion`, `References`... thành từng chương riêng biệt.
- **Tái tạo đoạn văn thông minh (Smart Paragraph Reconstruction)**: Tự động ghép nối các từ bị gãy dấu gạch nối cuối dòng (`transduc-\n tion` ➔ `transduction`), phát hiện chuẩn xác ranh giới đoạn văn theo cấu trúc căn lề, chấm dứt hoàn toàn tình trạng dính chữ dính đoạn.
- **Bảo toàn công thức toán học & Ký hiệu kỹ thuật**: Chế độ Prompt Học thuật chuyên sâu (`ACADEMIC_SYSTEM_PROMPT`) bảo toàn 100% công thức LaTeX, biến số ($Q, K, V, d_k, d_{model}, \text{FFN}(x)$), mã trích dẫn `[1]`, `[2]` và định danh `Figure`, `Table`.
- **Trích xuất ảnh & Nhúng sơ đồ vào file xuất bản (Word, HTML, PDF)**: Tự động trích xuất toàn bộ hình ảnh, biểu đồ từ file PDF (Figure 1, Figure 2...) và nhúng sắc nét vào file Word (.docx), file HTML Reader (hỗ trợ in ra PDF giữ trọn vẹn cả chữ lẫn hình), cũng như hiển thị trực quan ngay trên giao diện đọc sách Dual Studio.
- **Chuẩn hóa thuật ngữ AI / Khoa học máy tính**: Dịch nghĩa mượt mà kết hợp giữ thuật ngữ tiếng Anh trong ngoặc đơn (hoặc giữ nguyên các thuật ngữ quốc tế phổ biến như *Self-Attention*, *Transformer*, *Residual Connection*, *Softmax*, *Dropout*, *BLEU score*).

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Khởi động nhanh trên Windows
Chỉ cần nhấp đúp chuột vào file **`run.bat`** ở thư mục gốc:
```
d:\ai_book_translator\run.bat
```
Ứng dụng sẽ tự khởi động máy chủ và mở trình duyệt tại: **`http://localhost:8000`**.

### 2. Khởi động bằng dòng lệnh
```bash
# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt

# Khởi chạy server
python main.py
```

---

## ⚙️ Cấu Hình Chạy Song Song Đa Luồng Nhiều Key

1. Mở giao diện web tại `http://localhost:8000`.
2. Bấm vào biểu tượng **⚙️ Cài đặt API** trên thanh menu.
3. Tại ô **API Key**, dán các Gemini API Key từ nhiều tài khoản Gmail khác nhau, cách nhau bằng **dấu phẩy (,)** hoặc **xuống dòng**:
   ```text
   AIzaSyA_KeyThuNhat...,
   AIzaSyB_KeyThuHai...,
   AIzaSyC_KeyThuBa...
   ```
4. Bấm **"🔍 Kiểm tra Quota & Sức khỏe Key"** để xem báo cáo tình trạng từng Key.
5. Bấm **"Lưu Cấu Hình"**.
6. Bấm **"▶ Bắt đầu Dịch"** để trải nghiệm tốc độ dịch song song siêu tốc!

---

## 📖 Bảng So Sánh Các Nhà Cung Cấp AI

| Nhà Cung Cấp | Mô Hình Tiêu Biểu | Tốc Độ & Tài Nguyên | Chi Phí & Giới Hạn | Khuyên Dùng Cho |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini (Đa luồng)** | `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.7-flash` | Siêu nhanh, 0% GPU, hỗ trợ chạy 5-10 key song song | **Miễn phí 100%** (15 RPM / 1.500 RPD mỗi key) | **Dịch sách chất lượng cao nhất & nhanh nhất** |
| **Ollama Local** | `qwen2.5:7b` (Cần GPU 8GB VRAM) | Chạy nội bộ, ~75-82°C GPU | **$0 trọn đời**, không cần mạng, không giới hạn | Dịch tài liệu nhạy cảm, bảo mật cao |
| **DeepSeek** | `deepseek-chat` (V3), `deepseek-reasoner` (R1) | Tốc độ cao, máy chủ đám mây | Siêu rẻ (~3.000 VNĐ / cả cuốn sách) | Sách có văn phong dịch tiếng Việt cần trau chuốt |
| **Dịch tự động miễn phí** | `free-fallback` | Trung bình | Miễn phí (không cần API key) | Đọc thử nhanh, cứu hộ khi AI chặn |

---

## 🛠️ Cấu Trúc Dự Án

```
ai_book_translator/
├── core/                   # Bộ máy xử lý cốt lõi
│   ├── parser.py           # Trích xuất EPUB (hỗ trợ Calibre), PDF, DOCX, TXT
│   ├── chunker.py          # Chia đoạn ngữ cảnh thông minh, gắn mã [[[P_id]]]
│   ├── translator.py       # Engine gọi AI (Gemini, Ollama, DeepSeek, Multi-Model, Fallback)
│   ├── glossary.py         # Quản lý nhân vật, đại từ xưng hô & thuật ngữ
│   └── exporter.py         # Xuất bản EPUB tiếng Việt, EPUB song ngữ, DOCX, HTML
├── server/                 # Máy chủ backend FastAPI
│   ├── app.py              # REST API, điều khiển tiến trình & kiểm tra Quota
│   ├── database.py         # Quản lý dữ liệu dự án & tự động lưu từng đoạn
│   └── translator_worker.py# KeyPool đa luồng, cách ly quota, tự động failover
├── web/                    # Giao diện Single Page App (Dark Glassmorphism)
│   ├── index.html          # Cấu trúc giao diện Dual Studio, Reader & Modal Quota
│   ├── app.css             # Thiết kế hiện đại chuẩn giao diện cao cấp
│   └── app.js              # Logic giao diện, kiểm tra Quota, đếm key & polling
├── main.py                 # File khởi động chính
├── run.bat                 # Trình khởi chạy 1-click cho Windows
└── requirements.txt        # Danh sách thư viện cần thiết
```

---

## 📜 Bản Quyền

Dự án được phát hành theo giấy phép **MIT License**. Tự do sử dụng, chỉnh sửa và phân phối cho mục đích cá nhân và phi thương mại.
