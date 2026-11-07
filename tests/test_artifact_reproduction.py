"""Gate tái lập mức artifact cho pipeline dự đoán STING.

Refit đúng theo công thức của ``scripts/predict_demo.py`` (StandardScaler +
STING fit trên năm ≤ 2023 với tham số đóng băng trong
``models/predict_config.json``, rồi ``predict`` cho từng năm) phải cho lại
CHÍNH XÁC toàn bộ nhãn ``pred_cluster`` trong ``results/predict_all_years.csv``
— 0 dòng lệch. STING không có yếu tố ngẫu nhiên nên đây là gate tất định:
mọi thay đổi ngữ nghĩa thuật toán phải làm gate này đỏ.

Chạy: python -m pytest tests/test_artifact_reproduction.py -q
"""
import json

import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from scripts.papi_pred_common import CONFIG_PATH, PANEL_PATH, ROOT
from sting import STING

PREDICT_CSV = ROOT / "results" / "predict_all_years.csv"
TRAIN_MAX_YEAR = 2023  # khớp TRAIN_MAX_YEAR của scripts/predict_demo.py

_REQUIRED = (PANEL_PATH, CONFIG_PATH, PREDICT_CSV)
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in _REQUIRED),
    reason="Thiếu artifact (panel / predict_config.json / predict_all_years.csv) "
    "— chạy python scripts/predict_demo.py để dựng lại",
)


def _refit_labels(df, feats, sting_params):
    """Refit scaler + STING như predict_demo.py và dự đoán cho mọi năm."""
    train = df[df.year <= TRAIN_MAX_YEAR]
    ptr = train[feats].dropna()
    scaler = StandardScaler().fit(ptr)
    model = STING(
        n_levels=sting_params["n_levels"],
        factor=sting_params["factor"],
        min_count=sting_params["min_count"],
    ).fit(scaler.transform(ptr))
    model.cluster(
        level=sting_params["cluster_level"],
        connectivity=sting_params["connectivity"],
    )

    rows = []
    for year in sorted(df.year.unique()):
        sub = df[df.year == year].dropna(subset=feats)
        if sub.empty:
            continue
        pred = model.predict(scaler.transform(sub[feats]))
        rows.append(
            pd.DataFrame(
                {
                    "year": int(year),
                    "province_code": sub["province_code"].to_numpy(),
                    "pred_cluster": pred,
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_predict_all_years_reproduces_from_frozen_config():
    """Refit từ config đóng băng phải cho lại 0/869 nhãn lệch so với artifact."""
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    df = pd.read_csv(PANEL_PATH)
    saved = pd.read_csv(PREDICT_CSV, encoding="utf-8-sig")

    refit = _refit_labels(df, cfg["features"], cfg["sting"])

    assert len(saved) == len(refit), (
        f"predict_all_years.csv có {len(saved)} dòng nhưng refit sinh {len(refit)} "
        "— panel hoặc logic dropna đã đổi so với lúc sinh artifact"
    )
    merged = saved.merge(
        refit,
        on=["year", "province_code"],
        how="left",
        suffixes=("_saved", "_refit"),
        validate="one_to_one",
    )
    assert len(merged) == len(saved), "year/province_code không là khóa duy nhất"
    n_diff = int((merged["pred_cluster_saved"] != merged["pred_cluster_refit"]).sum())
    assert n_diff == 0, (
        f"{n_diff}/{len(saved)} nhãn lệch khi refit từ config đóng băng "
        f"(rows lệch: {merged.loc[merged.pred_cluster_saved != merged.pred_cluster_refit, ['year', 'province_code']].to_dict('records')[:10]})"
    )
