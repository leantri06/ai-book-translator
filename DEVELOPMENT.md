# Phát triển và kiểm thử

## Môi trường

Dùng Python 3.10 trở lên và môi trường ảo riêng cho project:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

## Kiểm thử hồi quy offline

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
node --check web/app.js
node test_web_workflows.js
git diff --check
```

Bộ test này dùng thư mục tạm, không ghi đè API key hay dự án thật, không gọi dịch vụ AI. Kiểm tra API, thống kê số từ, lưu JSON nguyên tử, đường dẫn không hợp lệ, upload lỗi và trạng thái dừng worker. Script test_verification.py cũ có luồng dịch qua mạng; không dùng làm test offline mặc định.

Test trình duyệt dùng Chrome/Edge headless đã cài và Node.js 22+ (WebSocket tích hợp), API được giả lập tại localhost. Không cài npm package, không gọi AI, không dùng hồ sơ trình duyệt cá nhân. Có thể đặt TEST_BROWSER tới executable Chromium khác. Test kiểm tra loại upload, khóa tone Paper, nhân vật Novel, cảnh báo an toàn, heading, dự án rỗng, mobile và modal inert.

## Cấu trúc Paper / Novel

- Upload nhận `document_type=paper|novel`; không truyền thì suy ra PDF→Paper, còn lại→Novel. Sai loại/đuôi file bị từ chối trước khi lưu.
- `BookProject.document_type` và `structure_warnings` được lưu trong metadata. Dự án cũ được suy ra loại trong bộ nhớ, không tự ghi lại hoặc chia lại chương.
- `core/paper_structure.py` dùng outline/font/vị trí, giữ tiểu mục dưới mục lớn và loại running header lặp ở mép trang.
- `core/epub_structure.py` dùng spine, TOC và fragment. `source_doc` / `source_element_index` định vị đoạn khi một XHTML có nhiều chương hoặc nội dung trùng; exporter dùng cùng phép chuẩn hóa phần tử.
- DOCX/Markdown dùng cấp heading mạnh nhất; cảnh báo khi chỉ nhận diện được một chương. Chunk dịch không tạo ranh giới chương mới.
- Worker tạo glossary hiệu dụng: Paper→academic, Novel không dùng academic; không sửa glossary người dùng chỉ để chuẩn hóa giọng.
- PDF→EPUB giáo trình giữ loại `textbook` và nút chuyển đổi riêng.

## Hành vi đã củng cố

- Lưu JSON bằng file tạm cùng thư mục rồi thay thế nguyên tử, giảm nguy cơ mất dữ liệu nếu ghi lỗi.
- Giữ số từ gốc khi cập nhật tiến độ hoặc sửa bản dịch.
- Upload tối đa 100 MiB; hỗ trợ EPUB, PDF, DOCX, TXT, MD; định dạng DOC cũ cần chuyển sang DOCX.
- Dọn file upload và dự án dở dang nếu phân tích thất bại.
- Không cho khởi động lại, chỉnh sửa đoạn hoặc xóa dự án khi worker đang chạy hoặc đang dừng. Lệnh dừng phải chờ yêu cầu AI đang thực hiện kết thúc.
- Không thông báo dịch thành công toàn bộ khi vẫn còn đoạn chưa hoàn thành.
- Giao diện và API phục vụ cùng origin; không bật CORS cho mọi website.

## Giới hạn triển khai

Ứng dụng dành cho chạy cục bộ bằng main.py trên 127.0.0.1. Chưa có xác thực người dùng; không công khai server ra Internet. API key vẫn lưu trong data/settings.json, vì vậy không chia sẻ file này. Lưu nguyên tử áp dụng cho từng file, không phải giao dịch nhiều file; chỉ chạy một tiến trình server. Kiểm thử offline không xác nhận chất lượng dịch, quota/model của nhà cung cấp hay độ trung thực xuất bản của mọi loại sách.
