# DEMO.md — Hướng dẫn trình diễn trước khi thi (15′ + 5′ Q&A)

_Mục tiêu: bạn mở repo ra và demo được ngay — không cần mạng, không cần chuẩn bị tinh thần nhiều._

## 0. Một lệnh kiểm tra sẵn sàng (làm trước giờ thi 15′)

```powershell
python scripts/deliverables/demo_smoke.py
```

Phải in ra: **KET LUAN: SAN SANG DEMO (N/N muc dat)** với N = số mục kiểm tra (gom cả `submission.pptx` ≤10 slide và `Nhom15_GiuaKy_STING_PAPI.ipynb` 0 lỗi). Nếu có FAIL → sửa xong chạy lại.

## 1. Lắp ráp máy demo

```powershell
# máy lạ: cài môi trường
python -m pip install -r requirements.txt

# Windows — hiển thị Unicode đẹp (tránh ký tự lạ khi chiếu)
chcp 65001

# đối chiếu môn học — mở sẵn trước Q&A (không cần mạng)
results\preprocessing_audit.md              # bảng kiểm tra tiền xử lý PAPI
results\course_supervised_baselines.md      # bảng NB/KNN/SVM/cây/RF (pseudo-label STING)
results\classifier_label_baselines.md       # sàn hoán vị nhãn + drift năm (exploratory)
results\figs\course_confusion_matrix.png    # 6 panel confusion (học phần)
reports\on-tap\qa_course_concepts.md               # hỏi đáp về học máy và nhãn nhiễu STING
```

Mở [slide giữa kỳ](submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.pptx) và
[notebook giữa kỳ](submissions/01-giua-ky/Nhom15_GiuaKy_STING_PAPI.ipynb).
Notebook đã lưu bảng, số liệu và biểu đồ để trình chiếu.

Môi trường đã kiểm chứng là Python 3.14.2 trên Windows 11. Cách tạo lại file
nằm trong [README](README.md#tái-tạo-file-nộp-và-zip).

## 2. Kịch bản 15 phút

Xem [kịch bản theo 10 slide](reports/on-tap/presentation_script.md). Slide 5
dùng bảng đếm 3 × 3. Slide 7–9 giải thích z-score, nguồn gốc số cụm và cách
chạy kiểm tra ngưỡng trên 869 quan sát PAPI 2011–2024.

Khi cần minh họa kết quả đối chiếu PCI, mở dashboard bằng
`python -m streamlit run app.py` và chọn tab **Kiểm chứng ngoại lai**.

## 3. Dự phòng sự cố

| Sự cố | Xử lý |
|---|---|
| Máy chiếu thiếu Python hoặc thư viện | Mở slide 7–9 và notebook giữa kỳ đã lưu sẵn kết quả. |
| Chạy nbconvert báo lỗi | Mở notebook đã lưu (không cần chạy lại); chạy `python scripts/deliverables/demo_smoke.py` để biết hỏng gì |
| Hình phân cụm giữa kỳ không hiện trong notebook | Mở hình cùng số liệu trên slide 7. |
| Font hiển thị lạ | `chcp 65001` rồi mở lại terminal; notebook/slides dùng DejaVu/Calibri (Unicode OK) |
| Mất mạng | Không liên quan — mọi dữ liệu, model, hình đã nằm trong repo |
| Hỏi về nguồn dữ liệu | Chỉ vào `data/raw/*/PROVENANCE.md` (URL + hash SHA-256) |

## 4. Cheat sheet số liệu cho Q&A (in 1 trang để bên cạnh)

| Chủ đề | Số liệu |
|---|---|
| Dataset | 882 × 41 (đáp ứng ≥500×10) · 63 tỉnh × 14 năm · 39 cột số |
| Nguồn | PAPI 2011–2024 (papi.org.vn) · Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1, crosscheck lệch 0.0) |
| STING trên dữ liệu giả lập | ARI = **0.950**, tỷ lệ nhiễu 2.5%. Bộ kiểm thử thuật toán ở `tests/test_sting.py`. |
| Phân cụm PAPI giữa kỳ | 869 quan sát đủ hai chỉ tiêu, gồm 61 quan sát năm 2024. STING cho ba cụm 677, 16 và 5 điểm, với 171 điểm nhiễu. K-means chọn k = 2 với silhouette 0,4472 trong k = 2–5. |
| Tiền xử lý PAPI | `results/preprocessing_audit.md` — 0 trùng khóa / 882 dòng; không nội suy; outlier giữ + đánh dấu |
| Classifier học phần | `results/course_supervised_baselines.csv` — CV macro-F1; holdout 2023→2024 **một lần**; so **khớp pseudo-label STING**, không ground truth xã hội (NB CV cao nhất ≠ “tốt nhất” tổng quát — xem `qa_course_concepts.md` câu 7) |
| Panel | 0.0→NaN (khớp Mendeley) · d7/d8 chỉ có từ 2018 · 23/37 cột bị cờ heuristic audit (`check_data.py`; chưa chứng minh đổi thang) |
| Gán quan sát 2024 bằng lưới cố định | Mục 4.8 giữa kỳ dùng lưới dựng từ 2011–2023. Trong 61 tỉnh có đủ hai chỉ tiêu năm 2024, 48 nằm ở 21 ô dày thuộc một cụm và 13 nằm trong ô thưa. |
| Kiểm chứng bên ngoài | PCI theo cụm STING: ANOVA F(3,743)=9.04, p=6.9e-06 · Kruskal–Wallis H=31.78, p=5.8e-07 · nhóm {nhiễu: 149, cụm 0: 5, cụm 1: 16, cụm 2: 577} · không chứng minh nhân quả (`results/external_validation.md`) |
| Thí nghiệm dự báo hai điểm (cuối kỳ) | Chọn Ridge theo MAE kiểm định trước 2024. Đối chiếu 59 tỉnh, MAE của 4.2 là 0,0736 vs 0,0763 và của 6.1 là 0,0641 vs 0,0683 khi giữ điểm 2023. Dự báo điểm nhận ra 0/11 tỉnh ngoài vùng dày. Xem slide 7–9 và mục 4.1 notebook cuối kỳ. |
| Robustness | PCA d1–d6 (63.2% phương sai, k=1) → không nhận diện · 8 chiều 2018–2024 OFAT so với gốc (k=3, nhiễu 60.5%): f=3 → k=1/91.9%, lv=2 → k=0/100% → không nhận diện; mc=2 → k=2/10.9% vượt ngưỡng k/noise NHƯNG silhouette −0.089 (âm — tách yếu) (`results/robustness.csv`) |
| Đối chứng giữa kỳ | Trên cùng 680 quan sát đã được cả ba cách gán cụm, silhouette là 0,3802 (STING), 0,4605 (K-means k = 2), 0,3499 (K-means k = 3), 0,2740 (DBSCAN). Số cụm và nhiễu tính trên 869 quan sát. |
| Vai trò z-score | Dựng lại lưới theo biên từng trục giữ nguyên 869 chỉ số ô STING. Cùng k = 2, có 68 điểm đổi cụm K-means sau khi ghép tên cụm. Mục 4.7 thử riêng điều kiện so ô con với ô cha. |
| Bài học lớn | Audit gãy thang đo: sd_5_4 đổi 0.25–2.5 → 0.33–3.33 tại 2021; mean 2020 = 1.897, bước nhảy +0.576, còn ×1.333 cộng +0.632 — cùng hướng đổi thang, workbook không chứng minh chỉ do hệ số đó |

## 5. Sau khi thi

1. Điền `reports/on-tap/rehearsal_log.md` (thời gian thực tế từng phần).
2. Điền `reports/on-tap/midterm_feedback.md` ngay sau buổi thi (câu hỏi GV, góp ý).
3. Nếu GV yêu cầu thay đổi → làm trong P4; cập nhật `reports/submission_checklist.md`.
