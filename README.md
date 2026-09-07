# 📚 AI Book & Research Paper Translator Pro (V3.5)

<p align="center">
  <strong>Phần mềm dịch sách & bài báo khoa học tiếng Anh sang tiếng Việt chuyên sâu với chất lượng xuất bản cao cấp</strong><br>
  <em>Hỗ trợ chạy song song đa luồng nhiều API Key, bóc tách chuẩn bố cục 2 cột (Two-Column Paper), bóc tách bảng biểu & sơ đồ vector không viền, công thức toán chuẩn Kindle (EPUB / MathML), định nghĩa nhân vật & xưng hô đồng nhất.</em>
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
  - 6 Keys: Tốc độ nhân gấp **6 lần** (~90 RPM) — dịch xong cả cuốn tiểu thuyết hoặc bài báo khoa học lớn chỉ trong vài phút!
- **Cô lập Quota hoàn hảo (Isolated Key Cooldown)**: Nếu Key #1 bị chạm giới hạn 15 RPM, hệ thống chỉ tạm dừng riêng Key #1 (nghỉ 30s), trong khi **các key còn lại vẫn tiếp tục dịch liên tục**, không hề bị gián đoạn.
- **Tự động chuyển giao (Failover)**: Đoạn sách đang dịch dở trên key bị lỗi sẽ tự động được chuyển ngay cho key còn trống tiếp quản.
- **Nhận diện trực quan**: Giao diện tự động đếm số lượng key, gắn nhãn huy hiệu `🚀 N Keys (Song song)` và thông báo hệ số nhân tốc độ.

### 2. 🔬 Chuyên Sâu Dịch Bài Báo Khoa Học & Bố Cục 2 Cột (Academic / AI Papers V3.5)
- **Bóc tách cấu trúc 2 cột thông minh (Two-Column Paper Structure)**:
  - Tự động nhận diện chuẩn xác các đề mục học thuật như `Abstract`, `1 Introduction`, `2 Methodology`, `3 Results`, `4 Discussion and Future Work`, `5 Related Work`, `6 Conclusions`, `References`... thành từng chương riêng biệt.
  - Phân tích luồng đọc theo cột (đọc hết cột trái rồi sang cột phải), không bị xáo trộn câu chữ giữa hai cột văn bản liền kề.
- **Bảo tồn Bảng biểu không viền & Chống cắt nuốt văn bản (Table Continuity Clustering)**:
  - Tự động phát hiện vị trí các bảng biểu (chuẩn LaTeX booktabs, bảng không viền dọc) và kết xuất thành ảnh PNG độ nét cao (250 DPI).
  - **Phân vùng cột chặt chẽ & Liên kết khoảng cách liên tục**: Giới hạn tọa độ theo từng cột (`pw * 0.45` / `pw * 0.55`), tự động loại trừ các khối ghi chú đặc biệt (callout boxes như `RQ1`, `RQ2`), chấm dứt triệt để lỗi cắt bảng quá tay nuốt mất văn bản bên dưới.
  - **Loại trừ triệt để dữ liệu số liệu thô trong bảng khỏi luồng dịch**: Giữ lại tiêu đề bảng để dịch chuẩn xác sang tiếng Việt (`Bảng 1`, `Bảng 2`...), không làm AI dịch nhầm số liệu ma trận hay bảng thống kê.
- **Trích xuất Sơ đồ Vector & Biểu đồ trực quan (PyMuPDF Vector Engine)**:
  - Quét và trích xuất không chỉ ảnh raster thông thường mà cả các **sơ đồ Vector Graphics**, Form XObjects, hình vẽ kiến trúc (như Figure 1, Figure 2 trong Transformer), biểu đồ Attention Visualizations và kết xuất thành ảnh PNG 250 DPI sắc nét.
  - Tự động mở rộng lề trên (`union_r.y0 - 35`) đảm bảo các nhãn văn bản của sơ đồ không bị cắt xén.
- **Định dạng Công thức Toán học chuẩn mực (Kindle Math & MathML Engine)**:
  - Tự động cô lập công thức toán độc lập có đánh số hiệu (`(1)`, `(2)`, `(3)`) và tách biệt hoàn toàn khỏi đoạn văn xuôi phía sau.
  - Hỗ trợ cú pháp chuẩn `\tag{...}`, gộp các khối công thức liên tiếp thành một thẻ `.math-block` liền mạch, có khung hiển thị chuyên nghiệp.
  - Tự động chuyển đổi công thức LaTeX sang ảnh PNG 300 DPI nền trong suốt nhúng vào EPUB, tương thích hoàn hảo 100% với máy đọc sách Kindle Paperwhite, Oasis, Scribe, app Kindle và hỗ trợ Dark Mode.
- **Lọc sạch Header & Footer trang bài báo**:
  - Tự động loại bỏ hoàn toàn các running header hội nghị (`FORGE '26...`, arXiv timestamps) và số trang chạy đầu/cuối trang, giữ nội dung dịch liền mạch và chuẩn sách in.
- **Tái tạo đoạn văn thông minh (Smart Paragraph Reconstruction)**:
  - Tự động ghép nối các từ bị gãy dấu gạch nối cuối dòng (`transduc-\n tion` ➔ `transduction`), phát hiện chuẩn xác ranh giới đoạn văn theo cấu trúc căn lề, chấm dứt hoàn toàn tình trạng dính chữ dính đoạn.

### 3. 🔍 Kiểm Tra Quota & Sức Khỏe Key 1-Chạm (1-Click Quota Health Check)
- **Nút "🔍 Kiểm tra Quota & Sức khỏe Key"** ngay trong bảng Cài đặt.
- **Kiểm tra song song trong 1-2 giây**: Quét đồng thời toàn bộ các key qua các mô hình (`gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.7-flash`).
- **Phân loại trạng thái rõ ràng**:
  - 🟢 **Sẵn sàng**: Key khỏe mạnh, còn nguyên quota để dịch ngay.
  - 🟡 **Chờ hồi lượt (15 RPM)**: Tạm nghỉ 20-30s để hồi quota phút.
  - 🟠 **Hết hạn mức 24h (Daily Quota)**: Báo rõ model đã chạm ngưỡng ngày và gợi ý model còn lượt.
  - 🔴 **Lỗi / Không hợp lệ**: Báo khi key sai định dạng hoặc bị khóa.

### 4. 🛡️ Cơ Chế Cứu Trợ Tự Động (Auto Safety-Filter Fallback)
- **Vượt qua bộ lọc kiểm duyệt quá khắt khe của Google**: Với các tác phẩm kỳ ảo/lãng mạn chứa từ ngữ nhạy cảm khiến AI từ chối phản hồi (`PROHIBITED_CONTENT`), hệ thống sẽ **tự động kích hoạt bộ dịch Google Translate thế chỗ ngay tức thì**.
- **Cam kết 100% không sót đoạn**: Không bao giờ xảy ra tình trạng bỏ sót hay để trống bất kỳ đoạn văn nào trong sách.
- **Kho mô hình dự phòng phong phú**: Tự động luân chuyển giữa `gemini-3.5-flash` ➔ `gemini-3.5-flash-lite` ➔ `gemini-3.1-flash-lite` ➔ `gemini-3.7-flash` ➔ `gemini-flash-lite-latest`.

### 5. ✍️ Văn Phong Thuần Việt & Giàu Chất Văn Học
- **Chấm dứt hoàn toàn dịch thô (word-by-word)**: Câu cú được biên tập uyển chuyển, giàu hình ảnh, nhịp điệu tự nhiên như sách xuất bản chuyên nghiệp.
- **Hỗ trợ đa dạng AI**:
  - **Google Gemini**: Dịch văn học cực hay, mát máy (0% GPU), hoàn toàn miễn phí.
  - **Ollama Offline**: Chạy 100% trên GPU cá nhân (GTX/RTX 8GB VRAM) với `qwen2.5:7b` — không cần internet, bảo mật tuyệt đối, vĩnh viễn không lo hết quota.
  - **DeepSeek (V3 / R1)**: Tốc độ cao, chi phí siêu rẻ, tiếng Việt xuất sắc.
  - **OpenAI & OpenRouter**: Hỗ trợ GPT-4o, Claude 3.5 Sonnet, v.v.

### 6. 👥 Quản Lý Nhân Vật, Thuật Ngữ & Dự Án Chuyên Nghiệp
- **AI Tự phân tích nhân vật**: Tự động quét bách khoa toàn thư tác phẩm để thiết lập danh sách nhân vật, vai trò và đại từ xưng hô phù hợp (*tôi - cậu, anh - em, chàng - nàng, sư phụ - đồ đệ*).
- **Chuẩn hóa thuật ngữ AI / Khoa học máy tính**: Giữ thuật ngữ tiếng Anh trong ngoặc đơn (hoặc giữ nguyên các thuật ngữ quốc tế phổ biến như *Self-Attention*, *Transformer*, *Residual Connection*, *Softmax*, *Dropout*, *BLEU score*).
- **Xóa dự án an toàn 1-chạm (Safe Delete Modal)**: Nút xóa kèm cửa sổ xác nhận cảnh báo màu đỏ, hỗ trợ xóa sạch dữ liệu, cache và ảnh đã trích xuất ngay lập tức mà không cần F5.

### 7. 🔄 Linh Hoạt Dịch Lại ("Dịch lại từ đầu")
- Nút **`🔄 Dịch lại từ đầu`** giúp dễ dàng xóa sạch bản dịch cũ của một chương bất kỳ và dịch lại từ đầu bằng mô hình AI mới xịn hơn chỉ với 1 click.

### 8. 📖 Giao Diện Kép Hiện Đại (Studio & Reader)
- **Dual Studio (Song ngữ đối chiếu)**: Đối chiếu từng đoạn tiếng Anh và tiếng Việt, cho phép nhấp chuột sửa trực tiếp bản dịch với tính năng tự động lưu.
- **Kindle Reader Mode**: Chế độ đọc sách sang trọng, hỗ trợ tùy biến phông chữ (Merriweather Serif / Outfit Sans-serif), cỡ chữ và chế độ hiển thị:
  - *Chỉ tiếng Việt (kèm cảnh báo thông minh nếu chương chưa dịch)*
  - *Song ngữ đối chiếu từng đoạn*
  - *Chỉ tiếng Anh*

### 9. 📱 Bảo Toàn 100% Định Dạng & Xuất Bản Đa Dạng
- **Đọc đa định dạng**: Hỗ trợ **EPUB** (kể cả file sinh ra từ Calibre), **PDF**, **DOCX**, **TXT**.
- **Xuất bản chuyên nghiệp**:
  - 📕 **EPUB Tiếng Việt**: Giữ nguyên toàn bộ ảnh minh họa, trang bìa, mục lục (sẵn sàng đọc trên Kindle, Kobo, iPad).
  - 📗 **EPUB Song Ngữ**: Tuyệt vời để học tiếng Anh qua sách.
  - 📄 **Word (.DOCX)**: Đầy đủ mục lục, căn lề chuẩn in ấn.
  - 🌐 **HTML Reader / In PDF**: Trực quan, nhúng ảnh base64 độc lập, hỗ trợ bấm `Ctrl + P` lưu file PDF chuẩn sách in.

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Khởi động nhanh trên Windows (Khuyên dùng)
Chỉ cần nhấp đúp chuột vào file **`run.bat`** ở thư mục gốc:
```bat
d:\ai_book_translator\run.bat
```
- File `run.bat` thế hệ mới sẽ **tự động kiểm tra Python**, **tự cài đặt thư viện thiếu** qua `requirements.txt`, thiết lập mã hóa UTF-8 và tự động mở trình duyệt tại: **`http://localhost:8000`**.

### 2. Khởi động thủ công bằng dòng lệnh
```bash
# 1. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 2. Khởi chạy server
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
│   ├── parser.py           # Trích xuất EPUB (Calibre), PDF 2 cột, DOCX, TXT, sơ đồ vector & bảng
│   ├── chunker.py          # Chia đoạn ngữ cảnh thông minh, gắn mã [[[P_id]]]
│   ├── translator.py       # Engine gọi AI (Gemini, Ollama, DeepSeek, Multi-Model, Fallback)
│   ├── glossary.py         # Quản lý nhân vật, đại từ xưng hô & thuật ngữ
│   └── exporter.py         # Xuất bản EPUB Kindle, EPUB song ngữ, DOCX, HTML standalone
├── server/                 # Máy chủ backend FastAPI
│   ├── app.py              # REST API, điều khiển tiến trình, xóa dự án & kiểm tra Quota
│   ├── database.py         # Quản lý dữ liệu dự án & tự động lưu từng đoạn
│   └── translator_worker.py# KeyPool đa luồng, cách ly quota, tự động failover
├── web/                    # Giao diện Single Page App (Dark Glassmorphism)
│   ├── index.html          # Cấu trúc giao diện Dual Studio, Reader & Modal Quota / Delete
│   ├── app.css             # Thiết kế hiện đại chuẩn giao diện cao cấp
│   └── app.js              # Logic giao diện, kiểm tra Quota, đếm key, modal xóa & polling
├── data/                   # Dữ liệu người dùng (dự án, upload & file xuất bản)
│   ├── projects/           # Lưu trữ các chương sách, ảnh trích xuất và thuật ngữ
│   ├── uploads/            # File PDF/EPUB/DOCX tải lên
│   └── exports/            # File đầu ra đã xuất (.epub, .docx, .html)
├── main.py                 # File khởi động chính (tự động dò cổng và mở trình duyệt)
├── run.bat                 # Trình khởi chạy 1-click cho Windows (tự kiểm tra dependencies)
└── requirements.txt        # Danh sách thư viện cần thiết
```

---

## 📜 Bản Quyền

Dự án được phát hành theo giấy phép **MIT License**. Tự do sử dụng, chỉnh sửa và phân phối cho mục đích cá nhân và phi thương mại.
