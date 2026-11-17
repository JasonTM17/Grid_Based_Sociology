# Kịch bản giữa kỳ — Grid-based clustering với STING

Giữa kỳ trình bày định nghĩa và demo cơ bản. Nhóm minh họa cơ chế bằng lưới 3 × 3, kiểm chứng trên dữ liệu giả lập và giới thiệu ứng dụng PAPI đã chuẩn bị.

Mở slide trong submissions/01-giua-ky và notebook cùng thư mục. Hướng dẫn thao tác ở [DEMO](../../DEMO.md). Bản có giải thích để tập nằm trong [study](../../study/Nhom15_GiuaKy_STING_PAPI_GiaiThich.ipynb).

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
| 7 | 8:30–10:30 | Giới thiệu ngắn PAPI. Hai chỉ tiêu là hai trục dữ liệu, lưới thô và mịn cho kết quả khác nhau. |
| 8 | 10:30–12:00 | Đọc bảng STING, K-means và DBSCAN. Xem số cụm, tỷ lệ nhiễu cùng silhouette. |
| 9 | 12:00–14:00 | Đổi riêng ngưỡng ô dày 3, 5 và 8. Giải thích vì sao số cụm và tỷ lệ gán cụm thay đổi. |
| 10 | 14:00–15:00 | Chốt cơ chế, kết quả minh họa và giới hạn khi áp dụng lên hai chỉ tiêu PAPI. |

Ghi người trình bày và thời gian đo được vào [nhật ký luyện tập](rehearsal_log.md).

## Hỏi đáp trong 5 phút

Ưu tiên tự trả lời câu 1–10 trong [câu hỏi giữa kỳ](qa_midterm.md). Các câu 12–17 giải thích phần PAPI khi thầy hỏi thêm. Mỗi người cần nói được quan hệ Grid-based → STING → dữ liệu minh họa.

## Chuẩn bị cuối kỳ

Cuối kỳ có báo cáo Word và notebook trong submissions/02-cuoi-ky, cùng slide vấn đáp tùy chọn. Phần này phát triển ứng dụng PAPI, đánh giá, độ nhạy và giới hạn của kết quả. Bộ câu hỏi cuối kỳ ở [qa_final.md](qa_final.md).
