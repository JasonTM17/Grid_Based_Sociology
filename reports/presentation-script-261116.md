# Kịch bản giữa kỳ — Grid-based clustering / biến thể STING

Kế hoạch thời lượng, không phải bằng chứng đã rehearsal với người thật.
Output đúng rubric: `slides/submission.pptx` và
`notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb` (Jupyter, đã có output).

| Slide | Thời gian | Nội dung và thao tác |
|---|---|---|
|1|0:00–0:30|Đề tài Grid-based; nhóm chọn biến thể STING; dữ liệu tỉnh-năm PAPI.|
|2|0:30–2:00|Bài toán unsupervised, 882×41, thiếu/thang đo, hai feature thực sự dùng.|
|3|2:00–3:15|Chỉ ba mức lưới từ thô đến mịn và số điểm trong ô viền cam.|
|4|3:15–4:30|Đi qua ba bước đếm điểm, chọn ô dày, nối ô chung cạnh.|
|5|4:30–6:00|Đọc bảng đếm 3 × 3. Chỉ hai cụm 7 điểm và một điểm nhiễu rồi chạy mục 2 trong notebook.|
|6|6:00–7:15|Xem kết quả trên 240 điểm giả lập. Giải thích ARI so với nhãn đã biết trong ví dụ.|
|7|7:15–9:45|Xem hai cấu hình trên dữ liệu 2023. Dùng lưới học đến năm 2023 để gán dữ liệu 2024.|
|8|9:45–11:45|Đọc bảng STING, K-means và DBSCAN. Giải thích số cụm, tỷ lệ nhiễu và cách đọc silhouette.|
|9|11:45–13:30|Mở bảng ngưỡng 3, 5 và 8 trong notebook. Giải thích kết quả khi chỉ đổi ngưỡng ô dày.|
|10|13:30–15:00|Chốt kết quả chính và mời hỏi đáp. Tên nguồn nằm trong ghi chú slide và notebook.|

## 5 phút Q&A

- Vì sao đây là Grid-based? Gán điểm→ô, ngưỡng mật độ→ô dày, liên thông→cụm.
- STING gốc khác bản nhóm ở đâu? Distribution type, confidence pruning top-down;
  bản nhóm chọn một mức để cluster/query, công bố là rút gọn.
- Vì sao không báo accuracy PAPI? Không có nhãn xã hội chuẩn; ARI synthetic
  kiểm chứng cài đặt, ARI giữa hai model chỉ là đồng thuận.
- Hai feature chọn thế nào, 2024 có dùng chọn không? Theo allowlist/sweep
  đã công bố; holdout không dùng chọn, nói cả giới hạn lựa chọn.
- Tham số đổi thì sao? Nêu độ nhạy, tỷ lệ noise/cỡ cụm; không chỉ nhìn silhouette.

## Cuối kỳ

Thi vấn đáp offline: `reports/final_report.docx` +
`notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb`; `slides/final.pptx` là phụ trợ tùy chọn.
Trình bày theo luồng dữ liệu PAPI, chọn cặp chỉ tiêu, cơ chế ô dày, cụm và nhiễu,
đối chứng phân cụm, độ nhạy và giới hạn kết luận. Dùng hồi quy, phân loại và
đối chiếu nguồn ngoài khi cần trả lời câu hỏi về phần phân tích bổ trợ.
