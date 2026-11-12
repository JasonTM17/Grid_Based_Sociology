# Q&A theo khái niệm bài giảng (Day 1–4) | Topic 6 · STING × PAPI

_Quy tắc: ≤60 giây/câu; A trả lời chính câu thuật toán/dữ liệu, B trả lời chính câu kết quả/ý nghĩa — nhưng mỗi thành viên phải trả lời được CẢ 37 câu. Mọi số lấy từ file ghi ở dòng "Repo" của từng câu; không đọc số từ trí nhớ._

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
- **Repo:** `results/course_supervised_baselines.csv:2-9`; `results/course_supervised_baselines.md:12-28,37`; `scripts/course_supervised_baselines.py:239-267`.

## Day 1 — Ý tưởng học máy

1. **Học máy là gì, theo đúng định nghĩa bài giảng?** — Định nghĩa Arthur Samuel: lĩnh vực cho máy tính khả năng học mà không được lập trình tường minh. Khung của bài giảng là Data → Algorithm → Model: thuật toán học quy luật từ dữ liệu rồi cho ra model dùng để dự đoán. Repo theo đúng khung đó: `STING.fit` chỉ nhận ma trận điểm, không có luật viết tay; model lưu ra file rồi `predict` cho tỉnh mới.
   - **Hỏi bẫy:** "Vậy AI có phải ML?" — Không; bài giảng nói AI bao gồm ML và DL, nên ML là tập con, và repo không dùng DL.
   - **Repo:** `src/sting.py:84-125`; `README.md:145-159`.
   - **Bài giảng:** Day 1, trang 15; trang 16.

2. **Học có giám sát khác học không giám sát ở đâu?** — Có giám sát: model học từ cặp (câu hỏi, đáp án) rồi trả lời câu mới. Không giám sát: chỉ nhận câu hỏi, tự tìm cấu trúc, không có đáp án đúng để đối chiếu. Repo có cả hai: STING là không giám sát (`cluster()` trả cụm và −1), còn Ridge/random forest/logistic regression là có giám sát trên cặp năm t → t+1.
   - **Hỏi bẫy:** "Đầu ra của không giám sát có phải nhãn đúng/sai?" — Không; đó là cụm, không có ground truth để chấm.
   - **Repo:** `src/sting.py:130-191`; `scripts/predict_supervised.py:1-14`.
   - **Bài giảng:** Day 1, trang 27.

3. **Vì sao STING là grid-based clustering không giám sát, và khớp đề tài 6 thế nào?** — STING chia không gian thành lưới phân cấp, mỗi ô giữ count/mean/std/min/max, gom các ô "dày" liền kề thành cụm — không cần nhãn, không cần k. Đó đúng là đề tài 6 "Grid-based (clustering)"; panel 882 dòng × 41 cột vượt yêu cầu cuối kỳ ≥500 hàng và ≥10 cột.
   - **Hỏi bẫy:** "STING có cần truyền k?" — Không; k là kết quả của mật độ lưới + `min_count`, không phải tham số vào.
   - **Repo:** `src/sting.py:1-13`; `README.md:10`; `scripts/check_data.py:17-18`.
   - **Bài giảng:** Day 1, trang 12.

4. **Regression và classification khác nhau thế nào, repo làm bài nào?** — Bài giảng: nhãn rời rạc → classification; nhãn liên tục → regression. Repo chạy cả hai: hồi quy dự báo điểm 6.1 Y tế công lập năm t+1 (Ridge, MAE holdout 0.0640) và phân loại nhị phân "vùng dày vs ngoại vi" (logistic regression, macro-F1 holdout 0.541).
   - **Hỏi bẫy:** "Nhãn bài phân loại là nhãn người gán?" — Không; là pseudo-label do STING tại từng cutoff sinh ra.
   - **Repo:** `scripts/predict_supervised.py:263-330, 332-370`; `results/supervised_metrics.csv:4-8`.
   - **Bài giảng:** Day 1, trang 34.

5. **Bài phân loại của repo có phải semi-supervised không?** — Bài giảng mô tả semi-supervised: gom cụm toàn bộ dữ liệu, xem các điểm đã có nhãn, gán nhãn cụm theo đa số, điểm mới vào cụm nào nhận nhãn đó. Repo không có nhãn người cho bài này nên không được gọi semi-supervised: nhãn 0/1 do STING sinh (pseudo-label), classifier chỉ học lại quy tắc "ô dày hay không".
   - **Hỏi bẫy:** "Pseudo-label có phải ground truth?" — Không; nó đo mức khớp với STING, không đo đúng/sai xã hội.
   - **Repo:** `scripts/predict_supervised.py:12-14, 187-211`; `results/supervised_summary.md:29`.
   - **Bài giảng:** Day 1, trang 36.

## Day 2 — Naive Bayes, KNN, đánh giá

6. **Naive Bayes hoạt động thế nào qua bảng xác suất, và repo đã chạy chưa?** — Naive Bayes tính xác suất có điều kiện từng thuộc tính theo lớp rồi nhân với xác suất tiên nghiệm, giả định các thuộc tính độc lập; bài giảng lập bảng đếm: Outlook Sunny là 2/9 và 3/5, tổng 5/14. Repo giờ CÓ: `GaussianNB` trong run so sánh học phần đạt macro-F1 CV 0.514, accuracy holdout 0.746, macro-F1 holdout 0.566 — cao nhất bảng theo CV.
   - **Hỏi bẫy:** "Ô Overcast ghi 0/5 thì xác suất bằng 0, sai ở đâu?" — Zero-frequency: phải làm trơn Laplace; bảng bài giảng chỉ là đếm thô. Lưu ý `GaussianNB` giả định mỗi đặc trưng có phân phối chuẩn theo lớp, không dùng đếm rời rạc như bảng bài giảng — cùng ý tưởng Bayes, khác công thức likelihood.
   - **Repo:** `scripts/course_supervised_baselines.py:138-141`; `results/course_supervised_baselines.csv:3`; `results/course_supervised_baselines.md:15,23`.
   - **Bài giảng:** Day 2, trang 15; bảng xác suất trang 16-18.

7. **Naive Bayes đứng đầu CV ở đây — có được nói nó là model tốt nhất không?** — Không được nói "tốt nhất" như kết luận tổng quát. Nó đứng đầu theo tiêu chí đã chốt trước (macro-F1 CV 0.514, hơn KNN 0.486 và RBF 0.437), nhưng holdout macro-F1 0.566 chỉ ngang SVM RBF 0.566 và hơn RF 0.560; holdout chỉ 59 tỉnh, 11 tỉnh lớp 0 nên một tỉnh đổi nhãn đã đổi accuracy ~0.017. Thêm nữa grid của NB rỗng nên điểm CV của nó không bị đẩy lên bởi chọn siêu tham số như các model khác (điểm CV của chúng là max trên lưới); đó là lý do cấu trúc khiến NB trông sạch hơn, không phải bằng chứng vượt trội.
   - **Hỏi bẫy:** "Vậy chọn NB để triển khai?" — Chọn theo tiêu chí CV là NB, nhưng phải nói kèm: một holdout, không kiểm định ý nghĩa, và 2 fold CV cuối trùng vùng chọn cấu hình STING (xem câu 29); CV chỉ là khám phá.
   - **Repo:** `results/course_supervised_baselines.csv:3-9`; `results/course_supervised_baselines.md:23,28,31-35`; `scripts/course_supervised_baselines.py:138-141,239-267`.

8. **KNN dùng khoảng cách và k thế nào?** — KNN không học tham số: với điểm mới, tính khoảng cách (bài giảng dùng Euclidean), lấy k hàng xóm gần nhất, bầu nhãn theo đa số. k nhỏ nhạy nhiễu, k lớn làm mượt; bài giảng khuyên thử k = 1, 3, 5… và chọn k lẻ. Repo chạy KNN ở cả hai bài: hồi quy là ứng viên R3 (k=20, weights=distance), R² CV 0.168 thấp hơn Ridge 0.265 nên không được chọn; phân loại học phần quét k ∈ {3,5,7,9}, macro-F1 CV 0.486, holdout accuracy 0.593, macro-F1 0.534.
   - **Hỏi bẫy:** "Vì sao KNN phải chuẩn hóa?" — Khoảng cách bị chiều có thang lớn chi phối; repo bọc `StandardScaler` trong Pipeline nên mỗi fold tự fit scaler trên train của fold đó.
   - **Repo:** `results/candidates_regression.md:61`; `scripts/candidates_regression.py:160-161`; `results/course_supervised_baselines.csv:4`; `scripts/course_supervised_baselines.py:143-150`.
   - **Bài giảng:** Day 2, trang 25-29 (Euclidean trang 26; chọn k trang 29).

9. **Vì sao báo accuracy thôi là chưa đủ, phải có macro-F1?** — Accuracy là tỉ lệ đoán đúng, dễ bị lớp đa số thống trị. Macro-F1 lấy trung bình F1 của từng lớp nên phạt việc bỏ rơi lớp thiểu số. Repo báo cả hai: logistic regression holdout accuracy 0.644, macro-F1 0.541; majority accuracy 0.186 nhưng macro-F1 0.157; CV dùng macro-F1 vì prevalence nhãn 1 trôi 0.000 (2011) → 0.917 (2021).
   - **Hỏi bẫy:** "Accuracy 0.9 là model tốt?" — Chưa, nếu lớp đa số đã chiếm 0.9; phải so với baseline đa số. Ở holdout này lớp 1 chiếm 48/59 ≈ 0.814, nên "luôn đoán 1" đã đạt accuracy 0.814; còn trên CV, baseline mù thời gian đó chỉ đạt macro-F1 0.400.
   - **Repo:** `scripts/predict_supervised.py:353-361`; `results/supervised_metrics.csv:6-7`; `results/supervised_summary.md:31`; `results/course_supervised_baselines.md:28`.
   - **Bài giảng:** Day 2, trang 30-34 (confusion matrix, precision & recall) — macro-F1 không có trong text bài giảng, nhóm tự chọn và phải nói rõ.

10. **Confusion matrix cho biết gì?** — Ma trận 2×2 đối chiếu nhãn thật với nhãn dự báo: TP, FN, FP, TN; từ đó tính precision, recall. Repo vẽ confusion cho bài phân loại 2023→2024, nhãn 0 = ngoại vi (nhiễu STING), 1 = vùng dày, hình ở `results/figs/supervised_confusion.png`; đây là ma trận của classifier chọn theo CV, không phải của STING.
    - **Hỏi bẫy:** "Positive là tỉnh tốt?" — Không; positive = vùng dày (nhãn 1), không phải đánh giá tốt/xấu.
    - **Repo:** `scripts/predict_supervised.py:96, 463-488`.
    - **Bài giảng:** Day 2, trang 31-33.

11. **Đọc hình `results/figs/course_confusion_matrix.png` thế nào?** — Hình có 6 panel, mỗi panel một model học phần: Naive Bayes Gauss, KNN, SVM tuyến tính, SVM RBF, cây quyết định, random forest. Hàng = nhãn STING thực tế, cột = nhãn dự báo; ô trên đường chéo là đoán đúng, ô ngoài đường chéo là FN/FP; màu đậm = nhiều tỉnh. Mỗi panel phải đọc kèm bối cảnh lớp: holdout có 11 tỉnh lớp 0 và 48 tỉnh lớp 1, nên model đoán thiên về 1 sẽ có accuracy cao mà vẫn sai nhiều ở lớp 0 — phải so đường chéo với 11 và 48, không chỉ nhìn màu. Hình không có majority và logistic regression; hai model đó nằm trong bảng số.
    - **Hỏi bẫy:** "Panel nào tốt nhất?" — Không chọn theo một hình: tiêu chí chọn là macro-F1 CV (câu 7 và câu 21); hình chỉ để đọc kiểu lỗi từng model.
    - **Repo:** `scripts/course_supervised_baselines.py:90-99, 339-394`; `results/course_supervised_baselines.md:26-28`.
    - **Bài giảng:** Day 2, trang 31-33.

12. **Majority baseline là gì và repo tính ra sao?** — Baseline đa số đoán theo lớp xuất hiện nhiều nhất trong train của từng fold — không phải "always 1". Repo tính bằng `expanding_majority_f1`: CV macro-F1 0.228; holdout accuracy 0.186, macro-F1 0.157. Vì prevalence trôi, baseline mù thời gian "always 1" lại đạt 0.400 macro-F1, cao hơn majority — nên phải đối chiếu cả hai sàn. Con số 0.186 chính là 11/59: lớp đa số của train là 0 ở cả 6 fold, nên majority đoán 0 cho tất cả và chỉ đúng 11 tỉnh lớp 0.
    - **Hỏi bẫy:** "Baseline đa số có luôn đoán 1?" — Không; ở cả 6 fold, lớp đa số của train là 0, ngược với validation (luôn đa số 1).
    - **Repo:** `scripts/predict_supervised.py:236-251`; `results/supervised_metrics.csv:6`; `results/supervised_summary.md:31`; `results/course_supervised_baselines.md:28`.
    - **Bài giảng:** Day 2, trang 30 (đo trên test set, không đo trên train).

13. **Precision và recall khác nhau thế nào?** — Precision = TP/(TP+FP), recall = TP/(TP+FN); đổi ngưỡng thì hai số đánh đổi nhau. Repo không xuất bảng precision/recall từng lớp; số tổng hợp đang có là accuracy và macro-F1 (ví dụ logistic regression holdout 0.644 / 0.541; NB 0.746 / 0.566). Muốn số từng lớp thì đọc bốn ô của confusion matrix trong `results/figs/course_confusion_matrix.png` rồi tính, hoặc chạy lại script để in ra — không đọc số từ trí nhớ.
    - **Hỏi bẫy:** "F1 là gì?" — Trung bình điều hòa của precision và recall; macro-F1 lấy trung bình đều hai lớp.
    - **Repo:** `scripts/predict_supervised.py:353-361, 463-478`; `results/course_supervised_baselines.csv:3,9`.
    - **Bài giảng:** Day 2, trang 34.

14. **Vì sao scaler nằm trong Pipeline?** — Vì Pipeline biến "chuẩn hóa rồi huấn luyện" thành một khối: khi GridSearchCV chạy từng fold, nó chỉ fit `StandardScaler` trên phần train của fold đó rồi transform validation, và khi fit lần cuối trên train thì tham số scaler vẫn chỉ đến từ train — holdout 2024 chỉ được transform. Nếu fit scaler bên ngoài trước khi chia fold, mean/std của validation rò vào train, điểm CV sẽ lạc quan giả tạo. Trong code, NB/KNN/SVM/cây/logistic đều bọc `Pipeline([("sc", StandardScaler()), ("clf", ...)])`; random forest không bọc vì cây bất biến với scale từng chiều.
    - **Hỏi bẫy:** "Pipeline có đảm bảo không leakage tuyệt đối?" — Nó chặn leakage của bước tiền xử lý trong fold, nhưng không chặn leakage theo thời gian; phần thời gian do cách dựng cặp năm t → t+1 và STING fit ≤ cutoff đảm nhận.
    - **Repo:** `scripts/course_supervised_baselines.py:138-213, 239-267`; `results/course_supervised_baselines.md:6`.
    - **Bài giảng:** Day 4, trang 9; trang 14.

## Day 3 — SVM và cây

15. **Margin, siêu phẳng và support vector là gì?** — SVM tìm siêu phẳng tách hai lớp với lề lớn nhất; các điểm nằm sát lề hoặc vi phạm lề là support vector — bỏ chúng đi thì siêu phẳng đổi. Repo có huấn luyện SVM trong run so sánh học phần: SVM tuyến tính (chỉ quét C ∈ {0.1, 1, 10}) đạt macro-F1 CV 0.343, holdout accuracy 0.695, macro-F1 0.556.
    - **Hỏi bẫy:** "Mọi điểm đều là support vector?" — Không; chỉ các điểm trên/trong lề mới quyết định siêu phẳng.
    - **Repo:** `scripts/course_supervised_baselines.py:152-164`; `results/course_supervised_baselines.csv:5`.
    - **Bài giảng:** Day 3, trang 7-8.

16. **Kernel giải quyết vấn đề gì?** — Kernel thay tích vô hướng bằng hàm K(x, z), cho SVM học ranh giới phi tuyến trong không gian đặc trưng nhiều chiều mà không cần ánh xạ tường minh. Đề tài 1 của môn là "SVM Kernel"; repo có SVM RBF: macro-F1 CV 0.437, holdout accuracy 0.678, macro-F1 0.566. Chỉ quét C, để gamma mặc định `scale` — nên đây là một điểm RBF, không phải kết luận kernel nào tốt nhất.
    - **Hỏi bẫy:** "Kernel làm dữ liệu thành tuyến tính?" — Không; nó cho phép ranh giới phi tuyến trong không gian gốc.
    - **Repo:** `scripts/course_supervised_baselines.py:166-178`; `results/course_supervised_baselines.csv:6`.
    - **Bài giảng:** Day 1, trang 12 (đề tài 1); Day 2, trang 9 (agenda V. SVM Kernel).

17. **SVM RBF và SVM tuyến tính: số liệu nói gì, có nên chọn RBF?** — Trên CV, RBF hơn tuyến tính rõ: macro-F1 0.437 so với 0.343 — gợi ý ranh giới cong, nhưng đó là suy đoán từ số chứ chưa kiểm định. Trên holdout thì gần như hòa: macro-F1 0.566 so với 0.556, còn accuracy tuyến tính lại cao hơn (0.695 so với 0.678). Với 59 tỉnh, khác biệt này nằm trong nhiễu; ngoài ra chỉ quét C, không quét gamma, nên chưa phải so sánh kernel công bằng. Cả hai đều thấp hơn NB trên CV, nên không model SVM nào được chọn.
    - **Hỏi bẫy:** "RBF luôn hơn tuyến tính?" — Không; ở đây RBF hơn trên CV nhưng không hơn trên holdout accuracy, và một holdout không đủ để khẳng định.
    - **Repo:** `results/course_supervised_baselines.csv:5-6`; `results/course_supervised_baselines.md:31-35`; `scripts/course_supervised_baselines.py:152-178`.

18. **Vì sao SVM chuẩn chỉ làm bài hai lớp?** — Bài giảng nhấn: SVM chuẩn chỉ giải bài toán hai lớp; đa lớp phải chia thành nhiều bài nhị phân (one-vs-rest hoặc one-vs-one). Repo khớp sẵn: bài phân loại là nhị phân (0 = ngoại vi, 1 = vùng dày), còn k=3 của STING là cụm, không phải lớp cần SVM tách.
    - **Hỏi bẫy:** "3 cụm STING thì cần SVM 3 lớp?" — Không; cụm là đầu ra không giám sát, không phải nhãn phân loại.
    - **Repo:** `scripts/predict_supervised.py:92-96, 187-211`.
    - **Bài giảng:** Day 3, trang 16.

19. **Cây quyết định chọn thuộc tính bằng entropy và information gain thế nào?** — Cây chọn thuộc tính làm entropy giảm nhiều nhất: entropy đo lượng thông tin (sự kiện ít xác suất mang nhiều tin), gain = entropy trước − entropy sau khi chia. Bài giảng tính trên 14 bản ghi 9 yes/5 no, các nhánh 7-3 và 2-2. Repo có cây quyết định trong run học phần (quét `max_depth` ∈ {2,3,4,5}): macro-F1 CV 0.426, holdout accuracy 0.559 — thấp nhất trong 6 classifier học phần, macro-F1 0.508.
    - **Hỏi bẫy:** "Entropy vượt 1 được không?" — Với hai lớp, tối đa là 1 bit; 9-5 xấp xỉ 0.94.
    - **Repo:** `scripts/course_supervised_baselines.py:180-189`; `results/course_supervised_baselines.csv:7`.
    - **Bài giảng:** Day 3, trang 22-23 (ví dụ trang 23).

20. **Random forest hơn một cây ở đâu, repo dùng nó thế nào?** — Random forest dựng nhiều cây trên bootstrap và chọn ngẫu nhiên tập con đặc trưng, rồi bỏ phiếu hoặc lấy trung bình — giảm phương sai so với một cây. Repo dùng ở cả hai bài: hồi quy R² CV 0.197, MAE holdout 0.0616 (thấp hơn Ridge nhưng không được chọn vì CV thấp hơn); phân loại học phần macro-F1 CV 0.394, holdout accuracy 0.627, macro-F1 0.560. Con số phân loại trong pipeline công bố (CV 0.397, accuracy 0.678, macro-F1 0.600) cao hơn một chút vì cấu hình khác — 300 cây thay vì 50 cây; hai lần chạy đều thật, không phải mâu thuẫn.
    - **Hỏi bẫy:** "Random forest luôn thắng model tuyến tính?" — Không; bài hồi quy của repo chọn Ridge theo CV dù RF có MAE holdout thấp hơn, và bài phân loại RF thấp hơn NB trên CV.
    - **Repo:** `scripts/predict_supervised.py:277, 344`; `results/supervised_metrics.csv:5, 8`; `results/course_supervised_baselines.csv:8`; `scripts/course_supervised_baselines.py:191-199, 247-248`.
    - **Bài giảng:** Day 2, trang 9 (agenda VII. Random Forest) — text trích xuất không có slide nội dung RF.

21. **Vì sao cây quyết định và random forest không được chọn?** — Quy tắc chọn đã đặt trước: model có macro-F1 CV cao nhất, không tính majority. Cây có CV 0.426 và holdout accuracy thấp nhất trong 6 classifier học phần (0.559); RF có CV 0.394 — thấp nhất trong 6 — dù holdout macro-F1 0.560 tốt hơn cây. Lý do: cây đơn chia theo trục nên phải xấp xỉ ranh giới mật độ cong bằng nhiều lát cắt bậc thang, dễ overfit với 738 cặp; RF lấy trung bình nhiều cây để giảm phương sai nhưng không sửa được bias chia theo trục. Cả hai đều dưới NB 0.514 nên không được chọn, dù RF có lúc nhỉnh hơn trên một holdout.
    - **Hỏi bẫy:** "Vậy cây vô dụng?" — Không; cây là baseline dễ giải thích và là nội dung môn học, nhưng không thắng tiêu chí CV ở bài này.
    - **Repo:** `results/course_supervised_baselines.md:8,23`; `results/course_supervised_baselines.csv:7-8`; `scripts/course_supervised_baselines.py:180-199`.

## Day 4 — Tiền xử lý

22. **Ba giai đoạn tiền xử lý theo thứ tự nào, repo kiểm chứng từng bước ra sao?** — Bài giảng: Cleaning → Integration → Transformation; mỗi bước Test → Decide, và phải định nghĩa bài toán/thuật toán trước. Repo có đúng thứ tự đó và có bước kiểm chứng ghi lại: `scripts/preprocessing_audit.py` (chỉ đọc dữ liệu) đo trên panel/master thật rồi ghi `results/preprocessing_audit.md` theo bảng Test | Result | Decision | Evidence. Cleaning: trùng khóa → thiếu → nhất quán → ngoại lai CUỐI CÙNG; Integration: khóa nối, cardinality, số dòng, xung đột, rò rỉ scaler; Transformation: chuẩn hóa và đối chiếu số học tham số đóng băng.
    - **Hỏi bẫy:** "Audit có phải cổng chặn tự động?" — Không; nó ghi lại quyết định đang áp dụng kèm bằng chứng, còn chặn cứng nằm trong code build/predict (ví dụ lỗi khi trùng khóa). Nói đúng mức, không thổi phồng thành "pipeline tự kiểm định".
    - **Repo:** `scripts/preprocessing_audit.py:1-16, 369-453`; `results/preprocessing_audit.md:11-27, 89-107`.
    - **Bài giảng:** Day 4, trang 5-6.

23. **Vì sao dedup phải làm đầu tiên, và audit đo được gì?** — Bản ghi trùng làm sai mọi thống kê phía sau: mean, tần suất, cả giá trị dùng để điền khuyết. Audit đo trên panel thật: 0 dòng trùng khóa / 882 dòng (882 khóa duy nhất), trùng toàn dòng cũng 0. Quyết định của pipeline: giữ đúng một dòng mỗi khóa và chặn cứng nếu phát hiện trùng — không tự xóa, để lỗi lộ ra. Đây là dedup theo khóa nghiệp vụ (province_code, year), không phải theo toàn bộ dòng.
    - **Hỏi bẫy:** "Sao không `drop_duplicates()` cả dòng?" — Hai dòng khác nhau một cột vẫn là cùng một tỉnh-năm; phải kiểm theo khóa.
    - **Repo:** `results/preprocessing_audit.md:19`; `scripts/build_external_master.py:139-140`; `scripts/predict_supervised.py:101-102`; `scripts/preprocessing_audit.py:65-69`.
    - **Bài giảng:** Day 4, trang 7.

24. **Repo điền khuyết thế nào, audit nói gì?** — Bài giảng đặt imputation trong Cleaning nhưng yêu cầu Test → Decide và không dùng null. Audit đo: 4649/32634 ô chỉ tiêu bị thiếu (14.2%), trong đó 4284 ô nằm NGOÀI cửa sổ thu thập của cột nên là thiếu cấu trúc; chỉ 13/882 dòng thiếu chỉ tiêu trong cửa sổ (365 ô, thiếu `sd_4_2` hoặc `sd_6_1`). Quyết định: KHÔNG nội suy, không điền, giữ NaN; chỉ loại dòng khi dựng ma trận feature / ghép cặp. Chỉ ứng viên exploratory R4 dùng `SimpleImputer` median trong Pipeline, chưa được duyệt.
    - **Hỏi bẫy:** "Điền median cho đủ 63 tỉnh có sao?" — Tạo dữ liệu không có thật và làm sai mật độ cục bộ mà STING dùng để gán nhãn; 13 dòng bị loại là 1.5%, minh bạch hơn là bịa.
    - **Repo:** `results/preprocessing_audit.md:20-21, 112`; `scripts/preprocessing_audit.py:86-113`; `scripts/papi_pred_common.py:53-57`; `scripts/predict_demo.py:67-68`; `scripts/candidates_regression.py:172`.
    - **Bài giảng:** Day 4, trang 7; trang 14.

25. **Vì sao outlier removal phải làm cuối, và repo xử lý ngoại lai thế nào?** — Vì nó phụ thuộc phân bố sau khi đã sửa lỗi và tích hợp; xóa sớm dễ xóa nhầm điểm hợp lệ. Audit đánh dấu |z| > 3 trên toàn panel: 122 ô (0.4%), 98 dòng, 29 cột — và GIỮ toàn bộ, chỉ đánh dấu. Lý do: đây là điểm khảo sát thật; điểm cực trị rơi vào ô lưới thưa nên tự nhận nhãn nhiễu −1 theo cơ chế `min_count` của STING, dữ liệu gốc không bị xóa. Vì vậy không được nói repo "đã xử lý outlier" theo nghĩa xóa.
    - **Hỏi bẫy:** "Nhiễu −1 có phải outlier?" — Không; −1 = ô không đủ `min_count` tại mức lưới đang dùng. Thêm nữa z tính gộp toàn panel nên trộn bước nhảy thang đo 2021; audit không kết luận tương đương thang đo xuyên năm.
    - **Repo:** `results/preprocessing_audit.md:26, 113-114`; `scripts/preprocessing_audit.py:261-290`; `src/sting.py:12-13, 151-155`; `results/predict_summary.md:48`.
    - **Bài giảng:** Day 4, trang 7.

26. **Data leakage là gì và repo chặn ở đâu?** — Leakage là dùng thông tin không được phép có lúc dự đoán: dữ liệu tương lai, hoặc fit scaler/imputer trên test. Repo chặn bằng: scaler + STING chỉ fit trên lịch sử ≤ cutoff; biến đổi nằm trong Pipeline nên GridSearchCV refit từng fold; holdout 2023→2024 chấm một lần. Audit kiểm thêm: tham số scaler đóng băng khớp thống kê ≤2023 với Δmean = 0, Δscale = 0; nếu fit cả 869 dòng thì Δmean = 0.011456 nên sẽ không khớp JSON — tức không rò rỉ. Còn một điểm hở đã khai báo: `sd_6_1` vừa là target vừa là feature lag-1.
    - **Hỏi bẫy:** "Target năm t+1 thì có leakage không?" — Không gian lận thời gian, nhưng feature `sd_6_1` năm t là thông tin lag của chính target — phải nói rõ.
    - **Repo:** `results/preprocessing_audit.md:98`; `scripts/predict_supervised.py:153-169, 276-285`; `results/supervised_summary.md:33`.
    - **Bài giảng:** Day 4, trang 8; trang 14.

27. **Vì sao scaler chỉ được fit trên train?** — Chuẩn hóa phải học mean/std trên train rồi áp cho test; fit trên toàn bộ là để phân bố test rò vào. Repo: `StandardScaler().fit(ptr)` với ptr = các năm ≤2023 rồi transform 2024; trong CV, scaler nằm trong Pipeline nên mỗi fold tự fit. Audit xác nhận tham số JSON tái lập đúng thống kê lịch sử với ddof=0 (ddof=1 lệch 1.13e-04). Lưu ý STING bất biến với biến đổi affine từng chiều, nhưng vẫn phải làm đúng để predict khớp.
    - **Hỏi bẫy:** "Z-score toàn panel có đổi cụm STING?" — Không, cùng một hệ trục thì chỉ đổi thang; đổi cụm xảy ra khi z theo từng năm (ARI non-noise 0.0060).
    - **Repo:** `scripts/predict_demo.py:64-72`; `scripts/predict_supervised.py:153-164`; `src/sting.py:95-99`; `results/preprocessing_audit.md:106-107`; `results/candidates_clustering.md:62`.
    - **Bài giảng:** Day 4, trang 9; trang 14.

28. **"Test → Decide" áp dụng vào việc chọn cấu hình thế nào?** — Nghĩa là mỗi quyết định phải có bước kiểm rồi mới chốt, không quyết bằng cảm tính. Repo áp dụng ở chỗ quan trọng nhất: `scripts/predict_sweep.py` fit ≤2020, chấm trên tương lai giả 2021-2022, bộ lọc và hàm điểm đặt trước, năm 2024 không tham gia; kết quả ghi vào `models/predict_config.json` và đóng băng trước khi dự đoán. Cần nói kèm giới hạn: đúng hai năm 2021-2022 đó cũng là hai fold CV cuối của classifier, nên CV chỉ là khám phá (câu 29).
    - **Hỏi bẫy:** "Chấm xong thấy chưa đạt rồi đổi ngưỡng?" — Đó là selection-on-test; repo đóng băng ngưỡng trước khi chạy.
    - **Repo:** `scripts/predict_sweep.py:53-59, 110-113, 156-190`.
    - **Bài giảng:** Day 4, trang 5.

## Câu bẫy hội đồng

29. **Chọn cấu hình STING trên 2021–2022 trùng hai fold CV cuối của classifier — vậy CV còn giá trị gì?** — Không còn là ước lượng generalization sạch, phải gọi đúng là khám phá. `predict_sweep.py` fit ≤2020 và chấm coverage trên đúng 2021-2022; classifier CV lại lấy validation ở 2017-2022, nên hai fold 2021, 2022 dùng pseudo-label do một cấu hình được chọn một phần nhờ chính hai năm đó. Hệ quả: macro-F1 CV (ví dụ LR 0.434, NB 0.514) hơi lạc quan. Phần sạch hơn là holdout 2023→2024: 2024 không tham gia chọn cấu hình và chỉ chấm một lần — nhưng vẫn chỉ một năm, 59 tỉnh, nên cũng không phải bằng chứng tổng quát hóa.
    - **Hỏi bẫy:** "Vậy bỏ CV?" — Không; CV dùng để so sánh tương đối các model dưới cùng một quy trình, chỉ không được phát biểu như hiệu năng kỳ vọng trên dữ liệu mới.
    - **Repo:** `scripts/predict_sweep.py:53-54, 111-113, 168`; `scripts/predict_supervised.py:73-74, 214-233`; `results/supervised_summary.md:30`; `results/course_supervised_baselines.md:7`.

30. **"External validation" của nhóm có chứng minh cụm đúng hoặc dự báo được không?** — Không. Đó là kiểm tra liên hệ với thước đo độc lập: PCI (khảo sát doanh nghiệp của VCCI, tách khỏi PAPI hộ dân) so với nhãn cụm trên 747 điểm 2011-2022 cho ANOVA F(3,743) = 9.04, p = 6.93e-06; Kruskal-Wallis p = 5.84e-07, eta² = 0.0352. Cụm 0 chỉ 5 tỉnh và cụm 1 chỉ 16 nên cặp đáng tin là nhiễu vs cụm 2. Nó nói cấu trúc cụm đồng biến với một thước đo chưa từng dùng khi học — quan hệ, không nhân quả; và không đo độ chính xác dự báo vì nhãn là pseudo-label. Kiểm tra Top-30 2023-2024 còn bị selection bias, p = 0.35, chỉ đọc như phụ.
    - **Hỏi bẫy:** "p nhỏ nghĩa là cụm có thật?" — Không; p nhỏ chỉ nói khác biệt PCI giữa nhóm khó do ngẫu nhiên, không nói nhãn đúng hay mô hình dự báo tốt.
    - **Repo:** `results/external_validation.md:17-19, 24, 32`; `scripts/external_validation.py:1-20`.

31. **Cài đặt STING của nhóm có phải tái lập đầy đủ bài Wang et al. (1997)?** — Không, là bản đơn giản hóa và phải nói đúng như vậy. Bài gốc lưu thêm distribution type trong mỗi ô và phân tích top-down: bắt từ lớp cao, kiểm ô liên quan bằng confidence rồi mới hạ xuống lớp con. Cài đặt của nhóm: mỗi `Cell` giữ count/mean/std/min/max theo từng chiều cùng biên ô, không có distribution type; `fit` dựng đủ mọi mức, còn `cluster`/`query` dùng một mức cố định, không duyệt top-down. Tham số `significance_z` mặc định tắt và cấu hình đóng băng không dùng, nên thực tế không có pruning theo confidence. Vì thế kết quả là của cài đặt này trên PAPI, không được phát biểu như tái lập nguyên văn thực nghiệm của bài báo.
    - **Hỏi bẫy:** "Vậy có được ghi 'theo Wang et al. 1997'?" — Được, nhưng phải ghi là triển khai ý tưởng lưới thống kê phân cấp, kèm rõ phần lược bỏ; không được ngụ ý kết quả trùng bài gốc.
    - **Repo:** `src/sting.py:1-13, 39-51, 119-125, 130-136`; `reports/qa_final.md:77,79`.

## Bổ sung — GV dễ hỏi (vấn đáp thêm)

32. **Vì sao không xóa ngoại lai khi audit đã gắn cờ 122 ô |z|>3?** — Day 4 xếp xử lý ngoại lai CUỐI bước Cleaning vì phải biết phân bố sau dedup, thiếu và nhất quán; audit đo trên panel thật: 122 ô (0.4%), 98 dòng, 29 cột — quyết định GIỮ toàn bộ, chỉ đánh dấu, không xóa. Điểm PAPI là khảo sát thật; cắt 122 ô làm méo thống kê panel 882×41. Điểm cực trị thường rơi vào ô lưới thưa nên STING tự gán nhiễu −1 qua `min_count`, không cần phá dữ liệu gốc — đúng tinh thần outlier removal cuối nhưng lựa chọn là không loại.
   - **Hỏi bẫy:** "122 ô >3 sigma thì bắt buộc cắt theo slide?" — Không; slide yêu cầu Test → Decide, và audit ghi rõ z-score gộp toàn panel nên cờ chỉ mang tính mô tả.
   - **Repo:** `results/preprocessing_audit.md:15,26,113-114`; `scripts/preprocessing_audit.py:261-290`; `src/sting.py:12-13`.
   - **Bài giảng:** Day 4, trang 7.

33. **Vì sao `dropna` thay vì imputation, và khi nào imputation hợp lý?** — Audit: 4649/32634 ô thiếu trong 37 chỉ tiêu (14.2%), trong đó 4284 ô nằm NGOÀI cửa sổ thu thập của cột — thiếu cấu trúc, không phải ngẫu nhiên để median "vá". Chỉ 13/882 dòng (1.5%) thiếu trong cửa sổ (365 ô trên `sd_4_2` hoặc `sd_6_1`). Pipeline chính: không nội suy, `dropna` khi ghép cặp và `year_frame` — minh bạch hơn tạo giá trị không có trong khảo sát. Imputation hợp lý khi đã Test → Decide trên thiếu ngẫu nhiên, quy mô lớn và không làm sai mật độ cục bộ STING — ví dụ tham khảo `SimpleImputer(strategy="median")` trong ứng viên R4, chưa đưa vào pipeline công bố.
   - **Hỏi bẫy:** "Slide Day 4 có imputation nên phải điền?" — Imputation nằm trong khung Cleaning, nhưng cùng slide yêu cầu Test → Decide; repo có bảng audit chứng minh quyết định không điền.
   - **Repo:** `results/preprocessing_audit.md:20-21,112`; `scripts/papi_pred_common.py:53-57`; `scripts/predict_supervised.py:106`; `scripts/candidates_regression.py:172`.
   - **Bài giảng:** Day 4, trang 7; trang 14.

34. **Vì sao Naive Bayes macro-F1 CV 0.514 cao nhất mà vẫn không kết luận "NB tốt nhất"?** — Theo quy tắc chọn pipeline vẫn lấy gaussian naive bayes vì `value_cv` lớn nhất, nhưng khoảng cách tới hạng hai (KNN 0.486) chỉ 0.028, nhỏ hơn `cv_std` của NB là 0.120 trên 6 fold — biến động giữa các fold lớn hơn gap giữa hai model đầu. Holdout macro-F1 NB 0.566 ngang SVM RBF 0.566; tất cả số đó là đồng thuận với pseudo-label STING, không ground truth. "Tốt nhất" ngụ ý vượt trội có ý nghĩa; repo chỉ được nói đứng đầu theo tiêu chí CV đã chốt và phải nói kèm giới hạn thống kê.
   - **Hỏi bẫy:** "0.514 > 0.486 là thắng rõ ràng?" — Không; `results/course_supervised_baselines.md:24` ghi gap 0.028 < cv_std 0.120 → thứ hạng mô tả, không khẳng định vượt trội.
   - **Repo:** `results/course_supervised_baselines.csv:3-4`; `results/course_supervised_baselines.md:23-24`; `scripts/course_supervised_baselines.py:374-377`.
   - **Bài giảng:** Day 2, trang 30-34 (đánh giá) — cv_std là chuẩn tự đặt của repo.

35. **Pseudo-label có vòng lặp nhãn không, và điều đó giới hạn kết luận thế nào?** — Có phụ thuộc vòng: cấu hình STING đóng băng (`predict_sweep.py` fit ≤2020, chấm coverage trên 2021–2022) → `build_classification_pairs` fit STING/scaler ≤t để gán nhãn tỉnh năm t+1 (`y = int(labels[pc] != -1)`, 738 cặp train) → classifier học khớp lại quy tắc "vùng dày vs ngoại vi" do chính STING sinh → macro-F1 đo mức khớp, không đúng/sai xã hội. Thêm vòng chọn cấu hình: hai năm 2021–2022 dùng trong sweep trùng hai fold CV cuối của classifier (`results/supervised_summary.md:30`) nên macro-F1 CV hơi lạc quan. Giới hạn: chỉ so sánh model A vs B dưới cùng protocol và cùng pseudo-label; không suy ra dự báo thực tế, không gọi là semi-supervised (Day 1), không dùng holdout để chọn sau khi đã thấy điểm.
   - **Hỏi bẫy:** "CV 0.514 chứng minh dự báo tốt?" — Không; nhãn y do STING tại từng cutoff tạo ra, classifier chỉ học tái hiện nhãn đó.
   - **Repo:** `scripts/predict_supervised.py:92-96,187-211`; `scripts/predict_sweep.py:53-54,110-113`; `results/supervised_summary.md:29-30`; `results/course_supervised_baselines.md:4,37`.
   - **Bài giảng:** Day 1, trang 36 (semi-supervised khác pseudo-label).

36. **STING khác DBSCAN và K-Means ở điểm nào (đề tài 6)?** — STING chia không gian thành lưới phân cấp, mỗi ô giữ thống kê (count/mean/std) và gom các ô "dày" (`count >= min_count`) liền kề; số cụm k là đầu ra của mật độ lưới, không phải tham số bắt buộc như K-Means. K-Means phải chọn k trước và luôn gán mọi điểm vào cụm (noise_ratio 0.0 trong pooled `results/metrics.csv`). DBSCAN dựa mật độ điểm + bán kính `eps`, cũng có nhãn nhiễu. Trên panel pooled 2011–2023: STING đóng băng k=3, noise 0.196; DBSCAN eps=0.2 noise 0.142, ARI so với STING 0.647; k-means k=2 ARI 0.166 — ba phương pháp phân vùng khác nhau, đề 6 bắt grid-based.
   - **Hỏi bẫy:** "K-Means k=3 cho cùng k=3 với STING?" — Không; STING k=3 từ lưới min_count=5, k-means k=3 ARI_vs_sting chỉ 0.139.
   - **Repo:** `src/sting.py:8-13`; `results/metrics.csv:2-4,7`; `README.md:10`.
   - **Bài giảng:** Day 1, trang 12 (đề 6 grid-based; K-Means/DBSCAN là đề khác).

37. **Vì sao ưu tiên macro-F1 thay vì accuracy khi holdout mất cân 11/48?** — Holdout một lần 2023→2024 có 59 tỉnh: lớp 0 (ngoại vi STING) = 11, lớp 1 (vùng dày) = 48 — tỉ lệ 48/59 ≈ 0.814. Chiến lược luôn đoán 1 đạt accuracy 0.814 trong khi bỏ hết 11 tỉnh lớp 0. NB có accuracy holdout 0.746 (cao hơn majority 0.186) nhưng macro-F1 0.566 phản ánh cả hai lớp; majority macro-F1 chỉ 0.157. Macro-F1 là trung bình F1 từng lớp nên phạt bỏ rơi lớp thiểu số — phù hợp Day 2 khi đọc confusion matrix, không chỉ tổng đúng. CV cũng chọn theo macro-F1 vì prevalence nhãn 1 trôi từ 0.000 (2011) đến 0.917 (2021).
   - **Hỏi bẫy:** "Accuracy 0.746 là rất cao?" — Cao hơn majority nhưng thấp hơn luôn-đoán-1 (0.814); phải đọc macro-F1 và `results/figs/course_confusion_matrix.png`.
   - **Repo:** `results/course_supervised_baselines.md:28-29`; `results/course_supervised_baselines.csv:2-3`; `results/supervised_summary.md:31`; `scripts/course_supervised_baselines.py:65-68`.
   - **Bài giảng:** Day 2, trang 30-34.
