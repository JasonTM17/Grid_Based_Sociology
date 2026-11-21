# Danh mục Notebook (`notebooks/`)

Toàn bộ notebook đã chạy đầy đủ từ ô đầu đến ô cuối (0 lỗi, 0 cảnh báo, đường dẫn tương đối).

## Notebook nộp bài & trình bày

| Tệp | Mục đích | Cách tái lập |
|---|---|---|
| `Nhom15_GiuaKy_STING_PAPI.ipynb` | Notebook nộp **giữa kỳ** (demo 2D, 869 điểm PAPI, phản biện nhiễu `−1`, K-Means/DBSCAN, gán năm 2024) | `python scripts/notebooks/gen_submission_demo.py` |
| `Nhom15_CuoiKy_STING_PAPI.ipynb` | Notebook nộp **cuối kỳ** (STING đầy đủ, đối chứng ngoại lai, dự báo 2 chỉ tiêu & Phụ lục Day 6) | `python scripts/notebooks/gen_final_analysis.py` |
| `Nhom15_Day4_TienXuLy_PAPI.ipynb` | Bài thực hành **tiền xử lý Day 4** chạy trực tiếp từ 14 workbook PAPI | Notebook tự chạy |
| `STING_PAPI_Demo_MoRong.ipynb` | Notebook minh họa mở rộng dùng cho kịch bản demo dài | `python scripts/notebooks/gen_midterm_demo.py` |

## Notebook thử nghiệm Phase 1–4 (`notebooks/thu-nghiem/`)

| Tệp | Mục đích | Cách tái lập |
|---|---|---|
| `thu-nghiem/STING_KiemChung_GiaLap.ipynb` | Kiểm chứng STING trên 2 cụm Gauss giả lập (Phase 1) | `python scripts/notebooks/gen_notebook_00.py` |
| `thu-nghiem/STING_KhaoSat_ThamSo.ipynb` | Khảo sát độ nhạy lưới/ngưỡng tham số STING (Phase 4) | `python scripts/notebooks/gen_params_sweep.py` |
