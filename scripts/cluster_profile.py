"""Hồ sơ chuyên sâu các cụm STING — chỉ số ngoài & ổn định bootstrap (lane MỚI).

Script CHỈ THÊM phân tích mới vào file results/ MỚI — không ghi đè, không đổi
bất kỳ artifact/số nào đã công bố (predict_all_years.csv, external_validation,
predict_summary, ...). Chạy từ thư mục gốc repo::

    python -E scripts/cluster_profile.py

Ba phần:
  1. Nhãn cụm theo tỉnh-năm từ ``results/predict_all_years.csv`` (model đóng
     băng ``models/predict_config.json``). Refit tất định theo đúng công thức
     ``scripts/predict_demo.py`` được chạy để KIỂM CHỨNG khớp 100% nhãn train
     trước khi dùng (cùng gate ngữ nghĩa với tests/test_artifact_reproduction.py).
  2. Hồ sơ từng nhóm (nhiễu −1, cụm 0, 1, 2) × chỉ số ngoài ĐỘC LẬP với PAPI:
     PCI weighted (lưới đầy 2011–2022), tỷ lệ nghèo (các năm giao với panel),
     mật độ cơ sở y tế/1.000 dân 2020 (ODM + dân số GSO), GRDP/người
     (2018–2024), % dân số đô thị (GSO, các năm nguồn có số) — Kruskal–Wallis
     từng chỉ số (scipy, có sửa tie) + trung vị từng nhóm.
  3. Ổn định bootstrap: 200 lần resample CÓ hoàn lại theo TỈNH (cluster
     bootstrap panel; seed 11 cố định, ``numpy.random.default_rng(11)``),
     refit STING đúng cấu hình đóng băng trên mẫu, khớp nhãn mẫu về nhãn gốc
     bằng Jaccard tối đa từng cụm (ghép cặp tối ưu 1-1) → phân bố tỉ lệ giữ
     nhãn + silhouette CI 95%.

Đầu ra MỚI:
  results/cluster_profile.md
  results/cluster_profile.csv
  results/figs/deep_cluster_profile.png

Tất định: mọi số tự tính trong bộ nhớ từ CSV provenance (không hardcode);
phần ngẫu nhiên duy nhất là bootstrap với seed 11; không có datetime.now()
trong đầu ra → chạy 2 lần cho md/csv sha256 byte-giống.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fig_style import (CLUSTER_COLORS, CLUSTER_LABELS, PALETTE,  # noqa: E402
                       add_source, new_fig, save_png, style_context)
from papi_pred_common import ROOT, load_config, load_panel  # noqa: E402
from sting import STING  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- hằng số --
SEED = 11                 # seed cố định cho TOÀN BỘ phần ngẫu nhiên (đặc tả lane)
N_BOOT = 200              # số lần resample bootstrap theo tỉnh
TRAIN_MAX_YEAR = 2023     # khớp scripts/predict_demo.py (fit 2011–2023)

# Cửa sổ phân tích là ĐẶC TẢ của lane (không phải kết quả tính được):
PCI_YEARS = (2011, 2022)    # "lưới đầy 2011–2022" (2023–2024 chỉ Top-30)
GRDP_YEARS = (2018, 2024)   # nguồn GSO V03.12 chỉ phủ 2018–2024 (2024 sơ bộ)
HEALTH_YEAR = 2020          # snapshot ODM Health Facilities 2020

PROC = ROOT / "data" / "processed"
RES = ROOT / "results"
FIGS = RES / "figs"
LABELS_CSV = RES / "predict_all_years.csv"
PCI_CSV = PROC / "external_pci_63_full.csv"
POV_CSV = PROC / "external_poverty_63.csv"
ODM_CSV = PROC / "external_odm_health_63.csv"
GRDP_CSV = PROC / "external_gso_grdp_63.csv"
POP_CSV = PROC / "external_gso_population_63_full.csv"
MD_PATH = RES / "cluster_profile.md"
CSV_PATH = RES / "cluster_profile.csv"
FIG_PATH = FIGS / "deep_cluster_profile.png"

# Số chữ số thập phân khi làm tròn hiển thị, theo đơn vị từng chỉ số.
DECIMALS = {"pci": 3, "poverty": 2, "health": 6, "grdp": 2, "urban": 2}


def fmt_p(p: float) -> str:
    """Định dạng p-value gọn, khớp phong cách external_validation.py."""
    return "p < 1e-12" if p < 1e-12 else f"p = {p:.3g}"


def rnd(v, nd: int):
    """Làm tròn an toàn None/NaN → None (ghi CSV thành ô trống)."""
    if v is None:
        return None
    v = float(v)
    return None if np.isnan(v) else round(v, nd)


# ------------------------------------------------------------------- dữ liệu --
def load_labels() -> pd.DataFrame:
    """Nhãn cụm tỉnh-năm từ artifact của model đóng băng (đọc, không ghi)."""
    lab = pd.read_csv(LABELS_CSV)
    assert not lab.duplicated(["year", "province_code"]).any(), "nhãn trùng khóa"
    return lab


def load_fit_rows(lab: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """Dòng fit gốc: panel ≤2023 đủ chỉ tiêu (đọc panel READ-ONLY) + nhãn CSV.

    Panel ``data/processed/papi_panel_63_2011_2024.csv`` được đọc (không ghi)
    vì bootstrap phải resample trên ĐÚNG dữ liệu đã sinh nhãn gốc — file CSV
    nhãn chỉ lưu feature làm tròn 3 số thập phân.
    """
    panel = load_panel()
    fit = panel[panel.year <= TRAIN_MAX_YEAR].dropna(subset=feats).copy()
    key = ["year", "province_code"]
    tr_keys = set(map(tuple, lab.loc[lab.split == "train", key].to_numpy()))
    fit_keys = set(map(tuple, fit[key].to_numpy()))
    assert tr_keys == fit_keys, (
        "Bộ dòng fit (panel ≤2023 đủ chỉ tiêu) lệch với dòng split=train của "
        f"predict_all_years.csv (chênh {len(tr_keys ^ fit_keys)} khóa)"
    )
    fit = fit.merge(lab[key + ["pred_cluster"]], on=key, how="left",
                    validate="one_to_one")
    assert fit.pred_cluster.notna().all(), "dòng fit thiếu nhãn trong CSV"
    fit["pred_cluster"] = fit["pred_cluster"].astype(int)
    return fit


def verify_frozen_refit(fit: pd.DataFrame, feats: list[str], sp: dict):
    """Refit đúng công thức predict_demo.py trên dòng fit → so khớp nhãn CSV.

    Trả về ``(ok, X0, labels0)``: X0 là ma trận z-score của model gốc (dùng
    cho silhouette tham chiếu), labels0 là nhãn refit (phải == nhãn CSV).
    """
    scaler = StandardScaler().fit(fit[feats])
    X0 = scaler.transform(fit[feats])
    model = STING(n_levels=sp["n_levels"], factor=sp["factor"],
                  min_count=sp["min_count"]).fit(X0)
    labels0 = model.cluster(level=sp["cluster_level"],
                            connectivity=sp["connectivity"])
    ok = bool(np.array_equal(labels0, fit["pred_cluster"].to_numpy()))
    return ok, X0, labels0


def join_labels(d: pd.DataFrame, lab: pd.DataFrame, value_cols: list[str]):
    """Left-join nhãn cụm theo (year, province_code); trả về (đã join, thiếu)."""
    m = d.merge(lab[["year", "province_code", "pred_cluster"]],
                on=["year", "province_code"], how="left", validate="many_to_one")
    n_missing = int(m["pred_cluster"].isna().sum())
    j = m.dropna(subset=["pred_cluster"] + value_cols).copy()
    j["pred_cluster"] = j["pred_cluster"].astype(int)
    return j, n_missing


# ------------------------------------------------------- hồ sơ chỉ số ngoài --
def load_pci(lab):
    pci = pd.read_csv(PCI_CSV)
    d = pci[pci.year.between(*PCI_YEARS) & pci.pci_weighted_score.notna()]
    j, n_miss = join_labels(d, lab, ["pci_weighted_score"])
    meta = dict(key="pci", name="PCI weighted (VCCI–USAID)",
                unit="điểm tổng 0–100", col="pci_weighted_score",
                window=f"{PCI_YEARS[0]}–{PCI_YEARS[1]} (lưới đầy)")
    return j, n_miss, meta


def load_poverty(lab):
    pov = pd.read_csv(POV_CSV)
    years = sorted(set(pov.year.unique()) & set(lab.year.unique()))
    d = pov[pov.year.isin(years) & pov.poverty_rate_pct.notna()]
    j, n_miss = join_labels(d, lab, ["poverty_rate_pct"])
    meta = dict(key="poverty", name="Tỷ lệ nghèo (GSO V14.47)",
                unit="% dân số", col="poverty_rate_pct",
                window=(f"{years[0]}–{years[-1]} "
                        f"({len(years)} năm giao với panel)"))
    return j, n_miss, meta


def load_health(lab):
    odm = pd.read_csv(ODM_CSV)
    pop = pd.read_csv(POP_CSV)
    p20 = pop.loc[pop.year == HEALTH_YEAR,
                  ["province_code", "gso_pop_total_thousand"]]
    h = odm.merge(p20, on="province_code", how="left", validate="one_to_one")
    assert h.gso_pop_total_thousand.notna().all(), "dân số 2020 thiếu tỉnh"
    # pop tính bằng NGHÌN người → count / pop_nghìn = cơ sở trên 1.000 dân
    h["fac_per_1000"] = h["hospital_count_odm2020"] / h["gso_pop_total_thousand"]
    j, n_miss = join_labels(h, lab, ["fac_per_1000"])
    meta = dict(key="health", name="Mật độ cơ sở y tế/1.000 dân (OD Mekong)",
                unit="cơ sở/1.000 dân", col="fac_per_1000",
                window=f"{HEALTH_YEAR} (snapshot 1 năm)")
    return j, n_miss, meta


def load_grdp(lab):
    grdp = pd.read_csv(GRDP_CSV)
    d = grdp[grdp.year.between(*GRDP_YEARS)
             & grdp.grdp_per_capita_million_vnd.notna()]
    j, n_miss = join_labels(d, lab, ["grdp_per_capita_million_vnd"])
    meta = dict(key="grdp", name="GRDP/người (GSO V03.12)",
                unit="triệu đồng", col="grdp_per_capita_million_vnd",
                window=f"{GRDP_YEARS[0]}–{GRDP_YEARS[1]} (2024 = Sơ bộ)")
    return j, n_miss, meta


def load_urban(lab):
    pop = pd.read_csv(POP_CSV)
    d = pop[pop.gso_urban_residence_pct_derived.notna()].copy()
    j, n_miss = join_labels(d, lab, ["gso_urban_residence_pct_derived"])
    yrs = sorted(int(y) for y in j.year.unique())
    meta = dict(key="urban", name="% dân số đô thị (GSO V02.01)",
                unit="%", col="gso_urban_residence_pct_derived",
                window=(f"{yrs[0]}–{yrs[-1]} (các năm nguồn có số: "
                        + ", ".join(map(str, yrs)) + ")"))
    return j, n_miss, meta


LOADERS = [load_pci, load_poverty, load_health, load_grdp, load_urban]


def group_table(d: pd.DataFrame, col: str, key: str) -> pd.DataFrame:
    """Thống kê từng nhóm nhãn: n, trung vị, mean, sd, min, max."""
    nd = DECIMALS[key]
    rows = []
    for c, sub in d.groupby("pred_cluster"):
        v = sub[col]
        rows.append({
            "cluster": int(c),
            "nhóm": CLUSTER_LABELS.get(int(c), str(c)),
            "n": int(len(sub)),
            "trung vị": rnd(v.median(), nd),
            "mean": rnd(v.mean(), nd),
            "sd": rnd(v.std(ddof=1), nd) if len(sub) > 1 else None,
            "min": rnd(v.min(), nd),
            "max": rnd(v.max(), nd),
        })
    return pd.DataFrame(rows).sort_values("cluster").reset_index(drop=True)


def kruskal_test(d: pd.DataFrame, col: str) -> dict:
    """Kruskal–Wallis từng chỉ số theo nhóm nhãn có dữ liệu (scipy, sửa tie)."""
    groups = [g[col].to_numpy() for _, g in d.groupby("pred_cluster")]
    n_per = [int(len(g)) for g in groups]
    out = {"h": None, "p": None, "df": len(groups) - 1, "n": int(len(d)),
           "n_per": n_per, "note": ""}
    if len(groups) < 2:
        out["note"] = "ít hơn 2 nhóm có dữ liệu — không kiểm định"
        return out
    try:
        h, p = stats.kruskal(*groups)
    except ValueError as exc:  # mọi giá trị giống hệt nhau — hiếm, ghi rõ
        out["note"] = f"scipy từ chối kiểm định: {exc}"
        return out
    out["h"], out["p"] = float(h), float(p)
    return out


# ------------------------------------------------- ổn định bootstrap (seed) --
def match_by_jaccard(lab_b: np.ndarray, orig: np.ndarray,
                     orig_ids: list[int]):
    """Ghép từng cụm mẫu về cụm gốc bằng Jaccard tối đa (1-1 tối ưu).

    Trả về ``(mapping, jac_map)``: mapping[nhãn_mẫu] = nhãn_gốc;
    jac_map[cụm_gốc] = Jaccard của cặp được ghép (0.0 nếu không ghép được).
    """
    boot_ids = sorted(int(c) for c in np.unique(lab_b) if c >= 0)
    jac = np.zeros((len(orig_ids), len(boot_ids)))
    for i, c in enumerate(orig_ids):
        mc = orig == c
        for j, k in enumerate(boot_ids):
            mb = lab_b == k
            inter = int(np.count_nonzero(mc & mb))
            union = int(np.count_nonzero(mc | mb))
            jac[i, j] = inter / union if union else 0.0
    jac_map = {c: 0.0 for c in orig_ids}
    mapping: dict[int, int] = {}
    if jac.size:
        row, col = linear_sum_assignment(-jac)  # cực đại tổng Jaccard
        mapping = {int(boot_ids[j]): int(orig_ids[i]) for i, j in zip(row, col)}
        for i, j in zip(row, col):
            jac_map[int(orig_ids[i])] = float(jac[i, j])
    return mapping, jac_map


def keep_mask(lab_b: np.ndarray, orig: np.ndarray, mapping: dict) -> np.ndarray:
    """Một dòng 'giữ nhãn' khi (gốc −1 & mẫu −1) hoặc (gốc c & mẫu khớp về c)."""
    mapped = np.array([mapping.get(int(k), -999) for k in lab_b])
    return np.where(orig == -1, lab_b == -1, mapped == orig)


def dist_stats(x) -> dict | None:
    """mean/median/sd/CI95 (percentile 2.5–97.5) của một phân bố, bỏ NaN."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size == 0:
        return None
    return {
        "n": int(x.size),
        "mean": float(x.mean()),
        "median": float(np.median(x)),
        "sd": float(x.std(ddof=1)) if x.size > 1 else float("nan"),
        "p2_5": float(np.percentile(x, 2.5)),
        "p97_5": float(np.percentile(x, 97.5)),
    }


def bootstrap_stability(fit: pd.DataFrame, feats: list[str], sp: dict,
                        orig_ids: list[int]):
    """200 lần resample CÓ hoàn lại theo TỈNH, refit cấu hình đóng băng.

    Đơn vị resample = tỉnh (cluster bootstrap panel): mỗi lần rút n tỉnh có
    hoàn lại; mẫu gồm toàn bộ dòng fit của các tỉnh được rút (tỉnh bị rút k
    lần góp k bản sao dòng). Refit = StandardScaler fit trên mẫu + STING đóng
    băng + cluster(level=2, connectivity=1) — không đổi tham số.
    """
    rng = np.random.default_rng(SEED)
    prov_arr = fit["province_code"].to_numpy()
    provs = np.sort(fit["province_code"].unique())
    X_all = fit[feats].to_numpy(dtype=float)
    orig = fit["pred_cluster"].to_numpy()
    idx_by_prov = {int(p): np.flatnonzero(prov_arr == p) for p in provs}
    labels_all = [-1] + orig_ids

    rates = np.full(N_BOOT, np.nan)
    sils = np.full(N_BOOT, np.nan)
    ks = np.zeros(N_BOOT, dtype=int)
    kept_sum = {c: 0 for c in labels_all}
    total_sum = {c: 0 for c in labels_all}
    rate_by_label = {c: [] for c in labels_all}
    jac_by_orig = {c: [] for c in orig_ids}

    for b in range(N_BOOT):
        draws = rng.integers(0, len(provs), size=len(provs))
        idx = np.concatenate([idx_by_prov[int(provs[d])] for d in draws])
        Xs = X_all[idx]
        os_ = orig[idx]
        sc = StandardScaler().fit(Xs)
        Xz = sc.transform(Xs)
        m = STING(n_levels=sp["n_levels"], factor=sp["factor"],
                  min_count=sp["min_count"]).fit(Xz)
        lab_b = m.cluster(level=sp["cluster_level"],
                          connectivity=sp["connectivity"])
        ks[b] = int(m.n_clusters_)
        mapping, jac_map = match_by_jaccard(lab_b, os_, orig_ids)
        kept = keep_mask(lab_b, os_, mapping)
        rates[b] = float(kept.mean())
        for c in labels_all:
            sel = os_ == c
            if sel.any():
                kept_sum[c] += int(kept[sel].sum())
                total_sum[c] += int(sel.sum())
                rate_by_label[c].append(float(kept[sel].mean()))
        for c, jv in jac_map.items():
            jac_by_orig[c].append(jv)
        nn = lab_b >= 0
        if np.unique(lab_b[nn]).size >= 2:
            try:
                sils[b] = float(silhouette_score(Xz[nn], lab_b[nn]))
            except ValueError:
                pass  # degenerate (ví dụ trùng điểm hoàn toàn) — bỏ lần này

    match_freq = {
        c: int(sum(1 for jv in jac_by_orig[c] if jv > 0.0)) for c in orig_ids
    }
    return {
        "rates": rates, "sils": sils, "ks": ks,
        "rate_dist": dist_stats(rates), "sil_dist": dist_stats(sils),
        "rate_by_label": rate_by_label, "pooled": {
            c: (kept_sum[c] / total_sum[c] if total_sum[c] else None)
            for c in labels_all
        },
        "total_by_label": total_sum,
        "jac_mean": {c: float(np.mean(jac_by_orig[c])) for c in orig_ids},
        "match_freq": match_freq,
        "k_counter": dict(sorted(Counter(ks.tolist()).items())),
        "n_prov": int(len(provs)),
        "n_fit": int(len(fit)),
    }


# ---------------------------------------------------------------- hình ảnh --
SOURCE_LINE = "PCI VCCI–USAID · GSO V14.47 · OD Mekong — provenance trong repo"
SHORT_NAMES = {
    "pci": "PCI 2011–22",
    "poverty": "Nghèo (năm giao)",
    "health": "Y tế/1000 dân 2020",
    "grdp": "GRDP/người 18–24",
    "urban": "% đô thị (nguồn)",
}


def wrap_lines(text: str, width: int = 100) -> int:
    """Đếm số dòng sau wrap — cùng quy tắc fig_style.add_source để chừa lề."""
    import textwrap

    return sum(max(1, len(textwrap.wrap(ch, width))) for ch in text.split("\n"))


def make_fig(inds: list[dict], boot: dict, sil0: float, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with style_context():
        # 2×2 cần khổ lớn hơn preset docx để tiêu đề/ nhãn tiếng Việt không
        # chồng nhau — target=None cho phép figsize riêng (fig_style.py:169
        # dành kích thước tự do cho hình ngoài 2 preset).
        fig, axes = new_fig(target=None, nrows=2, ncols=2, figsize=(9.6, 7.0))

        # (a) Phân bố tỉ lệ giữ nhãn qua 200 lần bootstrap
        ax = axes[0, 0]
        rd = boot["rate_dist"]
        ax.hist(boot["rates"], bins=20, color=PALETTE["blue"], alpha=0.75)
        ax.axvline(rd["mean"], color="#222222", linewidth=1.4,
                   label=f"mean = {rd['mean']:.1%}")
        ax.axvline(rd["p2_5"], color="#222222", linewidth=1.0, linestyle="--",
                   label=f"CI95 = [{rd['p2_5']:.1%}, {rd['p97_5']:.1%}]")
        ax.axvline(rd["p97_5"], color="#222222", linewidth=1.0, linestyle="--")
        ax.set_xlabel("Tỉ lệ giữ nhãn (dòng tỉnh-năm trong mẫu)")
        ax.set_ylabel("Số lần bootstrap")
        ax.set_title(f"Tỉ lệ giữ nhãn — {N_BOOT} lần, seed {SEED}",
                     fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.25)

        # (b) Phân bố silhouette (không nhiễu) + tham chiếu model gốc
        ax = axes[0, 1]
        sd = boot["sil_dist"]
        valid = boot["sils"][~np.isnan(boot["sils"])]
        ax.hist(valid, bins=20, color=PALETTE["green"], alpha=0.75)
        ax.axvline(sil0, color="#B22222", linewidth=1.4,
                   label=f"model gốc (train) = {sil0:.3f}")
        if sd:
            ax.axvline(sd["mean"], color="#222222", linewidth=1.0,
                       linestyle="--", label=f"mean bootstrap = {sd['mean']:.3f}")
        ax.set_xlabel("Silhouette (điểm non-noise, z-score theo mẫu)")
        ax.set_ylabel("Số lần bootstrap")
        ci_txt = (f"CI95 [{sd['p2_5']:.3f}, {sd['p97_5']:.3f}] "
                  f"({sd['n']}/{N_BOOT} lần)"
                  if sd else "không lần nào có ≥2 cụm non-noise")
        ax.set_title(f"Silhouette — {ci_txt}", fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.25)

        # (c) Tỉ lệ giữ nhãn theo NHÃN GỐC (mean + CI95 theo lần có mặt)
        ax = axes[1, 0]
        labs = sorted(boot["rate_by_label"])
        means, los, his, cols = [], [], [], []
        for c in labs:
            d_ = dist_stats(boot["rate_by_label"][c])
            if d_ is None:
                means.append(np.nan)
                los.append(np.nan)
                his.append(np.nan)
            else:
                means.append(d_["mean"])
                los.append(d_["mean"] - d_["p2_5"])
                his.append(d_["p97_5"] - d_["mean"])
            cols.append(CLUSTER_COLORS.get(c, "#937860"))
        ax.bar(range(len(labs)), means, color=cols, alpha=0.8,
               yerr=[los, his], capsize=3, ecolor="#444444")
        ax.set_xticks(range(len(labs)))
        ax.set_xticklabels([CLUSTER_LABELS.get(c, str(c)) for c in labs],
                           fontsize=9)
        ax.set_ylim(0, 1.08)
        ax.set_ylabel("Tỉ lệ giữ nhãn")
        ax.set_title("Giữ nhãn theo nhóm gốc (thanh lỗi = CI95)", fontsize=11)
        ax.grid(axis="y", alpha=0.25)

        # (d) Kruskal–Wallis từng chỉ số ngoài
        ax = axes[1, 1]
        names = [SHORT_NAMES[i["meta"]["key"]] for i in inds]
        hs = [i["kw"]["h"] if i["kw"]["h"] is not None else 0.0 for i in inds]
        ax.bar(range(len(inds)), hs, color=PALETTE["blue"], alpha=0.8)
        for k, i in enumerate(inds):
            kw = i["kw"]
            top = f"H={kw['h']:.1f}\ndf={kw['df']}, {fmt_p(kw['p'])}" \
                if kw["h"] is not None else "không\nkiểm định"
            ax.text(k, hs[k], top, ha="center", va="bottom", fontsize=7,
                    color="#333333")
        ax.set_xticks(range(len(inds)))
        ax.set_xticklabels(names, fontsize=8, rotation=20, ha="right")
        ax.set_ylabel("Kruskal–Wallis H")
        ax.set_title("Khác biệt giữa các nhóm — từng chỉ số ngoài",
                     fontsize=11)
        ax.margins(y=0.24)
        ax.grid(axis="y", alpha=0.25)

        fig.suptitle("Hồ sơ chuyên sâu cụm STING — chỉ số ngoài & ổn định "
                     "bootstrap", fontsize=13, fontweight="bold")
        n_src = wrap_lines(f"Nguồn: {SOURCE_LINE}")
        add_source(fig, SOURCE_LINE)
        fig.tight_layout(rect=(0, 0.02 + 0.032 * n_src, 1, 0.95))
        save_png(fig, out_path, dpi=300)
        plt.close(fig)


# ---------------------------------------------------------------- outputs --
CSV_COLS = ["section", "indicator", "group", "n", "mean", "median", "std",
            "min", "max", "note"]


def _row(**kw) -> dict:
    base = {c: "" for c in CSV_COLS}
    base.update(kw)
    return base


def build_csv_rows(lab, inds, boot, sil0) -> list[dict]:
    rows: list[dict] = []
    for c, sub in lab.groupby("pred_cluster"):
        rows.append(_row(
            section="labels_overview", indicator="predict_all_years.csv",
            group=CLUSTER_LABELS.get(int(c), str(c)), n=int(len(sub)),
            note=(f"tỉnh duy nhất = {sub.province_code.nunique()}; "
                  f"năm {int(sub.year.min())}–{int(sub.year.max())}"),
        ))
    for ind in inds:
        nd = DECIMALS[ind["meta"]["key"]]
        for _, g in ind["groups"].iterrows():
            rows.append(_row(
                section="group_profile", indicator=ind["meta"]["name"],
                group=g["nhóm"], n=int(g["n"]), mean=rnd(g["mean"], nd),
                median=rnd(g["trung vị"], nd), std=rnd(g["sd"], nd),
                min=rnd(g["min"], nd), max=rnd(g["max"], nd),
                note=f"cửa sổ {ind['meta']['window']}",
            ))
        kw = ind["kw"]
        rows.append(_row(
            section="kruskal", indicator=ind["meta"]["name"],
            group="Kruskal–Wallis", n=kw["n"],
            note=(f"H = {kw['h']:.4f}; df = {kw['df']}; {fmt_p(kw['p'])}; "
                  f"n theo nhóm {kw['n_per']}")
            if kw["h"] is not None else kw["note"],
        ))
    rd, sd = boot["rate_dist"], boot["sil_dist"]
    pct = lambda v: f"{v:.1%}"  # noqa: E731
    rows.append(_row(
        section="bootstrap", indicator=f"resample theo tỉnh (seed {SEED})",
        group="tỉ lệ giữ nhãn — toàn bộ dòng",
        mean=rnd(rd["mean"], 4), median=rnd(rd["median"], 4),
        std=rnd(rd["sd"], 4), min=rnd(rd["p2_5"], 4), max=rnd(rd["p97_5"], 4),
        note=(f"phân bố {N_BOOT} lần; CI95 percentile "
              f"[{pct(rd['p2_5'])}, {pct(rd['p97_5'])}]"),
    ))
    for c in sorted(boot["rate_by_label"]):
        d_ = dist_stats(boot["rate_by_label"][c])
        pooled = boot["pooled"][c]
        rows.append(_row(
            section="bootstrap", indicator=f"resample theo tỉnh (seed {SEED})",
            group=f"tỉ lệ giữ nhãn — nhóm {CLUSTER_LABELS.get(c, str(c))}",
            n=boot["total_by_label"][c],
            mean=rnd(d_["mean"], 4) if d_ else None,
            median=rnd(d_["median"], 4) if d_ else None,
            min=rnd(d_["p2_5"], 4) if d_ else None,
            max=rnd(d_["p97_5"], 4) if d_ else None,
            note=(f"gộp {N_BOOT} lần: {pct(pooled) if pooled is not None else '—'}"
                  f"; có mặt trong {d_['n']}/{N_BOOT} lần"
                  if d_ else "nhóm không xuất hiện trong mẫu nào"),
        ))
    for c in sorted(boot["jac_mean"]):
        rows.append(_row(
            section="bootstrap", indicator=f"resample theo tỉnh (seed {SEED})",
            group=f"Jaccard cặp ghép — cụm gốc {c}",
            mean=rnd(boot["jac_mean"][c], 4),
            note=f"được ghép (Jaccard>0) trong {boot['match_freq'][c]}/{N_BOOT} lần",
        ))
    rows.append(_row(
        section="bootstrap", indicator=f"resample theo tỉnh (seed {SEED})",
        group="silhouette (non-noise)",
        mean=rnd(sd["mean"], 4) if sd else None,
        median=rnd(sd["median"], 4) if sd else None,
        min=rnd(sd["p2_5"], 4) if sd else None,
        max=rnd(sd["p97_5"], 4) if sd else None,
        note=(f"{sd['n']}/{N_BOOT} lần hợp lệ; model gốc (train) = {sil0:.4f}"
              if sd else "không lần nào có ≥2 cụm non-noise"),
    ))
    for k, cnt in boot["k_counter"].items():
        rows.append(_row(
            section="bootstrap", indicator=f"resample theo tỉnh (seed {SEED})",
            group=f"số cụm refit k′ = {k}", n=int(cnt),
            note=f"{cnt}/{N_BOOT} lần",
        ))
    return rows


def build_md(lab, cfg, fit, n_fit, inds, boot, sil0) -> str:
    sp = cfg["sting"]
    feats = cfg["features"]
    fl = cfg["feature_labels"]
    lines: list[str] = []
    lines.append("# Hồ sơ chuyên sâu cụm STING — chỉ số ngoài & ổn định bootstrap\n")
    lines.append(
        "Sinh bởi `scripts/cluster_profile.py` — lane phân tích **MỚI**, không "
        "thay đổi bất kỳ artifact/số đã công bố. Nhãn cụm tỉnh-năm lấy từ "
        "`results/predict_all_years.csv` (model đóng băng "
        "`models/predict_config.json`: features **"
        + "** × **".join(fl[f] for f in feats)
        + f"**; STING(L={sp['n_levels']}, factor={sp['factor']}, "
          f"min_count={sp['min_count']}), level={sp['cluster_level']}, "
          f"connectivity={sp['connectivity']}; fit 2011–{TRAIN_MAX_YEAR}). "
        "Mọi số do script tự tính trong bộ nhớ từ CSV provenance — không "
        "hardcode; kiểm định bằng `scipy.stats.kruskal` (có sửa tie).\n"
    )
    lines.append(
        f"- **Bootstrap**: {N_BOOT} lần resample CÓ hoàn lại **theo TỈNH** "
        f"(cluster bootstrap panel), seed **{SEED}** = "
        f"`numpy.random.default_rng({SEED})`; khớp nhãn mẫu → nhãn gốc bằng "
        "Jaccard tối đa từng cụm (ghép cặp 1-1 tối ưu, "
        "`scipy.optimize.linear_sum_assignment`).\n"
        f"- Kiểm chứng tất định: refit đúng công thức `predict_demo.py` cho "
        f"lại **đúng {n_fit}/{n_fit} nhãn train** của CSV (0 lệch) — cùng ngữ "
        "nghĩa gate `tests/test_artifact_reproduction.py`.\n"
    )

    # ---------------- 1) nhãn tỉnh-năm ----------------
    lines.append("## 1) Nhãn cụm theo tỉnh-năm\n")
    ov = []
    for c, sub in lab.groupby("pred_cluster"):
        ov.append({
            "nhóm": CLUSTER_LABELS.get(int(c), str(c)),
            "n (tỉnh-năm)": int(len(sub)),
            "n tỉnh duy nhất": int(sub.province_code.nunique()),
            "năm có điểm": f"{int(sub.year.min())}–{int(sub.year.max())}",
            "split": (f"train {int((sub.split == 'train').sum())} / "
                      f"test {int((sub.split == 'test').sum())}"),
        })
    lines.append(pd.DataFrame(ov).to_markdown(index=False))
    lines.append("")
    cnt = lab.pred_cluster.value_counts().sort_index()
    lines.append(
        f"- Cấu trúc nhãn: 1 cụm lớn (cụm 2: {int(cnt.get(2, 0))} dòng) + 2 cụm "
        f"li ti (cụm 0: {int(cnt.get(0, 0))} dòng, cụm 1: {int(cnt.get(1, 0))} "
        "dòng — chỉ xuất hiện những năm đầu panel) và vùng nhiễu (−1: "
        f"{int(cnt.get(-1, 0))} dòng, ô lưới không đủ min_count). Nhìn nhận "
        "trục này trước khi đọc các bảng dưới.\n"
    )

    # ---------------- 2) hồ sơ × chỉ số ngoài ----------------
    lines.append("## 2) Hồ sơ nhóm × chỉ số ngoài (Kruskal–Wallis + trung vị)\n")
    lines.append(
        "*Lưu ý chung*: nhóm cụm 0 / cụm 1 có n rất nhỏ (cụm li ti) — thống kê "
        "chỉ mang tính mô tả; cặp tương phản đáng tin là **nhiễu (−1) vs cụm 2**. "
        "p nhỏ với nhóm n rất nhỏ KHÔNG chứng minh cụm nhỏ là một \"kiểu tỉnh\" "
        "độc lập. Không nội suy ô thiếu; join khóa (year, province_code).\n"
    )
    for i, ind in enumerate(inds, start=1):
        meta, kw = ind["meta"], ind["kw"]
        lines.append(f"### 2.{i}) {meta['name']} — {meta['window']}\n")
        lines.append(
            f"- Join nhãn: {ind['n_join']}/{ind['n_src']} ô có nhãn "
            f"({ind['n_miss']} ô tỉnh-năm panel thiếu sd_4_2/sd_6_1 nên không "
            f"có nhãn); {kw['n']} ô vào thống kê.\n"
        )
        # sd = None với nhóm n=1 → hiển thị "–" thay vì nan trong md
        lines.append(ind["groups"].fillna("–").to_markdown(index=False))
        lines.append("")
        if kw["h"] is not None:
            lines.append(
                f"- **Kruskal–Wallis**: H = {kw['h']:.4f}, df = {kw['df']}, "
                f"{fmt_p(kw['p'])} (n = {kw['n']}; n theo nhóm {kw['n_per']}).\n"
            )
        else:
            lines.append(f"- Kruskal–Wallis: {kw['note']}.\n")
        if meta["key"] == "health":
            zeros = ind.get("zeros", [])
            if zeros:
                lines.append(
                    f"- Tỉnh `count = 0` là 0-thật (nguồn điểm ODM không phủ, "
                    f"không phải lỗi nối tên): {', '.join(zeros)}.\n"
                )

    # ---------------- 3) ổn định bootstrap ----------------
    rd, sd = boot["rate_dist"], boot["sil_dist"]
    lines.append(
        f"## 3) Ổn định bootstrap — {N_BOOT} lần, seed {SEED}, resample theo tỉnh\n"
    )
    lines.append(
        "- **Phương pháp**: mỗi lần rút "
        f"{boot['n_prov']} tỉnh CÓ hoàn lại (`rng.integers(0, {boot['n_prov']}, "
        f"size={boot['n_prov']})`); mẫu = toàn bộ dòng fit (2011–{TRAIN_MAX_YEAR}, "
        f"đủ chỉ tiêu; {boot['n_fit']} dòng gốc) của các tỉnh được rút — tỉnh bị "
        "rút k lần góp k bản sao dòng (đúng cluster bootstrap cho panel, tôn "
        "trọng tương quan trong tỉnh). Refit ĐÚNG cấu hình đóng băng: "
        "StandardScaler fit trên mẫu + STING(L, factor, min_count) như trên + "
        "cluster(level=2, connectivity=1).\n"
        "- **Khớp nhãn**: với từng cụm gốc 0/1/2, ghép cặp 1-1 tối ưu tổng "
        "Jaccard giữa các dòng của cụm mẫu và cụm gốc; nhãn −1 giữ trạng thái "
        "riêng. Một dòng \"giữ nhãn\" khi (gốc −1 & mẫu −1) hoặc (gốc c & mẫu "
        "khớp về c). Silhouette tính trên điểm KHÔNG nhiễu của mẫu; lần refit "
        "ra < 2 cụm non-noise bị bỏ khỏi phân bố silhouette.\n"
    )
    rows = [{
        "đại lượng": "Tỉ lệ giữ nhãn — toàn bộ dòng",
        "mean": f"{rd['mean']:.4f}", "median": f"{rd['median']:.4f}",
        "sd": f"{rd['sd']:.4f}",
        "CI95 (p2.5–p97.5)": f"[{rd['p2_5']:.4f}, {rd['p97_5']:.4f}]",
        "n lần": rd["n"],
    }]
    if sd:
        rows.append({
            "đại lượng": "Silhouette (non-noise)",
            "mean": f"{sd['mean']:.4f}", "median": f"{sd['median']:.4f}",
            "sd": f"{sd['sd']:.4f}",
            "CI95 (p2.5–p97.5)": f"[{sd['p2_5']:.4f}, {sd['p97_5']:.4f}]",
            "n lần": sd["n"],
        })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")
    lines.append(
        f"- Tham chiếu: silhouette của model gốc trên train (không nhiễu) = "
        f"**{sil0:.4f}** — phân bố bootstrap thấp hơn là chi phí của việc rút "
        "lại tỉnh (mẫu lệch + trùng bản sao), không phải lỗi cài đặt.\n"
    )
    rows = []
    for c in sorted(boot["rate_by_label"]):
        d_ = dist_stats(boot["rate_by_label"][c])
        pooled = boot["pooled"][c]
        rows.append({
            "nhãn gốc": CLUSTER_LABELS.get(c, str(c)),
            "tỉ lệ gộp (200 lần)": ("—" if pooled is None else f"{pooled:.1%}"),
            "mean theo lần có mặt": "—" if d_ is None else f"{d_['mean']:.1%}",
            "CI95 theo lần": ("—" if d_ is None else
                              f"[{d_['p2_5']:.1%}, {d_['p97_5']:.1%}]"),
            "dòng gộp": boot["total_by_label"][c],
            "số lần có mặt": "—" if d_ is None else f"{d_['n']}/{N_BOOT}",
        })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")
    rows = [{
        "cụm gốc": str(c),
        "Jaccard TB cặp ghép": f"{boot['jac_mean'][c]:.3f}",
        "được ghép (Jaccard>0)": f"{boot['match_freq'][c]}/{N_BOOT}",
    } for c in sorted(boot["jac_mean"])]
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("")
    k_rows = [{"k′ của refit": str(k), "số lần": f"{cnt}/{N_BOOT}"}
              for k, cnt in boot["k_counter"].items()]
    lines.append(pd.DataFrame(k_rows).to_markdown(index=False))
    lines.append("")
    lines.append(
        "- **Đọc kết quả**: cụm lớn + nhiễu được tái lập gần như chắc chắn "
        "(tỉ lệ giữ nhãn cao); cụm li ti 0/1 phụ thuộc việc các tỉnh sáng lập "
        "chúng có được rút vào mẫu hay không — phân bố tỉ lệ giữ nhãn của hai "
        "nhóm này trải rộng, đúng bản chất cụm li ti dưới bootstrap. Kết luận "
        "vững chỉ nên dựa trên tương phản nhiễu vs cụm 2.\n"
    )

    # ---------------- 4) tái lập ----------------
    lines.append("## 4) Tái lập\n")
    lines.append("```powershell\npython -E scripts/cluster_profile.py\n```\n")
    lines.append(
        "- Đầu vào: `results/predict_all_years.csv`, "
        "`data/processed/papi_panel_63_2011_2024.csv` (đọc), "
        "`data/processed/external_{pci_63_full,poverty_63,odm_health_63,"
        "gso_grdp_63,gso_population_63_full}.csv`, "
        "`models/predict_config.json` (đọc).\n"
        "- Đầu ra MỚI: file này, `results/cluster_profile.csv`, "
        "`results/figs/deep_cluster_profile.png`.\n"
        f"- Tất định: bootstrap seed {SEED}; không có thời gian hệ thống trong "
        "đầu ra → chạy 2 lần cho md/csv sha256 byte-giống.\n"
        "- Provenance nguồn: `data/processed/external_provenance.md`, "
        "`data/raw/*/PROVENANCE.md`."
    )
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------- main --
def main() -> int:
    cfg = load_config()
    feats = list(cfg["features"])
    sp = cfg["sting"]

    lab = load_labels()
    fit = load_fit_rows(lab, feats)
    ok, X0, labels0 = verify_frozen_refit(fit, feats, sp)
    if not ok:
        n_diff = int((labels0 != fit["pred_cluster"].to_numpy()).sum())
        print(f"DỪNG: refit tất định lệch {n_diff}/{len(fit)} nhãn train — "
              "không ghi output. Kiểm tra models/predict_config.json và gate "
              "tests/test_artifact_reproduction.py.")
        return 1
    nn0 = labels0 >= 0
    sil0 = float(silhouette_score(X0[nn0], labels0[nn0]))

    inds = []
    for loader in LOADERS:
        d, n_miss, meta = loader(lab)
        inds.append({
            "meta": meta, "kw": kruskal_test(d, meta["col"]),
            "groups": group_table(d, meta["col"], meta["key"]),
            "n_src": int(len(d)) + n_miss, "n_join": int(len(d)),
            "n_miss": n_miss,
            "zeros": (d.loc[d[meta["col"]] == 0, "province_vi"].tolist()
                      if meta["key"] == "health" else []),
        })

    orig_ids = sorted(int(c) for c in fit.pred_cluster.unique() if c >= 0)
    boot = bootstrap_stability(fit, feats, sp, orig_ids)

    FIGS.mkdir(parents=True, exist_ok=True)
    rows = build_csv_rows(lab, inds, boot, sil0)
    pd.DataFrame(rows)[CSV_COLS].to_csv(CSV_PATH, index=False,
                                        encoding="utf-8-sig")
    md = build_md(lab, cfg, fit, int(len(fit)), inds, boot, sil0)
    MD_PATH.write_text(md, encoding="utf-8")
    make_fig(inds, boot, sil0, FIG_PATH)

    rd, sd = boot["rate_dist"], boot["sil_dist"]
    print(f"labels: {len(lab)} tỉnh-năm | fit n={boot['n_fit']} "
          f"({boot['n_prov']} tỉnh) | refit khớp 100%")
    for ind in inds:
        kw = ind["kw"]
        stat = (f"H={kw['h']:.4f}, {fmt_p(kw['p'])}" if kw["h"] is not None
                else kw["note"])
        print(f"  {ind['meta']['name']}: n={kw['n']} | Kruskal {stat}")
    print(f"bootstrap ({N_BOOT} lần, seed {SEED}, resample theo tỉnh):")
    print(f"  retention mean={rd['mean']:.4f} "
          f"CI95=[{rd['p2_5']:.4f}, {rd['p97_5']:.4f}]")
    if sd:
        print(f"  silhouette mean={sd['mean']:.4f} "
              f"CI95=[{sd['p2_5']:.4f}, {sd['p97_5']:.4f}] "
              f"({sd['n']}/{N_BOOT} lần hợp lệ) | model gốc={sil0:.4f}")
    print(f"  k′ distribution: {boot['k_counter']}")
    print(f"đã ghi: {MD_PATH.name}, {CSV_PATH.name}, {FIG_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
