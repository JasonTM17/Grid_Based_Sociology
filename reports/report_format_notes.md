# Định dạng báo cáo cuối kỳ

Trang bìa theo mẫu giảng viên `Report-proj.pdf.docx` do người dùng gửi ngày
27/11/2026, SHA-256
`1d5ccf67b3a5abd3b9876b2367cb2671852a69dac72bb64fbe23d2957c9ec67d`.
Bìa giữ thứ tự trường, khoa, bộ môn, logo FIT HCM-UTE, sinh viên, đề tài, tên
môn và giảng viên hướng dẫn của mẫu; thay phần tô vàng bằng thông tin đã xác
nhận của Nhóm 15. Dòng cuối ghi nhóm, mã học phần và thời điểm báo cáo; không
sao chép niên khóa minh họa của hai sinh viên trong mẫu.

Thân bài tiếp tục dùng thể thức đã áp dụng từ `Báo cáo cuối kì .docx` do người
dùng gửi ngày 18/11/2026, SHA-256
`c10f9b2c8dfe456283374a2b99ce402ebe877a9bd38ba4448b478f295ed28313`.
Bản Học máy giữ cấu trúc bảy chương nghiên cứu STING trên PAPI.

| Thành phần | Thể thức áp dụng |
|---|---|
| Bìa | Khung đen một nét 0,5 pt, cách mép trang 24 pt; logo FIT HCM-UTE từ mẫu, giữ tỷ lệ vuông; ba dòng đơn vị Tahoma 13 pt; sinh viên Times New Roman 14 pt; đề tài Tahoma 20 pt, dòng PAPI 16 pt; tên môn và giảng viên 14 pt; bỏ tô vàng của nội dung mẫu |
| Trang đầu | Nhóm thực hiện, tóm tắt, lời mở đầu, mục lục, danh mục chữ viết tắt, hình ảnh và bảng |
| Khổ và lề | A4 11906 × 16838 twip; riêng bìa theo mẫu mới, trái 1699 twip (khoảng 3 cm), phải/trên/dưới 1138 twip (khoảng 2 cm); thân bài giữ lề trái 1417 twip (2,5 cm), phải/trên/dưới 1134 twip (2 cm) |
| Thân bài | Times New Roman 13 pt, giãn dòng 1,5, căn đều hai lề, dòng đầu thụt 1,27 cm |
| Tiêu đề | Trang đầu 20 pt, chương 16 pt, đề mục 14 pt, tiểu mục 12 pt; chữ đen |
| Bảng | Nền trắng, chữ và toàn bộ đường viền màu đen; tiêu đề in đậm; bảng từ bốn cột dùng 11 pt, bảng nhỏ dùng 12 pt; hàng tiêu đề lặp ở trang sau, hàng dữ liệu không bị xé đôi |
| Chú thích | Đậm nghiêng 12 pt, đặt dưới hình hoặc bảng; trường SEQ giữ số thứ tự có thể cập nhật |
| Mục lục và danh mục | Chữ 12 pt, liên kết nội bộ đến từng tiêu đề/chú thích, số trang có dấu chấm dẫn |
| Phân trang | Phần đầu dùng số La Mã; Chương 1 bắt đầu lại từ trang 1; các chương tiếp theo và phụ lục bắt đầu ở trang mới |

`assets/report-cover.xml` lưu các đoạn bìa, khổ trang, lề và khung đã điền
thông tin. Định dạng được ghi trực tiếp để bìa không phụ thuộc vào các kiểu
chữ của thân bài. `assets/report-cover-logo.png` là ảnh logo trích nguyên vẹn
từ mẫu giảng viên. Hai tệp này đủ để dựng lại bìa trong dự án.

## Dựng và cập nhật mục lục

Chạy từ thư mục gốc dự án:

```bash
python scripts/deliverables/build_report.py
python scripts/deliverables/update_report_fields.py
```

- Trên Windows, chế độ mặc định dùng Microsoft Word và `pywin32` để cập nhật
  TOC, danh mục hình/bảng, SEQ và phân trang.
- Trên Linux/macOS, chế độ mặc định dùng LibreOffice và PyMuPDF. Có thể chọn rõ
  bằng `--engine libreoffice`; nếu LibreOffice chưa có trên PATH, truyền
  `--soffice /duong/dan/soffice`.
- Nhánh LibreOffice xuất PDF tạm để đo trang, điền cache của các trường Word và
  lặp đến khi số trang ổn định. Các trường TOC/SEQ/PAGE và liên kết nội bộ vẫn
  còn trong DOCX để Word cập nhật tiếp. Quy trình không chạy macro trong tài
  liệu và không thay hồ sơ Office của người dùng.
- Chỉ ghi lại bản DOCX khi xác định được vị trí của mọi mục và phân trang hội tụ.
  Bản xuất PDF cùng tệp tạm phục vụ kiểm tra, không phải thành phần bài nộp.

PyMuPDF và `pywin32` theo nền tảng được khai báo trong `requirements-dev.txt`.
LibreOffice là ứng dụng hệ thống cài riêng khi dùng nhánh Linux/macOS.

## Kiểm tra bản nộp

Bộ đóng gói yêu cầu đủ bảy chương trong mục lục, 13 mục hình và 15 mục bảng,
bao gồm mục 5.8 về thống kê mô tả và gợi ý rà soát 63 tỉnh. Hai bảng mở đầu
(nhóm thực hiện và chữ viết tắt) không đánh số. Bản cập nhật ngày 27/11/2026 có
82 mục điều hướng và render thành 49 trang A4 bằng LibreOffice.

Đối chiếu mục lục với trang nội dung sau mỗi lần thay đổi bố cục. Số trang có
thể thay đổi giữa các trình soạn thảo hoặc khi máy thiếu phông chữ; khi chỉnh
sửa tiếp bằng Word, cập nhật toàn bộ trường rồi kiểm tra lại trước khi in.
