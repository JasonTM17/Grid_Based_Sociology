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

8. **Điểm nhiễu là gì?** Ô có 1 điểm nằm dưới ngưỡng 3 nên điểm đó nhận nhãn −1. Trong PAPI cũng vậy. Điểm nằm trong ô có ít hơn 5 quan sát nhận nhãn −1 ở cấu hình chính. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

9. **Đổi độ mịn lưới hoặc ngưỡng ô dày ảnh hưởng thế nào?** Lưới mịn hơn phân tán điểm vào nhiều ô. Trên cùng lưới 16 × 16, khi nâng ngưỡng từ 5 lên 8, số cụm giảm từ 3 xuống 1 và tỷ lệ nhiễu tăng từ 19,7% lên 31,2%. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

10. **Bản nhóm khác STING gốc ở đâu?** Nhóm lưu số điểm và các thống kê theo ô, sau đó chọn một mức lưới và gom các ô dày chung cạnh. STING gốc còn mô hình hóa phân phối và duyệt lưới từ trên xuống theo tiêu chí thống kê. (nguồn: src/sting.py)

11. **Độ phức tạp cần giải thích thế nào?** Với L mức lưới, n điểm và d đặc trưng, bước xây thống kê phụ thuộc L, n và d. Ở chế độ nối qua cạnh, mỗi ô xét tối đa 2d ô kề. Có thể nói chi phí tăng theo số điểm khi các tham số còn lại được giữ cố định. (nguồn: src/sting.py)

## Hiểu phần ứng dụng PAPI

12. **Một điểm PAPI đại diện cho gì?** Một điểm ứng với một tỉnh trong một năm. Tọa độ là chỉ tiêu 4.2 và 6.1 sau chuẩn hóa. Mẫu phân cụm có 869 quan sát đủ cả hai chỉ tiêu, gồm 61 quan sát năm 2024. Nhóm dùng cả mẫu để mô tả cấu trúc vùng điểm trong giai đoạn 2011–2024. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

13. **Vì sao cần chuẩn hóa?** Hai chỉ tiêu được đưa về cùng đơn vị độ lệch chuẩn. Với chỉ tiêu 4.2 của Lạng Sơn năm 2024, lấy điểm gốc 2,072702 trừ trung bình 1,908406 rồi chia độ lệch chuẩn 0,182448 để được z ≈ 0,9005. Tính tương tự với chỉ tiêu 6.1 được z ≈ 0,3737. Hai tọa độ này đưa điểm vào ô (12, 10) của lưới, với 17 quan sát trong ô. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

14. **Ba cụm STING đến từ đâu?** Dùng lưới 16 × 16 và ngưỡng ít nhất 5 quan sát mỗi ô. Đếm được 56 ô dày. Nối qua cạnh cho ba vùng gồm 1, 3 và 52 ô dày. Số điểm tương ứng là 5, 16 và 677. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

15. **Vì sao K-means dùng hai cụm?** Nhóm thử k = 2, 3, 4 và 5. Silhouette lần lượt là 0,4472, 0,3354, 0,3649 và 0,3311. Chọn k = 2 vì điểm cao nhất trong nhóm giá trị đã thử. K-means gán đủ 869 điểm theo khoảng cách tới tâm cụm. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

16. **Vì sao có hai cỡ mẫu trong bảng?** Số cụm và số điểm nhiễu được đếm trên 869 điểm. Silhouette so trực tiếp trên 680 điểm cả ba cách gán cụm, dùng cùng tọa độ z-score và giữ nguyên nhãn từ mẫu đầy đủ. STING đạt 0,3802, K-means k = 2 đạt 0,4605, K-means k = 3 đạt 0,3499, DBSCAN đạt 0,2740. Đây là độ gọn và độ tách theo khoảng cách Euclid trên 680 điểm. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

17. **Kết luận nào phù hợp với kết quả hiện có?** Trên hai chỉ tiêu đã chọn, cấu hình chính cho một vùng tập trung lớn, hai vùng nhỏ và 171 điểm nhiễu. Cụm lớn chứa 677 trong 698 điểm đã vào cụm. Nêu rõ kết quả mô tả hai chỉ tiêu và phụ thuộc tham số lưới. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

18. **Nếu đặt K-means k = 3 thì có ra đúng ba cụm STING không?** Bảng chéo cho thấy 677 điểm trong cụm STING lớn nhất bị K-means chia thành 482 và 195 điểm khi k = 2. Khi k = 3, những điểm này vẫn bị chia thành ba phần 306, 303 và 68 điểm. Hai cách dùng tiêu chí khác nhau. STING nối các ô dày, K-means chia điểm theo tâm gần nhất. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

19. **Bỏ z-score thì ba thuật toán đổi ra sao?** Dựng lại lưới theo min–max giữ 869/869 điểm trong cùng ô STING. K-means k = 2 đổi cụm ở 68 điểm sau ghép tên cụm. DBSCAN với min_samples = 5 đi từ 5 lên 6 cụm, từ 116 lên 120 điểm nhiễu và có 8 điểm đổi trạng thái nhiễu. Lượt chạy DBSCAN trên điểm gốc dùng vòng tròn cùng diện tích với elip tương ứng của ε = 0,2 trên thang z. Cả sáu ô hình dùng cùng tọa độ hiển thị. [Hình đối chiếu](../../results/figs/papi_zscore_comparison.png) · [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

20. **Tham số significance_z có ý nghĩa gì?** Đây là quy tắc lọc tùy chọn so trung bình ô con với ô cha sau bước đếm điểm. Khi thử ngưỡng minh họa 2,0 với cùng lưới, có 46 ô đạt, 4 cụm và 270 điểm nhiễu. Kết quả chính dùng ngưỡng 5 điểm/ô. Z-score đầu vào vẫn dùng để chuẩn hóa tọa độ từng điểm. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

**Hình phân bổ quan sát cuối dùng để làm gì?** Dùng chung lưới tới 2023 để đo độ phủ và phát hiện tỉnh đổi trạng thái, chẳng hạn Lạng Sơn từ ngoài vùng dày năm 2023 vào cụm lớn năm 2024. Nhãn suy từ hai điểm PAPI đã quan sát cũng là mốc đối chiếu cho phần dự báo. Ridge tạo hai điểm 2024 từ tám điểm 2023, sau đó đối chiếu sai số điểm và số tỉnh ngoài vùng dày trên mẫu đủ dữ liệu. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

**Vì sao đã tiền xử lý mà vẫn giữ nhiễu?** Tiền xử lý kiểm tra tính hợp lệ của dữ liệu. Hai tỉnh thiếu chỉ tiêu năm 2024 được loại khỏi phép gán. Trong 61 tỉnh đủ điểm, 13 tỉnh vào ô có dưới 5 quan sát tham chiếu nên nhận nhãn −1. Giữ 13 tỉnh trong mẫu giúp đo đúng độ phủ 48/61 và xem xét các trường hợp ngoài vùng dày. Nếu chỉ giữ 48 tỉnh đã vào cụm, phép đếm sẽ cho 48/48 và che mất giới hạn độ phủ. Notebook tính bảng lý do gán từ lưới. Có thể tra ô và số quan sát tham chiếu của từng tỉnh trong CSV. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb) · [Bảng gán năm 2024](../../results/papi_observed_grid_2024.csv)

## Mở tài liệu đúng mốc

21. **Mở file nào khi tập và khi chiếu?** Dùng notebook và slide trong thư mục `submissions/01-giua-ky` để tập theo kết quả mới. Giải nén cả ZIP để chạy lại trên máy khác. [Hướng dẫn demo](../../DEMO.md)
