# Kịch bản giữa kỳ — Grid-based clustering với STING

Giữa kỳ trình bày định nghĩa và demo cơ bản. Nhóm minh họa cơ chế bằng lưới 3 × 3, kiểm chứng trên dữ liệu giả lập và giới thiệu ứng dụng PAPI đã chuẩn bị.

Mở slide trong `submissions/01-giua-ky`. Để chạy notebook ở máy trình chiếu, giải nén toàn bộ ZIP giữa kỳ và mở notebook ở thư mục gốc của gói. Dùng mục 4 để minh họa phép tính và mã. [Hướng dẫn demo](../../DEMO.md)

## Lời mở đầu có thể dùng

> Thưa thầy, nhóm em phụ trách chủ đề phân cụm dựa trên lưới và chọn biến thể rút gọn của STING. Nhóm em dùng ví dụ lưới 3 × 3 để minh họa cách đếm điểm, chọn ô dày và nối các ô thành cụm. Nhóm em cũng đã chuẩn bị dữ liệu PAPI 2011–2024 để giới thiệu thêm phần ứng dụng.

## Thời lượng dự kiến

| Slide | Thời gian | Nội dung cần nói và thao tác |
|---|---|---|
| 1 | 0:00–0:25 | Nêu chủ đề Grid-based clustering và thuật toán STING đã chọn. |
| 2 | 0:25–1:30 | Giải thích một dòng PAPI là một tỉnh trong một năm. Chỉ hai trục 4.2 và 6.1 cùng số hàng đủ điểm. |
| 3 | 1:30–2:55 | Chỉ cùng một tập điểm ở các mức lưới. Giải thích ô lưu số điểm và thống kê. |
| 4 | 2:55–6:00 | Chỉ công thức dưới hình. Chia độ dài trục cho số ô để có bề rộng Δ, đo vị trí từ biên dưới theo Δ rồi dùng `floor` và `clip` ở `sting.py` dòng 378–379. Chỉ ngưỡng ô dày và DFS ở dòng 133–158. Nối ý tưởng lưới thống kê và truy vấn từ trên xuống của bài gốc với cách tạo cụm tại một tầng của nhóm. |
| 5 | 6:00–7:30 | Đọc bảng đếm ở mục 2 của notebook. Ngưỡng 3 cho hai cụm 7 điểm và một điểm nhiễu. Giải thích hai vùng chỉ chạm góc. |
| 6 | 7:30–8:25 | Chỉ hai cụm tham chiếu của 240 điểm và sáu điểm nhiễu. Trong hai phân số, T đếm cặp cùng nhóm theo cả hai bộ nhãn và E là mức khớp kỳ vọng khi xáo nhãn. ARI 0,950 đo mức khớp sau hiệu chỉnh. |
| 7 | 8:25–9:40 | Nêu 869 quan sát, gồm 61 quan sát năm 2024. Dùng Lạng Sơn ở mục 4.2 để giải thích hai trục z-score và chỉ vùng ô dày. |
| 8 | 9:40–10:55 | Chỉ 56 ô dày tạo 3 vùng rồi nhắc K-means chọn k = 2 trong 2–5. Đọc số cụm và nhiễu trên 869 điểm, silhouette trên 680 điểm giao. |
| 9 | 10:55–12:20 | Giải thích vì sao 869 điểm STING giữ cùng ô khi dựng lại lưới sau z-score. Nêu 68 điểm đổi cụm K-means và 8 điểm đổi trạng thái nhiễu DBSCAN khi đối chiếu. |
| 10 | 12:20–14:45 | Mục 4.8 đặt điểm đã quan sát năm 2024 lên lưới 2011–2023. Nêu 48 tỉnh ở cụm lớn, 13 tỉnh ở ô thưa và 2 tỉnh thiếu điểm. Đọc từ điểm gốc đến ô và nhãn của Lạng Sơn. |
| 11 | 14:45–15:00 | Cảm ơn thầy và các bạn, chuyển sang hỏi đáp. |

Ghi người trình bày và thời gian đo được vào [nhật ký luyện tập](rehearsal_log.md).

## Hỏi đáp trong 5 phút

Ưu tiên tự trả lời câu 1–10 trong câu hỏi giữa kỳ. Các câu 12–23 giải thích phần PAPI và nhiễu khi thầy hỏi thêm. Mỗi người cần nói được quan hệ Grid-based → STING → dữ liệu minh họa. Nếu thầy hỏi *"Sao lọc rồi mà vẫn nhiễu?"*, mở ngay biểu đồ 3 panel ở **Mục 4.3** của notebook để chỉ cho thầy thấy: (i) tiền xử lý chỉ loại dòng thiếu, còn `162/171` điểm `−1` vẫn nằm gọn trong khung `|z| ≤ 3`; (ii) xóa 9 điểm `|z| > 3` khiến biên co lại làm nhiễu tăng lên `20,1%`; (iii) cả 13 tỉnh `−1` năm 2024 nằm ở ô thưa `< 5` điểm tham chiếu (gồm cả tỉnh điểm cao như Hà Tĩnh, Bình Thuận, Quảng Ninh, Tây Ninh). [Câu hỏi giữa kỳ](qa_midterm.md)

## Chuẩn bị cuối kỳ

Cuối kỳ có báo cáo Word và notebook trong submissions/02-cuoi-ky, cùng slide vấn đáp tùy chọn. Phần này phát triển ứng dụng PAPI, đánh giá, độ nhạy và giới hạn của kết quả. Bộ câu hỏi cuối kỳ ở [qa_final.md](qa_final.md).
