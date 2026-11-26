# Checklist nộp bài thống nhất cuối kỳ — Topic 6 · STING × PAPI

_Cập nhật ngày 26/11/2026 · Nhóm 15._

## Deliverable thống nhất của đồ án

- [x] **Báo cáo DOCX tiếng Việt** — `reports/Nhom15_BaoCao_STING_PAPI.docx` (bảy chương, có Mục 5.8 **Thống kê bàn giao cho khách hàng trên 63 tỉnh**, mục lục + 13 hình + 15 bảng cập nhật bằng Word COM), đồng bộ trong [gói thống nhất](../submissions/Nhom15_STING_PAPI.zip).
- [x] **Notebook phân tích thống nhất** — `notebooks/Nhom15_STING_PAPI.ipynb` chạy sạch 18 code cell từ gói giải nén (gộp demo 3×3 giữa kỳ, 240 điểm giả lập, phân cụm PAPI, thống kê bàn giao 63 tỉnh, dự báo, kiểm chứng ngoại lai & phụ lục học phần). [Kết quả chạy lại](../submissions/verification.json)
- [x] **Notebook tiền xử lý PAPI** — `notebooks/Nhom15_TienXuLy_PAPI.ipynb` chạy sạch 9 code cell trực tiếp từ 14 workbook PAPI gốc qua `PREPROCESSING_PIPELINE` 6 bước.
- [x] **Slide trình bày thống nhất (11 trang)** — `slides/Nhom15_STING_PAPI.pptx` (gồm Slide 6–7 thống kê bàn giao 63 tỉnh cho khách hàng và Slide 11 cảm ơn; sinh bằng `python scripts/deliverables/build_slides.py`).
- [x] **Dataset thật ≥ 500 × ≥ 10** — panel 882×41 (`data/processed/papi_panel_63_2011_2024.csv`); check: `python scripts/data/check_data.py` → PASS.
- [x] **Gỡ bỏ phân mảnh & thư mục `study/`** — bỏ các bản tách giữa kỳ/cuối kỳ rời, thư mục `study/` và `notebooks/exploratory/` để giữ 1 cấu trúc đồ án hoàn thiện duy nhất.

## Đối chiếu môn học & Thống kê khách hàng

- [x] **Thống kê bàn giao cho khách hàng (63 tỉnh)** — `scripts/analysis/stakeholder_summary.py --with-excel`, tạo `results/stakeholder_province_summary_2024.csv`, `results/stakeholder_summary.md`, `results/figs/stakeholder_quadrants_2024.png`, sheet thứ 24 trong `results/KetQua_STING_PAPI.xlsx` và tab **Thống kê khách hàng** trên `app.py`.
- [x] **Bộ tiền xử lý PAPI** — gói `submissions/Nhom15_STING_PAPI.zip` chứa cả `Nhom15_TienXuLy_PAPI.ipynb` ở cấp đầu cùng `src/preprocessing.py` và 14 workbook gốc; báo cáo Word dùng kết quả `results/preprocessing_audit.csv` và `results/preprocessing_sensitivity.csv`.
- [x] **Classifier học phần (NB, KNN, SVM, cây, RF)** — `scripts/supervised/course_supervised_baselines.py` + `results/course_supervised_baselines.{csv,md}` + `results/figs/course_confusion_matrix.png` (pseudo-label STING; một holdout).
- [x] **Baseline đánh giá nhãn (hoán vị / drift năm)** — `scripts/supervised/classifier_label_baselines.py` + `results/classifier_label_baselines.{csv,md}` (exploratory; không thay bảng primary).
- [x] **Q&A theo khái niệm bài giảng & phản biện GV** — `reports/on-tap/qa_course_concepts.md`, `qa_midterm.md`, `qa_final.md`.

## Tái lập / chất lượng mã

- [x] Bộ kiểm thử bao phủ thuật toán STING, thống kê khách hàng 63 tỉnh, UI dashboard 6 tab, notebook thống nhất và tính đồng bộ giữa tệp gốc và gói nộp (`python -m pytest tests -q`).
- [x] Smoke demo (`python scripts/deliverables/demo_smoke.py` → SAN SANG DEMO, toàn bộ mục PASS)
- [x] Từ ZIP giải nén, dựng lại panel và metadata thang đo trùng từng byte. Đối chiếu Mendeley cho 5.118 cặp giá trị có độ lệch bằng 0 trên 756 khóa tỉnh–năm.
- [x] Gói thống nhất có đủ mã ghép nguồn và CSV rác thải/nghèo GSO. Bảng ghép 882 × 59 trùng từng byte khi dựng lại.
- [x] Mọi số liệu trong báo cáo/slide truy được về `results/*.csv` và `results/stakeholder_*.{csv,md}`
- [x] PROVENANCE + SHA-256 cho các nguồn dữ liệu (`data/raw/*/PROVENANCE.md`)
- [x] Model lưu local `models/` (STING pkl + scaler JSON + joblib Ridge/RF)
- [x] Panel v1 khóa với hash (`reports/panel_lock.md`)

## Đã xong giữa kỳ & Còn lại cuối kỳ (CON NGƯỜI thực hiện)

- [x] Báo cáo xong giữa kỳ + ghi nhận phản hồi thầy tại `reports/on-tap/midterm_feedback.md` (*"em phân cụm vậy nhưng cuối cùng thống kê với khách hàng cái gì á"*) → đã bổ sung đầy đủ trước khi chốt bản thống nhất.
- [x] Điền họ tên và MSSV ở trang Nhóm thực hiện (Nguyễn Tiến Sơn — 24110054 · Trần Thị Ngọc Quyên — 24110051).
- [ ] Rehearsal vấn đáp cuối kỳ ≤ 15' + Q&A 5' (`reports/on-tap/rehearsal_log.md`)
- [ ] Mock defense cuối kỳ (`reports/on-tap/mock_defense_log.md`)
- [ ] Nộp gói `submissions/Nhom15_STING_PAPI.zip` lên cổng LMS theo thông báo giảng viên

## Tạo & kiểm chứng gói thống nhất

```powershell
python scripts/deliverables/update_report_fields.py
python scripts/deliverables/build_submission_packages.py
python scripts/deliverables/build_submission_packages.py --verify
```

Đầu ra tại `submissions/`:

- `Nhom15_STING_PAPI.zip` (và thư mục giải nén sẵn `Nhom15_STING_PAPI/`) đặt báo cáo `Nhom15_BaoCao_STING_PAPI.docx`, slide `Nhom15_STING_PAPI.pptx`, bộ đôi notebook `Nhom15_STING_PAPI.ipynb` & `Nhom15_TienXuLy_PAPI.ipynb`, `HUONG-DAN.txt`, `requirements.txt` cùng `src/`, `data/`, `scripts/`, `models/`, `results/`, `reports/` ở cấp đầu.
- `SHA256SUMS.txt`: hash gói ZIP; trong thư mục giải nén có `MANIFEST.json` ghi hash/vai trò từng file.
- `verification.json` ghi kết quả chạy lại cả hai notebook từ gói giải nén.

Verifier xóa output cũ ở bản sao notebook, dùng kernel mới, kiểm tra đếm lần chạy
và chặn đọc kho mã gốc. Cách mở tệp và chạy lại được ghi trong [hướng dẫn nộp bài](../submissions/HUONG-DAN.txt).
Kịch bản 11 slide: `reports/on-tap/presentation_script.md`.

## Git tag

- [x] `v1.0` — trạng thái hoàn thiện về mặt kỹ thuật của repo tại 2026-11-04.
