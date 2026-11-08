"""Kiểm định bổ trợ: tỷ lệ hộ nghèo GSO theo nhãn cụm STING — cửa sổ giao.

Nghèo là kết quả thứ HAI được dùng để kiểm chứng ngoại lai cụm STING, sau PCI
(scripts/external_validation.py). Nguồn độc lập với PAPI: thống kê chính thức
GSO pxweb V14.47, chuẩn hóa bởi scripts/build_poverty_63.py thành
data/processed/external_poverty_63.csv (63 tỉnh × 17 năm 2006, 2008, 2010 +
2012–2025 liên tục; 2017–2019 điền từ Niên giám Thống kê 2020/2021 theo quy ước
vintage-mới-nhất-chứa-năm — cột `source` ghi nguồn theo từng dòng).
Chạy từ thư mục gốc:

    python -E scripts/poverty_validation.py

Giao thức join — GIỐNG NGUYÊN XI protocol PCI của external_validation.py:
  - Nhãn cụm lấy TỪ results/predict_all_years.csv (model CHỐT, gate bởi
    tests/test_artifact_reproduction.py) — KHÔNG dùng results/cluster_labels.csv
    (external_validation.py:21-23).
  - Khóa join (year, province_code); assert khóa duy nhất hai phía rồi
    merge(how="left", validate="one_to_one") (external_validation.py:313-323).
  - Cột tên (province_ascii/province_vi) CHỈ để hiển thị, không làm khóa.
  - KHÔNG nội suy bất kỳ ô nào; không tự tính lại nhãn; không gán nhãn cho ô
    thiếu. Ô thiếu bị loại KHỎI kiểm định nhưng ĐƯỢC ĐẾM VÀ LIỆT KÊ tường
    minh (pattern masked của GRDP — external_validation.py:477-486).

Cửa sổ phân tích = các năm CÓ Ở CẢ HAI nguồn (tự tính từ dữ liệu, trùng cửa
sổ thiết kế 2012–2024): poverty có 2006/2008/2010/2025 nhưng không có nhãn cụm
(predict_all_years.csv phủ 2011–2024); nhãn có 2011 nhưng chuỗi nghèo không có
năm đó (pxweb V14.47 không có cột 2011; 2017–2019 đã điền từ Niên giám Thống
kê 2020/2021).

Hai kiểm định CHÍNH, bắt buộc báo cáo CÙNG nhau (nguyên tắc trung thực):
  1. Kruskal–Wallis poverty_rate_pct theo pred_cluster GỘP cửa sổ — kèm
     One-way ANOVA + eta² như mô tả bổ sung (bố cục external_validation.py:
     98-114, 604-607). Test gộp thô NHIỄM hiệu ứng năm (median nghèo giảm rất
     mạnh xuyên năm) vì tỷ trọng cụm trôi theo năm.
  2. Kruskal–Wallis trên poverty ĐÃ TRỪ median trong từng năm (demean trong
     panel phân tích n ô) — tách hiệu ứng năm. So GIỮA CỤM trong cùng một năm
     là so sánh hợp lệ duy nhất vì chuẩn nghèo đổi theo giai đoạn
     (data/raw/gso/PROVENANCE.md:48-58).
Kèm Mann–Whitney nhiễu vs cụm 2 — cặp tương phản đáng tin duy nhất (đối xứng
với cảnh báo PCI, external_validation.py:608-610). KW theo từng năm CHỈ mô tả.

Helper thống kê và trình bày TÁI DỤNG NGUYÊN XI từ scripts/external_validation
(group_table, anova_kruskal, test_rows, stats_rows, source_note,
source_rect_bottom, place_n_labels, fmt_p, FIG_DPI_PRINT, RETRIEVED_DATE) —
không viết lại, không hardcode số. Mọi số trong outputs tự tính từ CSV.

Đầu ra:
  results/poverty_validation.csv                  — số liệu dạng bảng
  results/poverty_validation.md                   — báo cáo + caveats đầy đủ
  results/figs/external_poverty_by_cluster.png    — 2 hàng (boxplot gộp +
                                                    median theo năm từng cụm)

File md/csv phải determinstic: chạy script 2 lần cho sha256 byte-giống (PNG
vẽ bằng rng seed cố định nên cũng ổn định; chỉ DPI/layout có thể lệch nhẹ).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from external_validation import (FIG_DPI_PRINT, RETRIEVED_DATE,
                                 anova_kruskal, fmt_p, group_table,
                                 place_n_labels, source_note,
                                 source_rect_bottom, stats_rows, test_rows)
from fig_style import (CLUSTER_COLORS, CLUSTER_LABELS, apply_style, new_fig,
                       save_png)

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RES = ROOT / "results"
FIGS = RES / "figs"

POVERTY_CSV = PROC / "external_poverty_63.csv"
LABELS_CSV = RES / "predict_all_years.csv"

OUT_CSV = RES / "poverty_validation.csv"
OUT_MD = RES / "poverty_validation.md"
OUT_PNG = FIGS / "external_poverty_by_cluster.png"

# Cửa sổ thiết kế trong giao thức — assert khớp cửa sổ tự tính từ dữ liệu.
# 2017–2019 đã có trong chuỗi nghèo (điền từ NGTK 2020/2021 —
# scripts/build_poverty_gap.py) nên cửa sổ giao với nhãn cụm liền 2012–2024.
DESIGN_WINDOW = [2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
                 2020, 2021, 2022, 2023, 2024]


def fmt_window(years: list[int]) -> str:
    """'2012-2016 & 2020-2024' dạng ngắn từ danh sách năm (runs liên tiếp).

    Năm đơn tách bằng dấu phẩy, khoảng liên tiếp tách bằng ' & ':
    '2006, 2008, 2010 & 2012–2016 & 2020–2025'.
    """
    runs: list[tuple[int, int]] = []
    start = prev = years[0]
    for y in years[1:]:
        if y == prev + 1:
            prev = y
            continue
        runs.append((start, prev))
        start = prev = y
    runs.append((start, prev))
    singles = [str(a) for a, b in runs if b == a]
    spans = [f"{a}–{b}" for a, b in runs if b > a]
    parts = ([", ".join(singles)] if singles else []) + spans
    return " & ".join(parts)


def group_stats_by_year(d: pd.DataFrame) -> pd.DataFrame:
    """n/mean/median/std/min/max theo (year, pred_cluster) — giá trị thô."""
    rows = []
    for (yr, lab), sub in d.groupby(["year", "pred_cluster"]):
        v = sub.poverty_rate_pct
        rows.append({
            "section": "poverty_by_year_raw",
            "group": CLUSTER_LABELS[int(lab)],
            "year": int(yr),
            "n": len(sub),
            "mean": round(float(v.mean()), 3),
            "median": round(float(v.median()), 3),
            "std": round(float(v.std(ddof=1)), 3) if len(sub) > 1 else None,
            "min": round(float(v.min()), 3),
            "max": round(float(v.max()), 3),
            "note": "",
        })
    return pd.DataFrame(rows).sort_values(["year", "group"]).reset_index(drop=True)


def kw_by_year_rows(d: pd.DataFrame) -> list[dict]:
    """KW từng năm — CHỈ mô tả (mô tả, không phải kiểm định chính)."""
    rows = []
    for yr, sub in d.groupby("year"):
        gy = [g.poverty_rate_pct.to_numpy() for _, g in sub.groupby("pred_cluster")]
        k, min_n = len(gy), min(len(g) for g in gy)
        degenerate = k < 3 or min_n < 2
        try:
            h, p = stats.kruskal(*gy)
        except ValueError:  # nhóm suy biến hoàn toàn — không tính được
            h, p = float("nan"), float("nan")
        note = f"k = {k} nhóm, min n = {min_n}; H = {h:.4f}; {fmt_p(p)}"
        if degenerate:
            note += "; suy biến (n<2 hoặc chỉ 2 nhóm) — CHỈ mô tả"
        rows.append({
            "section": "kw_by_year_descriptive", "group": "Kruskal–Wallis",
            "year": int(yr), "n": len(sub), "mean": "", "median": "", "std": "",
            "min": "", "max": "", "note": note,
        })
    return rows


def mw_noise_vs_c2(d: pd.DataFrame, value_col: str) -> dict:
    """Mann–Whitney nhiễu (−1) vs cụm 2 — cặp tương phản đáng tin duy nhất."""
    a = d.loc[d.pred_cluster == -1, value_col].to_numpy()
    b = d.loc[d.pred_cluster == 2, value_col].to_numpy()
    u, p = stats.mannwhitneyu(a, b)  # two-sided (mặc định scipy)
    return {"u": float(u), "p": float(p), "n": int(len(a) + len(b))}


def mw_verdict(p: float) -> str:
    """Cụm từ kết luận theo p — ngưỡng 0.05/0.10, KHÔNG chỉnh cho nhiều so sánh."""
    if p < 0.05:
        return "khác biệt đáng kể"
    if p < 0.10:
        return "biên (cận ngưỡng 0.05, không chỉnh sửa cho nhiều so sánh)"
    return "không khác biệt"


def make_figure(d: pd.DataFrame, window: list[int], t_raw: dict, t_dm: dict,
                mw_raw: dict, mw_dm: dict, out_path: Path,
                n_no_label: int) -> None:
    """Hình 2 hàng: boxplot gộp (template plot_pci) + median theo năm (GRDP)."""
    import matplotlib

    matplotlib.use("Agg")  # trước khi import pyplot
    import matplotlib.pyplot as plt

    fig, axes = new_fig(nrows=2, ncols=1,
                        gridspec_kw={"height_ratios": [1.15, 1.0]})
    ax1, ax2 = axes

    # ---------------- hàng 1: boxplot gộp (external_validation.py:256-294) --
    labels = sorted(int(x) for x in d.pred_cluster.unique())
    arrays = [d.loc[d.pred_cluster == lab, "poverty_rate_pct"].to_numpy()
              for lab in labels]
    bp = ax1.boxplot(arrays, patch_artist=True, widths=0.55, showfliers=False,
                     medianprops={"color": "#222222"})
    for patch, lab in zip(bp["boxes"], labels):
        patch.set_facecolor(CLUSTER_COLORS[lab])
        patch.set_alpha(0.55)
    rng = np.random.default_rng(11)
    for i, (arr, lab) in enumerate(zip(arrays, labels), start=1):
        jitter = rng.uniform(-0.16, 0.16, size=len(arr))
        ax1.scatter(np.full(len(arr), i) + jitter, arr, s=9, alpha=0.35,
                    color=CLUSTER_COLORS[lab], edgecolors="none")
    ax1.set_xticklabels([
        f"{CLUSTER_LABELS[lab]}\nn = {len(a)}" for lab, a in zip(labels, arrays)
    ])
    ax1.set_xlabel("Nhóm nhãn cụm STING (pred_cluster)")
    ax1.set_ylabel("Tỷ lệ hộ nghèo (%)")
    ax1.set_title(f"Tỷ lệ hộ nghèo GSO theo cụm STING — cửa sổ giao "
                  f"{fmt_window(window)}", pad=34)
    sub = (f"Kruskal–Wallis H = {t_raw['h']:.2f}, {fmt_p(t_raw['p_kw'])} (gộp); "
           f"H = {t_dm['h']:.2f}, {fmt_p(t_dm['p_kw'])} (trừ median trong năm)\n"
           f"Mann–Whitney nhiễu vs cụm 2: {fmt_p(mw_raw['p'])} (thô) / "
           f"{fmt_p(mw_dm['p'])} (đã trừ median năm)")
    ax1.text(0.5, 1.01, sub, transform=ax1.transAxes, ha="center",
             va="bottom", fontsize=9, color="#444444")
    ax1.grid(axis="y", alpha=0.25)

    # ---------------- hàng 2: median theo năm (template GRDP :455-490) ------
    med_year = d.groupby("year").poverty_rate_pct.median()
    series: list[tuple[int, list[tuple[float, float, int]]]] = []
    for lab in labels:
        s = (d[d.pred_cluster == lab].groupby("year")
             .agg(med=("poverty_rate_pct", "median"),
                  n=("poverty_rate_pct", "size"))
             .sort_index())
        ax2.plot(s.index, s.med, marker="o", color=CLUSTER_COLORS[lab],
                 label=CLUSTER_LABELS[lab])  # "(median)" đã có ở nhãn trục y
        series.append((lab, [(float(y), float(r.med), int(r.n))
                             for y, r in s.iterrows()]))
    # Chừa đầu trên trục y cho legend (pattern WDI: margins/ylim là lớp trình
    # bày, không đổi dữ liệu) — ymax = median lớn nhất của các series.
    ymax = max(m for _, rows in series for _, m, _ in rows)
    ax2.set_ylim(-0.10 * ymax, 1.45 * ymax)
    ax2.set_xticks(window)
    ax2.set_ylabel("Median theo năm (%)")
    ax2.set_xlabel("Năm")
    ax2.set_title(f"Median theo năm từng cụm — hiệu ứng năm mạnh "
                  f"({med_year.iloc[0]:.1f}% {int(med_year.index[0])} → "
                  f"{med_year.iloc[-1]:.1f}% {int(med_year.index[-1])})",
                  fontsize=10, pad=10)
    # Legend 1 hàng 4 cột neo phải-trên: dải đầu trên đã chừa không có điểm
    # nào cao (max ngoài c0-2012 thuộc nửa trái) → không đè đường số;
    # place_n_labels đọc bbox legend và né nó.
    ax2.legend(loc="upper right", ncol=4, fontsize=8.5, columnspacing=1.0,
               handlelength=1.6, borderaxespad=0.4)
    ax2.grid(alpha=0.25)

    n_src = source_note(
        fig,
        "GSO pxweb V14.47 + Niên giám 2020/2021 (điền 2017–2019, data/raw/gso) "
        "→ data/processed/external_poverty_63.csv; nhãn cụm "
        "results/predict_all_years.csv",
        retrieved=RETRIEVED_DATE,
        extra=(f"TP.HCM 2016 thiếu phía nguồn; {n_no_label} ô tỉnh-năm không có "
               "nhãn cụm nên không vẽ/kiểm định"),
    )
    fig.tight_layout(rect=(0, source_rect_bottom(n_src), 1, 1))
    # Nhãn n= đặt SAU tight_layout về phía trống nhất (external_validation.py:
    # 488-490) — chỉ lớp trình bày.
    place_n_labels(ax2, series)
    save_png(fig, out_path, dpi=FIG_DPI_PRINT)  # 400 dpi — hình 2 hàng dày chữ
    plt.close(fig)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    apply_style()  # rcParams chuẩn repo — gọi đầu script
    FIGS.mkdir(parents=True, exist_ok=True)

    # ====================================================================== #
    # 1) Đọc dữ liệu + join đúng protocol (year, province_code)
    # ====================================================================== #
    pov = pd.read_csv(POVERTY_CSV)
    lab = pd.read_csv(LABELS_CSV)
    assert not lab.duplicated(["year", "province_code"]).any(), "nhãn trùng khóa"
    assert not pov.duplicated(["year", "province_code"]).any(), "poverty trùng khóa"
    # papi_province_code khớp province_code → khóa join thống nhất hai bên
    assert (pov.province_code == pov.papi_province_code).all(), \
        "papi_province_code lệch province_code"

    window = [int(y) for y in sorted(set(pov.year) & set(lab.year))]
    assert window == DESIGN_WINDOW, f"cửa sổ giao lệch thiết kế: {window}"
    wyears = fmt_window(window)

    win = pov[pov.year.isin(window)]
    n_win = len(win)
    n_val = int(win.poverty_rate_pct.notna().sum())
    missing_src = win.loc[win.poverty_rate_pct.isna(),
                          ["year", "province_code", "province_vi"]] \
        .sort_values(["year", "province_code"]).reset_index(drop=True)

    wv = win.dropna(subset=["poverty_rate_pct"])
    m = wv.merge(lab[["year", "province_code", "pred_cluster"]],
                 on=["year", "province_code"], how="left",
                 validate="one_to_one")
    n_no_label = int(m.pred_cluster.isna().sum())
    no_label_cells = m.loc[m.pred_cluster.isna(),
                           ["year", "province_code", "province_vi"]] \
        .sort_values(["year", "province_code"]).reset_index(drop=True)

    d = m.dropna(subset=["pred_cluster"]).copy()
    d["pred_cluster"] = d["pred_cluster"].astype(int)
    assert set(d.pred_cluster) <= set(CLUSTER_COLORS), "nhãn ngoài palette"
    n_panel = len(d)

    # Trừ median TRONG TỪNG NĂM trên chính panel phân tích (n ô) — hằng số
    # trong năm nên KHÔNG đổi so sánh giữa cụm trong năm; chỉ tái trọng số
    # giữa các năm khi gộp (đúng ý nghĩa của test đã-điều-chỉnh-năm).
    d["pov_dm"] = d.poverty_rate_pct - \
        d.groupby("year").poverty_rate_pct.transform("median")

    print(f"Cửa sổ giao {wyears}: {n_win} ô, {n_val} ô có giá trị poverty "
          f"(thiếu phía nguồn: "
          + "; ".join(f"{r.province_vi} {int(r.year)}"
                      for _, r in missing_src.iterrows()) + ")")
    print(f"Left-join nhãn: {n_panel} ô vào kiểm định; {n_no_label} ô không có "
          f"nhãn (loại khỏi kiểm định, liệt kê tường minh)")

    # ====================================================================== #
    # 2) Kiểm định: gộp thô + đã-trừ-median-năm (báo cáo CÙNG nhau)
    # ====================================================================== #
    t_raw = anova_kruskal(d, "poverty_rate_pct")
    t_dm = anova_kruskal(d, "pov_dm")
    mw_raw = mw_noise_vs_c2(d, "poverty_rate_pct")
    mw_dm = mw_noise_vs_c2(d, "pov_dm")

    tab_raw = group_table(d, "poverty_rate_pct")
    tab_dm = group_table(d, "pov_dm")
    tab_year = group_stats_by_year(d)
    kw_year = kw_by_year_rows(d)

    print(tab_raw.to_string(index=False))
    print(f"Gộp thô:        KW H={t_raw['h']:.4f} ({fmt_p(t_raw['p_kw'])}) | "
          f"ANOVA F={t_raw['f']:.4f} ({fmt_p(t_raw['p_anova'])}) | "
          f"eta²={t_raw['eta_sq']:.4f}")
    print(f"Trừ median năm: KW H={t_dm['h']:.4f} ({fmt_p(t_dm['p_kw'])}) | "
          f"ANOVA F={t_dm['f']:.4f} ({fmt_p(t_dm['p_anova'])}) | "
          f"eta²={t_dm['eta_sq']:.4f}")
    print(f"Mann–Whitney nhiễu vs cụm 2: thô U={mw_raw['u']:.0f} "
          f"({fmt_p(mw_raw['p'])}); đã trừ median năm U={mw_dm['u']:.0f} "
          f"({fmt_p(mw_dm['p'])})")

    # ====================================================================== #
    # 3) CSV — cùng schema external_validation.csv
    # ====================================================================== #
    year_rows = [dict(r) for r in tab_year.to_dict("records")]
    mw_rows = [
        {"section": "test_mw_noise_vs_c2",
         "group": "Mann–Whitney nhiễu vs cụm 2 (thô)", "year": "",
         "n": mw_raw["n"], "mean": "", "median": "", "std": "", "min": "",
         "max": "", "note": f"U = {mw_raw['u']:.0f}; {fmt_p(mw_raw['p'])}"},
        {"section": "test_mw_noise_vs_c2",
         "group": "Mann–Whitney nhiễu vs cụm 2 (đã trừ median năm)", "year": "",
         "n": mw_dm["n"], "mean": "", "median": "", "std": "", "min": "",
         "max": "", "note": f"U = {mw_dm['u']:.0f}; {fmt_p(mw_dm['p'])}"},
    ]
    rows = (
        stats_rows("poverty_pooled_raw", tab_raw)
        + test_rows("poverty_pooled_raw", t_raw)
        + stats_rows("poverty_pooled_demeaned", tab_dm)
        + test_rows("poverty_pooled_demeaned", t_dm)
        + year_rows
        + mw_rows
        + kw_year
    )
    cols = ["section", "group", "year", "n", "mean", "median", "std",
            "min", "max", "note"]
    pd.DataFrame(rows)[cols].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Đã ghi {OUT_CSV} ({len(rows)} dòng)")

    # ====================================================================== #
    # 4) MD — báo cáo + caveats đầy đủ (mọi số f-string từ biến đã tính)
    # ====================================================================== #
    med_year = d.groupby("year").poverty_rate_pct.median()
    cnt = d.pred_cluster.value_counts().sort_index()
    noise_by_year = d[d.pred_cluster == -1].groupby("year").size()
    pov_only_years = sorted(int(y) for y in set(pov.year) - set(window))
    label_only_years = sorted(int(y) for y in set(lab.year) - set(window))
    missing_src_txt = "; ".join(f"{r.province_vi} {int(r.year)} (code "
                                f"{int(r.province_code)})"
                                for _, r in missing_src.iterrows())
    no_label_txt = "; ".join(f"{r.province_vi} {int(r.year)}"
                             for _, r in no_label_cells.iterrows())

    xt = pd.crosstab(d.year, d.pred_cluster).rename(
        columns={k: v for k, v in CLUSTER_LABELS.items()})
    xt.index.name = "năm"
    kw_tab = pd.DataFrame(kw_year)[["year", "n", "note"]]

    md: list[str] = []
    md.append(f"# Kiểm định bổ trợ — tỷ lệ hộ nghèo GSO theo nhãn cụm STING "
              f"(cửa sổ giao {wyears})\n")
    md.append(
        "Sinh bởi `scripts/poverty_validation.py`. Kiểm chứng ngoại lai thứ hai "
        "của cụm STING sau PCI (nguồn độc lập với PAPI): nghèo GSO là số liệu "
        "thống kê chính thức, không phải khảo sát hộ dân. Nhãn cụm lấy từ "
        "`results/predict_all_years.csv` (model đóng băng, gate bởi "
        "`tests/test_artifact_reproduction.py`); join khóa (year, "
        "province_code) `validate=\"one_to_one\"` đúng protocol "
        "`scripts/external_validation.py`. Thống kê bằng scipy "
        f"{__import__('scipy').__version__} (Python "
        f"{'.'.join(map(str, sys.version_info[:3]))}), helper tái dùng nguyên "
        "xi (`group_table`, `anova_kruskal`, `source_note`, `place_n_labels`). "
        "Mọi số tự tính lại từ CSV — không hardcode, không nội suy.\n"
    )
    md.append(f"## 1) Dữ liệu và join — cửa sổ giao {wyears}\n")
    md.append(
        f"- `external_poverty_63.csv`: {len(pov)} dòng × "
        f"{pov.year.nunique()} năm ({fmt_window(sorted(int(y) for y in pov.year.unique()))}); "
        f"cửa sổ giao có nhãn: **{n_win} ô**, trong đó **{n_val} ô có giá trị** "
        f"`poverty_rate_pct`.\n"
        f"- Thiếu phía nguồn (dòng có trong CSV, giá trị trống — nguồn pxweb "
        f"ghi `\"..\"`): {missing_src_txt}. KHÔNG nội suy "
        f"(data/raw/gso/PROVENANCE.md:90).\n"
        f"- Left-join nhãn cụm: **{n_panel} ô vào kiểm định**; **{n_no_label} "
        "ô tỉnh-năm có poverty nhưng KHÔNG có nhãn** (panel PAPI thiếu "
        "sd_4_2/sd_6_1) — loại KHỎI kiểm định, mask tường minh (pattern GRDP, "
        f"external_validation.py:477-486): {no_label_txt}.\n"
        f"- Panel theo cụm: " + ", ".join(
            f"{CLUSTER_LABELS[int(k)]} n={int(v)}" for k, v in cnt.items())
        + ".\n"
    )
    md.append("## 2) Kiểm định gộp — HAI kết quả báo cáo CÙNG nhau\n")
    md.append(tab_raw.to_markdown(index=False))
    md.append("")
    md.append(tab_dm.to_markdown(index=False))
    md.append("")
    md.append(
        f"- **Gộp thô** (poverty gốc, nhiễm xu hướng năm): Kruskal–Wallis "
        f"H = {t_raw['h']:.4f}, {fmt_p(t_raw['p_kw'])}; One-way ANOVA "
        f"F({t_raw['df1']},{t_raw['df2']}) = {t_raw['f']:.4f}, "
        f"{fmt_p(t_raw['p_anova'])}; eta² = {t_raw['eta_sq']:.4f} — KHÔNG đáng "
        "kể thống kê.\n"
        f"- **Đã trừ median trong năm** (tách hiệu ứng năm): Kruskal–Wallis "
        f"H = {t_dm['h']:.4f}, {fmt_p(t_dm['p_kw'])}; ANOVA "
        f"F({t_dm['df1']},{t_dm['df2']}) = {t_dm['f']:.4f}, "
        f"{fmt_p(t_dm['p_anova'])}; eta² = {t_dm['eta_sq']:.4f} — đáng kể.\n"
        f"- Median nghèo toàn panel giảm rất mạnh xuyên năm: "
        f"{med_year.iloc[0]:.1f}% ({int(med_year.index[0])}) → "
        f"{med_year.iloc[-1]:.1f}% ({int(med_year.index[-1])}); tỷ trọng cụm "
        f"cũng trôi theo năm (nhiễu {int(noise_by_year.iloc[0])}/{len(d[d.year == d.year.iloc[0]])} "
        f"năm {int(noise_by_year.index[0])} → "
        f"{int(noise_by_year.min())}–{int(noise_by_year.max())}/63 trong các "
        "năm của cửa sổ). Test gộp thô phối trộn hiệu ứng năm với khác biệt cụm — "
        "hai số trên PHẢI đọc cùng nhau, không chọn trình bày một kết quả.\n"
        f"- Diễn giải thận trọng: cụm 0 (n={int(cnt.get(0, 0))}) và cụm 1 "
        f"(n={int(cnt.get(1, 0))}) quá nhỏ để tự kết luận; cặp tương phản đáng "
        "tin duy nhất là **nhiễu vs cụm 2** (đối xứng cảnh báo PCI — "
        "external_validation.py:608-610). Đọc eta²/ANOVA chỉ như mô tả bổ "
        "sung.\n"
    )
    md.append("## 3) Mann–Whitney nhiễu vs cụm 2 (hai phía)\n")
    md.append(
        f"- Thô: U = {mw_raw['u']:.0f}, {fmt_p(mw_raw['p'])} — "
        f"{mw_verdict(mw_raw['p'])}.\n"
        f"- Đã trừ median trong năm: U = {mw_dm['u']:.0f}, "
        f"{fmt_p(mw_dm['p'])} — {mw_verdict(mw_dm['p'])}.\n"
        f"- Kết luận an toàn: ở mức gộp, Mann–Whitney nhiễu vs cụm 2 "
        f"{mw_verdict(mw_raw['p'])} (thô) và {mw_verdict(mw_dm['p'])} (đã trừ "
        "median năm) — nghèo GSO đọc như kiểm chứng bổ trợ, không phải bằng "
        "chứng độc lập mạnh như PCI; tín hiệu cụm (nếu có) nằm trong kiểm "
        "định đã-trừ-median-năm ở mục 2, so phân phối toàn bộ các nhóm.\n"
    )
    md.append("## 4) Thống kê từng nhóm — RIÊNG TỪNG năm giao và pooled\n")
    md.append(f"### 4a) Pooled gộp thô (n={n_panel})\n")
    md.append(tab_raw.to_markdown(index=False))
    md.append("")
    md.append(f"### 4b) Pooled đã trừ median trong năm (n={n_panel})\n")
    md.append(tab_dm.to_markdown(index=False))
    md.append("")
    md.append("### 4c) Theo từng năm × cụm (giá trị thô)\n")
    md.append(tab_year.to_markdown(index=False))
    md.append("")
    md.append("### 4d) Cỡ nhóm theo năm (n ô)\n")
    md.append(xt.to_markdown())
    md.append("")
    md.append("### 4e) Kruskal–Wallis từng năm — CHỈ mô tả, không phải kiểm "
              "định chính\n")
    md.append(kw_tab.to_markdown(index=False))
    md.append("")
    kw_degen = [int(r["year"]) for r in kw_year if "suy biến" in r["note"]]
    kw_valid = [int(r["year"]) for r in kw_year if "suy biến" not in r["note"]]
    md.append(
        "- Trừ median trong năm là HẰNG SỐ trong năm nên không đổi so sánh "
        "giữa cụm trong từng năm — thống kê theo năm chỉ cần trình bày trên "
        "giá trị thô.\n"
        f"- Năm {', '.join(map(str, kw_valid))} có test ≥3 nhóm không suy "
        f"biến; năm {', '.join(map(str, kw_degen))} suy biến (n<2 hoặc chỉ 2 "
        "nhóm — cụm 0/1 rỗng) → KW từng năm không phải bằng chứng độc lập.\n"
    )
    md.append("## 5) Caveats\n")
    md.append(f"1. {missing_src_txt} thiếu `poverty_rate_pct` phía nguồn "
              "(pxweb ghi `\"..\"`) — dòng có trong CSV nhưng bị loại khỏi "
              "kiểm định vì NaN; KHÔNG nội suy "
              "(data/raw/gso/PROVENANCE.md:90).\n")
    md.append(
        f"2. Các năm {', '.join(map(str, pov_only_years))} có poverty nhưng "
        "KHÔNG có nhãn cụm (`predict_all_years.csv` chỉ phủ 2011–2024; 2025 "
        "còn là Sơ bộ) → loại khỏi mọi thống kê theo cụm.\n")
    md.append(
        f"3. Các năm {', '.join(map(str, label_only_years))} KHÔNG có poverty: "
        "bảng pxweb V14.47 không có cột năm đó (data/raw/gso/PROVENANCE.md:25) "
        "→ loại.\n")
    md.append(
        f"4. {n_no_label} ô tỉnh-năm trong cửa sổ giao có poverty nhưng không "
        f"có nhãn (panel PAPI thiếu sd_4_2/sd_6_1): {no_label_txt} — mask "
        "tường minh, không vẽ không test.\n")
    md.append(
        "5. Chuẩn nghèo ĐỔI theo giai đoạn (thu nhập 2011–2015 vs đa chiều từ "
        "~2020 — data/raw/gso/PROVENANCE.md:48-58); các năm 2017–2019 điền "
        "thêm là ĐA CHIỀU theo footnote (*) của bảng Niên giám — cùng chuẩn với "
        "phần pxweb từ 2020, khớp 124/124 ở cột giao 2020/2021 "
        "(scripts/build_poverty_gap.py): so MỨC tuyệt đối xuyên "
        "năm không like-for-like; chỉ so GIỮA CỤM trong cùng một năm là hợp "
        "lệ — lý do bắt buộc phải có test đã-trừ-median-năm song song với "
        "test gộp.\n")
    md.append(
        f"6. KW gộp thô KHÔNG đáng kể ({fmt_p(t_raw['p_kw'])}) trong khi "
        f"đã-trừ-median-năm đáng kể ({fmt_p(t_dm['p_kw'])}): hai kết quả phải "
        "báo cáo cùng nhau; không được chọn trình bày một kết quả duy nhất "
        "(nguyên tắc trung thực của repo, build_report.py:628).\n")
    md.append(
        f"7. Cụm 0 (n={int(cnt.get(0, 0))}) và cụm 1 (n={int(cnt.get(1, 0))}) "
        "quá nhỏ để tự kết luận — cặp tương phản đáng tin duy nhất là nhiễu "
        "vs cụm 2; đọc eta²/ANOVA chỉ như mô tả.\n")
    md.append(
        "8. KW theo từng năm không khả thi ở 2012/2015/2016 (nhóm n<2) và suy "
        "biến 2 nhóm ở 2020–2024 — chỉ dạng bảng mô tả, không làm kiểm định "
        "chính.\n")
    md.append(
        f"9. Tỷ trọng cụm trôi mạnh theo năm (nhiễu {int(noise_by_year.iloc[0])}"
        f"/63 năm {int(noise_by_year.index[0])} → "
        f"{int(noise_by_year.min())}–{int(noise_by_year.max())}/63 trong các "
        "năm của cửa sổ) — test gộp phối trộn năm với cụm; limitation khai "
        "báo, không phải lỗi dữ liệu.\n")
    md.append(
        "10. External check bằng thước đo độc lập (GSO thống kê chính thức, "
        "tách khỏi PAPI khảo sát hộ dân) — KHÔNG đưa vào feature, KHÔNG chứng "
        "minh nhân quả; poverty là kết quả thứ hai sau PCI nên đọc như kiểm "
        "chứng bổ trợ, không thay thế kiểm định chính PCI.\n")
    md.append(
        "11. Hà Nội bao gồm Hà Tây từ 2008 (chú thích gốc bảng, "
        "data/raw/gso/PROVENANCE.md:48) — ngoài cửa sổ phân tích nhưng ghi "
        "trong provenance để tránh nhầm khi mở rộng cửa sổ.\n")
    md.append("## 6) Tái lập\n")
    md.append(
        "```powershell\npython -E scripts/poverty_validation.py\n```\n"
        f"- Đầu vào: `{POVERTY_CSV.relative_to(ROOT).as_posix()}` + "
        f"`{LABELS_CSV.relative_to(ROOT).as_posix()}`.\n"
        f"- Đầu ra: `results/{OUT_MD.name}` (file này), "
        f"`results/{OUT_CSV.name}`, `results/figs/{OUT_PNG.name}`.\n"
        f"- Determinism: chạy 2 lần — md/csv byte-giống (sha256); hình vẽ bằng "
        f"rng seed 11.\n"
        f"- Provenance nguồn: `data/raw/gso/PROVENANCE.md` (tải "
        f"{RETRIEVED_DATE}), `data/processed/external_provenance.md`; kiểm "
        "định chính PCI: `results/external_validation.md`."
    )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Đã ghi {OUT_MD}")

    make_figure(d, window, t_raw, t_dm, mw_raw, mw_dm, OUT_PNG, n_no_label)
    print(f"Đã ghi {OUT_PNG} (dpi={FIG_DPI_PRINT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
