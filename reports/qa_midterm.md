# Q&A giữa kỳ — bộ câu hỏi dự kiến (12 câu) | Topic 6 · STING × PAPI

_Quy tắc trả lời: ≤60 giây/câu; không chắc → nói "chưa chắc, nhóm sẽ kiểm và trả lời". Trình bày bởi A (câu thuật toán) và B (câu dữ liệu/ý nghĩa)._

## Thuật toán STING

1. **Vì sao grid-based?** — Grid-based không giả định hình dạng cụm; mỗi ô lưu thống kê cục bộ; chi phí xây lưới O(n); phù hợp khi cụm kéo dài theo trục và cần xử lý nhanh dữ liệu lớn.
2. **STING khác DBSCAN thế nào?** — STING chia không gian thành lưới phân cấp, gom ô "dày" liền kề; DBSCAN gom điểm theo mật độ kề trực tiếp. STING song song hóa tự nhiên theo ô và có thống kê truy vấn; DBSCAN trả cụm mềm hơn nhưng nhạy với `eps` và không có lưới phân cấp.
3. **STING khác k-means thế nào?** — k-means gán mọi điểm về centroid gần nhất (ép mọi điểm vào cụm); STING không ép điểm thưa vào cụm — nhận nhãn −1 (nhiễu), nên kết quả trung thực hơn với dữ liệu nhiễu.
4. **min_count chọn thế nào?** — Không cố định trước: nhóm sweep trên dữ liệu giả lập (ARI ≥ 0.9 khi mc=3–8) và trên dữ liệu thật; cấu hình cuối cùng được chốt bằng **quy trình train-only** (`predict_sweep.py`): chọn trên ≤2020, kiểm trên 2021–2022, hoàn toàn không nhìn 2024 — tránh "chọn theo test".
5. **Noise (−1) là gì?** — Điểm thuộc ô lưới không đạt mật độ min_count; STING không ép chúng vào cụm. Ta luôn tách noise khỏi silhouette/DB/CH (metric hình học chỉ tính trên điểm thuộc cụm) và báo cáo noise ratio riêng.
6. **Độ phức tạp của STING?** — Xây lưới O(n) mỗi mức — tổng O(n × số mức) ≈ O(n log n); gom cụm trên các ô dày (số ô nhỏ), truy vấn vùng chữ nhật chỉ duyệt ô chứa trong vùng.
7. **Nhược điểm lớn nhất của STING?** — Lưới song song trục; nhạy với độ phân giải lưới và min_count; ở không gian ít chiều/nhiều mẫu thưa dễ mất cụm (curse of dimensionality — nhóm đo được: 8 chiều trên 430 điểm cho k=0/100% nhiễu).

## Dữ liệu & chất lượng

8. **Dữ liệu PAPI có gì đặc biệt ảnh hưởng đến phân cụm?** — 23/37 cột chỉ tiêu có **gãy thang đo** giữa các năm (vd `sd_5_4` đổi thang tại 2021 từ 0.25–2.5 lên 0.33–3.33). Ảnh hưởng: phải audit và chỉ dùng chỉ tiêu ổn định cho phân tích xuyên năm (`sd_1_3, sd_1_4, sd_4_1–4.4, sd_6_1, sd_6_3`); còn lại không trộn nếu chưa xử lý.
9. **0.0 trong PAPI nghĩa là gì?** — "Không có đủ dữ liệu/xếp hạng" của tỉnh năm đó (không phải điểm 0 thật); nhóm quy về NaN theo đúng quy ước gói replication Mendeley (đối chiếu chéo lệch 0.0).
10. **d7/d8 ở đâu?** — Chỉ được đo từ 2018 (Môi trường + Quản trị điện tử); 2011–2017 chỉ có d1–d6. Mọi bảng/biểu đồ xuyên năm trước 2018 chỉ dùng d1–d6; robustness 8 chiều chỉ làm cho 2018–2024 (kết quả âm tính, nhóm báo cáo trung thực).

## Kết quả & ý nghĩa

11. **Kết quả chính là gì? Vì sao 1 cụm lớn?** — Dữ liệu quản trị công PAPI cấp tỉnh/năm **rất đồng nhất** — đại đa số tỉnh-năm rơi vào một vùng dày; chỉ một nhóm ngoại vi nhỏ (~14–16 điểm pooled) tách được. Đây là phát hiện nghiên cứu trung thực, không phải lỗi thuật toán; nhóm trình bày kèm độ nhạy theo min_count (phủ 79–82%).
12. **Nhóm ngoại vi có ý nghĩa gì?** — Gợi ý "hai tốc độ" quản trị dịch vụ công giữa các tỉnh; tuy nhiên với dữ liệu chỉ số tổng hợp, không nên suy ra nguyên nhân — cần dữ liệu định tính/phỏng vấn để diễn giải chính sách. Nhóm đề xuất hướng nghiên cứu tiếp theo.

## Bẫy thường gặp (trả lời gọn)

- *"Bạn có chọn cấu hình theo kết quả test không?"* — Không; quy trình train-only, 2024 không tham gia chọn cấu hình.
- *"Tại sao không dùng Silhouette cao nhất để chốt model?"* — Silhouette không bản địa với lưới song song trục; nhóm dùng nó chỉ để so sánh thô, tách noise.
- *"Model dự đoán 2024 có chắc không?"* — Ridge/RF thắng baseline ~10% MAE trên holdout 2023→2024, nhưng chỉ MỘT holdout duy nhất — cần thêm nhiều năm; nhóm nêu rõ độ bất định.
