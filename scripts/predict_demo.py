"""Huấn luyện STING trên PAPI 2011–2023 và DỰ ĐOÁN cụm cho 63 tỉnh năm 2024.

Cấu hình (cặp chỉ tiêu + tham số STING) được ĐÓNG BĂNG TRƯỚC khi đánh giá:
`models/predict_config.json` do `scripts/predict_sweep.py` sinh theo quy trình
train-only (chọn trên ≤2020, kiểm trên tương lai giả 2021–2022; năm 2024 KHÔNG
tham gia bước chọn — tránh selection-on-test).

Quy trình:
  fit 2011–2023 → save() → load() lại từ file → predict() 2024 (out-of-sample).

Đầu ra:
  models/sting_predict_model.pkl   — model đã huấn luyện (pickle)
  models/sting_predict_scaler.json — tham số chuẩn hóa z-score + provenance
  results/predict_all_years.csv    — cụm dự đoán cho 63 tỉnh × mọi năm
  results/predict_summary.md       — tóm tắt số liệu (cho báo cáo/slide)
  results/figs/predict_2024.png    — scatter: train + dự đoán 2024

Chạy: python scripts/predict_demo.py
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sting import STING  # noqa: E402
from papi_pred_common import ROOT, load_config, load_panel  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MODELS = ROOT / "models"
RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"

TRAIN_MAX_YEAR = 2023
TEST_YEAR = 2024
MODEL_PATH = MODELS / "sting_predict_model.pkl"
SCALER_PATH = MODELS / "sting_predict_scaler.json"
CSV_PATH = RESULTS / "predict_all_years.csv"
SUMMARY_PATH = RESULTS / "predict_summary.md"
FIG_PATH = FIGS / "predict_2024.png"


def main() -> int:
    cfg = load_config()
    feats = cfg["features"]
    labels_map = cfg["feature_labels"]
    sp = cfg["sting"]
    for d in (MODELS, RESULTS, FIGS):
        d.mkdir(parents=True, exist_ok=True)

    df = load_panel()
    train = df[df.year <= TRAIN_MAX_YEAR]
    test = df[df.year == TEST_YEAR]
    ptr = train[feats].dropna()
    pte = test[["province_code", "province_vi"] + feats].dropna()

    scaler = StandardScaler().fit(ptr)
    Xtr = scaler.transform(ptr)
    Xte = scaler.transform(pte[feats])

    # 1) Huấn luyện + gom cụm
    model = STING(
        n_levels=sp["n_levels"], factor=sp["factor"], min_count=sp["min_count"]
    ).fit(Xtr)
    labels = model.cluster(level=sp["cluster_level"], connectivity=sp["connectivity"])
    sizes = sorted(
        [int((labels == c).sum()) for c in range(model.n_clusters_)], reverse=True
    )
    noise_tr = float((labels == -1).mean())

    # 2) Lưu model local + tham số chuẩn hóa
    model.save(MODEL_PATH)
    scaler_info = {
        "features": feats,
        "feature_labels": labels_map,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "sting": sp,
        "provenance": {
            "config": "models/predict_config.json",
            "frozen_via": "scripts/predict_sweep.py (train-only, không nhìn 2024)",
            "trained_on": f"PAPI 2011–{TRAIN_MAX_YEAR}",
        },
    }
    SCALER_PATH.write_text(
        json.dumps(scaler_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 3) Nạp lại TỪ FILE và dự đoán — không cần huấn luyện lại
    loaded = STING.load(MODEL_PATH)
    assert np.array_equal(loaded.predict(Xtr), labels), "load() phải khôi phục đúng"
    pred_te = loaded.predict(Xte)

    # 4) Dự đoán cụm cho mọi năm (2024 là năm out-of-sample duy nhất)
    rows = []
    for y in sorted(df.year.unique()):
        sub = df[df.year == y].dropna(subset=feats)
        if sub.empty:
            continue
        pred = loaded.predict(scaler.transform(sub[feats]))
        split = "train" if y <= TRAIN_MAX_YEAR else "test"
        for (_, r), c in zip(sub.iterrows(), pred):
            rows.append(
                {
                    "year": int(y),
                    "province_code": int(r["province_code"]),
                    "province_vi": r["province_vi"],
                    feats[0]: round(float(r[feats[0]]), 3),
                    feats[1]: round(float(r[feats[1]]), 3),
                    "pred_cluster": int(c),
                    "split": split,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    # 5) Tóm tắt trung thực
    cov = float((pred_te != -1).mean())
    dist = dict(sorted(Counter(pred_te.tolist()).items()))
    te2 = pte.copy()
    te2["pred_cluster"] = pred_te

    # hồ sơ cụm train — KHÔNG trộn dòng nhiễu (-1) vào bảng cụm
    prof = ptr.copy()
    prof["cluster"] = labels
    profile = (
        prof[prof.cluster >= 0]
        .groupby("cluster")
        .agg(n=(feats[0], "size"), **{feats[0]: (feats[0], "mean"), feats[1]: (feats[1], "mean")})
        .round(2)
    )

    comp = (
        te2[te2.pred_cluster >= 0]
        .groupby("pred_cluster")
        .agg(
            n=("province_vi", "size"),
            vi_du=("province_vi", lambda s: ", ".join(list(s)[:6])),
        )
    )

    # chuyển cụm 2023 → 2024, TÁCH RÕ chuyển thật vs chuyển sang/từ nhiễu
    a = out[out.year == TRAIN_MAX_YEAR][["province_code", "pred_cluster"]]
    b = out[out.year == TEST_YEAR][["province_code", "pred_cluster"]]
    m = a.merge(b, on="province_code", suffixes=("_prev", "_test"))
    real_move = int(((m.pred_cluster_prev >= 0) & (m.pred_cluster_test >= 0) &
                     (m.pred_cluster_prev != m.pred_cluster_test)).sum())
    to_noise = int(((m.pred_cluster_prev >= 0) & (m.pred_cluster_test == -1)).sum())
    from_noise = int(((m.pred_cluster_prev == -1) & (m.pred_cluster_test >= 0)).sum())
    stay_same = int((m.pred_cluster_prev == m.pred_cluster_test).sum())
    n_common = len(m)
    n_excluded = int(test[feats].isna().any(axis=1).sum()
                     + train[train.year == TRAIN_MAX_YEAR][feats].isna().any(axis=1).sum())

    # độ nhạy coverage theo min_count (coverage là ngưỡng-phụ thuộc — nói rõ)
    sens = []
    for mc2 in sorted({max(1, sp["min_count"] - 2), sp["min_count"], sp["min_count"] + 3}):
        m2 = STING(n_levels=sp["n_levels"], factor=sp["factor"], min_count=mc2).fit(Xtr)
        m2.cluster(level=sp["cluster_level"], connectivity=sp["connectivity"])
        p2 = m2.predict(Xte)
        sens.append((mc2, round(float((p2 != -1).mean()), 2), m2.n_clusters_))

    crosstab = pd.crosstab(
        m.pred_cluster_prev, m.pred_cluster_test, margins=True
    )

    lines = []
    lines.append("# Dự đoán cụm PAPI bằng STING — train 2011–2023, dự đoán 2024\n")
    lines.append(f"- Cặp chỉ tiêu: **{labels_map[feats[0]]}** × **{labels_map[feats[1]]}**")
    lines.append(
        f"- Cấu hình (đóng băng trước đánh giá qua `predict_sweep.py`): "
        f"STING(L={sp['n_levels']}, factor={sp['factor']}, min_count={sp['min_count']}), "
        f"level={sp['cluster_level']}; train n={len(ptr)}, test n={len(pte)}"
    )
    lines.append(
        f"- Kết quả train: {model.n_clusters_} cụm {sizes}, nhiễu {noise_tr:.0%} "
        f"(nhiễu = ô không đủ dày, KHÔNG nằm trong bảng hồ sơ cụm bên dưới)"
    )
    lines.append(f"- Dự đoán 2024 (đánh giá MỘT LẦN sau khi chốt cấu hình): phủ {cov:.0%}, phân bố {dist}\n")
    lines.append("## Hồ sơ cụm (train, chỉ điểm thuộc cụm)\n")
    lines.append(profile.to_markdown())
    lines.append("\n## Thành phần dự đoán 2024 (chỉ điểm thuộc cụm)\n")
    lines.append(comp.to_markdown() if len(comp) else "(không có)")
    lines.append("\n## Chuyển cụm 2023 → 2024\n")
    lines.append(crosstab.to_markdown())
    lines.append(
        f"\n- **Chuyển thật giữa 2 cụm**: {real_move}/{n_common} tỉnh; "
        f"sang nhiễu: {to_noise}; từ nhiễu ra: {from_noise}; giữ nguyên (kể cả nhiễu): {stay_same}."
    )
    lines.append(
        f"- Loại khỏi so sánh (thiếu chỉ tiêu): {n_excluded} dòng (2023 và/hoặc 2024)."
    )
    lines.append("\n## Độ nhạy coverage theo min_count (cảnh báo: coverage là ngưỡng-phụ thuộc)\n")
    lines.append("| min_count | coverage 2024 | số cụm |")
    lines.append("|---|---|---|")
    for mc2, cv2, k2 in sens:
        lines.append(f"| {mc2} | {cv2:.0%} | {k2} |")
    lines.append(
        "\n## Lưu ý phương pháp\n"
        "- Một lưới TOÀN CỤC cho mọi năm (nhãn so sánh được giữa các năm; các năm không độc lập — "
        "phù hợp cho mục tiêu dự đoán). Phân tích per-year ở Phase 5 là phương pháp KHÁC, không trộn số liệu.\n"
        "- Năm 2024 KHÔNG tham gia bước chọn cấu hình (xem `predict_sweep.py`); kết quả 2024 ở trên là out-of-sample.\n"
        "- Cặp chỉ tiêu nằm trong nhóm ĐÃ QUA AUDIT thang đo (xem `scripts/check_data.py`); các sub-dim có bước nhảy "
        "(sd_5_4 tại 2021, sd_2_1 tại 2018, …) đã bị loại khỏi pipeline dự đoán.\n"
        "- Nhãn 2023 cũng do model gán (in-sample); dịch chuyển sát ranh giới ô lưới có thể nhạy với ngưỡng cố định — "
        "không diễn giải quá mức các dịch chuyển nhỏ."
    )
    lines.append("")
    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")

    # 6) Hình scatter
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {0: "#4c72b0", 1: "#dd8452", 2: "#55a868", 3: "#8172b3", 4: "#937860"}
    xa, ya = ptr[feats[0]].to_numpy(), ptr[feats[1]].to_numpy()
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    noise_mask = labels == -1
    ax.scatter(xa[noise_mask], ya[noise_mask], s=14, c="#bbbbbb", alpha=0.5,
               label=f"train – nhiễu ({int(noise_mask.sum())})")
    for c in range(model.n_clusters_):
        mm = labels == c
        if not mm.any():
            continue
        ax.scatter(xa[mm], ya[mm], s=14, c=colors[c % 5], alpha=0.35,
                   label=f"train – cụm {c} ({int(mm.sum())})")
    xt, yt = pte[feats[0]].to_numpy(), pte[feats[1]].to_numpy()
    te_noise = pred_te == -1
    ax.scatter(xt[te_noise], yt[te_noise], s=55, marker="x", c="#666666", linewidths=1.6,
               label=f"2024 – nhiễu ({int(te_noise.sum())})")
    for c in range(model.n_clusters_):
        mm = pred_te == c
        if not mm.any():
            continue
        ax.scatter(xt[mm], yt[mm], s=55, marker="o", c=colors[c % 5], edgecolors="black",
                   linewidths=0.7, label=f"2024 → cụm {c} ({int(mm.sum())})")
    ax.set_xlabel(labels_map[feats[0]])
    ax.set_ylabel(labels_map[feats[1]])
    ax.set_title("STING học 2011–2023 → dự đoán cụm cho 2024 (out-of-sample)")
    ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=150)
    plt.close(fig)

    print(f"features={feats} | train n={len(ptr)} | test n={len(pte)}")
    print(f"train: k={model.n_clusters_} sizes={sizes} noise={noise_tr:.0%}")
    print(f"du doan 2024: coverage={cov:.0%} dist={dist} | chuyen that {real_move}/{n_common}"
          f" | sang nhieu {to_noise} | tu nhieu {from_noise} | loai {n_excluded}")
    print(f"da luu: {MODEL_PATH.name}, {SCALER_PATH.name}, {CSV_PATH.name}, {SUMMARY_PATH.name}, {FIG_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
