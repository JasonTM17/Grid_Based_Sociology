# Định dạng báo cáo theo mẫu người dùng gửi ngày16/11/2026

Nguồn: `File báo cáo tiến độ dự án nhóm.docx` của môn khác; chỉ dùng làm
tham chiếu trình bày. Không lấy nội dung WEB, nhóm13, phân công, cam kết hay
rubric tự chấm vào bài Học máy. Mẫu gốc giữ nguyên, SHA256:
`39803646dfd0aa0050926bd5fe27d4c9478771039eecfa683120686e844aca5c`.

## Thông số đo trực tiếp từ DOCX

| Thành phần | Mẫu và cách áp dụng |
|---|---|
| Khổ trang |A4 làm tròn11909×16834twips, khoảng21.006×29.693cm |
| Lề |Trái/phải1080twips=1.905cm; trên/dưới1008twips=1.778cm |
| Header/footer |Header1.27cm,footer0.8008cm; header trống, số trang PAGE giữa chân trang |
| Thân bài |Times New Roman12pt, đen, giãn dòng1.1, sau đoạn6pt; căn trái, không thụt dòng đầu |
| Tiêu đề đầu |20pt đậm, căn giữa; trước6pt/sau2pt |
| Dòng học phần |12pt nghiêng, căn giữa, sau8pt |
| Heading1 |14pt đậm, trước24pt |
| Heading2/3 |12pt đậm, trước10pt |
| Bảng thông tin |Hai cột, căn giữa bảng, viền đen0.5pt, không tô màu |
| Đoạn trong ô |12pt; trước/sau1pt,giãn1.05; căn giữa theo chiều dọc |
| Đệm ô |Trên/dưới30twips,trái/phải60twips |

Trang bìa dùng trực tiếp hai đoạn tiêu đề và bảng ba hàng, hai cột ở đầu
trang 1 của tài liệu mẫu. Các khối Word giữ vị trí, lề ô và đường viền gốc.
Các ô điền mã nhóm 15, đề tài STING/PAPI, học phần, giảng viên và hai thành viên.
Dòng cuối trang giữ thông tin trường, khoa, bộ môn và tháng 11/2026.

## Áp dụng cho báo cáo Học máy

Giữ ba section bìa/frontmatter/nội dung và bảy chương đã soạn. Đây là phạm vi
nội dung của bài Học máy; số section của mẫu tiến độ không thay đề cương này.
Giữ nguyên mọi đoạn kỹ thuật, số liệu, bảng, hình, field và tài liệu tham khảo.
Đổi typography/màu/căn chỉnh đồng nhất. Bảng dài có header lặp và chiều rộng
không vượt vùng chữ; không tái hiện bảng mẫu vốn rộng hơn vùng chữ.

Hình/caption/TOC không có mẫu tương ứng: giữ cấu trúc và cỡ hình/caption đã có,
đổi font/màu cho thống nhất. Bìa không đánh số; nội dung dùng PAGE giữa chân
trang. Bỏ ngắt trang kép sau bìa. Các field có updateFields để Word cập nhật.

`assets/report-cover.xml` giữ các khối Word đã sao chép và điền thông tin.
`scripts/deliverables/build_report.py` dùng `scripts/deliverables/report_style.py` để ghép bìa trước khi lưu.
Thay bìa của bản hiện có bằng lệnh sau:

```powershell
python scripts/deliverables/report_style.py reports/final_report.docx --cover-only
# Nếu bản chính đang được Word mở, dùng --output <bản-mới.docx>
```

Kiểm tra riêng việc bảo toàn nội dung và render. Không lấy kiểm XML làm bằng
chứng bố cục trực quan; kết quả thực tế lưu tại kế hoạch261116-1540-report-template.
