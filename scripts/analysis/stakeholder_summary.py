"""Thống kê bàn giao cho khách hàng từ kết quả phân cụm STING trên 63 tỉnh PAPI.

Script KHÔNG thay đổi hay refit bất kỳ model / nhãn STING đã công bố nào
(predict_all_years.csv, papi_observed_grid_2024.csv, papi_forecast_provinces_2024.csv).
Nhiệm vụ của module là biến đầu ra kỹ thuật (cụm -1, 0, 1, 2 và ô lưới) thành
4 nhóm hành động vận hành và bộ chỉ tiêu bàn giao cho cơ quan quản lý / khách hàng:

  1. Bảng phân nhóm hành động đầy đủ 63 tỉnh năm 2024:
     - Vùng lõi ổn định (Cụm 2, kèm nhận diện 5 tỉnh chuẩn 14/14 năm & nhóm rìa dưới 6.1)
     - Biên bứt phá vượt chuẩn (ô thưa phía trên/phải: vượt chuẩn kép hoặc dẫn đầu 4.2)
     - Ưu tiên cải thiện Y tế công lập 6.1 (ô thưa dưới ngưỡng Q25 − 0.5×IQR của Cụm 2)
     - Thiếu dữ liệu kiểm toán 2024 (chỉ định thu thập bổ sung)
  2. Quỹ đạo dài hạn 2011–2024 & phân tách hướng dịch chuyển 2023 → 2024.
  3. Danh sách xếp hạng kịch bản ngoài vùng trong hồi kiểm 2023→2024
  4. Hồ sơ đối chiếu kinh tế–xã hội độc lập theo nhóm hành động (GRDP/người 2024,
     tỷ lệ nghèo GSO 2024, PCI mới nhất 2022, dân số GSO 2024) — chỉ mô tả tương quan.

Đầu ra:
  - results/stakeholder_province_summary_2024.csv (63 dòng = 63 tỉnh)
  - results/stakeholder_summary.md
  - results/figs/stakeholder_quadrants_2024.png

Chạy từ thư mục gốc repo:
    python -E scripts/analysis/stakeholder_summary.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.gridspec as gridspec  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.common.fig_style import (  # noqa: E402
    PALETTE,
    add_source,
    save_png,
    style_context,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


OBSERVED_2024_CSV = ROOT / "results" / "papi_observed_grid_2024.csv"
ALL_YEARS_CSV = ROOT / "results" / "predict_all_years.csv"
FORECAST_2024_CSV = ROOT / "results" / "papi_forecast_provinces_2024.csv"
PCI_CSV = ROOT / "data" / "processed" / "external_pci_63_full.csv"
GRDP_CSV = ROOT / "data" / "processed" / "external_gso_grdp_63.csv"
POVERTY_CSV = ROOT / "data" / "processed" / "external_poverty_63.csv"
POP_CSV = ROOT / "data" / "processed" / "external_gso_population_63_full.csv"

OUT_CSV = ROOT / "results" / "stakeholder_province_summary_2024.csv"
OUT_MD = ROOT / "results" / "stakeholder_summary.md"
OUT_FIG = ROOT / "results" / "figs" / "stakeholder_quadrants_2024.png"

ACTION_GROUP_ORDER = [
    "Biên bứt phá vượt chuẩn",
    "Vùng lõi ổn định (Cụm 2)",
    "Ưu tiên cải thiện Y tế 6.1",
    "Ngoại vi biến động khác",
    "Thiếu dữ liệu 2024",
]

ACTION_GROUP_COLORS = {
    "Biên bứt phá vượt chuẩn": PALETTE["blue"],
    "Vùng lõi ổn định (Cụm 2)": PALETTE["green"],
    "Ưu tiên cải thiện Y tế 6.1": "#D55E00",
    "Ngoại vi biến động khác": PALETTE["purple"],
    "Thiếu dữ liệu 2024": PALETTE["gray"],
}


def compute_core_benchmarks(observed_2024: pd.DataFrame) -> dict[str, float]:
    """Tính các mốc phân vị thực nghiệm của Cụm 2 năm 2024 (không hardcode)."""
    core = observed_2024.loc[observed_2024["grid_status"].eq("in_cluster")]
    if core.empty:
        raise ValueError("Không tìm thấy quan sát in_cluster trong năm 2024.")
    med_42 = float(core["sd_4_2"].median())
    med_61 = float(core["sd_6_1"].median())
    q25_42 = float(core["sd_4_2"].quantile(0.25))
    q75_42 = float(core["sd_4_2"].quantile(0.75))
    q25_61 = float(core["sd_6_1"].quantile(0.25))
    q75_61 = float(core["sd_6_1"].quantile(0.75))
    iqr_61 = q75_61 - q25_61
    lower_61_fence = q25_61 - 0.5 * iqr_61
    return {
        "n_core": int(len(core)),
        "med_42": med_42,
        "med_61": med_61,
        "q25_42": q25_42,
        "q75_42": q75_42,
        "q25_61": q25_61,
        "q75_61": q75_61,
        "iqr_61": iqr_61,
        "lower_61_fence": lower_61_fence,
    }


def _classify_row(row: pd.Series, bench: dict[str, float]) -> tuple[str, str, str]:
    status = str(row["grid_status"])
    sd42 = row["sd_4_2"]
    sd61 = row["sd_6_1"]
    years_scored = int(row["years_scored_2011_2024"])
    years_c2 = int(row["years_cluster2_2011_2024"])
    med_42 = bench["med_42"]
    med_61 = bench["med_61"]
    fence_61 = bench["lower_61_fence"]

    if status == "missing_score" or pd.isna(sd42) or pd.isna(sd61):
        return (
            "Thiếu dữ liệu 2024",
            "Thiếu chỉ tiêu 4.2 hoặc 6.1",
            "Kiểm tra lại mẫu khảo sát PAPI 2024 và thu thập bổ sung trước khi xếp nhóm.",
        )

    if status == "in_cluster":
        if years_scored == 14 and years_c2 == 14:
            return (
                "Vùng lõi ổn định (Cụm 2)",
                "Chuẩn tham chiếu 14/14 năm",
                "Duy trì ổn định dài hạn và dùng làm điểm chuẩn đối sánh (benchmark).",
            )
        if float(sd61) < fence_61:
            return (
                "Vùng lõi ổn định (Cụm 2)",
                "Trong cụm nhưng rìa dưới Y tế 6.1",
                "Theo dõi sát y tế công lập 6.1 vì điểm nằm dưới ngưỡng phân vị lõi dù vẫn ở ô dày.",
            )
        return (
            "Vùng lõi ổn định (Cụm 2)",
            "Lõi ổn định chuẩn",
            "Duy trì cân bằng giữa kiểm soát tham nhũng (4.2) và y tế công lập (6.1).",
        )

    if float(sd61) < fence_61:
        if float(sd42) >= med_42:
            return (
                "Ưu tiên cải thiện Y tế 6.1",
                "Lệch pha: 4.2 đạt/vượt chuẩn, 6.1 tụt sâu",
                "Rà soát các thành phần của chỉ tiêu y tế công lập 6.1 và xác minh bằng dữ liệu địa phương.",
            )
        return (
            "Ưu tiên cải thiện Y tế 6.1",
            "Thấp hơn lõi trên cả 2 trục (đặc biệt 6.1)",
            "Ưu tiên rà soát toàn diện chất lượng y tế công lập 6.1 và kiểm soát tham nhũng 4.2.",
        )

    if float(sd42) >= med_42:
        if float(sd61) >= med_61:
            return (
                "Biên bứt phá vượt chuẩn",
                "Vượt trội kép (4.2 & 6.1 > trung vị lõi)",
                "Khảo sát điển hình quản trị tốt trên cả hai trục để chia sẻ kinh nghiệm liên tỉnh.",
            )
        return (
            "Biên bứt phá vượt chuẩn",
            "Dẫn đầu trục 4.2 (6.1 quanh vùng cụm)",
            "Nhân rộng thực hành tốt về kiểm soát tham nhũng trong dịch vụ công 4.2 và giữ ổn định y tế 6.1.",
        )

    return (
        "Ngoại vi biến động khác",
        "Ô thưa ngoài lõi khác",
        "Theo dõi thêm biến động hai trục qua các kỳ khảo sát tiếp theo.",
    )


def _transition_2023_2024_label(c2023: float, c2024: float, action_group: str) -> str:
    if pd.isna(c2023) and pd.isna(c2024):
        return "Thiếu dữ liệu cả 2 năm"
    if pd.isna(c2023):
        return "Thiếu dữ liệu 2023"
    if pd.isna(c2024):
        return "Thiếu dữ liệu 2024"
    c23, c24 = int(c2023), int(c2024)
    if c23 == 2 and c24 == 2:
        return "Giữ vững Cụm 2"
    if c23 == -1 and c24 == -1:
        return "Duy trì ngoài lõi (−1)"
    if c23 != 2 and c24 == 2:
        return "Vào Cụm 2 từ ngoài lõi"
    if c23 == 2 and c24 == -1:
        if action_group == "Biên bứt phá vượt chuẩn":
            return "Rời Cụm 2 lên biên bứt phá"
        if action_group == "Ưu tiên cải thiện Y tế 6.1":
            return "Rời Cụm 2 xuống rìa Y tế 6.1"
        return "Rời Cụm 2 sang ô thưa khác"
    return f"Chuyển {c23} → {c24}"


def build_stakeholder_tables(root: Path = ROOT) -> dict[str, object]:
    """Tổng hợp đầy đủ 63 tỉnh và các bảng thống kê bàn giao từ artifact gốc."""
    obs = pd.read_csv(root / "results" / "papi_observed_grid_2024.csv")
    all_years = pd.read_csv(root / "results" / "predict_all_years.csv")
    forecast = pd.read_csv(root / "results" / "papi_forecast_provinces_2024.csv")
    pci = pd.read_csv(root / "data" / "processed" / "external_pci_63_full.csv")
    grdp = pd.read_csv(root / "data" / "processed" / "external_gso_grdp_63.csv")
    poverty = pd.read_csv(root / "data" / "processed" / "external_poverty_63.csv")
    pop = pd.read_csv(root / "data" / "processed" / "external_gso_population_63_full.csv")

    if len(obs) != 63:
        raise ValueError(f"Expected 63 provinces in 2024 observed file, got {len(obs)}.")

    bench = compute_core_benchmarks(obs)

    # Lịch sử STING 14 năm (2011–2024) trên lưới tham chiếu cố định
    hist = (
        all_years.groupby("province_code", as_index=False)
        .agg(
            years_scored_2011_2024=("pred_cluster", lambda s: int(s.notna().sum())),
            years_cluster2_2011_2024=("pred_cluster", lambda s: int((s == 2).sum())),
            years_noise_2011_2024=("pred_cluster", lambda s: int((s == -1).sum())),
            years_small_cluster_2011_2024=(
                "pred_cluster",
                lambda s: int(s.isin([0, 1]).sum()),
            ),
        )
    )
    y2023 = (
        all_years.loc[
            all_years["year"].eq(2023),
            ["province_code", "pred_cluster", "sd_4_2", "sd_6_1"],
        ]
        .rename(
            columns={
                "pred_cluster": "cluster_2023",
                "sd_4_2": "sd_4_2_2023",
                "sd_6_1": "sd_6_1_2023",
            }
        )
    )

    fc = forecast[
        [
            "province_code",
            "forecast_sd_4_2",
            "forecast_sd_6_1",
            "forecast_cluster",
            "outside_scenario_share",
        ]
    ].rename(
        columns={
            "forecast_sd_4_2": "ridge_pred_4_2",
            "forecast_sd_6_1": "ridge_pred_6_1",
            "outside_scenario_share": "risk_outside_scenario_share",
        }
    )

    pci_2022 = (
        pci.loc[pci["year"].eq(2022), ["papi_province_code", "pci_weighted_score"]]
        .rename(columns={"papi_province_code": "province_code", "pci_weighted_score": "pci_2022"})
    )
    grdp_2024 = (
        grdp.loc[grdp["year"].eq(2024), ["papi_province_code", "grdp_per_capita_million_vnd"]]
        .rename(
            columns={
                "papi_province_code": "province_code",
                "grdp_per_capita_million_vnd": "grdp_2024_mil_vnd",
            }
        )
    )
    pov_2024 = (
        poverty.loc[poverty["year"].eq(2024), ["papi_province_code", "poverty_rate_pct"]]
        .rename(columns={"papi_province_code": "province_code", "poverty_rate_pct": "poverty_2024_pct"})
    )
    pop_2024 = (
        pop.loc[pop["year"].eq(2024), ["papi_province_code", "gso_pop_total_thousand"]]
        .rename(columns={"papi_province_code": "province_code", "gso_pop_total_thousand": "pop_2024_thousand"})
    )

    summary = (
        obs.merge(hist, on="province_code", how="left")
        .merge(y2023, on="province_code", how="left")
        .merge(fc, on="province_code", how="left")
        .merge(pci_2022, on="province_code", how="left")
        .merge(grdp_2024, on="province_code", how="left")
        .merge(pov_2024, on="province_code", how="left")
        .merge(pop_2024, on="province_code", how="left")
    )

    classified = summary.apply(lambda r: _classify_row(r, bench), axis=1, result_type="expand")
    classified.columns = ["action_group", "action_subtier", "client_recommendation"]
    summary = pd.concat([summary, classified], axis=1)

    summary["delta_vs_core_med_4_2"] = summary["sd_4_2"] - bench["med_42"]
    summary["delta_vs_core_med_6_1"] = summary["sd_6_1"] - bench["med_61"]
    summary["transition_2023_2024"] = summary.apply(
        lambda r: _transition_2023_2024_label(
            r["cluster_2023"], r["cluster"], str(r["action_group"])
        ),
        axis=1,
    )

    order_map = {name: idx for idx, name in enumerate(ACTION_GROUP_ORDER)}
    summary["_group_rank"] = summary["action_group"].map(order_map).fillna(99)
    summary = (
        summary.sort_values(
            ["_group_rank", "sd_6_1", "sd_4_2", "province_code"],
            ascending=[True, True, False, True],
            na_position="last",
        )
        .drop(columns=["_group_rank"])
        .reset_index(drop=True)
    )

    group_rows = []
    for grp in ACTION_GROUP_ORDER:
        sub = summary.loc[summary["action_group"].eq(grp)]
        if sub.empty:
            continue
        group_rows.append(
            {
                "action_group": grp,
                "n_provinces": int(len(sub)),
                "share_63_pct": round(100.0 * len(sub) / len(summary), 1),
                "median_sd_4_2": float("nan") if sub["sd_4_2"].dropna().empty else round(float(sub["sd_4_2"].median()), 4),
                "median_sd_6_1": float("nan") if sub["sd_6_1"].dropna().empty else round(float(sub["sd_6_1"].median()), 4),
                "median_years_c2": round(float(sub["years_cluster2_2011_2024"].median()), 1),
                "median_risk_outside_pct": (
                    float("nan")
                    if sub["risk_outside_scenario_share"].dropna().empty
                    else round(100.0 * float(sub["risk_outside_scenario_share"].median()), 1)
                ),
                "median_grdp_2024_mil": (
                    float("nan")
                    if sub["grdp_2024_mil_vnd"].dropna().empty
                    else round(float(sub["grdp_2024_mil_vnd"].median()), 2)
                ),
                "median_pci_2022": (
                    float("nan")
                    if sub["pci_2022"].dropna().empty
                    else round(float(sub["pci_2022"].median()), 2)
                ),
                "median_poverty_2024_pct": (
                    float("nan")
                    if sub["poverty_2024_pct"].dropna().empty
                    else round(float(sub["poverty_2024_pct"].median()), 2)
                ),
                "provinces": ", ".join(sub["province_vi"].tolist()),
            }
        )
    group_stats = pd.DataFrame(group_rows)

    transitions = (
        summary["transition_2023_2024"]
        .value_counts()
        .rename_axis("transition_2023_2024")
        .reset_index(name="n_provinces")
    )

    benchmarks_14y = summary.loc[
        summary["years_scored_2011_2024"].eq(14) & summary["years_cluster2_2011_2024"].eq(14),
        ["province_code", "province_vi", "sd_4_2", "sd_6_1", "grdp_2024_mil_vnd", "pci_2022"],
    ].sort_values("province_code")

    watchlist = (
        summary.loc[summary["risk_outside_scenario_share"].notna()]
        .sort_values(["risk_outside_scenario_share", "province_code"], ascending=[False, True])
        .head(10)[
            [
                "province_code",
                "province_vi",
                "action_group",
                "sd_4_2",
                "sd_6_1",
                "risk_outside_scenario_share",
            ]
        ]
        .reset_index(drop=True)
    )

    return {
        "summary": summary,
        "group_stats": group_stats,
        "bench": bench,
        "transitions": transitions,
        "benchmarks_14y": benchmarks_14y,
        "watchlist": watchlist,
    }


def make_stakeholder_figure(data: dict[str, object], out_path: Path = OUT_FIG) -> None:
    """Vẽ hình 2 panel: Phân nhóm hành động 63 tỉnh 2024 & So sánh KPI giữa 3 nhóm có điểm."""
    summary: pd.DataFrame = data["summary"]  # type: ignore[assignment]
    group_stats: pd.DataFrame = data["group_stats"]  # type: ignore[assignment]
    bench: dict[str, float] = data["bench"]  # type: ignore[assignment]

    scored = summary.loc[summary["grid_status"].ne("missing_score")].copy()
    core = scored.loc[scored["action_group"].eq("Vùng lõi ổn định (Cụm 2)")]
    bench_14 = scored.loc[scored["action_subtier"].eq("Chuẩn tham chiếu 14/14 năm")]
    frontier = scored.loc[scored["action_group"].eq("Biên bứt phá vượt chuẩn")]
    priority = scored.loc[scored["action_group"].eq("Ưu tiên cải thiện Y tế 6.1")]
    missing = summary.loc[summary["action_group"].eq("Thiếu dữ liệu 2024")]

    # Vị trí nhãn theo tọa độ dữ liệu để đảm bảo tách biệt hoàn toàn giữa các điểm và đường ngưỡng
    frontier_positions = {
        "Hà Tĩnh": (2.066, 2.191, "left"),
        "Bình Thuận": (2.234, 2.113, "left"),
        "Sóc Trăng": (2.268, 2.050, "left"),
        "Bà Rịa - Vũng Tàu": (2.274, 2.002, "left"),
        "Tây Ninh": (2.299, 1.944, "left"),
        "Quảng Ninh": (2.275, 1.896, "left"),
        "Cà Mau": (2.192, 1.902, "left"),
        "An Giang": (2.092, 1.894, "left"),
    }
    priority_positions = {
        "Hà Nội": (1.917, 1.686, "right"),
        "Cần Thơ": (2.038, 1.696, "left"),
        "Gia Lai": (2.064, 1.766, "left"),
        "Long An": (2.088, 1.825, "left"),
        "Bình Dương": (2.191, 1.808, "left"),
    }

    with style_context():
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(12.2, 5.5))
        gs = gridspec.GridSpec(2, 2, width_ratios=[1.48, 1.0], height_ratios=[1.0, 1.0], hspace=0.44, wspace=0.28)
        ax_left = fig.add_subplot(gs[:, 0])
        ax_top = fig.add_subplot(gs[0, 1])
        ax_bot = fig.add_subplot(gs[1, 1])

        # Nền vùng phân rã hành động phía sau (dưới ngưỡng 6.1 là vùng ưu tiên y tế)
        ax_left.axhspan(1.635, bench["lower_61_fence"], color="#FFF5EE", alpha=0.65, zorder=0)
        ax_left.axvspan(bench["med_42"], 2.40, ymin=(bench["lower_61_fence"] - 1.635) / (2.265 - 1.635),
                        color="#F0F7FC", alpha=0.45, zorder=0)
        ax_left.axvline(bench["med_42"], color=PALETTE["green"], linestyle="--", linewidth=1.0, alpha=0.75, zorder=1)
        ax_left.axhline(bench["med_61"], color=PALETTE["green"], linestyle="--", linewidth=1.0, alpha=0.75, zorder=1)
        ax_left.axhline(bench["lower_61_fence"], color="#D55E00", linestyle=":", linewidth=1.35, alpha=0.9, zorder=2)

        ax_left.scatter(
            core["sd_4_2"],
            core["sd_6_1"],
            s=46,
            color=ACTION_GROUP_COLORS["Vùng lõi ổn định (Cụm 2)"],
            alpha=0.72,
            edgecolors="white",
            linewidths=0.6,
            label=f"Vùng lõi ổn định — Cụm 2 (n = {len(core)})",
            zorder=3,
        )
        ax_left.scatter(
            bench_14["sd_4_2"],
            bench_14["sd_6_1"],
            s=95,
            facecolors="none",
            edgecolors="#004D38",
            linewidths=1.6,
            marker="o",
            label=f"Chuẩn 14/14 năm trong Cụm 2 (n = {len(bench_14)})",
            zorder=4,
        )
        ax_left.scatter(
            frontier["sd_4_2"],
            frontier["sd_6_1"],
            s=80,
            color=ACTION_GROUP_COLORS["Biên bứt phá vượt chuẩn"],
            marker="D",
            edgecolors="white",
            linewidths=0.8,
            label=f"Biên bứt phá vượt chuẩn (n = {len(frontier)})",
            zorder=5,
        )
        ax_left.scatter(
            priority["sd_4_2"],
            priority["sd_6_1"],
            s=84,
            color=ACTION_GROUP_COLORS["Ưu tiên cải thiện Y tế 6.1"],
            marker="s",
            edgecolors="white",
            linewidths=0.8,
            label=f"Ưu tiên cải thiện Y tế 6.1 (n = {len(priority)})",
            zorder=5,
        )

        for _, r in frontier.iterrows():
            name = str(r["province_vi"])
            tx, ty, ha = frontier_positions.get(name, (float(r["sd_4_2"]) + 0.014, float(r["sd_6_1"]), "left"))
            short_name = "BR-VT" if name == "Bà Rịa - Vũng Tàu" else name
            ax_left.annotate(
                short_name,
                (float(r["sd_4_2"]), float(r["sd_6_1"])),
                xytext=(tx, ty),
                textcoords="data",
                ha=ha,
                va="center",
                fontsize=7.6,
                fontweight="semibold",
                color="#004C78",
                arrowprops={"arrowstyle": "-", "color": "#88B5D3", "lw": 0.65, "shrinkA": 2, "shrinkB": 3},
                zorder=6,
            )

        for _, r in priority.iterrows():
            name = str(r["province_vi"])
            tx, ty, ha = priority_positions.get(name, (float(r["sd_4_2"]) + 0.014, float(r["sd_6_1"]), "left"))
            ax_left.annotate(
                f"{name} ({r['sd_6_1']:.2f})",
                (float(r["sd_4_2"]), float(r["sd_6_1"])),
                xytext=(tx, ty),
                textcoords="data",
                ha=ha,
                va="center",
                fontsize=7.6,
                fontweight="semibold",
                color="#9A3F00",
                arrowprops={"arrowstyle": "-", "color": "#E2A37C", "lw": 0.65, "shrinkA": 2, "shrinkB": 3},
                zorder=6,
            )

        ax_left.text(
            1.792,
            bench["med_61"] + 0.010,
            f"Trung vị 6.1 lõi = {bench['med_61']:.3f}",
            fontsize=7.2,
            color="#005A40",
        )
        ax_left.text(
            bench["med_42"] + 0.008,
            1.728,
            f"Trung vị 4.2 lõi = {bench['med_42']:.3f}",
            fontsize=7.2,
            color="#005A40",
        )
        ax_left.text(
            1.792,
            bench["lower_61_fence"] - 0.012,
            f"Ngưỡng dưới 6.1 (Q25−0,5×IQR) = {bench['lower_61_fence']:.3f}",
            va="top",
            fontsize=7.2,
            color="#9A3F00",
        )
        missing_names = ", ".join(missing["province_vi"].tolist())
        ax_left.text(
            0.985,
            0.03,
            f"Thiếu dữ liệu 2024 (n = {len(missing)}): {missing_names}",
            transform=ax_left.transAxes,
            ha="right",
            fontsize=7.4,
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "#F4F5F6", "edgecolor": "#CCCCCC"},
        )

        ax_left.set_xlim(1.78, 2.40)
        ax_left.set_ylim(1.635, 2.265)
        ax_left.set_title("(a) Phân nhóm hành động 63 tỉnh năm 2024 (tách vùng −1)", fontsize=10.5, fontweight="bold")
        ax_left.set_xlabel("4.2 Kiểm soát tham nhũng dịch vụ công (2024)")
        ax_left.set_ylabel("6.1 Y tế công lập (2024)")
        ax_left.legend(loc="upper left", fontsize=6.7, frameon=True, framealpha=0.94, borderpad=0.3)

        # Panel (b1): Trung vị hai trục PAPI 2024 giữa 3 nhóm có điểm
        scored_groups = group_stats.loc[group_stats["action_group"].isin([
            "Biên bứt phá vượt chuẩn",
            "Vùng lõi ổn định (Cụm 2)",
            "Ưu tiên cải thiện Y tế 6.1",
        ])].copy()
        short_names = {
            "Biên bứt phá vượt chuẩn": "Biên bứt phá",
            "Vùng lõi ổn định (Cụm 2)": "Vùng lõi Cụm 2",
            "Ưu tiên cải thiện Y tế 6.1": "Ưu tiên Y tế 6.1",
        }
        x_tick_labels = [
            f"{short_names[g]}\n(n={int(n)})"
            for g, n in zip(scored_groups["action_group"], scored_groups["n_provinces"], strict=True)
        ]
        y_tick_labels = [lbl.replace("\n", " ") for lbl in x_tick_labels]
        x = np.arange(len(scored_groups))
        w = 0.34
        vals_42 = scored_groups["median_sd_4_2"].astype(float).to_numpy()
        vals_61 = scored_groups["median_sd_6_1"].astype(float).to_numpy()
        b1 = ax_top.bar(x - w / 2, vals_42, width=w, color=PALETTE["sky"], label="Trung vị 4.2")
        b2 = ax_top.bar(x + w / 2, vals_61, width=w, color=PALETTE["orange"], label="Trung vị 6.1")
        for bar in (*b1, *b2):
            h = float(bar.get_height())
            ax_top.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.012,
                f"{h:.2f}",
                ha="center",
                va="bottom",
                fontsize=7.8,
            )
        ax_top.set_xticks(x)
        ax_top.set_xticklabels(x_tick_labels, fontsize=8.0)
        ax_top.set_ylim(1.55, 2.38)
        ax_top.set_ylabel("Điểm PAPI")
        ax_top.set_title("(b) Trung vị 2 trục PAPI 2024 theo nhóm", fontsize=10.2, fontweight="bold")
        ax_top.legend(loc="upper right", fontsize=7.6, frameon=False, ncol=2)

        # Panel (b2): GRDP/người 2024 Sơ bộ — minh họa nghịch lý đô thị–công nghiệp
        grdp_vals = scored_groups["median_grdp_2024_mil"].astype(float).to_numpy()
        colors = [ACTION_GROUP_COLORS[g] for g in scored_groups["action_group"]]
        y_pos = np.arange(len(scored_groups))
        hb = ax_bot.barh(y_pos, grdp_vals, height=0.56, color=colors, alpha=0.88)
        for bar in hb:
            w_val = float(bar.get_width())
            ax_bot.text(w_val + 2.2, bar.get_y() + bar.get_height() / 2, f"{w_val:.1f}", va="center", fontsize=8.0)
        ax_bot.set_yticks(y_pos)
        ax_bot.set_yticklabels(y_tick_labels, fontsize=7.9)
        ax_bot.invert_yaxis()
        ax_bot.set_xlim(0, max(grdp_vals) * 1.24)
        ax_bot.set_xlabel("Triệu đồng / người (GSO 2024 Sơ bộ)")
        ax_bot.set_title("(c) Trung vị GRDP/người 2024 theo nhóm", fontsize=10.2, fontweight="bold")

        fig.suptitle(
            "Thống kê bàn giao cho khách hàng từ phân cụm STING trên 63 tỉnh (năm 2024)",
            fontsize=11.8,
            fontweight="bold",
            y=0.985,
        )
        add_source(fig, "PAPI 2024 & GSO PX-Web 2024 — tổng hợp từ nhãn STING cố định (2011–2023)", retrieved="2026-11-03")
        fig.subplots_adjust(left=0.065, right=0.975, top=0.87, bottom=0.12)
        save_png(fig, out_path, dpi=200)
        plt.close(fig)


def write_stakeholder_markdown(data: dict[str, object], out_path: Path = OUT_MD) -> None:
    summary: pd.DataFrame = data["summary"]  # type: ignore[assignment]
    group_stats: pd.DataFrame = data["group_stats"]  # type: ignore[assignment]
    bench: dict[str, float] = data["bench"]  # type: ignore[assignment]
    transitions: pd.DataFrame = data["transitions"]  # type: ignore[assignment]
    benchmarks_14y: pd.DataFrame = data["benchmarks_14y"]  # type: ignore[assignment]
    watchlist: pd.DataFrame = data["watchlist"]  # type: ignore[assignment]

    lines: list[str] = [
        "# Thống kê bàn giao cho khách hàng từ kết quả phân cụm STING (63 tỉnh PAPI)",
        "",
        "Tài liệu này trả lời trực tiếp câu hỏi nghiệp vụ: **sau khi chạy phân cụm STING ra các nhãn kỹ thuật "
        "(`-1, 0, 1, 2`) và chỉ số ô lưới `(i, j)`, cuối cùng thống kê được gì để bàn giao cho khách hàng "
        "(cơ quan quản lý địa phương / đơn vị tư vấn cải cách hành chính công)?**",
        "",
        "Mọi số liệu dưới đây được tính tất định từ bộ nhãn đóng băng "
        "(`results/papi_observed_grid_2024.csv`, `results/predict_all_years.csv`, `results/papi_forecast_provinces_2024.csv`) "
        "và dữ liệu độc lập (`PCI 2022`, `GRDP/người 2024`, `Nghèo GSO 2024`).",
        "",
        "## 1. Phân loại hành động 63 tỉnh năm 2024 (không gộp chung nhãn nhiễu `-1`)",
        "",
        f"- **Mốc chuẩn thực nghiệm từ Cụm 2 (`n = {bench['n_core']}` tỉnh trong vùng dày năm 2024):** "
        f"trung vị **4.2 = {bench['med_42']:.4f}** (IQR {bench['q25_42']:.4f}–{bench['q75_42']:.4f}); "
        f"trung vị **6.1 = {bench['med_61']:.4f}** (IQR {bench['q25_61']:.4f}–{bench['q75_61']:.4f}).",
        f"- **Ngưỡng tách hai cực bên trong 13 tỉnh ô thưa (`-1`):** `sd_6_1 < Q25 − 0.5 × IQR = {bench['lower_61_fence']:.4f}` "
        "phân tách rạch ròi 5 tỉnh tụt sâu về y tế công lập (thực tế đều `≤ 1.808`) khỏi 8 tỉnh biên tăng trưởng vượt chuẩn (`4.2 > trung vị lõi`, `6.1 ≥ 1.888`).",
        "",
        "| Nhóm hành động bàn giao | Số tỉnh | Tỉ lệ /63 | Trung vị 4.2 | Trung vị 6.1 | Trung vị số năm Cụm 2 | Trung vị kịch bản ngoài vùng 2024 (%) | Trung vị GRDP 2024 (tr.đ) | Trung vị PCI 2022 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in group_stats.iterrows():
        m42 = "—" if pd.isna(r["median_sd_4_2"]) else f"{r['median_sd_4_2']:.3f}"
        m61 = "—" if pd.isna(r["median_sd_6_1"]) else f"{r['median_sd_6_1']:.3f}"
        rsk = "—" if pd.isna(r["median_risk_outside_pct"]) else f"{r['median_risk_outside_pct']:.1f}%"
        grd = "—" if pd.isna(r["median_grdp_2024_mil"]) else f"{r['median_grdp_2024_mil']:.2f}"
        pci = "—" if pd.isna(r["median_pci_2022"]) else f"{r['median_pci_2022']:.2f}"
        lines.append(
            f"| **{r['action_group']}** | {int(r['n_provinces'])} | {r['share_63_pct']:.1f}% | "
            f"{m42} | {m61} | {r['median_years_c2']:.1f} | {rsk} | {grd} | {pci} |"
        )

    lines.extend(["", "### Danh sách chi tiết từng nhóm ngoài vùng lõi và nhóm chuẩn", ""])
    for grp in ("Biên bứt phá vượt chuẩn", "Ưu tiên cải thiện Y tế 6.1", "Thiếu dữ liệu 2024"):
        sub = summary.loc[summary["action_group"].eq(grp)]
        if sub.empty:
            continue
        lines.append(f"#### {grp} (`n = {len(sub)}`)")
        lines.append("")
        lines.append("| Tỉnh | 4.2 | 6.1 | Ô lưới 2024 | Phân tầng cụ thể | Khuyến nghị hành động |")
        lines.append("|---|---:|---:|:---:|---|---|")
        for _, r in sub.iterrows():
            s42 = "—" if pd.isna(r["sd_4_2"]) else f"{r['sd_4_2']:.3f}"
            s61 = "—" if pd.isna(r["sd_6_1"]) else f"{r['sd_6_1']:.3f}"
            cell = "—" if pd.isna(r["grid_cell"]) or not str(r["grid_cell"]).strip() else str(r["grid_cell"])
            lines.append(
                f"| {r['province_vi']} | {s42} | {s61} | `{cell}` | {r['action_subtier']} | {r['client_recommendation']} |"
            )
        lines.append("")

    core_sub = summary.loc[summary["action_group"].eq("Vùng lõi ổn định (Cụm 2)")]
    core_edge = core_sub.loc[core_sub["action_subtier"].eq("Trong cụm nhưng rìa dưới Y tế 6.1")]
    lines.extend([
        f"#### 5 tỉnh chuẩn tham chiếu bền vững 14/14 năm trong Cụm 2 (`n = {len(benchmarks_14y)}`)",
        "",
        ", ".join(
            f"**{r['province_vi']}** (`4.2={r['sd_4_2']:.3f}`, `6.1={r['sd_6_1']:.3f}`)"
            for _, r in benchmarks_14y.iterrows()
        )
        + ".",
        "",
        f"#### Nhóm rìa dưới ngay trong Cụm 2 cần giữ nhịp Y tế 6.1 (`sd_6_1 < {bench['lower_61_fence']:.3f}`, `n = {len(core_edge)}`)",
        "",
        ", ".join(
            f"**{r['province_vi']}** (`4.2={r['sd_4_2']:.3f}`, `6.1={r['sd_6_1']:.3f}`, ô `{r['grid_cell']}`)"
            for _, r in core_edge.iterrows()
        )
        + ".",
        "",
        "## 2. Dịch chuyển trạng thái 2023 → 2024 (tách rõ hướng rời cụm)",
        "",
        "| Xu hướng dịch chuyển 2023 → 2024 | Số tỉnh | Danh sách tỉnh |",
        "|---|---:|---|",
    ])
    for _, tr in transitions.iterrows():
        label = str(tr["transition_2023_2024"])
        provs = ", ".join(
            summary.loc[summary["transition_2023_2024"].eq(label), "province_vi"].tolist()
        )
        lines.append(f"| {label} | {int(tr['n_provinces'])} | {provs} |")

    lines.extend([
        "",
        "## 3. Kịch bản ngoài vùng năm 2024 (Top 10 `outside_scenario_share`)",
        "",
        "Trong hồi kiểm 2023→2024, dự báo điểm phát hiện 0/11 tỉnh ngoài vùng dày trên 59 tỉnh đối chiếu được. Tỉ lệ kịch bản dùng phần dư lịch sử để xếp hạng rủi ro biến động (AUC thăm dò = `0.816` trên năm 2024). Đây không phải xác suất đã hiệu chỉnh hay dự báo cho năm sau 2024.",
        "",
        "| Hạng | Tỉnh | Nhóm 2024 | 4.2 | 6.1 | Tỉ lệ kịch bản ngoài vùng (%) |",
        "|---:|---|---|---:|---:|---:|",
    ])
    for rank, (_, r) in enumerate(watchlist.iterrows(), start=1):
        lines.append(
            f"| {rank} | {r['province_vi']} | {r['action_group']} | {r['sd_4_2']:.3f} | {r['sd_6_1']:.3f} | {100.0 * r['risk_outside_scenario_share']:.1f}% |"
        )

    lines.extend([
        "",
        "## 4. Ý nghĩa kinh tế–xã hội bàn giao cho khách hàng (chỉ mô tả, không suy nhân quả)",
        "",
        "- **Tách được hai câu chuyện trái ngược trong mã kỹ thuật `-1`:** 8 tỉnh vùng biên bứt phá đạt trung vị GRDP 2024 là "
        f"`{group_stats.loc[group_stats['action_group'].eq('Biên bứt phá vượt chuẩn'), 'median_grdp_2024_mil'].iloc[0]:.2f}` triệu/người và PAPI `4.2 = "
        f"{group_stats.loc[group_stats['action_group'].eq('Biên bứt phá vượt chuẩn'), 'median_sd_4_2'].iloc[0]:.3f}` (cao hơn hẳn vùng lõi), trong khi 5 tỉnh ưu tiên Y tế `6.1` có trung vị GRDP 2024 tới "
        f"`{group_stats.loc[group_stats['action_group'].eq('Ưu tiên cải thiện Y tế 6.1'), 'median_grdp_2024_mil'].iloc[0]:.2f}` triệu/người (cao hơn vùng lõi `"
        f"{group_stats.loc[group_stats['action_group'].eq('Vùng lõi ổn định (Cụm 2)'), 'median_grdp_2024_mil'].iloc[0]:.2f}` triệu/người) nhưng `6.1 = "
        f"{group_stats.loc[group_stats['action_group'].eq('Ưu tiên cải thiện Y tế 6.1'), 'median_sd_6_1'].iloc[0]:.3f}` — chênh lệch mô tả, không chứng minh quá tải hay quan hệ nhân quả.",
        "- Toàn bộ bảng chi tiết 63 tỉnh nằm tại `results/stakeholder_province_summary_2024.csv` và hình minh họa tại `results/figs/stakeholder_quadrants_2024.png`.",
        "",
    ])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def update_excel_workbook(
    summary: pd.DataFrame, xlsx_path: Path = ROOT / "results" / "KetQua_STING_PAPI.xlsx"
) -> None:
    """Cập nhật sheet 'Thống kê khách hàng 2024' và 'Mục lục' trong KetQua_STING_PAPI.xlsx."""
    from copy import copy

    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "Thống kê khách hàng 2024"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]

    ws = wb.create_sheet(title=sheet_name, index=1)
    ws.views.sheetView[0].showGridLines = False

    white_fill = PatternFill("solid", fgColor="FFFFFF")
    thin_side = Side(style="thin", color="BFBFBF")
    header_font = Font(name="Arial", size=10, bold=True, color="000000")
    body_font = Font(name="Arial", size=10, color="000000")

    col_specs = [
        ("province_code", "Mã tỉnh", 9.5, "0", "right"),
        ("province_vi", "Tỉnh / thành phố", 20.0, "General", "left"),
        ("action_group", "Nhóm hành động 2024", 26.0, "General", "left"),
        ("action_subtier", "Phân tầng chi tiết", 34.0, "General", "left"),
        ("sd_4_2", "Điểm 4.2 (2024)", 13.0, "0.000", "right"),
        ("sd_6_1", "Điểm 6.1 (2024)", 13.0, "0.000", "right"),
        ("grid_cell", "Ô lưới 2024", 12.0, "General", "center"),
        ("reference_count", "Điểm tham chiếu ô", 15.0, "#,##0", "right"),
        ("years_cluster2_2011_2024", "Số năm Cụm 2 (2011–2024)", 17.0, "#,##0", "right"),
        ("years_noise_2011_2024", "Số năm ngoài lõi", 15.0, "#,##0", "right"),
        ("transition_2023_2024", "Dịch chuyển 2023→2024", 27.0, "General", "left"),
        ("risk_outside_scenario_share", "Kịch bản ngoài vùng 2024", 19.0, "0.0%", "right"),
        ("grdp_2024_mil_vnd", "GRDP/người 2024 (tr.đ)", 17.0, "0.00", "right"),
        ("pci_2022", "PCI 2022", 11.0, "0.00", "right"),
        ("poverty_2024_pct", "Tỉ lệ nghèo 2024 (%)", 15.0, "0.0", "right"),
        ("client_recommendation", "Khuyến nghị bàn giao", 46.0, "General", "left"),
    ]
    last_col_letter = openpyxl.utils.get_column_letter(len(col_specs))

    ws["A2"] = "Thống kê bàn giao cho khách hàng — 63 tỉnh năm 2024"
    ws["A2"].font = Font(name="Arial", size=15, bold=True, color="000000")
    ws["A2"].fill = copy(white_fill)
    ws["A2"].alignment = Alignment(vertical="center", wrap_text=True)
    ws.merge_cells(f"A2:{last_col_letter}2")
    ws.row_dimensions[2].height = 24.0

    counts_map = summary["action_group"].value_counts().to_dict()
    ws["A3"] = (
        f"Phân nhóm hành động từ nhãn STING cố định ({counts_map.get('Vùng lõi ổn định (Cụm 2)', 0)} Vùng lõi ổn định, "
        f"{counts_map.get('Biên bứt phá vượt chuẩn', 0)} Biên bứt phá vượt chuẩn, "
        f"{counts_map.get('Ưu tiên cải thiện Y tế 6.1', 0)} Ưu tiên Y tế 6.1, "
        f"{counts_map.get('Thiếu dữ liệu 2024', 0)} Thiếu dữ liệu 2024), kèm dịch chuyển 2023→2024, kịch bản ngoài vùng năm 2024 và GRDP/PCI."
    )
    ws["A3"].font = Font(name="Arial", size=10, italic=True, color="000000")
    ws["A3"].fill = copy(white_fill)
    ws["A3"].alignment = Alignment(vertical="center", wrap_text=True)
    ws.merge_cells(f"A3:{last_col_letter}3")
    ws.row_dimensions[3].height = 21.75

    ws.row_dimensions[5].height = 32.25
    for col_idx, (_, title, width, _, _) in enumerate(col_specs, start=1):
        cell = ws.cell(5, col_idx, title)
        cell.font = copy(header_font)
        cell.fill = copy(white_fill)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(
            top=thin_side,
            bottom=thin_side,
            left=None if col_idx == 1 else thin_side,
            right=None if col_idx == len(col_specs) else thin_side,
        )
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    export_df = summary[[k for k, *_ in col_specs]]
    for row_offset, (_, row) in enumerate(export_df.iterrows(), start=6):
        rec_text = str(row["client_recommendation"] or "")
        ws.row_dimensions[row_offset].height = 28.5 if len(rec_text) > 46 else 18.0
        for col_idx, (key, _, _, num_fmt, h_align) in enumerate(col_specs, start=1):
            val = row[key]
            if pd.isna(val):
                val = None
            elif hasattr(val, "item"):
                val = val.item()
            cell = ws.cell(row_offset, col_idx, val)
            cell.font = copy(body_font)
            cell.fill = copy(white_fill)
            cell.number_format = num_fmt
            cell.alignment = Alignment(
                horizontal=h_align if h_align != "left" else None,
                vertical="center",
                wrap_text=(key == "client_recommendation"),
            )

    last_row = 5 + len(export_df)
    table = Table(displayName="PapiStakeholder2024", ref=f"A5:{last_col_letter}{last_row}")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleLight1",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=False,
        showColumnStripes=False,
    )
    ws.add_table(table)
    ws.freeze_panes = "A6"

    ws_toc = wb["Mục lục"]
    csv_col = 6
    target_row = None
    for r in range(6, ws_toc.max_row + 1):
        if ws_toc.cell(r, csv_col).value == "stakeholder_province_summary_2024.csv":
            target_row = r
            break
    if target_row is None:
        ws_toc.insert_rows(6)
        target_row = 6
    ws_toc.row_dimensions[target_row].height = 19.5
    ws_toc.cell(target_row, 1, "Bàn giao khách hàng")
    ws_toc.cell(target_row, 2, f"=HYPERLINK(\"#'{sheet_name}'!A2\",\"{sheet_name}\")")
    ws_toc.cell(target_row, 3, "Phân loại hành động & khuyến nghị 63 tỉnh năm 2024")
    ws_toc.cell(target_row, 4, len(export_df))
    ws_toc.cell(target_row, 5, len(col_specs))
    ws_toc.cell(target_row, 6, "stakeholder_province_summary_2024.csv")
    ref_toc_row = 7 if target_row == 6 else 6
    for c in range(1, 7):
        src_cell = ws_toc.cell(ref_toc_row, c)
        dst_cell = ws_toc.cell(target_row, c)
        dst_cell.font = copy(src_cell.font)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.alignment = copy(src_cell.alignment)
        dst_cell.number_format = src_cell.number_format

    n_tables = sum(
        1 for r in range(6, ws_toc.max_row + 1) if ws_toc.cell(r, csv_col).value
    )
    ws_toc["A3"] = f"{n_tables} bảng kết quả theo tệp nguồn. Mở Thống kê khách hàng 2024 hoặc Quan sát 2024 để xem kết quả chính."
    if "PapiDanhMuc" in ws_toc.tables:
        toc_ref = f"A5:F{5 + n_tables}"
        toc_table = ws_toc.tables["PapiDanhMuc"]
        toc_table.ref = toc_ref
        if toc_table.autoFilter is not None:
            toc_table.autoFilter.ref = toc_ref

    wb.save(xlsx_path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-excel", action="store_true", help="Cập nhật thêm trang Excel KetQua_STING_PAPI.xlsx")
    args = parser.parse_args(argv)

    data = build_stakeholder_tables(ROOT)
    summary: pd.DataFrame = data["summary"]  # type: ignore[assignment]
    summary.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    write_stakeholder_markdown(data, OUT_MD)
    make_stakeholder_figure(data, OUT_FIG)
    if args.with_excel:
        update_excel_workbook(summary)
        print("Updated: results\\KetQua_STING_PAPI.xlsx")
    print(f"Saved: {OUT_CSV.relative_to(ROOT)} ({len(summary)} rows)")
    print(f"Saved: {OUT_MD.relative_to(ROOT)}")
    print(f"Saved: {OUT_FIG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
