# Checklist nộp bài cuối kỳ — Topic 6 · STING × PAPI

_Cập nhật: 2026-11-12 · Owner: A + B · Mốc: M7 (nộp trước 2027-01-15 hoặc sớm nhất có thể)_

## Deliverable bắt buộc của môn

- [x] **Báo cáo (.docx tiếng Việt)** — `reports/final_report.docx` (7 chương + phụ lục + TLTK; hình và bảng nhúng đầy đủ — hiện 12 hình, 12 bảng đo bằng `python-docx`; bìa đã điền: Nguyễn Tiến Sơn — 24110054 · Trần Thị Ngọc Quyên — 24110051; định dạng tự biên soạn đã được chấp nhận không phụ thuộc template môn — xem `reports/report_format_notes.md`).
- [x] **Notebook cuối kỳ** — `notebooks/final_analysis.ipynb` (execute sạch, 5 output `image/png` nhúng; lệnh: `python -m nbconvert --to notebook --execute --inplace notebooks/final_analysis.ipynb`).
- [x] **Dataset thật ≥ 500 × ≥ 10** — panel 882×41 (`data/processed/papi_panel_63_2011_2024.csv`); check: `python scripts/check_data.py` → PASS.
- [x] **Notebook nộp bài (giữa kỳ)** — `notebooks/submission_demo.ipynb` (execute sạch, 0 lỗi; sinh bằng `python scripts/gen_submission_demo.py`).
- [x] **Slides nộp bài (giữa kỳ)** — `slides/submission.pptx` (10 slide, tiếng Việt, notes kèm từng slide; build bằng `python scripts/build_slides_10.py`). Deck phụ lục mở rộng cho cuối kỳ: `slides/final.pptx` (16 slide).

## Đối chiếu môn học (2026-11-12)

- [x] **Audit tiền xử lý Day 4** — `scripts/preprocessing_audit.py` + `results/preprocessing_audit.{md,csv}`; notebook cuối kỳ đọc CSV (`tests/test_submission_artifacts.py` gate).
- [x] **Classifier học phần (NB, KNN, SVM, cây, RF)** — `scripts/course_supervised_baselines.py` + `results/course_supervised_baselines.{csv,md}` + `results/figs/course_confusion_matrix.png` (pseudo-label STING; một holdout).
- [x] **Q&A theo khái niệm bài giảng** — `reports/qa_course_concepts.md`.

## Tái lập / chất lượng mã

- [x] Toàn bộ test xanh (`python -m pytest tests -q`)
- [x] Smoke demo (`python scripts/demo_smoke.py` → SAN SANG DEMO, toàn bộ mục PASS)
- [x] Đối chiếu chéo Mendeley: max |diff| = 0.0
- [x] Mọi số liệu trong báo cáo/slide truy được về `results/*.csv` (metrics.csv, per_year.csv, robustness.csv, predict_summary.md, supervised_summary.md)
- [x] PROVENANCE + SHA-256 cho 3 nguồn dữ liệu (`data/raw/*/PROVENANCE.md`)
- [x] Model lưu local `models/` (STING pkl + scaler JSON + joblib Ridge/RF)
- [x] Panel v1 khóa với hash (`reports/panel_lock.md`)

## Còn lại (cần CON NGƯỜI, không thể tự động hóa)

- [ ] Rehearsal live ≤ 15' + Q&A 5' ×2 buổi (`reports/rehearsal_log.md`)
- [ ] Trình bày giữa kỳ 24/11–01/12 + điền `reports/midterm_feedback.md`
- [ ] Mock defense cuối kỳ (`reports/mock_defense_log.md`)
- [x] Điền họ tên/MSSV lên bìa `final_report.docx` (Nguyễn Tiến Sơn — 24110054 · Trần Thị Ngọc Quyên — 24110051)
- [ ] Chốt định dạng nộp cuối cùng với GV nếu khác đề xuất (TASK P4 bước 6)
- [ ] Khai báo liêm chính học thuật theo quy định môn (nếu trường yêu cầu)

## Cách tạo gói nộp (default đến khi GV chốt khác)

```
Nhom15_HocMay_Topic6_STING_CuoiKy/
├── bao-cao.docx                 (copy từ reports/final_report.docx, đổi tên)
├── notebooks/final_analysis.ipynb
└── data/panel.csv               (nếu GV yêu cầu kèm dữ liệu)
```

## Git tag

- [x] `v1.0` — trạng thái hoàn thiện về mặt kỹ thuật của repo tại 2026-11-04.
