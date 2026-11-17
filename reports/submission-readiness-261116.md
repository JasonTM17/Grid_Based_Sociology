# Kết quả kiểm tra bài nộp STING × PAPI — 16/11/2026

Đã kiểm tra và sửa cho **cả giữa kỳ lẫn cuối kỳ**. Dataset chính đủ; không
cần tải thêm dataset để đạt quy mô môn học. Hai gói đã chạy notebook sau khi
giải nén, trong kernel mới bị chặn đọc kho mã gốc/Downloads.

Bìa sao chép trực tiếp các đoạn tiêu đề và bảng thông tin từ file mẫu. Đã
kiểm tra chữ đen trên bản xuất Word và đối chiếu cả 33 trang sau bìa. Bản rời là
`reports/final_report.docx`. Chấp nhận dàn ý bảy chương, tên/nơi nộp
và hạn nộp vẫn theo GV/LMS.

## Hai gói để dùng

| Mốc | File | Kích thước | Sản phẩm chính |
|---|---|---:|---|
| Giữa kỳ | `submissions/Nhom15_GiuaKy_STING_PAPI.zip` | 10.02 MB | `slides/submission.pptx` (10 slide), `notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb` |
| Cuối kỳ | `submissions/Nhom15_CuoiKy_STING_PAPI.zip` | 18.92 MB | Bản Word đã căn chỉnh ở `reports/final_report.docx`, `notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb` và `slides/final.pptx` tùy chọn (16 slide) |

ZIP giữa kỳ có 124 file, cuối kỳ 145 file (chưa tính manifest tự mô tả).
Trong mỗi ZIP, `HUONG_DAN.txt` ghi cách chạy và giới hạn;
`MANIFEST.json` ghi đường dẫn, vai trò, bytes và SHA-256 từng file.
`submissions/SHA256SUMS.txt` ghi hash hai ZIP;
`verification.json` ghi kết quả chạy lại tương ứng đúng hash ZIP.

Giải nén toàn bộ, giữ nguyên cấu trúc. Không tách notebook ra khỏi dữ liệu/mã.

```powershell
python -m pip install -r requirements.txt
python -m nbconvert --to notebook --execute --inplace notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb
# Trong gói cuối kỳ, thay tên bằng notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb
```

Môi trường đã chạy: Windows, Python 3.14.2. Chưa cài lại trong một môi trường
sạch hoàn toàn hay kiểm thử macOS/Linux; không dùng kết quả local để khẳng
định mọi môi trường đều chạy. Sau khi cài dependency, notebook dùng dữ liệu
local, không có bước tải dataset từ mạng.

## Dataset: đủ gì, thiếu gì, thừa gì

| Hạng mục | Kết quả và cách xử lý |
|---|---|
| Dữ liệu chính | PAPI 2011–2024: **882 dòng × 41 cột**, 63 tỉnh × 14 năm; 37 chỉ tiêu, 39 cột số nếu tính mã tỉnh/năm. Đủ yêu cầu quy mô, không dùng cột định danh để giả số feature. |
| Nguồn gốc | 14/14 workbook đúng kích thước và SHA-256 theo manifest. Đã parse lại tất cả workbook: panel tái tạo **khớp từng byte** với CSV hiện tại và bản khóa. |
| Đối chiếu độc lập | Mendeley: 756 dòng giao, 8 dimension; max chênh lệch bằng 0 trên các ô hợp lệ. Đây không phải kiểm chứng độc lập mọi sub-dimension. |
| Thiếu dữ liệu mô hình | 13/882 dòng thiếu ít nhất một trong hai feature đóng băng. Năm 2024 đủ dữ liệu ở **61/63 tỉnh**, không bịa điểm cho hai tỉnh còn thiếu. |
| Thiếu do lịch sử thu thập | d7/d8 chỉ có từ 2018; thiếu ở các năm trước là cấu trúc, không cần kiếm dataset khác để điền. |
| Thang đo | 23/37 chỉ tiêu bị cờ heuristic bước nhảy mean >0.25; **không có nghĩa tất cả 23 đã được chứng minh đổi thang**. Metadata tái tạo khớp từng byte; giữ cảnh báo cột đổi thang/ngừng thu thập. |
| Dữ liệu ngoài | PCI, dân số/GRDP, y tế, nghèo: kiểm chứng/bối cảnh; không lẫn thành feature chính. Bảng master 618,443 bytes đã kèm để tái tạo audit tiền xử lý. |
| Nghèo GSO | Chuỗi chính có bổ sung 2017–2019 từ Niên giám, không nội suy; ô TP.HCM 2016 thiếu phía nguồn giữ thiếu. Cửa sổ kiểm chứng hiện tại 2012–2024. |
| Phần không cần nộp nguyên kho | Kho tracked khoảng 279.70 MB: nhiều PDF Niên giám, báo cáo nguồn, WB/UNDP probes và dump tìm kiếm OD Mekong. Giữ làm hồ sơ trong repo; loại phần lớn khỏi ZIP. URL/nguồn vẫn trong provenance. |
| Tài liệu/công cụ nội bộ | Không đưa PDF bài giảng GV, agent config, plans, cache, `.git` vào gói. |

Panel SHA-256:
`87404305f36bd2609a63a213c41ac365960dd7909d0d122a0909fa9a5d0d9e27`.

Với đề tài Grid-based, STING là trọng tâm. Ridge/RF/classifier và dữ liệu ngoài
là phần bổ trợ; khi trình bày không để người nghe tưởng nhóm đổi sang đề tài
classification/regression hoặc coi pseudo-label là nhãn xã hội chuẩn.

`scikit-learn==1.8.0` đã có trong requirements và môi trường kiểm tra. Dùng
cho chuẩn hóa, baseline và metric; thuật toán Grid-based/STING nằm ở
`src/sting.py` do nhóm cài đặt. Không cần thêm thư viện hay dataset để đổi
trọng tâm bài. Có bảng so sánh và các kết quả yếu/âm cần giữ khi bảo vệ.

## Đối chiếu bài giảng thật

- Day 1, tr.8: giữa kỳ slide + notebook, cuối kỳ DOCX + notebook; tr.12:
  Topic6 Grid-based và quy mô dataset trên 500 dòng/10 cột. PAPI 882×41 vượt
  ngưỡng này. Giữ deck 10 slide theo cấu hình nộp bài đã có trong dự án.
- Day 9, tr.25–31: đánh giá unsupervised/goodness of fit, WCSS/elbow;
  tr.32–47: HC/linkage/dendrogram. Đã thêm Q&A39–45 để giải thích quan hệ
  với STING, noise và đánh giá cụm.
- Day 9, tr.48 ghi bài tập **cá nhân** KMeans + HC trên dữ liệu tổng hợp hai
  cột. Không tự biến nội dung đó thành yêu cầu thêm dataset/thay đề tài nhóm.
- STING của nhóm là **biến thể rút gọn**: không lưu distribution type và
  không confidence-based top-down pruning. Đây là khác biệt phương pháp cần
  công bố, đã sửa ở báo cáo và notebook cuối kỳ; không gọi là tái hiện đầy đủ
  mọi chức năng [STING gốc](https://www.vldb.org/conf/1997/P186.PDF).

Nguồn bài giảng local: `data/raw/course/lecture-day1-ideas-of-machine-learning.pdf`
và `lecture-day9-clustering.pdf`; không kèm trong ZIP.

## Những lỗi đã sửa

| Lỗi | Sửa và bằng chứng |
|---|---|
| Refit còn dùng nhãn lưới cũ | `fit→cluster→fit` trước đây vẫn cho predict. Nay hủy trạng thái cluster, yêu cầu cluster lại; hai regression cùng/khác số chiều đã thất bại trước sửa, qua sau sửa. Nhãn PAPI công bố không đổi. |
| Cận trên lưới nhỏ hơn cực đại train vì sai số float | Seed97 cho sai lệch4.44e-16, làm predict loại điểm train dù cluster nhận điểm đó. Giữ cận trên ít nhất bằng hi thật; regression2D thất bại trước sửa/qua sau sửa, companion3D vốn đã qua. 869nhãn PAPI và797cặp pseudo-label theo13origin giữ nguyên. |
| Smoke báo đã execute chỉ vì không có error | Dùng gate chung kiểm tra execution_count tuần tự, output, error/stderr và lệnh bỏ qua warning; có kiểm thử âm cho notebook rỗng/chưa chạy/chạy lệch thứ tự. |
| Gói nộp thiếu phụ thuộc | Thay cây gói chỉ có DOCX/notebook/panel đổi tên bằng allowlist đủ src/scripts/models/results/data; giữ tên chuẩn của panel. |
| Bảng master thiếu trong ZIP dù notebook chạy | Reviewer độc lập phát hiện. Gói cũ chạy `preprocessing_audit.py` lỗi FileNotFoundError; gói mới chạy audit và cho toàn bộ nội dung CSV giống bản công bố (chỉ chuẩn hóa LF/CRLF của hệ điều hành). |
| Báo cáo trộn STING gốc với bản nhóm | Sửa generator: giải thích cơ chế gốc/bản rút gọn, chi phí theo n/d/số mức/ô; bỏ suy luận sai O(n·L) mặc nhiên ≈ O(n log n) trong Q&A; sửa ngưỡng ARI kiểm thử từ ≥0.8 thành ≥0.9, bỏ coverage cố định cũ. |
| Notebook cuối chủ yếu đọc bảng và diễn giải cũ | Thêm chạy STING thật trên synthetic, refit và đối chiếu model/nhãn; tính lại MAE Ridge holdout; đường dẫn dựa vào root gói. |
| Nghèo dùng cửa sổ/kết luận cũ | Sửa 2012–2024 và nguồn bổ sung 2017–2019; không gọi Mann–Whitney p=0.269 là biên. Hai phép so noise-vs-cụm2 p=0.767/0.269 đều không đạt mức0.05. |
| Cờ heuristic bị gọi thành gãy thang chắc chắn | Sửa phần kết luận notebook, giữ đúng mức bằng chứng. |
| Deck cuối còn mô tả kế hoạch tương lai và khẳng định cũ | Sửa generator, khai báo biến thể STING; bỏ số28test cũ; tách O(Lnd) xây lưới khỏi chi phí query/cluster; thêm slide đúng DOCX+notebook và PPTX tùy chọn. Cả hai deck tái tạo và xem lại toàn bộ từ render. |

## Những kiểm tra đã thực sự chạy

| Kiểm tra | Kết quả / giới hạn |
|---|---|
| Baseline trước sửa | 162 passed; STING coverage99%. |
| Regression STING/notebook/nhãn | 47 passed; gồm 0 sai khác trên 869 nhãn PAPI. |
| Gate toàn bộ sau sửa chính | Pytest exit0, 184 case được thu thập; receipt PASS,257.396giây. Snapshot lịch sử trước bản vá master/cận float/slide, không diễn giải thành gate toàn bộ hiện tại. |
| Core sau sửa cận float |39test STING+frozen-artifact PASS,3.23giây;869nhãn PAPI không đổi. |
| Đối chiếu Grid-based độc lập |180cấu hình trên random2D/3D, dữ liệu lặp và PAPI: histogramdd + scipy connected components khớp số cụm/noise/phân hoạch, train predict=cluster. Chỉ xác minh biến thể đã công bố, không thay bằng chứng đầy đủ STING gốc. |
| Ảnh hưởng pseudo-label theo thời gian |797cặp tại origins2011–2023 khớp từng giá trị trước/sau duy nhất bản sửa cận; không cần huấn luyện/chọn lại mô hình. |
| Artifact/package sau sửa |28test artifact/final-notebook/package PASS,10.24giây, gồm audit từ gói giải nén và nội dung optionalfinalPPT. |
| Coverage | Gate toàn bộ lịch sử:193statements,2miss,99%; không đo lại sau cận float. |
| Lint | Toàn repo ruff PASS ở snapshot code mới, git diff --check PASS. |
| Notebook giữa kỳ | 10 ô code, gồm ví dụ lưới 3 × 3 như slide 5. Chạy độc lập sau giải nén và đối chiếu đủ 869 nhãn PAPI. |
| Notebook cuối kỳ | Chạy sạch trong ZIP:14ô code, thêm1ô guard; tổng notebook26cells; 0error/stderr. |
| Kiểm chứng số chính | Synthetic ARI0.950;869/869nhãn refit khớp; model lưu khớp; Ridge holdout59cặp MAE0.0640 vs carry0.0683. |
| Raw→panel/metadata | Cả hai tái tạo byte-identical, không ghi đè dữ liệu chính. |
| Source pointers Q&A |224tham chiếu file/dòng hợp lệ; gate chỉ kiểm tồn tại/phạm vi dòng, không tự chứng minh nội dung mọi câu. |
| Demo smoke mới |38/38PASS, có gate lần chạy notebook chặt hơn. |
| ZIP | Đã kiểm CRC/member/hash, không thiếu/thừa so manifest; chạy mới trong đường dẫn có khoảng trắng/Unicode; chặn đọc repo gốc và Downloads; xóa biến môi trường chèn root. |
| Rà soát độc lập | Snapshot trước: vòng1 phát hiện P2thiếu master; vòng2PASS, P2đóng. Vòng riêng cho delta cận float/slide:PASS trên16file, snapshot9fe13dbb…a3384f; không lỗi quan trọng mới. |
| Toàn vẹn bàn giao | CRC, danh sách file, hash manifest và hai biên bản chạy notebook khớp hai ZIP hiện tại. Bản Word trong ZIP cuối kỳ khớp bản rời đã định dạng. |
| Word nội dung | Đối chiếu nguyên văn 241 khối nội dung, 13 bảng và 12 hình. Có thêm bảng thông tin ở bìa và cập nhật 50 dòng mục lục/danh mục. |
| Word bố cục | Word xuất 34 trang. Đã đối chiếu bìa, kiểm từng trang, kiểm số trang 2–34 ở giữa chân trang và bìa không hiện số. |
| Slide | Bản giữa kỳ có 10 slide, dùng ví dụ lưới 3 × 3 thay trang nguồn và hỏi đáp. Đã xuất ảnh và xem các slide sửa. Deck cuối kỳ 16 slide nằm trong ZIP cuối kỳ. |
| Cảnh báo môi trường |Launcher Jupyter/Windows có thông báo event-loop/TCP trong log riêng; không nằm trong output notebook; không thêm lệnh giấu warning. |
| Git/CI/LMS |Thay đổi local, chưa commit/push, không tạo/khẳng định CI mới, chưa nộp LMS. |

Evidence máy đọc nằm ở
`plans/261116-1344-submission-readiness/reports/` và
`plans/261116-1458-grid-based-deliverables/reports/` cùng
`plans/261116-1540-report-template/reports/` và
`submissions/verification.json`.

## Giới hạn cần giải thích khi bảo vệ

PAPI frozen có một cụm lớn và hai cụm rất nhỏ, không phải ba nhóm xã hội
rõ ràng. Năm2024 là48tỉnh cụm lớn và13nhiễu trên61tỉnh đủ feature. Hai cụm
nhỏ không xuất hiện ở giai đoạn gần; không dùng “không chuyển cụm” để suy ra
ổn định xã hội. Giữ kết quả robustness yếu/âm, không tuning cho đẹp.

Silhouette/DB/CH loại noise nên các phương pháp có thể được chấm trên tập
điểm khác nhau; so sánh thô cần đọc kèm coverage/cỡ cụm. Classifier chỉ học
khớp pseudo-label STING. Một holdout2023→2024 không chứng minh tổng quát hóa.
Kiểm định ngoài gộp các tỉnh lặp qua năm có giới hạn giả định độc lập; không
dùng p-value để kết luận nhân quả hay cấu trúc xã hội chắc chắn.

## Việc con người còn cần làm trước khi nộp

1. Dùng bản chính `reports/final_report.docx`
   bên trong ZIP cuối kỳ. File rời tên cũ vẫn bị Word giữ khóa ghi.
2. Chốt tên file/nơi nộp/deadline và mẫu3hay7chương theo GV/LMS. Hiện giữ
   bảy chương; không tự xác nhận thầy đã chấp nhận.
3. Cả hai thành viên luyện trình bày15phút + Q&A5phút; ưu tiên lưới, mật độ,
   khác STING gốc, noise, chọn feature, giới hạn đánh giá. Xem Q&A39–45 và
   `reports/presentation-script-261116.md` (lịch nói dự kiến, chưa đo rehearsal).
4. Nếu GV yêu cầu đầy đủ STING gốc hoặc có yêu cầu miệng khác với tài liệu,
   chốt yêu cầu đó trước khi nộp; không lấy test xanh làm thay cho rubric.

## Câu hỏi chưa chốt

- Hạn/nơi/tên gói nộp chính thức của GV/LMS?
- Mẫu báo cáo bảy chương và phạm vi biến thể STING có được GV chấp nhận?
