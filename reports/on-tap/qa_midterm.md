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

9. **Đổi độ mịn lưới hoặc ngưỡng ô dày ảnh hưởng thế nào?** Giữ ngưỡng 5, lưới 1 × 1, 4 × 4 và 16 × 16 lần lượt tạo 1, 1 và 3 cụm, với 0, 6 và 171 điểm nhiễu. Trên riêng lưới 16 × 16, nâng ngưỡng từ 5 lên 8 cho 1 cụm và 31,2% nhiễu. Giải thích tác động của từng tham số bằng lượt thử chỉ đổi tham số đó. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

10. **Nhóm dùng lưới STING để phân cụm và truy vấn ra sao?** Khi phân cụm, nhóm chọn một mức lưới và nối các ô dày chung cạnh. Khi cần thống kê theo vùng, notebook minh họa `query_top_down`, duyệt từ mức thô và tỉa nhánh theo xác suất ước lượng từ phân phối chuẩn từng chiều. Bài báo gốc lưu loại phân phối của từng thuộc tính trong ô. [Mã STING](../../src/sting.py)

11. **Độ phức tạp cần giải thích thế nào?** Với L mức lưới, n điểm và d đặc trưng, bước xây thống kê phụ thuộc L, n và d. Ở chế độ nối qua cạnh, mỗi ô xét tối đa 2d ô kề. Có thể nói chi phí tăng theo số điểm khi các tham số còn lại được giữ cố định. (nguồn: src/sting.py)

## Hiểu phần ứng dụng PAPI

12. **Một điểm PAPI đại diện cho gì?** Một điểm ứng với một tỉnh trong một năm. Tọa độ là chỉ tiêu 4.2 và 6.1 sau chuẩn hóa. Mẫu phân cụm có 869 quan sát đủ cả hai chỉ tiêu, gồm 61 quan sát năm 2024. Nhóm dùng cả mẫu để mô tả cấu trúc vùng điểm trong giai đoạn 2011–2024. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

13. **Vì sao cần chuẩn hóa?** Hai chỉ tiêu được đưa về cùng đơn vị độ lệch chuẩn. Với chỉ tiêu 4.2 của Lạng Sơn năm 2024, lấy điểm gốc 2,072702 trừ trung bình 1,908406 rồi chia độ lệch chuẩn 0,182448 để được z ≈ 0,9005. Tính tương tự với chỉ tiêu 6.1 được z ≈ 0,3737. Hai tọa độ này đưa điểm vào ô (12, 10) của lưới, với 17 quan sát trong ô. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

14. **Ba cụm STING đến từ đâu và vì sao dùng ngưỡng 5?** Nhóm chọn cặp chỉ tiêu và tham số cùng nhau qua thử cấu hình với dữ liệu đến 2020, đối chiếu độ phủ 2021–2022. Quy tắc chọn ưu tiên các cấu hình gần 3 cụm. Ở cấu hình 16 × 16 và ngưỡng 5, thuật toán đếm được 56 ô dày và nối qua cạnh thành ba vùng gồm 1, 3 và 52 ô. Chúng chứa 5, 16 và 677 điểm. [Cấu hình đã chốt](../../models/predict_config.json) · [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

15. **Vì sao K-means dùng hai cụm?** Nhóm thử k = 2, 3, 4 và 5. Silhouette lần lượt là 0,4472, 0,3354, 0,3649 và 0,3311. Chọn k = 2 vì điểm cao nhất trong nhóm giá trị đã thử. K-means gán đủ 869 điểm theo khoảng cách tới tâm cụm. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

16. **Vì sao có hai cỡ mẫu trong bảng?** Đếm cụm và nhiễu trên 869 điểm. STING bỏ 171 điểm khi tính silhouette, DBSCAN bỏ 120 điểm, trùng 102 điểm. Vì vậy phần giao còn 869 − (171 + 120 − 102) = 680 điểm. K-means k = 2 đạt 0,4472 ở bước chọn k trên 869 điểm và 0,4605 ở bước đối chiếu trên 680 điểm. Bảng giữ nguyên nhãn đã tạo trên mẫu đầy đủ và đo khoảng cách trên cùng thang z. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

17. **Kết luận nào phù hợp với kết quả hiện có?** Trên hai chỉ tiêu đã chọn, cấu hình chính cho một vùng tập trung lớn, hai vùng nhỏ và 171 điểm nhiễu. Cụm lớn chứa 677 trong 698 điểm đã vào cụm. Nêu rõ kết quả mô tả hai chỉ tiêu và phụ thuộc tham số lưới. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

18. **Nếu đặt K-means k = 3 thì có ra đúng ba cụm STING không?** Bảng chéo cho thấy 677 điểm trong cụm STING lớn nhất bị K-means chia thành 482 và 195 điểm khi k = 2. Khi k = 3, những điểm này vẫn bị chia thành ba phần 306, 303 và 68 điểm. Hai cách dùng tiêu chí khác nhau. STING nối các ô dày, K-means chia điểm theo tâm gần nhất. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

19. **Bỏ z-score thì ba thuật toán đổi ra sao?** Dựng lại lưới theo min–max giữ 869/869 điểm trong cùng ô STING. K-means k = 2 đổi cụm ở 68 điểm sau ghép tên cụm. DBSCAN với min_samples = 5 đi từ 5 lên 6 cụm, từ 116 lên 120 điểm nhiễu và có 8 điểm đổi trạng thái nhiễu. Lượt chạy DBSCAN trên điểm gốc dùng vòng tròn cùng diện tích với elip tương ứng của ε = 0,2 trên thang z. Cả sáu ô hình dùng cùng tọa độ hiển thị. [Hình đối chiếu](../../results/figs/papi_zscore_comparison.png) · [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

20. **Tham số significance_z có ý nghĩa gì?** Đây là quy tắc lọc tùy chọn so trung bình ô con với ô cha sau bước đếm điểm. Khi thử ngưỡng minh họa 2,0 với cùng lưới, có 46 ô đạt, 4 cụm và 270 điểm nhiễu. Kết quả chính dùng ngưỡng 5 điểm/ô. Z-score đầu vào vẫn dùng để chuẩn hóa tọa độ từng điểm. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

**Hình phân bổ quan sát cuối dùng để làm gì?** Dùng hai chỉ tiêu PAPI đã ghi nhận năm 2024 để xem các tỉnh nằm ở đâu trên lưới 2011–2023. 48 tỉnh nằm ở 21 ô dày thuộc cùng cụm lớn. Khi ghép cùng tỉnh qua hai năm, 39/43 tỉnh giữ nguyên cụm vẫn đổi ô. Lạng Sơn là ví dụ từ ô thưa vào cụm lớn. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

**Nếu thầy hỏi nhóm dự báo điều gì?** Giữa kỳ dùng trực tiếp số liệu năm 2024 để mô tả phân cụm và sự thay đổi giữa hai năm. Trong thí nghiệm hồi cứu cuối kỳ, Ridge dự báo hai giá trị 4.2 và 6.1 trong tình huống chỉ dùng dữ liệu đến 2023. Đưa điểm do Ridge tạo lên lưới cho kết quả cả 59 tỉnh đối chiếu vào cụm lớn, bỏ sót 11 tỉnh thực tế nằm ngoài vùng dày. Mức trùng nhãn 48/59 bằng cách luôn chọn cụm lớn. [Notebook cuối kỳ](../../notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb)

**Vì sao đã tiền xử lý mà vẫn giữ nhiễu (sao lọc rồi mà vẫn còn nhiễu)?** Có 3 ý ngắn gọn để trả lời trực tiếp:
1. **Tiền xử lý lọc dữ liệu thiếu/lỗi**, không xóa điểm khảo sát thật: loại 13/882 dòng thiếu chỉ tiêu (năm 2024 loại 2 tỉnh Vĩnh Phúc, Tiền Giang), còn 869 quan sát đều đúng khoảng thang đo.
2. **Ngoại lai `|z| > 3` khác với nhãn `−1` của STING**: `|z| > 3` xét độ lệch trên từng trục (chỉ 9/869 điểm toàn mẫu và 0/61 tỉnh năm 2024), còn STING gán `−1` khi điểm rơi vào ô lưới `16 × 16` có dưới 5 quan sát. Trên toàn mẫu, `162/171` điểm nhãn `−1` (và cả `13/13` tỉnh nhãn `−1` năm 2024) đều có `|z| ≤ 3` ở cả hai trục; kể cả nếu bỏ 9 điểm `|z| > 3` rồi dựng lại lưới trên 860 điểm, biên `min–max` co lại làm ô hẹp hơn nên vẫn còn `173/860` điểm (`20,1%`) rơi vào ô thưa.
3. **Vì sao không xóa điểm `−1` sau khi phân cụm**: `−1` là kết quả của thuật toán cho biết các tỉnh nằm ở vùng thưa/khác biệt với cụm lớn (48 tỉnh) và giúp đo đúng độ phủ `48/61` (`78,7%`). Nếu chỉ giữ 48 tỉnh đã vào cụm, phép đếm sẽ cho 48/48 và che mất giới hạn độ phủ, cũng không theo dõi được các tỉnh chuyển từ ô thưa vào cụm lớn qua các năm (như Lạng Sơn 2023 → 2024). Notebook tính bảng lý do gán từ lưới; có thể tra ô và số quan sát tham chiếu của từng tỉnh trong CSV. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb) · [Bảng gán năm 2024](../../results/papi_observed_grid_2024.csv)

**Cờ z-score và nhãn −1 khác nhau ở phép tính nào?** Cờ `|z| > 3` xét giá trị trên từng trục (9/869 điểm toàn mẫu; 0/61 tỉnh năm 2024). STING xét số điểm trong ô của cả hai tọa độ. Trên 869 quan sát, `162/171` điểm nhãn `−1` (và `13/13` tỉnh nhãn `−1` năm 2024) có `|z| ≤ 3` ở cả hai chỉ tiêu. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

21. **Nhãn nhiễu −1 có đồng nghĩa tỉnh quản trị yếu kém không?** Không. Cả `13/13` tỉnh nhãn `−1` năm 2024 đều là trường hợp rơi vào ô thưa (`0–3` điểm tham chiếu) với `|z| ≤ 2,1299`, bao gồm cả các tỉnh đạt điểm **rất cao** ở rìa phải/trên (Tây Ninh `4.2 = 2,285`, Quảng Ninh `4.2 = 2,260`, Bà Rịa - Vũng Tàu `4.2 = 2,258`, Sóc Trăng `4.2 = 2,252`, Bình Thuận `4.2 = 2,218`, Hà Tĩnh `6.1 = 2,191`) lẫn rìa thấp hơn ở `6.1` (Hà Nội `1,686`, Cần Thơ `1,698`). [Bảng gán năm 2024](../../results/papi_observed_grid_2024.csv) · [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

22. **Đổi kề 8 hướng (`connectivity=2`) có giảm được điểm nhiễu không?** Không. `connectivity=2` nối qua góc chỉ gộp `56` ô dày từ `3` cụm thành `1` cụm duy nhất, còn số điểm nhiễu vẫn giữ nguyên `171/869` (`19,7%`) vì quy tắc đếm `count ≥ 5` của từng ô không đổi. Nhiễu chỉ đổi khi thay ngưỡng `min_count` (`3 → 9,8%`, `8 → 31,2%`) hoặc thay mức lưới (`4 × 4 → 0,7%`). (nguồn: src/sting.py:133-168; scripts/notebooks/gen_submission_demo.py:548-566)

23. **Khi thầy hỏi chỉ nhanh các sơ đồ từng bước trên đồ thị 2D thì mở ở đâu?** Mở trực tiếp **Slide 4** (`submission.pptx`) và notebook giữa kỳ: (1) **Mục 2** — tiến trình 4 bước STING trên lưới `3 × 3`; (2) **Mục 3** — 240 điểm Gauss + lưới `16 × 16`; (3) **Mục 4.3** — lưới phân cấp 3 mức (`1×1 → 4×4 → 16×16`) + biểu đồ 3 panel `|z| ≤ 3` vs nhiễu `−1`, bẫy xóa `|z| > 3`, bẫy `connectivity=2`; (4) **Mục 4.4–4.5** — K-Means dịch chuyển tâm + **TRAP!** + WCSS, Elbow/Silhouette và 4 quy tắc Linkage + ghép vòng & cắt Dendrogram; (5) **Mục 4.7** — 4 panel độ nhạy tham số. [Notebook giữa kỳ](../../notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb)

## Mở tài liệu đúng mốc

24. **Mở file nào khi tập và khi chiếu?** Dùng notebook và slide trong thư mục `submissions/01-giua-ky` để tập theo kết quả mới. Giải nén cả ZIP để chạy lại trên máy khác. [Hướng dẫn demo](../../DEMO.md)
