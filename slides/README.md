# Slide bảo vệ STING trên dữ liệu PAPI

[Nhom15_STING_PAPI.pptx](Nhom15_STING_PAPI.pptx) gồm 15 trang khổ 16:9, có ghi chú
thuyết trình và nguồn cho từng trang. Văn bản, bảng và biểu đồ chính là đối tượng
PowerPoint có thể chỉnh sửa. Nội dung dự kiến trình bày trong 15 phút, thêm 5 phút
hỏi đáp. Xem [kịch bản theo từng slide](../reports/on-tap/presentation_script.md).

## Nội dung

| Slide | Chủ đề |
|---:|---|
| 1 | Đề tài và nhóm thực hiện |
| 2–3 | Bài toán, nguồn dữ liệu, mẫu số và tiền xử lý theo thời gian |
| 4–6 | Cơ chế STING, cụm trên 808 quan sát lịch sử và đối chứng cùng mẫu |
| 7–9 | Quan sát 2024, bảng 63 tỉnh, dịch chuyển trên 59 tỉnh và ca Lạng Sơn |
| 10 | Dự báo hai chỉ tiêu, baseline và giới hạn hồi kiểm |
| 11–12 | Đối chiếu với nguồn ngoài và độ bền của kết quả |
| 13–15 | Demo, kết luận và cảm ơn |

## Tái tạo bản đã chốt

Từ thư mục gốc repo, với các thư viện Python trong `requirements.txt`:

```bash
python scripts/deliverables/build_slides.py
python scripts/deliverables/build_submission_packages.py
```

Lệnh đầu tính lại dữ liệu dùng cho slide rồi đối chiếu với bản đã duyệt trong
`assets/sting_papi_slides_evidence.json`. Nếu dữ liệu và nguồn bố cục còn khớp,
lệnh xuất bản PPTX từ mẫu đã kiểm tra. Cách này không cần Node hay phần mềm Office
để tái tạo đúng bản đã chốt. Đây là đường tái tạo một phiên bản đã duyệt, không
tự thiết kế lại slide khi đổi dữ liệu.

Nếu nguồn dữ liệu, cấu hình hoặc mã bố cục thay đổi, lệnh dừng với thông báo cụ thể
để tránh xuất slide chứa số liệu cũ. Có thể chỉ xuất dữ liệu để đối chiếu:

```bash
python scripts/deliverables/build_slides.py --data-only evidence.json
```

## Thay đổi nội dung hoặc bố cục

Người trình bày có thể sửa trực tiếp PPTX bằng PowerPoint. Nếu cần tái sinh toàn bộ
bố cục bằng mã, nguồn nằm ở `scripts/deliverables/build_slides.mjs` và dùng
`@oai/artifact-tool`. Nhánh này cần một môi trường đã được cấp thư viện đó; thư viện
không nằm trong `requirements.txt` và không cần thiết để mở bài nộp.

```bash
python scripts/deliverables/build_slides.py --engine artifact --render-dir slide-previews
```

Nhánh này tự nhúng hai workbook Excel vào biểu đồ và đối chiếu từng giá trị với
dữ liệu hiển thị trước khi ghi tệp đích. Các bảng, biểu đồ và dữ liệu biểu đồ vẫn
có thể chỉnh sửa trong PowerPoint; không cần bước đóng gói workbook riêng.

Kiểm tra toàn bộ 15 trang, số liệu, chú thích và ghi chú sau khi dựng. Khi bản mới
đã được duyệt, lưu mẫu và đồng bộ lại gói nộp:

```bash
python scripts/deliverables/slides_portable.py --freeze slides/Nhom15_STING_PAPI.pptx
python scripts/deliverables/build_submission_packages.py
python scripts/deliverables/build_submission_packages.py --verify
```

`--freeze` ghi nhận một phiên bản mới, không tự đánh giá chất lượng hình thức.
Không dùng lệnh đó để bỏ qua bước kiểm tra dữ liệu hoặc bố cục.
