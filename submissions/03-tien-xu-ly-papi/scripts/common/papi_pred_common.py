"""Tiện ích chung cho pipeline DỰ ĐOÁN PAPI (STING + model có giám sát).

- `load_panel()`  — đọc panel sạch 63 tỉnh × 2011–2024.
- `load_config()` — đọc cấu hình đã ĐÓNG BĂNG tại `models/predict_config.json`
  (do `scripts/analysis/predict_sweep.py` chọn theo quy trình train-only).
- `year_frame()`  — ma trận một năm với đủ chỉ tiêu + tên tỉnh.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv"
CONFIG_PATH = ROOT / "models" / "predict_config.json"

REGRESSION_FEATURES = [
    "sd_1_3", "sd_1_4", "sd_4_1", "sd_4_2",
    "sd_4_3", "sd_4_4", "sd_6_1", "sd_6_3",
]
REGRESSION_TARGET = "sd_6_1"

GRID_ASSIGNMENT_LABELS = {
    "in_cluster": "Thuộc cụm",
    "sparse_cell": "Ô thưa",
    "outside_grid": "Ngoài biên lưới",
    "filtered_cell": "Ô bị lọc theo tiêu chí bổ sung",
    "missing_score": "Thiếu chỉ tiêu",
    "nonfinite_score": "Điểm không hữu hạn",
}


FEATURE_LABELS = {
    "sd_1_3": "1.3 Chất lượng bầu cử",
    "sd_1_4": "1.4 Đóng góp tự nguyện",
    "sd_4_1": "4.1 Kiểm soát tham nhũng trong chính quyền địa phương",
    "sd_4_2": "4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công",
    "sd_4_3": "4.3 Công bằng trong tuyển dụng vào khu vực công",
    "sd_4_4": "4.4 Quyết tâm chống tham nhũng của chính quyền địa phương",
    "sd_6_1": "6.1 Y tế công lập",
    "sd_6_3": "6.3 Cơ sở hạ tầng căn bản",

    "d1": "Chiều 1 – Tham gia ở cấp cơ sở",
    "d2": "Chiều 2 – Minh bạch",
    "d3": "Chiều 3 – Trách nhiệm giải trình",
    "d4": "Chiều 4 – Kiểm soát tham nhũng",
    "d5": "Chiều 5 – Thủ tục hành chính công",
    "d6": "Chiều 6 – Cung ứng dịch vụ công",
}


def load_panel() -> pd.DataFrame:
    return pd.read_csv(PANEL_PATH)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def year_frame(df: pd.DataFrame, year: int, feats: list[str]) -> pd.DataFrame:
    """Các dòng của `year` có ĐỦ chỉ tiêu trong `feats` (kèm tên tỉnh)."""
    sub = df[df["year"] == year]
    sub = sub.dropna(subset=feats)
    return sub[["province_code", "province_vi", "year"] + feats].reset_index(drop=True)


def describe_grid_assignment(frame: pd.DataFrame, features, scaler, grid) -> pd.DataFrame:
    """Ghi nhãn và lý do gán cho từng quan sát trên lưới đã dựng."""
    features = list(features)
    rows = frame[["province_code", "province_vi", "year", *features]].reset_index(drop=True)
    raw = rows[features].to_numpy(dtype=float, na_value=np.nan)
    missing = np.isnan(raw).any(axis=1)
    complete = np.isfinite(raw).all(axis=1)
    rows["grid_status"] = np.where(missing, "missing_score", "nonfinite_score")
    rows["cluster"] = pd.Series(pd.NA, index=rows.index, dtype="Int64")
    rows["grid_cell"] = pd.Series(pd.NA, index=rows.index, dtype="string")
    rows["reference_count"] = pd.Series(pd.NA, index=rows.index, dtype="Int64")
    if not complete.any():
        return rows

    points = scaler.transform(rows.loc[complete, features])
    labels = grid.predict(points)
    rows.loc[complete, "cluster"] = labels
    rows.loc[complete, "grid_status"] = "outside_grid"
    within = ((points >= grid.bounds_min_) & (points <= grid.bounds_max_)).all(axis=1)
    if not within.any():
        return rows

    level = grid.cluster_level_
    indices, _ = grid._assign(points[within], grid.factor**level)
    keys = [tuple(map(int, index)) for index in indices]
    cells = grid.cells_[level]
    counts = np.array([cells[key].count if key in cells else 0 for key in keys])
    inside_rows = rows.index[complete][within]
    rows.loc[inside_rows, "grid_cell"] = [str(key) for key in keys]
    rows.loc[inside_rows, "reference_count"] = counts
    rows.loc[inside_rows, "grid_status"] = np.select(
        [labels[within] >= 0, counts < grid.min_count_],
        ["in_cluster", "sparse_cell"],
        default="filtered_cell",
    )
    return rows


def select_model_by_cv(metrics: pd.DataFrame) -> str:
    """Choose a model using CV scores only; holdout columns are not consulted."""
    candidates = metrics.dropna(subset=["value_cv"])
    if candidates.empty:
        raise ValueError("Không có CV score để chọn model.")
    best_index = candidates["value_cv"].idxmax()
    return str(candidates.loc[best_index, "model"])
