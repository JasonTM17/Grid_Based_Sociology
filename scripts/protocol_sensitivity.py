"""B5 — Độ nhạy giao thức chọn cấu hình STING (protocol sensitivity), in-memory.

Tái hiện TRONG BỘ NHỚ toàn bộ quy trình của ``scripts/predict_sweep.py`` rồi
chạy lại đủ 224 tổ hợp (28 cặp × 8 cấu hình) dưới HAI bộ lọc:

  (a) Bộ lọc CŨ (nguyên văn predict_sweep.py:56-59, 127-132) — bắt buộc tái
      lập đúng 4 dòng ``pass`` của ``results/predict_config_search.csv``;
  (b) Bộ lọc SỬA (đề xuất B5):
      - largest tính trên điểm KHÔNG nhiễu: sizes[0] / max(1, n_non-noise);
      - điều kiện MỚI MIN_CLUSTER_SHARE: cụm nhỏ nhất ≥ mcs × n_non-noise,
        mcs ∈ {0.02, 0.05, 0.10} (chính = 0.05);
      - các điều kiện khác giữ nguyên (k∈[2,6], noise≤0.25, coverage≥0.75;
        ngưỡng largest vẫn 0.85 nhưng trên mẫu số non-noise);
      - score_sửa dùng cùng trọng số, thay largest bằng largest_sửa.

Phạm vi: THAM KHẢO cho GV duyệt B5. Script KHÔNG ghi
``models/predict_config.json``, KHÔNG lưu model, KHÔNG thực thi
``scripts/predict_sweep.py``, KHÔNG sửa bất kỳ số đã công bố nào. Đầu ra MỚI:
``results/protocol_sensitivity.csv``, ``results/protocol_sensitivity.md``,
``results/figs/protocol_sensitivity_grid.png``.

Chạy (từ thư mục gốc repo): python -E scripts/protocol_sensitivity.py
Seed: 11 — pipeline không có bước ngẫu nhiên (STING là lưới thống kê
deterministic, StandardScaler deterministic), nên seed không tác động kết quả;
không có bootstrap/permutation nào được dùng trong phân tích này.
"""
from __future__ import annotations

import hashlib
import sys
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from check_data import scale_audit  # noqa: E402
from fig_style import add_source, new_fig, save_png, style_context  # noqa: E402
from papi_pred_common import load_panel  # noqa: E402
from sting import STING  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Giao thức gốc — sao chép NGUYÊN VĂN từ scripts/predict_sweep.py:48-59.
# Tính trung thực của bản sao được kiểm chứng bằng đối chiếu 224/224 dòng với
# results/predict_config_search.csv (mục 3 của results/protocol_sensitivity.md).
# ---------------------------------------------------------------------------
STABLE_SUBDIMS = ["sd_1_3", "sd_1_4", "sd_4_1", "sd_4_2",
                  "sd_4_3", "sd_4_4", "sd_6_1", "sd_6_3"]
CONFIGS = [
    (3, 3, 4, 2), (3, 3, 5, 2), (3, 3, 8, 2), (3, 3, 12, 2),
    (3, 4, 5, 2), (3, 4, 8, 2), (2, 3, 12, 1), (2, 4, 8, 1),
]
SELECT_MAX_YEAR = 2020
VALIDATE_YEARS = (2021, 2022)
K_RANGE = (2, 6)
NOISE_MAX = 0.25
LARGEST_MAX = 0.85
COV_MIN = 0.75

# Tham số B5 (theo đề bài lane; mcs chính = 0.05, dò nhạy 3 giá trị).
SEED = 11
MCS_MAIN = 0.05
MCS_GRID = (0.02, 0.05, 0.10)
FROZEN_NAME = "sd_4_2+sd_6_1"  # định danh theo đề bài — đối chiếu CSV công bố

OUT_CSV = ROOT / "results" / "protocol_sensitivity.csv"
OUT_MD = ROOT / "results" / "protocol_sensitivity.md"
OUT_PNG = ROOT / "results" / "figs" / "protocol_sensitivity_grid.png"
PUB_CSV = ROOT / "results" / "predict_config_search.csv"

PUB_COLS = ["features", "n_levels", "factor", "min_count", "level", "k",
            "sizes_top5", "noise_train", "largest_share",
            "coverage_2021_2022", "stable_mc_pm1", "score", "pass"]
CSV_COLS = PUB_COLS[:9] + ["n_train", "n_nonnoise_train", "n_val"] + PUB_COLS[9:] \
    + ["largest_share_nonnoise", "min_cluster_share_nonnoise", "score_mod",
       "pass_mod_mcs002", "pass_mod_mcs005", "pass_mod_mcs010",
       "fail_mod_mcs005"]


def candidate_pairs(train: pd.DataFrame) -> list[list[str]]:
    """Bản sao predict_sweep.py:65-77 — cặp feature từ allowlist, lọc trên train."""
    flagged = {feature for feature, _, _ in scale_audit(train)}
    eligible = [
        feature for feature in STABLE_SUBDIMS
        if feature in train.columns and feature not in flagged
    ]
    if len(eligible) < 2:
        raise ValueError("Ít hơn hai sub-dimension đủ điều kiện trong giai đoạn train.")
    return [list(pair) for pair in combinations(eligible, 2)]


def stable_under_mc_pm1(ptr_f, pva_f, feats, sc, pred, nl, f, mc, lv) -> bool:
    """Bản sao predict_sweep.py:97-107 — mc±1 có cho CÙNG dự đoán không."""
    Xte = sc.transform(pva_f[feats])
    for mc2 in (mc - 1, mc + 1):
        if mc2 < 1:
            continue
        m2 = STING(n_levels=nl, factor=f, min_count=mc2).fit(sc.transform(ptr_f[feats]))
        m2.cluster(level=lv, connectivity=1)
        if not np.array_equal(m2.predict(Xte), pred):
            return False
    return True


def evaluate_full(ptr_f: pd.DataFrame, pva_f: pd.DataFrame, feats: list[str],
                  nl: int, f: int, mc: int, lv: int) -> dict:
    """Một tổ hợp: cùng logic evaluate() (predict_sweep.py:80-90) + chỉ số B5.

    largest_cũ = sizes[0]/n_tổng (predict_sweep.py:87); largest_sửa =
    sizes[0]/max(1, n_non-noise); min_share = sizes[-1]/max(1, n_non-noise).
    """
    sc = StandardScaler().fit(ptr_f[feats])
    Xtr = sc.transform(ptr_f[feats])
    m = STING(n_levels=nl, factor=f, min_count=mc).fit(Xtr)
    lab = m.cluster(level=lv, connectivity=1)
    sizes = sorted([int((lab == c).sum()) for c in range(m.n_clusters_)],
                   reverse=True)
    noise = float((lab == -1).mean())
    n_total = int(len(lab))
    n_nonnoise = int((lab != -1).sum())
    largest = sizes[0] / n_total if sizes else 1.0
    largest_nn = sizes[0] / max(1, n_nonnoise) if sizes else 1.0
    min_share = sizes[-1] / max(1, n_nonnoise) if sizes else 0.0
    pred = m.predict(sc.transform(pva_f[feats]))
    cov = float((pred != -1).mean())
    k = int(m.n_clusters_)
    stable = stable_under_mc_pm1(ptr_f, pva_f, feats, sc, pred, nl, f, mc, lv)
    return {"k": k, "sizes": sizes, "noise": noise, "n_total": n_total,
            "n_nonnoise": n_nonnoise, "n_val": int(len(pva_f)),
            "largest": largest, "largest_nn": largest_nn,
            "min_share": min_share, "cov": cov, "stable": stable}


def fail_reasons(k: int, noise: float, largest_nn: float, min_share: float,
                 cov: float, mcs: float) -> str:
    """Các điều kiện bộ lọc SỬA bị phạm (chuỗi rỗng = đạt)."""
    reasons = []
    if not (K_RANGE[0] <= k <= K_RANGE[1]):
        reasons.append("k")
    if noise > NOISE_MAX:
        reasons.append("noise")
    if largest_nn > LARGEST_MAX:
        reasons.append("largest")
    if min_share < mcs:
        reasons.append("min_share")
    if cov < COV_MIN:
        reasons.append("coverage")
    return "+".join(reasons)


def run_sweep() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chạy đủ 224 tổ hợp in-memory; trả (bảng hiển thị, bảng giá trị thô)."""
    df = load_panel()
    ptr = df[df.year <= SELECT_MAX_YEAR]
    pva = df[df.year.isin(VALIDATE_YEARS)]

    candidates = candidate_pairs(ptr)
    rows, raws = [], []
    for feats in candidates:
        ptr_f = ptr[feats + ["year"]].dropna()
        pva_f = pva[feats].dropna()
        if len(ptr_f) < 500 or len(pva_f) < 100:
            continue
        for (nl, f, mc, lv) in CONFIGS:
            r = evaluate_full(ptr_f, pva_f, feats, nl, f, mc, lv)
            k, noise, cov, stable = r["k"], r["noise"], r["cov"], r["stable"]
            largest, largest_nn, min_share = r["largest"], r["largest_nn"], r["min_share"]
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
            score_mod = (
                cov - 0.5 * noise - 0.15 * largest_nn - 0.02 * abs(k - 3)
                + (0.03 if stable else 0.0)
            )
            fr = fail_reasons(k, noise, largest_nn, min_share, cov, MCS_MAIN)
            rows.append({
                "features": "+".join(feats),
                "n_levels": nl, "factor": f, "min_count": mc, "level": lv,
                "k": k, "sizes_top5": str(r["sizes"][:5]),
                "n_train": r["n_total"], "n_nonnoise_train": r["n_nonnoise"],
                "n_val": r["n_val"],
                "noise_train": round(noise, 3),
                "largest_share": round(largest, 3),
                "coverage_2021_2022": round(cov, 3),
                "stable_mc_pm1": stable,
                "score": round(score, 4),
                "pass": passed,
                "largest_share_nonnoise": round(largest_nn, 3),
                "min_cluster_share_nonnoise": round(min_share, 4),
                "score_mod": round(score_mod, 4),
                "pass_mod_mcs002": fail_reasons(k, noise, largest_nn, min_share,
                                                cov, 0.02) == "",
                "pass_mod_mcs005": fr == "",
                "pass_mod_mcs010": fail_reasons(k, noise, largest_nn, min_share,
                                                cov, 0.10) == "",
                "fail_mod_mcs005": fr if fr else "(đạt)",
            })
            raws.append({
                "features": "+".join(feats),
                "n_levels": nl, "factor": f, "min_count": mc, "level": lv,
                "noise_raw": noise, "largest_raw": largest,
                "largest_nn_raw": largest_nn, "min_share_raw": min_share,
                "cov_raw": cov, "score_raw": score, "score_mod_raw": score_mod,
            })
    tab = pd.DataFrame(rows)
    raw = pd.DataFrame(raws)
    if len(tab) != len(STABLE_SUBDIMS) * (len(STABLE_SUBDIMS) - 1) // 2 * len(CONFIGS):
        print(f"[CẢNH BÁO] Chỉ chạy được {len(tab)} tổ hợp (mong đợi 224).")
    return tab, raw


def crosscheck(tab: pd.DataFrame) -> dict:
    """Đối chiếu tái lập bộ lọc CŨ với results/predict_config_search.csv."""
    pub = pd.read_csv(PUB_CSV, encoding="utf-8-sig")
    rep = tab[PUB_COLS].copy()
    key = ["features", "n_levels", "factor", "min_count", "level"]
    merged = pub.merge(rep, on=key, how="inner", suffixes=("_pub", "_rep"))
    fields = ["k", "sizes_top5", "noise_train", "largest_share",
              "coverage_2021_2022", "stable_mc_pm1", "score", "pass"]
    row_ok = merged[fields[0] + "_pub"].eq(merged[fields[0] + "_rep"])
    for fld in fields[1:]:
        row_ok &= merged[fld + "_pub"].eq(merged[fld + "_rep"])
    rep_sorted = rep.sort_values(
        ["pass", "score", "stable_mc_pm1"], ascending=[False, False, False]
    ).reset_index(drop=True)
    order_same = rep_sorted.equals(pub[PUB_COLS].reset_index(drop=True))
    pub_pass = pub[pub["pass"]]
    frozen = pub_pass.sort_values(
        ["score", "stable_mc_pm1"], ascending=[False, False]
    ).iloc[0]
    return {
        "pub": pub, "n_pub": int(len(pub)), "n_rep": int(len(rep)),
        "n_inner": int(len(merged)),
        "n_match": int(row_ok.sum()),
        "fields_ok": {fld: bool(merged[fld + "_pub"].eq(merged[fld + "_rep"]).all())
                      for fld in fields},
        "order_same": bool(order_same),
        "n_pass_pub": int(pub["pass"].sum()),
        "frozen_pub": frozen,
        "pass_rows": pub_pass.sort_values(
            ["score", "stable_mc_pm1"], ascending=[False, False]),
    }


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(v: float, nd: int) -> str:
    return f"{v:.{nd}f}"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def make_figure(full: pd.DataFrame, frozen_key: dict) -> None:
    """Hình chẩn đoán B5: largest_sửa vs min-share, 224 tổ hợp + ngưỡng."""
    with style_context():
        fig, ax = new_fig()
        x_all = full["largest_nn_raw"].to_numpy()
        y_all = np.maximum(full["min_share_raw"].to_numpy(), 1e-4)
        pass_mod = full["pass_mod_mcs005"].to_numpy()
        pass_old = full["pass"].to_numpy()

        for mask, marker, color, label in [
            (~pass_mod & ~pass_old, "o", "#999999", "không đạt bộ lọc nào"),
            (~pass_mod & pass_old, "D", "#999999",
             "pass bộ lọc CŨ, không đạt bộ lọc sửa"),
            (pass_mod, "o", "#0072B2", "đạt bộ lọc sửa (mcs=0.05)"),
        ]:
            if mask.any():
                ax.scatter(x_all[mask], y_all[mask], s=26, marker=marker,
                           facecolor=color, edgecolor="white", linewidth=0.4,
                           label=label, zorder=3)

        ax.axvline(LARGEST_MAX, ls="--", lw=1.0, color="#444444", zorder=2)
        ax.text(LARGEST_MAX - 0.015, 1.05, f"largest ≤ {LARGEST_MAX}",
                ha="right", va="top", fontsize=9, color="#444444")
        for mcs in MCS_GRID:
            ax.axhline(mcs, ls=":", lw=0.9, color="#444444", zorder=2)
            ax.text(1.005, mcs, f"mcs={mcs}", ha="left", va="center",
                    fontsize=8, color="#444444")
        ax.annotate(
            f"đóng băng: {frozen_key['features']} ({frozen_key['cfg_str']})",
            xy=(frozen_key["largest_nn"], frozen_key["min_share"]),
            xytext=(12, 18), textcoords="offset points", fontsize=9,
            arrowprops={"arrowstyle": "->", "color": "#444444"}, zorder=4)

        ax.set_yscale("log")
        ax.set_xlim(0.0, 1.02)
        ax.set_ylim(5e-4, 1.5)
        ax.set_xlabel("largest sửa = sizes[0] / max(1, n_non-noise) (thang tuyến tính)")
        ax.set_ylabel("min cluster share trên non-noise (thang log)")
        ax.set_title("B5 — 224 tổ hợp STING dưới bộ lọc sửa (mcs = 0.05)")
        ax.legend(loc="lower left")
        add_source(fig, "PAPI — CECODES, VFF-CRT, RTA & UNDP",
                   retrieved="2026-11-03",
                   extra="phân tích B5, tính lại in-memory (seed 11)")
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        save_png(fig, OUT_PNG)


def write_md(full: pd.DataFrame, cc: dict) -> None:
    fp = cc["frozen_pub"]
    frozen_feats = str(fp["features"])
    frozen_cfg = (int(fp["n_levels"]), int(fp["factor"]),
                  int(fp["min_count"]), int(fp["level"]))
    cfg_str = "/".join(str(v) for v in frozen_cfg)
    fr_row = full[(full["features"] == frozen_feats)
                  & (full["n_levels"] == frozen_cfg[0])
                  & (full["factor"] == frozen_cfg[1])
                  & (full["min_count"] == frozen_cfg[2])
                  & (full["level"] == frozen_cfg[3])].iloc[0]
    pub_score = float(fp["score"])

    passers = full[full["pass_mod_mcs005"]]
    has_winner = bool(len(passers))
    if has_winner:
        winner = passers.sort_values(
            ["score_mod", "stable_mc_pm1", "features"], ascending=[False, False, True]
        ).iloc[0]
    top5 = full.sort_values(
        ["pass_mod_mcs005", "score_mod", "stable_mc_pm1", "features"],
        ascending=[False, False, False, True]).head(5)

    near = full[(full["k"] >= K_RANGE[0]) & (full["k"] <= K_RANGE[1])
                & (full["noise_train"] <= NOISE_MAX)
                & (full["coverage_2021_2022"] >= COV_MIN)]
    near_top = near.sort_values("min_cluster_share_nonnoise",
                                ascending=False).head(8)

    sens = []
    for mcs in MCS_GRID:
        col = {0.02: "pass_mod_mcs002", 0.05: "pass_mod_mcs005",
               0.10: "pass_mod_mcs010"}[mcs]
        sel = full[full[col]]
        if len(sel):
            b = sel.sort_values(["score_mod", "features"],
                                ascending=[False, True]).iloc[0]
            sens.append((mcs, len(sel),
                         f"{b['features']} ({b['n_levels']}/{b['factor']}/"
                         f"{b['min_count']}/{b['level']})",
                         fmt(float(b["score_mod"]), 4), "(đạt)"))
        else:
            b = full.sort_values(["score_mod", "features"],
                                 ascending=[False, True]).iloc[0]
            sens.append((mcs, 0,
                         f"{b['features']} ({b['n_levels']}/{b['factor']}/"
                         f"{b['min_count']}/{b['level']})",
                         fmt(float(b["score_mod"]), 4),
                         f"không pass: {b['fail_mod_mcs005']}"))

    L: list[str] = []
    L.append("# B5 — Protocol sensitivity: largest trên tổng n vs trên non-noise")
    L.append("")
    L.append("> **Trạng thái: PHÂN TÍCH THAM KHẢO cho GV duyệt B5.** Script chạy")
    L.append("> in-memory, KHÔNG ghi `models/predict_config.json`, không lưu model,")
    L.append("> không thực thi `scripts/predict_sweep.py`, không sửa số đã công bố.")
    L.append("")
    if has_winner:
        L.append("## 0. Tóm tắt")
        L.append("")
        L.append(f"- Bộ lọc CŨ: {cc['n_pass_pub']}/224 tổ hợp pass — tái lập đúng"
                 f" (mục 3).")
        L.append(f"- Bộ lọc SỬA (mcs=0.05): **{len(passers)}/224 tổ hợp pass**;")
        L.append(f"  ứng viên thắng: **{winner['features']}** "
                 f"(STING {winner['n_levels']}/{winner['factor']}/"
                 f"{winner['min_count']}/{winner['level']}), "
                 f"score_sửa = {fmt(float(winner['score_mod']), 4)}, "
                 f"stable_mc_pm1 = {winner['stable_mc_pm1']}.")
        L.append(f"- Khoảng cách với cấu hình đóng băng {frozen_feats} "
                 f"({cfg_str}): xem mục 6.")
    else:
        L.append("## 0. Tóm tắt")
        L.append("")
        L.append(f"- Bộ lọc CŨ: {cc['n_pass_pub']}/224 tổ hợp pass — tái lập đúng"
                 f" (mục 3).")
        L.append("- Bộ lọc SỬA (mcs=0.05): **KHÔNG có ứng viên nào trong 224 tổ"
                 " hợp pass** — đây chính là phát hiện quan trọng của B5: kết")
        L.append("  quả phân cụm của giao thức đóng băng KHÔNG vững dưới một bộ"
                 " lọc cân bằng cụm chặt hơn (cụm \"nhỏ\" hiện có chỉ là đơn vị")
        L.append("  vài điểm, tương đương nhiễu).")
        L.append(f"- Cấu hình đóng băng {frozen_feats} ({cfg_str}) tự nó cũng"
                 f" fail bộ lọc sửa: largest_sửa = "
                 f"{fmt(float(fr_row['largest_nn_raw']), 4)} > {LARGEST_MAX},"
                 f" min_share = {fmt(float(fr_row['min_share_raw']), 4)} <"
                 f" {MCS_MAIN}.")
    L.append("")
    L.append("## 1. Phạm vi & phương pháp")
    L.append("")
    L.append("- Dữ liệu: `data/processed/papi_panel_63_2011_2024.csv` (chỉ ĐỌC).")
    L.append("- Preprocessing tái hiện nguyên văn `scripts/predict_sweep.py`:")
    L.append("  train ≤ 2020, tương lai giả 2021–2022 (2024 không tham gia);")
    L.append("  StandardScaler fit trên train của từng cặp; dropna cặp gồm cột")
    L.append("  `year` (`predict_sweep.py:118`); ngưỡng 500/100 dòng")
    L.append("  (`predict_sweep.py:120`); allowlist 8 sub-dimension sau sàng")
    L.append("  mean-jump trên train (`predict_sweep.py:48`, `:65-77`).")
    L.append("- 224 tổ hợp = 28 cặp × 8 cấu hình STING")
    L.append("  `(n_levels, factor, min_count, level)` (`predict_sweep.py:49-52`).")
    L.append("- Seed: 11 (quy định). Pipeline không có bước ngẫu nhiên nào")
    L.append("  (STING lưới thống kê + StandardScaler đều deterministic); không")
    L.append("  dùng bootstrap/permutation, nên seed không tác động kết quả.")
    L.append("- Kết quả render không chứa thời gian chạy → chạy script 2 lần cho")
    L.append("  md/csv/png sha256 byte-giống (bảng hash ở mục 10).")
    L.append("")
    L.append("## 2. Hai bộ lọc được so sánh")
    L.append("")
    L.append("| Thành phần | Bộ lọc CŨ (đóng băng) | Bộ lọc SỬA (B5) |")
    L.append("| --- | --- | --- |")
    L.append("| k | ∈ [2, 6] | ∈ [2, 6] (giữ nguyên) |")
    L.append("| noise_train | ≤ 0.25 | ≤ 0.25 (giữ nguyên) |")
    L.append("| largest | sizes[0] / n_tổng ≤ 0.85 | sizes[0] / max(1, n_non-noise) ≤ 0.85 |")
    L.append("| cụm nhỏ nhất | (không có) | sizes[-1] / max(1, n_non-noise) ≥ mcs |")
    L.append("| coverage 21–22 | ≥ 0.75 | ≥ 0.75 (giữ nguyên) |")
    L.append("| điểm | cov − 0.5·noise − 0.15·largest − 0.02·&#124;k−3&#124; + 0.03·stable"
             " | cùng trọng số, largest → largest_sửa |")
    L.append("")
    L.append("Công thức điểm bộ lọc cũ: `predict_sweep.py:133-136`; điều kiện pass")
    L.append("cũ: `predict_sweep.py:127-132`. Điểm sửa chỉ thay biến `largest`")
    L.append("bằng định nghĩa non-noise — lựa chọn này được ghi rõ vì đề bài B5")
    L.append("định nghĩa lại biến `largest` ở bộ lọc sửa; bảng CSV giữ cả hai điểm")
    L.append("(`score`, `score_mod`) để đối chiếu.")
    L.append("")
    L.append("## 3. Đối chiếu tái lập bộ lọc CŨ (bắt buộc)")
    L.append("")
    L.append(f"- N dòng: published = {cc['n_pub']}, tái lập = {cc['n_rep']},"
             f" khớp khóa = {cc['n_inner']}.")
    L.append(f"- Khớp giá trị từng trường trên {cc['n_match']}/{cc['n_inner']}"
             f" dòng (k, sizes_top5, noise_train, largest_share,")
    L.append("  coverage_2021_2022, stable_mc_pm1, score, pass).")
    L.append(f"- Khớp cả THỨ TỰ 224 dòng sau sort như gốc: {cc['order_same']}.")
    L.append("")
    L.append("Bảng 4 dòng pass của `results/predict_config_search.csv` — giá trị")
    L.append("published (đọc từ CSV) và tái lập (tính in-memory lần này) trùng nhau:")
    L.append("")
    heads = ["features", "cfg", "k", "sizes_top5", "noise", "largest",
             "coverage", "stable", "score (công bố)"]
    rows4 = []
    for _, r in cc["pass_rows"].iterrows():
        cfg = f"{int(r['n_levels'])}/{int(r['factor'])}/{int(r['min_count'])}/{int(r['level'])}"
        rows4.append([str(r["features"]), cfg, str(int(r["k"])),
                      str(r["sizes_top5"]), fmt(float(r["noise_train"]), 3),
                      fmt(float(r["largest_share"]), 3),
                      fmt(float(r["coverage_2021_2022"]), 3),
                      str(bool(r["stable_mc_pm1"])), fmt(float(r["score"]), 4)])
    L.append(md_table(heads, rows4))
    L.append("")
    L.append("## 4. Bộ lọc SỬA — kết quả chính (mcs = 0.05)")
    L.append("")
    if has_winner:
        L.append(f"**Ứng viên thắng: `{winner['features']}` — STING "
                 f"{int(winner['n_levels'])}/{int(winner['factor'])}/"
                 f"{int(winner['min_count'])}/{int(winner['level'])}** với "
                 f"score_sửa = {fmt(float(winner['score_mod']), 4)} "
                 f"(score công thức cũ = {fmt(float(winner['score']), 4)}), "
                 f"k = {int(winner['k'])}, sizes = {winner['sizes_top5']}, "
                 f"noise = {fmt(float(winner['noise_train']), 3)}, "
                 f"largest_sửa = {fmt(float(winner['largest_nn_raw']), 4)}, "
                 f"min_share = {fmt(float(winner['min_share_raw']), 4)}, "
                 f"coverage = {fmt(float(winner['coverage_2021_2022']), 3)}, "
                 f"stable_mc_pm1 = {winner['stable_mc_pm1']}.")
    else:
        n_fail = {}
        for _, r in full.iterrows():
            for reason in str(r["fail_mod_mcs005"]).split("+"):
                if reason and reason != "(đạt)":
                    n_fail[reason] = n_fail.get(reason, 0) + 1
        L.append("**KHÔNG có ứng viên nào pass bộ lọc sửa (0/224).** Ghi đúng"
                 " như vậy theo yêu cầu B5. Số tổ hợp phạm từng điều kiện")
        L.append("(một tổ hợp có thể phạm nhiều điều kiện): "
                 + ", ".join(f"{k_}: {v}" for k_, v in sorted(n_fail.items()))
                 + ".")
        if len(near):
            gap = near_top.iloc[0]
            L.append("")
            L.append(f"Tổ hợp gần đạt nhất (trong nhóm đạt k/noise/coverage,"
                     f" {len(near)}/{cc['n_rep']} tổ hợp): "
                     f"`{gap['features']}` "
                     f"({int(gap['n_levels'])}/{int(gap['factor'])}/"
                     f"{int(gap['min_count'])}/{int(gap['level'])}) — "
                     f"min_share = {fmt(float(gap['min_cluster_share_nonnoise']), 4)}"
                     f" (còn thiếu {fmt(MCS_MAIN - float(gap['min_share_raw']), 4)}"
                     f" để đạt {MCS_MAIN}), largest_sửa = "
                     f"{fmt(float(gap['largest_nn_raw']), 4)}.")
    L.append("")
    L.append("## 5. Top-5 theo điểm bộ lọc sửa")
    L.append("")
    if not has_winner:
        L.append("Vì không có tổ hợp nào pass, bảng dưới là **top-5 toàn bộ 224**")
        L.append("theo score_sửa (không phải ứng viên đạt lọc) — dùng để thấy"
                 " điểm cao nhất nằm ở đâu và vì sao vẫn bị loại.")
        L.append("")
    heads = ["#", "features", "cfg", "k", "sizes_top5", "noise", "largest_sửa",
             "min_share", "coverage", "stable", "score (cũ)", "score_sửa",
             "fail (mcs=0.05)"]
    rows5 = []
    for i, (_, r) in enumerate(top5.iterrows(), 1):
        cfg = f"{int(r['n_levels'])}/{int(r['factor'])}/{int(r['min_count'])}/{int(r['level'])}"
        rows5.append([str(i), str(r["features"]), cfg, str(int(r["k"])),
                      str(r["sizes_top5"]), fmt(float(r["noise_train"]), 3),
                      fmt(float(r["largest_nn_raw"]), 4),
                      fmt(float(r["min_share_raw"]), 4),
                      fmt(float(r["coverage_2021_2022"]), 3),
                      str(bool(r["stable_mc_pm1"])), fmt(float(r["score"]), 4),
                      fmt(float(r["score_mod"]), 4), str(r["fail_mod_mcs005"])])
    L.append(md_table(heads, rows5))
    L.append("")
    if not has_winner and len(near):
        L.append("Top-8 tổ hợp đạt k/noise/coverage, xếp theo min_share giảm dần")
        L.append("(gần đạt bộ lọc sửa nhất — cho thấy khoảng cách còn bao xa):")
        L.append("")
        heads = ["features", "cfg", "k", "noise", "largest_sửa", "min_share",
                 "còn thiếu để đạt mcs=0.05", "vượt ngưỡng largest"]
        rowsn = []
        for _, r in near_top.iterrows():
            cfg = f"{int(r['n_levels'])}/{int(r['factor'])}/{int(r['min_count'])}/{int(r['level'])}"
            rowsn.append([
                str(r["features"]), cfg, str(int(r["k"])),
                fmt(float(r["noise_train"]), 3),
                fmt(float(r["largest_nn_raw"]), 4),
                fmt(float(r["min_share_raw"]), 4),
                fmt(max(0.0, MCS_MAIN - float(r["min_share_raw"])), 4),
                fmt(max(0.0, float(r["largest_nn_raw"]) - LARGEST_MAX), 4),
            ])
        L.append(md_table(heads, rowsn))
        L.append("")
    L.append(f"## 6. Khoảng cách với cấu hình đóng băng `{frozen_feats}` ({cfg_str})")
    L.append("")
    L.append("Định danh đóng băng suy ra từ `results/predict_config_search.csv`")
    L.append(f"(dòng pass điểm cao nhất) — trùng định danh đề bài B5: "
             f"{frozen_feats == str(fp['features'])}.")
    L.append("")
    L.append("| Đại lượng | Giá trị |")
    L.append("| --- | --- |")
    L.append(f"| score công bố (bộ lọc cũ) | {fmt(pub_score, 4)} |")
    L.append(f"| score tái lập (cùng công thức) | {fmt(float(fr_row['score']), 4)} |")
    L.append(f"| largest theo tổng n (cũ) | {fmt(float(fr_row['largest_raw']), 4)} |")
    L.append(f"| largest_sửa (non-noise) | {fmt(float(fr_row['largest_nn_raw']), 4)}"
             f" — vượt ngưỡng {LARGEST_MAX} thêm "
             f"{fmt(float(fr_row['largest_nn_raw']) - LARGEST_MAX, 4)} |")
    L.append(f"| min_share (non-noise) | {fmt(float(fr_row['min_share_raw']), 4)}"
             f" — thiếu {fmt(MCS_MAIN - float(fr_row['min_share_raw']), 4)}"
             f" so với mcs={MCS_MAIN} |")
    L.append(f"| score_sửa của cấu hình đóng băng | {fmt(float(fr_row['score_mod_raw']), 4)} |")
    L.append(f"| pass bộ lọc sửa (mcs=0.02/0.05/0.10) | "
             f"{bool(fr_row['pass_mod_mcs002'])} / "
             f"{bool(fr_row['pass_mod_mcs005'])} / "
             f"{bool(fr_row['pass_mod_mcs010'])} |")
    best = winner if has_winner else top5.iloc[0]
    best_label = ("ứng viên thắng bộ lọc sửa" if has_winner
                  else "top-1 toàn bảng (không pass bộ lọc sửa)")
    L.append(f"| khoảng cách score_sửa: {best_label} − đóng băng | "
             f"{fmt(float(best['score_mod']) - float(fr_row['score_mod']), 4)} |")
    L.append(f"| khoảng cách score (công thức cũ): top-1 − {fmt(pub_score, 4)} | "
             f"{fmt(float(best['score']) - pub_score, 4)} |")
    L.append("")
    best_name = (f"**{best['features']}** ({int(best['n_levels'])}/"
                 f"{int(best['factor'])}/{int(best['min_count'])}/"
                 f"{int(best['level'])})")
    if has_winner:
        L.append(f"Ứng viên mới {best_name} đạt {fmt(float(best['score_mod']), 4)}"
                 f" theo score_sửa; nếu chấm bằng công thức cũ thì "
                 f"{fmt(float(best['score']), 4)} — cách điểm công bố "
                 f"{fmt(pub_score, 4)} của cấu hình đóng băng một khoảng "
                 f"{fmt(float(best['score']) - pub_score, 4)}.")
    else:
        L.append(f"Không có ứng viên mới; top-1 toàn bảng là {best_name} với "
                 f"score_sửa {fmt(float(best['score_mod']), 4)} (công thức cũ: "
                 f"{fmt(float(best['score']), 4)}, so với {fmt(pub_score, 4)}: "
                 f"{fmt(float(best['score']) - pub_score, 4)}) — nhưng tổ hợp")
        L.append("này vẫn fail bộ lọc sửa nên không thể thay cấu hình đóng băng"
                 " mà không nới thêm giao thức (quyền của GV).")
    L.append("")
    L.append("## 7. Độ nhạy MIN_CLUSTER_SHARE ∈ {0.02, 0.05, 0.10}")
    L.append("")
    heads = ["mcs", "số tổ hợp pass", "tổ hợp điểm cao nhất", "score_sửa",
             "ghi chú"]
    L.append(md_table(heads, [[f"{mcs}", str(n), name, s, note]
                              for mcs, n, name, s, note in sens]))
    L.append("")
    largest_ok = full[full["largest_nn_raw"] <= LARGEST_MAX]
    if not has_winner and len(largest_ok):
        nlo = float(largest_ok["noise_train"].min())
        nhi = float(largest_ok["noise_train"].max())
        clo = float(largest_ok["coverage_2021_2022"].min())
        chi = float(largest_ok["coverage_2021_2022"].max())
        L.append(
            f"Kết quả không đổi theo mcs vì ràng buộc gắt nhất không phải"
            f" min_share: chỉ {len(largest_ok)}/{cc['n_rep']} tổ hợp có"
            f" largest_sửa ≤ {LARGEST_MAX}, và cả nhóm này có noise_train"
            f" {fmt(nlo, 3)}–{fmt(nhi, 3)}, coverage {fmt(clo, 3)}–{fmt(chi, 3)}"
            " — cụm cân bằng trên non-noise chỉ xuất hiện kèm mức nhiễu và mất"
            " phủ không chấp nhận được, nên nới mcs xuống 0.02 cũng không cứu"
            " được."
        )
        L.append("")
    L.append("## 8. stable_mc_pm1 của ứng viên")
    L.append("")
    if has_winner:
        L.append(f"- Ứng viên mới `{winner['features']}` "
                 f"({int(winner['n_levels'])}/{int(winner['factor'])}/"
                 f"{int(winner['min_count'])}/{int(winner['level'])}): "
                 f"stable_mc_pm1 = **{winner['stable_mc_pm1']}**"
                 + ("" if winner["stable_mc_pm1"]
                    else " — dự đoán 2021–2022 ĐỔI khi min_count lệch ±1"
                         " (điểm mất hệ số +0.03; lưu ý cả 4 dòng pass cũ cũng"
                         " có stable=False)."))
    else:
        b = top5.iloc[0]
        L.append(f"- Không có ứng viên pass; top-1 toàn bảng "
                 f"`{b['features']}` ({int(b['n_levels'])}/{int(b['factor'])}/"
                 f"{int(b['min_count'])}/{int(b['level'])}) có "
                 f"stable_mc_pm1 = **{b['stable_mc_pm1']}**.")
        if len(near):
            g = near_top.iloc[0]
            L.append(f"- Contender gần đạt bộ lọc sửa nhất trong nhóm đạt "
                     f"k/noise/coverage `{g['features']}` "
                     f"({int(g['n_levels'])}/{int(g['factor'])}/"
                     f"{int(g['min_count'])}/{int(g['level'])}): "
                     f"stable_mc_pm1 = **{g['stable_mc_pm1']}**"
                     + ("" if g["stable_mc_pm1"]
                        else " — trùng stable=False của 4 dòng pass cũ."))
    L.append("")
    L.append("## 9. Hình")
    L.append("")
    L.append("`results/figs/protocol_sensitivity_grid.png` — 224 tổ hợp trên")
    L.append("mặt phẳng (largest_sửa, min_share); vùng đạt bộ lọc sửa là x ≤ 0.85")
    L.append("và y ≥ 0.05; kim cương = 4 tổ hợp pass bộ lọc cũ.")
    L.append("")
    L.append("## 10. Kiểm định & giới hạn")
    L.append("")
    L.append("- File CSV đầy đủ 224 tổ hợp: `results/protocol_sensitivity.csv`")
    L.append("  (cột `pass` = bộ lọc cũ; `pass_mod_mcs002/005/010` = bộ lọc sửa")
    L.append("  theo ba mcs; `fail_mod_mcs005` = điều kiện bị phạm).")
    L.append(f"- sha256(`protocol_sensitivity.csv`) = `{sha256_of(OUT_CSV)}`")
    L.append(f"- sha256(`protocol_sensitivity_grid.png`) = `{sha256_of(OUT_PNG)}`")
    L.append("- Kiểm định deterministic: chạy `python -E scripts/protocol_sensitivity.py`")
    L.append("  2 lần từ thư mục gốc repo; md/csv/png phải sha256 byte-giống")
    L.append("  (người chạy đối chiếu ngoài script; output cố tình không chứa")
    L.append("  thời gian chạy).")
    L.append("- Giới hạn: phân tích chỉ DÙNG lại đúng dữ liệu train/validation")
    L.append("  của giao thức gốc (≤2022); 2024 không tham gia. Không có kiểm")
    L.append("  định thống kê mới ngoài bộ lọc/điểm đã nêu; không tự nới hoặc")
    L.append("  đổi ngưỡng đóng băng — mọi thay đổi giao thức thuộc quyền GV.")
    L.append("- Hằng số giao thức sao chép nguyên văn từ `predict_sweep.py:48-59`")
    L.append("  và được kiểm chứng bằng đối chiếu 224 dòng ở mục 3.")
    L.append("")
    OUT_MD.write_text("\n".join(L), encoding="utf-8", newline="\n")


def main() -> int:
    tab, raw = run_sweep()
    full = pd.concat([tab, raw.drop(columns=["features", "n_levels", "factor",
                                             "min_count", "level"])],
                     axis=1)
    cc = crosscheck(tab)

    full_sorted = full.sort_values(
        ["pass_mod_mcs005", "score_mod", "score", "features", "n_levels",
         "factor", "min_count", "level"],
        ascending=[False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    full_sorted[CSV_COLS].to_csv(OUT_CSV, index=False, encoding="utf-8-sig",
                                 lineterminator="\n")

    fp = cc["frozen_pub"]
    frozen_cfg = (int(fp["n_levels"]), int(fp["factor"]),
                  int(fp["min_count"]), int(fp["level"]))
    frow = full_sorted[(full_sorted["features"] == str(fp["features"]))
                       & (full_sorted["n_levels"] == frozen_cfg[0])
                       & (full_sorted["factor"] == frozen_cfg[1])
                       & (full_sorted["min_count"] == frozen_cfg[2])
                       & (full_sorted["level"] == frozen_cfg[3])].iloc[0]
    make_figure(full_sorted, {
        "features": str(fp["features"]),
        "cfg_str": "/".join(str(v) for v in frozen_cfg),
        "largest_nn": float(frow["largest_nn_raw"]),
        "min_share": max(float(frow["min_share_raw"]), 1.2e-4),
    })
    write_md(full_sorted, cc)

    print(f"Tổ hợp chạy: {len(full_sorted)}/224")
    print(f"Đối chiếu bộ lọc cũ: khớp {cc['n_match']}/{cc['n_inner']} dòng, "
          f"order_same={cc['order_same']}, pass cũ={cc['n_pass_pub']}")
    n_pass_mod = int(full_sorted['pass_mod_mcs005'].sum())
    print(f"Bộ lọc sửa mcs=0.05: {n_pass_mod}/224 pass; "
          f"mcs=0.02: {int(full_sorted['pass_mod_mcs002'].sum())}/224; "
          f"mcs=0.10: {int(full_sorted['pass_mod_mcs010'].sum())}/224")
    top1 = full_sorted.iloc[0]
    print(f"Top-1 score_sửa: {top1['features']} "
          f"({int(top1['n_levels'])}/{int(top1['factor'])}/"
          f"{int(top1['min_count'])}/{int(top1['level'])}) "
          f"score_mod={top1['score_mod']} fail={top1['fail_mod_mcs005']}")
    print(f"Ghi: {OUT_CSV}")
    print(f"Ghi: {OUT_MD}")
    print(f"Ghi: {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
