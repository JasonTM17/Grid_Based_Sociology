# Kịch bản thuyết trình 12 slide STING và PAPI

Bộ slide chính là [`slides/Nhom15_STING_PAPI.pptx`](../../slides/Nhom15_STING_PAPI.pptx). Nội dung đi từ bài toán và cơ chế thuật toán đến kết quả PAPI, dự báo bổ trợ và giới hạn ứng dụng. Bộ trình chiếu có **12 slide**, dành khoảng **15 phút trình bày và 5 phút hỏi đáp**. Bảng thời gian dưới đây là kế hoạch luyện tập, chưa phải thời gian đã đo. Nội dung trên màn hình giữ các kết quả và giới hạn cần thiết; ghi chú slide cung cấp chi tiết để trả lời phản biện, không cần đọc nguyên văn.

Mạch bài nói đi từ **phân cụm**, qua **thống kê**, đến **nhận xét từ kết quả**.
Slide 3–5 giải thích cách dựng lưới, tạo cụm và đối chứng. Slide 6–7 đọc số liệu
quan sát và tính thử một ô thật. Slide 11 tổng hợp số lượng, tỷ lệ và trung vị.

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
| 1 | 0:00–0:50 | Giới thiệu nhóm, đề tài và mạch phân cụm, thống kê, nhận xét. |
| 2 | 0:50–2:10 | Giải thích hai chỉ tiêu và đơn vị tỉnh–năm. Panel 882 × 41 có 13 dòng thiếu hai chỉ tiêu. Nêu kiểm tra khóa, cách xử lý điểm 0, cờ cực trị và thang đo. Chọn cấu hình với 2021–2022, dựng lưới tham chiếu trên 808 dòng 2011–2023, giữ nguyên khi gán điểm 2024. |
| 3 | 2:10–4:15 | Đi theo fit → cluster → predict và đọc bảng 3 × 3. Hai cặp ô chung cạnh tạo hai cụm, mỗi cụm 7 điểm. Một điểm ô thưa nhận −1. Giải thích công thức tra ô và ngưỡng 5 trên lưới PAPI 16 × 16. ARI 0,950 đo trên 240 điểm giả lập. |
| 4 | 4:15–5:05 | Lưới 808 dòng có các cụm 629, 16, 5 và 158 điểm −1. Cụm 2 chiếm 96,8% số điểm đã vào cụm. Hai cụm còn lại có rất ít quan sát. |
| 5 | 5:05–6:00 | Trên 631 điểm chung, silhouette lần lượt là 0,366, 0,457 và 0,258. Mẫu 808 dùng để đếm cụm và nhiễu. Khi dựng lại lưới đều trên cùng 869 điểm, z-score giữ nguyên 869 chỉ số ô. |
| 6 | 6:00–7:50 | Chỉ bốn nhóm trong bảng. STING gán nhãn trên 61 tỉnh đủ điểm. Hai mốc từ Cụm 2 chia tiếp 13 điểm ô thưa theo hai chỉ tiêu, còn 2 tỉnh thiếu vẫn có dòng trong báo cáo. |
| 7 | 7:50–9:30 | Đọc ma trận trên 59 tỉnh, sau đó tính từng trục cho Lạng Sơn năm 2024. Lấy phần nguyên được ô (12, 10) với 12 điểm tham chiếu nên vào Cụm 2. Ô năm 2023 có 2 điểm nên nhãn −1. Trong 7 tỉnh rời vùng dày, 5 nằm phía điểm cao. |
| 8 | 9:30–10:40 | Ridge giảm MAE nhẹ, còn RMSE của 4.2 tăng. Dự báo điểm phát hiện 0/11 tỉnh ngoài vùng. AUC 0,816 là kết quả hồi cứu; macro-F1 của Naive Bayes đo độ khớp nhãn STING. |
| 9 | 10:40–11:30 | Nêu một ví dụ đối chiếu PCI và giới hạn của kiểm định khi nhiều quan sát thuộc cùng tỉnh. Các nguồn ngoài bổ sung bối cảnh cho thống kê PAPI. |
| 10 | 11:30–12:15 | PCA và nhánh tám chiều cho thấy kết quả nhạy với biểu diễn. Hạ ngưỡng số điểm làm tỷ lệ nhiễu giảm trong thử nghiệm 8D, silhouette vẫn âm −0,089. |
| 11 | 12:15–14:10 | Đọc tỷ lệ 76,2%, 12,7%, 7,9% và 3,2% trên 63 tỉnh. Đối chiếu 2,235 với 2,032 ở trục 4.2 và 1,787 với 1,963 ở trục 6.1. Nhóm cùng nhãn −1 có thể nằm ở hai phía của phân bố. Trong Cụm 2 vẫn có 7 tỉnh dưới mốc 6.1. |
| 12 | 14:10–15:00 | Chốt STING truy vết được nhãn theo ô. Báo cáo nhận diện một vùng dày lớn cùng các trường hợp ở ô thưa. Nêu phạm vi hai chỉ tiêu và hướng kiểm tra với dữ liệu mới. |

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

Không. Các nguồn ngoài hỗ trợ đối chiếu mô tả. Nhiều quan sát thuộc cùng tỉnh qua các năm nên giả định độc lập bị hạn chế. Cần thiết kế và mô hình phù hợp hơn trước khi suy luận tác động chính sách.

Ghi người trình bày, thời gian đo được và điểm cần sửa vào [nhật ký luyện tập](rehearsal_log.md). Các câu hỏi chuyên sâu nằm trong [Q&A cuối kỳ](qa_final.md), [Q&A giữa kỳ](qa_midterm.md) và [khái niệm môn học](qa_course_concepts.md).
