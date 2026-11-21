# Checklist nộp bài cuối kỳ — Topic 6 · STING × PAPI

_Cập nhật ngày 21/11/2026 · Nhóm 15._

## Deliverable bắt buộc của môn

- [x] **Báo cáo DOCX tiếng Việt** — dùng bản Word trong [gói cuối kỳ](../submissions/Nhom15_CuoiKy_STING_PAPI.zip). Bìa theo mẫu ngày 18/11, có mục lục và danh mục hình, bảng.
- [x] **Notebook cuối kỳ** — `notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb` chạy từ gói giải nén theo `HUONG_DAN.txt` và tái lập 869/869 nhãn STING. [Kết quả chạy lại](../submissions/verification.json)
- [x] **Dataset thật ≥ 500 × ≥ 10** — panel 882×41 (`data/processed/papi_panel_63_2011_2024.csv`); check: `python scripts/data/check_data.py` → PASS.
- [x] **Notebook nộp bài (giữa kỳ)** — `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb` (execute sạch, 0 lỗi; sinh bằng `python scripts/notebooks/gen_submission_demo.py`).
- [x] **Slides nộp bài (giữa kỳ)** — `slides/submission.pptx` gồm 10 trang đầu kể cả bìa và một trang cảm ơn. Chạy `python scripts/deliverables/build_slides_10.py` để tạo lại slide và ghi chú. Slide cuối kỳ nằm ở `slides/final.pptx`.

## Đối chiếu môn học (2026-11-12)

- [x] **Bộ tiền xử lý PAPI** — hai ZIP đều có `Nhom15_TienXuLy_PAPI.ipynb` ở cấp đầu (kèm bộ chạy độc lập tại `submissions/03-tien-xu-ly-papi/`) để dựng lại bảng từ 14 tệp Excel gốc qua `PREPROCESSING_PIPELINE` 6 bước, kiểm tra `scale_audit`/miền/ngoại lai và thử nghiệm Cleaning/Transformation. Hai notebook đồ án và báo cáo Word dùng panel, `results/preprocessing_audit.csv` và `results/preprocessing_sensitivity.csv`.
- [x] **Classifier học phần (NB, KNN, SVM, cây, RF)** — `scripts/supervised/course_supervised_baselines.py` + `results/course_supervised_baselines.{csv,md}` + `results/figs/course_confusion_matrix.png` (pseudo-label STING; một holdout).
- [x] **Baseline đánh giá nhãn (hoán vị / drift năm)** — `scripts/supervised/classifier_label_baselines.py` + `results/classifier_label_baselines.{csv,md}` (exploratory; không thay bảng primary).
- [x] **Q&A theo khái niệm bài giảng** — `reports/on-tap/qa_course_concepts.md`.

## Tái lập / chất lượng mã

- [x] Bộ kiểm thử bao phủ các trường hợp biên của STING, notebook và tính đồng bộ giữa tệp gốc và gói nộp. Chạy `python -m pytest tests -q` để kiểm tra sau khi sửa mã.
- [x] Smoke demo (`python scripts/deliverables/demo_smoke.py` → SAN SANG DEMO, toàn bộ mục PASS)
- [x] Từ ZIP giải nén, dựng lại panel và metadata thang đo trùng từng byte. Đối chiếu Mendeley cho 5.118 cặp giá trị có độ lệch bằng 0 trên 756 khóa tỉnh–năm.
- [x] Gói cuối kỳ có đủ mã ghép nguồn và CSV rác thải GSO. Bảng ghép 882 × 59 trùng từng byte khi dựng lại. Bảng kiểm tiền xử lý chạy trên dữ liệu vừa tạo và cho đúng kết quả đã lưu.
- [x] Mọi số liệu trong báo cáo/slide truy được về `results/*.csv` (metrics.csv, per_year.csv, robustness.csv, predict_summary.md, supervised_summary.md)
- [x] PROVENANCE + SHA-256 cho 3 nguồn dữ liệu (`data/raw/*/PROVENANCE.md`)
- [x] Model lưu local `models/` (STING pkl + scaler JSON + joblib Ridge/RF)
- [x] Panel v1 khóa với hash (`reports/panel_lock.md`)

## Còn lại (cần CON NGƯỜI, không thể tự động hóa)

- [ ] Rehearsal live ≤ 15' + Q&A 5' ×2 buổi (`reports/on-tap/rehearsal_log.md`)
- [ ] Trình bày giữa kỳ 24/11–01/12 + điền `reports/on-tap/midterm_feedback.md`
- [ ] Mock defense cuối kỳ (`reports/on-tap/mock_defense_log.md`)
- [x] Điền họ tên và MSSV ở trang Nhóm thực hiện (Nguyễn Tiến Sơn — 24110054 · Trần Thị Ngọc Quyên — 24110051).
- [ ] Chốt định dạng nộp cuối cùng với GV nếu khác đề xuất (TASK P4 bước 6)
- [ ] Khai báo liêm chính học thuật theo quy định môn (nếu trường yêu cầu)

## Tạo gói tự chứa cho cả hai mốc

Không chỉ chép notebook và đổi tên panel: notebook còn cần `src/`, `scripts/`,
`models/`, `results/` và đúng đường dẫn `data/processed/`.

```powershell
python scripts/deliverables/update_report_fields.py
python scripts/deliverables/build_submission_packages.py
python scripts/deliverables/build_submission_packages.py --verify
```

Đầu ra tại `submissions/`:

- `Nhom15_GiuaKy_STING_PAPI.zip` đặt slide 11 trang, notebook giữa kỳ, notebook tiền xử lý, `HUONG_DAN.txt`, `requirements.txt` cùng các thư mục chuẩn `src/`, `data/`, `scripts/`, `models/`, `results/` ở cấp đầu.
- `Nhom15_CuoiKy_STING_PAPI.zip` đặt báo cáo, notebook cuối kỳ, notebook tiền xử lý, slide vấn đáp, `HUONG_DAN.txt`, `requirements.txt` cùng các thư mục chuẩn `src/`, `data/`, `scripts/`, `models/`, `results/`, `reports/` ở cấp đầu.
- Bộ dựng và bộ xác minh dùng chung danh mục tệp. Xem số lượng và vai trò của từng tệp trong `results/MANIFEST.json`.
- `SHA256SUMS.txt`: hash hai ZIP; mỗi ZIP có `MANIFEST.json` ghi hash/vai trò từng file.
- `verification.json` ghi kết quả chạy notebook tiền xử lý và notebook báo cáo trong mỗi gói giải nén.

Verifier xóa output cũ ở bản sao notebook, dùng kernel mới, kiểm tra đếm lần chạy
và chặn đọc kho mã gốc và Downloads. Gói nộp chứa 14 bảng tính PAPI gốc,
báo cáo PAPI 2024, ZIP dữ liệu đối chiếu Mendeley, metadata thang đo và hồ sơ nguồn.

Cấu trúc này là đề xuất; tên file/nơi nộp/deadline chính thức cần theo GV/LMS.
Cách mở tệp và chạy lại được ghi trong [hướng dẫn nộp bài](../submissions/HUONG-DAN.txt).
Kịch bản giữa kỳ 15 phút + Q&A 5 phút: `reports/on-tap/presentation_script.md`.

## Git tag

- [x] `v1.0` — trạng thái hoàn thiện về mặt kỹ thuật của repo tại 2026-11-04.
