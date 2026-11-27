# Kịch bản thuyết trình 15 slide STING và PAPI

Bộ slide chính là [`slides/Nhom15_STING_PAPI.pptx`](../../slides/Nhom15_STING_PAPI.pptx). Nội dung đi từ bài toán và cơ chế thuật toán đến kết quả PAPI, dự báo bổ trợ và giới hạn ứng dụng. Dành khoảng **15 phút trình bày và 5 phút hỏi đáp**. Bảng thời gian dưới đây là kế hoạch luyện tập, chưa phải thời gian đã đo.

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
| 1 | 0:00–0:20 | Giới thiệu đề tài, Nhóm 15, hai thành viên và giảng viên hướng dẫn. |
| 2 | 0:20–1:20 | Câu hỏi phân tích, hai trục 4.2 và 6.1, panel 882 × 41. Giải thích một điểm là một tỉnh–năm, không phải một người trả lời khảo sát. Địa giới theo bộ 63 tỉnh lịch sử. |
| 3 | 1:20–2:35 | Trình bày kiểm tra khóa, thiếu dữ liệu, thang đo và cực trị. Chọn cấu hình qua fit đến 2020 và chấm 2021–2022, sau đó fit lại 2011–2023. Năm 2024 chỉ dùng transform và gán nhãn. |
| 4 | 2:35–4:10 | Đọc bảng đếm 3 × 3: hai cặp ô dày tạo hai cụm 7 điểm, một điểm ô thưa nhận −1. Kề góc không nối. Nêu đây là biến thể gom ô dày tại một tầng của đồ án, phân biệt với truy vấn vùng top-down của STING gốc. Giả lập 240 điểm đạt ARI 0,950, không phải accuracy trên PAPI. |
| 5 | 4:10–4:55 | Lưới 808 dòng cho các cụm 629, 16, 5 và 158 điểm −1. Cụm 2 chiếm 96,8% số điểm được gán cụm, nên không diễn giải thành ba phân khúc cân bằng. |
| 6 | 4:55–5:55 | Silhouette trên cùng 631 điểm giao: STING 0,366; K-means 0,457; DBSCAN 0,258. Số cụm và nhiễu vẫn tính trên 808. Thí nghiệm toàn kỳ có 869/869 điểm giữ nguyên ô sau z-score vì dựng lại lưới đều trên cùng mẫu. |
| 7 | 5:55–6:45 | Đọc biểu đồ 61 tỉnh đã có điểm 2024: 48 vào Cụm 2, 13 nằm ở ô thưa trong biên lưới. Vĩnh Phúc và Tiền Giang thiếu dữ liệu. Nhãn −1 không có nghĩa là tỉnh yếu kém. |
| 8 | 6:45–8:05 | Giới thiệu bốn nhóm mô tả tổng 63: 48 trong vùng dày, 8 ngoài vùng phía điểm cao, 5 ngoài vùng có 6.1 thấp, 2 thiếu điểm. Ngưỡng 1,8791 là quy tắc mô tả năm 2024, không phải chuẩn chính thức. Có 7 tỉnh trong vùng dày cũng thấp hơn ngưỡng 6.1. |
| 9 | 8:05–9:10 | Ma trận 59 tỉnh: 43 giữ vùng dày, 7 rời vùng, 5 đi vào, 4 vẫn ngoài. Truy vết Lạng Sơn từ ô (13,9), count 2 sang ô (12,10), count 12. Count là số điểm lịch sử trong ô, không phải quy mô dân số. |
| 10 | 9:10–10:40 | Phân biệt dự báo điểm với gán điểm đã quan sát. Ridge cải thiện MAE nhẹ, nhưng RMSE 4.2 xấu hơn carry-forward. Dự báo điểm nhận ra 0/11 tỉnh ngoài vùng, balanced accuracy 0,500. AUC 0,816 từ 364 cặp phần dư là hồi cứu thăm dò, chưa phải xác suất hiệu chỉnh. |
| 11 | 10:40–11:40 | Đối chiếu PCI, GRDP, ODM và nghèo. Đọc p-value như thống kê tham khảo do dữ liệu tỉnh lặp theo năm. ODM có 10 tỉnh không ghi nhận điểm cơ sở trong nguồn; không kết luận các tỉnh này không có cơ sở y tế. P-value lớn chưa chứng minh không có khác biệt. |
| 12 | 11:40–12:35 | Mở rộng PCA/8D cho thấy nhạy với biểu diễn và tham số. Hạ min_count xuống 2 giảm nhiễu nhưng silhouette âm −0,089, nên không gọi đó là cấu trúc tốt. Nêu đây là thử nghiệm mô tả, không phải đánh giá dự báo. |
| 13 | 12:35–13:55 | Demo nhanh tab “Thống kê khách hàng”: xem 2024, mở một tỉnh, đọc trạng thái và xuất bảng. Chỉ thực hiện một ca Lạng Sơn đã chuẩn bị sẵn. |
| 14 | 13:55–14:45 | Kết luận về cài đặt, khả năng truy vết và bảng mô tả. Nêu giới hạn cụm lớn chiếm ưu thế, nhạy ngưỡng, quy tắc hậu nghiệm và nhu cầu kiểm định độc lập. |
| 15 | 14:45–15:00 | Cảm ơn và mời câu hỏi. |

## Chuẩn bị demo

Chạy từ thư mục gốc dự án:

```bash
python scripts/deliverables/demo_smoke.py
python -m streamlit run app.py
```

Trước khi vào phần nói, mở sẵn tab **Thống kê khách hàng** và dữ liệu năm 2024. Tên nhóm trong ứng dụng và CSV là nhãn quy tắc của sản phẩm; khi diễn giải, dùng ý nghĩa mô tả trên slide 8. Không gọi các nhóm là chứng nhận chất lượng hay bốn cụm do STING tự tìm được.

Nếu không chạy được ứng dụng tại phòng trình chiếu, mở [`results/stakeholder_province_summary_2024.csv`](../../results/stakeholder_province_summary_2024.csv) và [`notebooks/Nhom15_STING_PAPI.ipynb`](../../notebooks/Nhom15_STING_PAPI.ipynb) với outputs đã lưu. Không chạy lại toàn bộ pipeline khi đang thuyết trình. Xem thêm [hướng dẫn demo](../../DEMO.md).

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
