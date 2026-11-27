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
khi tài liệu, 12 slide, bảng kết quả và outputs notebook đã lưu đều đạt kiểm tra.
Trong bản giải nén, lệnh còn đối chiếu checksum với manifest. Lệnh này không
thực thi lại các ô mã; dùng các lệnh `nbconvert` bên dưới để kiểm tra chạy lại.
Sửa các mục FAIL rồi kiểm tra lại; nếu đã chủ động tái tạo dữ liệu làm đổi
checksum, dùng một bản giải nén mới để kiểm tra gói bàn giao ban đầu.

## 1. Chuẩn bị môi trường demo từ repo đầy đủ

```powershell
# Cài thư viện trên máy trình diễn
python -m pip install -r requirements.txt

# Bật UTF-8 trong terminal Windows
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

Mở tài liệu theo đường dẫn của bộ đang dùng. Notebook đã lưu bảng, số liệu và biểu đồ để trình chiếu ngay.

| Tài liệu | Trong kho mã nguồn | Trong thư mục gói ZIP giải nén |
|---|---|---|
| Slide | `slides/Nhom15_STING_PAPI.pptx` | `Nhom15_STING_PAPI.pptx` |
| Báo cáo Word | `reports/Nhom15_BaoCao_STING_PAPI.docx` | `Nhom15_BaoCao_STING_PAPI.docx` |
| Notebook phân tích | `notebooks/Nhom15_STING_PAPI.ipynb` | `Nhom15_STING_PAPI.ipynb` |
| Notebook tiền xử lý | `notebooks/Nhom15_TienXuLy_PAPI.ipynb` | `Nhom15_TienXuLy_PAPI.ipynb` |

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

Xem [kịch bản theo 12 slide](https://github.com/JasonTM17/Grid_Based_Sociology/blob/main/reports/on-tap/presentation_script.md) trong kho mã nguồn. Slide 2 trình bày dữ liệu và tiền xử lý; slide 3–5 giải thích lưới 3×3, 240 điểm giả lập, kết quả lịch sử, đối chứng K-Means/DBSCAN và bất biến z-score. Slide 6 dùng 61/63 tỉnh có hai điểm quan sát năm 2024 và giữ đủ 63 tỉnh trong bảng bàn giao. Slide 7 đối chiếu 59 tỉnh ghép được hai năm và truy vết Lạng Sơn. Slide 8–10 trình bày dự báo hồi cứu, đối chiếu nguồn ngoài và độ bền. Slide 11 dành cho demo bàn giao; slide 12 gộp kết luận, cảm ơn và hỏi đáp.

Khi cần minh họa trực quan cho khách hàng hoặc đối chiếu PCI, mở dashboard bằng
`python -m streamlit run app.py` rồi chọn tab **Thống kê khách hàng** để xem bản đồ 63 tỉnh, lọc nhóm mô tả và tải **Phiếu rà soát tỉnh** dạng HTML; mở HTML trong trình duyệt để in hoặc lưu PDF. Tab **Kiểm chứng ngoại lai** trình bày các nguồn đối chiếu.

Người nhận có thể làm theo [hướng dẫn dashboard](reports/customer_guide.md) và [giải thích kết quả bàn giao](reports/ban-giao-khach-hang-2024.md); cả hai tài liệu nằm trong ZIP.

## 3. Dự phòng sự cố

| Sự cố | Xử lý |
|---|---|
| Máy chiếu thiếu Python hoặc thư viện | Mở slide PPTX 12 trang, báo cáo Word và notebook đã lưu sẵn kết quả. |
| Chạy nbconvert báo lỗi | Mở notebook đã lưu; chạy `python scripts/deliverables/demo_smoke.py` để xác định tệp hoặc đầu ra chưa đạt kiểm tra. |
| Hình phân cụm không hiện trong notebook | Mở hình cùng số liệu tương ứng trên slide 3–6 hoặc `results/figs/`. |
| Font hiển thị lạ | `chcp 65001` rồi mở lại terminal; notebook/slides dùng DejaVu/Calibri (Unicode OK) |
| Mất mạng | Sau khi cài đủ thư viện, có thể trình diễn bằng dữ liệu, mô hình và hình đã lưu trong repo. |
| Hỏi về nguồn dữ liệu | Chỉ vào `data/raw/*/PROVENANCE.md` (URL + hash SHA-256) |

## 4. Bảng số liệu dùng khi hỏi đáp

| Chủ đề | Số liệu |
|---|---|
| Dataset | 882 × 41 (đáp ứng ≥500×10) · 63 tỉnh × 14 năm · 39 cột số |
| Nguồn | PAPI 2011–2024 (papi.org.vn) · Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1, crosscheck lệch 0.0) |
| STING trên dữ liệu giả lập | ARI = **0.950**, tỷ lệ nhiễu 2.5%. Bộ kiểm thử thuật toán ở `tests/test_sting.py`. |
| Phân cụm STING PAPI | 869 quan sát đủ hai chỉ tiêu (`808` train 2011–2023 + `61` năm 2024). Trên 2011–2023: 3 cụm `629 / 16 / 5` và `158` điểm nhiễu (`19,6%`); toàn kỳ 869: `677 / 16 / 5` và `171` nhiễu (`19,7%`). |
| Tiền xử lý PAPI | `results/preprocessing_audit.md` — 0 trùng khóa / 882 dòng; không nội suy; outlier giữ + đánh dấu |
| Thống kê bàn giao 63 tỉnh (2024) | Ngoài vùng dày phía điểm cao: 8 tỉnh (trung vị `4.2` là 2,235, `6.1` là 1,963; GRDP/người trung vị 87,38 triệu đồng). Trong vùng dày (Cụm 2): 48 tỉnh, gồm 5 tỉnh giữ nhãn Cụm 2 trong 14/14 năm (Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận, Vĩnh Long) và 7 tỉnh có `6.1` dưới mốc rà soát nội bộ. Ngoài vùng dày, `6.1` thấp theo quy tắc rà soát: 5 tỉnh (Hà Nội, Cần Thơ, Gia Lai, Long An, Bình Dương; GRDP/người trung vị 104,26 triệu đồng). Thiếu dữ liệu 2024: 2 tỉnh (Vĩnh Phúc, Tiền Giang). Đây là các nhóm mô tả, không phải chuẩn chất lượng chính thức. (`results/stakeholder_summary.md`) |
| Classifier học phần | `results/course_supervised_baselines.csv` — CV macro-F1; đối chiếu tại **một mốc** 2023→2024; so **khớp pseudo-label STING**, không ground truth xã hội (NB CV cao nhất ≠ “tốt nhất” tổng quát — xem `qa_course_concepts.md` câu 7) |
| Panel | 0.0→NaN (khớp Mendeley) · d7/d8 chỉ có từ 2018 · 23/37 cột bị cờ heuristic audit (`check_data.py`; chưa chứng minh đổi thang) |
| Gán quan sát 2024 bằng lưới cố định | Slide 6 & mục 4 notebook dùng lưới dựng từ 2011–2023. Trong 61 tỉnh có đủ hai chỉ tiêu năm 2024, 48 nằm ở 21 ô dày thuộc Cụm 2 và 13 nằm trong ô thưa (tách riêng 7 tỉnh rời Cụm 2: 5 tới nhóm phía điểm cao, 2 tới nhóm rà soát `6.1`). |
| Kiểm chứng bên ngoài | PCI theo cụm STING: ANOVA F(3,743)=9.04, p=6.9e-06 · Kruskal–Wallis H=31.78, p=5.8e-07 · nhóm {nhiễu: 149, cụm 0: 5, cụm 1: 16, cụm 2: 577} · không chứng minh nhân quả (`results/external_validation.md`) |
| Thí nghiệm dự báo hai điểm | Chọn Ridge theo MAE kiểm định trước 2024. Đối chiếu 59 tỉnh, MAE của 4.2 là 0,0736 vs 0,0763 và của 6.1 là 0,0641 vs 0,0683 khi giữ điểm 2023. Dự báo điểm nhận ra 0/11 tỉnh ngoài vùng dày → phân tích bổ sung kịch bản sai số với AUC hồi cứu thăm dò 0,816, chưa phải xác suất cảnh báo. Xem slide 8 và mục 6.1 notebook. |
| Độ bền của phân cụm | PCA d1–d6 giữ 63,2% phương sai nhưng chỉ cho 1 cụm, không đạt tiêu chí số cụm. Với 8 chiều trong 2018–2024, cấu hình gốc có 3 cụm và 60,5% nhiễu; thay lần lượt từng tham số cho kết quả: factor=3 còn 1 cụm/91,9% nhiễu; levels=2 không có cụm/100% nhiễu; min_count=2 đạt 2 cụm/10,9% nhiễu nhưng silhouette = −0,089, cho thấy mức tách cụm yếu. (`results/robustness.csv`) |
| Đối chứng thuật toán | Trên cùng 680 điểm giao (869): silhouette 0,380 (STING), 0,461 (K-means k=2), 0,274 (DBSCAN); trên 631 điểm giao (808): 0,366 vs 0,457 vs 0,258. |
| Vai trò z-score | Dựng lại lưới theo biên từng trục giữ nguyên 869/869 chỉ số ô STING. Cùng k = 2, có 68 điểm đổi cụm K-means sau khi ghép tên cụm. |
| Bài học lớn | Audit gãy thang đo: sd_5_4 đổi 0.25–2.5 → 0.33–3.33 tại 2021; mean 2020 = 1.897, bước nhảy +0.576, còn ×1.333 cộng +0.632 — cùng hướng đổi thang, workbook không chứng minh chỉ do hệ số đó |

## 5. Sau khi tập luyện & bảo vệ cuối kỳ

1. Điền `reports/on-tap/rehearsal_log.md` (thời gian thực tế từng slide trong khung 15 phút và các điểm cần chỉnh sửa).
2. Chạy thử hỏi đáp và ghi biên bản các câu cần ôn tại `reports/on-tap/mock_defense_log.md` (đối chiếu `qa_final.md`, `qa_course_concepts.md`, `qa_midterm.md`).
3. Rà soát và đánh dấu hoàn tất các mục còn lại trong `reports/submission_checklist.md` trước khi nộp `submissions/Nhom15_STING_PAPI.zip` lên LMS.
