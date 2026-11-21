# Định dạng báo cáo cuối kỳ theo mẫu ngày 18/11/2026

Mẫu trình bày là `Báo cáo cuối kì .docx` do người dùng gửi, SHA-256
`c10f9b2c8dfe456283374a2b99ce402ebe877a9bd38ba4448b478f295ed28313`.
Bản Học máy dùng thông tin của Nhóm 15 và nội dung nghiên cứu STING trên PAPI.

| Thành phần | Thể thức áp dụng |
|---|---|
| Bìa | Khung đen hai nét, logo trường, tên trường và khoa, tên môn, đề tài, giảng viên, mã học phần và địa danh cuối trang |
| Trang đầu | Nhóm thực hiện, tóm tắt, lời mở đầu, mục lục, danh mục chữ viết tắt, hình ảnh và bảng |
| Khổ và lề | A4 11906 × 16838 twip, lề trái 2,5 cm, phải/trên/dưới 2 cm |
| Thân bài | Times New Roman 13 pt, giãn dòng 1,5, căn đều hai lề, dòng đầu thụt 1,27 cm |
| Tiêu đề | Trang đầu 20 pt, chương 16 pt, đề mục 14 pt, tiểu mục 12 pt |
| Bảng và hình | Hàng tiêu đề bảng nền xám, chú thích đậm nghiêng 12 pt đặt dưới bảng hoặc hình |
| Phân trang | Bảy chương chuyên môn. Số trang đặt giữa chân trang, bắt đầu từ 1 ở Chương 1 |

`assets/report-cover.xml` lưu các đoạn bìa và khung đã điền thông tin.
`assets/report-cover-logo.png` là ảnh logo dùng trên bìa mẫu.
Hai tệp đủ để dựng lại bìa trong dự án.

## Dựng và kiểm tra

```powershell
python scripts/deliverables/build_report.py
python scripts/deliverables/update_report_fields.py
```

Cập nhật trường bằng Microsoft Word trên Windows trước khi đóng gói.
Bộ đóng gói kiểm tra mục lục bảy chương cùng 12 mục hình và 13 mục bảng
đã được Word lưu. Bản hiện tại (sau khi bổ sung mục 3.7 và Bảng 4) kết
xuất 45 trang trong Word (9 trang đầu và 36 trang nội dung đánh số 1–36).
Các mục hình, bảng và chú thích (gồm mục 3.7, mục 5.5, các hình dự báo
và bảng sai số) nằm trọn trên trang tương ứng.
