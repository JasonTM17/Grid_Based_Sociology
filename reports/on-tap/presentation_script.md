# Kịch bản thuyết trình 12 slide STING và PAPI

Bộ slide chính là [`slides/Nhom15_STING_PAPI.pptx`](../../slides/Nhom15_STING_PAPI.pptx). Nội dung đi từ bài toán và cơ chế thuật toán đến kết quả PAPI, dự báo bổ trợ và giới hạn ứng dụng. Bộ trình chiếu có **12 slide**, dành khoảng **15 phút trình bày và 5 phút hỏi đáp**. Bảng thời gian dưới đây là kế hoạch luyện tập, chưa phải thời gian đã đo. Nội dung trên màn hình giữ các kết quả và giới hạn cần thiết; ghi chú slide cung cấp chi tiết để trả lời phản biện, không cần đọc nguyên văn.

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

> Thưa thầy và các bạn, nhóm 15 trình bày cài đặt thuật toán phân cụm dựa trên lưới STING và ứng dụng trên dữ liệu PAPI giai đoạn 2011–2024. Nhóm tập trung giải thích cơ chế gán cụm, kiểm tra kết quả trên cùng phạm vi dữ liệu và tạo bảng mô tả để hỗ trợ rà soát từng tỉnh. Phần gán điểm PAPI đã quan sát năm 2024 được trình bày riêng với thí nghiệm dự báo điểm năm 2024.

## Thời lượng và trọng tâm từng slide

| Slide | Thời gian | Nội dung cần nói |
|---|---|---|
| 1 | 0:00–0:50 | Giới thiệu đề tài, Nhóm 15, hai thành viên và giảng viên. Nêu câu hỏi các tỉnh tập trung ở đâu trong không gian chỉ tiêu và thay đổi thế nào; mục tiêu là kiểm chứng STING, truy vết kết quả và tạo bảng rà soát 63 tỉnh. |
| 2 | 0:50–2:20 | Giải thích 4.2 và 6.1; panel 882 × 41, 13 dòng thiếu nên còn 869 dòng đầy đủ. Một dòng là một tỉnh–năm. Nêu kiểm tra khóa, quy ước 0 thành thiếu, giữ NaN và gắn cờ cực trị. Kiểm tra thang đo theo giai đoạn. Chọn cấu hình qua fit đến 2020 và kiểm định 2021–2022, sau đó fit lại 808 dòng 2011–2023. Scaler chỉ fit trên train; 2024 chỉ transform và gán nhãn. |
| 3 | 2:20–3:55 | Đọc bảng đếm 3 × 3: hai cặp ô dày tạo hai cụm 7 điểm, một điểm ô thưa nhận −1. Kề góc không nối. Phân biệt biến thể gom ô tại một tầng với truy vấn vùng top-down của STING gốc. Giả lập 240 điểm đạt ARI 0,950, không phải accuracy trên PAPI. |
| 4 | 3:55–4:40 | Lưới 808 dòng có các cụm 629, 16, 5 và 158 điểm −1. Cụm 2 chiếm 96,8% số điểm đã vào cụm; ba nhãn không đồng nghĩa ba phân khúc quản trị cân bằng. |
| 5 | 4:40–5:40 | So silhouette trên cùng 631 điểm giao: STING 0,366; K-means 0,457; DBSCAN 0,258. Số cụm và nhiễu vẫn dùng mẫu 808. Kết quả hình học chưa xác nhận ý nghĩa quản trị. Thí nghiệm toàn kỳ giữ nguyên 869/869 chỉ số ô sau z-score vì dựng lại lưới đều trên cùng mẫu. |
| 6 | 5:40–7:10 | Kết hợp đồ thị 61 điểm quan sát và bảng đủ 63 tỉnh: 48 trong vùng dày, 8 ngoài vùng phía điểm cao, 5 ngoài vùng có 6.1 thấp, 2 thiếu dữ liệu. Ngưỡng 1,8791 là quy tắc mô tả hậu nghiệm; 7 tỉnh trong vùng dày cũng dưới ngưỡng. Không coi −1 là yếu kém hay bảng này là bốn cụm do STING học. |
| 7 | 7:10–8:25 | Ma trận 59 tỉnh: 43 giữ vùng dày, 7 rời vùng, 5 đi vào, 4 vẫn ngoài. Nêu 5/7 tỉnh rời vùng nằm phía điểm cao. Truy vết Lạng Sơn từ ô (13,9), count 2 sang ô (12,10), count 12. Count là số điểm lịch sử trong ô, không phải dân số hoặc lượng khảo sát của tỉnh. |
| 8 | 8:25–10:05 | Phân biệt dự báo giá trị liên tục và gán nhãn từ điểm đã quan sát. Ridge cải thiện MAE nhẹ, nhưng RMSE 4.2 xấu hơn giữ điểm 2023. Dự báo điểm phát hiện 0/11 tỉnh ngoài vùng; balanced accuracy 0,500. AUC 0,816 từ 364 cặp phần dư là thăm dò hồi cứu, chưa phải xác suất hiệu chỉnh. Giới thiệu nhánh phân loại học phần dùng pseudo-label STING, đánh giá macro-F1; chi tiết CV và từng mô hình dùng khi hỏi đáp. |
| 9 | 10:05–11:15 | Đối chiếu PCI, GRDP, ODM và nghèo. P-value chỉ tham khảo do quan sát lặp theo tỉnh và khác biệt năm. ODM không ghi nhận điểm cơ sở ở 10 tỉnh không có nghĩa các tỉnh đó không có cơ sở y tế. P-value lớn chưa chứng minh không có khác biệt. |
| 10 | 11:15–12:20 | PCA/8D cho thấy độ nhạy với biểu diễn và tham số. Hạ min_count xuống 2 giảm nhiễu nhưng silhouette âm −0,089; giảm nhiễu chưa đủ để gọi cấu trúc tốt. Đây là các thử nghiệm mô tả, không dùng làm kết quả dự báo. |
| 11 | 12:20–13:45 | Demo tab “Thống kê khách hàng” luôn hiển thị 2024: chọn Lạng Sơn, đọc hai chỉ tiêu, ô lưới và count. Lọc nhóm, tải CSV hoặc phiếu HTML; mở phiếu và in thành PDF khổ A4. Chỉ thực hiện một ca đã chuẩn bị sẵn, nêu giới hạn ngay khi giải thích kết quả. |
| 12 | 13:45–15:00 | Tổng kết phần cài đặt, tái lập, truy vết và bảng 63 tỉnh. Nhắc ba giới hạn chính: cụm lớn chiếm ưu thế, nhạy tham số, quy tắc và AUC mang tính hồi cứu. Hướng tiếp theo là kiểm định độc lập, đánh giá cuốn chiếu và thẩm định với người dùng. Cảm ơn và mời câu hỏi. |

## Chuẩn bị demo

Chạy từ thư mục gốc dự án:

```bash
python scripts/deliverables/demo_smoke.py
python -m streamlit run app.py
```

Trước khi vào phần nói, mở sẵn tab **Thống kê khách hàng**, luôn hiển thị dữ liệu năm 2024. Dùng bộ lọc tỉnh và nhóm trong tab; tải CSV theo đúng bộ lọc. Phiếu tải trực tiếp là HTML, mở trong trình duyệt rồi in khổ A4 để lưu PDF. Xem [hướng dẫn sử dụng](../customer_guide.md). Tên nhóm trong ứng dụng và CSV là nhãn quy tắc của sản phẩm; khi diễn giải, dùng ý nghĩa mô tả trên slide 6. Không gọi các nhóm là chứng nhận chất lượng hay bốn cụm do STING tự tìm được.

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

Không. Các nguồn ngoài hỗ trợ đối chiếu mô tả. Nhiều quan sát thuộc cùng tỉnh qua các năm nên giả định độc lập bị hạn chế. Cần thiết kế và mô hình phù hợp hơn trước khi suy luận tác động chính sách.

Ghi người trình bày, thời gian đo được và điểm cần sửa vào [nhật ký luyện tập](rehearsal_log.md). Các câu hỏi chuyên sâu nằm trong [Q&A cuối kỳ](qa_final.md), [Q&A giữa kỳ](qa_midterm.md) và [khái niệm môn học](qa_course_concepts.md).
