# Q&A giữa kỳ — bộ câu hỏi dự kiến (12 câu) | Topic 6 · STING × PAPI

_Quy tắc trả lời: ≤60 giây/câu; không chắc → nói "chưa chắc, nhóm sẽ kiểm và trả lời". Trình bày bởi A (câu thuật toán) và B (câu dữ liệu/ý nghĩa)._

## Thuật toán STING

1. **Vì sao grid-based?** — Grid-based không giả định hình dạng cụm; mỗi ô lưu thống kê cục bộ (count, mean, std, min, max theo chiều; **không lưu distribution type như bài gốc — đơn giản hóa**); chi phí xây lưới O(n); phù hợp khi cụm kéo dài theo trục và cần xử lý nhanh dữ liệu lớn.
2. **STING khác DBSCAN thế nào?** — STING chia không gian thành lưới phân cấp, gom ô "dày" liền kề; DBSCAN gom điểm theo mật độ kề trực tiếp. STING song song hóa tự nhiên theo ô và có thống kê truy vấn; DBSCAN trả cụm mềm hơn nhưng nhạy với `eps` và không có lưới phân cấp.
3. **STING khác k-means thế nào?** — k-means gán mọi điểm về centroid gần nhất (ép mọi điểm vào cụm); STING không ép điểm thưa vào cụm — nhận nhãn −1 (nhiễu), nên kết quả trung thực hơn với dữ liệu nhiễu.
4. **min_count chọn thế nào?** — Không cố định trước: nhóm sweep trên dữ liệu giả lập (ARI ≥ 0.9 khi mc=3–8) và trên dữ liệu thật; cấu hình cuối cùng được chốt bằng **quy trình train-only** (`predict_sweep.py`): chọn trên ≤2020, kiểm trên 2021–2022, hoàn toàn không nhìn 2024 — tránh "chọn theo test".
5. **Noise (−1) là gì?** — Điểm thuộc ô lưới không đạt mật độ min_count; STING không ép chúng vào cụm. Ta luôn tách noise khỏi silhouette/DB/CH (metric hình học chỉ tính trên điểm thuộc cụm) và báo cáo noise ratio riêng.
6. **Độ phức tạp của STING?** — Xây lưới O(n) mỗi mức — tổng O(n × số mức) ≈ O(n log n); gom cụm trên các ô dày (số ô nhỏ) tại một mức cố định; `query_rect` chỉ duyệt ô **một mức** nằm trọn trong vùng (không hạ top-down theo confidence như STING gốc).
7. **Nhược điểm lớn nhất của STING?** — Lưới song song trục; nhạy với độ phân giải lưới và min_count; ở không gian ít chiều/nhiều mẫu thưa dễ mất cụm (curse of dimensionality — nhóm đo được: 8 chiều trên 430 điểm cho k=0/100% nhiễu).

## Dữ liệu & chất lượng

8. **Dữ liệu PAPI có gì đặc biệt ảnh hưởng đến phân cụm?** — **23/37 chỉ tiêu bị đánh dấu bởi kiểm tra heuristic (bước nhảy trung bình > 0.25); chưa chứng minh là đổi thang** — ví dụ **đã chứng minh** đổi thang: `sd_5_4` tại 2021 (0.25–2.5 → 0.33–3.33, `data/raw/papi/PROVENANCE.md`). Ảnh hưởng: phải audit và chỉ dùng chỉ tiêu ổn định cho phân tích xuyên năm (`sd_1_3, sd_1_4, sd_4_1–4.4, sd_6_1, sd_6_3`); còn lại không trộn nếu chưa xử lý. (nguồn: scripts/check_data.py:34-40; data/raw/papi/PROVENANCE.md)
9. **0.0 trong PAPI nghĩa là gì?** — "Không có đủ dữ liệu/xếp hạng" của tỉnh năm đó (không phải điểm 0 thật); nhóm quy về NaN theo đúng quy ước gói replication Mendeley (đối chiếu chéo lệch 0.0).
10. **d7/d8 ở đâu?** — Chỉ được đo từ 2018 (Môi trường + Quản trị điện tử); 2011–2017 chỉ có d1–d6. Mọi bảng/biểu đồ xuyên năm trước 2018 chỉ dùng d1–d6; robustness 8 chiều chỉ làm cho 2018–2024 (kết quả âm tính, nhóm báo cáo trung thực).

## Kết quả & ý nghĩa

11. **Kết quả chính là gì? Vì sao 1 cụm lớn?** — Dữ liệu quản trị công PAPI cấp tỉnh/năm **rất đồng nhất** — đại đa số tỉnh-năm rơi vào một vùng dày; chỉ hai cụm ngoại vi nhỏ (16 và 5 điểm, tổng 21) tách được. Đây là phát hiện nghiên cứu trung thực, không phải lỗi thuật toán; nhóm trình bày kèm độ nhạy theo min_count (phủ 79–82%).
12. **Nhóm ngoại vi có ý nghĩa gì?** — Gợi ý "hai tốc độ" quản trị dịch vụ công giữa các tỉnh; tuy nhiên với dữ liệu chỉ số tổng hợp, không nên suy ra nguyên nhân — cần dữ liệu định tính/phỏng vấn để diễn giải chính sách. Nhóm đề xuất hướng nghiên cứu tiếp theo.

## Lý thuyết & demo nộp bài (bổ sung — khớp `submission.pptx` / notebook)

13. **Lưới phân cấp khác lưới phẳng thế nào?** — Mỗi mức chia tinh hơn (`factor**l` đoạn/chiều); thống kê ô được tính lại từng mức với chi phí O(n) khi `fit()` dựng từng mức trực tiếp từ điểm; STING gốc truy vấn **top-down** với pruning confidence, còn nhóm gom cụm/truy vấn tại **một** `cluster_level` cố định. (nguồn: src/sting.py:106-111; src/sting.py:117; src/sting.py:223)
14. **Ô lưới lưu gì?** — count và mean/std/min/max **theo từng chiều**; **không lưu distribution type (đơn giản hóa so với bài gốc)** — đủ cho mật độ cục bộ và truy vấn vùng một mức. (nguồn: src/sting.py:10; src/sting.py:37-49)
15. **Gom cụm?** — Chỉ ô đạt `min_count` (dày); ô kề liên thông được gộp; điểm ô thưa → nhiễu −1.
16. **STING vs k-means/DBSCAN (một câu)?** — STING: lưới + nhiễu tùy chọn, không cần k; k-means ép k và mọi điểm vào cụm; DBSCAN mật độ điểm, không có thống kê ô phân cấp.
17. **Tham số chính?** — `n_levels`, `factor` (độ mịn), `min_count` (ngưỡng dày), `cluster_level` (mức gán nhãn).
18. **Demo 2-D 240 điểm seed 42?** — Hai blob; ARI ≈0.950; chứng minh code trước PAPI; cùng tham số với slide 5 và `tests/test_sting.py`.
19. **PAPI vì sao thường k=1?** — Panel cấp tỉnh/năm rất đồng nhất — `per_year.csv` gần như mọi năm một cụm lớn; tăng độ phân giải lưới mới tách ngoại vi.
20. **Chạy lại notebook nộp bài?** — `python scripts/gen_submission_demo.py` hoặc nbconvert execute `notebooks/submission_demo.ipynb`.
21. **10 slide nộp bài vs 16 slide phụ lục?** — Nộp chính: `slides/submission.pptx` (10 trang, `build_slides_10.py`). Phụ lục cuối kỳ: `slides/final.pptx` (16 trang). Giữa kỳ cũ: `midterm.pptx` 15 trang — không nhầm ba bộ.

## Bẫy thường gặp (trả lời gọn)

- *"Bạn có chọn cấu hình theo kết quả test không?"* — Không; quy trình train-only, 2024 không tham gia chọn cấu hình.
- *"Tại sao không dùng Silhouette cao nhất để chốt model?"* — Silhouette không bản địa với lưới song song trục; nhóm dùng nó chỉ để so sánh thô, tách noise.
- *"Model dự đoán 2024 có chắc không?"* — Ridge (chọn theo CV) đạt MAE 0.064 so với carry-forward 0.0683 = giảm 6.3%; RF 0.0616 = giảm 9.8% trên holdout 2023→2024, nhưng chỉ MỘT holdout duy nhất — cần thêm nhiều năm; nhóm nêu rõ độ bất định.
