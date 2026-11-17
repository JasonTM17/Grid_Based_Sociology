# Checklist nộp bài cuối kỳ — Topic 6 · STING × PAPI

_Cập nhật: 2026-11-12 · Owner: A + B · Mốc: M7 (nộp trước 2027-01-15 hoặc sớm nhất có thể)_

## Deliverable bắt buộc của môn

- [x] **Báo cáo DOCX tiếng Việt** — `reports/final_report.docx`, cùng nội dung với bản Word trong gói cuối kỳ. Đã kiểm tra 34 trang xuất từ Word, gồm bìa và mục lục theo phân trang mới, 12 hình và 13 bảng nội dung.
- [x] **Notebook cuối kỳ** — `notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb` (execute sạch, 5 output `image/png` nhúng; lệnh: `python -m nbconvert --to notebook --execute --inplace notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb`).
- [x] **Dataset thật ≥ 500 × ≥ 10** — panel 882×41 (`data/processed/papi_panel_63_2011_2024.csv`); check: `python scripts/check_data.py` → PASS.
- [x] **Notebook nộp bài (giữa kỳ)** — `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb` (execute sạch, 0 lỗi; sinh bằng `python scripts/gen_submission_demo.py`).
- [x] **Slides nộp bài (giữa kỳ)** — `slides/submission.pptx` (10 slide, tiếng Việt, notes kèm từng slide; build bằng `python scripts/build_slides_10.py`). Deck phụ lục mở rộng cho cuối kỳ: `slides/final.pptx` (16 slide).

## Đối chiếu môn học (2026-11-12)

- [x] **Bài nhóm Day 4** — `notebooks/Nhom15_Day4_TienXuLy_PAPI.ipynb` là bài riêng đã chạy từ workbook gốc và có bảng kết quả. Hai notebook đồ án dùng panel và bảng kiểm tra tiền xử lý đã lưu.
- [x] **Classifier học phần (NB, KNN, SVM, cây, RF)** — `scripts/course_supervised_baselines.py` + `results/course_supervised_baselines.{csv,md}` + `results/figs/course_confusion_matrix.png` (pseudo-label STING; một holdout).
- [x] **Baseline đánh giá nhãn (hoán vị / drift năm)** — `scripts/classifier_label_baselines.py` + `results/classifier_label_baselines.{csv,md}` (exploratory; không thay bảng primary).
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

## Tạo gói tự chứa cho cả hai mốc (kiểm tra 2026-11-16)

Không chỉ chép notebook và đổi tên panel: notebook còn cần `src/`, `scripts/`,
`models/`, `results/` và đúng đường dẫn `data/processed/`.

```powershell
python scripts/build_submission_packages.py
python scripts/build_submission_packages.py --verify
```

Đầu ra tại `submissions/`:

- `Nhom15_GiuaKy_STING_PAPI.zip`: slide 10 trang + notebook giữa kỳ + phụ thuộc.
- `Nhom15_CuoiKy_STING_PAPI.zip`: báo cáo Word + notebook cuối kỳ + PPTX tùy chọn + phụ thuộc.
- `SHA256SUMS.txt`: hash hai ZIP; mỗi ZIP có `MANIFEST.json` ghi hash/vai trò từng file.
- `verification.json`: chỉ sinh sau khi notebook trong cả hai gói giải nén chạy qua.

Verifier xóa output cũ ở bản sao notebook, dùng kernel mới, kiểm tra đếm lần chạy
và chặn đọc kho mã gốc/Downloads. Giữ 14 workbook PAPI, metadata thang đo và nguồn
trích dẫn. Không kèm agent config, PDF bài giảng, cache và các dump/probe tải nguồn.
PDF nguồn ngoài lớn vẫn ở repository, có URL trong provenance.

Cấu trúc này là đề xuất; tên file/nơi nộp/deadline chính thức cần theo GV/LMS.
Xem báo cáo kiểm tra mới: `reports/submission-readiness-261116.md`.
Kịch bản giữa kỳ 15 phút + Q&A 5 phút: `reports/presentation-script-261116.md`.

## Git tag

- [x] `v1.0` — trạng thái hoàn thiện về mặt kỹ thuật của repo tại 2026-11-04.
