# Models — artifact đã huấn luyện

Tất cả model là **local, deterministic** (seed cố định, không dịch vụ ngoài).
Retrain 2026-11-14 tái lập **byte-identical** cho cả 4 binary — chỉ `predict_config.json.frozen_at` đổi ngày.

| File | Loại | Mục đích | Tái tạo bằng |
|---|---|---|---|
| `predict_config.json` | cấu hình | Cặp chỉ tiêu + tham số STING **đóng băng** theo quy trình train-only (≤2020 chọn, 2021–2022 kiểm, 2024 không tham gia) | `python scripts/predict_sweep.py` |
| `sting_predict_model.pkl` | STING (tự viết) | Phân cụm không giám sát: fit PAPI 2011–2023 → gán cụm ngoài mẫu 2024 (`-1` = nhiễu/ngoài vùng học) | `python scripts/predict_demo.py` |
| `sting_predict_scaler.json` | metadata | mean/scale z-score + nhãn chỉ tiêu + provenance của model STING | cùng `predict_demo.py` |
| `sup_ridge.joblib` | sklearn Pipeline | Hồi quy: dự báo `6.1 Y tế công lập` năm t+1 từ 8 sub-dimension năm t. Được CV train-only chọn (R²=0.265) | `python scripts/predict_supervised.py` |
| `sup_rf.joblib` | RandomForestRegressor | Ứng viên hồi quy cùng bài toán (R² CV=0.197, MAE holdout thấp hơn ridge nhưng không được chọn) | cùng `predict_supervised.py` |
| `sup_classifier.joblib` | classifier CV-chọn (hiện: Pipeline StandardScaler + LogisticRegression) | Phân loại pseudo-label STING: dự báo nhãn 0/1 (ngoại vi/vùng dày) năm t+1 từ 8 chỉ số năm t | cùng `predict_supervised.py` |

## Chỉ số chính (holdout 2023→2024, một lần)

- **STING 2024**: coverage 79% (48/61 xếp cụm, 13 nhiễu); train k=3, noise 20%.
- **Hồi quy**: Ridge MAE 0.0640 / RMSE 0.0769 / R² 0.381 — tốt hơn carry-forward (MAE 0.0683, giảm 6.3%). RF MAE 0.0616 nhưng không được chọn vì CV train-only.
- **Phân loại pseudo-label** (phụ): classifier CV-chọn (hiện LogisticRegression) macro-F1 0.541 vs majority 0.157 — mức khớp nhãn do STING sinh, **không phải** accuracy so với ground truth xã hội.

## Thứ tự retrain đầy đủ

```powershell
python scripts/predict_sweep.py       # 1) chốt cấu hình (ghi predict_config.json)
python scripts/predict_demo.py        # 2) train STING + predict 2024
python scripts/predict_supervised.py  # 3) train model có giám sát
```

Đầu vào: `data/processed/papi_panel_63_2011_2024.csv` (tái tạo bằng `python scripts/build_panel.py`).
Chi tiết pipeline & giới hạn đánh giá: [`../README.md`](../README.md) mục "Dự đoán";
kết quả số: [`../results/predict_summary.md`](../results/predict_summary.md),
[`../results/supervised_summary.md`](../results/supervised_summary.md).

## Cách nạp

```python
import json, joblib, sys
sys.path.insert(0, "src")
import numpy as np
from sting import STING

sting = STING.load("models/sting_predict_model.pkl")
info = json.load(open("models/sting_predict_scaler.json", encoding="utf-8"))
z = (np.array([[1.9, 1.9]]) - info["mean"]) / info["scale"]   # [sd_4_2, sd_6_1]
print(sting.predict(z))

ridge = joblib.load("models/sup_ridge.joblib")
print(ridge.predict(np.array([[1.5, 2.6, 2.0, 2.1, 1.9, 1.7, 1.9, 1.8]])))
```
