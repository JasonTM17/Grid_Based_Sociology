# DEMO.md — Hướng dẫn trình diễn trước khi thi (15′ + 5′ Q&A)

_Mục tiêu: bạn mở repo ra và demo được ngay — không cần mạng, không cần chuẩn bị tinh thần nhiều._

## 0. Một lệnh kiểm tra sẵn sàng (làm trước giờ thi 15′)

```powershell
python scripts/demo_smoke.py
```

Phải in ra: **KET LUAN: SAN SANG DEMO (33/33 muc dat)**. Nếu có FAIL → sửa xong chạy lại.

## 1. Lắp ráp máy demo

```powershell
# máy lạ: cài môi trường
python -m pip install -r requirements.txt

# Windows — hiển thị Unicode đẹp (tránh ký tự lạ khi chiếu)
chcp 65001

# mở sẵn 2 thứ
notebooks\midterm_demo.ipynb   # notebook đã có output sẵn (chiếu trực tiếp không cần chạy)
slides\midterm.pptx            # 15 trang, có speaker notes từng trang
```

Môi trường đã kiểm chứng: Python 3.14.2, Windows 11.

## 2. Kịch bản 15 phút (khớp `reports/rehearsal_log.md`)

| Phút | Màn hình | Nội dung |
|---|---|---|
| 0–1 | Slide 1 | Bìa — thesis: dữ liệu PAPI rất đồng nhất, nhóm báo cáo trung thực |
| 1–2 | Slide 2 | Vì sao grid-based (O(n), không giả định hình dạng) |
| 2–3 | Slide 3 | STING 3 bước: lưới phân cấp → thống kê ô → gom cụm |
| 3–4 | Slide 4 | Dữ liệu 882×41; audit thang đo 23/37 cột |
| 4–5 | Slide 5 + notebook §2 | Demo synthetic — ARI 0.950, 22 test xanh |
| 5–6 | Slide 6 + notebook §3–4 | Kết quả thật: đồng nhất (k≈1); độ nhạy lưới |
| 6–8 | Slide 7 | Pipeline dự đoán: train ≤2023 → predict 2024 (out-of-sample duy nhất) |
| 8–9 | Slide 8 | 2024: 48 tỉnh cụm lớn / 13 tỉnh ngoại vi (coverage 79%) |
| 9–10 | Slide 9 | Ridge dự báo 6.1 Y tế công lập năm sau — tốt hơn baseline ~10% MAE |
| 10–11 | Slide 10 | STING vs k-means vs DBSCAN (noise tách khỏi metric) |
| 11–12 | Slide 11 | Bản đồ centroid 2024 |
| 12–13 | Slide 12 | Hạn chế trung thực (robustness âm tính, gãy thang đo) |
| 13–14 | Slide 13 | Lộ trình cuối kỳ (M5–M7) |
| 14–15 | Slide 14–15 | Nguồn dữ liệu · Q&A |

Mẹo: notebook đã **execute sẵn** (0 lỗi, ~18s) — chiếu thẳng không cần chạy live; muốn chạy lại live: `python -m nbconvert --to notebook --execute --inplace notebooks/midterm_demo.ipynb`.

## 3. Dự phòng sự cố

| Sự cố | Xử lý |
|---|---|
| Máy chiếu không có Python/x86 gói | Mở notebook đã có output sẵn + `results/figs/predict_2024.png` |
| Chạy nbconvert báo lỗi | Mở notebook đã lưu (không cần chạy lại); chạy `python scripts/demo_smoke.py` để biết hỏng gì |
| Hình không hiện trong notebook | Mở trực tiếp `results/figs/predict_2024.png`, `evolution.png`, `map_2024.png` |
| Font hiển thị lạ | `chcp 65001` rồi mở lại terminal; notebook/slides dùng DejaVu/Calibri (Unicode OK) |
| Mất mạng | Không liên quan — mọi dữ liệu, model, hình đã nằm trong repo |
| Hỏi về nguồn dữ liệu | Chỉ vào `data/raw/*/PROVENANCE.md` (URL + hash SHA-256) |

## 4. Cheat sheet số liệu cho Q&A (in 1 trang để bên cạnh)

| Chủ đề | Số liệu |
|---|---|
| Dataset | 882 × 41 (đáp ứng ≥500×10) · 63 tỉnh × 14 năm · 39 cột số |
| Nguồn | PAPI 2011–2024 (papi.org.vn) · Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1, crosscheck lệch 0.0) |
| STING synthetic | ARI = **0.950** · nhiễu 2.5% · 22 unit tests xanh · coverage 99% cho `src/sting.py` |
| Panel | 0.0→NaN (khớp Mendeley) · d7/d8 chỉ có từ 2018 · 23/37 cột gãy thang đo (check_data audit) |
| Dự đoán 2024 | Train ≤2023 (frozen, train-only) · phủ **79%** · {nhiễu: 13, cụm lớn: 48} · 0 chuyển thật 2023→2024 |
| Model giám sát | Ridge/RF dự báo 6.1 Y tế công lập năm sau: **thắng carry-forward ~10% MAE** (0.062–0.064 vs 0.068) |
| Robustness | PCA d1–d6 (63% phương sai) và 8 chiều 2018–2024 → **không nhận diện cấu trúc** (âm tính, báo cáo trung thực) |
| So sánh | STING ≈ DBSCAN(eps=0.2) (ARI 0.65) · k-means ép k, silhouette 0.445 (k=2) |
| Bài học lớn | Audit gãy thang đo (sd_5_4 đổi thang 2021, hệ số 1.333 ≈ bước nhảy mean +0.576) |

## 5. Sau khi thi

1. Điền `reports/rehearsal_log.md` (thời gian thực tế từng phần).
2. Điền `reports/midterm_feedback.md` ngay sau buổi thi (câu hỏi GV, góp ý).
3. Nếu GV yêu cầu thay đổi → làm trong P4; cập nhật `reports/submission_checklist.md`.
