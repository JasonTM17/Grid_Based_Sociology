# Kịch bản thuyết trình 15 slide STING và PAPI

Bộ slide chính là [`slides/Nhom15_STING_PAPI.pptx`](../../slides/Nhom15_STING_PAPI.pptx). Nội dung đi từ bài toán và cơ chế thuật toán đến kết quả PAPI, mở rộng hồi quy/đa chiều/suy luận bảng, hệ thống bàn giao 63 tỉnh và giới hạn ứng dụng. Bộ trình chiếu có **15 slide**, dành khoảng **15 phút trình bày và 5 phút hỏi đáp**. Bảng thời gian dưới đây là kế hoạch luyện tập, chưa phải thời gian đã đo. Nội dung trên màn hình giữ các kết quả và giới hạn cần thiết; ghi chú slide cung cấp chi tiết để trả lời phản biện, không cần đọc nguyên văn.

Mạch bài nói đi từ **phân cụm**, qua **dự báo & mở rộng học thuật**, đến **suy luận thống kê & hệ thống bàn giao**.
Slide 3–5 giải thích cách dựng lưới, tạo cụm và đối chứng. Slide 6–7 đọc số liệu
quan sát và tính thử một ô thật. Slide 8–12 trình bày dự báo 6.1, 17 cấu hình hồi quy + Conformal 90%, STING đa chiều (`QuantileSTING`/`CLIQUE`) và suy luận bảng CR1/TWFE/FDR/Moran's I. Slide 13–15 tổng hợp 63 tỉnh, sản phẩm tích hợp và kết luận.

Các kết quả chính cần phân biệt xuyên suốt bài nói:

| Phạm vi | Mẫu số | Ý nghĩa |
|---|---:|---|
| Panel gốc | 882 tỉnh–năm | 63 tỉnh × 14 năm, giữ cả dòng thiếu |
| Mẫu đủ hai đặc trưng toàn kỳ | 869 | Thí nghiệm mô tả 2011–2024 và kiểm tra bất biến z-score |
| Lưới tham chiếu | 808 | Fit trên các năm 2011–2023 |
| Quan sát đủ hai đặc trưng năm 2024 | 61 | Gán điểm đã quan sát lên lưới cố định, 48 trong vùng dày và 13 ô thưa |
| Mẫu giao 2023–2024 / đánh giá dự báo | 59 | Có dữ liệu đối chiếu, gồm 11 tỉnh ngoài vùng dày |
| Bảng mô tả bàn giao | 63 | Bao gồm cả 2 tỉnh thiếu dữ liệu, không gán thiếu thành nhiễu |

## Lời mở đầu

> Thưa thầy và các bạn, nhóm 15 áp dụng STING lên hai chỉ tiêu PAPI giai đoạn 2011–2024. Nhóm sẽ giải thích cách STING gán một tỉnh vào ô lưới, thống kê vị trí của các tỉnh năm 2024, rồi đối chiếu số liệu để nhận xét các nhóm.

## Thời lượng và trọng tâm từng slide

| Slide | Thời gian | Nội dung cần nói |
|---|---|---|
| 1 | 0:00–0:40 | Giới thiệu nhóm, đề tài và mạch phân cụm → hồi quy/đa chiều → suy luận → bàn giao. |
| 2 | 0:40–1:40 | Hai chỉ tiêu 4.2/6.1 trên panel 882 × 41; tiền xử lý 6 bước `Test → Decide` (0/882 trùng, 109 ô 0→NaN, giữ 7/808 `|z|>3`, `|Δ CV| ≤ 0,015 < cv_std(A)`). Phân tách thời gian fit đến 2023 và giữ nguyên khi gán 2024. |
| 3 | 1:40–3:10 | Cơ chế `fit → cluster → predict` trên ví dụ 3 × 3 và lưới PAPI 16 × 16, ngưỡng 5; giả lập 240 điểm đạt ARI 0,950. |
| 4 | 3:10–3:50 | Lưới 808 dòng: 629/650 điểm vào cụm thuộc Cụm 2 (96,8%) và 158 nhãn `−1`; nêu rõ hạn chế một cụm chi phối. |
| 5 | 3:50–4:35 | Đối chứng STING/K-means/DBSCAN trên 631 điểm giao (0,366 / 0,457 / 0,258) và bất biến z-score 869/869 ô. |
| 6 | 4:35–5:55 | Biểu đồ & bảng 63 tỉnh năm 2024: 48 Cụm 2, 8 rìa điểm cao, 5 rìa 6.1 thấp (`< 1,8791`), 2 thiếu dữ liệu. |
| 7 | 5:55–7:15 | Dịch chuyển 59 tỉnh (7 rời, 5 vào) và truy vết phép chia ô cho Lạng Sơn năm 2023 `(13, 9)` → 2024 `(12, 10)` với 12 ≥ 5. |
| 8 | 7:15–8:20 | Dự báo Ridge 2 đầu ra (bỏ sót 0/11 ca ngoài vùng, AUC 0,816) + phân loại cân bằng `C3 RF` (`CV 0,524`, `Acc 71,2%/F1 0,569`) và `C1 LR` (`74,6%/0,595`). |
| 9 | 8:20–9:30 | Hồi quy 17 cấu hình `6.1`: cơ chế AR(1) (0,2679), sai phân `Δ6.1` Ridge (CV `0,2732`), `VIF = 3,76–5,00`, `Wilcoxon p = 0,01939`, `Conformal 90%` phủ `94,9%` (precision `4/28`, độ phủ ≠ độ chính xác cảnh báo), `E3` thắng 4/6 năm. |
| 10 | 9:30–10:40 | Điểm nghẽn lưới đều (`PCA k=1`, `8D 60,5%`, `16^d` `24,1%→100%`, `0/28` cặp `≤90%`); `QuantileSTING` hạ nhiễu 8D còn `44,7%` (`Silh +0,161`), `8D sàng lọc mc=7` tách `k=4` phủ `60,7%` 2024, `CLIQUE 5D/4D`, và lý do giữ `2D 3/4/5/2`. |
| 11 | 10:40–11:25 | Đối chiếu PCI/GRDP/ODM/Nghèo: chứng minh bằng cột `Year-FE CR1 (63 tỉnh)` rằng PCI gộp trên 2D (`5,84e-7`) tan biến thành `p = 0,7007`. |
| 12 | 11:25–12:35 | Suy luận bảng `FWL + CR1 + WCR Bootstrap (B=1.999) + TWFE`: `8D Quantile mc=7` đạt CR1 trên PCI (`β=+1,561, p=0,0156, WCR=0,0185`), Holm nội họ `0,0468`, Holm 6 phép `0,0937` (chưa đạt 5%), TWFE `p=0,3420` chưa bác bỏ 0; thăm dò `117/383 BH-FDR`; `residual_ridge` chưa phát hiện tự tương quan 5% (`I = −0,0431, p = 0,7930`). |
| 13 | 12:35–13:30 | Thống kê & nhận xét 63 tỉnh (76,2%, 12,7%, 7,9%, 3,2%), đối chiếu `2,235` vs `2,032` và `1,787` vs `1,963`, cùng `7` tỉnh trong Cụm 2 dưới mốc `6.1`. |
| 14 | 13:30–14:20 | Trình diễn hệ thống tích hợp: Dashboard Streamlit 6 tab (fail-closed), Excel 28 sheet, DOCX 7 chương, 2 notebook, khung mù đôi 16 hồ sơ & CI 3 HĐH (`293` test, `94%`). |
| 15 | 14:20–15:00 | Tổng kết 4 trụ cột, giới hạn phương pháp luận và 2 bước tiếp theo (chấm mù đôi 16 ca + kiểm định tiền cứu PAPI 2025). |

## Chuẩn bị demo

Chạy từ thư mục gốc dự án:

```bash
python scripts/deliverables/demo_smoke.py
python -m streamlit run app.py
```

Nếu cần kiểm tra một dòng khi hỏi đáp, mở sẵn bảng năm 2024 trên dashboard. Lọc Hà Nội để đối chiếu ô (10, 5), 3 điểm tham chiếu và điểm 6.1 = 1,686. Phiếu HTML có thể in thành một trang A4. [Hướng dẫn sử dụng](../customer_guide.md)

Nếu không chạy được ứng dụng tại phòng trình chiếu, mở [`results/stakeholder_province_summary_2024.csv`](../../results/stakeholder_province_summary_2024.csv) và [`notebooks/Nhom15_STING_PAPI.ipynb`](../../notebooks/Nhom15_STING_PAPI.ipynb) với outputs đã lưu. Không chạy lại toàn bộ pipeline khi đang thuyết trình. Xem thêm [hướng dẫn demo](../../DEMO.md).

## Nội dung học có giám sát dùng khi hỏi đáp slide 8

Hồi quy dự báo điểm liên tục, còn phân loại dự báo trạng thái trong/ngoài vùng dày
mà STING tạo ra. Các mô hình học phần gồm Gaussian Naive Bayes, KNN, SVM tuyến tính
và RBF, cây quyết định, Random Forest và Logistic Regression. Đọc kết quả tại
[`course_supervised_baselines.md`](../../results/course_supervised_baselines.md)
và các ma trận nhầm lẫn, với cùng dữ liệu đầu vào và các fold theo thời gian.

- Chọn mô hình bằng macro-F1 qua sáu fold expanding origin 2017–2022; giữ riêng
  mốc 2023→2024 gồm 59 tỉnh để đối chiếu.
- Naive Bayes có macro-F1 CV 0,514 và KNN 0,486. Khoảng cách 0,028 nhỏ hơn độ lệch
  fold của Naive Bayes 0,120, nên thứ hạng này chưa chứng minh mô hình vượt trội.
- Đọc macro-F1, recall từng lớp và ma trận nhầm lẫn; accuracy cao vẫn có thể bỏ
  sót toàn bộ lớp ít, như dự báo điểm Ridge ở slide 8.
- Đây là nhãn tham chiếu của mô hình, chưa phải đánh giá chất lượng quản trị do
  chuyên gia xác nhận. Hai fold cuối trùng một phần các năm đã dùng để chọn
  cấu hình STING, nên kết quả CV phân loại chưa độc lập hoàn toàn với lựa chọn nhãn.

Chi tiết classifier không thay thế thí nghiệm dự báo hai chỉ tiêu bằng Ridge.
Nhánh Ridge trên slide 8 chọn theo MAE với sáu lượt kiểm định có đích 2018–2023;
không trộn số liệu của nhánh này với bảng hồi quy một mục tiêu ở phụ lục báo cáo.

## Các câu hỏi dễ nhầm và cách trả lời

**Có ba cụm thì tại sao chỉ nói về một cụm lớn?**

Ba nhãn kỹ thuật có kích thước 5, 16 và 629 trên 808 quan sát lịch sử. Hai cụm nhỏ chỉ xuất hiện trong các năm đầu và không nhận điểm năm 2024. Vì vậy dữ liệu chủ yếu tạo một vùng tập trung lớn; số nhãn không bảo đảm có ba nhóm quản trị có ý nghĩa.

**Tại sao 13 tỉnh ngoài vùng nhưng dự báo chỉ đánh giá 11?**

13 là số tỉnh ngoài vùng trong 61 tỉnh có điểm quan sát năm 2024. Dự báo cần thêm dữ liệu đầu vào năm 2023 và điểm thực tế 2024, nên chỉ đối chiếu được 59 tỉnh, trong đó 11 tỉnh ngoài vùng. Hai mẫu số phục vụ hai câu hỏi khác nhau.

**Nhãn −1 có phải lỗi dữ liệu hoặc tỉnh yếu kém?**

Nhãn −1 là kết quả của quy tắc mật độ và biên lưới. Nó khác cờ cực trị |z| > 3 và khác giá trị thiếu. Trong năm 2024, cả 13 điểm −1 đều thuộc ô thưa trong biên lưới; một số ở phía điểm PAPI cao. Cần đọc tọa độ và nguồn dữ liệu trước khi diễn giải.

**Vì sao giữ các điểm cực trị?**

Các điểm vẫn hợp lệ theo miền dữ liệu. Xóa điểm có thể làm co biên lưới và thay đổi cách chia ô. Pipeline gắn cờ để kiểm tra, không tự xóa hoặc biến cờ đó thành nhãn cụm.

**AUC 0,816 có nghĩa dự báo đúng 81,6% không?**

Không. AUC đo khả năng xếp hạng giữa trường hợp ngoài và trong vùng trên tập đối chiếu, không phải tỷ lệ dự báo đúng. Đây là đánh giá hồi cứu một năm. Tỷ lệ kịch bản ngoài vùng chưa được hiệu chỉnh thành xác suất, và dự báo điểm thực tế bỏ sót cả 11 trường hợp ngoài vùng.

**STING có tốt hơn K-means không?**

Chưa có cơ sở kết luận tổng quát. K-means k = 2 có silhouette cao hơn trên cùng 631 điểm giao. STING có ưu điểm truy vết qua ô và ngưỡng đếm, nhưng hình học cụm và ý nghĩa sử dụng cần đánh giá riêng. ARI 0,950 chỉ là kiểm chứng trên bộ giả lập có nhãn tham chiếu.

**Kiểm định nguồn ngoài có chứng minh quan hệ nhân quả không?**

Không. Các nguồn ngoài hỗ trợ đối chiếu mô tả. Nhiều quan sát thuộc cùng tỉnh qua các năm nên giả định độc lập bị hạn chế — bổ sung suy luận bảng [`panel_inference.md`](../../results/panel_inference.md) (Year-FE + sai số gộp 63 tỉnh **CR1** và Wild Cluster Bootstrap `B=1.999`) xác nhận tín hiệu PCI của STING 2D (`p thô = 8,14e-7`) biến mất hoàn toàn sau kiểm soát năm (`p CR1 = 0,7007`), trong khi **8D Quantile mc=7** có tín hiệu Year-FE CR1 (`β = +1,561`, Holm nội họ 8D `0,0468`, Holm 6 phép chính `0,0937`); TWFE `p = 0,3420` chưa bác bỏ 0 và không chứng minh nhân quả nội tỉnh.

**8D Quantile tách được 4 cụm và kiểm định FDR đa chiều kết luận gì thêm?**

Trên `m = 383` phép thử sàng lọc thăm dò từ `high_dim_sting_subspaces.csv` (`223` bộ đặc trưng PCI), hiệu chỉnh đa kiểm định giữ lại **`117` BH-FDR 5%** (`68` BY-FDR, `34` Holm FWER), đồng thời chẩn đoán không gian 2024 cho thấy phần dư Ridge chưa phát hiện tự tương quan không gian ở ngưỡng 5% (`Moran's I = -0,0431, p = 0,7930`, hoán vị quanh `E[I]`). Tuy vậy, STING 2D `3/4/5/2` vẫn là cấu hình bàn giao chính vì chia quantile trên lưới mịn `2D 16×16` làm vỡ lõi lên `49,0%` nhiễu.

**Vì sao 8D lưới đều nhiễu 60,5% và PCA(2) chỉ còn 1 cụm; mở rộng STING đa chiều xử lý thế nào và có thay bản 2D không?**

Lưới đều mịn `16^d` bùng nổ số ô theo số chiều (`24,1% → 93,9%` ở `d=3` → `100%` ở `d=4`) nên các quan sát bị loãng thành nhiễu, còn `PCA(2)` trên `9×9` chỉ giữ `63,2%` phương sai nên gom vào `1` lõi. Mở rộng [`high_dim_sting.md`](../../results/high_dim_sting.md) giữ chống rò rỉ `<= 2023` và bổ sung hai hướng: (1) `Subspace CLIQUE` tìm không gian con dày từ dưới lên đến `5D` (`41,0%` phủ) và `4D Quantile` (`Silhouette 0,772`, `PCI_dm p = 6,99e-6`); (2) `QuantileSTING` chia ô theo phân vị kết hợp ngưỡng hiệu chuẩn `n/res^d`, hạ nhiễu `8D d1–d8` từ `60,5%` xuống `44,7%` (`Silh. +0,161`) và tách `k=4` trên 8 tiểu chỉ tiêu (phủ `56,6%` train / `60,7%` năm 2024, `PCI_dm p = 0,0005`, vẫn giữ `k=3` sau chuẩn hóa `within-year z`). Ngược lại, trên lưới mịn `2D 16×16` (`4.2, 6.1`), chia quantile cắt vụn vùng lõi (`49,0%` nhiễu vs `19,6%` lưới đều), nên cấu hình chính `2D 3/4/5/2` vẫn giữ nguyên làm chuẩn bàn giao 63 tỉnh.

Ghi người trình bày, thời gian đo được và điểm cần sửa vào [nhật ký luyện tập](rehearsal_log.md). Các câu hỏi chuyên sâu nằm trong [Q&A cuối kỳ](qa_final.md), [Q&A giữa kỳ](qa_midterm.md) và [khái niệm môn học](qa_course_concepts.md).
