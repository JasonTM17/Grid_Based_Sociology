# Định dạng báo cáo cuối kỳ — ghi chú nghiên cứu từ tài liệu mẫu

_Nguồn mẫu: file báo cáo môn khác của nhóm (OneDrive Đại học). Chỉ học **bố cục/định dạng/kỷ luật trình bày** — nội dung dưới đây tự soạn cho đồ án ML của chúng ta, không sao chép nội dung/số liệu của nhóm khác._

## Trang & lề (đo từ file mẫu)

- A4 21.0 × 29.7 cm; 3 sections (bìa / front matter / nội dung).
- Lề: trái 2.5 cm, phải 2.0 cm, trên 2.0 cm, dưới 2.0 cm.
- Font: Normal 13pt; Title 20pt bold; Heading 1 16pt bold; Heading 2 14pt bold; Heading 3 12pt bold.
  (Font chữ: mặc định theme — sẽ tự chọn Times New Roman hoặc giữ bộ theo mẫu khi soạn.)
- Header/footer trống ở section nội dung; có 3 sections (bìa → danh mục → nội dung).

## Cấu trúc front matter (theo mẫu)

1. Trang bìa (mẫu `BÌA TIỂU LUẬN.docx`: BỘ GIÁO DỤC VÀ ĐÀO TẠO → trường → khoa → tên đề tài → sinh viên/nhóm → Thành phố …, tháng … năm …).
2. TÓM TẮT (abstract ~½ trang).
3. LỜI MỞ ĐẦU (bối cảnh, lý do chọn đề tài).
4. MỤC LỤC (TOC tự động, đánh số trang).
5. DANH MỤC CHỮ VIẾT TẮT.
6. DANH MỤC HÌNH ẢNH + DANH MỤC BẢNG (caption tự động: "Hình N.x. …", "Bảng N.x. …").

## Kỷ luật trình bày quan sát được ở mẫu (đáng học theo)

- Đánh số chương/mục kiểu `CHƯƠNG 1.` → `1.1` → `1.1.1`; caption luôn kèm số + tên + được tham chiếu trong text.
- Mỗi hình/bảng đều có caption kiểu "Hình 2.1. <mô tả>" / "Bảng 3.2. <mô tả>" và được trích dẫn trong nội dung.
- Mục tiêu/phạm vi nằm ở Chương 1; phần lý thuyết ở Chương 2; phần lõi kỹ thuật ngâm sâu ở Chương 2–4; đánh giá thực nghiệm + hạn chế riêng; kết luận riêng; TÀI LIỆU THAM KHẢO cuối.
- Front matter đầy đủ (tóm tắt, mở đầu, mục lục, danh mục viết tắt, danh mục hình, danh mục bảng).

## Dàn ý áp dụng cho đồ án ML (Topic 6 – Grid-based clustering, PAPI)

_Soạn mới hoàn toàn theo dàn ý môn, bám yêu cầu báo cáo ML; chỉ mượn "khung" trên._

1. TÓM TẮT · 2. LỜI MỞ ĐẦU · 3. MỤC LỤC · 4. DANH MỤC CHỮ VIẾT TẮT · 5. HÌNH / BẢNG
6. CHƯƠNG 1. TỔNG QUAN — bối cảnh PAPI & quản trị công; mục tiêu; phạm vi (14 năm, 63 tỉnh); đóng góp.
7. CHƯƠNG 2. CƠ SỞ LÝ THUYẾT — grid-based clustering; STING (lưới phân cấp, thống kê ô, phân cụm, O(n)); baselines k-means/DBSCAN; chỉ số đánh giá; PAPI & các chỉ tiêu.
8. CHƯƠNG 3. DỮ LIỆU & TIỀN XỬ LÝ — nguồn + PROVENANCE; panel 882×41; kiểm tra chất lượng (PASS); **audit gãy thang đo**; chuẩn hóa/mã hóa tên tỉnh.
9. CHƯƠNG 4. PHƯƠNG PHÁP — STING tự cài chi tiết; chọn cấu hình (quy trình train-only, `predict_sweep.py`); mô hình giám sát dự báo năm sau; kiểm thử (22 test).
10. CHƯƠNG 5. KẾT QUẢ — phân cụm theo năm; so sánh STING vs k-means/DBSCAN (bảng metrics, tách noise); robustness (PCA d1–d6 + nhánh 8 chiều); bản đồ 63 tỉnh; **pipeline dự đoán** (STING.predict OUT-of-sample 2024; hồi quy Ridge vượt carry-forward; phân loại ngoại vi — kết quả ÂM TÍNH); hình dịch chuyển cụm.
11. CHƯƠNG 6. THẢO LUẬN & HẠN CHẾ — gãy thang đo xuyên năm (23/37 cột); nhiễu −1; lưới song song trục; dữ liệu khá đồng nhất; ngoại suy giữa các năm nhạy với thang đo; kết quả âm tính giữ nguyên.
12. CHƯƠNG 7. KẾT LUẬN & HƯỚNG PHÁT TRIỂN — tổng kết; hướng tiếp theo (rank-based normalization, mở rộng chỉ tiêu, dự báo nhiều năm).
13. TÀI LIỆU THAM KHẢO — PAPI; Mendeley (DOI 10.17632/wbk42j9wc8.1); Wang & Yang & Muntz (VLDB 1997); OD Mekong (GeoJSON).

**Kích thước kỳ vọng:** ML course report nên ~20–35 trang (mẫu môn khác của nhóm ~120+ trang — không cần lớn như vậy).
