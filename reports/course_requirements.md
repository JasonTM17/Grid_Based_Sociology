# Yêu cầu môn học và hồ sơ nộp bài

_Cập nhật ngày 27/11/2026 · Nhóm 15._

## Tiêu chí chấm và nội dung môn học

### Tiêu chí chấm giữa kỳ

| Hạng mục | Điểm |
|---|---|
| Tiền xử lý (preprocessing) | 1.5 |
| Học model (model learning) | 2 |
| Đánh giá (evaluation) | 2 |
| Báo cáo (report) | 2.5 |
| Q&A | 2 |

_Liên hệ đồ án thống nhất:_ phần cơ chế thuật toán giữa kỳ (định nghĩa, lưới 3×3,
tiền xử lý, kết quả STING trên PAPI, bất biến z-score trên 869
quan sát và đối chứng lịch sử trên 808 quan sát, với silhouette cùng mẫu 631 điểm) đã được hợp nhất trực tiếp vào `slides/Nhom15_STING_PAPI.pptx` (slide 2–5)
và `notebooks/Nhom15_STING_PAPI.ipynb` (Phần 1–3). Kiểm tra tiền xử lý tham chiếu bảng
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

Bộ trình bày gồm 12 slide, kết hợp cơ chế STING, dữ liệu và tiền xử lý, kết quả thực nghiệm, thống kê 63 tỉnh, phần bàn giao và giới hạn. Slide cuối gộp kết luận, cảm ơn và hỏi đáp.

### Bài thực hành tiền xử lý dữ liệu

1. **Cleaning** — theo thứ tự: **dedup trước** → imputation → consistency → **outlier removal cuối cùng**
2. **Integration** — merge, xử lý xung đột, cardinality một-nhiều / nhiều-nhiều, tránh data leakage
3. **Transformation** — scaling và biến đổi thang

Nguyên tắc: **với mỗi giai đoạn: Test → Decide** (có bằng chứng trước khi chốt).

_Áp dụng trong repo:_ `scripts/data/preprocessing_audit.py` ghi bảng Test | Result | Decision | Evidence vào `results/preprocessing_audit.{md,csv}`; quyết định “cứng” nằm trong `scripts/data/build_panel.py`, `predict_demo.py`, `predict_supervised.py`, v.v.

Trang 17 của bài giảng về tiền xử lý yêu cầu bài nhóm chạy pipeline tiền xử lý, in kết quả và ghi lại các bước đã chọn. Bài thực hành `notebooks/Nhom15_TienXuLy_PAPI.ipynb` dựng panel từ 14 workbook gốc, đối chiếu panel 882 × 41 và chạy chuẩn hóa bằng thống kê của tập 2011–2023. Tệp này nằm trực tiếp ở cấp đầu của gói nộp thống nhất [Nhom15_STING_PAPI.zip](../submissions/Nhom15_STING_PAPI.zip).

### Mẫu bìa báo cáo của giảng viên

Bìa dùng mẫu `Report-proj.pdf.docx` được cung cấp ngày 27/11/2026: khung đen một nét, ba dòng tên trường/khoa/bộ môn, logo, sinh viên, đề tài, tên môn và giảng viên hướng dẫn. Thông tin mẫu được thay bằng thông tin Nhóm 15; các vùng tô vàng được bỏ sau khi điền.

Thân báo cáo giữ bảy chương để trình bày phương pháp, dữ liệu, kết quả và giới hạn, kèm các phụ lục tái lập. [Ghi chú định dạng](report_format_notes.md) lưu thông số bìa và cách dựng lại tài liệu.

## Hồ sơ theo yêu cầu môn học

| Mốc | Yêu cầu đề | Tệp bàn giao | Trạng thái |
|---|---|---|---|
| Đồ án thống nhất (gộp Giữa kỳ + Cuối kỳ + Thống kê khách hàng) | Báo cáo DOCX tiếng Việt, Slide PPTX, Notebook thực thi sạch (Jupyter), Dataset ≥500×10, kiểm chứng & thống kê bàn giao 63 tỉnh | `reports/Nhom15_BaoCao_STING_PAPI.docx` + `slides/Nhom15_STING_PAPI.pptx` (12 slide) + `notebooks/Nhom15_STING_PAPI.ipynb` + `notebooks/Nhom15_TienXuLy_PAPI.ipynb` trong [gói thống nhất](../submissions/Nhom15_STING_PAPI.zip) | Hoàn thiện, đồng bộ 1-1 (`submissions/Nhom15_STING_PAPI/`). [Kết quả chạy lại](../submissions/verification.json) |

## Thông tin đã chốt và mục cần xác nhận

- [x] **Định dạng `.docx`** đã áp dụng theo file mẫu người dùng chọn (`reports/report_format_notes.md`), cấu trúc **7 chương** (có Chương 5.8 **Thống kê bàn giao cho khách hàng trên 63 tỉnh**).
- [x] **Số slide.** 12 slide thống nhất (`slides/Nhom15_STING_PAPI.pptx`), gồm cơ chế giữa kỳ (3×3, 240 điểm, z-score), quan sát 2024, **phần quan sát, thống kê 63 tỉnh và dịch chuyển**, dự báo bổ trợ, đối chứng ngoại lai và kết luận.
- [x] **Nhóm: 2 người** — Nguyễn Tiến Sơn (24110054), Trần Thị Ngọc Quyên (24110051).
- [x] **Phản hồi giữa kỳ đã xử lý** — đã báo cáo xong giữa kỳ, bổ sung thống kê bàn giao khách hàng (`scripts/analysis/stakeholder_summary.py`) và gộp hoàn chỉnh toàn đồ án.
- [x] **Trọng số cuối kỳ** — bài giảng nhập môn học máy, trang 10 ghi 8 điểm nhóm và 2 điểm vấn đáp cá nhân.
- [ ] **Hạn và cổng nộp cuối kỳ chính thức** — theo thông báo của giảng viên trên LMS.
- [ ] **Phân công vấn đáp cuối kỳ** — nhóm rà soát trước buổi vấn đáp bằng `reports/on-tap/qa_final.md`.

## Định dạng gói nộp thống nhất

Trong kho dự án, gói nộp duy nhất được sinh bằng
`python scripts/deliverables/build_submission_packages.py`
vào `submissions/Nhom15_STING_PAPI.zip` (kèm thư mục giải nén sẵn `submissions/Nhom15_STING_PAPI/`) và kiểm tra bằng `python scripts/deliverables/build_submission_packages.py --verify`.

- Thành phần trọng tâm: `reports/Nhom15_BaoCao_STING_PAPI.docx`, `slides/Nhom15_STING_PAPI.pptx`, `notebooks/Nhom15_STING_PAPI.ipynb` và `notebooks/Nhom15_TienXuLy_PAPI.ipynb`.
- Mã nguồn, dữ liệu, model và kết quả đi kèm: `src/`, `data/`, `scripts/`, `models/`, `results/`, `reports/`.

`submissions/Nhom15_STING_PAPI/HUONG_DAN.txt` chỉ cách chạy lại các notebook và phân tích. `submissions/Nhom15_STING_PAPI/results/MANIFEST.json` (bên trong gói ZIP) liệt kê tệp kèm theo và mã SHA-256. [Kịch bản thuyết trình 12 slide](on-tap/presentation_script.md)

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
