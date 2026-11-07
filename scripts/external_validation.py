"""External validation của cụm STING bằng các nguồn ĐỘC LẬP với PAPI.

Gap [2], [8], [9] trong reports/external_data_expansion.md §4.2 (cộng phần
GRDP của gap [3] dưới dạng quyết định thiết kế). Chạy từ thư mục gốc:

    python scripts/external_validation.py

Bốn phần:
  1. Kiểm định CHÍNH — PCI (VCCI–USAID, khảo sát doanh nghiệp, tách hoàn toàn
     khỏi PAPI) theo nhãn cụm STING trên lưới đầy 2011–2022 (756 ô có điểm
     PCI; 9 ô trong đó không có nhãn cụm → join được 747 điểm). One-way ANOVA
     + Kruskal–Wallis của pci_weighted_score theo pred_cluster.
  2. Kiểm tra PHỤ Top-30 2023–2024 (60 ô) — cảnh báo chọn mẫu: nhà xuất bản
     chỉ công bố tỉnh tốt; tập Top-30 hai năm không cùng tập.
  3. Mật độ cơ sở y tế/1.000 dân theo cụm năm 2020 (ODM health + dân số GSO),
     ghi chú bắt buộc "10 tỉnh count=0 là 0-thật (nguồn điểm không phủ)".
  4. Bối cảnh vĩ mô WDI 2010–2024 (panel 2×2) — chuỗi không đều phía nguồn,
     KHÔNG nội suy; và GRDP/người theo cụm cửa sổ 2018–2024 (2024 = Sơ bộ).

Nguyên tắc:
  - Nhãn cụm lấy từ results/predict_all_years.csv (model CHỐT, refit tất định
    được gate bởi tests/test_artifact_reproduction.py) — KHÔNG dùng
    results/cluster_labels.csv (phương pháp per-year khác, artifact khác).
  - Join theo khóa (year, province_code); kiểm tra khóa duy nhất hai phía.
  - Không nội suy ô thiếu; không tự tính lại PCI weighted score từ sub-index.
  - Thống kê: scipy.stats (f_oneway, kruskal). Script tự tính lại mọi số từ
    CSV, không hardcode.

Đầu ra:
  results/external_validation.md                     — báo cáo 4 phần
  results/external_validation.csv                    — số liệu dạng bảng
  results/figs/external_pci_by_cluster.png           — boxplot PCI theo cụm
  results/figs/external_health_density_2020.png      — mật độ y tế theo cụm
  results/figs/external_wdi_panel.png                — WDI 2×2
  results/figs/external_grdp_by_cluster.png          — GRDP theo cụm 2018–2024

Trình bày hình theo chuẩn `scripts/fig_style.py`: palette Okabe–Ito, DPI 200,
dòng nguồn ghi ngày tải lấy từ PROVENANCE.md (không tự điền ngày render).
"""

from __future__ import annotations

import math
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Chuẩn trình bày hình của repo (palette Okabe–Ito, rcParams, dòng nguồn) —
# chỉ tác động lớp vẽ, không đổi logic tính số liệu.
from fig_style import (CLUSTER_COLORS, CLUSTER_LABELS, PALETTE, UNIT_LABELS,
                       add_source, apply_style, new_fig, save_png)

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RES = ROOT / "results"
FIGS = RES / "figs"

PCI_CSV = PROC / "external_pci_63_full.csv"
POP_CSV = PROC / "external_gso_population_63_full.csv"
GRDP_CSV = PROC / "external_gso_grdp_63.csv"
ODM_CSV = PROC / "external_odm_health_63.csv"
WDI_CSV = PROC / "external_worldbank_vnm.csv"
LABELS_CSV = RES / "predict_all_years.csv"

# Ngày tải của TẤT CẢ các nguồn external — xác nhận trong data/raw/*/PROVENANCE.md
# (pci, gso, odmekong, worldbank đều ghi "Ngày tải: 2026-11-07").
RETRIEVED_DATE = "2026-11-07"

# Fallback màu cho nhãn ngoài {-1, 0, 1, 2} — không xảy ra với dữ liệu hiện có.
_FALLBACK_COLOR = "#937860"


def fmt_p(p: float) -> str:
    return "p < 1e-12" if p < 1e-12 else f"p = {p:.3g}"


def group_table(df: pd.DataFrame, value_col: str, group_col: str = "pred_cluster") -> pd.DataFrame:
    rows = []
    for lab, sub in df.groupby(group_col):
        v = sub[value_col]
        rows.append({
            "pred_cluster": int(lab),
            "nhóm": CLUSTER_LABELS.get(int(lab), str(lab)),
            "n": len(sub),
            "mean": round(float(v.mean()), 3),
            "median": round(float(v.median()), 3),
            "std": round(float(v.std(ddof=1)), 3) if len(sub) > 1 else None,
            "min": round(float(v.min()), 3),
            "max": round(float(v.max()), 3),
        })
    return pd.DataFrame(rows).sort_values("pred_cluster").reset_index(drop=True)


def anova_kruskal(df: pd.DataFrame, value_col: str) -> dict:
    groups = [g[value_col].to_numpy() for _, g in df.groupby("pred_cluster")]
    f_stat, p_anova = stats.f_oneway(*groups)
    h_stat, p_kw = stats.kruskal(*groups)
    grand = df[value_col].to_numpy()
    ss_total = float(((grand - grand.mean()) ** 2).sum())
    ss_between = float(sum(
        len(g) * (g.mean() - grand.mean()) ** 2
        for g in (pd.Series(x) for x in groups)
    ))
    return {
        "f": float(f_stat), "p_anova": float(p_anova),
        "df1": len(groups) - 1, "df2": len(df) - len(groups),
        "h": float(h_stat), "p_kw": float(p_kw),
        "eta_sq": ss_between / ss_total if ss_total > 0 else float("nan"),
        "n": len(df),
    }


def test_rows(section: str, t: dict) -> list[dict]:
    k = t["df1"]
    return [
        {"section": section, "group": f"ANOVA F({k},{t['df2']})", "year": "", "n": t["n"],
         "mean": "", "median": "", "std": "", "min": "", "max": "",
         "note": f"F = {t['f']:.4f}; {fmt_p(t['p_anova'])}"},
        {"section": section, "group": "Kruskal–Wallis", "year": "", "n": t["n"],
         "mean": "", "median": "", "std": "", "min": "", "max": "",
         "note": f"H = {t['h']:.4f}; {fmt_p(t['p_kw'])}"},
        {"section": section, "group": "eta squared", "year": "", "n": t["n"],
         "mean": "", "median": "", "std": "", "min": "", "max": "",
         "note": f"eta² = {t['eta_sq']:.4f} (SS giữa / SS tổng)"},
    ]


def stats_rows(section: str, tab: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in tab.iterrows():
        rows.append({
            "section": section, "group": r["nhóm"], "year": "", "n": r["n"],
            "mean": r["mean"], "median": r["median"], "std": r["std"],
            "min": r["min"], "max": r["max"], "note": "",
        })
    return rows


def source_note(fig, source: str, retrieved: str | None = None,
                extra: str | None = None, *, wrap_width: int = 100) -> int:
    """Ghi dòng nguồn bằng helper chuẩn ``fig_style.add_source``.

    Trả về số dòng sau khi wrap (đếm theo cùng quy tắc của helper) để phần
    gọi chừa lề dưới cho ``tight_layout(rect=...)`` — helper chuẩn không trả
    giá trị nên đếm lại tại đây. Định dạng dòng:
    ``'Nguồn: <nguồn> — tải <ngày> — <extra>'``.
    """
    parts = [f"Nguồn: {source}"]
    if retrieved:
        parts.append(f"tải {retrieved}")
    if extra:
        parts.append(extra)
    text = " — ".join(parts)
    n_lines = sum(
        max(1, len(textwrap.wrap(chunk, wrap_width)))
        for chunk in text.split("\n")
    )
    add_source(fig, source, retrieved=retrieved, extra=extra, wrap_width=wrap_width)
    return n_lines


def source_rect_bottom(n_lines: int) -> float:
    """Lề dưới cho ``tight_layout`` đủ chỗ cho ``n_lines`` dòng nguồn 8pt."""
    return min(0.32, 0.02 + 0.032 * n_lines)


# DPI xuất cho 2 hình bị nhận xét độ phân giải ở vòng soi 1 (GRDP, WDI): figure
# 6.5 in x 400 dpi ≈ 2600 px rộng → chèn full-width 15–16 cm trong báo cáo vẫn
# đạt ≥ 300 dpi hiệu dụng (chuẩn in), thay vì ~210 dpi khi lưu 200 dpi.
FIG_DPI_PRINT = 400


def _pt_seg_dist(
    px: float, py: float, seg: tuple[tuple[float, float], tuple[float, float]]
) -> float:
    """Khoảng cách điểm → đoạn thẳng trong cùng hệ tọa độ (pixel hiển thị)."""
    (x1, y1), (x2, y2) = seg
    dx, dy = x2 - x1, y2 - y1
    den = dx * dx + dy * dy
    if den == 0.0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / den))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def place_n_labels(
    ax, series: list[tuple[int, list[tuple[float, float, int]]]]
) -> None:
    """Đặt nhãn ``n=…`` về phía trống nhất quanh mỗi điểm — CHỈ lớp trình bày.

    Trước đây nhãn luôn đặt trên điểm nên đường của cụm khác đi xuyên qua chữ
    (GRDP: nhãn cụm 2 năm 2019 bị đường nhiễu cắt ngang, nhãn nhiễu năm 2020
    bị đường cụm 2 cắt ngang). Hàm chấm từng ứng viên vị trí (trên/dưới điểm,
    kèm lệch ngang) bằng khoảng cách gần nhất tới đường/marker của cụm KHÁC,
    legend, các nhãn đã đặt và biên khung trục rồi chọn ứng viên xa nhất.
    Không đọc/sửa bất kỳ giá trị dữ liệu nào — chỉ chọn vị trí chữ.
    """
    fig = ax.figure
    fig.canvas.draw()  # chốt bố cục (gọi sau tight_layout) để có tọa độ hiển thị
    rend = fig.canvas.get_renderer()
    pt = fig.dpi / 72.0  # điểm ảnh trên 1pt
    pts_px = {
        lab: [tuple(ax.transData.transform((x, y))) for x, y, _ in rows]
        for lab, rows in series
    }
    segs = [  # (đoạn nối 2 điểm liền kề, nhãn chủ)
        ((pts_px[lab][k], pts_px[lab][k + 1]), lab)
        for lab, rows in series for k in range(len(pts_px[lab]) - 1)
    ]
    markers = [  # điểm dữ liệu của từng cụm (marker tròn)
        (pts_px[lab][k], lab) for lab, rows in series for k in range(len(rows))
    ]
    ax_bb = ax.get_window_extent()
    leg = ax.get_legend()
    leg_bb = leg.get_window_extent(rend) if leg is not None else None
    placed: list[tuple[float, float, float, float]] = []  # tâm + nửa rộng/cao nhãn
    # Ứng viên offset (dx_pt, dy_pt) — trên trước (giữ thói quen đọc cũ).
    candidates = ((0, 8), (0, -9), (9, 8), (-9, 8), (9, -9), (-9, -9),
                  (16, 8), (-16, 8), (16, -9), (-16, -9))
    for lab, rows in series:
        for k, (yr, med, n) in enumerate(rows):
            x0, y0 = pts_px[lab][k]
            best = None
            for dx_pt, dy_pt in candidates:
                cx, cy = x0 + dx_pt * pt, y0 + dy_pt * pt
                if not (ax_bb.x0 + 3 <= cx <= ax_bb.x1 - 3
                        and ax_bb.y0 + 3 <= cy <= ax_bb.y1 - 3):
                    continue  # ứng viên lòi ra ngoài khung trục
                d = min((_pt_seg_dist(cx, cy, s) for s, owner in segs
                         if owner != lab), default=float("inf"))
                md = [math.hypot(cx - qx, cy - qy)
                      for (qx, qy), owner in markers if owner != lab]
                if md:
                    d = min(d, min(md))
                for lx, ly, hw, hh in placed:
                    d = min(d, math.hypot(max(abs(cx - lx) - hw, 0.0),
                                          max(abs(cy - ly) - hh, 0.0)))
                if leg_bb is not None:
                    d = min(d, math.hypot(max(leg_bb.x0 - cx, 0.0, cx - leg_bb.x1),
                                          max(leg_bb.y0 - cy, 0.0, cy - leg_bb.y1)))
                if best is None or d > best[0]:
                    best = (d, dx_pt, dy_pt)
            dx_pt, dy_pt = (best[1], best[2]) if best else (0, 8)
            ann = ax.annotate(f"n={n}", (yr, med), fontsize=6.5,
                              xytext=(dx_pt, dy_pt), textcoords="offset points",
                              ha="center", va="bottom" if dy_pt > 0 else "top")
            bb = ann.get_window_extent(rend)
            placed.append(((bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2,
                           bb.width / 2, bb.height / 2))


def plot_pci(df: pd.DataFrame, t: dict, out_path: Path, title: str, source: str,
             *, retrieved: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = sorted(df["pred_cluster"].unique())
    arrays = [df.loc[df.pred_cluster == lab, "pci_weighted_score"].to_numpy()
              for lab in labels]
    fig, ax = new_fig()  # 6.5 x 4.3 in — đúng cột docx
    bp = ax.boxplot(arrays, patch_artist=True, widths=0.55, showfliers=False,
                    medianprops={"color": "#222222"})
    for patch, lab in zip(bp["boxes"], labels):
        patch.set_facecolor(CLUSTER_COLORS.get(int(lab), _FALLBACK_COLOR))
        patch.set_alpha(0.55)
    rng = np.random.default_rng(11)
    for i, (arr, lab) in enumerate(zip(arrays, labels), start=1):
        jitter = rng.uniform(-0.16, 0.16, size=len(arr))
        ax.scatter(np.full(len(arr), i) + jitter, arr, s=9, alpha=0.35,
                   color=CLUSTER_COLORS.get(int(lab), _FALLBACK_COLOR),
                   edgecolors="none")
    ax.set_xticklabels([
        f"{CLUSTER_LABELS.get(int(lab), lab)}\nn = {len(a)}" for lab, a in zip(labels, arrays)
    ])
    ax.set_xlabel("Nhóm nhãn cụm STING (pred_cluster)")
    ax.set_ylabel(f"PCI điểm tổng ({UNIT_LABELS['pci']})")
    sub = (f"One-way ANOVA F({t['df1']},{t['df2']}) = {t['f']:.2f}, "
           f"{fmt_p(t['p_anova'])}; Kruskal–Wallis H = {t['h']:.2f}, "
           f"{fmt_p(t['p_kw'])}; eta² = {t['eta_sq']:.3f}")
    # Tiêu đề chính theo rcParams (12pt đậm); dòng thống kê là chú thích nhỏ
    # đặt dưới tiêu đề, trên khung trục.
    ax.set_title(title, pad=30)
    ax.text(0.5, 1.01, "\n".join(textwrap.wrap(sub, 80)), transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9, color="#444444")
    ax.grid(axis="y", alpha=0.25)
    n_src = source_note(fig, source, retrieved=retrieved)
    fig.tight_layout(rect=(0, source_rect_bottom(n_src), 1, 1))
    save_png(fig, out_path)
    plt.close(fig)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_style()  # rcParams chuẩn repo — chỉ tác động lớp trình bày hình

    FIGS.mkdir(parents=True, exist_ok=True)

    pci = pd.read_csv(PCI_CSV)
    labels = pd.read_csv(LABELS_CSV)
    assert not labels.duplicated(["year", "province_code"]).any(), "nhãn trùng khóa"

    # ================================================================== #
    # 1) Kiểm định CHÍNH: PCI 2011–2022 theo nhãn cụm STING
    # ================================================================== #
    main = pci[(pci.year >= 2011) & (pci.year <= 2022) & pci.pci_weighted_score.notna()]
    m = main.merge(labels[["year", "province_code", "pred_cluster"]],
                   on=["year", "province_code"], how="left", validate="one_to_one")
    n_no_label = int(m.pred_cluster.isna().sum())
    dmain = m.dropna(subset=["pred_cluster"]).copy()
    dmain["pred_cluster"] = dmain["pred_cluster"].astype(int)
    no_label_cells = m.loc[m.pred_cluster.isna(), ["year", "province_ascii"]]
    print(f"1) PCI 2011–2022: {len(main)} ô có điểm; thiếu nhãn {n_no_label} "
          f"→ kiểm định trên {len(dmain)} điểm")
    tab_main = group_table(dmain, "pci_weighted_score")
    t_main = anova_kruskal(dmain, "pci_weighted_score")
    print(tab_main.to_string(index=False))
    print(f"   ANOVA F({t_main['df1']},{t_main['df2']})={t_main['f']:.4f} "
          f"({fmt_p(t_main['p_anova'])}) | Kruskal H={t_main['h']:.4f} "
          f"({fmt_p(t_main['p_kw'])}) | eta²={t_main['eta_sq']:.4f}")
    plot_pci(
        dmain, t_main, FIGS / "external_pci_by_cluster.png",
        "PCI (VCCI–USAID) theo cụm STING — lưới đầy 2011–2022",
        "PCI VCCI–USAID 2011–2022 (pcivietnam.vn — data/raw/pci) → "
        "data/processed/external_pci_63_full.csv; nhãn cụm STING "
        "từ results/predict_all_years.csv (model đóng băng)",
        retrieved=RETRIEVED_DATE,
    )

    # ================================================================== #
    # 2) Kiểm tra PHỤ: Top-30 2023–2024 (chọn mẫu — chỉ tỉnh tốt)
    # ================================================================== #
    t30 = pci[(pci.year >= 2023) & pci.pci_weighted_score.notna()]
    mt = t30.merge(labels[["year", "province_code", "pred_cluster"]],
                   on=["year", "province_code"], how="left", validate="one_to_one")
    dtop = mt.dropna(subset=["pred_cluster"]).copy()
    dtop["pred_cluster"] = dtop["pred_cluster"].astype(int)
    sets = {y: set(t30.loc[t30.year == y, "province_ascii"]) for y in (2023, 2024)}
    only23 = sorted(sets[2023] - sets[2024])
    only24 = sorted(sets[2024] - sets[2023])
    tab_top = group_table(dtop, "pci_weighted_score")
    t_top = anova_kruskal(dtop, "pci_weighted_score")
    print(f"2) Top-30 2023–2024: {len(t30)} ô có điểm, {len(dtop)} ô có nhãn; "
          f"chỉ 2023 có {only23}; chỉ 2024 có {only24}")
    print(tab_top.to_string(index=False))
    print(f"   ANOVA F({t_top['df1']},{t_top['df2']})={t_top['f']:.4f} "
          f"({fmt_p(t_top['p_anova'])}) | Kruskal H={t_top['h']:.4f} "
          f"({fmt_p(t_top['p_kw'])})")

    # ================================================================== #
    # 3) Mật độ y tế 2020 theo cụm (ODM health + dân số GSO)
    # ================================================================== #
    odm = pd.read_csv(ODM_CSV)
    pop = pd.read_csv(POP_CSV)
    p20 = pop[pop.year == 2020][["province_code", "gso_pop_total_thousand"]]
    h = odm.merge(p20, on="province_code", how="left", validate="one_to_one")
    assert h.gso_pop_total_thousand.notna().all(), "dân số 2020 thiếu tỉnh"
    h = h.merge(labels[["year", "province_code", "pred_cluster"]],
                on=["year", "province_code"], how="left", validate="one_to_one")
    assert h.pred_cluster.notna().all(), "2020 có tỉnh thiếu nhãn cụm"
    h["pred_cluster"] = h["pred_cluster"].astype(int)
    h["fac_per_1000"] = h["hospital_count_odm2020"] / h["gso_pop_total_thousand"]
    zero10 = h.loc[h.hospital_count_odm2020 == 0, "province_vi"].tolist()
    health_rows = []
    for lab, sub in h.groupby("pred_cluster"):
        fac, popk = sub.hospital_count_odm2020.sum(), sub.gso_pop_total_thousand.sum()
        health_rows.append({
            "section": "odm_health_2020", "group": CLUSTER_LABELS[int(lab)],
            "year": 2020, "n": len(sub),
            "mean": round(float(sub.fac_per_1000.mean()), 6),
            "median": round(float(sub.fac_per_1000.median()), 6),
            "std": round(float(sub.fac_per_1000.std(ddof=1)), 6) if len(sub) > 1 else None,
            "min": round(float(sub.fac_per_1000.min()), 6),
            "max": round(float(sub.fac_per_1000.max()), 6),
            "note": (f"tổng {int(fac)} cơ sở / {popk / 1000:.2f} triệu người → "
                     f"{fac / popk:.6f} cơ sở/1.000 dân (theo quy mô nhóm)"),
        })
    print("3) Y tế 2020:", len(h), "tỉnh; 10 tỉnh count=0:",
          ", ".join(sorted(zero10)))

    fig, ax = new_fig()  # 6.5 x 4.3 in — đúng cột docx
    labs = sorted(h.pred_cluster.unique())
    arrays = [h.loc[h.pred_cluster == lab, "fac_per_1000"].to_numpy() for lab in labs]
    bp = ax.boxplot(arrays, patch_artist=True, widths=0.5, showfliers=False,
                    medianprops={"color": "#222222"})
    for patch, lab in zip(bp["boxes"], labs):
        patch.set_facecolor(CLUSTER_COLORS.get(int(lab), _FALLBACK_COLOR))
        patch.set_alpha(0.55)
    rng = np.random.default_rng(11)
    for i, (arr, lab) in enumerate(zip(arrays, labs), start=1):
        ax.scatter(np.full(len(arr), i) + rng.uniform(-0.14, 0.14, len(arr)),
                   arr, s=14, alpha=0.5,
                   color=CLUSTER_COLORS.get(int(lab), _FALLBACK_COLOR),
                   edgecolors="none")
    ax.set_xticklabels([
        f"{CLUSTER_LABELS.get(int(lab), lab)}\nn = {len(a)} tỉnh"
        for lab, a in zip(labs, arrays)
    ])
    ax.set_xlabel("Nhóm nhãn cụm STING 2020 (pred_cluster)")
    ax.set_ylabel("Bệnh viện/điểm y tế trên 1.000 dân (2020)")
    ax.set_title("Mật độ cơ sở y tế 2020 theo cụm STING\n"
                 "(ODM Health Facilities + dân số GSO)")
    ax.grid(axis="y", alpha=0.25)
    zero_names = ", ".join(zero10)
    n_src = source_note(
        fig,
        "ODM Health Facilities in Mekong Countries 2020 (ODbL — data/raw/odmekong), "
        "point-in-polygon qua ranh giới 63 tỉnh; dân số GSO 2020 (data/raw/gso)",
        retrieved=RETRIEVED_DATE,
        extra=("Ghi chú: 10 tỉnh count=0 là 0-THẬT (nguồn điểm không phủ, "
               f"không phải lỗi nối tên): {zero_names}"),
    )
    fig.tight_layout(rect=(0, source_rect_bottom(n_src), 1, 1))
    save_png(fig, FIGS / "external_health_density_2020.png")
    plt.close(fig)

    # ================================================================== #
    # 4) GRDP/người theo cụm, cửa sổ 2018–2024 (2024 = Sơ bộ)
    # ================================================================== #
    grdp = pd.read_csv(GRDP_CSV)
    mg = grdp.merge(labels[["year", "province_code", "pred_cluster"]],
                    on=["year", "province_code"], how="left", validate="one_to_one")
    masked = mg.loc[mg.pred_cluster.isna(), ["year", "province_ascii"]]
    dg = mg.dropna(subset=["pred_cluster"]).copy()
    dg["pred_cluster"] = dg["pred_cluster"].astype(int)
    print(f"4) GRDP 2018–2024: {len(grdp)} ô, có nhãn {len(dg)}; thiếu nhãn "
          f"{len(masked)}: {masked.to_dict('records')}")
    grdp_rows = []
    for (lab, yr), sub in dg.groupby(["pred_cluster", "year"]):
        grdp_rows.append({
            "section": "grdp_2018_2024", "group": CLUSTER_LABELS[int(lab)],
            "year": int(yr), "n": len(sub),
            "mean": round(float(sub.grdp_per_capita_million_vnd.mean()), 2),
            "median": round(float(sub.grdp_per_capita_million_vnd.median()), 2),
            "std": (round(float(sub.grdp_per_capita_million_vnd.std(ddof=1)), 2)
                    if len(sub) > 1 else ""),
            "min": round(float(sub.grdp_per_capita_million_vnd.min()), 2),
            "max": round(float(sub.grdp_per_capita_million_vnd.max()), 2),
            "note": "",
        })
    print(dg.groupby(["pred_cluster", "year"]).size().to_string())

    fig, ax = new_fig()  # 6.5 x 4.3 in — đúng cột docx
    grdp_series: list[tuple[int, list[tuple[float, float, int]]]] = []
    for lab in sorted(dg.pred_cluster.unique()):
        sub = dg[dg.pred_cluster == lab].groupby("year").agg(
            med=("grdp_per_capita_million_vnd", "median"),
            n=("grdp_per_capita_million_vnd", "size"),
        )
        sub = sub.sort_index()
        ax.plot(sub.index, sub.med, marker="o",
                color=CLUSTER_COLORS.get(int(lab), _FALLBACK_COLOR),
                label=f"{CLUSTER_LABELS[int(lab)]} (trung vị)")
        grdp_series.append(
            (int(lab), [(float(yr), float(r.med), int(r.n)) for yr, r in sub.iterrows()])
        )
    ax.set_ylabel("GRDP/người (triệu đồng, trung vị nhóm)")
    ax.set_xlabel("Năm")
    ax.set_title("GRDP/người theo cụm STING — chỉ cửa sổ 2018–2024\n"
                 "(không nội suy 2011–2017)")
    ax.legend()
    ax.grid(alpha=0.25)
    # Nhãn tỉnh có dấu cho trình bày hình (chỉ đọc, không đổi bộ masked của md)
    masked_vi = mg.loc[mg.pred_cluster.isna(), ["year", "province_vi"]]
    n_src = source_note(
        fig,
        "GSO pxweb V03.12 (data/raw/gso) → data/processed/external_gso_grdp_63.csv; "
        "nhãn cụm results/predict_all_years.csv. 2024 = Sơ bộ (chưa chính thức)",
        retrieved=RETRIEVED_DATE,
        extra=(f"{len(masked)} ô tỉnh-năm trong cửa sổ không có nhãn cụm (panel "
               "PAPI thiếu sd_4_2/sd_6_1) nên không vẽ: "
               + "; ".join(f"{r.province_vi} {int(r.year)}"
                           for _, r in masked_vi.iterrows())),
    )
    fig.tight_layout(rect=(0, source_rect_bottom(n_src), 1, 1))
    # Nhãn n= đặt SAU tight_layout về phía trống nhất — đường cụm khác không
    # còn đi xuyên qua chữ như bản trước (2019, 2020). Chỉ lớp trình bày.
    place_n_labels(ax, grdp_series)
    save_png(fig, FIGS / "external_grdp_by_cluster.png", dpi=FIG_DPI_PRINT)
    plt.close(fig)

    # ================================================================== #
    # 5) WDI — bối cảnh vĩ mô quốc gia 2010–2024 (chuỗi không đều)
    # ================================================================== #
    wdi = pd.read_csv(WDI_CSV)
    # (tên panel, đơn vị trục y): đơn vị đưa về nhãn trục y riêng của từng
    # panel thay vì chỉ nằm trong tiêu đề (nhận xét soi hình vòng 1).
    VI_PANELS = {
        "NY.GDP.PCAP.CD": ("GDP/người", "USD hiện hành"),
        "SP.URB.TOTL.IN.ZS": ("Dân số đô thị", "% tổng dân số"),
        "SH.XPD.CHEX.GD.ZS": ("Chi y tế hiện hành", "% GDP"),
        "SH.MED.BEDS.ZS": ("Giường bệnh", "trên 1.000 dân"),
    }
    wdi_rows = []
    for code, sub in wdi.groupby("indicator_code"):
        sub = sub.sort_values("year")
        wdi_rows.append({
            "section": "wdi_2010_2024", "group": code, "year": "",
            "n": len(sub), "mean": round(float(sub.value.mean()), 3),
            "median": round(float(sub.value.median()), 3), "std": "",
            "min": round(float(sub.value.min()), 3),
            "max": round(float(sub.value.max()), 3),
            "note": (f"cửa sổ thật {int(sub.year.min())}–{int(sub.year.max())} "
                     f"({len(sub)}/15 năm); phần thiếu là phía nguồn — không nội suy"),
        })
        print(f"   WDI {code}: {len(sub)}/15 năm "
              f"({int(sub.year.min())}–{int(sub.year.max())})")

    fig, axes = new_fig(nrows=2, ncols=2)  # 6.5 x 4.3 in — đúng cột docx
    from matplotlib.ticker import MaxNLocator

    for ax, (code, (name, unit)) in zip(axes.flat, VI_PANELS.items()):
        sub = wdi[wdi.indicator_code == code].sort_values("year")
        ax.plot(sub.year, sub.value, marker="o", color=PALETTE["blue"],
                linewidth=1.4)
        # Đầu trên trục y chừa 10% để marker chấm cuối (thường là max) không
        # bị cắt phẳng tại biên axes khi tràn sát trần (GDP 2024, đô thị 2024,
        # giường bệnh 2017) — chỉ đổi khung nhìn, không đổi dữ liệu.
        ax.margins(y=0.10)
        # Mã chỉ số + phủ dữ liệu là dòng nhỏ giữa tiêu đề và khung trục —
        # nằm NGOÀI khung nên không bao giờ đè đường số.
        ax.set_title(name, pad=16)
        ax.set_ylabel(unit)
        ax.text(0.5, 1.02,
                f"{code} — {len(sub)}/15 năm "
                f"({int(sub.year.min())}–{int(sub.year.max())})",
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=7.5, color="#555555")
        # Trục năm nguyên, bước 2/5 năm — tránh tick thập phân và chồng chữ
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        ax.grid(alpha=0.25)
    # Nhãn trục x chung cho hàng dưới (4 panel cùng thang năm 2010–2024).
    for ax in axes.flat[2:]:
        ax.set_xlabel("Năm")
    note = ("Giường bệnh: chuỗi dừng 2017 phía nguồn (raw gốc rỗng 2018–2024) — "
            "KHÔNG nội suy. Chi y tế: thiếu 2024 phía nguồn.")
    fig.suptitle("Bối cảnh vĩ mô Việt Nam (World Bank WDI) —\n"
                 "chuỗi không đều, giữ trống ô thiếu")
    n_src = source_note(
        fig,
        "World Bank WDI, quốc gia VNM (CC BY 4.0; API v2 — data/raw/worldbank) "
        "→ data/processed/external_worldbank_vnm.csv",
        retrieved=RETRIEVED_DATE,
    )
    y_note = 0.008 + 0.032 * n_src + 0.012
    fig.text(0.5, y_note, "\n".join(textwrap.wrap(note, 100)),
             ha="center", va="bottom", fontsize=8, color="#555555")
    # rect top = 1.0: tight_layout tính cả suptitle vào phần dự trữ phía trên,
    # nên trần thấp hơn sẽ đẩy axes xuống tạo khoảng trống lớn dưới suptitle.
    fig.tight_layout(rect=(0, y_note + 0.075, 1, 1.0))
    save_png(fig, FIGS / "external_wdi_panel.png", dpi=FIG_DPI_PRINT)
    plt.close(fig)

    # ================================================================== #
    # 6) Xuất CSV + md
    # ================================================================== #
    rows = (
        stats_rows("pci_2011_2022", tab_main) + test_rows("pci_2011_2022", t_main)
        + stats_rows("pci_top30_2023_2024", tab_top) + test_rows("pci_top30_2023_2024", t_top)
        + health_rows + grdp_rows + wdi_rows
    )
    cols = ["section", "group", "year", "n", "mean", "median", "std", "min", "max", "note"]
    pd.DataFrame(rows)[cols].to_csv(RES / "external_validation.csv",
                                    index=False, encoding="utf-8-sig")
    print(f"Đã ghi {RES / 'external_validation.csv'} ({len(rows)} dòng)")

    md = []
    md.append("# External validation của cụm STING — PCI · y tế 2020 · GRDP · WDI\n")
    md.append(
        "Sinh bởi `scripts/external_validation.py` (gaps [2], [8], [9] + phần GRDP "
        "của gap [3] — reports/external_data_expansion.md §4.2). Nhãn cụm lấy từ "
        "`results/predict_all_years.csv` (model đóng băng, refit tất định được gate "
        "bởi `tests/test_artifact_reproduction.py`); thống kê bằng "
        f"scipy {__import__('scipy').__version__} (Python "
        f"{'.'.join(map(str, sys.version_info[:3]))}). "
        "Mọi số liệu tính lại trực tiếp từ CSV — không hardcode.\n"
    )
    md.append("## 1) Kiểm định CHÍNH: PCI theo nhãn cụm trên lưới đầy 2011–2022\n")
    md.append(
        f"- PCI (`pci_weighted_score`, VCCI–USAID — khảo sát **doanh nghiệp**, tách "
        "hoàn toàn khỏi PAPI là khảo sát hộ dân của CECODES/UNDP) đủ 63 tỉnh × 12 "
        f"năm = **{len(main)} ô**; join với nhãn cụm được **{len(dmain)} điểm** "
        f"({n_no_label} ô có PCI nhưng panel thiếu sd_4_2/sd_6_1 nên không có nhãn: "
        + "; ".join(f"{r.province_ascii} {int(r.year)}"
                    for _, r in no_label_cells.iterrows()) + ").\n"
        "- Không nội suy 66 ô PCI trống 2023–2024; không tự tính weighted score "
        "từ sub-index.\n"
    )
    md.append(tab_main.to_markdown(index=False))
    md.append("")
    md.append(
        f"- **One-way ANOVA:** F({t_main['df1']},{t_main['df2']}) = "
        f"{t_main['f']:.4f}, {fmt_p(t_main['p_anova'])}.\n"
        f"- **Kruskal–Wallis** (phi tham số, có sửa tie): H = {t_main['h']:.4f}, "
        f"{fmt_p(t_main['p_kw'])}; eta² = {t_main['eta_sq']:.4f}.\n"
        "- Diễn giải thận trọng: cụm 0 (n=5) và cụm 1 (n=16) quá nhỏ để tự kết "
        "luận; cặp tương phản đáng tin là **nhiễu vs cụm 2**. PCI khác biệt có ý "
        "nghĩa thống kê giữa các nhóm → cấu trúc cụm STING tương ứng với một thước "
        "đo ĐỘC LẬP chưa từng dùng khi học — external validation đúng nghĩa, KHÔNG "
        "chứng minh quan hệ nhân quả.\n"
        f"- Hình: `results/figs/external_pci_by_cluster.png`.\n"
    )
    md.append("## 2) Kiểm tra PHỤ: Top-30 2023–2024 — có cảnh báo chọn mẫu\n")
    md.append(
        f"- 2023–2024 nhà xuất bản chỉ công bố Top-30 tỉnh tốt: {len(t30)} ô có "
        f"điểm ({len(dtop)} ô có nhãn). Trung bình mẫu bị kéo lên so với tổng thể "
        "(selection bias) → KHÔNG ghép với lưới đủ 63 tỉnh trong cùng một thống kê.\n"
        f"- Tập Top-30 hai năm KHÔNG cùng tập: {len(sets[2023] & sets[2024])} tỉnh "
        f"chung; chỉ 2023 có {', '.join(only23)}; chỉ 2024 có {', '.join(only24)}.\n"
    )
    md.append(tab_top.to_markdown(index=False))
    md.append("")
    md.append(
        f"- ANOVA F({t_top['df1']},{t_top['df2']}) = {t_top['f']:.4f}, "
        f"{fmt_p(t_top['p_anova'])}; Kruskal–Wallis H = {t_top['h']:.4f}, "
        f"{fmt_p(t_top['p_kw'])} — chỉ đọc như kiểm tra phụ.\n"
    )
    md.append("## 3) Mật độ cơ sở y tế/1.000 dân theo cụm — năm 2020 (ODM + GSO)\n")
    hospital_sum = int(h.hospital_count_odm2020.sum())
    md.append(
        f"- **{hospital_sum}** điểm y tế trên "
        f"{h.gso_pop_total_thousand.sum() / 1000:.2f} triệu người (63 tỉnh, join "
        "point-in-polygon với ranh giới `data/raw/boundaries/diaphantinh.geojson`). "
        "Đếm thô không so được tỉnh khác quy mô → chuẩn hóa trên 1.000 dân.\n"
    )
    md.append(pd.DataFrame(health_rows)[
        ["group", "year", "n", "mean", "median", "std", "min", "max", "note"]
    ].to_markdown(index=False))
    md.append("")
    md.append(
        f"- **10 tỉnh `count = 0` là 0-thật** (nguồn điểm không phủ tỉnh đó, KHÔNG "
        f"phải lỗi map tên — dump 2.169 điểm đã point-in-polygon với bộ alias tên "
        f"tỉnh đã kiểm tra): {', '.join(zero10)}.\n"
        "- Snapshot một năm duy nhất (2020), đếm số ĐIỂM không phải số giường → "
        "chỉ dùng làm external check một lần, không đưa vào feature.\n"
        f"- Hình: `results/figs/external_health_density_2020.png`.\n"
    )
    md.append("## 4) GRDP/người theo cụm — chỉ cửa sổ 2018–2024 (quyết định thiết kế)\n")
    md.append(
        f"- GRDP pxweb V03.12 chỉ phủ 2018–2024 ({len(grdp)} ô, 0 ô trống trong "
        "cửa sổ); **không nội suy 441 ô 2011–2017** (lỗ phía nguồn, gap [3]). "
        "Thiết kế chốt: GRDP chỉ dùng cửa sổ 2018–2024, dân số là normalizer chính "
        "xuyên panel.\n"
        f"- Join với nhãn cụm được **{len(dg)}/{len(grdp)} ô**; {len(masked)} ô "
        "trong cửa sổ thiếu nhãn (panel PAPI thiếu sd_4_2/sd_6_1) — mask tường "
        "minh, không vẽ: "
        + "; ".join(f"{r.province_ascii} {int(r.year)}"
                    for _, r in masked.iterrows()) + ".\n"
        "- Trong cửa sổ này gần như chỉ còn nhiễu vs cụm 2 (cụm 0 rỗng, cụm 1 "
        "còn ít điểm) — hình nói đúng điều dữ liệu cho phép.\n"
    )
    md.append(pd.DataFrame(grdp_rows)[
        ["group", "year", "n", "mean", "median", "std", "min", "max"]
    ].to_markdown(index=False))
    md.append("")
    md.append(
        "- **2024 = Sơ bộ** (GSO pxweb, chưa chính thức — có thể được sửa sau); "
        "Hình: `results/figs/external_grdp_by_cluster.png`.\n"
    )
    md.append("## 5) WDI — bối cảnh vĩ mô quốc gia (chuỗi không đều phía nguồn)\n")
    md.append(pd.DataFrame(wdi_rows)[
        ["group", "n", "mean", "median", "min", "max", "note"]
    ].to_markdown(index=False))
    md.append("")
    md.append(
        "- `SH.MED.BEDS.ZS` (giường bệnh) dừng 2017 và `SH.XPD.CHEX.GD.ZS` (chi y "
        "tế) thiếu 2024 — truncate là phía nguồn; giữ ô trống, không nội suy.\n"
        "- Cấp QUỐC GIA: dùng làm bối cảnh/year effects, không phải feature cấp "
        "tỉnh (giá trị giống nhau cho mọi tỉnh trong cùng một năm).\n"
        "- Hình: `results/figs/external_wdi_panel.png`.\n"
    )
    md.append("## 6) Tái lập\n")
    md.append(
        "```powershell\npython -E scripts/external_validation.py\n```\n"
        "- Đầu vào: `data/processed/external_{pci_63_full,gso_population_63_full,"
        "gso_grdp_63,odm_health_63,worldbank_vnm}.csv` + "
        "`results/predict_all_years.csv`.\n"
        "- Đầu ra: `results/external_validation.md` (file này), "
        "`results/external_validation.csv`, 4 hình trong `results/figs/external_*`.\n"
        "- Provenance nguồn: `data/processed/external_provenance.md`, "
        "`data/raw/*/PROVENANCE.md`."
    )
    (RES / "external_validation.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Đã ghi {RES / 'external_validation.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
