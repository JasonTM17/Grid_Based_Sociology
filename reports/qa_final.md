# Q&A bảo vệ cuối kỳ — bộ câu hỏi nâng cao | Topic 6 · STING × PAPI

_Quy tắc: ≤60 giây/câu; người trả lời A (thuật toán/dữ liệu) / B (kết quả/ý nghĩa). Mỗi thành viên trả lời được CẢ 14 câu._

## Trọng tâm khoa học

1. **Bạn chứng minh được STING chạy đúng như thế nào?** — 22 unit test trong `tests/test_sting.py`: thống kê ô khớp numpy (tol 1e-9); blobs ARI=0.950; predict/save/load roundtrip; out-of-support → −1; biên/ô rỗng. Nếu được yêu cầu, chạy `python -m pytest tests -q` (toàn bộ test xanh, không nêu số).
2. **Vì sao silhouette không dùng để chọn model?** — Metric hình học không bản địa với lưới song song trục (lưới vuông không hiểu “khoảng cách Euclide giữa cụm”); nhóm dùng silhouette chỉ để so sánh thô, luôn kèm noise tách riêng và độ nhạy min_count; quy tắc chọn cấu hình là train-only dựa trên coverage + độ vững.
3. **“Cấu trúc 3 cụm” ban đầu của bạn hóa ra là artifact thang đo — kể lại.** — cặp sd_5_4×sd_6_2 cho 3 cụm “đẹp” tách hoàn toàn theo giai đoạn 2011–2020 vs 2021–2024; audit chỉ ra sd_5_4 đổi thang tại 2021 (0.25–2.5→0.33–3.33). Mean năm 2020 là 1.897; bước nhảy 2020→2021 là +0.576. Nhân mean 2020 với 1.333 sẽ cộng thêm +0.632, nên bước nhảy cùng hướng với đổi thang, nhưng workbook không chứng minh bước nhảy chỉ do hệ số đó. Mọi kết quả trên cặp đó bị loại; pipeline chuyển sang chỉ tiêu qua audit.
4. **Xử lý gãy thang đo thế nào trong thực nghiệm?** — Audit bước nhảy trung bình năm > 0.25 (23/37 cột bị đánh dấu); phân tích xuyên năm chỉ dùng 8 chỉ tiêu sạch; trong-năm z cho PCA/baselines; báo cáo luôn kèm danh sách audit trong check_data.py.
5. **Robustness âm tính — tại sao vẫn coi là kết quả?** — Vì giả thuyết thay thế (“cấu trúc ẩn ở chiều cao”) đã bị bác bỏ có hệ thống: PCA d1–d6 (63.2% phương sai, k=1) và 8 chiều 2018–2024 (noise 60–99.5%, k=1–3). Báo cáo âm tính minh bạch ngăn người khác tái sử dụng phương pháp sai.

## Chi tiết thuật toán

6. **STING có đảm bảo tìm được đúng cụm không?** — Không có đảm bảo lý thuyết số lớp như k-means (k cố định) hay DBSCAN (tham số mật độ); STING phụ thuộc grid/min_count; ưu điểm là O(n), thống kê cục bộ, truy vấn vùng; độ mạnh/ yếu phụ thuộc phân giải lưới — nhóm đo độ nhạy và báo cáo.
7. **Điều kiện mật độ & vai trò của kiểm định ô?** — Bản hiện thực dùng `min_count` cứng để xác định ô “dày”, kèm tùy chọn `significance_z` để loại các ô có trung bình khác biệt không đáng kể so với ô cha (gọn hơn hai bước reward/penalty class-level của bài báo gốc — mức tương đồng dừng ở ý tưởng "lưới phân cấp + thống kê ô", không overclaim). Có thể bật `significance_z` khi factory cho phép kiểm chứng thêm.
8. **Vì sao dùng 4-connectivity?** — STING nguyên bản gom ô kề mặt; 8-connectivity có thể tạo cụm chéo góc không hợp lý với ranh giới song song trục; nhóm dùng 4-hướng (connectivity=1) và bật tắt được bằng tham số.
9. **Predict cho điểm mới có rủi ro gì?** — Điểm ngoài vùng huấn luyện → −1 (không kẹp biên); điểm trong ô thưa → −1; coverage 79% là ngưỡng-phụ thuộc (mc=3→82%, mc=5→79%, mc=8→70%); báo cáo kèm bảng độ nhạy.

## Kết quả & phương pháp

10. **Vì sao STING ≈ DBSCAN (ARI 0.65) nhưng ≠ k-means (ARI 0.16)?** — STING và DBSCAN cùng họ mật độ-lưới (điểm thuộc vùng đặc); k-means tối ưu centroid toàn cục và ép mọi điểm vào k cụm — hai phân vùng khác bản chất trên gần như một khối điểm; minh chứng: k-means k=2 có silhouette 0.445 và ARI so với STING 0.166 (`results/metrics.csv`), và gán mọi điểm vào cụm — khác STING, vốn để một phần điểm là nhiễu. Kích thước cụm không có trong file metrics.
11. **“Chuyển cụm 2023→2024”: 0 chuyển thật?** — Sau khi loại noise khỏi bài toán gán, 43 tỉnh giữ nguyên cụm 2, 9 đổi sang nhiễu hoặc từ nhiễu ra; không có tỉnh nào đổi giữa hai cụm thật; kết hợp với “dữ liệu đồng nhất”, điều này là kỳ vọng chứ không mâu thuẫn.
12. **Model giám sát giảm MAE 6.3% so với carry-forward — có ý nghĩa gì?** — Ridge (chọn theo CV) dự báo 6.1 Y tế công lập năm sau đạt MAE 0.064 so với carry-forward 0.0683 = giảm 6.3% (RF 0.0616 = giảm 9.8%) trên holdout 2023→2024; nhưng MỘT holdout duy nhất — cần backtest cuốn chiếu nhiều mốc để khẳng định; nhóm không tuyên bố vượt quá bằng chứng.
13. **Phân loại ngoại vi/vùng dày hơn baseline bao nhiêu, có đáng tin không?** — Trên CV expanding-origin (2017–2022), macro-F1 của Logistic Regression đạt 0.434 (LR chọn theo CV), RF 0.397 so với đa số baseline 0.228; trên holdout 2023→2024, mô hình vượt trội đa số baseline về accuracy (LR 0.644, RF 0.678 vs baseline 0.186) và macro-F1 (LR 0.541, RF 0.600 vs baseline 0.157). Dù vượt baseline trên holdout, nhãn chỉ là pseudo-label STING và mới thử nghiệm trên một holdout 2023→2024 nên không khẳng định năng lực dự báo xã hội tổng quát; nhóm giữ tinh thần trung thực, không đưa ra tuyên bố mới.

## Cuối cùng

14. **Nếu làm lại từ đầu, bạn đổi gì?** — (i) chuẩn hóa theo hạng từ đầu để bỏ qua gãy thang đo hoàn toàn; (ii) phân cụm quỹ đạo tỉnh (feature theo thời gian) thay vì phân cụm từng mốc; (iii) backtest cuốn chiếu thay vì một holdout; (iv) ranh giới GeoJSON (choropleth) thay centroid; (v) phỏng vấn sâu 3–5 tỉnh ngoại vi cho phần định tính.

## Câu bổ sung (bảo vệ)

15. **Vì sao pipeline chỉ dùng 8 chỉ tiêu?** — Audit trong `check_data.py` đánh dấu cột có bước nhảy trung bình năm trên 0.25 điểm. Đó là heuristic, không tự chứng minh gãy thang. Một ví dụ đã đối chiếu workbook là `sd_5_4` (0.25–2.5 đến 2020, 0.33–3.33 từ 2021). Hồi quy vì vậy chỉ dùng 8 chỉ tiêu đã qua sàng: `sd_1_3`, `sd_1_4`, `sd_4_1`, `sd_4_2`, `sd_4_3`, `sd_4_4`, `sd_6_1`, `sd_6_3`. (nguồn: scripts/check_data.py:27; scripts/papi_pred_common.py:19)

16. **Vì sao siêu tham số STING được chọn chỉ trên tập train?** — `predict_sweep.py` đóng băng lựa chọn trước khi nhìn 2024. Fit trên dữ liệu đến 2020, chấm trên 2021–2022, và năm 2024 không xuất hiện trong script chọn cấu hình. (nguồn: scripts/predict_sweep.py:3; scripts/predict_sweep.py:17)

17. **Vì sao CV hồi quy là chronological?** — Fold hồi quy chỉ lấy origin train nhỏ hơn năm validation (`years < validation_year`), validation là 2017–2022, và khung train là `year_t < 2023`. Holdout 2023 không vào các fold và không được dùng để chọn mô hình. (nguồn: scripts/predict_supervised.py:118; scripts/predict_supervised.py:249; results/supervised_summary.md:26)

18. **Vì sao chọn Ridge chứ không phải random forest?** — Luật chọn chỉ nhìn `value_cv`. Ridge có CV R² 0.265, random forest 0.197, nên Ridge được chọn dù MAE holdout của random forest (0.0616) thấp hơn Ridge (0.0640). (nguồn: scripts/papi_pred_common.py:61; results/supervised_metrics.csv:4; results/supervised_metrics.csv:5; results/supervised_summary.md:25)

19. **Pseudo-label phân loại cho thấy gì và không cho thấy gì?** — Nhãn là `1` khi STING không gán nhiễu tại cutoff, không phải nhãn người gán. Trên một holdout 2023→2024, logistic regression và random forest có accuracy 0.644 / 0.678 và macro-F1 0.541 / 0.600, so với majority 0.186 và 0.157. Một holdout và pseudo-label không đủ để khẳng định năng lực dự báo tổng quát. (nguồn: scripts/predict_supervised.py:190; results/supervised_metrics.csv:6; results/supervised_metrics.csv:7; results/supervised_metrics.csv:8; results/supervised_summary.md:28)

20. **Hạn chế nào đã được ghi trong repo?** — Một holdout 2023→2024 không chứng minh tổng quát hóa. PCA d1–d6 giữ 0.632 phương sai và không nhận diện cấu trúc; hai nhánh 8 chiều 2018–2024 có noise 0.605 và 0.995, cùng kết luận không nhận diện. (nguồn: results/supervised_summary.md:28; results/robustness.csv:2; results/robustness.csv:3; results/robustness.csv:4)

21. **Nạp lại mô hình đã lưu bằng cách nào?** — `joblib.load('models/sup_ridge.joblib')`, rồi truyền vector 8 chỉ số. Không cần train lại. (nguồn: results/supervised_summary.md:30)

22. **Hai thành viên trình bày những gì?** — Nhật ký rehearsal ghi người nói theo slide, không ghi tỷ lệ phần việc. A nói slide 2, 3, 5, 6, 7, 8, 9 và 10 (vì sao grid, STING ba bước, demo synthetic, kết quả thật, pipeline, kết quả 2024, Ridge, baselines). B nói slide 1, 4, 11, 12, 13 và 14 (bìa, audit PAPI, bản đồ, hạn chế, lộ trình, nguồn). Slide 15 là cả hai. Một tỷ lệ phần trăm công việc không được ghi. (nguồn: reports/rehearsal_log.md:12-26)
