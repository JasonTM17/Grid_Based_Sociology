# Câu hỏi ôn tập giữa kỳ — Grid-based clustering và STING

## Hiểu chủ đề trước khi học mã

| Thành phần | Ý nghĩa trong bài nhóm |
|---|---|
| Grid-based clustering | Nhóm phương pháp phân cụm dựa trên lưới. |
| STING | Thuật toán nhóm chọn để minh họa chủ đề. Cài đặt dùng biến thể rút gọn. |
| PAPI | Dữ liệu thật nhóm đã chuẩn bị để minh họa phần ứng dụng. |

1. **Nhóm đang làm đề tài gì?** Nhóm nghiên cứu phân cụm dựa trên lưới, chọn STING và áp dụng thử lên dữ liệu PAPI cấp tỉnh. Giữa kỳ tập trung vào định nghĩa và demo cơ bản. (nguồn: reports/course_requirements.md)

2. **STING liên quan thế nào đến Grid-based clustering?** Grid-based là cách tiếp cận chung. STING thuộc nhóm này, tổ chức dữ liệu theo lưới nhiều mức và lưu thống kê trong từng ô. (nguồn: src/sting.py)

3. **Phân cụm tạo ra kết quả gì?** Đầu vào gồm các điểm có các đặc trưng số. Kết quả gán mỗi điểm vào một cụm hoặc đánh dấu nhiễu. Với dữ liệu giả lập, nhãn đã biết khi sinh dữ liệu được dùng để kiểm chứng kết quả. (nguồn: notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

4. **Notebook đang dùng dữ liệu nào?** Có ba ví dụ. Lưới 3 × 3 được dựng từ 15 điểm để thấy từng bước tạo cụm. Bộ 240 điểm giả lập có hai nhóm tham chiếu. Phần ứng dụng dùng dữ liệu PAPI thật. (nguồn: scripts/notebooks/gen_submission_demo.py)

5. **Đã có dữ liệu thật thì trình bày giữa kỳ ra sao?** Có thể nói với thầy rằng nhóm dùng ví dụ nhỏ để giải thích thuật toán, sau đó giới thiệu ngắn dữ liệu PAPI đã chuẩn bị cho phần ứng dụng. Yêu cầu giữa kỳ trong slide là định nghĩa và demo cơ bản. (nguồn: reports/course_requirements.md)

## Giải thích ví dụ lưới 3 × 3

6. **Số trong mỗi ô có ý nghĩa gì?** Đó là số điểm thuộc ô. Bảng đếm gồm hàng trên 4, 3, 0, hàng giữa 1, 0, 4 và hàng dưới 0, 0, 3. Tổng cộng có 15 điểm. (nguồn: notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

7. **Vì sao có hai cụm, mỗi cụm 7 điểm?** Ngưỡng ô dày là 3. Hai ô 4 và 3 điểm chung cạnh ở hàng trên tạo một cụm. Hai ô 4 và 3 điểm phía phải tạo cụm còn lại. Hai vùng chỉ chạm góc nên tách riêng theo quy tắc nối qua cạnh. (nguồn: scripts/deliverables/build_slides_10.py)

8. **Điểm nhiễu là gì?** Ô có 1 điểm nằm dưới ngưỡng 3 nên điểm đó nhận nhãn −1. Trong PAPI, nhãn nhiễu mô tả vị trí ngoài các ô dày đã học trên hai chỉ tiêu đang xét. (nguồn: src/sting.py; scripts/notebooks/gen_submission_demo.py)

9. **Đổi độ mịn lưới hoặc ngưỡng ô dày ảnh hưởng thế nào?** Lưới mịn hơn phân tán điểm vào nhiều ô. Ngưỡng lớn hơn đòi hỏi nhiều điểm hơn trong mỗi ô dày. Cả hai thay đổi có thể làm đổi số cụm và tỷ lệ nhiễu, nên cần xem bảng độ nhạy. (nguồn: results/predict_summary.md)

10. **Bản nhóm khác STING gốc ở đâu?** Nhóm lưu số điểm và các thống kê theo ô, sau đó chọn một mức lưới và gom các ô dày chung cạnh. STING gốc còn mô hình hóa phân phối và duyệt lưới từ trên xuống theo tiêu chí thống kê. (nguồn: src/sting.py)

11. **Độ phức tạp cần giải thích thế nào?** Với L mức lưới, n điểm và d đặc trưng, bước xây thống kê phụ thuộc L, n và d. Ở chế độ nối qua cạnh, mỗi ô xét tối đa 2d ô kề. Có thể nói chi phí tăng theo số điểm khi các tham số còn lại được giữ cố định. (nguồn: src/sting.py)

## Hiểu phần ứng dụng PAPI

12. **Một điểm PAPI đại diện cho gì?** Một dòng ứng với một tỉnh trong một năm. Demo phân cụm dùng hai chỉ tiêu: kiểm soát tham nhũng trong cung ứng dịch vụ công và y tế công lập. Đầu vào thuật toán được chuẩn hóa; đơn vị hiển thị được ghi trên trục từng hình. Ví dụ, biểu đồ dự đoán năm 2024 hiển thị điểm thành phần PAPI gốc. Bảng dữ liệu có 882 dòng và 41 cột. (nguồn: models/predict_config.json; data/processed/papi_panel_63_2011_2024.csv; scripts/analysis/predict_demo.py)

13. **Vì sao cần chuẩn hóa?** Hai chỉ tiêu được đưa về thang z-score để đo khoảng cách và đặt lưới trên cùng quy mô. Thống kê chuẩn hóa được học từ 2011–2023 rồi áp dụng cho năm 2024. (nguồn: scripts/common/papi_pred_common.py; scripts/analysis/predict_demo.py)

14. **Kết quả 48 tỉnh và 13 tỉnh được hiểu thế nào?** Năm 2024 có 61/63 tỉnh đủ hai chỉ tiêu. Trong số này, 48 tỉnh được gán vào cụm và 13 tỉnh nhận nhãn nhiễu. Tỷ lệ được gán cụm là 48/61, xấp xỉ 79%. (nguồn: results/predict_summary.md)

15. **Đánh giá bằng chỉ số nào?** Ví dụ giả lập dùng ARI so với nhãn đã biết. Với PAPI, nhóm xem số cụm, kích thước cụm, tỷ lệ nhiễu và silhouette. ARI giữa STING và phương pháp khác đo mức đồng thuận giữa hai cách phân hoạch. (nguồn: results/metrics.csv)

16. **STING, K-means và DBSCAN khác nhau thế nào?** STING dùng thống kê ô lưới. K-means dùng các tâm cụm và số cụm đã đặt trước. DBSCAN tìm vùng điểm dày theo lân cận quanh từng điểm. Bảng so sánh cần đọc kèm tỷ lệ nhiễu và tập điểm dùng để tính silhouette. (nguồn: results/metrics.csv; src/sting.py)

17. **Kết luận nào phù hợp với kết quả hiện có?** Trên hai chỉ tiêu đã chọn, cấu hình STING cho một cụm lớn và hai cụm nhỏ ở tập 2011–2023. Kết luận cần giới hạn trong hai chỉ tiêu, giai đoạn dữ liệu và cấu hình đã dùng. (nguồn: results/metrics.csv; models/predict_config.json)

## Mở tài liệu đúng mốc

18. **Mở file nào khi tập và khi chiếu?** Khi tập, mở bản có giải thích trong study và kịch bản cùng thư mục này. Khi chiếu, mở notebook và slide đã đặt tên theo nhóm trong submissions/01-giua-ky. Cách chạy lại nằm trong README và DEMO. (nguồn: README.md; DEMO.md)
