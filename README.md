# Đồ án Học máy — Phân cụm 63 tỉnh Việt Nam bằng STING (PAPI 2011–2024)

Đồ án môn Học máy · Chủ đề 6: **Grid-based (clustering)** · Domain: Sociology / History.

## Cấu trúc dự án

| Thư mục | Nội dung |
|---|---|
| `plans/` | Kế hoạch triển khai (không commit theo quy định công cụ) |
| `data/raw/papi/` | 14 workbook PAPI 2011–2024 (nguồn: papi.org.vn, dữ liệu công khai) |
| `data/raw/mendeley/` | Gói replication CC BY 4.0 (panel đối chiếu, crosswalk, centroid) |
| `data/raw/boundaries/` | GeoJSON 63 tỉnh (Open Development Vietnam, CC-BY-SA 4.0) |
| `data/processed/` | Panel sạch (kết quả Phase 2) |
| `src/` | Thư viện STING (tự viết từ đầu) |
| `scripts/` | Script dữ liệu & phân tích |
| `models/` | Model STING đã huấn luyện + tham số chuẩn hóa (dùng cho dự đoán) |
| `notebooks/` | Notebook nộp bài (Jupyter) |
| `tests/` | Unit test |
| `results/figs/` | Hình kết quả |
| `reports/` | Báo cáo, ghi chú |
| `slides/` | Slide trình bày |

## Nguồn dữ liệu & giấy phép

- **PAPI 2011–2024** — CECODES / VFF-CRT / RTA / UNDP. Tải từ <https://papi.org.vn/du-lieu-papi/>.
- **Gói replication** — Le et al., Mendeley Data, CC BY 4.0. DOI: 10.17632/wbk42j9wc8.1.
- **GeoJSON tỉnh** — Open Development Vietnam (OD Mekong), CC-BY-SA 4.0.

## Chạy nhanh

```powershell
# Kiểm tra môi trường
python -c "import pandas, openpyxl, plotly, sklearn; print('ok')"

# Unit test STING
python -m pytest tests -q

# Kiểm tra dữ liệu (sau khi panel được tạo ở Phase 2)
python scripts/check_data.py
```

Ghi chú: `jupyter` CLI chưa vào PATH — dùng `python -m jupyter` / `python -m nbconvert`.

## Dự đoán (train quá khứ → dự đoán năm mới)

Toàn bộ chạy **local, không cần dịch vụ ngoài**. Ba bước:

```powershell
python scripts/predict_sweep.py        # 1) chốt cấu hình (train-only, KHÔNG nhìn 2024)
python scripts/predict_demo.py         # 2) STING: học 2011–2023 → dự đoán cụm 2024
python scripts/predict_supervised.py   # 3) model ML có giám sát (scikit-learn)
```

1. **`predict_sweep.py`** — quét ứng viên cặp chỉ tiêu đã audit thang đo + cấu hình lưới;
   chọn bằng CV trên dữ liệu ≤2020, kiểm trên tương lai giả 2021–2022, rồi đóng băng vào
   `models/predict_config.json` (tránh "chọn theo kết quả test"). Bảng đầy đủ:
   `results/predict_config_search.csv`.
2. **`predict_demo.py`** — STING `fit → save → load → predict`: lưu model local
   (`models/sting_predict_model.pkl`) rồi nạp lại để dự đoán cụm cho 63 tỉnh năm 2024
   (năm chưa từng thấy). Kết quả: `results/predict_all_years.csv`,
   `results/predict_summary.md` (gồm độ nhạy theo `min_count` và chuyển cụm tách riêng
   "chuyển thật" vs "chuyển sang/từ nhiễu"), `results/figs/predict_2024.png`.
3. **`predict_supervised.py`** — model có giám sát, lưu local bằng joblib:
   - **Hồi quy (chính):** dự báo *6.1 Y tế công lập* năm t+1 từ 8 chỉ tiêu năm t —
     Ridge/RandomForest vượt baseline carry-forward ~10% MAE trên holdout 2023→2024.
     Lưu `models/sup_ridge.joblib`, `models/sup_rf.joblib`; kết quả
     `results/supervised_metrics.csv` + `results/supervised_summary.md`.
   - **Phân loại (phụ, kết quả âm tính):** dự báo "thuộc vùng cấu trúc hay ngoại vi"
     năm sau — không vượt baseline đủ tin cậy; ghi lại trung thực.

Nạp model để dự đoán điểm mới:

```python
import json, sys
sys.path.insert(0, "src")
import numpy as np
from sting import STING

model = STING.load("models/sting_predict_model.pkl")
info = json.load(open("models/sting_predict_scaler.json", encoding="utf-8"))
mean, scale = np.array(info["mean"]), np.array(info["scale"])

x = np.array([[1.9, 1.9]])           # [sd_4_2, sd_6_1] của tỉnh mới
z = (x - mean) / scale
print(model.predict(z))               # -> cụm dự đoán (hoặc -1: nhiễu/ngoài vùng học)

import joblib
ridge = joblib.load("models/sup_ridge.joblib")
print(ridge.predict(np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])))  # dự báo 6.1 năm sau
```

**Lưu ý thang đo:** nhiều sub-dimension PAPI đổi thang điểm giữa các năm (ví dụ `sd_5_4`
đổi từ 0.25–2.5 lên 0.33–3.33 tại 2021; `sd_2_1` đổi tại 2018). `scripts/check_data.py`
in danh sách cảnh báo gãy thang đo (bước nhảy trung bình năm > 0.25 điểm); pipeline dự đoán
chỉ dùng các chỉ tiêu nằm ngoài danh sách này.
