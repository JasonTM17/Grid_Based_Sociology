"""Huấn luyện STING trên PAPI 2011–2023 và DỰ ĐOÁN cụm cho 63 tỉnh năm 2024.

Ý tưởng: mô hình "học" cấu trúc lưới từ dữ liệu quá khứ (811 dòng, 2011–2023),
lưu xuống file local, rồi dự đoán cụm cho năm mới nhất (2024) mà KHÔNG cần
huấn luyện lại — minh hoạ khả năng predict() của STING.

Cặp chỉ tiêu (chọn qua quét các cặp sub-dimension phủ đủ 2011–2023, xem
plans/.../phase-02 — tiêu chí: k=3 cụm, nhiễu thấp, phủ dự đoán cao):
  - sd_5_4 = "5.4 Dịch vụ hành chính cấp xã/phường" (thang 0,33–3,33)
  - sd_6_2 = "6.2 Giáo dục tiểu học công lập"        (thang 0,25–2,5)

Cấu hình: STING(n_levels=3, factor=3, min_count=5), gom cụm ở mức lưới 2
(mức 0 là lưới thô 3×3 ô). Kiểm tra độ ổn định: min_count 5 và 6 cho kết quả
dự đoán giống hệt nhau.

Chạy: python scripts/predict_demo.py
Đầu ra:
  models/sting_papi_sd54_sd62.pkl  — model đã huấn luyện (STING.save)
  models/sting_papi_scaler.json    — tham số chuẩn hóa z-score của huấn luyện
  results/predict_all_years.csv    — cụm dự đoán cho 63 tỉnh × mọi năm
  results/predict_summary.md       — tóm tắt số liệu cho báo cáo/slide
  results/figs/predict_2024.png    — scatter: train + dự đoán 2024
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from sting import STING  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv"
MODELS = ROOT / "models"
RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"

FEATS = ["sd_5_4", "sd_6_2"]
FEAT_LABELS = {
    "sd_5_4": "5.4 Dịch vụ hành chính cấp xã/phường",
    "sd_6_2": "6.2 Giáo dục tiểu học công lập",
}
TRAIN_MAX_YEAR = 2023
TEST_YEAR = 2024
# Cấu hình chính (chọn qua quét ở Phase 2; ổn định: mc 5 ≡ mc 6)
N_LEVELS, FACTOR, MIN_COUNT, LEVEL = 3, 3, 5, 2

MODEL_PATH = MODELS / "sting_papi_sd54_sd62.pkl"
SCALER_PATH = MODELS / "sting_papi_scaler.json"
CSV_PATH = RESULTS / "predict_all_years.csv"
SUMMARY_PATH = RESULTS / "predict_summary.md"
FIG_PATH = FIGS / "predict_2024.png"


def main() -> int:
    for d in (MODELS, RESULTS, FIGS):
        d.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PANEL)
    train = df[df.year <= TRAIN_MAX_YEAR]
    test = df[df.year == TEST_YEAR]

    ptr = train[FEATS].dropna()
    pte = test[["province_code", "province_vi"] + FEATS].dropna()

    scaler = StandardScaler().fit(ptr)
    Xtr = scaler.transform(ptr)
    Xte = scaler.transform(pte[FEATS])

    # 1) Huấn luyện + gom cụm
    model = STING(n_levels=N_LEVELS, factor=FACTOR, min_count=MIN_COUNT).fit(Xtr)
    labels = model.cluster(level=LEVEL, connectivity=1)
    sizes = sorted(
        [int((labels == c).sum()) for c in range(model.n_clusters_)], reverse=True
    )
    noise_tr = float((labels == -1).mean())

    # 2) Lưu model local + tham số chuẩn hóa
    model.save(MODEL_PATH)
    scaler_info = {
        "features": FEATS,
        "feature_labels": FEAT_LABELS,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "sting": {
            "n_levels": N_LEVELS,
            "factor": FACTOR,
            "min_count": MIN_COUNT,
            "cluster_level": LEVEL,
        },
    }
    SCALER_PATH.write_text(json.dumps(scaler_info, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3) Nạp lại model TỪ FILE và dự đoán — chứng minh không cần huấn luyện lại
    loaded = STING.load(MODEL_PATH)
    assert np.array_equal(loaded.predict(Xtr), labels), "load() phải cho kết quả y hệt"
    pred_te = loaded.predict(Xte)

    # 4) Dự đoán cụm cho mọi năm (2024 là năm out-of-sample thật sự)
    rows = []
    for y in sorted(df.year.unique()):
        sub = df[df.year == y]
        mask = sub[FEATS].notna().all(axis=1)
        sub = sub[mask]
        if sub.empty:
            continue
        pred = loaded.predict(scaler.transform(sub[FEATS]))
        split = "train" if y <= TRAIN_MAX_YEAR else "test"
        for (_, r), c in zip(sub.iterrows(), pred):
            rows.append(
                {
                    "year": int(y),
                    "province_code": int(r["province_code"]),
                    "province_vi": r["province_vi"],
                    "sd_5_4": round(float(r["sd_5_4"]), 3),
                    "sd_6_2": round(float(r["sd_6_2"]), 3),
                    "pred_cluster": int(c),
                    "split": split,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    # 5) Tóm tắt
    cov = float((pred_te != -1).mean())
    dist = dict(sorted(Counter(pred_te.tolist()).items()))
    te2 = pte.copy()
    te2["pred_cluster"] = pred_te
    comp = (
        te2.groupby("pred_cluster")
        .agg(
            n=("province_vi", "size"),
            sd_5_4_mean=("sd_5_4", "mean"),
            sd_6_2_mean=("sd_6_2", "mean"),
            vi_du=("province_vi", lambda s: ", ".join(list(s)[:6])),
        )
        .round(2)
    )

    labels_2023 = out[(out.year == 2023)][["province_code", "pred_cluster"]]
    labels_2024 = out[(out.year == 2024)][["province_code", "pred_cluster"]]
    merged = labels_2023.merge(labels_2024, on="province_code", suffixes=("_23", "_24"))
    changed = int((merged.pred_cluster_23 != merged.pred_cluster_24).sum())
    crosstab = pd.crosstab(
        merged.pred_cluster_23, merged.pred_cluster_24, margins=True
    )

    train_profile = ptr.copy()
    train_profile["cluster"] = labels
    profile = (
        train_profile.groupby("cluster")
        .agg(n=(FEATS[0], "size"), sd_5_4=("sd_5_4", "mean"), sd_6_2=("sd_6_2", "mean"))
        .round(2)
    )

    lines = []
    lines.append("# Dự đoán cụm PAPI 2024 bằng STING (train 2011–2023)\n")
    lines.append(f"- Cặp chỉ tiêu: {FEAT_LABELS['sd_5_4']} × {FEAT_LABELS['sd_6_2']}")
    lines.append(
        f"- Cấu hình: STING(L={N_LEVELS}, factor={FACTOR}, min_count={MIN_COUNT}), "
        f"cluster level={LEVEL}; train n={len(ptr)}, test n={len(pte)}"
    )
    lines.append(
        f"- Kết quả train: {model.n_clusters_} cụm, kích thước {sizes}, nhiễu {noise_tr:.0%}"
    )
    lines.append(f"- Dự đoán 2024: phủ {cov:.0%} ({dist}); {changed}/{len(merged)} tỉnh đổi cụm so với 2023\n")
    lines.append("## Hồ sơ cụm (train)\n")
    lines.append(profile.to_markdown())
    lines.append("\n## Thành phần dự đoán 2024\n")
    lines.append(comp.to_markdown())
    lines.append("\n## Chuyển cụm 2023 → 2024 (chỉ tỉnh có đủ 2 chỉ tiêu cả 2 năm)\n")
    lines.append(crosstab.to_markdown())
    lines.append(
        "\nLưu ý: nhãn 2023 ở đây cũng do model gán (in-sample); các thay đổi sát "
        "ranh giới ô lưới có thể nhạy với ngưỡng cố định — không nên diễn giải "
        "quá mức các dịch chuyển nhỏ."
    )
    lines.append("")
    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")

    # 6) Hình scatter
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {0: "#4c72b0", 1: "#dd8452", 2: "#55a868", 3: "#8172b3", 4: "#937860"}
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    xa, ya = ptr[FEATS[0]].to_numpy(), ptr[FEATS[1]].to_numpy()
    noise_mask = labels == -1
    ax.scatter(xa[noise_mask], ya[noise_mask], s=14, c="#bbbbbb", alpha=0.5,
               label=f"train – nhiễu ({int(noise_mask.sum())})")
    for c in range(model.n_clusters_):
        m = labels == c
        if not m.any():
            continue
        ax.scatter(xa[m], ya[m], s=14, c=colors[c % 5], alpha=0.35,
                   label=f"train – cụm {c} ({int(m.sum())})")
    xt, yt = pte[FEATS[0]].to_numpy(), pte[FEATS[1]].to_numpy()
    te_noise = pred_te == -1
    ax.scatter(xt[te_noise], yt[te_noise], s=55, marker="x", c="#666666", linewidths=1.6,
               label=f"2024 – nhiễu ({int(te_noise.sum())})")
    for c in range(model.n_clusters_):
        m = pred_te == c
        if not m.any():
            continue
        ax.scatter(xt[m], yt[m], s=55, marker="o", c=colors[c % 5], edgecolors="black",
                   linewidths=0.7, label=f"2024 → cụm {c} ({int(m.sum())})")
    ax.set_xlabel(FEAT_LABELS["sd_5_4"] + " (thang 0,33–3,33)")
    ax.set_ylabel(FEAT_LABELS["sd_6_2"] + " (thang 0,25–2,5)")
    ax.set_title("STING học 2011–2023 → dự đoán cụm cho 2024 (out-of-sample)")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=150)
    plt.close(fig)

    print(f"train n={len(ptr)} | test n={len(pte)}")
    print(f"train: k={model.n_clusters_} sizes={sizes} noise={noise_tr:.0%}")
    print(f"du doan 2024: coverage={cov:.0%} dist={dist} doi cum 2023->2024: {changed}/{len(merged)}")
    print(f"da luu: {MODEL_PATH.name}, {SCALER_PATH.name}, {CSV_PATH.name}, {SUMMARY_PATH.name}, {FIG_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
