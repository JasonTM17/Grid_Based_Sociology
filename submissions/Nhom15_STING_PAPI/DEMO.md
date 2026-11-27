# DEMO.md — Hướng dẫn trình diễn trước khi thi (15′ + 5′ Q&A)

Hướng dẫn trình bày kết quả đã lưu và chạy dashboard sau khi cài đủ thư viện.
Các đường dẫn trong Mục 1 dùng cấu trúc repo đầy đủ. Khi dùng ZIP giải nén,
Word, PowerPoint và hai notebook nằm ngay ở thư mục gốc; xem bảng đối chiếu
trong `HUONG_DAN.txt`. Tài liệu ôn tập và các ứng viên mô hình vẫn nằm trên repo.

## 0. Một lệnh kiểm tra sẵn sàng (làm trước giờ thi 15′)

```powershell
python scripts/deliverables/demo_smoke.py
```

Lệnh hỗ trợ cả repo và ZIP giải nén, in **KET LUAN: SAN SANG DEMO (N/N muc dat)**
khi tài liệu, 15 slide, bảng kết quả và outputs notebook đã lưu đều đạt kiểm tra.
Trong bản giải nén, lệnh còn đối chiếu checksum với manifest. Lệnh này không
thực thi lại các ô mã; dùng các lệnh `nbconvert` bên dưới để kiểm tra chạy lại.
Sửa các mục FAIL rồi kiểm tra lại; nếu đã chủ động tái tạo dữ liệu làm đổi
checksum, dùng một bản giải nén mới để kiểm tra gói bàn giao ban đầu.

## 1. Lắp ráp máy demo từ repo đầy đủ

```powershell
# máy lạ: cài môi trường
python -m pip install -r requirements.txt

# Windows — hiển thị Unicode đẹp (tránh ký tự lạ khi chiếu)
chcp 65001

# đối chiếu môn học & thống kê khách hàng — mở sẵn trước Q&A (không cần mạng)
results\stakeholder_summary.md               # thống kê bàn giao 63 tỉnh (4 nhóm hành động)
results\stakeholder_province_summary_2024.csv
results\preprocessing_audit.md              # bảng kiểm tra tiền xử lý PAPI
results\preprocessing_sensitivity.md        # đối chiếu độ nhạy dropna vs SimpleImputer vs Winsorizer
submissions\Nhom15_STING_PAPI\Nhom15_TienXuLy_PAPI.ipynb  # notebook tiền xử lý 6 bước từ workbook gốc
results\course_supervised_baselines.md      # bảng NB/KNN/SVM/cây/RF (pseudo-label STING)
results\classifier_label_baselines.md       # sàn hoán vị nhãn + drift năm (exploratory)
results\figs\course_confusion_matrix.png    # 6 panel confusion (học phần)
reports\on-tap\qa_course_concepts.md        # hỏi đáp về học máy và nhãn nhiễu STING
reports\on-tap\qa_final.md                  # hỏi đáp tổng hợp & câu 45 bàn giao khách hàng
```

Mở [slide trình bày](submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.pptx),
[báo cáo Word](submissions/Nhom15_STING_PAPI/Nhom15_BaoCao_STING_PAPI.docx) và
[notebook thống nhất](submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.ipynb).
Notebook đã lưu đầy đủ bảng, số liệu và biểu đồ để trình chiếu ngay.

### Chạy gói nộp thống nhất trên Windows, Linux và macOS

Giải nén toàn bộ `submissions/Nhom15_STING_PAPI.zip`. Mở terminal trong thư mục giải nén chứa hai notebook,
`requirements.txt`, `src/` và `data/`. Tạo môi trường bằng
`python -m venv .venv` với Python 3.14. Dùng trình thông dịch trong môi trường
này để cài thư viện và chạy notebook.

```sh
python -m pip install -r requirements.txt
python scripts/deliverables/demo_smoke.py
python -m nbconvert --to notebook --execute Nhom15_TienXuLy_PAPI.ipynb --output TienXuLy_chay_lai
python -m nbconvert --to notebook --execute Nhom15_STING_PAPI.ipynb --output STING_PAPI_chay_lai
```

Sau khi kích hoạt môi trường, chạy các lệnh trên với `python`. Có thể dùng
 đường dẫn trực tiếp `./.venv/Scripts/python.exe` trong PowerShell hoặc
`./.venv/bin/python` trên Linux và macOS. Trong Jupyter hoặc VS Code, chọn
kernel của môi trường vừa cài rồi dùng **Restart Kernel → Run All**.
Từ thư mục repo, có thể kiểm tra riêng ZIP thống nhất bằng
`python scripts/deliverables/build_submission_packages.py --verify`.
[Các lượt kiểm tra CI](https://github.com/JasonTM17/Grid_Based_Sociology/actions/workflows/ci.yml)

## 2. Kịch bản 15 phút

Xem [kịch bản theo 15 slide](reports/on-tap/presentation_script.md). Slide 4–6
giải thích cơ chế lưới 3×3, 240 điểm giả lập, đối chứng K-Means/DBSCAN và bất biến z-score.
Slide 7 trình bày 61/63 tỉnh có hai điểm quan sát năm 2024. Slide 8 giữ toàn bộ 63 tỉnh trong bảng gợi ý rà soát; slide 9 dùng 59 tỉnh ghép được hai năm và truy vết Lạng Sơn. Slide 10–12 trình bày dự báo hồi cứu, đối chiếu nguồn ngoài và độ bền. Slide 13 dành cho demo, slide 14 kết luận và slide 15 cảm ơn.

Khi cần minh họa trực quan cho khách hàng hoặc đối chiếu PCI, mở dashboard bằng
`python -m streamlit run app.py` rồi chọn tab **Thống kê khách hàng** (có bản đồ Choropleth 63 tỉnh tương tác, lọc nhóm hành động và xuất Phiếu chẩn đoán 1 trang/tỉnh để in PDF) hoặc **Kiểm chứng ngoại lai**.

## 3. Dự phòng sự cố

| Sự cố | Xử lý |
|---|---|
| Máy chiếu thiếu Python hoặc thư viện | Mở slide PPTX 15 trang, báo cáo Word và notebook đã lưu sẵn kết quả. |
| Chạy nbconvert báo lỗi | Mở notebook đã lưu (không cần chạy lại); chạy `python scripts/deliverables/demo_smoke.py` để biết hỏng gì |
| Hình phân cụm không hiện trong notebook | Mở hình cùng số liệu tương ứng trên slide 4–7 hoặc `results/figs/`. |
| Font hiển thị lạ | `chcp 65001` rồi mở lại terminal; notebook/slides dùng DejaVu/Calibri (Unicode OK) |
| Mất mạng | Không liên quan — mọi dữ liệu, model, hình đã nằm trong repo |
| Hỏi về nguồn dữ liệu | Chỉ vào `data/raw/*/PROVENANCE.md` (URL + hash SHA-256) |

## 4. Cheat sheet số liệu cho Q&A (in 1 trang để bên cạnh)

| Chủ đề | Số liệu |
|---|---|
| Dataset | 882 × 41 (đáp ứng ≥500×10) · 63 tỉnh × 14 năm · 39 cột số |
| Nguồn | PAPI 2011–2024 (papi.org.vn) · Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1, crosscheck lệch 0.0) |
| STING trên dữ liệu giả lập | ARI = **0.950**, tỷ lệ nhiễu 2.5%. Bộ kiểm thử thuật toán ở `tests/test_sting.py`. |
| Phân cụm STING PAPI | 869 quan sát đủ hai chỉ tiêu (`808` train 2011–2023 + `61` năm 2024). Trên 2011–2023: 3 cụm `629 / 16 / 5` và `158` điểm nhiễu (`19,6%`); toàn kỳ 869: `677 / 16 / 5` và `171` nhiễu (`19,7%`). |
| Tiền xử lý PAPI | `results/preprocessing_audit.md` — 0 trùng khóa / 882 dòng; không nội suy; outlier giữ + đánh dấu |
| Thống kê bàn giao 63 tỉnh (2024) | `Biên bứt phá vượt chuẩn`: 8 tỉnh (`4.2` med 2,235, `6.1` med 1,963, GRDP 87,38 tr); `Vùng lõi ổn định (Cụm 2)`: 48 tỉnh (gồm 5 chuẩn 14/14 năm: Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận, Vĩnh Long & 7 tỉnh rìa dưới `6.1`); `Ưu tiên Y tế 6.1`: 5 tỉnh (Hà Nội, Cần Thơ, Gia Lai, Long An, Bình Dương — GRDP med 104,26 tr); `Thiếu dữ liệu 2024`: 2 tỉnh (Vĩnh Phúc, Tiền Giang). (`results/stakeholder_summary.md`) |
| Classifier học phần | `results/course_supervised_baselines.csv` — CV macro-F1; đối chiếu tại **một mốc** 2023→2024; so **khớp pseudo-label STING**, không ground truth xã hội (NB CV cao nhất ≠ “tốt nhất” tổng quát — xem `qa_course_concepts.md` câu 7) |
| Panel | 0.0→NaN (khớp Mendeley) · d7/d8 chỉ có từ 2018 · 23/37 cột bị cờ heuristic audit (`check_data.py`; chưa chứng minh đổi thang) |
| Gán quan sát 2024 bằng lưới cố định | Slide 7 & mục 4 notebook dùng lưới dựng từ 2011–2023. Trong 61 tỉnh có đủ hai chỉ tiêu năm 2024, 48 nằm ở 21 ô dày thuộc Cụm 2 và 13 nằm trong ô thưa (tách riêng 7 tỉnh rời Cụm 2: 5 tới nhóm phía điểm cao, 2 tới nhóm rà soát `6.1`). |
| Kiểm chứng bên ngoài | PCI theo cụm STING: ANOVA F(3,743)=9.04, p=6.9e-06 · Kruskal–Wallis H=31.78, p=5.8e-07 · nhóm {nhiễu: 149, cụm 0: 5, cụm 1: 16, cụm 2: 577} · không chứng minh nhân quả (`results/external_validation.md`) |
| Thí nghiệm dự báo hai điểm | Chọn Ridge theo MAE kiểm định trước 2024. Đối chiếu 59 tỉnh, MAE của 4.2 là 0,0736 vs 0,0763 và của 6.1 là 0,0641 vs 0,0683 khi giữ điểm 2023. Dự báo điểm nhận ra 0/11 tỉnh ngoài vùng dày → phân tích bổ sung kịch bản sai số với AUC hồi cứu thăm dò 0,816, chưa phải xác suất cảnh báo. Xem Slide 10 và mục 6.1 notebook. |
| Robustness | PCA d1–d6 (63.2% phương sai, k=1) → không nhận diện · 8 chiều 2018–2024 OFAT so với gốc (k=3, nhiễu 60.5%): f=3 → k=1/91.9%, lv=2 → k=0/100% → không nhận diện; mc=2 → k=2/10.9% vượt ngưỡng k/noise NHƯNG silhouette −0.089 (âm — tách yếu) (`results/robustness.csv`) |
| Đối chứng thuật toán | Trên cùng 680 điểm giao (869): silhouette 0,380 (STING), 0,461 (K-means k=2), 0,274 (DBSCAN); trên 631 điểm giao (808): 0,366 vs 0,457 vs 0,258. |
| Vai trò z-score | Dựng lại lưới theo biên từng trục giữ nguyên 869/869 chỉ số ô STING. Cùng k = 2, có 68 điểm đổi cụm K-means sau khi ghép tên cụm. |
| Bài học lớn | Audit gãy thang đo: sd_5_4 đổi 0.25–2.5 → 0.33–3.33 tại 2021; mean 2020 = 1.897, bước nhảy +0.576, còn ×1.333 cộng +0.632 — cùng hướng đổi thang, workbook không chứng minh chỉ do hệ số đó |

## 5. Sau khi tập luyện & bảo vệ cuối kỳ

1. Điền `reports/on-tap/rehearsal_log.md` (thời gian thực tế từng slide trong khung 15 phút và các điểm cần chỉnh sửa).
2. Chạy thử hỏi đáp và ghi biên bản các câu cần ôn tại `reports/on-tap/mock_defense_log.md` (đối chiếu `qa_final.md`, `qa_course_concepts.md`, `qa_midterm.md`).
3. Rà soát và đánh dấu hoàn tất các mục còn lại trong `reports/submission_checklist.md` trước khi nộp `submissions/Nhom15_STING_PAPI.zip` lên LMS.
