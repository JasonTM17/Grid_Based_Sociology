# Hỏi đáp về học máy và ứng dụng STING trên PAPI

_Quy tắc: ≤60 giây/câu; mỗi thành viên phải giải thích được toàn bộ câu hỏi. Mọi số lấy từ file ghi ở dòng "Repo" của từng câu; không đọc số từ trí nhớ._

## Bảng số dùng chung — 8 baseline trên nhãn STING

| Model | Macro-F1 CV | Accuracy holdout | Macro-F1 holdout |
|---|---|---|---|
| Majority (lớp đa số của train) | 0.228 | 0.186 | 0.157 |
| Gaussian Naive Bayes | **0.514** | 0.746 | 0.566 |
| KNN | 0.486 | 0.593 | 0.534 |
| SVM tuyến tính | 0.343 | 0.695 | 0.556 |
| SVM RBF | 0.437 | 0.678 | 0.566 |
| Cây quyết định | 0.426 | 0.559 | 0.508 |
| Random forest | 0.394 | 0.627 | 0.560 |
| Logistic regression | 0.434 | 0.644 | 0.541 |

- CV = macro-F1, expanding origin 2017–2022, warm-up 2011–2016; holdout chấm một lần 2023→2024, 59 tỉnh: lớp 0 = 11, lớp 1 = 48; train 738 cặp.
- Hình confusion matrix của 6 model học phần (không có majority và logistic regression): `results/figs/course_confusion_matrix.png`.
- **Repo:** `results/course_supervised_baselines.csv:2-9`; `results/course_supervised_baselines.md:12-28,37`; `scripts/supervised/course_supervised_baselines.py:239-267`.

## Khái niệm học máy

1. **Học máy là gì, theo đúng định nghĩa bài giảng?** — Định nghĩa Arthur Samuel: lĩnh vực cho máy tính khả năng học mà không được lập trình tường minh. Khung của bài giảng là Data → Algorithm → Model: thuật toán học quy luật từ dữ liệu rồi cho ra model dùng để dự đoán. Repo theo đúng khung đó: `STING.fit` chỉ nhận ma trận điểm, không có luật viết tay; model lưu ra file rồi `predict` cho tỉnh mới.
   - **Hỏi bẫy:** "Vậy AI có phải ML?" — Không; bài giảng nói AI bao gồm ML và DL, nên ML là tập con, và repo không dùng DL.
   - **Repo:** `src/sting.py:84-125`; `README.md:233-250`.
   - **Bài giảng:** “Nhập môn học máy”, trang 15; trang 16.

2. **Học có giám sát khác học không giám sát ở đâu?** — Có giám sát: model học từ cặp (câu hỏi, đáp án) rồi trả lời câu mới. Không giám sát: chỉ nhận câu hỏi, tự tìm cấu trúc, không có đáp án đúng để đối chiếu. Repo có cả hai: STING là không giám sát (`cluster()` trả cụm và −1), còn Ridge/random forest/logistic regression là có giám sát trên cặp năm t → t+1.
   - **Hỏi bẫy:** "Đầu ra của không giám sát có phải nhãn đúng/sai?" — Không; đó là cụm, không có ground truth để chấm.
   - **Repo:** `src/sting.py:130-191`; `scripts/supervised/predict_supervised.py:1-14`.
   - **Bài giảng:** “Nhập môn học máy”, trang 27.

3. **Vì sao STING là grid-based clustering không giám sát, và khớp đề tài 6 thế nào?** — STING chia không gian thành lưới phân cấp, mỗi ô giữ count/mean/std/min/max, gom các ô "dày" liền kề thành cụm — không cần nhãn, không cần k. Đó đúng là đề tài 6 "Grid-based (clustering)"; panel 882 dòng × 41 cột vượt yêu cầu cuối kỳ ≥500 hàng và ≥10 cột.
   - **Hỏi bẫy:** "STING có cần truyền k?" — Không; k là kết quả của mật độ lưới + `min_count`, không phải tham số vào.
   - **Repo:** `src/sting.py:1-13`; `README.md:10`; `scripts/data/check_data.py:17-18`.
   - **Bài giảng:** “Nhập môn học máy”, trang 12.

4. **Regression và classification khác nhau thế nào, repo làm bài nào?** — Bài giảng: nhãn rời rạc → classification; nhãn liên tục → regression. Repo chạy cả hai: hồi quy dự báo điểm 6.1 Y tế công lập năm t+1 (Ridge, MAE holdout 0.0640) và phân loại nhị phân "vùng dày vs ngoại vi" (logistic regression, macro-F1 holdout 0.541).
   - **Hỏi bẫy:** "Nhãn bài phân loại là nhãn người gán?" — Không; là pseudo-label do STING tại từng cutoff sinh ra.
   - **Repo:** `scripts/supervised/predict_supervised.py:263-330, 332-370`; `results/supervised_metrics.csv:4-8`.
   - **Bài giảng:** “Nhập môn học máy”, trang 34.

5. **Bài phân loại của repo có phải semi-supervised không?** — Bài giảng mô tả semi-supervised: gom cụm toàn bộ dữ liệu, xem các điểm đã có nhãn, gán nhãn cụm theo đa số, điểm mới vào cụm nào nhận nhãn đó. Repo không có nhãn người cho bài này nên không được gọi semi-supervised: nhãn 0/1 do STING sinh (pseudo-label), classifier chỉ học lại quy tắc "ô dày hay không".
   - **Hỏi bẫy:** "Pseudo-label có phải ground truth?" — Không; nó đo mức khớp với STING, không đo đúng/sai xã hội.
   - **Repo:** `scripts/supervised/predict_supervised.py:12-14, 187-211`; `results/supervised_summary.md:29`.
   - **Bài giảng:** “Nhập môn học máy”, trang 36.

## Naive Bayes, KNN và đánh giá phân loại

6. **Naive Bayes hoạt động thế nào qua bảng xác suất, và repo đã chạy chưa?** — Naive Bayes tính xác suất có điều kiện từng thuộc tính theo lớp rồi nhân với xác suất tiên nghiệm, giả định các thuộc tính độc lập; bài giảng lập bảng đếm: Outlook Sunny là 2/9 và 3/5, tổng 5/14. Repo giờ CÓ: `GaussianNB` trong run so sánh học phần đạt macro-F1 CV 0.514, accuracy holdout 0.746, macro-F1 holdout 0.566 — cao nhất bảng theo CV.
   - **Hỏi bẫy:** "Ô Overcast ghi 0/5 thì xác suất bằng 0, sai ở đâu?" — Zero-frequency: phải làm trơn Laplace; bảng bài giảng chỉ là đếm thô. Lưu ý `GaussianNB` giả định mỗi đặc trưng có phân phối chuẩn theo lớp, không dùng đếm rời rạc như bảng bài giảng — cùng ý tưởng Bayes, khác công thức likelihood.
   - **Repo:** `scripts/supervised/course_supervised_baselines.py:138-141`; `results/course_supervised_baselines.csv:3`; `results/course_supervised_baselines.md:15,23`.
   - **Bài giảng:** “Học có giám sát”, trang 15; bảng xác suất trang 16-18.

7. **Naive Bayes đứng đầu CV ở đây — có được nói nó là model tốt nhất không?** — Không được nói "tốt nhất" như kết luận tổng quát. Nó đứng đầu theo tiêu chí đã chốt trước (macro-F1 CV 0.514, hơn KNN 0.486 và RBF 0.437), nhưng holdout macro-F1 0.566 chỉ ngang SVM RBF 0.566 và hơn RF 0.560; holdout chỉ 59 tỉnh, 11 tỉnh lớp 0 nên một tỉnh đổi nhãn đã đổi accuracy ~0.017. Thêm nữa grid của NB rỗng nên điểm CV của nó không bị đẩy lên bởi chọn siêu tham số như các model khác (điểm CV của chúng là max trên lưới); đó là lý do cấu trúc khiến NB trông sạch hơn, không phải bằng chứng vượt trội.
   - **Hỏi bẫy:** "Vậy chọn NB để triển khai?" — Chọn theo tiêu chí CV là NB, nhưng phải nói kèm: một holdout, không kiểm định ý nghĩa, và 2 fold CV cuối trùng vùng chọn cấu hình STING (xem câu 29); CV chỉ là khám phá.
   - **Repo:** `results/course_supervised_baselines.csv:3-9`; `results/course_supervised_baselines.md:23,28,31-35`; `scripts/supervised/course_supervised_baselines.py:138-141,239-267`.

8. **KNN dùng khoảng cách và k thế nào?** — KNN không học tham số: với điểm mới, tính khoảng cách (bài giảng dùng Euclidean), lấy k hàng xóm gần nhất, bầu nhãn theo đa số. k nhỏ nhạy nhiễu, k lớn làm mượt; bài giảng khuyên thử k = 1, 3, 5… và chọn k lẻ. Repo chạy KNN ở cả hai bài: hồi quy là ứng viên R3 (k=20, weights=distance), R² CV 0.168 thấp hơn Ridge 0.265 nên không được chọn; phân loại học phần quét k ∈ {3,5,7,9}, macro-F1 CV 0.486, holdout accuracy 0.593, macro-F1 0.534.
   - **Hỏi bẫy:** "Vì sao KNN phải chuẩn hóa?" — Khoảng cách bị chiều có thang lớn chi phối; repo bọc `StandardScaler` trong Pipeline nên mỗi fold tự fit scaler trên train của fold đó.
   - **Repo:** `results/candidates_regression.md:61`; `scripts/supervised/candidates_regression.py:160-161`; `results/course_supervised_baselines.csv:4`; `scripts/supervised/course_supervised_baselines.py:143-150`.
   - **Bài giảng:** “Học có giám sát”, trang 25-29 (Euclidean trang 26; chọn k trang 29).

9. **Vì sao báo accuracy thôi là chưa đủ, phải có macro-F1?** — Accuracy là tỉ lệ đoán đúng, dễ bị lớp đa số thống trị. Macro-F1 lấy trung bình F1 của từng lớp nên phạt việc bỏ rơi lớp thiểu số. Repo báo cả hai: logistic regression holdout accuracy 0.644, macro-F1 0.541; majority accuracy 0.186 nhưng macro-F1 0.157; CV dùng macro-F1 vì prevalence nhãn 1 trôi 0.000 (2011) → 0.917 (2021).
   - **Hỏi bẫy:** "Accuracy 0.9 là model tốt?" — Chưa, nếu lớp đa số đã chiếm 0.9; phải so với baseline đa số. Ở holdout này lớp 1 chiếm 48/59 ≈ 0.814, nên "luôn đoán 1" đã đạt accuracy 0.814; còn trên CV, baseline mù thời gian đó chỉ đạt macro-F1 0.400.
   - **Repo:** `scripts/supervised/predict_supervised.py:353-361`; `results/supervised_metrics.csv:6-7`; `results/supervised_summary.md:31`; `results/course_supervised_baselines.md:28`.
   - **Bài giảng:** “Học có giám sát”, trang 30-34 (confusion matrix, precision & recall) — macro-F1 không có trong text bài giảng, nhóm tự chọn và phải nói rõ.

10. **Confusion matrix cho biết gì?** — Ma trận 2×2 đối chiếu nhãn thật với nhãn dự báo: TP, FN, FP, TN; từ đó tính precision, recall. Repo vẽ confusion cho bài phân loại 2023→2024, nhãn 0 = ngoại vi (nhiễu STING), 1 = vùng dày, hình ở `results/figs/supervised_confusion.png`; đây là ma trận của classifier chọn theo CV, không phải của STING.
    - **Hỏi bẫy:** "Positive là tỉnh tốt?" — Không; positive = vùng dày (nhãn 1), không phải đánh giá tốt/xấu.
    - **Repo:** `scripts/supervised/predict_supervised.py:96, 463-488`.
    - **Bài giảng:** “Học có giám sát”, trang 31-33.

11. **Đọc hình `results/figs/course_confusion_matrix.png` thế nào?** — Hình có 6 panel, mỗi panel một model học phần: Naive Bayes Gauss, KNN, SVM tuyến tính, SVM RBF, cây quyết định, random forest. Hàng = nhãn STING thực tế, cột = nhãn dự báo; ô trên đường chéo là đoán đúng, ô ngoài đường chéo là FN/FP; màu đậm = nhiều tỉnh. Mỗi panel phải đọc kèm bối cảnh lớp: holdout có 11 tỉnh lớp 0 và 48 tỉnh lớp 1, nên model đoán thiên về 1 sẽ có accuracy cao mà vẫn sai nhiều ở lớp 0 — phải so đường chéo với 11 và 48, không chỉ nhìn màu. Hình không có majority và logistic regression; hai model đó nằm trong bảng số.
    - **Hỏi bẫy:** "Panel nào tốt nhất?" — Không chọn theo một hình: tiêu chí chọn là macro-F1 CV (câu 7 và câu 21); hình chỉ để đọc kiểu lỗi từng model.
    - **Repo:** `scripts/supervised/course_supervised_baselines.py:90-99, 339-394`; `results/course_supervised_baselines.md:26-28`.
    - **Bài giảng:** “Học có giám sát”, trang 31-33.

12. **Majority baseline là gì và repo tính ra sao?** — Baseline đa số đoán theo lớp xuất hiện nhiều nhất trong train của từng fold — không phải "always 1". Repo tính bằng `expanding_majority_f1`: CV macro-F1 0.228; holdout accuracy 0.186, macro-F1 0.157. Vì prevalence trôi, baseline mù thời gian "always 1" lại đạt 0.400 macro-F1, cao hơn majority — nên phải đối chiếu cả hai sàn. Con số 0.186 chính là 11/59: lớp đa số của train là 0 ở cả 6 fold, nên majority đoán 0 cho tất cả và chỉ đúng 11 tỉnh lớp 0.
    - **Hỏi bẫy:** "Baseline đa số có luôn đoán 1?" — Không; ở cả 6 fold, lớp đa số của train là 0, ngược với validation (luôn đa số 1).
    - **Repo:** `scripts/supervised/predict_supervised.py:236-251`; `results/supervised_metrics.csv:6`; `results/supervised_summary.md:31`; `results/course_supervised_baselines.md:28`.
    - **Bài giảng:** “Học có giám sát”, trang 30 (đo trên test set, không đo trên train).

13. **Precision và recall khác nhau thế nào?** — Precision = TP/(TP+FP), recall = TP/(TP+FN); đổi ngưỡng thì hai số đánh đổi nhau. Repo không xuất bảng precision/recall từng lớp; số tổng hợp đang có là accuracy và macro-F1 (ví dụ logistic regression holdout 0.644 / 0.541; NB 0.746 / 0.566). Muốn số từng lớp thì đọc bốn ô của confusion matrix trong `results/figs/course_confusion_matrix.png` rồi tính, hoặc chạy lại script để in ra — không đọc số từ trí nhớ.
    - **Hỏi bẫy:** "F1 là gì?" — Trung bình điều hòa của precision và recall; macro-F1 lấy trung bình đều hai lớp.
    - **Repo:** `scripts/supervised/predict_supervised.py:353-361, 463-478`; `results/course_supervised_baselines.csv:3,9`.
    - **Bài giảng:** “Học có giám sát”, trang 34.

14. **Vì sao scaler nằm trong Pipeline?** — Vì Pipeline biến "chuẩn hóa rồi huấn luyện" thành một khối: khi GridSearchCV chạy từng fold, nó chỉ fit `StandardScaler` trên phần train của fold đó rồi transform validation, và khi fit lần cuối trên train thì tham số scaler vẫn chỉ đến từ train — holdout 2024 chỉ được transform. Nếu fit scaler bên ngoài trước khi chia fold, mean/std của validation rò vào train, điểm CV sẽ lạc quan giả tạo. Trong code, NB/KNN/SVM/cây/logistic đều bọc `Pipeline([("sc", StandardScaler()), ("clf", ...)])`; random forest không bọc vì cây bất biến với scale từng chiều.
    - **Hỏi bẫy:** "Pipeline có đảm bảo không leakage tuyệt đối?" — Nó chặn leakage của bước tiền xử lý trong fold, nhưng không chặn leakage theo thời gian; phần thời gian do cách dựng cặp năm t → t+1 và STING fit ≤ cutoff đảm nhận.
    - **Repo:** `scripts/supervised/course_supervised_baselines.py:138-213, 239-267`; `results/course_supervised_baselines.md:6`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 9; trang 14.

## SVM, cây quyết định và rừng ngẫu nhiên

15. **Margin, siêu phẳng và support vector là gì?** — SVM tìm siêu phẳng tách hai lớp với lề lớn nhất; các điểm nằm sát lề hoặc vi phạm lề là support vector — bỏ chúng đi thì siêu phẳng đổi. Repo có huấn luyện SVM trong run so sánh học phần: SVM tuyến tính (chỉ quét C ∈ {0.1, 1, 10}) đạt macro-F1 CV 0.343, holdout accuracy 0.695, macro-F1 0.556.
    - **Hỏi bẫy:** "Mọi điểm đều là support vector?" — Không; chỉ các điểm trên/trong lề mới quyết định siêu phẳng.
    - **Repo:** `scripts/supervised/course_supervised_baselines.py:152-164`; `results/course_supervised_baselines.csv:5`.
    - **Bài giảng:** “SVM và cây quyết định”, trang 7-8.

16. **Kernel giải quyết vấn đề gì?** — Kernel thay tích vô hướng bằng hàm K(x, z), cho SVM học ranh giới phi tuyến trong không gian đặc trưng nhiều chiều mà không cần ánh xạ tường minh. Đề tài 1 của môn là "SVM Kernel"; repo có SVM RBF: macro-F1 CV 0.437, holdout accuracy 0.678, macro-F1 0.566. Chỉ quét C, để gamma mặc định `scale` — nên đây là một điểm RBF, không phải kết luận kernel nào tốt nhất.
    - **Hỏi bẫy:** "Kernel làm dữ liệu thành tuyến tính?" — Không; nó cho phép ranh giới phi tuyến trong không gian gốc.
    - **Repo:** `scripts/supervised/course_supervised_baselines.py:166-178`; `results/course_supervised_baselines.csv:6`.
    - **Bài giảng:** “Nhập môn học máy”, trang 12 (đề tài 1); “Học có giám sát”, trang 9 (agenda V. SVM Kernel).

17. **SVM RBF và SVM tuyến tính: số liệu nói gì, có nên chọn RBF?** — Trên CV, RBF hơn tuyến tính rõ: macro-F1 0.437 so với 0.343 — gợi ý ranh giới cong, nhưng đó là suy đoán từ số chứ chưa kiểm định. Trên holdout thì gần như hòa: macro-F1 0.566 so với 0.556, còn accuracy tuyến tính lại cao hơn (0.695 so với 0.678). Với 59 tỉnh, khác biệt này nằm trong nhiễu; ngoài ra chỉ quét C, không quét gamma, nên chưa phải so sánh kernel công bằng. Cả hai đều thấp hơn NB trên CV, nên không model SVM nào được chọn.
    - **Hỏi bẫy:** "RBF luôn hơn tuyến tính?" — Không; ở đây RBF hơn trên CV nhưng không hơn trên holdout accuracy, và một holdout không đủ để khẳng định.
    - **Repo:** `results/course_supervised_baselines.csv:5-6`; `results/course_supervised_baselines.md:31-35`; `scripts/supervised/course_supervised_baselines.py:152-178`.

18. **Vì sao SVM chuẩn chỉ làm bài hai lớp?** — Bài giảng nhấn: SVM chuẩn chỉ giải bài toán hai lớp; đa lớp phải chia thành nhiều bài nhị phân (one-vs-rest hoặc one-vs-one). Repo khớp sẵn: bài phân loại là nhị phân (0 = ngoại vi, 1 = vùng dày), còn k=3 của STING là cụm, không phải lớp cần SVM tách.
    - **Hỏi bẫy:** "3 cụm STING thì cần SVM 3 lớp?" — Không; cụm là đầu ra không giám sát, không phải nhãn phân loại.
    - **Repo:** `scripts/supervised/predict_supervised.py:92-96, 187-211`.
    - **Bài giảng:** “SVM và cây quyết định”, trang 16.

19. **Cây quyết định chọn thuộc tính bằng entropy và information gain thế nào?** — Cây chọn thuộc tính làm entropy giảm nhiều nhất: entropy đo lượng thông tin (sự kiện ít xác suất mang nhiều tin), gain = entropy trước − entropy sau khi chia. Bài giảng tính trên 14 bản ghi 9 yes/5 no, các nhánh 7-3 và 2-2. Repo có cây quyết định trong run học phần (quét `max_depth` ∈ {2,3,4,5}): macro-F1 CV 0.426, holdout accuracy 0.559 — thấp nhất trong 6 classifier học phần, macro-F1 0.508.
    - **Hỏi bẫy:** "Entropy vượt 1 được không?" — Với hai lớp, tối đa là 1 bit; 9-5 xấp xỉ 0.94.
    - **Repo:** `scripts/supervised/course_supervised_baselines.py:180-189`; `results/course_supervised_baselines.csv:7`.
    - **Bài giảng:** “SVM và cây quyết định”, trang 22-23 (ví dụ trang 23).

20. **Random forest hơn một cây ở đâu, repo dùng nó thế nào?** — Random forest dựng nhiều cây trên bootstrap và chọn ngẫu nhiên tập con đặc trưng, rồi bỏ phiếu hoặc lấy trung bình — giảm phương sai so với một cây. Repo dùng ở cả hai bài: hồi quy R² CV 0.197, MAE holdout 0.0616 (thấp hơn Ridge nhưng không được chọn vì CV thấp hơn); phân loại học phần macro-F1 CV 0.394, holdout accuracy 0.627, macro-F1 0.560. Con số phân loại trong pipeline công bố (CV 0.397, accuracy 0.678, macro-F1 0.600) cao hơn một chút vì cấu hình khác — 300 cây thay vì 50 cây; hai lần chạy đều thật, không phải mâu thuẫn.
    - **Hỏi bẫy:** "Random forest luôn thắng model tuyến tính?" — Không; bài hồi quy của repo chọn Ridge theo CV dù RF có MAE holdout thấp hơn, và bài phân loại RF thấp hơn NB trên CV.
    - **Repo:** `scripts/supervised/predict_supervised.py:277, 344`; `results/supervised_metrics.csv:5, 8`; `results/course_supervised_baselines.csv:8`; `scripts/supervised/course_supervised_baselines.py:191-199, 247-248`.
    - **Bài giảng:** “Học có giám sát”, trang 9 (agenda VII. Random Forest) — text trích xuất không có slide nội dung RF.

21. **Vì sao cây quyết định và random forest không được chọn?** — Quy tắc chọn đã đặt trước: model có macro-F1 CV cao nhất, không tính majority. Cây có CV 0.426 và holdout accuracy thấp nhất trong 6 classifier học phần (0.559); RF có CV 0.394 — thấp nhất trong 6 — dù holdout macro-F1 0.560 tốt hơn cây. Lý do: cây đơn chia theo trục nên phải xấp xỉ ranh giới mật độ cong bằng nhiều lát cắt bậc thang, dễ overfit với 738 cặp; RF lấy trung bình nhiều cây để giảm phương sai nhưng không sửa được bias chia theo trục. Cả hai đều dưới NB 0.514 nên không được chọn, dù RF có lúc nhỉnh hơn trên một holdout.
    - **Hỏi bẫy:** "Vậy cây vô dụng?" — Không; cây là baseline dễ giải thích và là nội dung môn học, nhưng không thắng tiêu chí CV ở bài này.
    - **Repo:** `results/course_supervised_baselines.md:8,23`; `results/course_supervised_baselines.csv:7-8`; `scripts/supervised/course_supervised_baselines.py:180-199`.

## Tiền xử lý dữ liệu

22. **Ba giai đoạn tiền xử lý theo thứ tự nào, repo kiểm chứng từng bước ra sao?** — Bài giảng: Cleaning → Integration → Transformation; mỗi bước Test → Decide, và phải định nghĩa bài toán/thuật toán trước. Repo có đúng thứ tự đó: notebook `notebooks/Nhom15_TienXuLy_PAPI.ipynb` triển khai chuỗi `PREPROCESSING_PIPELINE` 6 bước trực tiếp từ 14 workbook PAPI gốc, còn `scripts/data/preprocessing_audit.py` (chỉ đọc dữ liệu) đo trên panel/master thật rồi ghi `results/preprocessing_audit.md` theo bảng Test | Result | Decision | Evidence. Cleaning: trùng khóa → thiếu → nhất quán → ngoại lai CUỐI CÙNG; Integration: khóa nối, cardinality, số dòng, xung đột, rò rỉ scaler; Transformation: chuẩn hóa và đối chiếu số học tham số đóng băng.
    - **Hỏi bẫy:** "Audit có phải cổng chặn tự động?" — Không; nó ghi lại quyết định đang áp dụng kèm bằng chứng, còn chặn cứng nằm trong code build/predict (ví dụ lỗi khi trùng khóa). Nói đúng mức, không thổi phồng thành "pipeline tự kiểm định".
    - **Repo:** `notebooks/Nhom15_TienXuLy_PAPI.ipynb`; `scripts/notebooks/gen_preprocessing_notebook.py:365-447`; `scripts/data/preprocessing_audit.py:1-16, 369-453`; `results/preprocessing_audit.md:11-27, 89-107`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 5-6.

23. **Vì sao dedup phải làm đầu tiên, và audit đo được gì?** — Bản ghi trùng làm sai mọi thống kê phía sau: mean, tần suất, cả giá trị dùng để điền khuyết. Audit đo trên panel thật: 0 dòng trùng khóa / 882 dòng (882 khóa duy nhất), trùng toàn dòng cũng 0. Quyết định của pipeline: giữ đúng một dòng mỗi khóa và chặn cứng nếu phát hiện trùng — không tự xóa, để lỗi lộ ra. Đây là dedup theo khóa nghiệp vụ (province_code, year), không phải theo toàn bộ dòng.
    - **Hỏi bẫy:** "Sao không `drop_duplicates()` cả dòng?" — Hai dòng khác nhau một cột vẫn là cùng một tỉnh-năm; phải kiểm theo khóa.
    - **Repo:** `results/preprocessing_audit.md:19`; `scripts/data/build_external_master.py:139-140`; `scripts/supervised/predict_supervised.py:101-102`; `scripts/data/preprocessing_audit.py:65-69`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 7.

24. **Repo điền khuyết thế nào, audit nói gì?** — Bài giảng đặt imputation trong Cleaning nhưng yêu cầu Test → Decide và không dùng null. Audit đo: 4649/32634 ô chỉ tiêu bị thiếu (14.2%), trong đó 4284 ô nằm NGOÀI cửa sổ thu thập của cột nên là thiếu cấu trúc; chỉ 13/882 dòng thiếu chỉ tiêu trong cửa sổ (365 ô, thiếu `sd_4_2` hoặc `sd_6_1`). Quyết định: KHÔNG nội suy, không điền, giữ NaN; chỉ loại dòng khi dựng ma trận feature / ghép cặp (`PREPROCESSING_PIPELINE` 6 bước trong `notebooks/Nhom15_TienXuLy_PAPI.ipynb` cũng minh họa điền `SimpleImputer(median)` đẩy nhân tạo `11` dòng thiếu về trung vị `sd_4_2`: `7` dòng thiếu cả hai chỉ tiêu dồn vào ô trung tâm `(10, 10)`, `2` dòng vào `(10, 13)` và `2` dòng vào ô thưa `−1` làm nhiễu tăng `158 → 160`). Hơn nữa, kiểm chứng độ nhạy `results/preprocessing_sensitivity.csv` so biến thể A (`dropna`) với B (`SimpleImputer(median)` trong Pipeline từng fold) trên cùng CV 2017–2022 ở Ridge (`Δ = −0.015` < `cv_std(A) = 0.130`), Logistic Regression (`0.000 < 0.056`) và Gaussian Naive Bayes (`−0.002 < 0.120`) đều cho `|Δ| < cv_std(A)` (`không khác biệt`), bên cạnh ứng viên exploratory R4 (`SimpleImputer` median, chưa duyệt).
    - **Hỏi bẫy:** "Điền median cho đủ 63 tỉnh có sao?" — Tạo dữ liệu không có thật và làm sai mật độ cục bộ mà STING dùng để gán nhãn; 13 dòng bị loại là 1.5%, minh bạch hơn là bịa, và độ nhạy CV xác nhận giữ `NaN` không làm lệch kết quả mô hình.
    - **Repo:** `results/preprocessing_audit.md:20-21, 112-113`; `results/preprocessing_sensitivity.csv:1-10`; `scripts/data/preprocessing_sensitivity.py:174-205`; `notebooks/Nhom15_TienXuLy_PAPI.ipynb`; `scripts/notebooks/gen_preprocessing_notebook.py:310-364`; `scripts/data/preprocessing_audit.py:86-113`; `scripts/common/papi_pred_common.py:53-57`; `scripts/analysis/predict_demo.py:67-68`; `scripts/supervised/candidates_regression.py:172`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 7; trang 14.

25. **Vì sao outlier removal phải làm cuối, và repo xử lý ngoại lai thế nào?** — Vì nó phụ thuộc phân bố sau khi đã sửa lỗi và tích hợp; xóa sớm dễ xóa nhầm điểm hợp lệ. Audit đánh dấu |z| > 3 trên toàn panel: 122 ô (0.4%), 98 dòng, 29 cột — và GIỮ toàn bộ, chỉ đánh dấu. Trên hai chỉ tiêu STING, lưới tham chiếu 2011–2023 (`808` dòng) chỉ có 7 dòng `|z| > 3` (còn 151/158 điểm `−1` có `|z| ≤ 3`, năm 2024 có 13/13 tỉnh ô thưa với `max |z| = 2.1299`); bảng gộp 2011–2024 (`869` dòng) chỉ có 9 dòng `|z| > 3` (còn 162/171 điểm `−1` có `|z| ≤ 3`). Nếu xóa các dòng `|z| > 3` rồi dựng lại lưới thì khung `[min, max]` co lại vẫn tạo 197/801 điểm `−1` (24.6% trên 2011–2023) và 173/860 điểm `−1` (20.1% trên 2011–2024). Lý do: dữ liệu PAPI là điểm khảo sát thật trong thang hợp lệ `[0.25, 2.5]`, còn nhãn `−1` của STING là vùng thưa 2D theo `min_count`, không phải xóa dữ liệu bẩn.
    - **Hỏi bẫy:** "Nhiễu −1 có phải outlier?" — Không; −1 = ô không đủ `min_count` tại mức lưới đang dùng (hoặc ngoài vùng lưới đã học). Thêm nữa z trên toàn panel trộn bước nhảy thang đo 2021 ở một số cột khác; audit không kết luận tương đương thang đo xuyên năm.
    - **Repo:** `results/preprocessing_audit.md:26, 114`; `scripts/data/preprocessing_audit.py:261-290`; `src/sting.py:12-13, 151-155`; `results/predict_summary.md:48`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 7.

26. **Data leakage là gì và repo chặn ở đâu?** — Leakage là dùng thông tin không được phép có lúc dự đoán: dữ liệu tương lai, hoặc fit scaler/imputer trên test. Repo chặn bằng: scaler + STING chỉ fit trên lịch sử ≤ cutoff; biến đổi nằm trong Pipeline nên GridSearchCV refit từng fold; holdout 2023→2024 chấm một lần. Audit kiểm thêm: tham số scaler đóng băng khớp thống kê ≤2023 với Δmean = 0, Δscale = 0; nếu fit cả 869 dòng thì Δmean = 0.011456 nên sẽ không khớp JSON — tức không rò rỉ. Còn một điểm hở đã khai báo: `sd_6_1` vừa là target vừa là feature lag-1.
    - **Hỏi bẫy:** "Target năm t+1 thì có leakage không?" — Không gian lận thời gian, nhưng feature `sd_6_1` năm t là thông tin lag của chính target — phải nói rõ.
    - **Repo:** `results/preprocessing_audit.md:98`; `scripts/supervised/predict_supervised.py:153-169, 276-285`; `results/supervised_summary.md:33`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 8; trang 14.

27. **Vì sao scaler chỉ được fit trên train?** — Chuẩn hóa phải học mean/std trên train rồi áp cho test; fit trên toàn bộ là để phân bố test rò vào. Repo: `StandardScaler().fit(ptr)` với ptr = các năm ≤2023 rồi transform 2024; trong CV, scaler nằm trong Pipeline nên mỗi fold tự fit. Audit xác nhận tham số JSON tái lập đúng thống kê lịch sử với ddof=0 (ddof=1 lệch 1.13e-04). Lưu ý STING bất biến với biến đổi affine từng chiều, nhưng vẫn phải làm đúng để predict khớp.
    - **Hỏi bẫy:** "Z-score toàn panel có đổi cụm STING?" — Không, cùng một hệ trục thì chỉ đổi thang; đổi cụm xảy ra khi z theo từng năm (ARI non-noise 0.0060).
    - **Repo:** `scripts/analysis/predict_demo.py:64-72`; `scripts/supervised/predict_supervised.py:153-164`; `src/sting.py:95-99`; `results/preprocessing_audit.md:106-107`; `results/candidates_clustering.md:62`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 9; trang 14.

28. **"Test → Decide" áp dụng vào việc chọn cấu hình thế nào?** — Nghĩa là mỗi quyết định phải có bước kiểm rồi mới chốt, không quyết bằng cảm tính. Repo áp dụng ở chỗ quan trọng nhất: `scripts/analysis/predict_sweep.py` fit ≤2020, chấm trên tương lai giả 2021-2022, bộ lọc và hàm điểm đặt trước, năm 2024 không tham gia; kết quả ghi vào `models/predict_config.json` và đóng băng trước khi dự đoán. Cần nói kèm giới hạn: đúng hai năm 2021-2022 đó cũng là hai fold CV cuối của classifier, nên CV chỉ là khám phá (câu 29).
    - **Hỏi bẫy:** "Chấm xong thấy chưa đạt rồi đổi ngưỡng?" — Đó là selection-on-test; repo đóng băng ngưỡng trước khi chạy.
    - **Repo:** `scripts/analysis/predict_sweep.py:53-59, 110-113, 156-190`.
    - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 5.

## Câu bẫy hội đồng

29. **Chọn cấu hình STING trên 2021–2022 trùng hai fold CV cuối của classifier — vậy CV còn giá trị gì?** — Không còn là ước lượng generalization sạch, phải gọi đúng là khám phá. `predict_sweep.py` fit ≤2020 và chấm coverage trên đúng 2021-2022; classifier CV lại lấy validation ở 2017-2022, nên hai fold 2021, 2022 dùng pseudo-label do một cấu hình được chọn một phần nhờ chính hai năm đó. Hệ quả: macro-F1 CV (ví dụ LR 0.434, NB 0.514) hơi lạc quan. Phần sạch hơn là holdout 2023→2024: 2024 không tham gia chọn cấu hình và chỉ chấm một lần — nhưng vẫn chỉ một năm, 59 tỉnh, nên cũng không phải bằng chứng tổng quát hóa.
    - **Hỏi bẫy:** "Vậy bỏ CV?" — Không; CV dùng để so sánh tương đối các model dưới cùng một quy trình, chỉ không được phát biểu như hiệu năng kỳ vọng trên dữ liệu mới.
    - **Repo:** `scripts/analysis/predict_sweep.py:53-54, 111-113, 168`; `scripts/supervised/predict_supervised.py:73-74, 214-233`; `results/supervised_summary.md:30`; `results/course_supervised_baselines.md:7`.

30. **"External validation" của nhóm có chứng minh cụm đúng hoặc dự báo được không?** — Không. Đó là kiểm tra liên hệ với thước đo độc lập: PCI (khảo sát doanh nghiệp của VCCI, tách khỏi PAPI hộ dân) so với nhãn cụm trên 747 điểm 2011-2022 cho ANOVA F(3,743) = 9.04, p = 6.93e-06; Kruskal-Wallis p = 5.84e-07, eta² = 0.0352. Cụm 0 chỉ 5 tỉnh và cụm 1 chỉ 16 nên cặp đáng tin là nhiễu vs cụm 2. Nó nói cấu trúc cụm đồng biến với một thước đo chưa từng dùng khi học — quan hệ, không nhân quả; và không đo độ chính xác dự báo vì nhãn là pseudo-label. Kiểm tra Top-30 2023-2024 còn bị selection bias, p = 0.35, chỉ đọc như phụ.
    - **Hỏi bẫy:** "p nhỏ nghĩa là cụm có thật?" — Không; p nhỏ chỉ nói khác biệt PCI giữa nhóm khó do ngẫu nhiên, không nói nhãn đúng hay mô hình dự báo tốt.
    - **Repo:** `results/external_validation.md:17-19, 24, 32`; `scripts/analysis/external_validation.py:1-20`.

31. **Cài đặt của nhóm triển khai những phần nào của STING?** Mỗi ô lưu số điểm, trung bình, độ lệch chuẩn, cực trị và biên theo từng chiều. `cluster` gom các ô đạt ngưỡng tại một mức, với `significance_z` tắt trong phân tích PAPI chính. `query_top_down` duyệt từ mức thô và dùng phân phối chuẩn từng chiều để ước lượng xác suất cho việc tỉa nhánh. Bài gốc lưu thêm loại phân phối theo thuộc tính trong từng ô. [Chương 2 của báo cáo](../Nhom15_BaoCao_STING_PAPI.docx)
    - **Hỏi bẫy:** "Vậy có được ghi 'theo Wang et al. 1997'?" — Được, nhưng phải ghi là triển khai ý tưởng lưới thống kê phân cấp, kèm rõ phần lược bỏ; không được ngụ ý kết quả trùng bài gốc.
    - **Repo:** `src/sting.py:1-13, 39-51, 119-125, 130-136`; `reports/on-tap/qa_final.md:22-23`.

## Bổ sung — GV dễ hỏi (vấn đáp thêm)

32. **Vì sao không xóa ngoại lai khi audit đã gắn cờ 122 ô |z|>3?** — Bài giảng về tiền xử lý đặt kiểm tra ngoại lai ở cuối bước làm sạch vì phải biết phân bố sau dedup, thiếu và nhất quán; audit đo trên panel thật: 122 ô (0.4%), 98 dòng, 29 cột — quyết định GIỮ toàn bộ, chỉ đánh dấu, không xóa. Điểm PAPI là khảo sát thật trong thang hợp lệ; cắt 122 ô làm méo thống kê panel 882×41. Hơn nữa thực nghiệm trên hai trục STING (`sd_4_2`, `sd_6_1`) trong `notebooks/Nhom15_TienXuLy_PAPI.ipynb` chứng minh: trên `2011–2023` chỉ có 7/808 điểm `|z| > 3` còn 151/158 điểm nhiễu `−1` có `|z| ≤ 3` (và 13/13 tỉnh ô thưa 2024 có `|z| ≤ 2.1299`); trên bảng gộp `2011–2024` chỉ có 9/869 điểm `|z| > 3` còn 162/171 điểm nhiễu `−1` có `|z| ≤ 3`. Nếu bỏ hết điểm `|z| > 3` rồi dựng lại lưới thì khung `[min, max]` co lại vẫn tạo 197/801 điểm `−1` (24.6% trên 2011–2023) và 173/860 điểm `−1` (20.1% trên 2011–2024). Kiểm chứng độ nhạy `results/preprocessing_sensitivity.csv` (biến thể C winsorize `|z| ≤ 3` theo fold-train) cũng cho `|Δ| < cv_std(A)` trên cả Ridge (`−0.001 < 0.130`), LR (`−0.014 < 0.056`) và GNB (`−0.001 < 0.120`). Lý do: dữ liệu PAPI là điểm khảo sát thật trong thang hợp lệ `[0.25, 2.5]`, còn nhãn `−1` của STING là vùng thưa 2D theo `min_count`, không phải xóa dữ liệu bẩn.
   - **Hỏi bẫy:** "122 ô >3 sigma thì bắt buộc cắt theo slide?" — Không; slide yêu cầu Test → Decide, và audit ghi rõ z-score gộp toàn panel nên cờ chỉ mang tính mô tả; cắt `|z| > 3` cũng không làm hết nhãn `−1` của STING.
   - **Repo:** `results/preprocessing_audit.md:15,26,114`; `results/preprocessing_sensitivity.csv:1-10`; `scripts/notebooks/gen_preprocessing_notebook.py:261-271,310-364`; `scripts/data/preprocessing_audit.py:261-290`; `src/sting.py:12-13`.
   - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 7.

33. **Vì sao `dropna` thay vì imputation, và khi nào imputation hợp lý?** — Audit: 4649/32634 ô thiếu trong 37 chỉ tiêu (14.2%), trong đó 4284 ô nằm NGOÀI cửa sổ thu thập của cột — thiếu cấu trúc, không phải ngẫu nhiên để median "vá". Chỉ 13/882 dòng (1.5%) thiếu trong cửa sổ (365 ô trên `sd_4_2` hoặc `sd_6_1`). Pipeline chính (`PREPROCESSING_PIPELINE` 6 bước trong `notebooks/Nhom15_TienXuLy_PAPI.ipynb`): không nội suy, `dropna` khi ghép cặp và `year_frame` — minh bạch hơn tạo giá trị không có trong khảo sát. Thử nghiệm độ nhạy trong `results/preprocessing_sensitivity.csv` cho thấy khi thay `dropna` (A) bằng `SimpleImputer(median)` (B) hay winsorize `|z| ≤ 3` (C) trên Ridge, Logistic Regression và Gaussian Naive Bayes, mọi chênh lệch CV đều nhỏ hơn độ lệch chuẩn giữa các fold (`|Δ| < cv_std(A)` — tối đa `|−0.015| < 0.130`). Imputation hợp lý khi đã Test → Decide trên thiếu ngẫu nhiên, quy mô lớn và không làm sai mật độ cục bộ STING — như kiểm chứng tham khảo ở biến thể B (`scripts/data/preprocessing_sensitivity.py`) và ứng viên R4 (`candidates_regression.py`), không cần đưa vào pipeline công bố.
   - **Hỏi bẫy:** "Khi nào cần điền giá trị thiếu?" — Imputation nằm trong khung Cleaning, nhưng cùng slide yêu cầu Test → Decide; repo có bảng audit, notebook `Nhom15_TienXuLy_PAPI.ipynb` và `results/preprocessing_sensitivity.csv` chứng minh quyết định không điền.
   - **Repo:** `results/preprocessing_audit.md:20-21,112-113`; `results/preprocessing_sensitivity.csv:1-10`; `results/preprocessing_sensitivity.md:1-16`; `scripts/data/preprocessing_sensitivity.py:174-205`; `notebooks/Nhom15_TienXuLy_PAPI.ipynb`; `scripts/notebooks/gen_preprocessing_notebook.py:310-364,370-405`; `scripts/common/papi_pred_common.py:53-57`; `scripts/supervised/predict_supervised.py:106`; `scripts/supervised/candidates_regression.py:172`.
   - **Bài giảng:** “Tiền xử lý dữ liệu”, trang 7; trang 14.

34. **Vì sao Naive Bayes macro-F1 CV 0.514 cao nhất mà vẫn không kết luận "NB tốt nhất"?** — Theo quy tắc chọn pipeline vẫn lấy gaussian naive bayes vì `value_cv` lớn nhất, nhưng khoảng cách tới hạng hai (KNN 0.486) chỉ 0.028, nhỏ hơn `cv_std` của NB là 0.120 trên 6 fold — biến động giữa các fold lớn hơn gap giữa hai model đầu. Holdout macro-F1 NB 0.566 ngang SVM RBF 0.566; tất cả số đó là đồng thuận với pseudo-label STING, không ground truth. "Tốt nhất" ngụ ý vượt trội có ý nghĩa; repo chỉ được nói đứng đầu theo tiêu chí CV đã chốt và phải nói kèm giới hạn thống kê.
   - **Hỏi bẫy:** "0.514 > 0.486 là thắng rõ ràng?" — Không; `results/course_supervised_baselines.md:24` ghi gap 0.028 < cv_std 0.120 → thứ hạng mô tả, không khẳng định vượt trội.
   - **Repo:** `results/course_supervised_baselines.csv:3-4`; `results/course_supervised_baselines.md:23-24`; `scripts/supervised/course_supervised_baselines.py:374-377`.
   - **Bài giảng:** “Học có giám sát”, trang 30-34 (đánh giá) — cv_std là chuẩn tự đặt của repo.

35. **Pseudo-label có vòng lặp nhãn không, và điều đó giới hạn kết luận thế nào?** — Có phụ thuộc vòng: cấu hình STING đóng băng (`predict_sweep.py` fit ≤2020, chấm coverage trên 2021–2022) → `build_classification_pairs` fit STING/scaler ≤t để gán nhãn tỉnh năm t+1 (`y = int(labels[pc] != -1)`, 738 cặp train) → classifier học khớp lại quy tắc "vùng dày vs ngoại vi" do chính STING sinh → macro-F1 đo mức khớp, không đúng/sai xã hội. Thêm vòng chọn cấu hình: hai năm 2021–2022 dùng trong sweep trùng hai fold CV cuối của classifier (`results/supervised_summary.md:30`) nên macro-F1 CV hơi lạc quan. Giới hạn: chỉ so sánh model A vs B dưới cùng protocol và cùng pseudo-label; không suy ra dự báo thực tế, không gọi là học bán giám sát, không dùng holdout để chọn sau khi đã thấy điểm.
   - **Hỏi bẫy:** "CV 0.514 chứng minh dự báo tốt?" — Không; nhãn y do STING tại từng cutoff tạo ra, classifier chỉ học tái hiện nhãn đó.
   - **Repo:** `scripts/supervised/predict_supervised.py:92-96,187-211`; `scripts/analysis/predict_sweep.py:53-54,110-113`; `results/supervised_summary.md:29-30`; `results/course_supervised_baselines.md:4,37`.
   - **Bài giảng:** “Nhập môn học máy”, trang 36 (semi-supervised khác pseudo-label).

36. **STING khác DBSCAN và K-Means ở điểm nào (đề tài 6)?** — STING chia không gian thành lưới phân cấp, mỗi ô giữ thống kê (count/mean/std) và gom các ô "dày" (`count >= min_count`) liền kề; số cụm k là đầu ra của mật độ lưới, không phải tham số bắt buộc như K-Means. K-Means phải chọn k trước và luôn gán mọi điểm vào cụm (noise_ratio 0.0 trong pooled `results/metrics.csv`). DBSCAN dựa mật độ điểm + bán kính `eps`, cũng có nhãn nhiễu. Trên panel pooled 2011–2023: STING đóng băng k=3, noise 0.196; DBSCAN eps=0.2 noise 0.142, ARI so với STING 0.647; k-means k=2 ARI 0.166 — ba phương pháp phân vùng khác nhau, đề 6 bắt grid-based.
   - **Hỏi bẫy:** "K-Means k=3 cho cùng k=3 với STING?" — Không; STING k=3 từ lưới min_count=5, k-means k=3 ARI_vs_sting chỉ 0.139.
   - **Repo:** `src/sting.py:8-13`; `results/metrics.csv:2-4,7`; `README.md:10`.
   - **Bài giảng:** “Nhập môn học máy”, trang 12 (đề 6 grid-based; K-Means/DBSCAN là đề khác).

37. **Vì sao ưu tiên macro-F1 thay vì accuracy khi holdout mất cân 11/48?** — Holdout một lần 2023→2024 có 59 tỉnh: lớp 0 (ngoại vi STING) = 11, lớp 1 (vùng dày) = 48 — tỉ lệ 48/59 ≈ 0.814. Chiến lược luôn đoán 1 đạt accuracy 0.814 trong khi bỏ hết 11 tỉnh lớp 0. NB có accuracy holdout 0.746 (cao hơn majority 0.186) nhưng macro-F1 0.566 phản ánh cả hai lớp; majority macro-F1 chỉ 0.157. Macro-F1 là trung bình F1 từng lớp nên phạt bỏ rơi lớp thiểu số — nên cần đọc cùng ma trận nhầm lẫn để biết mô hình bỏ sót lớp nào. CV cũng chọn theo macro-F1 vì prevalence nhãn 1 trôi từ 0.000 (2011) đến 0.917 (2021).
   - **Hỏi bẫy:** "Accuracy 0.746 là rất cao?" — Cao hơn majority nhưng thấp hơn luôn-đoán-1 (0.814); phải đọc macro-F1 và `results/figs/course_confusion_matrix.png`.
   - **Repo:** `results/course_supervised_baselines.md:28-29`; `results/course_supervised_baselines.csv:2-3`; `results/supervised_summary.md:31`; `scripts/supervised/course_supervised_baselines.py:65-68`.
   - **Bài giảng:** “Học có giám sát”, trang 30-34.

38. **Điểm classifier cao hơn chance thế nào, và bao nhiêu là drift theo năm?** — Phân tích thăm dò `scripts/supervised/classifier_label_baselines.py` (không thay bảng primary): (1) hoán vị nhãn **train** mỗi fold 200 lần (seed 42) với siêu tham số cố định từ GridSearchCV đã công bố — macro-F1 quan sát (NB 0.514, KNN 0.486, LR 0.434) cao hơn hầu hết hoán vị (perm mean ~0.23–0.34; empirical p = 0.005 = 1/200); (2) model chỉ dùng `year_t` hoặc prevalence nhãn năm *t−1* đạt ~0.38–0.40, nên phần lớn điểm vẫn gắn drift thời gian; (3) NB thắng KNN ở 4/6 fold (mean paired diff 0.028) — sáu fold không đủ để khẳng định ý nghĩa. Holdout không dùng trong script này.
   - **Hỏi bẫy:** "p=0.005 chứng minh model tốt?" — Chỉ nói điểm quan sát cao hơn phân phối hoán vị nhãn train dưới cùng feature/năm; vẫn là khớp pseudo-label STING + drift năm, không ground truth xã hội.
   - **Repo:** `results/classifier_label_baselines.md`; `results/classifier_label_baselines.csv`; `scripts/supervised/classifier_label_baselines.py`.
   - **Bài giảng:** “Học có giám sát”, trang 30-34 (đánh giá / baseline).


## Phân cụm và đánh giá kết quả

39. **Không có nhãn chuẩn, đánh giá clustering thế nào?** — Trang 25 của bài giảng về phân cụm phân biệt goodness of fit với accuracy/precision/recall của supervised. Nhóm dùng silhouette/DB/CH kèm k, cỡ cụm và noise; ARI synthetic có nhãn thật, ARI PAPI chỉ đo đồng thuận hai phân hoạch. Accuracy của classifier không phải accuracy xã hội của STING.
   - **Repo:** `results/metrics.csv`; `notebooks/Nhom15_STING_PAPI.ipynb`.
   - **Bài giảng:** “Phân cụm”, tr.25–31.

40. **WCSS nhỏ nhất có phải k tốt nhất?** — WCSS = tổng bình phương khoảng cách từ điểm tới centroid cụm; tăng k làm giá trị tối ưu không tăng, k=n cho WCSS=0. Elbow tìm điểm lợi ích giảm dần, không chứng minh số nhóm xã hội thật. Không bỏ noise rồi so tổng WCSS giữa các phương pháp trên tập điểm khác nhau.
   - **Repo:** `scripts/analysis/run_analysis.py`; `results/metrics.csv`.
   - **Bài giảng:** “Phân cụm”, tr.27–31.

41. **Hierarchy của STING có phải HC/dendrogram?** — Không: STING chia không gian thành ô lồng nhau; agglomerative HC bắt đầu mỗi điểm là một cụm rồi ghép cặp cụm gần nhau theo linkage. Dendrogram ghi thứ tự/khoảng cách ghép. Bản nhóm chọn một mức lưới để gom ô dày, không xây dendrogram HC.
   - **Repo:** `src/sting.py`; `notebooks/Nhom15_STING_PAPI.ipynb`.
   - **Bài giảng:** “Phân cụm”, tr.32–47.

42. **Mô tả thế nào khi thầy hỏi phạm vi triển khai STING?** Nhóm cài đặt lưới thống kê nhiều mức, gom các ô dày liền kề và minh họa truy vấn từ trên xuống ở notebook. Phần truy vấn dùng một mô hình xác suất chuẩn theo từng chiều. Kết quả PAPI được báo cáo theo cấu hình lưới, ngưỡng số điểm và hai chỉ tiêu mà nhóm đã kiểm tra. [Notebook thống nhất](../../notebooks/Nhom15_STING_PAPI.ipynb)
   - **Repo:** `src/sting.py`; `scripts/deliverables/build_report.py`; `notebooks/Nhom15_STING_PAPI.ipynb`.
   - **Nguồn gốc:** Wang, Yang & Muntz (1997), https://www.vldb.org/conf/1997/P186.PDF.

43. **Có thiếu dataset vì model chỉ dùng hai feature?** — Dataset chính có 882 dòng, 41 cột, trong đó 37 chỉ tiêu (không tính mã tỉnh/năm). Ngưỡng >=500×10 áp dụng dataset theo yêu cầu môn hiện có. Không ép dùng mọi cột: hai feature cho clustering và tám feature hồi quy do protocol đã công bố; d7/d8 thiếu lịch sử và một số thang thay đổi. 2024 có 61/63 tỉnh đủ feature, hai tỉnh thiếu giữ thiếu.
   - **Repo:** `data/processed/papi_panel_scale_metadata.csv`; `scripts/data/check_data.py`; `models/predict_config.json`.
   - **Bài giảng:** Bài giảng nhập môn học máy ghi yêu cầu về quy mô dữ liệu. Bài giảng về phân cụm có bài tập riêng trên dữ liệu tổng hợp.

44. **Bài tập trang 48 có phải bổ sung cho đồ án nhóm?** — Trang ghi Homework (indv.): dữ liệu tổng hợp hai cột, KMeans, HC, dendrogram. Đây là bài cá nhân riêng trong PDF; không có yêu cầu trong trang đó thay đề tài nhóm STING hay thêm dataset thật. Hỏi lại GV nếu có chỉ dẫn miệng khác; không đưa bài cá nhân thành kết quả nghiên cứu nhóm.
   - **Repo:** `reports/course_requirements.md`.
   - **Bài giảng:** “Phân cụm”, tr.48; bản PDF lưu local tại `data/raw/course/bai-giang-phan-cum.pdf`, không đưa vào ZIP.

45. **Vì sao chưa kết luận nghèo khác nhau giữa noise và cụm lớn?** — Mann–Whitney trong artifact hiện tại: thô p=0.767, trừ median năm p=0.269; cả hai >0.05. Kruskal–Wallis sau tách năm có tín hiệu trên toàn bộ nhóm nhưng hai cụm nhỏ n=2/10: không thay kết luận cặp noise-vs-cụm2. Đây là kiểm chứng bổ trợ; tỉnh lặp qua năm còn làm giả định độc lập của kiểm định gộp hạn chế.
   - **Repo:** `results/poverty_validation.csv`; `results/poverty_validation.md`.

46. **Bẫy khởi tạo xấu (TRAP!) của K-Means khác gì các bẫy cấu hình của STING?** — Các trang 19–24 của bài giảng về phân cụm minh họa K-Means chọn tâm ban đầu tệ sẽ kẹt ở cực tiểu địa phương, trong khi STING không phụ thuộc ngẫu nhiên nhưng có 3 bẫy riêng trên đồ thị 2D: (i) xóa điểm `|z| > 3` làm co biên `[min, max]` khiến lưới dịch và nhiễu tăng (`19.7% → 20.1%` / `19.6% → 24.6%`); (ii) đặt lưới quá mịn với `min_count` cao biến đa số điểm thành `−1`; (iii) đổi sang kề 8 hướng (`connectivity=2`) chỉ gộp cụm qua góc thành `1` cụm mà không giảm 1 điểm nhiễu nào.
   - **Hỏi bẫy:** "STING không bị ngẫu nhiên nên không bao giờ ra kết quả dở?" — Sai; chọn sai `min_count`, độ mịn hoặc biên lưới vẫn tạo cấu trúc méo hoặc 100% nhiễu.
   - **Repo:** `scripts/common/midterm_clustering.py:308-370`; `scripts/notebooks/gen_final_analysis.py:474-522`.
   - **Bài giảng:** “Phân cụm”, tr.19–24 (TRAP).

47. **Bốn khoảng cách Linkage của Hierarchical Clustering và mẹo cắt Dendrogram hoạt động thế nào?** — Agglomerative bắt đầu mỗi điểm một cụm rồi ghép dần từ dưới lên theo `#1 Closest points (Single)`, `#2 Furthest points (Complete)`, `#3 Centroid distance`, hoặc `#4 Average distance` (cùng `Ward` trong thực nghiệm); Dendrogram ghi độ cao ghép dần và trang 47 của bài giảng về phân cụm minh họa cách cắt ngang tại khoảng trống chiều cao lớn nhất. Bản STING của nhóm không xây Dendrogram HC mà nối ô dày ở đúng một mức lưới chọn trước.
   - **Hỏi bẫy:** "Single linkage luôn tốt nhất?" — Không; Single dễ bị hiện tượng dây xích nối bắc cầu qua vài điểm lẻ, còn Complete/Ward tạo cụm gọn hơn.
   - **Repo:** `scripts/common/midterm_clustering.py`; `src/sting.py:1-13`.
   - **Bài giảng:** “Phân cụm”, tr.32–47 (bốn linkage tr.35, cắt dendrogram tr.47).

## Hồi quy tuyến tính, đa thức và logistic

48. **OLS tính hệ số và tối ưu sai số thế nào, khác Ridge của repo ở đâu?** — Linear Regression giả định $y = X\beta + \beta_0 + \varepsilon$, cực tiểu hóa tổng bình phương các đoạn phần dư dọc $\sum \varepsilon_i^2$ để thu nghiệm đóng $\hat{\beta} = (X^T X)^{-1} X^T y$. Khi áp dụng lên 8 chỉ tiêu PAPI có tương quan với nhau, repo dùng `Ridge` (OLS + phạt $L_2 = \alpha \|\mathbf{w}\|_2^2$) bọc trong `Pipeline([('sc', StandardScaler()), ...])` đạt CV $R^2 = 0.265$ và holdout MAE `0.0640` cho chỉ tiêu `6.1`.
   - **Hỏi bẫy:** "Ridge có thay đổi phần dư trên tập train thành 0?" — Không; phạt $L_2$ thu nhỏ hệ số để chống quá khớp trên mẫu mới thay vì ép lỗi train nhỏ nhất.
   - **Repo:** `scripts/supervised/predict_supervised.py:274-287,322-323`; `results/supervised_metrics.csv:4`.
   - **Bài giảng:** “Hồi quy”, tr.3–12 (residuals & OLS).

49. **Polynomial Regression xử lý quan hệ phi tuyến ra sao, vì sao repo không dùng đa thức bậc cao trên PAPI?** — Slide tạo ma trận thiết kế bậc $m$: $X' = [1, x, x^2, \dots, x^m]$ ($m \le n$) rồi giải $\hat{\beta} = (X'^T X')^{-1} X'^T y$. Khi $m = n - 1$ (như $m = 5$ trên 6 điểm tr.19), đường cong đi qua mọi điểm với MSE train `= 0` nhưng dao động gắt (overfit). Trên ~738 cặp PAPI với 8 chỉ tiêu, các mô hình phi tuyến (`RF`, `HGB`) đều thua `Ridge` theo CV $R^2$ (`0.265`), nên giữ mô hình tuyến tính điều chuẩn.
   - **Hỏi bẫy:** "Tăng bậc đa thức luôn cải thiện dự báo?" — Sai; chỉ giảm sai số train trong khi phương sai trên holdout tăng mạnh.
   - **Repo:** `scripts/notebooks/gen_final_analysis.py:662-685`; `results/supervised_metrics.csv:4-5`.
   - **Bài giảng:** “Hồi quy”, tr.13–14, 19.

50. **Logistic Regression phân loại qua Sigmoid và Binary Cross-Entropy thế nào?** — Thay vì xuất số thực không chặn, Logistic đưa logit tuyến tính $z = \beta_0 + \mathbf{w}^T \mathbf{x}$ qua Sigmoid $f(z) = \frac{1}{1 + e^{-z}} \in (0, 1)$, tối đa hóa Bernoulli likelihood $\prod f_i^{y_i}(1-f_i)^{1-y_i}$ — tương đương tối thiểu **Binary Cross-Entropy (Log Loss)** $L_{\text{BCE}} = -\frac{1}{M}\sum [y_i \ln f_i + (1-y_i)\ln(1-f_i)]$. Trên holdout 59 tỉnh (`0 = nhiễu`, `1 = vùng dày`), model đạt `BCE = 0.7059`, Accuracy `0.644`, Macro-F1 `0.541`.
   - **Hỏi bẫy:** "Có thể dùng MSE cho Logistic Regression thay Log Loss?" — Rất dở: với Sigmoid, MSE không lồi và gradient rất nhỏ khi đoán tự tin sai, còn Log Loss phạt logarit tiến tới $+\infty$.
   - **Repo:** `scripts/supervised/predict_supervised.py:338-363`; `results/supervised_metrics.csv:7`; `scripts/notebooks/gen_final_analysis.py:687-715`.
   - **Bài giảng:** “Hồi quy”, tr.15–18.

51. **Vì sao Linear/OLS có nghiệm đóng còn Logistic Regression phải tối ưu lặp (`max_iter=3000`)?** — Ở OLS, đạo hàm của $\sum (y_i - \mathbf{x}_i^T \beta)^2$ là hệ phương trình tuyến tính theo $\beta$ nên giải thẳng $(X^T X)^{-1} X^T y$. Ở Binary Cross-Entropy, dự báo chứa hàm phi tuyến $f(z) = \frac{1}{1+e^{-z}}$ nên phương trình $\nabla L = 0$ không có nghiệm đóng đại số, scikit-learn phải lặp gradient/Newton (`max_iter=3000`) tới cực tiểu lồi.
   - **Hỏi bẫy:** "Tăng `max_iter=3000` có làm model học nhiều hơn để overfit?" — Không; khi đã hội tụ nghiệm cực tiểu lồi duy nhất của Binary Cross-Entropy (+ phạt L2 mặc định), các bước dư không chạy thêm.
   - **Repo:** `scripts/supervised/predict_supervised.py:274,338-340`; `scripts/notebooks/gen_final_analysis.py:687-715`.
   - **Bài giảng:** “Hồi quy”, tr.10–12, 16–18.

52. **Vì sao Ridge giảm MAE hồi quy điểm nhưng chiếu lên lưới STING vẫn bỏ sót 11/11 tỉnh nhiễu?** — Hồi quy bình phương tối thiểu/Ridge ước lượng kỳ vọng có điều kiện $\mathbb{E}[y \mid x]$, vốn co các dự báo về vùng trung tâm phân bố (*regression to the mean*). Vùng trung tâm đó trùng khít 52 ô dày cụm lớn của STING, nên cả `59/59` điểm dự báo rơi vào cụm lớn (`balanced_zone_accuracy = 0.50`). Để nhận diện vùng thưa, repo kết hợp thêm 364 cặp sai số lịch sử để xếp hạng rủi ro (AUC `0.816`).
   - **Hỏi bẫy:** "Vậy dùng Random Forest regressor thay Ridge thì có bắt được 11 tỉnh nhiễu?" — Phần lớn vẫn co về trung tâm; muốn bắt lớp `0` trực tiếp phải dự báo xác suất/xếp hạng với cân bằng lớp (`class_weight='balanced'`), không lấy mỗi dự báo điểm kỳ vọng.
   - **Repo:** `results/papi_forecast_2024.json:49-87,100-105`; `scripts/common/papi_forecast.py:1-28`.
   - **Bài giảng:** “Hồi quy”, tr.5–8 (kỳ vọng & phần dư); đối chiếu mục mật độ ở biên trong bài giảng về phân cụm.

## Chuyên sâu về nhiễu (−1) trong STING — 6 câu hỏi hay bị vặn nhất

53. **Vì sao sau tiền xử lý vẫn còn 19,7% (171/869) và 19,6% (158/808) điểm nhiễu −1?** — Tiền xử lý chỉ làm sạch bản ghi thiếu (`dropna` loại `11/819` năm `2011–2023` và `2/63` năm `2024`, giữ `869` dòng đủ 2 chỉ tiêu trong khoảng hợp lệ `[0.25, 2.5]`). Còn nhãn `−1` của STING là **đầu ra của thuật toán phân cụm dựa trên mật độ ô 2D**: điểm nào rơi vào ô lưới `16 × 16` có dưới `5` quan sát tham chiếu thì nhận `−1`, hoàn toàn không phải dữ liệu lỗi bị bỏ sót.
   - **Hỏi bẫy:** "Vậy nói 19,7% dữ liệu là dữ liệu rác chưa sạch đúng không?" — Sai hoàn toàn; `162/171` điểm `−1` (và `151/158` trên `2011–2023`) đều nằm gọn trong khung sạch `|z| ≤ 3`.
    - **Repo:** `results/preprocessing_audit.md:19-26`; `scripts/notebooks/gen_final_analysis.py:374-395`.

54. **Nếu xóa hết các điểm `|z| > 3` rồi chạy lại STING thì có hết nhãn −1 không?** — Không — ngược lại tỷ lệ nhiễu còn **tăng thêm**. Lý do: STING tự chia lưới đều trên hộp bao `[min, max]` của dữ liệu đưa vào. Khi bỏ `7` điểm `|z| > 3` trên `2011–2023` (`808 → 801`), khung `[min, max]` bị co hẹp, kích thước từng ô lưới nhỏ lại và đường chia ô dịch chuyển, làm số điểm rơi vào ô thưa tăng từ `158/808 (19,6%)` lên `197/801 (24,6%)` (`4` cụm); trên `869 → 860` cũng tăng từ `171/869 (19,7%)` lên `173/860 (20,1%)`.
   - **Hỏi bẫy:** "Co ô lại nhỏ hơn thì điểm không đáng ra phải cụm chặt hơn sao?" — Ô nhỏ hơn lại chứa ít điểm hơn trên mỗi ô nên càng dễ rớt xuống dưới ngưỡng `min_count = 5`!
    - **Repo:** `scripts/notebooks/gen_final_analysis.py:386-395`; `scripts/common/midterm_clustering.py:308-399`.

55. **Đổi quy tắc kề 8 hướng (`connectivity=2`) có giảm được nhiễu không; muốn giảm nhiễu thì đổi gì?** — Đổi `connectivity=2` (cho nối chéo góc) **không giảm bất kỳ một điểm nhiễu nào** (`158/808` trên `2011–2023` và `171/869` trên `2011–2024` giữ nguyên tuyệt đối), chỉ gộp `56` ô dày từ `3` cụm thành `1` cụm duy nhất vì chạm góc. Nhiễu chỉ thay đổi khi đổi tiêu chí "ô dày": hạ `min_count` (ví dụ `5 → 3` giảm nhiễu còn `9,8%`), giảm `cluster_level` (`2 → 1`, lưới `4 × 4` giảm nhiễu còn `0,7%`), hoặc thay đổi `factor`.
   - **Hỏi bẫy:** "Lý do không giảm nhiễu là gì trong code?" — Vì `dense_set` chỉ lọc theo `count >= min_count`, còn `connectivity` chỉ chạy DFS nối các ô đã có trong `dense_set`.
    - **Repo:** `src/sting.py:133-168`; `scripts/notebooks/gen_final_analysis.py:508-522`.

56. **Trong 13 tỉnh nhãn −1 năm 2024, có tỉnh nào bị `outside_grid` (tràn biên) hoặc `|z| > 3` không?** — Không một tỉnh nào: `0/61` tỉnh năm `2024` có `|z| > 3` và `0` tỉnh `outside_grid`. Cả `13/13` tỉnh nhãn `−1` đều nằm trọn trong miền lưới tham chiếu `2011–2023`, với `|z|` lớn nhất trên cả hai trục chỉ là `2,1299` (Tây Ninh), và nhận nhãn `−1` thuần túy vì rơi vào ô thưa (`sparse_cell`) có từ `0` đến `3` quan sát tham chiếu (`< 5`).
   - **Hỏi bẫy:** "Đoán xem tỉnh nào có `reference_count = 0`?" — Quảng Ninh (`sd_4_2 = 2,2598; sd_6_1 = 1,8891`, ô `(14, 9)` chưa từng có điểm tham chiếu nào `2011–2023`).
    - **Repo:** `results/papi_observed_grid_2024.csv:1-64`; `scripts/notebooks/gen_final_analysis.py:539-555`.

57. **Nhãn nhiễu `−1` có đồng nghĩa tỉnh quản trị yếu kém không?** — Không. Phân tích CSV gán năm 2024 cho thấy 13 tỉnh `sparse_cell` đứng ở hai nhóm rìa đối lập nhau: nhóm đạt **điểm rất cao** ở rìa phải/trên (Tây Ninh `4.2 = 2,285`, Quảng Ninh `4.2 = 2,260`, Bà Rịa - Vũng Tàu `4.2 = 2,258`, Sóc Trăng `4.2 = 2,252`, Bình Thuận `4.2 = 2,218; 6.1 = 2,112`, Hà Tĩnh `6.1 = 2,191`) và nhóm điểm `6.1` thấp hơn ở rìa dưới (Hà Nội `1,686`, Cần Thơ `1,698`). Nhãn `−1` chỉ có nghĩa *"nằm ngoài vùng tập trung phổ biến 2011–2023"*, không gắn phán xét tốt/xấu.
   - **Hỏi bẫy:** "Hà Nội hay Quảng Ninh cũng bị −1 à?" — Đúng; Hà Nội (ô `(10, 5)`, `3` điểm) và Quảng Ninh (ô `(14, 9)`, `0` điểm) đều đủ dữ liệu hợp lệ nhưng thuộc 2 cực khác nhau trên mặt phẳng PAPI 2024.
    - **Repo:** `results/papi_observed_grid_2024.csv:2,15,29,40,47,50,60,62`; `results/stakeholder_summary.md:1-42`; `scripts/notebooks/gen_final_analysis.py:569-595`.

58. **Điểm nhiễu `−1` ảnh hưởng thế nào khi tính WCSS, Silhouette và ARI để so với K-Means và DBSCAN?** — K-Means không tạo nhiễu nên WCSS và Silhouette tính trên đủ `100%` điểm (`808` hoặc `869`). STING (`−1 = 158/808`) và DBSCAN (`−1 = 115/808`) loại các điểm rìa thưa nên Silhouette trên tập riêng của mỗi thuật toán trông cao/thấp khác nhau không cùng mẫu số. Vì vậy nhóm khóa thêm **hai quy tắc bắt buộc**: (i) tính Silhouette lại trên **cùng tập giao** được tất cả thuật toán gán cụm (`631/808` hoặc `680/869` điểm), và (ii) khi đọc ARI phải nói rõ tính trên toàn mẫu gồm nhãn `−1` (`0,647`) hay chỉ trên tập giao không nhiễu (`0,431`).
   - **Hỏi bẫy:** "Nếu dùng Silhouette cao hơn (`0,445` vs `0,361`) để kết luận K-Means thắng STING có được không?" — Không; hai con số đó đo trên hai hình học khác nhau (`808` vs `650` điểm) và K-Means ép mọi điểm rìa vào tâm thay vì giữ mục tiêu phát hiện vùng dày/ngoại vi của grid-based clustering.
    - **Repo:** `results/metrics.csv:2-7`; `scripts/notebooks/gen_final_analysis.py:457-466`.
