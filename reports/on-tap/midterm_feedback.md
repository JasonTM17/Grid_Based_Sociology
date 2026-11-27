# Phản hồi giữa kỳ & tổng hợp hoàn thiện cuối kỳ

_Trạng thái: **Đã hoàn thành báo cáo giữa kỳ (26/11/2026)** và đã xử lý toàn bộ góp ý vào bản đồ án thống nhất cuối cùng._

## Ghi nhận từ buổi trình bày giữa kỳ

| Mục | Nội dung |
|---|---|
| Câu hỏi / Góp ý trực tiếp của GV | Thầy hỏi thẳng vào giá trị thực tế: **"Em phân cụm vậy nhưng cuối cùng thống kê với khách hàng cái gì á?"** |
| Điểm cần bổ sung phát hiện ra | Bản giữa kỳ mới dừng ở giải thích thuật toán STING (`Cụm 2`, nhãn nhiễu `-1`) và truy vết từng tỉnh mẫu, chưa xuất bảng **thống kê bàn giao theo ngôn ngữ hành động cho khách hàng** trên 63 tỉnh và chưa gộp sản phẩm giữa kỳ + cuối kỳ thành một cấu trúc đồng nhất. |
| Hướng khắc phục đã triển khai | 1. Xây dựng `scripts/analysis/stakeholder_summary.py` phân loại 63 tỉnh năm 2024 thành 4 nhóm hành động (`Biên bứt phá vượt chuẩn 8`, `Vùng lõi ổn định 48` gồm `5` chuẩn 14/14 năm, `Ưu tiên cải thiện Y tế 6.1: 5`, `Thiếu dữ liệu 2`), tách rõ hướng đi của `7` tỉnh rời Cụm 2 (`5` lên biên bứt phá, `2` xuống rìa `6.1`), kèm Top cảnh báo trượt vùng và nghịch lý Đô thị–Y tế.<br>2. Tích hợp vào báo cáo Word Mục 5.8 (`Hình 8`, `Bảng 11–12`), Slide 8–9 trong `slides/Nhom15_STING_PAPI.pptx`, Mục 5 trong `notebooks/Nhom15_STING_PAPI.ipynb`, sheet thứ 24 Excel và tab **Thống kê khách hàng** trên `app.py`.<br>3. Gộp bản giữa kỳ + cuối kỳ + bỏ thư mục `study/` dư thừa để giữ đúng 1 bộ hồ sơ hoàn chỉnh thống nhất (`submissions/Nhom15_STING_PAPI.zip`). |
| Câu hỏi cần chuẩn bị thêm cho cuối kỳ | Xem câu 45 trong [`qa_final.md`](qa_final.md) ("Phân cụm STING xong cuối cùng thống kê được gì bàn giao cho khách hàng?"). |

## Chuỗi kiểm chứng sau chỉnh sửa

1. Toàn bộ bảng/hình thống kê khách hàng truy xuất từ `results/stakeholder_province_summary_2024.csv` và `results/stakeholder_summary.md`.
2. Bộ kiểm thử `python -m pytest tests -q` và gói tự chứa `python scripts/deliverables/build_submission_packages.py --verify` xác nhận đồ án tái lập đầy đủ sau khi gộp.

**Cách đọc sau lần rà soát ngày 27/11/2026:** Tên nhóm trong bảng lịch sử là nhãn nội bộ của sản phẩm. Bản trình bày hiện dùng nhóm mô tả và gợi ý rà soát: 48 tỉnh trong vùng dày, 8 tỉnh ngoài vùng dày phía điểm cao, 5 tỉnh ngoài vùng dày có 6.1 thấp và 2 tỉnh thiếu dữ liệu. Giữ nhãn cụm không chứng minh chất lượng ổn định; GRDP và PAPI chỉ được đối chiếu mô tả; AUC năm 2024 là kết quả thăm dò hồi cứu.
