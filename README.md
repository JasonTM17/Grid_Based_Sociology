# Ứng dụng thuật toán phân cụm dựa trên lưới STING để phân tích đặc điểm và sự biến động của các chỉ số quản trị, hành chính công tại 63 tỉnh, thành phố Việt Nam dựa trên dữ liệu PAPI giai đoạn 2011–2024

*Application of STING grid-based clustering to analyze governance and public administration performance patterns and temporal changes across 63 Vietnamese provinces using PAPI data (2011–2024)*

Đồ án môn Học máy — Nhóm 15.

[![CI](https://github.com/JasonTM17/Grid_Based_Sociology/actions/workflows/ci.yml/badge.svg)](https://github.com/JasonTM17/Grid_Based_Sociology/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Nhóm 15 · Môn Học máy · Chủ đề 6 — Grid-based clustering · Sociology / History

Luồng chính của STING gồm ba bước. `fit()` dựng lưới nhiều mức và đếm điểm theo ô.
`cluster()` giữ các ô đủ điểm ở mức được chọn, rồi dùng DFS nối các ô dày chung cạnh.
`predict()` tra ô và nhãn trên lưới đã học. Trong cấu hình PAPI, hai trục là chỉ tiêu 4.2
và 6.1, lưới có 16 × 16 ô và ngưỡng là 5 quan sát mỗi ô. Bài báo gốc trình bày
cấu trúc lưới thống kê và phép truy vấn phân cấp. [STING, Wang, Yang và Muntz (1997)](https://www.vldb.org/conf/1997/P186.PDF)

## Hồ sơ nộp & Thống kê bàn giao khách hàng

Toàn bộ sản phẩm giữa kỳ và cuối kỳ đã được gộp thành **một bộ đồ án hoàn thiện, đồng nhất** trong [`submissions/`](submissions/) (đã bỏ các bản chia tách và thư mục `study/`). Các notebook và báo cáo đều đã lưu sẵn đầu ra để mở xem ngay.

| Thành phần | Tệp chuẩn trong repo | Bản đồng bộ đóng gói & chạy lại |
|---|---|---|
| Báo cáo Word (DOCX) | [`reports/Nhom15_BaoCao_STING_PAPI.docx`](reports/Nhom15_BaoCao_STING_PAPI.docx) | [`submissions/Nhom15_STING_PAPI/Nhom15_BaoCao_STING_PAPI.docx`](submissions/Nhom15_STING_PAPI/Nhom15_BaoCao_STING_PAPI.docx) |
| Slide trình bày (11 trang) | [`slides/Nhom15_STING_PAPI.pptx`](slides/Nhom15_STING_PAPI.pptx) | [`submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.pptx`](submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.pptx) |
| Notebook phân tích chính | [`notebooks/Nhom15_STING_PAPI.ipynb`](notebooks/Nhom15_STING_PAPI.ipynb) | [`submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.ipynb`](submissions/Nhom15_STING_PAPI/Nhom15_STING_PAPI.ipynb) |
| Notebook tiền xử lý PAPI | [`notebooks/Nhom15_TienXuLy_PAPI.ipynb`](notebooks/Nhom15_TienXuLy_PAPI.ipynb) | [`submissions/Nhom15_STING_PAPI/Nhom15_TienXuLy_PAPI.ipynb`](submissions/Nhom15_STING_PAPI/Nhom15_TienXuLy_PAPI.ipynb) |
| Gói ZIP tự chứa toàn đồ án | [`submissions/Nhom15_STING_PAPI.zip`](submissions/Nhom15_STING_PAPI.zip) | [`HUONG-DAN.txt`](submissions/HUONG-DAN.txt) · [`SHA256SUMS.txt`](submissions/SHA256SUMS.txt) |

**Thống kê bàn giao cho khách hàng (63 tỉnh năm 2024):** Thay vì giao mã kỹ thuật thô (`−1`, `2`), `scripts/analysis/stakeholder_summary.py` chuyển hóa kết quả lưới STING thành 4 nhóm hành động trực diện trên 63 tỉnh ([bảng CSV 63 tỉnh](results/stakeholder_province_summary_2024.csv), [báo cáo tổng hợp](results/stakeholder_summary.md), sheet `Thống kê khách hàng 2024` trong [Excel](results/KetQua_STING_PAPI.xlsx) và tab **Thống kê khách hàng** trên Streamlit):

- **Biên bứt phá vượt chuẩn (8 tỉnh):** Hà Tĩnh, Quảng Ninh, Bình Thuận, Bà Rịa – Vũng Tàu, Sóc Trăng, Tây Ninh, Cà Mau, An Giang (trung vị `4.2 = 2.235`, `6.1 = 1.963`, GRDP `87.38` tr.đ/người) — không đánh đồng là "yếu" dù mang mã `−1`, cần khảo sát chia sẻ điển hình tốt.
- **Vùng lõi ổn định — Cụm 2 (48 tỉnh):** Gồm **5 tỉnh chuẩn tham chiếu 14/14 năm** (`0` năm nhiễu 2011–2024: Phú Thọ, Đà Nẵng, Bình Định, Ninh Thuận, Vĩnh Long) và 7 tỉnh vùng rìa dưới `6.1` cần giữ nhịp đầu tư.
- **Ưu tiên cải thiện Y tế công lập 6.1 (5 tỉnh):** Hà Nội (`1.686`), Cần Thơ (`1.698`), Gia Lai (`1.787`), Long An (`1.807`), Bình Dương (`1.808`) — GRDP/người trung vị đạt `104.26` triệu đồng (vùng lõi `80.97` triệu đồng), nhưng điểm PAPI Y tế công lập `6.1` thấp. Đây là đối chiếu mô tả, không chứng minh quá tải.
- **Thiếu dữ liệu 2024 (2 tỉnh):** Vĩnh Phúc, Tiền Giang (cần kiểm toán thu thập dữ liệu, không nội suy).
- **Phân tách 7 tỉnh rời Cụm 2 (2023→2024):** 5 tỉnh đi lên Biên bứt phá; chỉ 2 tỉnh (Gia Lai, Long An) tụt xuống rìa `6.1`, kèm Top cảnh báo trượt vùng theo kịch bản sai số (AUC `0.816`).

Slide trình bày có **11 trang**: trang 2 bài toán & tiền xử lý; trang 3–4 cơ chế lưới 3×3, giả lập 240 điểm (`ARI = 0,950`), đối chứng K-Means/DBSCAN & bất biến z-score; trang 5 quan sát 2024 & truy vết Lạng Sơn; **trang 6–7 thống kê bàn giao 63 tỉnh cho khách hàng**; trang 8–10 dự báo bổ trợ, kiểm chứng ngoại lai/độ bền đa chiều và kết luận; trang 11 cảm ơn.

Tài liệu ôn tập hỏi đáp, kịch bản thuyết trình và ghi nhận phản biện nằm trong `reports/on-tap/`: [`qa_midterm.md`](reports/on-tap/qa_midterm.md), [`qa_final.md`](reports/on-tap/qa_final.md), [`qa_course_concepts.md`](reports/on-tap/qa_course_concepts.md) và [`presentation_script.md`](reports/on-tap/presentation_script.md). Có thể mở [Hướng dẫn demo](DEMO.md) để chạy kiểm tra trước khi trình bày.

## Cấu trúc dự án

```text
Grid_Based_Sociology/
├── app.py                     # Dashboard Streamlit (gồm tab Thống kê khách hàng & Kiểm chứng ngoại lai)
├── src/                       # Cài đặt lõi STING (sting.py) & tiền xử lý PAPI (preprocessing.py)
├── scripts/                   # Mã tái lập pipeline (chi tiết trong scripts/README.md)
│   ├── data/                  #   Dựng panel, đối chiếu Mendeley, kiểm tra tiền xử lý
│   ├── analysis/              #   Sweep cấu hình, gán cụm, thống kê khách hàng 63 tỉnh, PCI/GRDP/nghèo
│   ├── supervised/            #   Hồi quy & phân loại đối chứng theo nội dung môn học
│   ├── figures/               #   Sinh hình phân tích & sơ đồ lưới
│   ├── notebooks/             #   Sinh bộ đôi notebook thống nhất
│   ├── deliverables/          #   Sinh báo cáo Word, slide PPTX 11 trang, ZIP thống nhất & smoke test
│   └── common/                #   Hàm dùng chung (fig_style, midterm_clustering, ...)
├── notebooks/                 # Hai notebook thống nhất (Nhom15_STING_PAPI & Nhom15_TienXuLy_PAPI)
├── slides/                    # Slide PowerPoint thống nhất (Nhom15_STING_PAPI.pptx — 11 trang)
├── reports/                   # Báo cáo Word thống nhất (Nhom15_BaoCao_STING_PAPI.docx) & hồ sơ kỹ thuật
│   └── on-tap/                #   Hỏi đáp, phản hồi giữa kỳ và kịch bản thuyết trình
├── submissions/               # Sản phẩm đóng gói thống nhất
│   ├── Nhom15_STING_PAPI/     #   Thư mục giải nén sẵn 1-1 với gói ZIP
│   └── Nhom15_STING_PAPI.zip  #   Gói ZIP tự chứa duy nhất để nộp bài & chạy lại
├── data/
│   ├── raw/                   #   Dữ liệu gốc & PROVENANCE.md từng nguồn (course/ lưu local)
│   └── processed/             #   Panel PAPI 882×41 & các bảng dữ liệu ngoài đã làm sạch
├── models/                    # Model STING (.pkl), scaler JSON và joblib hồi quy/phân loại
├── results/                   # Kết quả CSV/MD/JSON, KetQua_STING_PAPI.xlsx (24 sheet) & figs/
├── tests/                     # Bộ kiểm thử pytest toàn dự án
└── assets/                    # Ảnh bìa repo & mẫu XML trang bìa báo cáo
```

| Khi cần | Mở thư mục |
|---|---|
| Gửi bài hoặc chạy lại toàn đồ án | `submissions/Nhom15_STING_PAPI/` hoặc gói tự chứa `submissions/Nhom15_STING_PAPI.zip`. |
| Xem thuật toán và cách chạy | `src/` chứa STING tự cài đặt. [`scripts/`](scripts/README.md) chia theo chức năng; chạy từ thư mục gốc, ví dụ `python scripts/data/check_data.py`. |
| Xem thống kê bàn giao 63 tỉnh | `python scripts/analysis/stakeholder_summary.py`, bảng `results/stakeholder_province_summary_2024.csv` hoặc chạy `app.py` ở tab **Thống kê khách hàng** (kèm bản đồ Choropleth 63 tỉnh & xuất Phiếu chẩn đoán từng tỉnh từ `scripts/analysis/client_product.py`). |
| Tìm dữ liệu | [`data/`](data/README.md): `data/raw/` chứa workbook và nguồn tham chiếu; `data/processed/` chứa panel PAPI và dữ liệu đã xử lý. |
| Xem kết quả đã lưu | `models/` chứa model và cấu hình. [`results/`](results/README.md) chứa bảng CSV/MD/JSON, Excel và hình `figs/`. |
| Tái tạo bài nộp & ôn tập | [`notebooks/`](notebooks/README.md), `slides/` và [`reports/`](reports/README.md) chứa bộ đôi notebook, slide, báo cáo nguồn và tài liệu ôn tập. |
| Kiểm tra hoặc chỉnh tài liệu | `tests/` có bộ kiểm thử. `assets/` chứa ảnh bìa repo và mẫu bìa báo cáo. |

Tư liệu bài giảng của giảng viên được lưu cục bộ trong `data/raw/course/` để nhóm ôn tập.

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
- Kết quả kiểm chứng bên ngoài bằng các nguồn này (ANOVA/Kruskal–Wallis PCI theo cụm STING, mật độ y tế 2020, GRDP 2018–2024, WDI): [`results/external_validation.md`](results/external_validation.md).
- Bằng chứng nguồn gốc (URL, ngày tải, giấy phép, SHA-256): các file `PROVENANCE.md` trong `data/raw/*/` và [`data/processed/external_provenance.md`](data/processed/external_provenance.md).

## Chạy nhanh

```powershell
# Kiểm tra môi trường
python -c "import pandas, openpyxl, plotly, sklearn, streamlit; print('ok')"

# Chạy bộ kiểm thử
python -m pytest tests -q

# Lint (tùy chọn): python -m pip install -r requirements-dev.txt
python -m ruff check .

# Kiểm tra dữ liệu (sau khi panel được tạo ở Phase 2)
python scripts/data/check_data.py
```

Ghi chú: `jupyter` CLI chưa vào PATH — dùng `python -m jupyter` / `python -m nbconvert`.

## Đối chiếu nội dung môn học

Bảng liên kết các nội dung học máy với mã nguồn, kết quả và notebook của đồ án. Số liệu classifier là **mức khớp với pseudo-label STING**, holdout **một lần** 2023→2024 — không có kết luận “vượt trội” so với ground truth xã hội.

| Nội dung học máy | Trong repo |
|---|---|
| Ý tưởng ML, học có/không giám sát, clustering grid-based | `src/sting.py`; demo synthetic + PAPI + test: `notebooks/Nhom15_STING_PAPI.ipynb`, `tests/test_sting.py`; PAPI thật: `scripts/analysis/predict_demo.py`, `results/predict_summary.md` |
| Regression vs classification | Hồi quy: `scripts/supervised/predict_supervised.py` → `results/supervised_metrics.csv`; phân loại pseudo-label: cùng script + `results/supervised_summary.md` |
| Naive Bayes, KNN, đánh giá accuracy / F1 | `scripts/supervised/course_supervised_baselines.py` → `results/course_supervised_baselines.{csv,md}`; sàn chance/drift: `scripts/supervised/classifier_label_baselines.py` → `results/classifier_label_baselines.{csv,md}`; pipeline chọn LR: `scripts/supervised/predict_supervised.py` |
| Confusion matrix, precision/recall | Ma trận 6 model học phần: `results/figs/course_confusion_matrix.png`; LR đã chọn (một model): `results/figs/supervised_confusion.png` |
| SVM tuyến tính + kernel RBF | Trong run `course_supervised_baselines` (cùng bảng CSV/MD và hình confusion gộp) |
| Decision Tree, Random Forest | Cùng `scripts/supervised/course_supervised_baselines.py`; RF hồi quy thử trong `scripts/supervised/predict_supervised.py` (chọn model theo CV, không theo holdout) |
| Tiền xử lý PAPI (làm sạch, tích hợp và chuẩn hóa) | Mô-đun `src/preprocessing.py` (`PREPROCESSING_PIPELINE` 6 bước, đọc trực tiếp 14 workbook PAPI + thử nghiệm Cleaning/Transformation) được nhập trực tiếp vào `notebooks/Nhom15_TienXuLy_PAPI.ipynb` và `notebooks/Nhom15_STING_PAPI.ipynb` (§2). `scripts/data/preprocessing_audit.py` và `scripts/data/preprocessing_sensitivity.py` tạo bảng kiểm tra và đối chiếu độ nhạy. |
| Linear, Polynomial & Logistic Regression | Phụ lục B của `notebooks/Nhom15_STING_PAPI.ipynb` (OLS residual $\varepsilon_i$, đa thức $m \le n$, Sigmoid & Binary Cross-Entropy) |
| K-Means, TRAP, Linkage & Dendrogram vs STING | Mục 1–3 & Phụ lục C của `notebooks/Nhom15_STING_PAPI.ipynb` (sơ đồ lưới 3×3, phản biện nhiễu `−1`, đối chứng K-Means/DBSCAN, Elbow/Silhouette & dendrogram phân cấp) |
| Thống kê bàn giao khách hàng (63 tỉnh) | `scripts/analysis/stakeholder_summary.py`, Mục 5 của `notebooks/Nhom15_STING_PAPI.ipynb`, Mục 5.8 báo cáo Word & Slide 6–7 |
| Q&A thi / vấn đáp theo slide | `reports/on-tap/qa_course_concepts.md`, `reports/on-tap/qa_midterm.md`, `reports/on-tap/qa_final.md` |

Tái tạo audit và bảng classifier (nếu artifact cũ):

```powershell
python scripts/data/preprocessing_audit.py
python scripts/supervised/course_supervised_baselines.py
python scripts/supervised/classifier_label_baselines.py   # tùy chọn — sàn hoán vị / drift thời gian
```

## Tái tạo bộ hồ sơ nộp và ZIP thống nhất

```powershell
# Tiền xử lý, phân tích khách hàng & dự báo lưới
python scripts/notebooks/gen_preprocessing_notebook.py
python scripts/analysis/stakeholder_summary.py --with-excel
python scripts/figures/forecast_papi_grid.py
python scripts/notebooks/gen_final_analysis.py

# Báo cáo Word (kèm cập nhật TOC/danh mục hình-bảng qua Word COM) & Slide 11 trang
python scripts/deliverables/build_report.py
python scripts/deliverables/update_report_fields.py
python scripts/deliverables/build_slides.py

# Đóng gói gói ZIP duy nhất & chạy thử cả hai notebook từ bản giải nén
python scripts/deliverables/build_submission_packages.py
python scripts/deliverables/build_submission_packages.py --verify
```

ZIP lấy các bản gốc trong `notebooks/`, `slides/` và `reports/`, đồng thời đồng bộ 1-1 ra thư mục `submissions/Nhom15_STING_PAPI/`.
Slide 5 và mục 4 của `Nhom15_STING_PAPI.ipynb` cùng tính kết quả gán năm 2024 từ panel PAPI và trình bày ví dụ Lạng Sơn; Slide 6–7 và mục 5 trình bày thống kê bàn giao 63 tỉnh cho khách hàng; Slide 11 dành để cảm ơn. Khi cập nhật panel, chạy `python scripts/analysis/predict_demo.py` và `python scripts/analysis/stakeholder_summary.py --with-excel` trước khi tạo lại notebook, báo cáo và slide. Trình đóng gói kiểm tra riêng PDF báo cáo PAPI và ZIP Mendeley; tệp nào có sẵn sẽ được đưa vào gói và liệt kê trong `HUONG-DAN.txt`.

## Dự báo hai chỉ tiêu và đối chiếu trên lưới STING

Chạy `python scripts/figures/forecast_papi_grid.py` để tạo dự báo 2024 từ tám điểm PAPI năm 2023. Quy trình chọn mô hình cho hai chỉ tiêu bằng sáu lượt kiểm định có đích 2018–2023, rồi đánh giá trên cùng các tỉnh đối chiếu được năm 2024. Dùng chung lưới STING dựng từ dữ liệu đến 2023 cho điểm dự báo và điểm thực tế.

Ridge đạt MAE 0,0736 và 0,0641 trên 59 tỉnh, so với 0,0763 và 0,0683 khi giữ điểm 2023. RMSE ở chỉ tiêu 4.2 tăng nhẹ. Dự báo điểm đưa cả 59 tỉnh vào cụm lớn và bỏ sót 11 tỉnh có quan sát ngoài vùng dày. Tỷ lệ kịch bản ngoài vùng dày từ 364 cặp sai số kiểm định là phân tích độ nhạy, với AUC xếp hạng thăm dò 0,816 trên năm 2024. [Kết quả từng tỉnh](results/papi_forecast_provinces_2024.csv) · [Số liệu tổng hợp](results/papi_forecast_2024.json)

### Phân tích gán vùng quan sát và đối chứng học phần

Toàn bộ chạy **local, không cần dịch vụ ngoài**. Ba bước:

```powershell
python scripts/analysis/predict_sweep.py        # 1) chốt cấu hình (train-only, KHÔNG nhìn 2024)
python scripts/analysis/predict_demo.py         # 2) đặt điểm đã quan sát lên lưới STING
python scripts/supervised/predict_supervised.py   # 3) model ML có giám sát (scikit-learn)
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
   Chỉ hàng đủ hai điểm PAPI được gán nhãn (61/63 tỉnh năm 2024; tỉnh thiếu bị loại,
   không nội suy). `-1` nghĩa là điểm nằm ngoài ô dày đã học, không phải cụm thường.
   Kết quả: `results/predict_all_years.csv`,
   `results/predict_summary.md` (gồm độ nhạy theo `min_count` và chuyển cụm tách riêng
   "chuyển thật" vs "chuyển sang/từ nhiễu"), `results/figs/predict_2024.png`.
3. **`predict_supervised.py`** — model có giám sát, lưu local bằng joblib:
   - **Đối chứng đơn chỉ tiêu:** dự báo *6.1 Y tế công lập* năm t+1 từ 8 sub-dimension năm t.
     Chọn model bằng metric `r2 (expanding origin 2017–2022)` train-only (warm-up 2011–2016):
     hiện Ridge được chọn với R²=0.265; MAE holdout 2023→2024 là 0.0640 so với
     carry-forward 0.0683 (giảm 6.3%). Random Forest có R² CV thấp hơn (0.197) và
     MAE holdout thấp hơn (0.0616); việc chọn model không dựa vào holdout. Đây vẫn
     chỉ là một năm holdout.
     Lưu `models/sup_ridge.joblib`, `models/sup_rf.joblib` (hồi quy) và
     `models/sup_classifier.joblib` (classifier được CV chọn); kết quả
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

Nạp mô hình để gán điểm lên lưới hoặc dự báo giá trị năm sau:

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
print(model.predict(z))               # -> nhãn ô lưới hoặc -1 nếu ở ngoài vùng dày

import joblib
ridge = joblib.load("models/sup_ridge.joblib")
print(ridge.predict(np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])))  # dự báo 6.1 năm sau
```

**Lưu ý thang đo:** `scripts/data/check_data.py` đánh dấu cột có bước nhảy mean năm >0.25;
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

Nhóm sử dụng trợ lý AI lập trình cho một số phần của đồ án: khung code ban đầu cho một số script dữ liệu/trực quan, gỡ lỗi, và dry-run đo thời gian chuẩn bị demo (`reports/on-tap/rehearsal_log.md` mục A ghi rõ phần dry-run do AI/từng cá nhân tự chạy). Hai thành viên chịu trách nhiệm rà soát nguồn, chạy lại kết quả và giải thích phương pháp, lựa chọn cấu hình cùng giới hạn của đồ án. Nhóm ghi nhận việc sử dụng công cụ hỗ trợ và chịu trách nhiệm về nội dung bài nộp.

## Giấy phép

- **Mã nguồn** (`src/`, `scripts/`, `notebooks/`, `tests/`): **MIT** — xem [`LICENSE`](LICENSE).
- **Dữ liệu** (`data/raw/*/`): giữ giấy phép gốc từng nguồn — xem `PROVENANCE.md` trong từng thư mục (PAPI: dữ liệu công khai CECODES/VFF-CRT/RTA/UNDP; Mendeley: CC BY 4.0, DOI 10.17632/wbk42j9wc8.1; GeoJSON: CC-BY-SA 4.0) — không thuộc MIT.
- **Tác giả:** Nguyễn Tiến Sơn (MSSV 24110054) · Trần Thị Ngọc Quyên (MSSV 24110051) — đồ án môn Học máy, Topic 6.
