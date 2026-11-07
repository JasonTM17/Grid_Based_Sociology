"""Chọn cặp chỉ tiêu + cấu hình STING cho pipeline dự đoán — quy trình TRAIN-ONLY.

Mục đích: đóng băng lựa chọn TRƯỚC khi nhìn dữ liệu 2024 để tránh
"selection-on-test" (red team Methodology finding M2: cấu hình cũ chọn bằng
cách nhìn coverage 2024 — không hợp lệ).

Quy trình:
  1. Ứng viên = các cặp trong allowlist sub-dimension đã sàng lọc; chỉ dùng
     cột không bị mean-jump heuristic flag trong giai đoạn train ≤2020.
     Không đưa dimension d1..d6 vào sweep: thang danh nghĩa 1–10 không chứng
     minh tính tương đương cấu trúc; tài liệu PAPI cũng ghi nhận thay đổi
     sub-dimension/indicator ở một số chiều năm 2021.
     Loại vì bước nhảy thang điểm: sd_5_1/5_3/5_4 (2021), sd_2_1 (2018),
     sd_1_1 (2019), sd_1_2 (2016), sd_3_2 (2016/2018/2021), sd_6_4...
  2. Fit trên dữ liệu ≤ 2020; chấm điểm trên "tương lai giả" 2021–2022:
     coverage + k + độ nhiễu + độ vững (mc±1 cho ra cùng dự đoán).
     Năm 2024 KHÔNG xuất hiện trong script này.
  3. Chọn top-1 theo điểm cố định → ghi `models/predict_config.json`
     + `results/predict_config_search.csv`.

Chạy: python scripts/predict_sweep.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sting import STING  # noqa: E402
from check_data import scale_audit  # noqa: E402
from papi_pred_common import FEATURE_LABELS, ROOT, load_panel  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- Ứng viên đã sàng lọc trước, không bao gồm dimension-level scores ---
STABLE_SUBDIMS = ["sd_1_3", "sd_1_4", "sd_4_1", "sd_4_2", "sd_4_3", "sd_4_4", "sd_6_1", "sd_6_3"]
CONFIGS = [
    (3, 3, 4, 2), (3, 3, 5, 2), (3, 3, 8, 2), (3, 3, 12, 2),
    (3, 4, 5, 2), (3, 4, 8, 2), (2, 3, 12, 1), (2, 4, 8, 1),
]
SELECT_MAX_YEAR = 2020          # fit trên ≤ 2020
VALIDATE_YEARS = (2021, 2022)   # tương lai giả để chấm điểm
# Bộ lọc chất lượng (đặt trước, không tinh chỉnh theo kết quả 2024)
K_RANGE = (2, 6)
NOISE_MAX = 0.25
LARGEST_MAX = 0.85
COV_MIN = 0.75

OUTC_CSV = ROOT / "results" / "predict_config_search.csv"
OUT_JSON = ROOT / "models" / "predict_config.json"


def candidate_pairs(train: pd.DataFrame) -> list[list[str]]:
    """Cặp feature từ allowlist, lọc heuristic chỉ trên giai đoạn train.

    Không dùng validation/holdout years để quyết định eligibility.
    """
    flagged = {feature for feature, _, _ in scale_audit(train)}
    eligible = [
        feature for feature in STABLE_SUBDIMS
        if feature in train.columns and feature not in flagged
    ]
    if len(eligible) < 2:
        raise ValueError("Ít hơn hai sub-dimension đủ điều kiện trong giai đoạn train.")
    return [list(pair) for pair in combinations(eligible, 2)]


def evaluate(ptr: pd.DataFrame, pva: pd.DataFrame, feats, nl, f, mc, lv):
    sc = StandardScaler().fit(ptr[feats])
    Xtr = sc.transform(ptr[feats])
    m = STING(n_levels=nl, factor=f, min_count=mc).fit(Xtr)
    lab = m.cluster(level=lv, connectivity=1)
    sizes = sorted([int((lab == c).sum()) for c in range(m.n_clusters_)], reverse=True)
    noise = float((lab == -1).mean())
    largest = sizes[0] / len(lab) if sizes else 1.0
    pred = m.predict(sc.transform(pva[feats]))
    cov = float((pred != -1).mean())
    return k_of(m), sizes, noise, largest, pred, cov, sc


def k_of(m: STING) -> int:
    return int(m.n_clusters_)


def stable_under_mc_pm1(ptr_f, pva_f, feats, sc, pred, nl, f, mc, lv) -> bool:
    """mc±1 (nếu hợp lệ) có cho CÙNG dự đoán trên tập validation không."""
    Xte = sc.transform(pva_f[feats])
    for mc2 in (mc - 1, mc + 1):
        if mc2 < 1:
            continue
        m2 = STING(n_levels=nl, factor=f, min_count=mc2).fit(sc.transform(ptr_f[feats]))
        m2.cluster(level=lv, connectivity=1)
        if not np.array_equal(m2.predict(Xte), pred):
            return False
    return True


def main() -> int:
    df = load_panel()
    ptr = df[df.year <= SELECT_MAX_YEAR]
    pva = df[df.year.isin(VALIDATE_YEARS)]

    candidates = candidate_pairs(ptr)
    rows = []
    for feats in candidates:
        ptr_f = ptr[feats + ["year"]].dropna()
        pva_f = pva[feats].dropna()
        if len(ptr_f) < 500 or len(pva_f) < 100:
            continue
        for (nl, f, mc, lv) in CONFIGS:
            k, sizes, noise, largest, pred, cov, sc = evaluate(
                ptr_f, pva_f, feats, nl, f, mc, lv
            )
            stable = stable_under_mc_pm1(ptr_f, pva_f, feats, sc, pred, nl, f, mc, lv)
            passed = (
                K_RANGE[0] <= k <= K_RANGE[1]
                and noise <= NOISE_MAX
                and largest <= LARGEST_MAX
                and cov >= COV_MIN
            )
            score = (
                cov - 0.5 * noise - 0.15 * largest - 0.02 * abs(k - 3)
                + (0.03 if stable else 0.0)
            )
            rows.append(
                {
                    "features": "+".join(feats),
                    "n_levels": nl, "factor": f, "min_count": mc, "level": lv,
                    "k": k, "sizes_top5": str(sizes[:5]),
                    "noise_train": round(noise, 3),
                    "largest_share": round(largest, 3),
                    "coverage_2021_2022": round(cov, 3),
                    "stable_mc_pm1": stable,
                    "score": round(score, 4),
                    "pass": passed,
                }
            )

    out = pd.DataFrame(rows).sort_values(
        ["pass", "score", "stable_mc_pm1"], ascending=[False, False, False]
    )
    out.to_csv(OUTC_CSV, index=False, encoding="utf-8-sig")

    ok = out[out["pass"]].head(1)
    if ok.empty:
        print("KHÔNG có ứng viên nào đạt bộ lọc — nới điều kiện hoặc báo cáo trung thực.")
        return 1

    best = ok.iloc[0]
    feats = best["features"].split("+")
    cfg = {
        "frozen_at": datetime.now().date().isoformat(),  # sinh lúc chạy, không hardcode
        "selection_protocol": (
            "Candidates: pairwise allowlist of screened sub-dimensions; mean-jump heuristic checked on train years ≤2020; "
            "dimension-level d1–d6 excluded pending cross-year comparability evidence. "
            "Fit ≤2020; chấm trên tương lai giả 2021–2022; 2024 không tham gia chọn. "
            "Lọc: k 2–6, noise≤0.25, largest≤0.85, coverage≥0.75. "
            "Điểm = coverage - 0.5*noise - 0.15*largest - 0.02*|k-3| + 0.03*stable(mc±1)."
        ),
        "features": feats,
        "feature_labels": {c: FEATURE_LABELS[c] for c in feats},
        "sting": {
            "n_levels": int(best["n_levels"]),
            "factor": int(best["factor"]),
            "min_count": int(best["min_count"]),
            "cluster_level": int(best["level"]),
            "connectivity": 1,
        },
        "selection_metrics": {
            "k": int(best["k"]),
            "sizes_top5": best["sizes_top5"],
            "noise_train": float(best["noise_train"]),
            "coverage_2021_2022": float(best["coverage_2021_2022"]),
            "stable_mc_pm1": bool(best["stable_mc_pm1"]),
            "score": float(best["score"]),
        },
    }
    OUT_JSON.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Ứng viên đạt lọc: {int(out['pass'].sum())}/{len(out)}")
    print("Top-5 theo điểm:")
    print(out.head(5).to_string(index=False))
    print(f"\nĐÃ CHỐT: {feats} | STING {cfg['sting']} | metrics chọn: {cfg['selection_metrics']}")
    print(f"Ghi: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
