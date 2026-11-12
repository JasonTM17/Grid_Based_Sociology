# Đồ án Học máy — Phân cụm 63 tỉnh Việt Nam bằng STING (PAPI 2011–2024)

[![CI](https://github.com/JasonTM17/Grid_Based_Sociology/actions/workflows/ci.yml/badge.svg)](https://github.com/JasonTM17/Grid_Based_Sociology/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center"><img src="assets/social_preview.png" alt="STING × PAPI — Grid-based clustering on Vietnam PAPI 2011-2024" width="100%"></p>

_Banner trên là minh họa trang trí — vị trí chấm sinh ngẫu nhiên (`scripts/build_banner.py`, rng seed 11, mật độ giả định), không phải dữ liệu/kết quả thật. Mọi hình kết quả trong `results/figs/` sinh từ dữ liệu thật._

Đồ án môn Học máy · Chủ đề 6: **Grid-based (clustering)** · Domain: Sociology / History.

**Sắp demo/thi?** Xem [`DEMO.md`](DEMO.md) — một lệnh kiểm tra sẵn sàng: `python scripts/demo_smoke.py` (phải in "SAN SANG DEMO" với toàn bộ mục PASS).

## Cấu trúc dự án

| Thư mục | Nội dung |
|---|---|
| `plans/` | Kế hoạch triển khai & báo cáo kiểm tra nội bộ (thư mục làm việc cục bộ — không commit) |
| `data/raw/papi/` | 14 workbook PAPI 2011–2024 (nguồn: papi.org.vn, dữ liệu công khai; manifest+hash: `PROVENANCE.md`) |
| `data/raw/mendeley/` | Gói replication CC BY 4.0 — 4 file nhỏ dùng trực tiếp được commit (+`PROVENANCE.md`); phần còn lại tải theo DOI |
| `data/raw/boundaries/` | GeoJSON 63 tỉnh (Open Development Vietnam, CC-BY-SA 4.0; lưu ý join: xem `PROVENANCE.md`) |
| `data/raw/pci/` | PCI VCCI–USAID — workbook + trang xếp hạng 2011/2023/2024, báo cáo PDF (dữ liệu công khai, ghi nguồn VCCI–USAID; `PROVENANCE.md`) |
| `data/raw/gso/` | GSO/NSO — HTML PX-Web (GRDP, dân số, **nghèo cấp tỉnh V14.47**) + PDF Niên giám Thống kê (thống kê chính thức công khai; `PROVENANCE.md`) |
| `data/processed/external_poverty_63.csv` | Nghèo cấp tỉnh: tỷ lệ hộ nghèo 63 tỉnh × 17 năm (2006, 2008, 2010 + 2012–2025 liên tục) — pxweb GSO **V14.47** (882 dòng; raw: `pxweb_V14.47_poverty_step2.html`) + 2017–2019 điền từ Niên giám Thống kê 2020/2021 (189 dòng; `scripts/build_poverty_gap.py`); cột `source` ghi nguồn theo từng dòng (builder gộp: `scripts/build_poverty_63.py`); 1070/1071 ô có số (thiếu TP.HCM 2016 — nguồn ghi ".."), không nội suy (`reports/external_data_expansion.md` §3.6–§3.7) |
| `data/raw/odmekong/` | OD Mekong — nghèo 6 vùng 1998–2016 (CC BY-SA), bệnh viện 2020 (ODbL; `PROVENANCE.md`) |
| `data/raw/worldbank/` | World Bank WDI — 4 chỉ số vĩ mô VNM 2010–2024 (CC BY 4.0; `PROVENANCE.md`) |
| `data/processed/` | Panel sạch (kết quả Phase 2) + các file `external_*` (nguồn ngoài; ma trận độ phủ: `reports/external_data_expansion.md`) |
| `src/` | Thư viện STING (tự viết từ đầu) |
| `scripts/` | Script dữ liệu & phân tích |
| `scripts/preprocessing_audit.py` | Kiểm chứng tiền xử lý (Day 4): chỉ đọc dữ liệu, ghi bảng Test → Decide → `results/preprocessing_audit.{md,csv}` |
| `scripts/course_supervised_baselines.py` | So sánh classifier học phần (NB, KNN, SVM, cây, RF) trên pseudo-label STING → `results/course_supervised_baselines.{csv,md}` + `results/figs/course_confusion_matrix.png` |
| `data/raw/course/` | Slide bài giảng + mẫu báo cáo GV — **chỉ lưu local, không commit** (tài liệu bên thứ ba); không script nào trong repo phụ thuộc thư mục này |
| `models/` | Model STING đã huấn luyện + tham số chuẩn hóa (dùng cho dự đoán) |
| `notebooks/` | Notebook nộp bài (Jupyter): `submission_demo.ipynb` (giữa kỳ) + `final_analysis.ipynb` (cuối kỳ) |
| `tests/` | Unit test |
| `results/figs/` | Hình kết quả |
| `reports/` | Báo cáo, ghi chú |
| `reports/qa_course_concepts.md` | Q&A ánh xạ khái niệm Day 1–4 ↔ artifact trong repo (kèm số từ CSV thật) |
| `slides/` | Slide nộp bài `submission.pptx` (10 slide) + deck phụ lục mở rộng `final.pptx` (16 slide) |

## Nguồn dữ liệu & giấy phép

- **PAPI 2011–2024** — CECODES / VFF-CRT / RTA / UNDP. Tải từ <https://papi.org.vn/du-lieu-papi/>.
- Báo cáo tường thuật PAPI 2024 nêu khảo sát 18.894 người dân ở 61 tỉnh, thành phố (trang 10), trong khi panel của repo này là workbook 63 tỉnh theo câu “toàn bộ 63 tỉnh/thành phố từ năm 2011” (trang 15; data/raw/papi/PROVENANCE.md).
- **Gói replication** — Le et al., Mendeley Data, CC BY 4.0. DOI: 10.17632/wbk42j9wc8.1.
- **GeoJSON tỉnh** — Open Development Vietnam (OD Mekong), CC-BY-SA 4.0.
- **PCI (Chỉ số Năng lực cạnh tranh cấp tỉnh)** — VCCI – USAID, dữ liệu công khai <https://pcivietnam.vn>; tái sử dụng ghi nguồn VCCI–USAID ([chính sách trích dẫn dữ liệu](https://pcivietnam.vn/gioi-thieu/chinh-sach-trich-dan-du-lieu.html)).
- **GSO/NSO** — PX-Web <https://pxweb.nso.gov.vn> và Niên giám Thống kê <https://www.nso.gov.vn>; dữ liệu thống kê chính thức công khai (trang bảng ghi "Bản quyền: Không").
- **Nghèo cấp tỉnh (pxweb GSO V14.47 "Tỷ lệ hộ nghèo phân theo địa phương")** — Cục Thống kê, database "Y tế, văn hóa và MSDC" trên <https://pxweb.nso.gov.vn> (database này không mở qua API `/api/v1` — tải qua giao diện PX-Web); cùng điều kiện GSO: dữ liệu thống kê chính thức công khai, trang bảng ghi "Bản quyền: Không" (cập nhật lần cuối 21/08/2026). Độ phủ 63 tỉnh × 14 năm trên bảng pxweb (2006, 2008, 2010, 2012–2016, 2020–2025); 2017–2019 pxweb không công bố — điền từ Niên giám Thống kê 2020/2021 (2026-11-08); lưu ý chuẩn nghèo theo thu nhập (2010–2016) khác chuẩn đa chiều — chi tiết `reports/external_data_expansion.md` §3.6.
- **OD Mekong (thêm)** — nghèo theo 6 vùng 1998–2016 và COVID: CC BY-SA 4.0 (<https://vietnam.opendevelopmentmekong.net/terms-of-use/>); *Health Facilities in Mekong Countries 2020*: ODbL.
- **World Bank WDI** — CC BY 4.0 ([Terms of Use for Datasets](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets)).
- Chi tiết từng nguồn (cách tải, schema, độ phủ, hạn chế) và ma trận độ phủ: [`reports/external_data_expansion.md`](reports/external_data_expansion.md).
- Kết quả kiểm chứng ngoại lai bằng các nguồn này (ANOVA/Kruskal–Wallis PCI theo cụm STING, mật độ y tế 2020, GRDP 2018–2024, WDI): [`results/external_validation.md`](results/external_validation.md).
- Bằng chứng nguồn gốc (URL, ngày tải, giấy phép, SHA-256): các file `PROVENANCE.md` trong `data/raw/*/` và [`data/processed/external_provenance.md`](data/processed/external_provenance.md).

## Chạy nhanh

```powershell
# Kiểm tra môi trường
python -c "import pandas, openpyxl, plotly, sklearn, streamlit; print('ok')"

# Unit test — toàn bộ test pass (gồm tests/test_sting.py cho STING)
python -m pytest tests -q
python -m pytest tests --cov=src -q

# Lint (tùy chọn): python -m pip install -r requirements-dev.txt
python -m ruff check .

# Kiểm tra dữ liệu (sau khi panel được tạo ở Phase 2)
python scripts/check_data.py
```

Ghi chú: `jupyter` CLI chưa vào PATH — dùng `python -m jupyter` / `python -m nbconvert`.

## Đối chiếu nội dung môn học

Bảng dưới ánh xạ chủ đề đã dạy (Day 1–4, môn Học máy — STING vẫn là đề tài clustering Topic 6) sang script/kết quả/notebook trong repo. Số liệu classifier là **mức khớp với pseudo-label STING**, holdout **một lần** 2023→2024 — không có kết luận “vượt trội” so với ground truth xã hội.

| Chủ đề (Day) | Trong repo |
|---|---|
| Ý tưởng ML, học có/không giám sát, clustering grid-based (Day 1) | `src/sting.py`; demo synthetic + test: `notebooks/submission_demo.ipynb`, `tests/test_sting.py`; PAPI thật: `scripts/predict_demo.py`, `results/predict_summary.md` |
| Regression vs classification (Day 1) | Hồi quy: `scripts/predict_supervised.py` → `results/supervised_metrics.csv`; phân loại pseudo-label: cùng script + `results/supervised_summary.md` |
| Naive Bayes, KNN, đánh giá accuracy / F1 (Day 2) | `scripts/course_supervised_baselines.py` → `results/course_supervised_baselines.{csv,md}`; pipeline chọn LR: `scripts/predict_supervised.py` |
| Confusion matrix, precision/recall (Day 2) | Ma trận 6 model học phần: `results/figs/course_confusion_matrix.png`; LR đã chọn (một model): `results/figs/supervised_confusion.png` |
| SVM tuyến tính + kernel RBF (Day 3) | Trong run `course_supervised_baselines` (cùng bảng CSV/MD và hình confusion gộp) |
| Decision Tree, Random Forest (Day 3) | Cùng `scripts/course_supervised_baselines.py`; RF hồi quy thử trong `scripts/predict_supervised.py` (chọn model theo CV, không theo holdout) |
| Tiền xử lý: Cleaning (dedup → imputation → consistency → outlier **cuối**) → Integration → Transformation; mỗi bước Test → Decide (Day 4) | `scripts/preprocessing_audit.py` → `results/preprocessing_audit.{md,csv}`; notebook cuối kỳ đọc CSV: `notebooks/final_analysis.ipynb` |
| Q&A thi / vấn đáp theo slide | `reports/qa_course_concepts.md` (midterm/cuối kỳ bổ sung: `reports/qa_midterm.md`, `reports/qa_final.md`) |

Tái tạo audit và bảng classifier (nếu artifact cũ):

```powershell
python scripts/preprocessing_audit.py
python scripts/course_supervised_baselines.py
```

## Tái tạo deliverable nộp bài (slides + notebook)

```powershell
# Deck nộp bài (10 slide) — build bằng python-pptx
python scripts/build_slides_10.py

# Notebook nộp bài — sinh bằng nbformat rồi execute
python scripts/gen_submission_demo.py
python -m nbconvert --to notebook --execute --inplace notebooks/submission_demo.ipynb
```

- Deck nộp bài: `slides/submission.pptx` (10 slide, tiếng Việt, notes từng slide).
- Notebook nộp bài: `notebooks/submission_demo.ipynb` (execute sạch, 0 lỗi).
- Deck phụ lục mở rộng (cuối kỳ): `slides/final.pptx` (16 slide).

## Dự đoán (train quá khứ → dự đoán năm mới)

Toàn bộ chạy **local, không cần dịch vụ ngoài**. Ba bước:

```powershell
python scripts/predict_sweep.py        # 1) chốt cấu hình (train-only, KHÔNG nhìn 2024)
python scripts/predict_demo.py         # 2) STING: học 2011–2023 → dự đoán cụm 2024
python scripts/predict_supervised.py   # 3) model ML có giám sát (scikit-learn)
```

1. **`predict_sweep.py`** — quét cặp sub-dimension trong allowlist đã sàng lọc;
   mean-jump heuristic chỉ dùng giai đoạn train ≤2020 để xét eligibility, sau đó
   chọn cấu hình bằng train/validation 2021–2022. Dimension-level `d1–d6` chưa vào
   sweep vì thang 1–10 không tự chứng minh tính tương đương xuyên năm. Bảng đầy đủ:
   `results/predict_config_search.csv`. Giao thức, nói trung thực: hàm điểm
   (coverage − 0.5·noise − 0.15·largest − 0.02·|k−3| + 0.03·stable) là heuristic
   chỉnh tay, không có dẫn xuất — cấu hình thoái hóa k=1 đạt điểm cao hơn (0.84 so
   với 0.6213) và chỉ bị chặn bởi bộ lọc cứng (k 2–6, noise ≤ 25%, largest ≤ 85%,
   coverage ≥ 75%); margin top-1/top-2 = 0.018; `stable_mc_pm1` của cấu hình thắng
   là false (được đo, không dùng làm gate); allowlist gồm cả kiến thức ngoại sinh
   PAPI 2021 (loại sd_5_1/5_3/5_4 vì bước nhảy 2021 nằm ngoài giai đoạn train).
2. **`predict_demo.py`** — STING `fit → save → load → predict`: lưu model local
   (`models/sting_predict_model.pkl`) rồi nạp lại để gán cụm ngoài mẫu năm 2024.
   Chỉ hàng đủ hai feature được dự đoán (hiện 61/63 tỉnh; tỉnh thiếu bị loại,
   không nội suy). `-1` nghĩa là điểm nằm ngoài ô dày đã học, không phải cụm thường.
   Kết quả: `results/predict_all_years.csv`,
   `results/predict_summary.md` (gồm độ nhạy theo `min_count` và chuyển cụm tách riêng
   "chuyển thật" vs "chuyển sang/từ nhiễu"), `results/figs/predict_2024.png`.
3. **`predict_supervised.py`** — model có giám sát, lưu local bằng joblib:
   - **Hồi quy (chính):** dự báo *6.1 Y tế công lập* năm t+1 từ 8 sub-dimension năm t.
     Chọn model bằng metric `r2 (expanding origin 2017–2022)` train-only (warm-up 2011–2016):
     hiện Ridge được chọn với R²=0.265; MAE holdout 2023→2024 là 0.0640 so với
     carry-forward 0.0683 (giảm 6.3%). Random Forest có R² CV thấp hơn (0.197) và
     MAE holdout thấp hơn (0.0616); việc chọn model không dựa vào holdout. Đây vẫn
     chỉ là một năm holdout.
     Lưu `models/sup_ridge.joblib`, `models/sup_rf.joblib`; kết quả
     `results/supervised_metrics.csv` + `results/supervised_summary.md`.
   - **Phân loại phụ:** dự báo pseudo-label STING cutoff-local cho năm sau, với expanding
     CV theo origin 2017–2022 (warm-up 2011–2016). CV chọn Logistic Regression
     (macro-F1 0.434; majority baseline 0.228). Trên holdout 2023→2024, macro-F1 là
     0.541 so với baseline 0.157. Đây là mức khớp với nhãn do STING sinh, không phải
     accuracy so với ground truth xã hội; một holdout không chứng minh tổng quát hóa.

## Dashboard phân tích local

Cài dependency và chạy từ thư mục gốc dự án:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Dashboard chỉ đọc panel, cấu hình, kết quả và model local đã lưu; không huấn luyện lại,
không sửa artifact và không gửi dữ liệu ra ngoài. Nếu artifact bị thiếu, app báo file và
lệnh pipeline cần chạy để tạo lại. Bộ lọc năm/tỉnh/cụm ở phần STING không áp dụng cho hồi
quy: holdout luôn là 2023→2024; phần hồi quy chỉ lọc theo tỉnh và assignment cụm ở năm gốc
2023. Kết quả 2024 của STING là assignment vào lưới train trước đó, không phải accuracy có
nhãn chuẩn. Metric hồi quy có một năm holdout; classifier đo khớp pseudo-label STING.

Nạp model để dự đoán điểm mới:

```python
import json, sys
sys.path.insert(0, "src")
import numpy as np
from sting import STING

model = STING.load("models/sting_predict_model.pkl")
info = json.load(open("models/sting_predict_scaler.json", encoding="utf-8"))
mean, scale = np.array(info["mean"]), np.array(info["scale"])

x = np.array([[1.9, 1.9]])           # [sd_4_2, sd_6_1] của tỉnh mới
z = (x - mean) / scale
print(model.predict(z))               # -> cụm dự đoán (hoặc -1: nhiễu/ngoài vùng học)

import joblib
ridge = joblib.load("models/sup_ridge.joblib")
print(ridge.predict(np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])))  # dự báo 6.1 năm sau
```

**Lưu ý thang đo:** `scripts/check_data.py` đánh dấu cột có bước nhảy mean năm >0.25;
đây là heuristic cần đối chiếu workbook/codebook, không tự chứng minh đổi thang. Ví dụ
`sd_5_4` có thay đổi khoảng điểm được ghi trong workbook. Sweep chỉ dùng allowlist
sub-dimension không bị flag trong giai đoạn train; dimension-level scores không được
đưa vào cho tới khi chứng minh được tính so sánh xuyên năm. Thang dimension 1–10 và các đánh dấu thay đổi năm 2021 đều có trong workbook gốc:
`data/raw/papi/2024PAPI_ProvincialIndicators_BangChiTieuCapTinh.xlsx` sheet `2024_PAPI_VIE_ENG`
cột C (dòng 7, 31, 55, 72, 92, 108, 134, 148 ghi `1-10 điểm`) và sheet `2021_VIE_ENG` dòng 166
(`* Những nội dung có thay đổi năm 2021`; dòng 98 đánh dấu Dimension 5);
[`PAPI 2024 One Pager`](https://papi.org.vn/wp-content/uploads/2025/04/26_Thanh_Hoa_ENG.pdf)
chỉ là tham khảo ngoài (máy chủ chặn truy cập tự động; chưa kiểm tự động).

Metadata thang đo theo từng cột của panel (khoảng thang 2011–2020 so với 2021–2024, năm đổi thang, năm ngừng thu thập, nguồn đối chiếu) được lưu kèm panel để bộ dữ liệu tự mô tả:
[`data/processed/papi_panel_scale_metadata.csv`](data/processed/papi_panel_scale_metadata.csv).
Panel giữ nguyên giá trị của cột đổi thang (`sd_5_1`/`sd_5_3`/`sd_5_4`) và cột ngừng thu thập
(`sd_5_2`) trong cùng một tên cột, không có tín hiệu nào trong CSV — đọc metadata này trước
khi học xuyên năm trên panel.

## Khai báo sử dụng công cụ hỗ trợ

Nhóm sử dụng trợ lý AI lập trình cho một số phần của đồ án: khung code ban đầu cho một số script dữ liệu/trực quan, gỡ lỗi, và dry-run đo thời gian chuẩn bị demo (`reports/rehearsal_log.md` mục A ghi rõ phần dry-run do AI/từng cá nhân tự chạy). Mọi quyết định phương pháp, quy trình chọn cấu hình, đánh giá và kết luận do hai thành viên quyết định và kiểm chứng lại; cả hai thành viên chịu trách nhiệm giải thích mọi phần của đồ án. Môn học chưa quy định rubric khai báo cụ thể — nhóm chủ động khai báo theo thông lệ liêm chính học thuật.

## Giấy phép

- **Mã nguồn** (`src/`, `scripts/`, `notebooks/`, `tests/`): **MIT** — xem [`LICENSE`](LICENSE).
- **Dữ liệu** (`data/raw/*/`): giữ giấy phép gốc từng nguồn — xem `PROVENANCE.md` trong từng thư mục (PAPI: dữ liệu công khai CECODES/VFF-CRT/RTA/UNDP; Mendeley: CC BY 4.0, DOI 10.17632/wbk42j9wc8.1; GeoJSON: CC-BY-SA 4.0) — không thuộc MIT.
- **Tác giả:** Nguyễn Tiến Sơn (MSSV 24110054) · Trần Thị Ngọc Quyên (MSSV 24110051) — đồ án môn Học máy, Topic 6.
