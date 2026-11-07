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
from sklearn.metrics import adjusted_rand_score
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

    # độ nhạy coverage + ổn định nhãn theo min_count (coverage là ngưỡng-phụ thuộc —
    # nói rõ). Ổn định nhãn so với dự đoán 2024 của cấu hình chốt (pred_te) trên cùng
    # len(pte) tỉnh đủ dữ liệu 2024: (i) ARI — bất biến với hoán vị nhãn, bắt buộc vì
    # nhãn cụm do thuật toán gán theo thứ tự ô dày và đổi min_count là đổi lưới;
    # (ii) số tỉnh đổi TRẠNG THÁI cụm↔nhiễu (p == -1 khác dấu với cấu hình chốt).
    sens = []
    te_by_mc: dict[int, np.ndarray] = {}
    for mc2 in sorted({max(1, sp["min_count"] - 2), sp["min_count"], sp["min_count"] + 3}):
        m2 = STING(n_levels=sp["n_levels"], factor=sp["factor"], min_count=mc2).fit(Xtr)
        m2.cluster(level=sp["cluster_level"], connectivity=sp["connectivity"])
        p2 = m2.predict(Xte)
        te_by_mc[mc2] = p2
        ari2 = float(adjusted_rand_score(p2, pred_te))
        flip2 = int(((p2 == -1) != (pred_te == -1)).sum())
        sens.append((mc2, round(float((p2 != -1).mean()), 2), m2.n_clusters_, ari2, flip2))

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
    lines.append(
        "| min_count | coverage 2024 | số cụm | ARI vs cấu hình chốt (2024) "
        "| đổi cụm↔nhiễu vs chốt (tỉnh) |"
    )
    lines.append("|---|---|---|---|---|")
    for mc2, cv2, k2, ari2, flip2 in sens:
        lines.append(f"| {mc2} | {cv2:.0%} | {k2} | {ari2:.3f} | {flip2} |")
    mc_lo = sens[0][0]
    lines.append(
        f"\n*Lưu ý phương pháp*: so khớp nhãn chính xác (exact agreement) giữa mc={mc_lo} "
        f"và cấu hình chốt mc={sp['min_count']} chỉ đạt {(te_by_mc[mc_lo] == pred_te).mean():.0%} "
        "— thấp do HOÁN VỊ NHÃN (nhãn 0/1/2 là quy ước gán theo thứ tự ô dày; đổi min_count là "
        "đổi lưới nên nhãn bị xáo trộn), còn ARI bất biến với hoán vị nhãn nên là thước đúng — "
        "không đọc nhầm thành gãy model."
    )

    # --- Hạn chế diễn giải: số liệu tính từ chính artifacts của script này ---
    import ast

    nn_total = int((labels >= 0).sum())
    share_largest_nn = sizes[0] / nn_total if nn_total else float("nan")
    largest_id = int(
        max(range(model.n_clusters_), key=lambda c: int((labels == c).sum()))
    )
    small_ids = [c for c in range(model.n_clusters_) if c != largest_id]
    small_pts = out[(out.pred_cluster >= 0) & (out.pred_cluster.isin(small_ids))]
    small_years = sorted(int(y) for y in small_pts.year.unique())
    small_in_2324 = int((small_pts.year >= TRAIN_MAX_YEAR - 1).sum())
    sel_sizes: list[int] = []
    sel_raw = cfg.get("selection_metrics", {}).get("sizes_top5")
    if isinstance(sel_raw, str):
        try:
            sel_sizes = [int(v) for v in ast.literal_eval(sel_raw)]
        except (ValueError, SyntaxError):
            sel_sizes = []
    lines.append("\n## Hạn chế diễn giải\n")
    _sel_note = (
        f"selection_metrics trong predict_config.json (fit ≤ 2020, sizes {sel_sizes}) ghi "
        f"{sel_sizes[0] / sum(sel_sizes):.1%} — metadata đó mô tả fit ≤ 2020, còn model.pkl đóng gói là "
        f"fit 2011–{TRAIN_MAX_YEAR} ({sizes})."
        if sel_sizes
        else ""
    )
    lines.append(
        f"- Cấu trúc “k=3” thực chất là 1 cụm khổng lồ + 2 cụm li ti: {share_largest_nn:.1%} điểm non-noise "
        f"thuộc cụm lớn nhất ({sizes[0]}/{nn_total}). {_sel_note}"
    )
    if small_years:
        lines.append(
            f"- Hai cụm li ti (nhãn {small_ids}) chỉ có điểm trong {small_years[0]}–{small_years[-1]} "
            f"và không nhận điểm nào từ {small_years[-1] + 1} trở đi: vùng đặc trưng tạo cụm nhỏ không còn "
            f"điểm mới — model fit 2011–{TRAIN_MAX_YEAR} dùng cho {TEST_YEAR} phải đọc theo ý đó (concept drift)."
        )
    lines.append(
        f"- “Chuyển thật giữa 2 cụm: {real_move}/{n_common}” là phát biểu rỗng (vacuous): cả {TRAIN_MAX_YEAR} lẫn "
        f"{TEST_YEAR} không có điểm nào thuộc cụm {", ".join(map(str, small_ids))} "
        f"({small_in_2324} điểm) — không phải bằng chứng về độ ổn định nhãn."
    )
    lines.append(
        f"- {dist.get(-1, 0)}/{len(pte)} tỉnh {TEST_YEAR} vào nhiễu do ô lưới thưa (count < min_count), không phải "
        "do scaler: STING bất biến với biến đổi affine từng chiều (z-score mỗi chiều), nguồn −1 là ô không đủ mật độ."
    )
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

    # 6) Hình scatter — trình bày theo chuẩn scripts/fig_style.py (palette
    #    Okabe–Ito, font/tiêu đề chuẩn, dòng nguồn PAPI, DPI in ấn 300).
    #    Chỉ đổi lớp trình bày; toàn bộ số liệu lấy từ kết quả tính phía trên.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from fig_style import (CLUSTER_COLORS, CLUSTER_LABELS, PALETTE,
                           add_source, new_fig, save_png, style_context)

    def cluster_color(c: int) -> str:
        """Màu cụm chuẩn: 0/1/2 theo CLUSTER_COLORS; k>3 dùng chuỗi phụ."""
        if c in CLUSTER_COLORS:
            return CLUSTER_COLORS[c]
        extras = [PALETTE["purple"], PALETTE["sky"]]
        return extras[(c - 3) % len(extras)]

    # Nhãn nhiễu cho legend: bỏ đuôi "(–1)" vì số điểm đã nằm trong ngoặc kế bên
    noise_name = CLUSTER_LABELS[-1].replace(" (–1)", "")

    with style_context():
        xa, ya = ptr[feats[0]].to_numpy(), ptr[feats[1]].to_numpy()
        fig, ax = new_fig(target="docx")  # 6.5 x 4.3 in — khớp cột docx + slide
        noise_mask = labels == -1
        ax.scatter(xa[noise_mask], ya[noise_mask], s=14, c=PALETTE["gray"], alpha=0.5,
                   label=f"train – {noise_name} ({int(noise_mask.sum())})")
        for c in range(model.n_clusters_):
            mm = labels == c
            if not mm.any():
                continue
            ax.scatter(xa[mm], ya[mm], s=14, c=cluster_color(c), alpha=0.35,
                       label=f"train – {CLUSTER_LABELS[c]} ({int(mm.sum())})")
        xt, yt = pte[feats[0]].to_numpy(), pte[feats[1]].to_numpy()
        te_noise = pred_te == -1
        ax.scatter(xt[te_noise], yt[te_noise], s=55, marker="x", c="#444444", linewidths=1.6,
                   label=f"2024 – {noise_name} ({int(te_noise.sum())})")
        for c in range(model.n_clusters_):
            mm = pred_te == c
            if not mm.any():
                continue
            ax.scatter(xt[mm], yt[mm], s=55, marker="o", c=cluster_color(c), edgecolors="black",
                       linewidths=0.7, label=f"2024 → {CLUSTER_LABELS[c]} ({int(mm.sum())})")
        # Nhãn trục theo cấu hình đóng băng. Điểm vẽ là GIÁ TRỊ GỐC của panel
        # (ptr/pte phía trên), KHÔNG phải z-score — STING chỉ chuẩn hóa bên trong
        # và bất biến với biến đổi affine từng chiều, nên tọa độ hiển thị giữ
        # nguyên điểm gốc. Cặp sd_* CHƯA đối chiếu workbook
        # (data/processed/papi_panel_scale_metadata.csv) nên KHÔNG được gắn thang
        # số ("thang điểm 1–10" chỉ xác nhận cho d1..d8); ghi rõ "điểm thành phần
        # PAPI" để người đọc không nhầm với điểm chiều chính d1..d8 (0–10) cũng
        # như với điểm chuẩn hóa.
        ax.set_xlabel(f"{labels_map[feats[0]]} (điểm thành phần PAPI)")
        ax.set_ylabel(f"{labels_map[feats[1]]} (điểm thành phần PAPI)")
        ax.set_title("STING học 2011–2023 → dự đoán cụm cho 2024 (out-of-sample)")
        ax.legend(loc="best", frameon=True, framealpha=0.9)
        ax.grid(alpha=0.25)
        # Nguồn/ngày tải theo data/raw/papi/PROVENANCE.md (không tự điền ngày render)
        add_source(fig, "PAPI — CECODES, VFF-CRT, RTA & UNDP", retrieved="2026-11-03")
        fig.tight_layout(rect=(0, 0.05, 1, 1))  # chừa lề dưới cho dòng nguồn
        # 300 DPI: 6.5 in × 300 ≈ 1950 px → ≥ 300 DPI hiệu dụng ở cột báo cáo ~16 cm
        save_png(fig, FIG_PATH, dpi=300)
        plt.close(fig)

    print(f"features={feats} | train n={len(ptr)} | test n={len(pte)}")
    print(f"train: k={model.n_clusters_} sizes={sizes} noise={noise_tr:.0%}")
    print(f"du doan 2024: coverage={cov:.0%} dist={dist} | chuyen that {real_move}/{n_common}"
          f" | sang nhieu {to_noise} | tu nhieu {from_noise} | loai {n_excluded}")
    # Chẩn đoán cặp đôi giữa các biến thể min_count (chỉ stdout): ARI + đổi trạng thái
    # cụm↔nhiễu giữa từng cặp biến thể — kiểm chứng chéo độc lập với bảng so-cấu-hình-chốt.
    _mc_list = sorted(te_by_mc)
    _pair_diag = "; ".join(
        f"mc{a}-mc{b}: ARI={adjusted_rand_score(te_by_mc[a], te_by_mc[b]):.3f}, "
        f"doi trang thai={int(((te_by_mc[a] == -1) != (te_by_mc[b] == -1)).sum())} tỉnh"
        for i, a in enumerate(_mc_list)
        for b in _mc_list[i + 1:]
    )
    print(f"so sanh cap doi theo min_count: {_pair_diag}")
    print(f"da luu: {MODEL_PATH.name}, {SCALER_PATH.name}, {CSV_PATH.name}, {SUMMARY_PATH.name}, {FIG_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
