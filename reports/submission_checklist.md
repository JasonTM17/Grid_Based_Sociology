# Checklist nộp bài cuối kỳ — Topic 6 · STING × PAPI

_Cập nhật: 2026-11-04 · Owner: A + B · Mốc: M7 (nộp trước 2027-01-15 hoặc sớm nhất có thể)_

## Deliverable bắt buộc của môn

- [x] **Báo cáo (.docx tiếng Việt)** — `reports/final_report.docx` (7 chương + phụ lục + TLTK; 6 hình, 8 bảng; bìa đã điền: Nguyễn Tiến Sơn — 24110054 · Trần Thị Ngọc Quyên — 24110051; định dạng tự biên soạn đã được chấp nhận không phụ thuộc template môn — xem `reports/report_format_notes.md`).
- [x] **Notebook cuối kỳ** — `notebooks/final_analysis.ipynb` (execute sạch, 4 hình nhúng; lệnh: `python -m nbconvert --to notebook --execute --inplace notebooks/final_analysis.ipynb`).
- [x] **Dataset thật ≥ 500 × ≥ 10** — panel 882×41 (`data/processed/papi_panel_63_2011_2024.csv`); check: `python scripts/check_data.py` → PASS.
- [x] **Notebook giữa kỳ** — `notebooks/midterm_demo.ipynb` (execute ~18s, 0 lỗi).
- [x] **Slides giữa kỳ** — `slides/midterm.pptx` (15 trang, tiếng Việt, notes kèm từng trang).

## Tái lập / chất lượng mã

- [x] Toàn bộ test xanh (`python -m pytest tests -q`)
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
