# Danh sách kiểm tra trước khi nộp bài cuối kỳ — Topic 6 · STING × PAPI

_Cập nhật ngày 27/11/2026 · Nhóm 15._

## Hồ sơ của đồ án

- [x] **Báo cáo DOCX tiếng Việt** — `reports/Nhom15_BaoCao_STING_PAPI.docx` (49 trang khi render bằng LibreOffice, bảy chương, có Mục 5.8 **Thống kê mô tả và gợi ý rà soát 63 tỉnh**, mục lục và danh mục 13 hình, 15 bảng có số trang đã cập nhật), đồng bộ trong [gói thống nhất](../submissions/Nhom15_STING_PAPI.zip).
- [x] **Notebook phân tích thống nhất** — `notebooks/Nhom15_STING_PAPI.ipynb` chạy sạch 18 code cell từ gói giải nén (gộp demo 3×3 giữa kỳ, 240 điểm giả lập, phân cụm PAPI, thống kê bàn giao 63 tỉnh, dự báo, kiểm chứng ngoại lai & phụ lục học phần). [Kết quả chạy lại](../submissions/verification.json)
- [x] **Notebook tiền xử lý PAPI** — `notebooks/Nhom15_TienXuLy_PAPI.ipynb` chạy sạch 9 code cell trực tiếp từ 14 workbook PAPI gốc qua `PREPROCESSING_PIPELINE` 6 bước.
- [x] **Slide trình bày thống nhất (12 trang)** — `slides/Nhom15_STING_PAPI.pptx` (bảng có thể chỉnh sửa, hai biểu đồ với workbook dữ liệu nhúng; slide 6–7 quan sát 2024, thống kê 63 tỉnh và dịch chuyển; slide 12 kết luận và cảm ơn; sinh bằng `python scripts/deliverables/build_slides.py`).
- [x] **Dataset thật ≥ 500 × ≥ 10** — panel 882×41 (`data/processed/papi_panel_63_2011_2024.csv`); check: `python scripts/data/check_data.py` → PASS.
- [x] **Gỡ bỏ phân mảnh & thư mục `study/`** — bỏ các bản tách giữa kỳ/cuối kỳ rời, thư mục `study/` và `notebooks/exploratory/` để giữ 1 cấu trúc đồ án hoàn thiện duy nhất.

## Đối chiếu môn học & Thống kê khách hàng

- [x] **Thống kê bàn giao cho khách hàng (63 tỉnh)** — `scripts/analysis/stakeholder_summary.py --with-excel`, tạo `results/stakeholder_province_summary_2024.csv`, `results/stakeholder_summary.md`, `results/figs/stakeholder_quadrants_2024.png`, sheet **Thống kê khách hàng 2024** trong `results/KetQua_STING_PAPI.xlsx` và tab **Thống kê khách hàng** trên `app.py`.
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

## Rà soát hình thức và nội dung

- Bìa theo mẫu giảng viên cung cấp ngày 27/11/2026; giữ thông tin hai thành viên và đề tài. Các bảng Word dùng nền trắng, chữ và đường viền đen; mục lục và danh mục có 82 mục điều hướng.
- Báo cáo dùng cách diễn đạt học thuật, giải thích CV, MAE, RMSE, AUC và OFAT; giữ khai báo công cụ AI và phân biệt kết quả mô tả với kết luận đã được kiểm chứng.
- Bộ slide gồm 12 trang với ghi chú, số liệu có nguồn và giới hạn đi cùng kết quả; trang cuối gộp kết luận và hỏi đáp. Kịch bản thuyết trình và tài liệu ôn tập dùng cùng số thứ tự slide.
- Người nhận có [hướng dẫn sử dụng dashboard](customer_guide.md) và [giải thích bảng bàn giao 2024](ban-giao-khach-hang-2024.md), cùng nằm trong ZIP. Nhóm mô tả và chỉ số thăm dò không được trình bày như xếp hạng chất lượng chính thức.
- Word, PowerPoint, notebook và các bản sao trong gói được đối chiếu từng byte. `results/MANIFEST.json` trong ZIP liệt kê tệp, vai trò và mã kiểm tra; [verification.json](../submissions/verification.json) gắn kết quả chạy lại với SHA-256 của đúng ZIP.
- Bộ kiểm thử, Ruff, kiểm tra dữ liệu và thực thi lại hai notebook bằng kernel Jupyter tiêu chuẩn trên Ubuntu, Windows, macOS được chạy trong [GitHub Actions](https://github.com/JasonTM17/Grid_Based_Sociology/actions/workflows/ci.yml).

## Các bước nhóm cần thực hiện trước khi nộp bài

- [x] Báo cáo xong giữa kỳ + ghi nhận phản hồi thầy tại `reports/on-tap/midterm_feedback.md` (*"em phân cụm vậy nhưng cuối cùng thống kê với khách hàng cái gì á"*) → đã bổ sung đầy đủ trước khi chốt bản thống nhất.
- [x] Điền họ tên và MSSV ở trang Nhóm thực hiện (Nguyễn Tiến Sơn — 24110054 · Trần Thị Ngọc Quyên — 24110051).
- [ ] Luyện trình bày cuối kỳ ≤ 15' + Q&A 5' (`reports/on-tap/rehearsal_log.md`)
- [ ] Tập hỏi đáp bảo vệ cuối kỳ (`reports/on-tap/mock_defense_log.md`)
- [ ] Nộp gói `submissions/Nhom15_STING_PAPI.zip` lên cổng LMS theo thông báo giảng viên

## Tạo & kiểm chứng gói thống nhất

```powershell
python scripts/deliverables/update_report_fields.py
python scripts/deliverables/build_submission_packages.py
python scripts/deliverables/build_submission_packages.py --verify
```

Đầu ra tại `submissions/`:

- `Nhom15_STING_PAPI.zip` (và thư mục giải nén sẵn `Nhom15_STING_PAPI/`) đặt báo cáo `Nhom15_BaoCao_STING_PAPI.docx`, slide `Nhom15_STING_PAPI.pptx`, bộ đôi notebook `Nhom15_STING_PAPI.ipynb` & `Nhom15_TienXuLy_PAPI.ipynb`, `HUONG_DAN.txt`, `requirements.txt` cùng `src/`, `data/`, `scripts/`, `models/`, `results/`, `reports/` ở cấp đầu.
- `SHA256SUMS.txt`: hash gói ZIP; trong thư mục giải nén có `results/MANIFEST.json` ghi hash/vai trò từng file.
- `verification.json` ghi kết quả chạy lại cả hai notebook từ gói giải nén.

Verifier xóa output cũ ở bản sao notebook, dùng kernel mới, kiểm tra đếm lần chạy
và chặn đọc kho mã gốc. Cách mở tệp và chạy lại được ghi trong [hướng dẫn nộp bài](../submissions/HUONG-DAN.txt).
Kịch bản 12 slide: `reports/on-tap/presentation_script.md`.

## Git tag

- [x] `v1.0` — trạng thái hoàn thiện về mặt kỹ thuật của repo tại 2026-11-04.
