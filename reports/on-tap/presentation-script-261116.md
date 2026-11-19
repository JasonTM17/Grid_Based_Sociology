# Kịch bản giữa kỳ — Grid-based clustering với STING

Giữa kỳ trình bày định nghĩa và demo cơ bản. Nhóm minh họa cơ chế bằng lưới 3 × 3, kiểm chứng trên dữ liệu giả lập và giới thiệu ứng dụng PAPI đã chuẩn bị.

Mở slide trong `submissions/01-giua-ky` và notebook cùng thư mục. Dùng mục 4 của notebook để tập giải thích phép tính và minh họa mã khi chiếu. [Hướng dẫn demo](../../DEMO.md)

## Lời mở đầu có thể dùng

> Thưa thầy, nhóm em phụ trách chủ đề phân cụm dựa trên lưới và chọn biến thể rút gọn của STING. Nhóm em dùng ví dụ lưới 3 × 3 để minh họa cách đếm điểm, chọn ô dày và nối các ô thành cụm. Nhóm em cũng đã chuẩn bị dữ liệu PAPI 2011–2024 để giới thiệu thêm phần ứng dụng.

## Thời lượng dự kiến

| Slide | Thời gian | Nội dung cần nói và thao tác |
|---|---|---|
| 1 | 0:00–0:30 | Nêu chủ đề Grid-based clustering và thuật toán STING đã chọn. |
| 2 | 0:30–2:00 | Chỉ rõ chủ đề, thuật toán, dữ liệu. Nêu ba ví dụ và giải thích một dòng PAPI là một tỉnh trong một năm. |
| 3 | 2:00–3:30 | Chỉ cùng một tập điểm ở các mức lưới. Giải thích ô lưu số điểm và thống kê. |
| 4 | 3:30–5:00 | Đi qua đếm điểm, chọn ô dày và nối các ô chung cạnh. Gọi đúng là biến thể rút gọn của STING. |
| 5 | 5:00–7:00 | Mở mục 2 của notebook. Ngưỡng 3 cho hai cụm 7 điểm và một điểm nhiễu. Giải thích hai vùng chỉ chạm góc. |
| 6 | 7:00–8:30 | Bộ giả lập có 240 điểm và hai nhóm tham chiếu. Giải thích ARI 0,950 đo mức khớp với nhãn khi sinh dữ liệu. |
| 7 | 8:30–10:30 | Nêu 869 quan sát đã có, gồm 61 quan sát năm 2024. Dùng ví dụ Lạng Sơn ở mục 4.2 để giải thích hai trục z-score. Chỉ vùng ô dày trên hình. |
| 8 | 10:30–12:00 | Chỉ 56 ô dày tạo 3 vùng. K-means chọn k = 2 trong các giá trị 2–5. Đọc số cụm và nhiễu trên 869 điểm, silhouette trên 680 điểm giao. Chỉ bảng chéo để giải thích cùng k = 3 vẫn ra cách chia khác. |
| 9 | 12:00–14:00 | Đọc ba nhánh sơ đồ. Chỉ các ô STING giữ nguyên và các vòng đen trên hình ở mục 4.6. Nêu 68 điểm đổi cụm K-means và 8 điểm đổi trạng thái nhiễu DBSCAN. Khi hỏi về bán kính, giải thích vòng gốc có cùng diện tích với elip lân cận sau đổi thang. |
| 10 | 14:00–15:00 | Chốt cơ chế, kết quả minh họa và giới hạn khi áp dụng lên hai chỉ tiêu PAPI. |

Ghi người trình bày và thời gian đo được vào [nhật ký luyện tập](rehearsal_log.md).

## Hỏi đáp trong 5 phút

Ưu tiên tự trả lời câu 1–10 trong câu hỏi giữa kỳ. Các câu 12–20 giải thích phần PAPI khi thầy hỏi thêm. Mỗi người cần nói được quan hệ Grid-based → STING → dữ liệu minh họa. [Câu hỏi giữa kỳ](qa_midterm.md)

## Chuẩn bị cuối kỳ

Cuối kỳ có báo cáo Word và notebook trong submissions/02-cuoi-ky, cùng slide vấn đáp tùy chọn. Phần này phát triển ứng dụng PAPI, đánh giá, độ nhạy và giới hạn của kết quả. Bộ câu hỏi cuối kỳ ở [qa_final.md](qa_final.md).
