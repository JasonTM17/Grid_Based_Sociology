# DEMO.md — Hướng dẫn trình diễn trước khi thi (15′ + 5′ Q&A)

_Mục tiêu: bạn mở repo ra và demo được ngay — không cần mạng, không cần chuẩn bị tinh thần nhiều._

## 0. Một lệnh kiểm tra sẵn sàng (làm trước giờ thi 15′)

```powershell
python scripts/demo_smoke.py
```

Phải in ra: **KET LUAN: SAN SANG DEMO (N/N muc dat)** với N = số mục kiểm tra (gom cả `submission.pptx` ≤10 slide và `submission_demo.ipynb` 0 lỗi). Nếu có FAIL → sửa xong chạy lại.

## 1. Lắp ráp máy demo

```powershell
# máy lạ: cài môi trường
python -m pip install -r requirements.txt

# Windows — hiển thị Unicode đẹp (tránh ký tự lạ khi chiếu)
chcp 65001

# đối chiếu môn học — mở sẵn trước Q&A (không cần mạng)
results\preprocessing_audit.md              # audit Day 4 (bảng Test → Decide)
results\course_supervised_baselines.md      # bảng NB/KNN/SVM/cây/RF (pseudo-label STING)
results\classifier_label_baselines.md       # sàn hoán vị nhãn + drift năm (exploratory)
results\figs\course_confusion_matrix.png    # 6 panel confusion (học phần)
reports\qa_course_concepts.md               # cheat sheet Q&A Day 1–4
```

Mở [slide giữa kỳ](submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.pptx) và
[notebook giữa kỳ](submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.ipynb).
Notebook đã lưu bảng, số liệu và biểu đồ để trình chiếu.

Môi trường đã kiểm chứng là Python 3.14.2 trên Windows 11. Cách tạo lại file
nằm trong [README](README.md#tái-tạo-file-nộp-và-zip).

## 2. Kịch bản 15 phút

Xem [kịch bản theo 10 slide](reports/presentation-script-261116.md). Slide 5
dùng bảng đếm 3 × 3, slide 6 trình bày dữ liệu giả lập, slide 10 chốt kết quả.

Khi cần minh họa kết quả đối chiếu PCI, mở dashboard bằng
`python -m streamlit run app.py` và chọn tab **Kiểm chứng ngoại lai**.

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
| STING trên dữ liệu giả lập | ARI = **0.950**, tỷ lệ nhiễu 2.5%. Bộ kiểm thử thuật toán ở `tests/test_sting.py`. |
| Tiền xử lý (Day 4) | `results/preprocessing_audit.md` — 0 trùng khóa / 882 dòng; không nội suy; outlier giữ + đánh dấu |
| Classifier học phần | `results/course_supervised_baselines.csv` — CV macro-F1; holdout 2023→2024 **một lần**; so **khớp pseudo-label STING**, không ground truth xã hội (NB CV cao nhất ≠ “tốt nhất” tổng quát — xem `qa_course_concepts.md` câu 7) |
| Panel | 0.0→NaN (khớp Mendeley) · d7/d8 chỉ có từ 2018 · 23/37 cột bị cờ heuristic audit (`check_data.py`; chưa chứng minh đổi thang) |
| Dự đoán 2024 | Train ≤2023 (frozen, train-only) · phủ **79%** · {nhiễu: 13, cụm lớn: 48} · 0 chuyển thật 2023→2024 — phát biểu rỗng/vacuous (cả 2023 lẫn 2024 không có điểm cụm 0/1), không chứng minh độ ổn định nhãn |
| Kiểm chứng bên ngoài | PCI theo cụm STING: ANOVA F(3,743)=9.04, p=6.9e-06 · Kruskal–Wallis H=31.78, p=5.8e-07 · nhóm {nhiễu: 149, cụm 0: 5, cụm 1: 16, cụm 2: 577} · không chứng minh nhân quả (`results/external_validation.md`) |
| Model giám sát | Ridge (chọn theo CV) dự báo 6.1 Y tế công lập năm sau: MAE 0.064 vs carry-forward 0.0683 = **giảm 6.3%**; RF 0.0616 = giảm 9.8% · baseline cũng có CV thật trên cùng fold: carry 0.145 vs ridge 0.265 (trung bình train −0.77) — Ridge vẫn được chọn theo CV |
| Robustness | PCA d1–d6 (63.2% phương sai, k=1) → không nhận diện · 8 chiều 2018–2024 OFAT so với gốc (k=3, nhiễu 60.5%): f=3 → k=1/91.9%, lv=2 → k=0/100% → không nhận diện; mc=2 → k=2/10.9% vượt ngưỡng k/noise NHƯNG silhouette −0.089 (âm — tách yếu) (`results/robustness.csv`) |
| So sánh | STING ≈ DBSCAN(eps=0.2) (ARI 0.65) · k-means ép k, silhouette 0.445 (k=2) |
| Bài học lớn | Audit gãy thang đo: sd_5_4 đổi 0.25–2.5 → 0.33–3.33 tại 2021; mean 2020 = 1.897, bước nhảy +0.576, còn ×1.333 cộng +0.632 — cùng hướng đổi thang, workbook không chứng minh chỉ do hệ số đó |

## 5. Sau khi thi

1. Điền `reports/rehearsal_log.md` (thời gian thực tế từng phần).
2. Điền `reports/midterm_feedback.md` ngay sau buổi thi (câu hỏi GV, góp ý).
3. Nếu GV yêu cầu thay đổi → làm trong P4; cập nhật `reports/submission_checklist.md`.
