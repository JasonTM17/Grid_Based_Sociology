# Yêu cầu môn học & quyết định nộp bài (checklist)

_Cập nhật: 2026-11-12 · Chủ sở hữu: nhóm · Hạn chốt logistics: xem `open-questions.md`_

## Rubric & nội dung đã dạy (trích từ bài giảng — không tự bịa trọng số)

### Giữa kỳ (rubric Day 1 — trọng số đọc được từ text bài giảng)

| Hạng mục | Điểm |
|---|---|
| Tiền xử lý (preprocessing) | 1.5 |
| Học model (model learning) | 2 |
| Đánh giá (evaluation) | 2 |
| Báo cáo (report) | 2.5 |
| Q&A | 2 |

_Liên hệ deliverable giữa kỳ:_ slides ≤10 + notebook execute; tiền xử lý/đánh giá có thể trỏ `results/preprocessing_audit.md`, classifier & confusion: `results/course_supervised_baselines.{md,csv}`, `results/figs/course_confusion_matrix.png`.

### Cuối kỳ (rubric Day 1, trang 10 — đã xác minh bằng mắt trên PDF gốc)

Các **hạng mục** (tên category) đọc được từ text trích PDF bài giảng:

- Tiền xử lý (preprocessing)
- Học model (model learning)
- Đánh giá & thảo luận (evaluation & discussion)
- Quy ước code + cảnh báo (coding conventions + warnings)
- Báo cáo (report)
- Thi vấn đáp (oral test)

Trọng số (Group +8, Individual +2; render trang 10 của `data/raw/course/lecture-day1-ideas-of-machine-learning.pdf`): tiền xử lý **1.5**, học model **1**, đánh giá & thảo luận **2**, quy ước code + cảnh báo **1**, báo cáo **2.5** (nhóm, tổng 8); thi vấn đáp **2** (cá nhân). Chia theo Group/Individual nên phần Q&A mỗi thành viên phải tự trả lời được.

### Day 4 — thứ tự tiền xử lý (bắt buộc đối chiếu khi trình bày)

1. **Cleaning** — theo thứ tự: **dedup trước** → imputation → consistency → **outlier removal cuối cùng**
2. **Integration** — merge, xử lý xung đột, cardinality một-nhiều / nhiều-nhiều, tránh data leakage
3. **Transformation** — scaling và biến đổi thang

Nguyên tắc: **với mỗi giai đoạn: Test → Decide** (có bằng chứng trước khi chốt).

_Áp dụng trong repo:_ `scripts/preprocessing_audit.py` ghi bảng Test | Result | Decision | Evidence vào `results/preprocessing_audit.{md,csv}`; quyết định “cứng” nằm trong `scripts/build_panel.py`, `predict_demo.py`, `predict_supervised.py`, v.v.

### Mẫu báo cáo GV (`Report-proj.docx`) — quan sát một lần, không có trong repo

Lead đã đọc **chỉ dạng text** file mẫu `Report-proj.docx` (sau đó file không còn trên máy local). Cấu trúc text quan sát (không khẳng định font/lề):

- Trường → Khoa CNTT → Bộ môn trí tuệ nhân tạo → sinh viên (placeholder) → đề tài → **Đồ án môn HỌC MAY** → GV: **ThS. Le Minh Tan** → Khóa 2023–2027
- **Lời cảm ơn**, **Mục lục**
- Nội dung gợi ý **3 chương:** Chương 1 Lý thuyết liên quan (mục/tiểu mục cấp 3) · Chương 2 Mô tả hệ thống · Chương 3 Kết luận

**Khác biệt với báo cáo hiện tại:** `reports/final_report.docx` giữ **7 chương** theo kế hoạch nhóm + front matter (TÓM TẮT, danh mục, TLTK) và **trang bìa / Lời cảm ơn** lấy cảm hứng từ mẫu GV (`reports/report_format_notes.md`). Câu hỏi **có bắt buộc thu gọn còn 3 chương như skeleton mẫu không** — **mở**, chờ GV (ghi `open-questions.md`).

_File mẫu không được commit vào repo (tài liệu bên thứ ba). Bản sao slide/mẫu có thể để local tại `data/raw/course/` — cũng không commit._

## Deliverable theo đề

| Mốc | Yêu cầu đề | Sản phẩm dự kiến | Trạng thái |
|---|---|---|---|
| Giữa kỳ | 15' trình bày + 5' Q&A; nộp slides (≤10 slide) + notebook (đã execute — Jupyter/Zeppelin) | `slides/submission.pptx` (10 slide) + `notebooks/submission_demo.ipynb` (execute sạch) | Sẵn sàng kỹ thuật (smoke + test) — rehearsal: con người |
| Cuối kỳ | Thi vấn đáp offline; nộp báo cáo (.docx) + notebook; dataset ≥500×10 | `reports/final_report.docx` (7 mục) + `notebooks/final_analysis.ipynb` + panel 882×41 | Sẵn sàng kỹ thuật — mock defense + nộp: con người |

## Quyết định cần chốt (hỏi GV — xem `open-questions.md`)

- [x] **Template `.docx`:** môn chưa cung cấp template bắt buộc trong repo → tự soạn theo ghi chú định dạng (`reports/report_format_notes.md`); đã khảo sát skeleton 3 chương từ mẫu GV (text only).
- [x] **Template slide:** chưa có → tự thiết kế, ≤10 slide (`slides/submission.pptx`); phụ lục cuối kỳ: `slides/final.pptx` (16 slide).
- [x] **Nhóm: 2 người** — Nguyễn Tiến Sơn (24110054), Trần Thị Ngọc Quyên (24110051).
- [ ] **Định dạng nộp (tên file/cấu trúc/zip/nơi nộp) và deadline chính thức** — chờ GV/LMS.
- [ ] **Người trình bày & Q&A** — rehearsal (con người).
- [x] **Trọng số rubric cuối kỳ** — đã xác minh Day 1 trang 10 (Group 8 + oral 2); xem mục rubric phía trên và `open-questions.md` câu 6.
- [ ] **Skeleton báo cáo 3 chương (mẫu GV) vs 7 chương (báo cáo hiện tại)** — chờ GV; mặc định giữ 7 chương.
- [x] **Ngày giữa kỳ: 24/11–01/12** (mặc định đã giữ) → freeze gói giữa kỳ 20/11.

## Định dạng nộp đề xuất (default đến khi GV chốt khác)

```
Nhom<XX>_HocMay_Topic6_STING_GiuaKy/     (giữa kỳ)
├── slides/submission.pptx               (10 slide)
└── notebooks/submission_demo.ipynb      (đã execute sẵn output)

Nhom<XX>_HocMay_Topic6_STING_CuoiKy/     (cuối kỳ)
├── bao-cao.docx
├── notebooks/final_analysis.ipynb        (đã execute sẵn output)
└── data/panel.csv                        (nếu GV yêu cầu kèm dữ liệu)
```

## Liêm chính học thuật

- Trích dẫn: PAPI (CECODES/VFF-CRT/RTA/UNDP); Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1);
  GeoJSON (Open Development Vietnam, CC-BY-SA 4.0) — bằng chứng trong các `PROVENANCE.md`.
- Khai báo công cụ hỗ trợ theo quy định môn; mọi thành viên giải thích được phần mình đã làm.
