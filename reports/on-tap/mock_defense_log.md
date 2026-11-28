# Mock Defense — kịch bản 30 phút (tự chạy, 2 người)

_Trạng thái: **chưa chạy live** — cần có mặt cả nhóm (hoặc nhờ bạn học cùng nhóm/mentor). Script dưới đây đủ để tự chạy 15–20 phút nếu không có người thứ 3._

## Kịch bản

| Phút | Việc |
|---|---|
| 0–2 | Người hỏi (đóng vai GV) nêu bối cảnh: "Tôi là GV phản biện, 15 phút" |
| 2–17 | Hỏi 12 câu bất kỳ trong `reports/on-tap/qa_final.md` (random 6 + tự nghĩ 6) |
| 17–20 | Người trả lời tự chấm theo thang (rõ/đúng một nửa/sai) |
| 20–28 | Sửa câu yếu: đọc lại phần tương ứng trong báo cáo/slide |
| 28–30 | Ghi biên bản: câu nào yếu nhất → giao cho ai ôn trước ngày bảo vệ |

## Thang chấm

- **Tốt**: trả lời trôi chảy, đúng số liệu, dẫn được nguồn (panel/test/report).
- **Tạm**: đúng ý nhưng thiếu số/thiếu nguồn → ôn lại trước ngày thi.
- **Yếu**: sai hoặc không trả lời được → xếp vào top-3 câu phải học thuộc.

## Câu hỏi nên luyện

1. STING tự cài như thế nào; khác DBSCAN/k-means ra sao. (qa_final #2, #8, #10)
2. Phân biệt cờ biến động thang đo và bằng chứng từ workbook, giải thích cách chọn chỉ tiêu. (#3, #4)
3. Giải thích một cụm lớn và hai cụm nhỏ trên hai chỉ tiêu đang xét, cùng giới hạn khi liên hệ thực tế. (#10–11, report Ch.6)
4. Phân biệt cấu hình không dùng năm 2024 trong script chọn mẫu với phân tích hồi cứu trên năm 2024 đã được xem; nêu rõ phần kiến thức thang đo 2021 và nguy cơ lạc quan của CV. (#16–17)
5. Kết quả âm tính là kết quả — không giấu, không tô vẽ. (#5, #13)
6. Thống kê bàn giao 63 tỉnh cho khách hàng — tách 13 tỉnh nhãn `-1` thành 8 ca phía điểm cao và 5 ca rà soát 6.1; giải thích vì sao giữ nhãn 14/14 năm chưa chứng minh ổn định chất lượng, và vì sao rời cụm chưa chắc là giảm điểm. (#45, Slide 6–7)
7. Phân tích hồi quy chuyên sâu — vì sao AR(1) / sai phân `Δ6.1` dẫn đầu trong 17 cấu hình (`CV R² = 0,2732`), đa cộng tuyến `VIF = 3,76–5,00` ở `sd_4_1..4_3`, chênh lệch Wilcoxon CV vs holdout 2024 và Conformal 90% phủ `94,9%` (precision `4/28`, độ phủ ≠ độ chính xác cảnh báo), cùng lựa chọn `C3/C1 balanced`. (#46, Báo cáo §5.5 & Slide 8–9)
8. Mở rộng STING đa chiều — chứng minh bùng nổ ô lưới `16^d`, `0/28` cặp có cụm chính ≤ 90%, Subspace CLIQUE (đến 5D) & QuantileSTING (`8D mc=7`, `d1–d8` giảm nhiễu `60,5% → 44,7%`), và lý do giữ STING `2D 3/4/5/2` làm cấu hình chính thức. (#47, Slide 10)
9. Suy luận bảng chuẩn hóa năm (CR1 / TWFE), sàng lọc thăm dò FDR 383 KGC & không gian phần dư — giải thích vì sao STING 2D trên PCI sụp về `p = 0,7007` sau Year-FE CR1, `8D Quantile mc=7` đạt CR1 `p = 0,0156` (Holm nhánh `0,0468`, Holm 6 phép `0,0937`, `TWFE p = 0,342` chưa bác bỏ 0), thăm dò `117/383` BH-FDR 5%, và `residual_ridge` chưa phát hiện tự tương quan 5% (`Moran's I = -0,0431, p = 0,7930`). (#48, Slide 9 & 12)

## Biên bản (điền khi chạy xong)

| Ngày | Người tham gia | Câu yếu nhất | Hành động | Trạng thái |
|---|---|---|---|---|
| ___/___/2026 | ___ | ___ | ___ | ⏳ |
