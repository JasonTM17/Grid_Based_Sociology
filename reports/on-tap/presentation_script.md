# Kịch bản thuyết trình 11 slide thống nhất — STING × PAPI

Bản thuyết trình hợp nhất phần cơ chế STING (giữa kỳ), kết quả PAPI 2011–2024, **thống kê bàn giao 63 tỉnh cho khách hàng** và kiểm chứng cuối kỳ trong `slides/Nhom15_STING_PAPI.pptx` (và bản đồng bộ `submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.pptx`). Để chạy lại notebook ở máy trình chiếu, mở `notebooks/Nhom15_STING_PAPI.ipynb` hoặc `submissions/Nhom15_STING_PAPI/`. [Hướng dẫn demo](../../DEMO.md)

## Lời mở đầu có thể dùng

> Thưa thầy, nhóm em báo cáo bản hoàn thiện thống nhất của đề tài phân cụm dựa trên lưới STING trên dữ liệu PAPI 2011–2024. Ngoài phần cơ chế lưới 3×3 và đối chứng thuật toán, nhóm đã bổ sung trọng tâm trả lời câu hỏi thống kê bàn giao 63 tỉnh cho khách hàng (Slide 6–7), kết hợp dự báo cảnh báo sớm và kiểm chứng ngoại lai.

## Thời lượng dự kiến (11 slide thống nhất)

| Slide | Thời gian | Nội dung cần nói và thao tác |
|---|---|---|
| 1 | 0:00–0:25 | Tiêu đề đồ án thống nhất: Nhóm 15, chủ đề STING × PAPI & Thống kê bàn giao 63 tỉnh. |
| 2 | 0:25–1:25 | Bài toán & tiền xử lý từ 14 workbook (`882×41`): pipeline 6 bước, giữ 7 cực trị, audit 23/37 cột nhảy thang và đối chiếu Mendeley lệch 0,0. |
| 3 | 1:25–3:25 | Cơ chế STING (`clip(floor)` ở `sting.py`, DFS kề 4 hướng), ví dụ lưới 3×3 (2 cụm 7 điểm + 1 nhiễu) và giả lập 240 điểm (`ARI = 0,950`). |
| 4 | 3:25–5:20 | Phân cụm PAPI 808 train / 869 toàn kỳ (1 cụm lớn `629` hoặc `677` điểm), phản biện 162/171 nhiễu nằm trong `|z| ≤ 3`, so silhouette cùng 680 điểm giao (0,380 vs 0,461 vs 0,274) và bất biến 869/869 ô dưới z-score. |
| 5 | 5:20–6:45 | Quan sát năm 2024 trên lưới cố định 2011–2023: `48/61` tỉnh vào Cụm 2, `13` ô thưa, `2` thiếu điểm; truy vết ca Lạng Sơn từ `(13,9)` sang `(12,10)`. |
| 6 | 6:45–8:45 | **Thống kê bàn giao khách hàng (1/2):** Biểu đồ 4 vùng hành động trên 63 tỉnh 2024 (`stakeholder_quadrants_2024.png`), chứng minh không đánh đồng `13` tỉnh mã `−1` là kém. |
| 7 | 8:45–11:15 | **Thống kê bàn giao khách hàng (2/2):** Bảng tổng hợp 4 nhóm (`8` Biên bứt phá / `48` Vùng lõi gồm `5` chuẩn 14/14 năm / `5` Ưu tiên Y tế `6.1` / `2` Thiếu DL), tách 7 tỉnh rời Cụm 2 (5 lên biên, 2 xuống rìa `6.1`), watchlist trượt vùng và nghịch lý GRDP cao (`104,3` tr) – Y tế `6.1` thấp (`1,69–1,81`). |
| 8 | 11:15–12:35 | Thí nghiệm dự báo bổ trợ Ridge + kịch bản sai số CV 2024 (`AUC = 0,816` xếp hạng tỉnh trượt vùng khi dự báo điểm bị co về trung bình). |
| 9 | 12:35–13:55 | Đối chứng dữ liệu độc lập (PCI, GRDP, Y tế ODM, Nghèo GSO) & kiểm tra độ bền đa chiều PCA/8D OFAT. |
| 10 | 13:55–14:45 | Kết luận giá trị thuật toán, giá trị khách hàng, giới hạn trung thực & 2 nhánh đề xuất cải thiện tiếp theo (cân bằng lớp CV `0,524`, Conformal, bản đồ Choropleth & PAPI 2025). |
| 11 | 14:45–15:00 | Cảm ơn thầy và các bạn, chuyển sang hỏi đáp. |

Ghi người trình bày và thời gian đo được vào [nhật ký luyện tập](rehearsal_log.md).

## Hỏi đáp trọng tâm

- Giải đáp cơ chế thuật toán & nhiễu STING: `reports/on-tap/qa_midterm.md` và `reports/on-tap/qa_course_concepts.md`.
- Giải đáp **thống kê bàn giao 63 tỉnh cho khách hàng** (Câu 45), dự báo & kiểm chứng ngoại lai: `reports/on-tap/qa_final.md`.
- Khi cần chứng minh trực quan trên số liệu sống: chạy `python -m streamlit run app.py` và mở tab **Thống kê khách hàng**.
