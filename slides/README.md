# Slide bảo vệ STING trên dữ liệu PAPI

[Nhom15_STING_PAPI.pptx](Nhom15_STING_PAPI.pptx) gồm 15 trang khổ 16:9, có ghi chú
thuyết trình và nguồn cho từng trang. Văn bản, bảng và biểu đồ chính là đối tượng
PowerPoint có thể chỉnh sửa. Nội dung dự kiến trình bày trong 15 phút, thêm 5 phút
hỏi đáp. Xem [kịch bản theo từng slide](../reports/on-tap/presentation_script.md).

## Nội dung

| Slide | Chủ đề |
|---:|---|
| 1 | Đề tài, câu hỏi phân tích, mục tiêu và nhóm thực hiện |
| 2 | Hai chỉ tiêu PAPI, 882 × 41, tiền xử lý 6 bước, kiểm toán thang đo & độ nhạy B/C vs A |
| 3 | Cơ chế gom ô dày STING, ví dụ 3 × 3 và kiểm chứng 240 điểm giả lập |
| 4 | Phân bố cụm trên 808 quan sát lịch sử và giới hạn cụm lớn chiếm ưu thế |
| 5 | Đối chứng STING, K-means, DBSCAN trên cùng mẫu và bất biến z-score |
| 6 | Đồ thị quan sát 2024 cùng bảng mô tả đủ 63 tỉnh |
| 7 | Dịch chuyển trên 59 tỉnh và phép tính chỉ số ô của Lạng Sơn |
| 8 | Dự báo Ridge, 0/11 trường hợp ngoài vùng, AUC 0,816 & phân loại cân bằng C3/C1 |
| 9 | Hồi quy 17 cấu hình 6.1 (AR(1), Δ6.1, Panel FE), VIF, Wilcoxon, Conformal 90% & E3 |
| 10 | Độ bền số chiều: điểm nghẽn lưới đều (16^d, 0/28 cặp) → QuantileSTING & Subspace CLIQUE |
| 11 | Đối chiếu PCI, GRDP, ODM, nghèo và cột p Year-FE CR1 (63 tỉnh) chỉ ra nhiễu gộp |
| 12 | Suy luận bảng FWL + CR1/TWFE, Wild Bootstrap, FDR 383 không gian con & Moran's I |
| 13 | Số lượng, tỷ lệ và nhận xét về bốn nhóm mô tả năm 2024 trên 63 tỉnh |
| 14 | Hệ thống tích hợp: Dashboard Streamlit 6 tab, Excel 28 sheet, DOCX, phiếu A4 & CI 3 HĐH |
| 15 | Kết luận 4 trụ cột, giới hạn phương pháp luận, bước tiếp theo và hỏi đáp |

Bản 15 trang giữ nguyên 2 biểu đồ PowerPoint nhúng workbook dữ liệu (Slide 4 & Slide 6)
và mở rộng phần học thuật (hồi quy 17 cấu hình, Conformal 90%, QuantileSTING/CLIQUE,
suy luận bảng CR1/TWFE/Holm/FDR, Moran's I) cùng phần hệ thống tích hợp thành các slide
trực quan kèm 4 biểu đồ PNG chẩn đoán. Toàn bộ bảng dữ liệu đều là đối tượng PowerPoint có
thể chỉnh sửa; chi tiết tham số và đường dẫn kiểm chứng nằm trong ghi chú từng trang.

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

Người trình bày có thể sửa trực tiếp PPTX bằng PowerPoint, chạy tác giả 15 trang
`scripts/deliverables/slides_author.py` hoặc đồng bộ nguồn JS tại
`scripts/deliverables/build_slides.mjs` (dùng `@oai/artifact-tool` khi có runtime hỗ trợ).
Thư viện `@oai/artifact-tool` không nằm trong `requirements.txt` và không cần thiết để
mở hoặc tái tạo snapshot bài nộp qua Python (`build_slides.py`).

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
