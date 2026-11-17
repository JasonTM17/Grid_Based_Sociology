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

_Liên hệ deliverable giữa kỳ:_ slide và notebook đã chạy trình bày định nghĩa,
demo lưới, tiền xử lý, kết quả STING trên PAPI và hai đối chứng phân cụm. Tham
chiếu bảng `results/preprocessing_audit.md` và `results/metrics.csv`.

### Cuối kỳ (rubric Day 1, trang 10 — đã xác minh bằng mắt trên PDF gốc)

Các **hạng mục** (tên category) đọc được từ text trích PDF bài giảng:

- Tiền xử lý (preprocessing)
- Học model (model learning)
- Đánh giá & thảo luận (evaluation & discussion)
- Quy ước code + cảnh báo (coding conventions + warnings)
- Báo cáo (report)
- Thi vấn đáp (oral test)

Trọng số (Group +8, Individual +2; render trang 10 của `data/raw/course/lecture-day1-ideas-of-machine-learning.pdf`): tiền xử lý **1.5**, học model **1**, đánh giá & thảo luận **2**, quy ước code + cảnh báo **1**, báo cáo **2.5** (nhóm, tổng 8); thi vấn đáp **2** (cá nhân). Chia theo Group/Individual nên phần Q&A mỗi thành viên phải tự trả lời được.

### Day 4 — tiền xử lý và bài thực hành nhóm

1. **Cleaning** — theo thứ tự: **dedup trước** → imputation → consistency → **outlier removal cuối cùng**
2. **Integration** — merge, xử lý xung đột, cardinality một-nhiều / nhiều-nhiều, tránh data leakage
3. **Transformation** — scaling và biến đổi thang

Nguyên tắc: **với mỗi giai đoạn: Test → Decide** (có bằng chứng trước khi chốt).

_Áp dụng trong repo:_ `scripts/preprocessing_audit.py` ghi bảng Test | Result | Decision | Evidence vào `results/preprocessing_audit.{md,csv}`; quyết định “cứng” nằm trong `scripts/build_panel.py`, `predict_demo.py`, `predict_supervised.py`, v.v.

Slide Day 4 trang 17 yêu cầu bài nhóm chạy pipeline tiền xử lý, in kết quả và ghi lại các bước đã chọn. Bài thực hành riêng `notebooks/Nhom15_Day4_TienXuLy_PAPI.ipynb` dựng panel từ 14 workbook, đối chiếu panel 882 × 41 và chạy chuẩn hóa bằng thống kê của tập 2011–2023. Giữ notebook trong thư mục `notebooks/` của dự án để chạy lại với các tệp dữ liệu đi kèm.

### Mẫu báo cáo GV (`Report-proj.docx`) — quan sát một lần, không có trong repo

Lead đã đọc **chỉ dạng text** file mẫu `Report-proj.docx` (sau đó file không còn trên máy local). Cấu trúc text quan sát (không khẳng định font/lề):

- Trường → Khoa CNTT → Bộ môn trí tuệ nhân tạo → sinh viên (placeholder) → đề tài → **Đồ án môn HỌC MAY** → GV: **ThS. Le Minh Tan** → Khóa 2023–2027
- **Lời cảm ơn**, **Mục lục**
- Nội dung gợi ý **3 chương:** Chương 1 Lý thuyết liên quan (mục/tiểu mục cấp 3) · Chương 2 Mô tả hệ thống · Chương 3 Kết luận

**Báo cáo hiện tại** giữ **7 chương** theo kế hoạch nhóm, kèm phần mở đầu và tài liệu tham khảo. Bìa và căn chỉnh theo file báo cáo tiến độ do người dùng gửi (`reports/report_format_notes.md`). Yêu cầu thu gọn còn ba chương vẫn chờ xác nhận từ GV (ghi `open-questions.md`).

_File mẫu không được commit vào repo (tài liệu bên thứ ba). Bản sao slide/mẫu có thể để local tại `data/raw/course/` — cũng không commit._

## Deliverable theo đề

| Mốc | Yêu cầu đề | Sản phẩm dự kiến | Trạng thái |
|---|---|---|---|
| Giữa kỳ | 15' trình bày + 5' Q&A; nộp slides (≤10 slide) + notebook (đã execute — Jupyter/Zeppelin) | `slides/submission.pptx` (10 slide) + `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb` (execute sạch) | Sẵn sàng kỹ thuật (smoke + test) — rehearsal: con người |
| Cuối kỳ | Thi vấn đáp trực tiếp, nộp DOCX + notebook, PPTX tùy chọn, dataset ≥500×10 | `reports/final_report.docx` và bản rời `submissions/02-cuoi-ky/Nhom15_CuoiKy_STING_PAPI.docx`, `notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb` và `slides/final.pptx` | Báo cáo đã kiểm tra từ bản xuất Word 34 trang. Còn lịch luyện vấn đáp của nhóm. |

## Quyết định cần chốt (hỏi GV — xem `open-questions.md`)

- [x] **Định dạng `.docx`** đã áp dụng theo file mẫu người dùng chọn (`reports/report_format_notes.md`). Đã khảo sát dàn ý ba chương trong tài liệu mẫu GV.
- [x] **Template slide:** chưa có → tự thiết kế, ≤10 slide (`slides/submission.pptx`); phụ lục cuối kỳ: `slides/final.pptx` (16 slide).
- [x] **Nhóm: 2 người** — Nguyễn Tiến Sơn (24110054), Trần Thị Ngọc Quyên (24110051).
- [ ] **Định dạng nộp (tên file/cấu trúc/zip/nơi nộp) và deadline chính thức** — chờ GV/LMS.
- [ ] **Người trình bày & Q&A** — rehearsal (con người).
- [x] **Trọng số rubric cuối kỳ** — đã xác minh Day 1 trang 10 (Group 8 + oral 2); xem mục rubric phía trên và `open-questions.md` câu 6.
- [ ] **Skeleton báo cáo 3 chương (mẫu GV) vs 7 chương (báo cáo hiện tại)** — chờ GV; mặc định giữ 7 chương.
- [x] **Ngày giữa kỳ: 24/11–01/12** (mặc định đã giữ) → freeze gói giữa kỳ 20/11.

## Định dạng nộp đề xuất (default đến khi GV chốt khác)

Trong kho dự án, hai gói được sinh bằng
`python scripts/build_submission_packages.py`
vào `submissions/` và kiểm tra bằng `python scripts/build_submission_packages.py --verify`.

- Giữa kỳ: `Nhom15_GiuaKy_STING_PAPI.zip`, trọng tâm
  `slides/submission.pptx` + `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb`.
- Cuối kỳ: `Nhom15_CuoiKy_STING_PAPI.zip`, trọng tâm
  `reports/final_report.docx` + `notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb`, thêm
  `slides/final.pptx` tùy chọn cho vấn đáp.

Cả hai giữ đủ `src/`, `scripts/`, `models/`, `results/`, `data/` và nguồn;
không đổi tên panel thành `data/panel.csv` vì notebook cần đường dẫn chuẩn.
Mỗi gói có `HUONG_DAN.txt`, `MANIFEST.json`; hash ZIP và receipt chạy lại ở
thư mục output. Kịch bản 15'+5': `reports/presentation-script-261116.md`.

## Liêm chính học thuật

- Trích dẫn: PAPI (CECODES/VFF-CRT/RTA/UNDP); Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1);
  GeoJSON (Open Development Vietnam, CC-BY-SA 4.0) — bằng chứng trong các `PROVENANCE.md`.
- Khai báo công cụ hỗ trợ theo quy định môn; mọi thành viên giải thích được phần mình đã làm.


## Đối chiếu Day 9 (2026-11-16)

PDF mới gồm 48 trang: phương pháp grid-based được liệt kê ở tr.8; đánh giá
unsupervised bằng goodness of fit/WCSS/elbow ở tr.25–31; HC/linkage/dendrogram
ở tr.32–47. Tr.48 ghi rõ bài tập **cá nhân** trên dữ liệu tổng hợp hai cột,
KMeans + HC + dendrogram. Không có yêu cầu mới trong PDF này buộc đồ án nhóm
Topic 6 đổi thuật toán hoặc bổ sung dataset thật. Quy mô PAPI 882×41 vẫn đủ
ngưỡng hiện có. Xem Q&A 39–45 trong `reports/qa_course_concepts.md`.

Bản nhóm là biến thể STING rút gọn (không distribution type / confidence
pruning top-down); cần trình bày đúng phạm vi. Nếu GV yêu cầu tái hiện đầy đủ
mọi chức năng bản gốc, đó là yêu cầu bổ sung cần chốt, không được suy từ test xanh.
