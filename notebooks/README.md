# Danh mục Notebook (`notebooks/`)

Toàn bộ notebook thống nhất đã chạy đầy đủ từ ô đầu đến ô cuối (0 lỗi, đường dẫn tương đối, không tạo file trung gian trong repo nhờ kiểm tra khóa xuất bản tạm thời).

Trong tiền xử lý, cờ bước nhảy trên toàn panel phục vụ báo cáo chất lượng dữ liệu. Điều kiện kiểm tra chỉ tiêu đã chọn và bảng đặc trưng dùng dữ liệu đến năm chốt huấn luyện.

## Bộ đôi notebook nộp bài thống nhất

| Tệp | Mục đích | Cách tái lập |
|---|---|---|
| `Nhom15_STING_PAPI.ipynb` | Notebook phân tích **thống nhất hoàn chỉnh** (cơ chế STING 3×3 & 240 điểm giả lập, phân cụm PAPI 2011–2024, đối chứng K-Means/DBSCAN & z-score, thống kê bàn giao 63 tỉnh, dự báo bổ trợ, kiểm chứng ngoại lai & phụ lục đối chiếu học phần) | `python scripts/notebooks/gen_final_analysis.py` |
| `Nhom15_TienXuLy_PAPI.ipynb` | **Tiền xử lý PAPI** trực tiếp từ 14 bảng tính gốc (`882×41`), thử nghiệm làm sạch/biến đổi và pipeline 6 bước | `python scripts/notebooks/gen_preprocessing_notebook.py` |
