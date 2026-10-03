# AI Book & Research Paper Translator Pro

Ứng dụng Python chạy cục bộ, dùng giao diện web để dịch sách và tài liệu tiếng Anh sang tiếng Việt, quản lý thuật ngữ, đối chiếu từng đoạn và xuất bản dịch.

> **Phạm vi:** công cụ hỗ trợ dịch và biên tập, không bảo đảm bản dịch đạt chất lượng xuất bản hoặc giữ nguyên mọi chi tiết bố cục. Hãy thử một chương trước khi dịch cả sách. Các tên model và nhãn quảng bá trong giao diện là cấu hình có sẵn trong mã nguồn, không phải xác nhận về khả dụng, giá hoặc quota hiện tại của nhà cung cấp.

## Mục lục

1. [Tính năng và định dạng](#1-tính-năng-và-định-dạng)
2. [Chuẩn bị](#2-chuẩn-bị)
3. [Cài đặt và khởi động](#3-cài-đặt-và-khởi-động)
4. [Bắt đầu với một cuốn sách](#4-bắt-đầu-với-một-cuốn-sách)
5. [Cấu hình dịch](#5-cấu-hình-dịch)
6. [Nhân vật, thuật ngữ và văn phong](#6-nhân-vật-thuật-ngữ-và-văn-phong)
7. [Dịch, tạm dừng và dịch lại](#7-dịch-tạm-dừng-và-dịch-lại)
8. [Đọc và sửa bản dịch](#8-đọc-và-sửa-bản-dịch)
9. [Xuất sách](#9-xuất-sách)
10. [Dữ liệu và sao lưu](#10-dữ-liệu-và-sao-lưu)
11. [Xử lý sự cố](#11-xử-lý-sự-cố)
12. [Bảo mật và giới hạn](#12-bảo-mật-và-giới-hạn)
13. [Phát triển và kiểm thử](#13-phát-triển-và-kiểm-thử)

## 1. Tính năng và định dạng

- Hai luồng nhập riêng: **Paper PDF** (xanh teal) và **Novel ebook** (tím nhẹ), dùng chung workspace dịch và lưu tiến độ.
- Paper nhận diện mục lớn theo outline, font và bố cục; tiểu mục ở trong mục cha. Novel ưu tiên spine/mục lục/anchor EPUB, sau đó phân cấp heading.
- Cảnh báo cấu trúc được hiển thị cạnh mục lục; không tự chia chương theo độ dài hay chia lại dự án đã lưu.
- Dịch một chương hoặc các phần còn thiếu của sách; có lệnh dịch lại từ đầu.
- Cấu hình nhà cung cấp, model, API key và endpoint tương thích.
- Quản lý nhân vật, đại từ xưng hô, thuật ngữ và yêu cầu bổ sung.
- Giao diện song ngữ để sửa từng đoạn và chế độ đọc sách có tùy chỉnh hiển thị.
- Hỗ trợ trích xuất ảnh và xử lý cấu trúc tài liệu học thuật, bảng và công thức ở mức phụ thuộc tài liệu nguồn.
- Worker hỗ trợ nhiều key, retry và cooldown; tối đa 6 worker theo số key và số chunk. Không bảo đảm tăng tốc tuyến tính.

### Đầu vào

| Luồng | Định dạng | Ghi chú |
| --- | --- | --- |
| Paper PDF | PDF | Cần lớp văn bản; mục lớn, tiểu mục, thứ tự hai cột cần kiểm tra sau nhập. PDF scan cần OCR trước. |
| Novel ebook | EPUB | Ưu tiên thứ tự đọc và mục lục, kể cả nhiều chương trong một XHTML hoặc một chương trải trên nhiều XHTML. |
| Novel ebook | DOCX | Dùng cấp heading mạnh nhất làm chương, giữ heading nhỏ trong chương; không hỗ trợ DOC cũ. |
| Novel ebook | TXT, MD | Nên dùng UTF-8 và tiêu đề chương rõ ràng. Markdown dùng cấp heading mạnh nhất; không giữ mọi cú pháp. |

**PDF → EPUB** dành cho giáo trình là chức năng riêng, không phải luồng Paper hay Novel.

Giới hạn mỗi lần upload: **100 MiB**. File rỗng bị từ chối. File và dự án tạo dở được dọn nếu quá trình upload/phân tích thất bại.

### Đầu ra trong giao diện

EPUB tiếng Việt, EPUB song ngữ, DOCX, HTML và TXT. Chức năng PDF sử dụng **in trang HTML ra PDF qua trình duyệt**, không phải tạo file PDF trực tiếp ở backend.

## 2. Chuẩn bị

- Python **3.10 trở lên**, có pip.
- Git nếu tải dự án bằng lệnh clone; cũng có thể tải ZIP mã nguồn rồi giải nén.
- Trình duyệt web và dung lượng lưu trữ cho sách, ảnh trích xuất, bản xuất và thư viện Python.
- Internet khi cài thư viện hoặc dùng dịch vụ dịch từ xa.
- API key hợp lệ nếu nhà cung cấp yêu cầu; tài khoản cần có quyền dùng model đã chọn.
- Nếu dùng Ollama: tự cài dịch vụ và tải model phù hợp với máy. Repository không cung cấp sẵn model.

Giao diện frontend không cần bước build bằng npm. Dùng môi trường ảo riêng để tránh trộn thư viện với các dự án khác.

## 3. Cài đặt và khởi động

### Windows: cách khuyên dùng

Mở PowerShell tại thư mục muốn lưu project:

~~~powershell
git clone https://github.com/leantri06/ai-book-translator.git
cd ai-book-translator
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
~~~

Không cần kích hoạt môi trường ảo khi gọi Python bằng đường dẫn như trên. Nếu máy không có lệnh py nhưng đã có Python, thay py bằng python ở bước tạo môi trường.

**Những lần chạy sau:**

~~~powershell
cd <thu-muc-chua-project>
.\.venv\Scripts\python.exe main.py
~~~

### Windows: chạy bằng run.bat

Có thể nhấp đúp run.bat sau khi cài Python vào PATH. Script tìm python hoặc py, kiểm tra một số thư viện và cài requirements.txt nếu kiểm tra thất bại, rồi chạy main.py.

**Lưu ý:** run.bat không tự tạo hoặc ưu tiên .venv. Nếu đã cài thư viện trong .venv, dùng lệnh khởi động bên trên; hoặc kích hoạt .venv trong terminal trước khi chạy run.bat. Nếu script bỏ sót thư viện còn thiếu, cài lại requirements.txt bằng đúng Python đang dùng.

### macOS / Linux

~~~bash
git clone https://github.com/leantri06/ai-book-translator.git
cd ai-book-translator
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
~~~

Đây là cách chạy Python tương đương; bộ kiểm thử được ghi nhận trong lần nâng cấp này chạy trên Windows, không phải chứng nhận đã kiểm thử mọi hệ điều hành.

### Truy cập và tắt ứng dụng

Launcher bind server vào 127.0.0.1, ưu tiên cổng 8000 và thử cổng khác nếu bị chiếm. Trình duyệt được mở tự động; nếu không mở, xem địa chỉ được in trong terminal.

~~~text
http://localhost:8000
~~~

Giữ terminal mở khi dùng ứng dụng. Để tắt an toàn, tạm dừng dịch, chờ worker kết thúc rồi nhấn Ctrl+C trong terminal. Đóng tab trình duyệt không đồng nghĩa với dừng server hoặc dừng dịch.

## 4. Bắt đầu với một cuốn sách

1. Khởi động ứng dụng và mở **Cài đặt API**.
2. Chọn nhà cung cấp, model và nhập key/endpoint nếu cần; bấm lưu cấu hình.
3. Chọn **Paper PDF** hoặc **Novel ebook**, chọn đúng loại file và chờ phân tích. Có thể đổi loại trong hộp tải tài liệu.
4. Chọn dự án và một mục/chương bên trái; đọc cảnh báo cấu trúc và kiểm tra bản gốc đúng thứ tự, không mất đoạn.
5. Mở **Văn phong & thuật ngữ**. Paper khóa giọng học thuật và ẩn nhân vật; Novel cho chọn giọng văn, xưng hô. Cả hai giữ thuật ngữ và chỉ dẫn riêng; bấm lưu.
6. Bấm **Dịch mục** hoặc **Dịch chương** để thử một phần ngắn.
7. Theo dõi log, đọc và sửa một số đoạn. Nếu cấu hình hoặc cách xưng hô chưa phù hợp, điều chỉnh trước khi dịch toàn bộ.
8. Dịch các phần còn lại, rà soát những đoạn chưa dịch rồi xuất sách.

Với PDF scan chỉ chứa ảnh, hãy OCR bằng công cụ riêng trước khi tải lên; project chưa có quy trình OCR đầy đủ tích hợp.

## 5. Cấu hình dịch

Cấu hình được lưu cục bộ và dùng chung giữa các dự án. Để áp dụng thay đổi một cách rõ ràng, dừng phiên dịch hiện tại, chờ kết thúc, lưu cấu hình mới rồi bắt đầu lại.

### Các trường chính

| Trường | Cách sử dụng |
| --- | --- |
| Nhà cung cấp | Chọn backend tương ứng với tài khoản hoặc dịch vụ cục bộ. |
| API key | Nhập key; không chụp màn hình hoặc đưa key vào Git. |
| Model | Chọn tên có sẵn hoặc **Nhập tên mô hình khác...**; nhập đúng ID được tài khoản cho phép dùng. |
| Base URL | Địa chỉ gốc API tương thích, thường kết thúc bằng /v1; backend tự nối /chat/completions. |

Tên model hiển thị sẵn có thể cũ hoặc không khả dụng. Một số tên Gemini còn bị engine ánh xạ sang model khác. Khi cần kiểm tra chính xác, đối chiếu log và mã nguồn thay vì giả định tên nhập vào luôn được dùng nguyên trạng.

### Gemini

Nhập key và chọn model, sau đó thử một chương ngắn. Engine có logic thử model dự phòng và trong một số tình huống chuyển sang dịch vụ Google Translate công khai, kể cả khi không có key. Vì vậy không nên dùng nhánh này cho tài liệu bắt buộc chỉ gửi tới một model/provider duy nhất.

### DeepSeek và OpenRouter

Giao diện có điền Base URL theo lựa chọn. Kiểm tra endpoint, model và key trước khi lưu. API tương thích cần hỗ trợ định dạng chat completions mà engine đang gửi.

### OpenAI: giới hạn cấu hình hiện tại

Mã nguồn có nhánh OpenAI-compatible, nhưng backend hiện mặc định sang endpoint DeepSeek nếu Base URL trống, trong khi giao diện lựa chọn OpenAI ẩn trường này và không tự gán endpoint OpenAI. **Không xem lựa chọn OpenAI trong giao diện là đã cấu hình hoàn chỉnh.**

Nếu cần dùng nhánh này, dừng server, sao lưu data/settings.json và chỉnh base_url trong file bằng endpoint đúng của tài khoản rồi khởi động lại. Tránh để nguyên endpoint từ nhà cung cấp trước. README này không xác nhận kết nối OpenAI thực tế đã được kiểm thử.

### Ollama cục bộ

1. Cài và chạy Ollama bên ngoài project.
2. Tải model trước bằng công cụ của Ollama; chọn model thực sự có trên máy.
3. Trong ứng dụng chọn Ollama, kiểm tra Base URL và nhập tên model chính xác.
4. Lưu và thử dịch một đoạn ngắn.

Giá trị Base URL mà giao diện điền sẵn:

~~~text
http://localhost:11434/v1
~~~

Các nhãn “đã cài sẵn” trong giao diện không thực hiện kiểm tra máy. Dịch qua Ollama có thể chạy cục bộ sau khi tải model, nhưng không nên suy ra mọi chức năng đều offline: **tự nhận diện nhân vật** có luồng gọi AI riêng và chưa được bảo đảm dùng cùng endpoint cục bộ. Với tài liệu riêng tư, nhập nhân vật/thuật ngữ thủ công và kiểm soát truy cập mạng.

### Chế độ dùng thử không cần key

Chế độ này gọi endpoint Google Translate công khai qua mạng, không phải dịch offline và không có bảo đảm dịch vụ. Văn phong và việc tuân thủ glossary không tương đương nhánh LLM. Nếu lỗi, có thể xuất hiện các tiền tố **[Chưa dịch]** hoặc **[Dịch tự động tạm thời]** kèm nguyên văn. Hãy tìm các dấu hiệu này khi rà soát kết quả.

### Nhiều key và kiểm tra quota

Có thể nhập nhiều key bằng cách xuống dòng, ngăn bằng dấu phẩy hoặc dấu chấm phẩy. Chỉ dùng key hợp lệ mà bạn được phép sử dụng. Các key có thể dùng chung quota; không xem nhiều key là cách bảo đảm tăng hạn mức.

Nút **Kiểm tra Quota & Sức khỏe Key** thực hiện yêu cầu thử; nó không đọc được chính xác số dư hoặc tổng quota còn lại. Với Gemini, danh sách model kiểm tra đang cố định trong mã nguồn, không nhất thiết trùng model bạn nhập. Lỗi model/quyền truy cập hoặc mạng có thể làm kết quả không phản ánh đúng chất lượng key. Yêu cầu kiểm tra cũng có thể tiêu thụ quota hoặc phát sinh chi phí.

## 6. Nhân vật, thuật ngữ và văn phong

Trong **Nhân vật & Văn phong**:

- Novel cho chọn tiểu thuyết, kỳ ảo, self-help hoặc cổ điển. Paper luôn dùng giọng học thuật, kể cả khi dữ liệu cũ lưu giọng khác; worker không ghi đè glossary đã lưu chỉ để áp dụng giọng phù hợp.
- Với nhân vật, nhập tên, vai trò, giới tính nếu biết, đại từ ngôi thứ nhất/thứ hai/thứ ba và ghi chú quan hệ.
- Với thuật ngữ, nhập cách viết gốc, bản dịch mong muốn và ghi chú ngữ cảnh.
- Thêm hướng dẫn riêng, ví dụ: “Giữ nguyên tên riêng; dùng tôi–cậu giữa hai nhân vật chính; không diễn giải thêm nội dung ngoài bản gốc.”
- Bấm lưu trước khi bắt đầu phiên dịch mới.

Ví dụ quy ước biên tập:

| Nội dung | Quy ước mẫu |
| --- | --- |
| Character A nói với Character B | Tôi – cậu |
| Transformer | Giữ nguyên Transformer |
| attention mechanism | Cơ chế chú ý (attention mechanism) ở lần đầu |

Tự nhận diện nhân vật chỉ tạo gợi ý; cần kiểm tra và sửa trước khi dùng. Thay đổi glossary không tự sửa những đoạn đã dịch; muốn áp dụng lại phải dịch lại hoặc biên tập thủ công.

## 7. Dịch, tạm dừng và dịch lại

### Dịch tiếp

- **Dịch chương này:** xử lý các phần còn thiếu theo trạng thái của chương đã chọn.
- Chức năng dịch toàn bộ xử lý những chương chưa hoàn thành.
- Tiến độ được lưu dần; sau khi khởi động lại, chọn dự án cũ để tiếp tục thay vì upload lại.

### Tạm dừng

Lệnh tạm dừng yêu cầu worker ngừng nhận việc mới; không hủy tức thời HTTP request đang chạy. Chờ trạng thái trở về sẵn sàng. Trong thời gian chạy hoặc đang dừng, ứng dụng chặn khởi động phiên mới, sửa đoạn và xóa dự án để tránh ghi đè dữ liệu.

Không ép đóng ứng dụng chỉ vì yêu cầu dừng chưa phản hồi ngay. Nếu có lỗi hoặc hết quota, đọc log trước khi thử tiếp.

### Dịch lại từ đầu

**Cảnh báo: thao tác này xóa bản dịch cũ, bao gồm phần bạn đã sửa tay trong phạm vi được dịch lại.** Sao lưu trước. Dùng khi đổi model, đổi văn phong hoặc muốn tái tạo cả chương. Nếu chỉ sửa vài lỗi nhỏ, biên tập từng đoạn thường phù hợp hơn.

Tiến độ phản ánh trạng thái xử lý của các đoạn, không phải điểm chất lượng. Đặc biệt, kết quả fallback có thể chứa nguyên văn hoặc dấu báo chưa dịch ngay cả khi đoạn được ghi nhận đã xử lý.

## 8. Đọc và sửa bản dịch

### Song ngữ đối chiếu

Chọn chương, xem bản gốc và bản dịch cạnh nhau. Khi worker đã dừng, nhấp vào bản dịch để sửa rồi nhấp ra ngoài ô: giao diện gửi yêu cầu lưu khi ô mất focus. Kiểm tra log xác nhận trước khi chuyển chương hoặc đóng trang. Nếu lưu lỗi, giữ lại nội dung chỉnh sửa để tránh mất công.

### Chế độ đọc sách

Chuyển sang **Chế độ đọc sách** và chọn chỉ tiếng Việt, song ngữ hoặc chỉ tiếng Anh. Có thể điều chỉnh kiểu chữ và cỡ chữ. Chế độ đọc phục vụ kiểm tra nội dung, không phải trình biên tập bố cục in ấn đầy đủ.

Với bài báo PDF, đặc biệt kiểm tra thứ tự hai cột, caption hình/bảng, công thức, chú thích và tài liệu tham khảo.

## 9. Xuất sách

1. Chờ dịch và chỉnh sửa xong; nên tạm dừng worker trước khi xuất để tránh bản xuất chứa dữ liệu từ các thời điểm khác nhau.
2. Mở chức năng xuất sách và chọn định dạng.
3. Tải file, mở bằng ứng dụng đọc tương ứng và kiểm tra vài chương, ảnh, dấu tiếng Việt và mục lục.

| Định dạng | Phù hợp khi |
| --- | --- |
| EPUB tiếng Việt | Đọc bằng phần mềm hoặc thiết bị hỗ trợ EPUB. |
| EPUB song ngữ | Đối chiếu nguồn và bản dịch. |
| DOCX | Tiếp tục biên tập trong trình soạn thảo Word. |
| HTML | Đọc bằng trình duyệt hoặc in ra PDF. |
| TXT | Lấy nội dung văn bản đơn giản. |

Để tạo PDF, mở HTML đã tải về, dùng Ctrl+P hoặc Cmd+P, chọn lưu PDF và kiểm tra khổ giấy/lề trước khi lưu.

Các đoạn chưa có bản dịch có thể được xuất bằng bản gốc, tùy nhánh exporter. Kiểm tra nội dung thay vì chỉ dựa vào việc xuất thành công. Bản xuất không tự cập nhật sau khi sửa; cần xuất lại. File tạm xuất được đặt theo tên sách và định dạng, nên dự án trùng tên có thể ghi đè file xuất trên server; tải và đổi tên bản cần giữ.

## 10. Dữ liệu và sao lưu

~~~text
data/
  settings.json            Cấu hình và API key dạng văn bản
  uploads/                 File nguồn đã upload
  projects/<project_id>/
    meta.json              Thông tin dự án và thống kê
    glossary.json          Nhân vật, thuật ngữ, văn phong
    chapters/*.json        Nội dung gốc, bản dịch, trạng thái
    images/                Ảnh trích xuất nếu có
  exports/                 Các file xuất
~~~

### Sao lưu

1. Tạm dừng dịch và chờ kết thúc, sau đó tắt server.
2. Sao chép toàn bộ thư mục data sang vị trí riêng an toàn để giữ cả nguồn, ảnh và đường dẫn liên quan.
3. Bảo vệ settings.json vì chứa key; không gửi bản sao nguyên trạng cho người khác.
4. Khi khôi phục, tắt server, sao lưu dữ liệu hiện tại rồi đưa dữ liệu cũ về đúng thư mục.

Một số đường dẫn nguồn/ảnh được lưu dạng tuyệt đối: chuyển sang máy hoặc thư mục khác có thể cần điều chỉnh, không bảo đảm sao chép data là đủ cho mọi bản xuất.

Xóa dự án là thao tác không có thùng rác tích hợp; chỉ xóa khi worker đã dừng. Các file đã tải về máy hoặc file trong exports không nên được coi là đã tự xóa theo dự án.

.gitignore loại dữ liệu cục bộ, settings và .venv khỏi Git. Trước khi chia sẻ hoặc push, vẫn kiểm tra các file đang được theo dõi; ignore không gỡ một bí mật đã từng commit.

## 11. Xử lý sự cố

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Không tìm thấy python/py | Cài Python, thêm PATH và mở terminal mới; hoặc dùng đường dẫn Python trong .venv. |
| ModuleNotFoundError | Cài requirements.txt bằng đúng Python dùng chạy main.py. |
| Trình duyệt không mở | Đọc URL trong terminal; kiểm tra server chưa thoát do lỗi. |
| Cổng 8000 đã bị chiếm | Dùng địa chỉ cổng thay thế do launcher in ra. |
| Upload bị từ chối | Kiểm tra định dạng, file không rỗng và không quá 100 MiB; chuyển DOC sang DOCX. |
| PDF không có chữ hoặc sai thứ tự | Kiểm tra lớp văn bản/OCR và thử nguồn EPUB/DOCX nếu có. |
| API trả 401/403 | Kiểm tra key, quyền tài khoản và endpoint; không gửi key trong báo lỗi. |
| Model không tìm thấy | Nhập ID model hợp lệ cho tài khoản; tên sẵn trong giao diện không phải cam kết khả dụng. |
| Quota/rate limit | Đọc log, chờ cooldown hoặc kiểm tra hạn mức với nhà cung cấp; tránh bấm thử liên tục. |
| Chọn OpenAI nhưng gọi sai server | Xem mục giới hạn cấu hình OpenAI và kiểm tra base_url đã lưu. |
| Ollama không kết nối | Kiểm tra dịch vụ, endpoint và model đã tải; model không đi kèm project. |
| Không sửa/xóa được khi đang dừng | Chờ request AI hiện tại kết thúc và worker về sẵn sàng. |
| Đoạn vẫn là tiếng Anh | Kiểm tra log và dấu fallback; rà soát hoặc dịch lại sau khi sửa cấu hình. |
| Đổi glossary mà bản dịch không đổi | Glossary mới áp dụng cho phiên dịch sau, không tự sửa kết quả cũ. |
| Xuất sách thiếu ảnh hoặc lỗi công thức | Kiểm tra file nguồn và thư mục ảnh; xem bằng trình đọc khác và so với nguồn. |

Khi báo lỗi, cung cấp hệ điều hành, phiên bản Python, định dạng đầu vào, các bước tái hiện và log đã xóa key/nội dung riêng tư. Ưu tiên file mẫu nhỏ không chứa tài liệu nhạy cảm.

## 12. Bảo mật và giới hạn

- Thiết kế cho **một người dùng, một tiến trình server, chạy cục bộ**. Chưa có đăng nhập/phân quyền; không public ra Internet hoặc mở port LAN khi chưa bổ sung bảo vệ.
- API key lưu dạng plaintext trong data/settings.json và được API cấu hình trả cho giao diện. CORS không thay thế xác thực.
- Dịch vụ từ xa nhận nội dung các đoạn dịch và ngữ cảnh/glossary được gửi kèm. Kiểm tra yêu cầu bảo mật của tài liệu trước khi sử dụng.
- Nhánh Gemini có fallback sang dịch vụ khác; chế độ dùng thử cũng cần mạng. Không bảo đảm xử lý offline trừ khi đã kiểm tra toàn bộ luồng đang dùng.
- Ghi JSON nguyên tử bảo vệ từng file khỏi ghi dở, không phải giao dịch nhiều file hoặc khóa liên tiến trình. Sao lưu vẫn cần thiết.
- Chưa có bảo đảm OCR, độ chính xác khoa học, giữ bố cục tuyệt đối hoặc chất lượng văn học. Cần người biên tập rà soát.
- Chỉ xử lý và chia sẻ những tài liệu bạn có quyền sử dụng. Không suy ra có giấy phép MIT từ README cũ; repository hiện chưa có file LICENSE xác định giấy phép dự án.

## 13. Phát triển và kiểm thử

### Cấu trúc mã nguồn

~~~text
main.py                      Launcher server và trình duyệt
run.bat                      Launcher Windows
core/parser.py               Đọc file và tạo cấu trúc sách
core/chunker.py              Chia đoạn thành chunk dịch
core/translator.py           Gọi backend dịch
core/glossary.py              Quy tắc nhân vật và thuật ngữ
core/exporter.py              Xuất bản dịch
server/app.py                HTTP API và phục vụ giao diện
server/database.py           Lưu/đọc JSON
server/translator_worker.py  Điều phối worker và tiến độ
web/                         HTML, CSS, JavaScript
~~~

### Test offline, không dùng key thật

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -v
node test_web_workflows.js
~~~

Trên macOS/Linux, thay đường dẫn Python bằng .venv/bin/python.

Bộ test dùng thư mục tạm và không gọi dịch vụ AI. Phạm vi gồm API cơ bản, giữ số từ sau chỉnh sửa, lưu JSON nguyên tử, đường dẫn không hợp lệ, cleanup upload và trạng thái worker đang dừng. Script test_verification.py cũ có luồng dịch qua mạng: **không dùng làm bài test offline mặc định**.

Kiểm tra cú pháp bổ sung:

~~~powershell
.\.venv\Scripts\python.exe -m compileall -q core server main.py test_server_endpoints.py
node --check web/app.js
git diff --check
~~~

Lệnh node ở trên chỉ dành cho kiểm tra JavaScript nếu có Node.js, không phải yêu cầu để chạy ứng dụng. Xem thêm [DEVELOPMENT.md](DEVELOPMENT.md).

### Kết quả kiểm chứng trong lần nâng cấp

Bộ hồi quy bao gồm API, lưu/đọc metadata cũ và mới, Paper/PDF, Novel/EPUB/DOCX/Markdown và xuất heading không lặp. Test giao diện chạy bằng Chrome/Edge headless với API giả lập, không cần npm package hay key thật; cần Node.js có WebSocket tích hợp (22+) và trình duyệt Chromium đã cài, hoặc đặt TEST_BROWSER tới executable.

Có cảnh báo deprecated từ TestClient/thư viện HTTP trong môi trường kiểm thử. Kết quả không chứng nhận kết nối thật tới từng provider, giá/quota/model hiện hành, chất lượng dịch hoặc độ trung thực của mọi tài liệu nguồn.
