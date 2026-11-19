"""Sinh bảng và hình của thí nghiệm dự báo hai chỉ tiêu PAPI năm 2024."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.common.fig_style import PALETTE, style_context  # noqa: E402
from scripts.common.papi_forecast import (  # noqa: E402
    ORIGIN_YEAR, TARGETS, MODEL_NAMES, forecast_from_history, scenario_auc, score_forecast,
)
from scripts.common.papi_pred_common import load_config, load_panel  # noqa: E402

LABELS = ("4.2 Kiểm soát tham nhũng trong\ncung ứng dịch vụ công", "6.1 Y tế công lập")


def _value_figure(rows, metrics):
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.5), layout="constrained")
        for ax, target, title in zip(axes, TARGETS, LABELS, strict=True):
            values = rows[[f"{prefix}_{target}" for prefix in ("actual", "forecast", "carry")]]
            margin = float(values.max().max() - values.min().min()) * 0.06
            lo, hi = float(values.min().min()) - margin, float(values.max().max()) + margin
            ax.plot([lo, hi], [lo, hi], ":", color="#667788", linewidth=1.2, label="Dự báo bằng thực tế")
            value_metrics = metrics.loc[metrics.target.eq(target)].set_index("method")
            for method, color, label in (("carry", PALETTE["gray"], "Giữ điểm 2023"),
                                         ("forecast", PALETTE["blue"], "Mô hình đã chọn")):
                ax.scatter(values[f"actual_{target}"], values[f"{method}_{target}"], s=23, color=color,
                           edgecolors="white", linewidths=0.3, alpha=0.85,
                           label=f"{label} · MAE {value_metrics.loc[method, 'mae']:.3f}")
            ax.set(xlim=(lo, hi), ylim=(lo, hi), title=title,
                   xlabel="Điểm PAPI quan sát năm 2024", ylabel="Điểm dự báo năm 2024")
            ax.set_aspect("equal")
            ax.grid(alpha=0.2)
            ax.legend(loc="upper left", fontsize=8)
        return fig


def _grid_figure(run, rows):
    model = run.grid
    cells = model.cells_[model.cluster_level_]
    rectangles = []
    for key in model.label_of_:
        cell = cells[key]
        low, high = run.scaler.inverse_transform(np.vstack((cell.bounds_min, cell.bounds_max)))
        rectangles.append(Rectangle(low, *(high - low)))
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharex=True, sharey=True, layout="constrained")
        for ax, prefix, title in zip(axes, ("forecast", "actual"),
                                    ("Dự báo từ thông tin đến 2023", "Điểm PAPI đã quan sát năm 2024"), strict=True):
            ax.add_collection(PatchCollection(rectangles, facecolor="#EAF1F6", edgecolor="#A8BAC9", linewidth=0.5))
            outside = rows[f"{prefix}_cluster"].eq(-1)
            ax.scatter(rows.loc[~outside, f"{prefix}_{TARGETS[0]}"], rows.loc[~outside, f"{prefix}_{TARGETS[1]}"],
                       s=24, color=PALETTE["blue"], edgecolor="white", linewidth=0.45,
                       label=f"Trong vùng dày ({int((~outside).sum())})")
            ax.scatter(rows.loc[outside, f"{prefix}_{TARGETS[0]}"], rows.loc[outside, f"{prefix}_{TARGETS[1]}"],
                       s=38, color="#B04E27", marker="x", linewidth=1.15, label=f"Ngoài vùng dày ({int(outside.sum())})")
            ax.set(title=title, xlabel=LABELS[0])
            ax.autoscale_view()
            ax.grid(alpha=0.18)
            ax.legend(loc="lower right", fontsize=8)
        axes[0].set_ylabel(LABELS[1])
        return fig


def main() -> int:
    matplotlib.use("Agg")
    panel = load_panel()
    config = load_config()
    if tuple(config["features"]) != TARGETS:
        raise ValueError("Cặp chỉ tiêu dự báo phải khớp cấu hình STING.")
    history = panel.loc[panel.year <= ORIGIN_YEAR]
    run = forecast_from_history(history, config["sting"])
    observed = panel.loc[panel.year == ORIGIN_YEAR + 1]
    rows, metrics, grid_metrics = score_forecast(run, observed)
    comparable = rows.dropna(subset=["actual_cluster"])
    outside = comparable.actual_cluster.eq(-1)
    dest = ROOT / "results"
    evidence = {
        "origin_year": ORIGIN_YEAR, "forecast_year": ORIGIN_YEAR + 1,
        "train_pairs": run.train_pairs, "forecast_count": len(rows), "comparable_count": len(comparable),
        "actual_eligible": len(observed.dropna(subset=list(TARGETS))), "actual_outside": int(outside.sum()),
        "selected_method": run.selection,
        "selected": {target: MODEL_NAMES[method] for target, method in run.selection.items()},
        "cv_mae": run.validation.pivot_table(index="target", columns="method", values="mae").to_dict(orient="index"),
        "scores": metrics.to_dict(orient="records"), "grid": grid_metrics.to_dict(orient="records"),
        "scenario_count": run.scenario_count, "scenario_auc": scenario_auc(rows),
        "scenario_share_range": [float(rows.outside_scenario_share.min()), float(rows.outside_scenario_share.max())],
    }
    (dest / "papi_forecast_2024.json").write_text(
        json.dumps(evidence, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8",
    )
    rows.to_csv(dest / "papi_forecast_provinces_2024.csv", index=False, encoding="utf-8-sig", float_format="%.10f")
    run.validation.to_csv(dest / "papi_forecast_cv.csv", index=False, float_format="%.10f")
    for stem, figure in (("papi_forecast_values", _value_figure(comparable, metrics)),
                         ("papi_forecast_grid", _grid_figure(run, comparable))):
        figure.savefig(dest / "figs" / f"{stem}.png", dpi=300, facecolor="white")
        plt.close(figure)
    print(f"{len(rows)} forecasts, {len(comparable)} paired, {outside.sum()} observed outside dense cells.")
    print(metrics.to_string(index=False))
    print(grid_metrics.to_string(index=False))
    print(f"Historical residual scenarios: {run.scenario_count}. Exploratory AUC: {evidence['scenario_auc']:.3f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
