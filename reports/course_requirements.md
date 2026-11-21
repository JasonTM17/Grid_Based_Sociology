# Yêu cầu môn học và hồ sơ nộp bài

_Cập nhật ngày 21/11/2026 · Nhóm 15._

## Tiêu chí chấm và nội dung môn học

### Tiêu chí chấm giữa kỳ

| Hạng mục | Điểm |
|---|---|
| Tiền xử lý (preprocessing) | 1.5 |
| Học model (model learning) | 2 |
| Đánh giá (evaluation) | 2 |
| Báo cáo (report) | 2.5 |
| Q&A | 2 |

_Liên hệ deliverable giữa kỳ:_ slide và notebook đã chạy trình bày định nghĩa,
demo lưới, tiền xử lý, kết quả STING trên PAPI và hai đối chứng phân cụm.
Notebook giữa kỳ tính lại z-score, số ô dày, silhouette và độ nhạy trên 869
quan sát đủ hai chỉ tiêu PAPI 2011–2024. Kiểm tra tiền xử lý tham chiếu bảng
`results/preprocessing_audit.md`.

### Tiêu chí chấm cuối kỳ

Các **hạng mục** (tên category) đọc được từ text trích PDF bài giảng:

- Tiền xử lý (preprocessing)
- Học model (model learning)
- Đánh giá & thảo luận (evaluation & discussion)
- Quy ước code + cảnh báo (coding conventions + warnings)
- Báo cáo (report)
- Thi vấn đáp (oral test)

Trang 10 của tài liệu `data/raw/course/bai-giang-nhap-mon-hoc-may.pdf` ghi điểm tiền xử lý **1.5**, học model **1**, đánh giá & thảo luận **2**, quy ước code + cảnh báo **1**, báo cáo **2.5** (nhóm, tổng 8); thi vấn đáp **2** (cá nhân). Chia theo Group/Individual nên phần Q&A mỗi thành viên phải tự trả lời được.

Bộ giữa kỳ gồm 10 slide là lựa chọn trình bày của nhóm để phù hợp thời lượng; PDF được cung cấp không ghi giới hạn số slide.

### Bài thực hành tiền xử lý dữ liệu

1. **Cleaning** — theo thứ tự: **dedup trước** → imputation → consistency → **outlier removal cuối cùng**
2. **Integration** — merge, xử lý xung đột, cardinality một-nhiều / nhiều-nhiều, tránh data leakage
3. **Transformation** — scaling và biến đổi thang

Nguyên tắc: **với mỗi giai đoạn: Test → Decide** (có bằng chứng trước khi chốt).

_Áp dụng trong repo:_ `scripts/data/preprocessing_audit.py` ghi bảng Test | Result | Decision | Evidence vào `results/preprocessing_audit.{md,csv}`; quyết định “cứng” nằm trong `scripts/data/build_panel.py`, `predict_demo.py`, `predict_supervised.py`, v.v.

Trang 17 của bài giảng về tiền xử lý yêu cầu bài nhóm chạy pipeline tiền xử lý, in kết quả và ghi lại các bước đã chọn. Bài thực hành riêng `notebooks/Nhom15_TienXuLy_PAPI.ipynb` dựng panel từ 14 workbook, đối chiếu panel 882 × 41 và chạy chuẩn hóa bằng thống kê của tập 2011–2023. Bản chạy độc lập cùng dữ liệu gốc nằm trong [bộ tiền xử lý PAPI](../submissions/03-tien-xu-ly-papi/).

### Mẫu báo cáo GV (`Report-proj.docx`) — quan sát một lần, không có trong repo

Lead đã đọc **chỉ dạng text** file mẫu `Report-proj.docx` (sau đó file không còn trên máy local). Cấu trúc text quan sát (không khẳng định font/lề):

- Trường → Khoa CNTT → Bộ môn trí tuệ nhân tạo → sinh viên (placeholder) → đề tài → **Đồ án môn HỌC MAY** → GV: **ThS. Le Minh Tan** → Khóa 2023–2027
- **Lời cảm ơn**, **Mục lục**
- Nội dung gợi ý **3 chương:** Chương 1 Lý thuyết liên quan (mục/tiểu mục cấp 3) · Chương 2 Mô tả hệ thống · Chương 3 Kết luận

**Báo cáo hiện tại** có **7 chương**, kèm phần mở đầu và tài liệu tham khảo. Bìa và thể thức theo mẫu nhóm chọn ngày 18/11. Mẫu giảng viên cung cấp gợi ý dàn ý ba chương. [Ghi chú định dạng báo cáo](report_format_notes.md)

_File mẫu không được commit vào repo (tài liệu bên thứ ba). Bản sao slide/mẫu có thể để local tại `data/raw/course/` — cũng không commit._

## Deliverable theo đề

| Mốc | Yêu cầu đề | Sản phẩm dự kiến | Trạng thái |
|---|---|---|---|
| Giữa kỳ | 15' trình bày + 5' Q&A; nộp slides (PPTX) + notebook (đã execute — Jupyter/Zeppelin) | `slides/submission.pptx` (10 slide) + `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb` (execute sạch) | Sẵn sàng kỹ thuật (smoke + test) — rehearsal: con người |
| Cuối kỳ | Thi vấn đáp trực tiếp, nộp DOCX + notebook, PPTX tùy chọn, dataset ≥500×10 | Báo cáo Word, notebook Jupyter và slide vấn đáp trong [gói cuối kỳ](../submissions/Nhom15_CuoiKy_STING_PAPI.zip) | Có bản rời và gói tự chứa. [Kết quả chạy lại](../submissions/verification.json) |

## Thông tin đã chốt và mục cần xác nhận

- [x] **Định dạng `.docx`** đã áp dụng theo file mẫu người dùng chọn (`reports/report_format_notes.md`). Đã khảo sát dàn ý ba chương trong tài liệu mẫu GV.
- [x] **Template slide:** nhóm tự thiết kế và chọn 10 slide (`slides/submission.pptx`); phụ lục cuối kỳ: `slides/final.pptx` (16 slide).
- [x] **Nhóm: 2 người** — Nguyễn Tiến Sơn (24110054), Trần Thị Ngọc Quyên (24110051).
- [x] **Tệp giữa kỳ** — slide PowerPoint và notebook Jupyter theo yêu cầu giảng viên.
- [x] **Trọng số cuối kỳ** — bài giảng nhập môn học máy, trang 10 ghi 8 điểm nhóm và 2 điểm vấn đáp cá nhân.
- [ ] **Quy cách đặt tên, hạn và nơi nộp** — theo thông báo của giảng viên hoặc LMS.
- [ ] **Phân công trình bày và luyện vấn đáp** — nhóm xác nhận trước buổi báo cáo.
- [ ] **Bố cục báo cáo cuối kỳ** — nhóm dùng bố cục bảy chương và đối chiếu với yêu cầu chính thức của giảng viên.

## Định dạng nộp đề xuất (default đến khi GV chốt khác)

Trong kho dự án, hai gói được sinh bằng
`python scripts/deliverables/build_submission_packages.py`
vào `submissions/` và kiểm tra bằng `python scripts/deliverables/build_submission_packages.py --verify`.

- Giữa kỳ: `Nhom15_GiuaKy_STING_PAPI.zip`, trọng tâm
  `slides/submission.pptx` + `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb`.
- Cuối kỳ: `Nhom15_CuoiKy_STING_PAPI.zip`, trọng tâm
  `reports/final_report.docx` + `notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb`, thêm
  `slides/final.pptx` tùy chọn cho vấn đáp.

Mỗi gói giữ cấu trúc mã, kết quả và dữ liệu mà notebook sử dụng.
`HUONG_DAN.txt` chỉ cách chạy lại. `tai_lieu_kem/MANIFEST.json` liệt kê tệp
kèm theo và mã SHA-256. [Kịch bản giữa kỳ 15 phút và 5 phút hỏi đáp](on-tap/presentation_script.md)

## Liêm chính học thuật

- Trích dẫn: PAPI (CECODES/VFF-CRT/RTA/UNDP); Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1);
  GeoJSON (Open Development Vietnam, CC-BY-SA 4.0) — bằng chứng trong các `PROVENANCE.md`.
- Khai báo công cụ hỗ trợ theo quy định môn; mọi thành viên giải thích được phần mình đã làm.


## Nội dung tham khảo về phân cụm

Trong bài giảng về phân cụm, phương pháp grid-based được liệt kê ở tr.8; đánh giá
unsupervised bằng goodness of fit/WCSS/elbow ở tr.25–31; HC/linkage/dendrogram
ở tr.32–47. Tr.48 ghi rõ bài tập **cá nhân** trên dữ liệu tổng hợp hai cột,
KMeans + HC + dendrogram. Không có yêu cầu mới trong PDF này buộc đồ án nhóm
Topic 6 đổi thuật toán hoặc bổ sung dataset thật. Quy mô PAPI 882×41 vẫn đủ
ngưỡng hiện có. Xem Q&A 39–45 trong `reports/on-tap/qa_course_concepts.md`.

Quy trình chính gom các ô dày liên thông ở mức lưới được chọn. Notebook minh
họa thêm `query_top_down`, phép truy vấn theo mô hình phân phối chuẩn từng
chiều. Hai thao tác trả về kết quả khác nhau. Phân cụm trả về nhãn điểm,
còn truy vấn trả về thống kê của các ô nằm trọn trong vùng yêu cầu.
