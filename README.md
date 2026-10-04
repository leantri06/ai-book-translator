# 📖 AI Book & Research Paper Translator Pro

<p align="center">
  <img src="https://img.shields.io/badge/Release-v4.1.0-brightgreen.svg?style=flat-square" alt="Release v4.1.0">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg?style=flat-square" alt="Python Versions">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat-square" alt="FastAPI">
  <img src="https://img.shields.io/badge/Interface-Modern%20Dark%20Studio-6366f1.svg?style=flat-square" alt="Modern Dark Studio">
  <img src="https://img.shields.io/badge/Engines-Gemini%20%7C%20DeepSeek%20%7C%20OpenAI%20%7C%20Ollama-orange.svg?style=flat-square" alt="AI Engines">
</p>

Ứng dụng dịch thuật sách, tiểu thuyết và tài liệu/bài báo nghiên cứu khoa học chuyên nghiệp chạy cục bộ (local-first). Tích hợp các mô hình ngôn ngữ lớn (Google Gemini, DeepSeek, OpenAI, OpenRouter, Ollama cục bộ) kết hợp công nghệ xử lý bố cục chuyên sâu, quản lý nhân vật & thuật ngữ nhất quán, đối chiếu song ngữ trực quan và xuất bản đa định dạng chuẩn in ấn.

---

## 📑 Mục lục

1. [Điểm nổi bật & Tính năng cốt lõi](#1-điểm-nổi-bật--tính-năng-cốt-lõi)
2. [So sánh 2 luồng: Paper PDF vs Novel Ebook](#2-so-sánh-2-luồng-paper-pdf-vs-novel-ebook)
3. [Cài đặt & Khởi động nhanh](#3-cài-đặt--khởi-động-nhanh)
4. [Hướng dẫn sử dụng từng bước](#4-hướng-dẫn-sử-dụng-từng-bước)
5. [Cấu hình các nhà cung cấp AI](#5-cấu-hình-các-nhà-cung-cấp-ai)
6. [Quản lý nhân vật, xưng hô và thuật ngữ](#6-quản-lý-nhân-vật-xưng-hô-và-thuật-ngữ)
7. [Không gian làm việc & Biên tập](#7-không-gian-làm-việc--biên-tập)
8. [Xuất bản tài liệu](#8-xuất-bản-tài-liệu)
9. [Cấu trúc dữ liệu & Sao lưu](#9-cấu-trúc-dữ-liệu--sao-lưu)
10. [Xử lý sự cố thường gặp (FAQ)](#10-xử-lý-sự-cố-thường-gặp-faq)
11. [Phát triển & Kiểm thử](#11-phát-triển--kiểm-thử)
12. [Bảo mật & Giới hạn sử dụng](#12-bảo-mật--giới-hạn-sử-dụng)

---

## 1. Điểm nổi bật & Tính năng cốt lõi

### 🎓 Luồng Paper PDF (Academic Research Engine)
- **Tách cột thông minh (Two-column Detection):** Tự động phân tích hình học trang, xử lý bài báo học thuật 2 cột phức tạp mà không bị xáo trộn thứ tự đọc.
- **Bảo tồn hình ảnh & biểu đồ vector:** Tích hợp PyMuPDF trích xuất sơ đồ khoa học ở độ nét cao (chuẩn Kindle 300 DPI).
- **Nhận diện bảng & công thức:** Giữ nguyên bảng số liệu, hỗ trợ công thức toán học LaTeX & MathML.
- **Lọc nhiễu tài liệu:** Tự động phát hiện và loại bỏ running headers, running footers, số trang và watermark lặp ở mép tài liệu.
- **Chuẩn hóa văn phong học thuật:** Tự động cố định giọng văn học thuật (`academic tone`), tối ưu hóa việc truyền tải các khái niệm nghiên cứu.

### 📚 Luồng Novel Ebook (Tiểu thuyết & Sách điện tử)
- **Hỗ trợ đa định dạng:** Đọc và phân tích sâu file EPUB (spine, TOC, anchor fragment), Microsoft Word (.docx), Markdown (.md) và Plain Text (.txt).
- **Hệ thống nhân vật & xưng hô thông minh:** Thiết lập đại từ xưng hô linh hoạt cho từng cặp nhân vật (tôi – cậu, anh – em, cô – hắn...).
- **Phân tích nhân vật tự động bằng AI (AI Auto-detect):** Quét nội dung chương đầu và tự động nhận diện danh sách nhân vật chính cùng gợi ý quan hệ.
- **Đa dạng giọng văn:** Tùy chọn giọng văn phù hợp với từng thể loại: *Tiểu thuyết / Văn học*, *Kỳ ảo / Light Novel*, *Kỹ năng / Self-Help*, *Văn học cổ điển*.
- **Từ điển thuật ngữ (Glossary) & Chỉ dẫn riêng:** Cố định cách dịch tên riêng, địa danh, vũ khí, thuật ngữ chuyên ngành xuyên suốt toàn bộ tác phẩm.

### 🔄 Chuyển đổi Giáo trình PDF → EPUB (Textbook Engine)
- Công cụ chuyên biệt xử lý các bộ giáo trình, tài liệu học tập PDF tiếng Việt dày hàng trăm trang.
- Bóc tách phân cấp chương mục (Chương I, Chương II, Mục 1, Mục 2...) và đóng gói thành file EPUB chuẩn tương thích hoàn hảo với mọi ứng dụng đọc sách.

### ⚡ Động cơ dịch AI đa tầng & Worker an toàn
- **Hỗ trợ đa nhà cung cấp:** Google Gemini (Gemini 2.5 Flash, Gemini Flash Latest, Gemini Pro...), DeepSeek (V3, R1), OpenAI-compatible, OpenRouter, Ollama (chạy model offline cục bộ) và chế độ dùng thử miễn phí.
- **Xoay vòng Multi-key API:** Nhập nhiều API key cùng lúc; hệ thống tự động luân phiên điều phối, retry khi gặp rate-limit và có cơ chế cooldown thông minh.
- **Worker đa luồng:** Chạy tối đa 6 worker song song với cơ chế pacing gap chuẩn mực, đảm bảo hiệu suất cao mà không vượt hạn mức nhà cung cấp.
- **Lưu trữ nguyên tử (Atomic Writes):** Dữ liệu được ghi an toàn qua file tạm và thay thế nguyên tử (`os.replace`), chống hỏng file tuyệt đối khi mất điện hoặc dừng chương trình đột ngột.

### 🖥️ Không gian làm việc hiện đại (Studio & Reader Mode)
- **Giao diện tối giản (Dark Theme):** Thiết kế vuông vức, tinh tế, tối ưu cho sự tập trung và giảm mỏi mắt khi đọc lâu.
- **Chế độ Studio (Đối chiếu song ngữ):** Đặt bản gốc tiếng Anh và bản dịch tiếng Việt cạnh nhau từng đoạn (`paragraph-by-paragraph`). Nhấp chuột trực tiếp vào đoạn văn để hiệu đính, lưu tự động khi rời ô.
- **Chế độ Đọc sách (Reader Mode):** Tùy chọn xem chỉ tiếng Việt, song ngữ hoặc chỉ tiếng Anh. Hỗ trợ chuyển đổi phông chữ Serif/Sans, tăng giảm cỡ chữ linh hoạt.
- **Cảnh báo cấu trúc (Structure Warnings):** Tự động phát hiện và cảnh báo các bất thường về cấu trúc chương/mục ngay trên thanh điều hướng.
- **Bảng điều khiển nhật ký hoạt động (Console Log Drawer):** Theo dõi tiến trình dịch, thời gian xử lý từng chunk và thông điệp hệ thống theo thời gian thực.

### 📦 Xuất bản đa định dạng chuẩn xuất bản
- **EPUB tiếng Việt:** Tương thích chuẩn cho máy đọc sách (Kindle, Kobo, Boox, reMarkable) và các app đọc sách di động.
- **EPUB song ngữ:** Mỗi đoạn tiếng Anh đi kèm ngay sau là bản dịch tiếng Việt, cực kỳ thuận tiện cho việc học ngoại ngữ và đối chiếu.
- **Microsoft Word (.docx):** Bố cục chỉn chu, sẵn sàng cho công tác biên tập chuyên sâu hoặc thiết kế bản in.
- **HTML tùy chỉnh:** Giao diện đọc trên trình duyệt web, tích hợp sẵn CSS in ấn tối ưu để **in ra file PDF sắc nét** (Ctrl+P / Cmd+P).
- **Plain Text (.txt):** Trích xuất văn bản thuần cho các nhu cầu lưu trữ đơn giản.

---

## 2. So sánh 2 luồng: Paper PDF vs Novel Ebook

| Tiêu chí | 🎓 Paper PDF | 📚 Novel Ebook |
| :--- | :--- | :--- |
| **Định dạng hỗ trợ** | PDF (bắt buộc có text layer hoặc đã OCR) | EPUB, DOCX, TXT, MD |
| **Bố cục xử lý** | Đơn cột hoặc 2 cột học thuật, lọc header/footer | Thứ tự đọc tuyến tính, tôn trọng TOC/spine |
| **Hình ảnh & Sơ đồ** | Trích xuất ảnh raster & vector độ phân giải cao | Trích xuất ảnh nhúng từ ebook/docx |
| **Công thức & Bảng** | Giữ nguyên bảng, hỗ trợ LaTeX / MathML | Định dạng theo chuẩn văn bản gốc |
| **Giọng văn (Tone)** | **Cố định Học thuật (`academic`)** | Tự chọn: Tiểu thuyết, Kỳ ảo, Self-Help, Cổ điển |
| **Quản lý nhân vật** | Ẩn (tập trung thuật ngữ & cấu trúc) | Đầy đủ: Phân tích AI, xưng hô, đại từ quan hệ |
| **Cảnh báo cấu trúc** | Cảnh báo khi thiếu heading hoặc bất thường cột | Cảnh báo khi tài liệu chỉ có 1 chương duy nhất |

> [!NOTE]
> Công cụ **PDF → EPUB** dành cho giáo trình là một luồng chuyển đổi chuyên biệt độc lập với 2 luồng dịch trên.

---

## 3. Cài đặt & Khởi động nhanh

### Yêu cầu hệ thống
- **Hệ điều hành:** Windows 10/11, macOS, hoặc Linux.
- **Python:** Phiên bản **3.10 trở lên** (đã tích hợp `pip`).
- **Trình duyệt:** Chrome, Edge, Brave, Firefox hoặc Safari.

---

### Cách 1: Windows 1-Click (Khuyên dùng)

Dự án cung cấp sẵn script `run.bat` cực kỳ tiện lợi:

1. Tải mã nguồn về máy (hoặc dùng `git clone https://github.com/leantri06/ai-book-translator.git`).
2. Nhấp đúp chuột vào file **`run.bat`**.
3. Script sẽ:
   - Tự động nhận diện môi trường ảo `.venv` (nếu có) hoặc Python hệ thống.
   - Tự động kiểm tra và cài đặt các thư viện còn thiếu từ `requirements.txt`.
   - Khởi động server nội bộ và tự động mở trình duyệt web tại `http://localhost:8000`.

---

### Cách 2: Chạy thủ công qua Terminal / PowerShell

#### Trên Windows (PowerShell):

```powershell
# 1. Clone repository
git clone https://github.com/leantri06/ai-book-translator.git
cd ai-book-translator

# 2. Khởi tạo và kích hoạt môi trường ảo
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Khởi chạy ứng dụng
.\.venv\Scripts\python.exe main.py
```

#### Trên macOS / Linux (Bash / Zsh):

```bash
# 1. Clone repository
git clone https://github.com/leantri06/ai-book-translator.git
cd ai-book-translator

# 2. Khởi tạo môi trường ảo
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# 3. Khởi chạy ứng dụng
.venv/bin/python main.py
```

### Truy cập & Tắt ứng dụng
- **Địa chỉ truy cập:** Ứng dụng tự động bind vào `127.0.0.1:8000`. Nếu cổng 8000 bị chiếm, hệ thống sẽ tự tìm cổng trống tiếp theo (8001, 8002...).
- **Tắt an toàn:** Nhấn **Dừng dịch** trên giao diện, chờ các worker hiện tại hoàn thành, sau đó nhấn `Ctrl + C` trong cửa sổ dòng lệnh.

---

## 4. Hướng dẫn sử dụng từng bước

### Bước 1: Cấu hình AI Provider
1. Mở ứng dụng, nhấn nút **Cài đặt** ở góc trên bên phải.
2. Chọn nhà cung cấp AI (Google Gemini, DeepSeek, OpenAI, OpenRouter, Ollama hoặc Dùng thử).
3. Nhập API Key (có thể nhập nhiều key, mỗi key một dòng).
4. Chọn mô hình tương ứng và điều chỉnh *Độ sáng tạo* (khuyến nghị 0.2 – 0.3 cho dịch thuật chuẩn xác).
5. Nhấn nút **Kiểm tra hạn mức** để xác thực kết nối, sau đó nhấn **Lưu cấu hình**.

### Bước 2: Tải tài liệu lên
- Để dịch bài báo, tài liệu học thuật: Nhấn nút **Paper PDF** và chọn file PDF.
- Để dịch tiểu thuyết, sách điện tử: Nhấn nút **Novel ebook** và chọn file EPUB, DOCX, TXT hoặc MD.
- Chờ hệ thống phân tích cấu trúc, trích xuất mục lục và hình ảnh.

### Bước 3: Thiết lập Văn phong, Nhân vật & Thuật ngữ
1. Mở bảng **Văn phong & thuật ngữ** ở cạnh phải.
2. Với sách Novel:
   - Chọn giọng văn (*novel*, *fantasy*, *selfhelp*, *classic*).
   - Nhấn **Phân tích AI** để tự động phát hiện các nhân vật chính.
   - Thêm hoặc hiệu chỉnh đại từ xưng hô của từng nhân vật (Tôi – Cậu, Anh – Em...).
3. Thêm các thuật ngữ chuyên ngành bắt buộc tuân thủ (ví dụ: *Transformer* -> *Mô hình Transformer*).
4. Nhập chỉ dẫn bổ sung (nếu có) rồi nhấn **Lưu thiết lập**.

### Bước 4: Tiến hành dịch thuật
- **Dịch thử nghiệm:** Chọn một chương ngắn ở mục lục bên trái, nhấn nút **Dịch chương** để kiểm tra chất lượng bản dịch và cách xưng hô.
- **Dịch toàn bộ:** Nhấn **Bắt đầu dịch** trên thanh công cụ chính để dịch toàn bộ tác phẩm từ đầu đến cuối.
- Quá trình dịch diễn ra tuần tự với thanh tiến độ hiển thị chi tiết phần trăm hoàn thành.

### Bước 5: Đối chiếu & Hiệu đính
- Xem đối chiếu song ngữ ở chế độ **Đối chiếu (Studio)**.
- Nếu thấy một câu/đoạn chưa ưng ý, nhấp chuột trực tiếp vào đoạn tiếng Việt để sửa chữ. Bản sửa sẽ tự động lưu lại vào hệ thống.
- Chuyển sang tab **Đọc sách (Reader)** để thưởng thức tác phẩm với trải nghiệm đọc sách mượt mà, tùy chỉnh phông chữ theo ý thích.

### Bước 6: Xuất bản tài liệu
1. Nhấn nút **Xuất sách** trên thanh công cụ.
2. Lựa chọn định dạng mong muốn:
   - **EPUB tiếng Việt:** Đọc trên thiết bị chuyên dụng.
   - **EPUB song ngữ:** Học tiếng Anh và đối chiếu câu chữ.
   - **DOCX:** Biên tập thêm bằng Microsoft Word.
   - **HTML / PDF:** Xem bằng trình duyệt web hoặc in ra PDF chất lượng cao.
   - **TXT:** Văn bản đơn giản.
3. Tải file về máy và sử dụng.

---

## 5. Cấu hình các nhà cung cấp AI

| Nhà cung cấp | Model khuyến nghị | Endpoint (Base URL) | Đặc điểm nổi bật |
| :--- | :--- | :--- | :--- |
| **Google Gemini** | `gemini-3.5-flash`<br>`gemini-flash-latest`<br>`gemini-3.1-pro-preview` | Mặc định từ Google SDK | Tốc độ cực nhanh, ngữ cảnh cực lớn, chi phí tối ưu nhất hiện nay. |
| **DeepSeek** | `deepseek-chat`<br>`deepseek-reasoner` | `https://api.deepseek.com/v1` | Văn phong tiếng Việt mượt mà, dịch thuật ngữ kỹ thuật rất chuẩn xác. |
| **OpenAI** | `gpt-4o`<br>`gpt-4o-mini` | `https://api.openai.com/v1` | Chất lượng ổn định cao, tương thích chuẩn OpenAPI. |
| **OpenRouter** | `anthropic/claude-3.5-sonnet`<br>`deepseek/deepseek-chat` | `https://openrouter.ai/api/v1` | Truy cập mọi model hàng đầu thông qua 1 API key duy nhất. |
| **Ollama (Cục bộ)** | `qwen2.5:7b`<br>`qwen2.5:14b` | `http://localhost:11434/v1` | **Chạy offline 100%**, bảo mật dữ liệu tuyệt đối, không tốn chi phí API. |
| **Dùng thử miễn phí** | Google Translate Web API | Tự động | Không cần key, thích hợp trải nghiệm thử nhanh tính năng của ứng dụng. |

### Cấu hình chi tiết cho từng loại:

#### 1. Google Gemini (Khuyên dùng)
1. Lấy API key miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Dán key vào ô API key. Hỗ trợ nhập nhiều key (mỗi dòng một key) để tự động xoay vòng quota.
3. Chọn model `gemini-3.5-flash` hoặc `gemini-flash-latest`.

#### 2. DeepSeek
1. Đăng ký tài khoản tại [DeepSeek Platform](https://platform.deepseek.com/).
2. Nhập key và Base URL: `https://api.deepseek.com/v1`.
3. Nhập tên model: `deepseek-chat` hoặc `deepseek-reasoner`.

#### 3. Ollama (Chạy offline cục bộ trên máy tính)
1. Tải và cài đặt Ollama từ [ollama.com](https://ollama.com/).
2. Mở terminal và tải model dịch thuật mạnh mẽ:
   ```bash
   ollama run qwen2.5:7b
   ```
3. Trong cài đặt ứng dụng:
   - Chọn nhà cung cấp: **Ollama Local**.
   - Base URL: `http://localhost:11434/v1`.
   - Model: Nhập đúng tên model đã tải (ví dụ: `qwen2.5:7b`).

---

## 6. Quản lý nhân vật, xưng hô và thuật ngữ

Hệ thống cung cấp cơ chế Prompt Engineering chuyên sâu dành cho dịch thuật văn học và tài liệu kỹ thuật:

### 1. Quản lý đại từ xưng hô (Pronouns Mapping)
Trong tiểu thuyết, cách xưng hô quyết định linh hồn của tác phẩm. Bạn có thể định nghĩa chi tiết:
- **Tên nhân vật:** Tên gốc trong tiếng Anh (ví dụ: *Shin*, *Lena*).
- **Vai trò / Giới tính:** Nam, Nữ, Nhóm...
- **Đại từ:**
  - Ngôi thứ nhất: *tôi*, *anh*, *em*, *ta*, *chú*...
  - Ngôi thứ hai: *cậu*, *cô*, *chàng*, *ngươi*...
  - Ngôi thứ ba: *cậu ấy*, *cô ấy*, *hắn*...
- **Ghi chú quan hệ:** Mô tả ngữ cảnh giao tiếp (ví dụ: *"Shin nói chuyện với Lena dùng tôi – cô; nói với đồng đội dùng tôi – cậu"*).

### 2. Từ điển thuật ngữ (Glossary)
Tránh tình trạng AI "sáng tạo" dịch mỗi lúc một kiểu:
- `Transformer` -> `Mô hình Transformer` (không dịch thành "Máy biến áp").
- `Attention Mechanism` -> `Cơ chế chú ý (attention mechanism)`.
- `Zero-shot` -> `Zero-shot (không cần mẫu huấn luyện)`.

### 3. Chỉ dẫn tùy chỉnh (Custom Instructions)
Nhập các quy tắc riêng như:
- *"Giữ nguyên tên riêng của các tổ chức và vũ khí."*
- *"Dùng đại từ thân mật giữa hai nhân vật chính."*
- *"Không tóm tắt hay tự ý cắt bớt câu chữ so với bản gốc."*

---

## 7. Không gian làm việc & Biên tập

### Giao diện Studio (Đối chiếu song ngữ)
- **Cột trái:** Văn bản gốc tiếng Anh.
- **Cột phải:** Bản dịch tiếng Việt tương ứng theo từng đoạn (`paragraph`).
- **Biên tập inline:** Bấm vào bất kỳ đoạn dịch nào để chỉnh sửa trực tiếp. Khi bạn bấm ra ngoài (blur), hệ thống tự động gửi yêu cầu lưu và cập nhật tiến độ tức thì.
- **Trạng thái đoạn:** Đoạn đang dịch, đoạn đã hoàn thành, hoặc đoạn có cảnh báo được hiển thị rõ ràng.

### Giao diện Reader (Đọc sách)
- Trải nghiệm như một ứng dụng đọc sách điện tử thực thụ.
- Tùy chỉnh chế độ hiển thị:
  - **Chỉ tiếng Việt:** Đọc trơn tru liền mạch.
  - **Song ngữ Anh – Việt:** Hiển thị xen kẽ từng câu/đoạn đối chiếu.
  - **Chỉ tiếng Anh:** Xem lại nguyên tác.
- Tùy chỉnh kiểu chữ: **Serif** (cổ điển, dễ chịu) hoặc **Sans** (hiện đại, rõ nét).
- Tăng / giảm cỡ chữ linh hoạt từ 14px đến 26px.

---

## 8. Xuất bản tài liệu

Hệ thống hỗ trợ 5 định dạng xuất bản chất lượng cao:

```
[Dự án đã dịch]
       │
       ├──> EPUB Bản tiếng Việt   (Kindle, Kobo, Apple Books, Google Play Books)
       ├──> EPUB Bản song ngữ    (Học ngoại ngữ, đối chiếu song song)
       ├──> Microsoft Word DOCX  (Biên tập chuyên sâu, chèn header/footer in ấn)
       ├──> Trang HTML tùy biến  (Đọc trên web, hỗ trợ In ra PDF chất lượng cao)
       └──> Văn bản thuần TXT    (Lưu trữ thô, xử lý NLP)
```

> [!TIP]
> **Cách xuất ra file PDF chất lượng cao:**
> 1. Bấm **Xuất sách** -> Chọn **HTML (Đọc trên web / In PDF)** và tải file về máy.
> 2. Mở file `.html` bằng trình duyệt Chrome hoặc Edge.
> 3. Nhấn `Ctrl + P` (hoặc `Cmd + P` trên Mac).
> 4. Chọn máy in: **Save as PDF** (Lưu dưới dạng PDF), chọn khổ giấy A4, bật tùy chọn *Background graphics*. Toàn bộ tiêu đề, canh lề, ngắt trang và ảnh minh họa sẽ được định dạng hoàn hảo chuẩn in ấn.

---

## 9. Cấu trúc dữ liệu & Sao lưu

Toàn bộ dữ liệu của bạn được lưu trữ cục bộ ngay trong thư mục `data/`:

```text
ai_book_translator/
├── data/
│   ├── settings.json            # Cấu hình AI, model, API keys
│   ├── uploads/                 # File tài liệu gốc đã tải lên
│   ├── projects/
│   │   └── <project_id>/        # Thư mục riêng của từng dự án sách
│   │       ├── meta.json        # Thông tin sách, tiến độ, cảnh báo cấu trúc
│   │       ├── glossary.json    # Nhân vật, xưng hô, thuật ngữ, văn phong
│   │       ├── chapters/        # Dữ liệu nội dung từng chương
│   │       │   ├── chap_0.json  # Bản gốc, bản dịch, trạng thái từng đoạn
│   │       │   └── chap_1.json
│   │       └── images/          # Hình ảnh, sơ đồ trích xuất từ tài liệu
│   └── exports/                 # Các file thành phẩm đã xuất (EPUB, DOCX...)
```

### Cơ chế lưu trữ an toàn (Atomic File Writes)
Ứng dụng sử dụng cơ chế ghi dữ liệu nguyên tử: Dữ liệu được ghi vào một file tạm cùng thư mục trước, sau đó mới dùng lệnh thay thế hệ thống (`os.replace`). Điều này đảm bảo file dữ liệu không bao giờ bị rỗng hay hỏng hóc nếu máy tính gặp sự cố sập nguồn hoặc tắt ứng dụng đột ngột.

### Hướng dẫn sao lưu (Backup)
1. Dừng tiến trình dịch và tắt ứng dụng.
2. Sao chép toàn bộ thư mục `data/` sang nơi lưu trữ an toàn (ổ cứng ngoài hoặc cloud cá nhân).
3. Khi cần khôi phục trên máy mới, chỉ cần cài đặt ứng dụng và chép thư mục `data/` vào lại thư mục gốc của project.

---

## 10. Xử lý sự cố thường gặp (FAQ)

| Hiện tượng | Nguyên nhân có thể | Cách xử lý |
| :--- | :--- | :--- |
| **Lỗi `ModuleNotFoundError` khi chạy** | Thiếu thư viện hoặc chưa cài vào đúng Python | Chạy lệnh `python -m pip install -r requirements.txt`. Nếu dùng `.venv`, hãy kích hoạt trước. |
| **Không mở được trình duyệt khi chạy `run.bat`** | Trình duyệt mặc định bị chặn hoặc cổng bận | Mở trình duyệt thủ công và truy cập địa chỉ `http://localhost:8000` được in trên terminal. |
| **Cổng 8000 bị báo bận** | Một ứng dụng khác đang chiếm cổng 8000 | Ứng dụng sẽ tự động chuyển sang cổng 8001, 8002... Xem địa chỉ chính xác trên cửa sổ terminal. |
| **Lỗi API 401 hoặc 403** | API key sai hoặc tài khoản chưa cấp quyền model | Kiểm tra lại API key trong menu *Cài đặt*, bấm *Kiểm tra hạn mức* để xác thực. |
| **Gặp lỗi Rate Limit (429) liên tục** | Vượt số lượng request miễn phí của nhà cung cấp | Nhập thêm nhiều API key để xoay vòng, hoặc chọn model có hạn mức cao hơn (`gemini-3.5-flash`), hoặc chuyển sang Ollama cục bộ. |
| **File PDF tải lên báo không có chữ** | File PDF là dạng scan toàn bộ bằng hình ảnh | Cần dùng phần mềm OCR (như Adobe Acrobat hoặc Abbyy FineReader) để tạo lớp chữ trước khi nạp vào hệ thống. |
| **Chỉnh sửa bản dịch nhưng không thấy lưu** | Worker dịch đang hoạt động chặn ghi đè | Nhấn **Dừng dịch**, chờ worker về trạng thái *Sẵn sàng* rồi mới tiến hành sửa tay hoặc xóa dự án. |
| **Không kết nối được với Ollama** | Ollama chưa được bật trên máy tính | Mở terminal riêng, chạy `ollama serve` và kiểm tra lệnh `ollama list` để đảm bảo model đã sẵn sàng. |

---

## 11. Phát triển & Kiểm thử

Dự án đi kèm bộ kiểm thử hồi quy tự động hoàn chỉnh, chạy hoàn toàn offline mà không cần API key thật và không phát sinh chi phí:

### Cấu trúc mã nguồn

```text
ai_book_translator/
├── core/                        # Các engine xử lý cốt lõi
│   ├── paper_structure.py       # Phân tích hình học trang, tách 2 cột, lọc header
│   ├── epub_structure.py        # Phân tích sâu EPUB TOC, spine, anchor fragment
│   ├── textbook_parser.py       # Engine bóc tách giáo trình PDF -> EPUB
│   ├── parser.py                # Bộ điều phối phân tích tài liệu đầu vào
│   ├── chunker.py               # Chia nhỏ văn bản thành các chunk dịch tối ưu
│   ├── glossary.py              # Xử lý quy tắc xưng hô, nhân vật & thuật ngữ
│   ├── translator.py            # Giao tiếp với các AI backend (Gemini, DeepSeek...)
│   └── exporter.py              # Đóng gói xuất bản EPUB, DOCX, HTML, TXT
├── server/                      # Backend FastAPI & Worker
│   ├── app.py                   # REST API routes và quản lý static files
│   ├── database.py              # Quản lý dự án, ghi file JSON nguyên tử
│   └── translator_worker.py     # Điều phối đa luồng, xoay vòng key, pacing gap
├── web/                         # Giao diện người dùng
│   ├── index.html               # Cấu trúc giao diện ngữ nghĩa chuẩn W3C
│   ├── app.css                  # Hệ thống design tokens & responsive styling
│   └── app.js                   # Xử lý tương tác giao diện và gọi API
├── main.py                      # File khởi động chính và tìm kiếm port tự động
├── run.bat                      # File khởi động 1-click cho Windows
└── requirements.txt             # Danh sách thư viện phụ thuộc
```

### Chạy kiểm thử tự động

```powershell
# Chạy toàn bộ 134 bài kiểm thử hồi quy backend
python -m unittest discover -v

# Kiểm thử luồng E2E hoàn chỉnh (Parser -> Glossary -> Chunker -> Translator -> Exporters)
python test_verification.py

# Kiểm tra cú pháp JavaScript giao diện
node --check web/app.js

# Chạy kiểm thử tự động quy trình giao diện trên trình duyệt headless
node test_web_workflows.js
```

---

## 12. Bảo mật & Giới hạn sử dụng

- **Quyền riêng tư:** Ứng dụng được thiết kế chạy hoàn toàn cục bộ trên máy tính của bạn (`localhost:127.0.0.1`). Không gửi bất kỳ dữ liệu sách hay thông tin cá nhân nào về server trung gian của bên thứ ba, ngoại trừ các yêu cầu dịch thuật gửi trực tiếp tới API nhà cung cấp do chính bạn cấu hình.
- **Bảo mật API Key:** Các API key của bạn được lưu trong file `data/settings.json` trên máy tính cá nhân. File này đã được thêm vào `.gitignore` để tránh vô tình đưa lên GitHub. Hãy giữ an toàn file này.
- **Bản quyền tác phẩm:** Người dùng tự chịu trách nhiệm về bản quyền của các tài liệu, sách và ấn phẩm đưa vào dịch thuật và xuất bản.

---

<p align="center">
  Phát triển với sự tận tâm nhằm đem lại công cụ dịch thuật và tiếp cận tri thức tốt nhất cho cộng đồng.<br>
  <strong>AI Book & Research Paper Translator Pro — V4.1.0</strong>
</p>
