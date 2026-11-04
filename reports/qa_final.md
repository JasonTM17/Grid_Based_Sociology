# Q&A bảo vệ cuối kỳ — bộ câu hỏi nâng cao | Topic 6 · STING × PAPI

_Quy tắc: ≤60 giây/câu; người trả lời A (thuật toán/dữ liệu) / B (kết quả/ý nghĩa). Mỗi thành viên trả lời được CẢ 14 câu._

## Trọng tâm khoa học

1. **Bạn chứng minh được STING chạy đúng như thế nào?** — 12 unit tests: thống kê ô khớp numpy (tol 1e-9); blobs ARI=0.950; predict/save/load roundtrip; out-of-support → −1; biên/ô rỗng. Chạy `python -m pytest tests -q` ngay trong bảo vệ nếu được yêu cầu.
2. **Vì sao silhouette không dùng để chọn model?** — Metric hình học không bản địa với lưới song song trục (lưới vuông không hiểu “khoảng cách Euclide giữa cụm”); nhóm dùng silhouette chỉ để so sánh thô, luôn kèm noise tách riêng và độ nhạy min_count; quy tắc chọn cấu hình là train-only dựa trên coverage + độ vững.
3. **“Cấu trúc 3 cụm” ban đầu của bạn hóa ra là artifact thang đo — kể lại.** — cặp sd_5_4×sd_6_2 cho 3 cụm “đẹp” tách hoàn toàn theo giai đoạn 2011–2020 vs 2021–2024; audit chỉ ra sd_5_4 đổi thang tại 2021 (0.25–2.5→0.33–3.33; bước nhảy mean +0.576, hệ số đổi thang 1.333 khớp); mọi kết quả trên cặp đó bị loại; pipeline chuyển sang chỉ tiêu qua audit.
4. **Xử lý gãy thang đo thế nào trong thực nghiệm?** — Audit bước nhảy trung bình năm > 0.25 (23/37 cột bị đánh dấu); phân tích xuyên năm chỉ dùng 8 chỉ tiêu sạch; trong-năm z cho PCA/baselines; báo cáo luôn kèm danh sách audit trong check_data.py.
5. **Robustness âm tính — tại sao vẫn coi là kết quả?** — Vì giả thuyết thay thế (“cấu trúc ẩn ở chiều cao”) đã bị bác bỏ có hệ thống: PCA d1–d6 (63.2% phương sai, k=1) và 8 chiều 2018–2024 (noise 60–99.5%, k=1–3). Báo cáo âm tính minh bạch ngăn người khác tái sử dụng phương pháp sai.

## Chi tiết thuật toán

6. **STING có đảm bảo tìm được đúng cụm không?** — Không có đảm bảo lý thuyết số lớp như k-means (k cố định) hay DBSCAN (tham số mật độ); STING phụ thuộc grid/min_count; ưu điểm là O(n), thống kê cục bộ, truy vấn vùng; độ mạnh/ yếu phụ thuộc phân giải lưới — nhóm đo độ nhạy và báo cáo.
7. **Điều kiện mật độ & vai trò của kiểm định ô?** — Bản hiện thực dùng `min_count` cứng để xác định ô “dày”, kèm tùy chọn `significance_z` để loại các ô có trung bình khác biệt không đáng kể so với ô cha (gọn hơn hai bước reward/penalty class-level của bài báo gốc — mức tương đồng dừng ở ý tưởng "lưới phân cấp + thống kê ô", không overclaim). Có thể bật `significance_z` khi factory cho phép kiểm chứng thêm.
8. **Vì sao dùng 4-connectivity?** — STING nguyên bản gom ô kề mặt; 8-connectivity có thể tạo cụm chéo góc không hợp lý với ranh giới song song trục; nhóm dùng 4-hướng (connectivity=1) và bật tắt được bằng tham số.
9. **Predict cho điểm mới có rủi ro gì?** — Điểm ngoài vùng huấn luyện → −1 (không kẹp biên); điểm trong ô thưa → −1; coverage 79% là ngưỡng-phụ thuộc (mc=3→82%, mc=5→79%, mc=8→70%); báo cáo kèm bảng độ nhạy.

## Kết quả & phương pháp

10. **Vì sao STING ≈ DBSCAN (ARI 0.65) nhưng ≠ k-means (ARI 0.16)?** — STING và DBSCAN cùng họ mật độ-lưới (điểm thuộc vùng đặc); k-means tối ưu centroid toàn cục và ép mọi điểm vào k cụm — hai phân vùng khác bản chất trên gần như một khối điểm; minh chứng: k-means k=2 silhouette 0.445 nhưng sizes [498,310] giả tạo so với dữ liệu 1 lõi + vệ tinh.
11. **“Chuyển cụm 2023→2024”: 0 chuyển thật?** — Sau khi loại noise khỏi bài toán gán, 43 tỉnh giữ nguyên cụm 2, 9 đổi sang nhiễu hoặc từ nhiễu ra; không có tỉnh nào đổi giữa hai cụm thật; kết hợp với “dữ liệu đồng nhất”, điều này là kỳ vọng chứ không mâu thuẫn.
12. **Model giám sát thắng carry-forward ~10% — có ý nghĩa gì?** — Ridge/RF dự báo 6.1 Y tế công lập năm sau tốt hơn “giữ nguyên giá trị năm nay” ~10% MAE (0.064/0.062 vs 0.068) trên holdout 2023→2024; nhưng MỘT holdout duy nhất — cần backtest cuốn chiếu nhiều mốc để khẳng định; nhóm không tuyên bố vượt quá bằng chứng.
13. **Vì sao phân loại ngoại vi âm tính?** — Cả LogReg lẫn RF chỉ đạt 0.814–0.831 (đa số baseline 0.814); thay đổi trạng thái ngoại vi gần như không dự báo được từ chỉ số năm trước (tỉnh ổn định theo thời gian); kết quả được giữ nguyên, không tô vẽ.

## Cuối cùng

14. **Nếu làm lại từ đầu, bạn đổi gì?** — (i) chuẩn hóa theo hạng từ đầu để bỏ qua gãy thang đo hoàn toàn; (ii) phân cụm quỹ đạo tỉnh (feature theo thời gian) thay vì phân cụm từng mốc; (iii) backtest cuốn chiếu thay vì một holdout; (iv) ranh giới GeoJSON (choropleth) thay centroid; (v) phỏng vấn sâu 3–5 tỉnh ngoại vi cho phần định tính.
