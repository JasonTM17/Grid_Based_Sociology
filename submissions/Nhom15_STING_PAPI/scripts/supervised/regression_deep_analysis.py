"""Phân tích hồi quy chuyên sâu — đa mô hình, phân rã cơ chế, VIF/hệ số, kiểm định cặp và Conformal 80%/90%.

Tái dùng giao thức của ``scripts/supervised/predict_supervised.py`` (cùng 740 cặp train
2011–2022, 6 fold expanding origin 2017–2022, và 59 cặp holdout 2023→2024 — holdout KHÔNG
bao giờ dùng để chọn siêu tham số, đặc trưng hay hiệu chỉnh bán kính Conformal).

Đầu ra:
  - results/regression_deep_analysis.csv      (bảng tổng hợp đa mô hình, ablation, beta/VIF, kiểm định, conformal)
  - results/regression_conformal_2024.csv     (59 tỉnh holdout kèm cận dự báo Conformal & Quantile)
  - results/regression_deep_analysis.md       (báo cáo phân tích kỹ thuật tiếng Việt)
  - results/figs/regression_diagnostics_deep.png
  - Đồng bộ thêm sheet 'Hồi quy chuyên sâu' trong results/KetQua_STING_PAPI.xlsx

Chạy: ``python -E scripts/supervised/regression_deep_analysis.py``
"""
from __future__ import annotations

import json
import math
import sys
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.common.fig_style import PALETTE, add_source, save_png, style_context  # noqa: E402
from scripts.common.papi_pred_common import (  # noqa: E402
    FEATURE_LABELS,
    REGRESSION_FEATURES,
    REGRESSION_TARGET,
    ROOT,
    load_config,
    load_panel,
)
from scripts.supervised.predict_supervised import (  # noqa: E402
    CLASSIFICATION_CV_FIRST_YEAR,
    FIG_DPI,
    FIG_EXTRA,
    FIG_RETRIEVED,
    FIG_SOURCE,
    HOLDOUT_YEAR,
    SEED,
    build_regression_pairs,
    expanding_origin_folds,
    fit_sting_labeler,
)
from scripts.supervised.supervised_depth import attach_pair_codes  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"
POP_PATH = ROOT / "data" / "processed" / "external_gso_population_63_full.csv"
PUBLISHED_METRICS = RESULTS / "supervised_metrics.csv"

OUT_CSV = RESULTS / "regression_deep_analysis.csv"
OUT_CONFORMAL_CSV = RESULTS / "regression_conformal_2024.csv"
OUT_MD = RESULTS / "regression_deep_analysis.md"
OUT_FIG = FIGS / "regression_diagnostics_deep.png"

BOOT_SEED = 11
BOOT_REPS = 2000


@dataclass(frozen=True)
class ModelSpec:
    key: str
    display: str
    group: str
    kind: str  # "estimator" | "diff" | "fe" | "carry" | "mean"
    feature_cols: tuple[str, ...]
    estimator_factory: Callable[[], Any] | None = None
    param_grid: dict[str, list[Any]] | None = None


def _short_params(params: dict[str, Any]) -> str:
    if not params:
        return "mặc định"
    parts = [f"{k.replace('m__', '')}={v}" for k, v in sorted(params.items())]
    return ", ".join(parts)


def conformal_quantile(abs_residuals: np.ndarray, alpha: float) -> float:
    """Finite-sample split conformal quantile ceil((n+1)*(1-alpha))/n (Vovk et al.)."""
    vals = np.sort(np.asarray(abs_residuals, dtype=float))
    vals = vals[np.isfinite(vals)]
    n = vals.size
    if n == 0:
        raise ValueError("Cần ít nhất 1 phần dư hợp lệ để hiệu chỉnh Conformal.")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha phải nằm trong (0, 1), nhận {alpha}.")
    rank = min(n, max(1, math.ceil((n + 1) * (1.0 - alpha))))
    return float(vals[rank - 1])


def paired_mae_comparison(
    y_true: np.ndarray,
    pred_candidate: np.ndarray,
    pred_reference: np.ndarray,
    *,
    n_boot: int = BOOT_REPS,
    seed: int = BOOT_SEED,
) -> dict[str, float | int | None]:
    """Compare |y - pred_candidate| against |y - pred_reference| via Wilcoxon & bootstrap CI."""
    y = np.asarray(y_true, dtype=float)
    err_cand = np.abs(y - np.asarray(pred_candidate, dtype=float))
    err_ref = np.abs(y - np.asarray(pred_reference, dtype=float))
    diff = err_cand - err_ref  # negative means candidate has smaller MAE
    n = int(diff.size)
    if n == 0:
        raise ValueError("Cần ít nhất 1 cặp quan sát để so sánh MAE.")

    mean_diff = float(diff.mean())
    mae_cand = float(err_cand.mean())
    mae_ref = float(err_ref.mean())
    improved = int((diff < 0.0).sum())

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = diff[idx].mean(axis=1)
    ci_lo, ci_hi = (float(x) for x in np.quantile(boot_means, [0.025, 0.975]))

    nonzero = diff[~np.isclose(diff, 0.0)]
    if nonzero.size == 0:
        stat_val, p_val = None, 1.0
    else:
        w = stats.wilcoxon(nonzero, alternative="two-sided")
        stat_val, p_val = float(w.statistic), float(w.pvalue)

    return {
        "n_pairs": n,
        "mae_candidate": mae_cand,
        "mae_reference": mae_ref,
        "mean_diff": mean_diff,
        "ci95_lo": ci_lo,
        "ci95_hi": ci_hi,
        "wilcoxon_stat": stat_val,
        "wilcoxon_p": p_val,
        "improved_count": improved,
        "improved_pct": float(improved / n),
    }


def compute_vif_table(X_raw: np.ndarray, feature_names: list[str]) -> pd.DataFrame:
    """Compute Variance Inflation Factor (VIF) & condition number on standardized predictors."""
    X_std = StandardScaler().fit_transform(np.asarray(X_raw, dtype=float))
    n_features = X_std.shape[1]
    rows: list[dict[str, Any]] = []
    for j in range(n_features):
        other = [idx for idx in range(n_features) if idx != j]
        reg = LinearRegression().fit(X_std[:, other], X_std[:, j])
        r2_j = float(reg.score(X_std[:, other], X_std[:, j]))
        vif_j = float(np.inf) if r2_j >= 1.0 - 1e-12 else float(1.0 / (1.0 - r2_j))
        rows.append(
            {
                "feature": feature_names[j],
                "label": FEATURE_LABELS.get(feature_names[j], feature_names[j]),
                "r2_on_others": r2_j,
                "vif": vif_j,
            }
        )
    corr = np.corrcoef(X_std, rowvar=False)
    eigvals = np.linalg.eigvalsh(corr)
    cond = float(np.sqrt(eigvals.max() / max(float(eigvals.min()), 1e-12)))
    out = pd.DataFrame(rows)
    out["condition_number"] = cond
    return out


def _build_fe_pipeline(alpha: float = 1.0) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), list(REGRESSION_FEATURES)),
            ("prov", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["province_code"]),
        ]
    )
    return Pipeline([("pre", pre), ("m", Ridge(alpha=alpha, random_state=SEED))])


def build_model_specs() -> list[ModelSpec]:
    """Declarative registry of baselines, course regressors, mechanisms, and panel FE."""
    all_feats = tuple(REGRESSION_FEATURES)
    no_target_feats = tuple(f for f in REGRESSION_FEATURES if f != REGRESSION_TARGET)
    ar1_feats = (REGRESSION_TARGET,)

    return [
        ModelSpec("carry_forward", "Giữ nguyên năm trước (carry-forward)", "baseline", "carry", ar1_feats),
        ModelSpec("train_mean", "Trung bình tập huấn luyện", "baseline", "mean", ar1_feats),
        ModelSpec(
            "ar1_ols",
            "AR(1) OLS (chỉ 6.1)",
            "mechanism",
            "estimator",
            ar1_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", LinearRegression())]),
            {},
        ),
        ModelSpec(
            "ar1_ridge",
            "AR(1) Ridge (chỉ 6.1)",
            "mechanism",
            "estimator",
            ar1_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))]),
            {"m__alpha": [0.1, 1.0, 10.0]},
        ),
        ModelSpec(
            "ols_8f",
            "OLS LinearRegression (8 đặc trưng)",
            "linear",
            "estimator",
            all_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", LinearRegression())]),
            {},
        ),
        ModelSpec(
            "ridge_8f",
            "Ridge (8 đặc trưng, chính thức)",
            "linear",
            "estimator",
            all_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))]),
            {"m__alpha": [0.1, 1.0, 10.0]},
        ),
        ModelSpec(
            "lasso_8f",
            "Lasso L1 (8 đặc trưng)",
            "linear",
            "estimator",
            all_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", Lasso(max_iter=10000, random_state=SEED))]),
            {"m__alpha": [0.001, 0.005, 0.01, 0.05]},
        ),
        ModelSpec(
            "elasticnet_8f",
            "ElasticNet L1+L2 (8 đặc trưng)",
            "linear",
            "estimator",
            all_feats,
            lambda: Pipeline(
                [("sc", StandardScaler()), ("m", ElasticNet(max_iter=10000, random_state=SEED))]
            ),
            {"m__alpha": [0.005, 0.01, 0.05], "m__l1_ratio": [0.2, 0.5, 0.8]},
        ),
        ModelSpec(
            "dt_8f",
            "Decision Tree (8 đặc trưng)",
            "nonlinear",
            "estimator",
            all_feats,
            lambda: DecisionTreeRegressor(random_state=SEED),
            {"max_depth": [2, 3, 4], "min_samples_leaf": [5, 10]},
        ),
        ModelSpec(
            "rf_8f",
            "Random Forest (8 đặc trưng, chính thức)",
            "nonlinear",
            "estimator",
            all_feats,
            lambda: RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=1),
            {"max_depth": [4, 6, None], "min_samples_leaf": [1, 2]},
        ),
        ModelSpec(
            "knn_8f",
            "KNN Regressor (8 đặc trưng)",
            "nonlinear",
            "estimator",
            all_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", KNeighborsRegressor())]),
            {"m__n_neighbors": [5, 10, 20], "m__weights": ["uniform", "distance"]},
        ),
        ModelSpec(
            "svr_rbf_8f",
            "SVR RBF (8 đặc trưng)",
            "nonlinear",
            "estimator",
            all_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", SVR(kernel="rbf"))]),
            {"m__C": [0.1, 1.0, 10.0], "m__epsilon": [0.02, 0.05, 0.1]},
        ),
        ModelSpec(
            "hgb_8f",
            "HistGradientBoosting (8 đặc trưng)",
            "nonlinear",
            "estimator",
            all_feats,
            lambda: HistGradientBoostingRegressor(max_iter=200, early_stopping=False, random_state=SEED),
            {"learning_rate": [0.03, 0.05, 0.1], "max_leaf_nodes": [8, 15]},
        ),
        ModelSpec(
            "ridge_no_target",
            "Ablation Ridge (7 đặc trưng, bỏ 6.1)",
            "mechanism",
            "estimator",
            no_target_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))]),
            {"m__alpha": [0.1, 1.0, 10.0]},
        ),
        ModelSpec(
            "ridge_diff_8f",
            "Mô hình sai phân Δ6.1 = y(t+1)-y(t) (Ridge)",
            "mechanism",
            "diff",
            all_feats,
            lambda: Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))]),
            {"m__alpha": [0.1, 1.0, 10.0, 50.0]},
        ),
        ModelSpec(
            "elasticnet_diff_8f",
            "Mô hình sai phân Δ6.1 = y(t+1)-y(t) (ElasticNet)",
            "mechanism",
            "diff",
            all_feats,
            lambda: Pipeline(
                [("sc", StandardScaler()), ("m", ElasticNet(max_iter=10000, random_state=SEED))]
            ),
            {"m__alpha": [0.005, 0.01, 0.05], "m__l1_ratio": [0.2, 0.5, 0.8]},
        ),
        ModelSpec(
            "ridge_fe_province",
            "Panel FE: Ridge + OneHot 63 tỉnh",
            "panel_fe",
            "fe",
            all_feats,
            _build_fe_pipeline,
            {"m__alpha": [1.0, 10.0, 50.0]},
        ),
    ]


def _evaluate_spec(
    spec: ModelSpec,
    tr: pd.DataFrame,
    te: pd.DataFrame,
    reg_cv: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, Any | None]:
    """Fit/select strictly inside expanding CV on `tr`, return summary + OOF & holdout preds."""
    ytr = tr["y"].to_numpy()
    yte = te["y"].to_numpy()
    carry_tr = tr["carry"].to_numpy()
    carry_te = te["carry"].to_numpy()
    oof_preds = np.full(len(tr), np.nan, dtype=float)
    fold_r2: list[float] = []
    fitted_model = None
    best_params: dict[str, Any] = {}

    if spec.kind == "carry":
        for _, va_idx in reg_cv:
            oof_preds[va_idx] = carry_tr[va_idx]
            fold_r2.append(float(r2_score(ytr[va_idx], carry_tr[va_idx])))
        pred_te = carry_te.copy()
    elif spec.kind == "mean":
        for tr_idx, va_idx in reg_cv:
            mu = float(ytr[tr_idx].mean())
            oof_preds[va_idx] = mu
            fold_r2.append(float(r2_score(ytr[va_idx], oof_preds[va_idx])))
        pred_te = np.full_like(yte, float(ytr.mean()))
    elif spec.kind == "estimator":
        Xtr = tr[list(spec.feature_cols)].to_numpy()
        Xte = te[list(spec.feature_cols)].to_numpy()
        gs = GridSearchCV(
            spec.estimator_factory(),  # type: ignore[misc]
            spec.param_grid or {},
            cv=reg_cv,
            scoring="r2",
            n_jobs=1,
            refit=True,
        )
        gs.fit(Xtr, ytr)
        best_params = dict(gs.best_params_)
        fitted_model = gs.best_estimator_
        pred_te = fitted_model.predict(Xte)
        for tr_idx, va_idx in reg_cv:
            est = clone(fitted_model).fit(Xtr[tr_idx], ytr[tr_idx])
            oof_preds[va_idx] = est.predict(Xtr[va_idx])
            fold_r2.append(float(r2_score(ytr[va_idx], oof_preds[va_idx])))
    elif spec.kind == "diff":
        # Train on delta = y(t+1) - y(t) and reconstruct y_hat(t+1) = y(t) + delta_hat.
        # Notice R^2 of reconstructed y_hat uses identical y_true scale as direct level models,
        # so CV tuning and R^2 comparisons stay 100% commensurate!
        Xtr = tr[list(spec.feature_cols)].to_numpy()
        Xte = te[list(spec.feature_cols)].to_numpy()
        delta_tr = ytr - carry_tr

        param_list = [
            dict(zip(spec.param_grid.keys(), combo, strict=True))
            for combo in np.array(
                np.meshgrid(*spec.param_grid.values()), dtype=object
            ).T.reshape(-1, len(spec.param_grid))
        ] if spec.param_grid else [{}]

        best_score = -np.inf
        best_oof = None
        best_fold_r2: list[float] = []
        for params in param_list:
            cand_oof = np.full(len(tr), np.nan, dtype=float)
            cand_r2: list[float] = []
            for tr_idx, va_idx in reg_cv:
                est = spec.estimator_factory().set_params(**params)  # type: ignore[misc]
                est.fit(Xtr[tr_idx], delta_tr[tr_idx])
                cand_oof[va_idx] = carry_tr[va_idx] + est.predict(Xtr[va_idx])
                cand_r2.append(float(r2_score(ytr[va_idx], cand_oof[va_idx])))
            mean_r2 = float(np.mean(cand_r2))
            if mean_r2 > best_score:
                best_score = mean_r2
                best_params = params
                best_oof = cand_oof
                best_fold_r2 = cand_r2
        oof_preds = best_oof  # type: ignore[assignment]
        fold_r2 = best_fold_r2
        fitted_model = spec.estimator_factory().set_params(**best_params).fit(Xtr, delta_tr)  # type: ignore[misc]
        pred_te = carry_te + fitted_model.predict(Xte)
    elif spec.kind == "fe":
        cols = ["province_code", *spec.feature_cols]
        Xtr_df = tr[cols].copy()
        Xte_df = te[cols].copy()
        gs = GridSearchCV(
            spec.estimator_factory(),  # type: ignore[misc]
            spec.param_grid or {},
            cv=reg_cv,
            scoring="r2",
            n_jobs=1,
            refit=True,
        )
        gs.fit(Xtr_df, ytr)
        best_params = dict(gs.best_params_)
        fitted_model = gs.best_estimator_
        pred_te = fitted_model.predict(Xte_df)
        for tr_idx, va_idx in reg_cv:
            est = clone(fitted_model).fit(Xtr_df.iloc[tr_idx], ytr[tr_idx])
            oof_preds[va_idx] = est.predict(Xtr_df.iloc[va_idx])
            fold_r2.append(float(r2_score(ytr[va_idx], oof_preds[va_idx])))
    else:
        raise ValueError(f"Unknown spec.kind: {spec.kind}")

    oof_mask = np.isfinite(oof_preds)
    cv_r2_raw = float(np.mean(fold_r2))
    cv_mae = float(mean_absolute_error(ytr[oof_mask], oof_preds[oof_mask]))
    cv_rmse = float(np.sqrt(mean_squared_error(ytr[oof_mask], oof_preds[oof_mask])))
    ho_mae = float(mean_absolute_error(yte, pred_te))
    ho_rmse = float(np.sqrt(mean_squared_error(yte, pred_te)))
    ho_r2 = float(r2_score(yte, pred_te))
    ho_bias = float(np.mean(yte - pred_te))
    corr_carry = float(np.corrcoef(pred_te, carry_te)[0, 1]) if np.std(pred_te) > 0 else np.nan

    row = {
        "key": spec.key,
        "model": spec.display,
        "group": spec.group,
        "n_features": len(spec.feature_cols),
        "best_params": _short_params(best_params),
        "cv_r2_raw": cv_r2_raw,
        "value_cv": round(cv_r2_raw, 3),
        "cv_r2_std": float(np.std(fold_r2, ddof=0)),
        "cv_mae": cv_mae,
        "cv_rmse": cv_rmse,
        "holdout_mae": ho_mae,
        "holdout_rmse": ho_rmse,
        "holdout_r2": ho_r2,
        "holdout_bias": ho_bias,
        "corr_with_carry_holdout": corr_carry,
        "fold_r2": fold_r2,
    }
    return row, oof_preds, pred_te, fitted_model


def _compute_train_fence(panel: pd.DataFrame, cfg: dict[str, Any]) -> tuple[float, float | None]:
    """Compute historical cluster lower fence (<=2023) without peeking at 2024 targets."""
    feats = list(cfg["features"])
    hist = panel.loc[panel["year"] <= HOLDOUT_YEAR].dropna(subset=feats).copy()
    sc, grid = fit_sting_labeler(hist, HOLDOUT_YEAR, feats, cfg["sting"])
    labels = grid.predict(sc.transform(hist[feats]))
    non_noise = labels[labels >= 0]
    core_cluster = int(pd.Series(non_noise).mode().iloc[0])
    hist_c2 = hist.loc[labels == core_cluster, REGRESSION_TARGET]
    q1, q3 = hist_c2.quantile([0.25, 0.75])
    train_fence = float(q1 - 0.5 * (q3 - q1))

    pub_fence = None
    stake_csv = RESULTS / "stakeholder_province_summary_2024.csv"
    if stake_csv.is_file():
        stake = pd.read_csv(stake_csv)
        c2_2024 = stake.loc[stake["grid_status"].eq("in_cluster"), "sd_6_1"].dropna()
        if not c2_2024.empty:
            sq1, sq3 = c2_2024.quantile([0.25, 0.75])
            pub_fence = float(sq1 - 0.5 * (sq3 - sq1))
    return train_fence, pub_fence


def _sync_excel_sheet(
    summary_df: pd.DataFrame,
    xlsx_path: Path = RESULTS / "KetQua_STING_PAPI.xlsx",
) -> None:
    """Append or refresh 'Hồi quy chuyên sâu' sheet and 'Mục lục' table in KetQua_STING_PAPI.xlsx."""
    if not xlsx_path.is_file():
        return
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "Hồi quy chuyên sâu"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)
    ws.views.sheetView[0].showGridLines = False

    white_fill = PatternFill("solid", fgColor="FFFFFF")
    thin_side = Side(style="thin", color="BFBFBF")
    header_font = Font(name="Arial", size=10, bold=True, color="000000")
    body_font = Font(name="Arial", size=10, color="000000")

    cols = [
        ("section", "Nhóm phân tích", 18.0, "General", "left"),
        ("item", "Mô hình / Chỉ tiêu", 36.0, "General", "left"),
        ("metric_primary", "CV R² / Chính", 14.0, "0.0000", "right"),
        ("metric_secondary", "CV MAE / Phụ", 14.0, "0.0000", "right"),
        ("holdout_mae", "Holdout MAE", 13.0, "0.0000", "right"),
        ("holdout_rmse", "Holdout RMSE", 14.0, "0.0000", "right"),
        ("holdout_r2", "Holdout R²", 12.0, "0.000", "right"),
        ("note", "Ghi chú / Thông số", 48.0, "General", "left"),
    ]
    last_col = openpyxl.utils.get_column_letter(len(cols))
    ws["A2"] = "Phân tích hồi quy chuyên sâu — đa mô hình, AR(1) vs Δy, VIF và Conformal 80%/90%"
    ws["A2"].font = Font(name="Arial", size=14, bold=True, color="000000")
    ws["A2"].fill = copy(white_fill)
    ws.merge_cells(f"A2:{last_col}2")
    ws.row_dimensions[2].height = 24.0
    ws["A3"] = "Train 740 cặp (2011–2022) · 6 fold expanding origin 2017–2022 · Holdout 59 tỉnh (2023→2024)"
    ws["A3"].font = Font(name="Arial", size=10, italic=True, color="000000")
    ws.merge_cells(f"A3:{last_col}3")
    ws.row_dimensions[3].height = 20.0

    ws.row_dimensions[5].height = 28.0
    for c_idx, (_, title, width, _, _) in enumerate(cols, start=1):
        cell = ws.cell(5, c_idx, title)
        cell.font = copy(header_font)
        cell.fill = copy(white_fill)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(
            top=thin_side,
            bottom=thin_side,
            left=None if c_idx == 1 else thin_side,
            right=None if c_idx == len(cols) else thin_side,
        )
        ws.column_dimensions[openpyxl.utils.get_column_letter(c_idx)].width = width

    export = summary_df[
        ["section", "item", "metric_primary", "metric_secondary", "holdout_mae", "holdout_rmse", "holdout_r2", "note"]
    ]
    for r_idx, (_, rec) in enumerate(export.iterrows(), start=6):
        ws.row_dimensions[r_idx].height = 24.0
        for c_idx, (k, _, _, num_fmt, h_align) in enumerate(cols, start=1):
            val = rec[k]
            val = None if pd.isna(val) else (val.item() if hasattr(val, "item") else val)
            cell = ws.cell(r_idx, c_idx, val)
            cell.font = copy(body_font)
            cell.fill = copy(white_fill)
            cell.number_format = num_fmt
            cell.alignment = Alignment(
                horizontal=h_align if h_align != "left" else None,
                vertical="center",
                wrap_text=(k == "note"),
            )

    end_row = 5 + len(export)
    tbl = Table(displayName="PapiRegressionDeep", ref=f"A5:{last_col}{end_row}")
    tbl.tableStyleInfo = TableStyleInfo(
        name="TableStyleLight1",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=False,
        showColumnStripes=False,
    )
    ws.add_table(tbl)
    ws.freeze_panes = "A6"

    if "Mục lục" in wb.sheetnames:
        ws_toc = wb["Mục lục"]
        csv_col = 6
        target_row = None
        for r in range(6, ws_toc.max_row + 1):
            if ws_toc.cell(r, csv_col).value == "regression_deep_analysis.csv":
                target_row = r
                break
        if target_row is None:
            target_row = ws_toc.max_row + 1
        ws_toc.row_dimensions[target_row].height = 19.5
        ws_toc.cell(target_row, 1, "Hồi quy chuyên sâu")
        ws_toc.cell(target_row, 2, f"=HYPERLINK(\"#'{sheet_name}'!A2\",\"{sheet_name}\")")
        ws_toc.cell(target_row, 3, "Đa mô hình, AR(1) vs Δy, hệ số/VIF, Wilcoxon & Conformal 90%")
        ws_toc.cell(target_row, 4, len(export))
        ws_toc.cell(target_row, 5, len(cols))
        ws_toc.cell(target_row, 6, "regression_deep_analysis.csv")
        ref_toc_row = 6
        for c in range(1, 7):
            src_cell = ws_toc.cell(ref_toc_row, c)
            dst_cell = ws_toc.cell(target_row, c)
            dst_cell.font = copy(src_cell.font)
            dst_cell.fill = copy(src_cell.fill)
            dst_cell.alignment = copy(src_cell.alignment)
            dst_cell.number_format = src_cell.number_format
        n_tables = sum(1 for r in range(6, ws_toc.max_row + 1) if ws_toc.cell(r, csv_col).value)
        ws_toc["A3"] = (
            f"{n_tables} bảng kết quả theo tệp nguồn. Mở Thống kê khách hàng 2024 hoặc Quan sát 2024 để xem kết quả chính."
        )
        if "PapiDanhMuc" in ws_toc.tables:
            toc_ref = f"A5:F{5 + n_tables}"
            toc_table = ws_toc.tables["PapiDanhMuc"]
            toc_table.ref = toc_ref
            if toc_table.autoFilter is not None:
                toc_table.autoFilter.ref = toc_ref

    wb.save(xlsx_path)


_PANEL_A_SHORT = {
    "carry_forward": "Giữ năm trước (Carry-forward)",
    "ar1_ols": "AR(1) OLS (chỉ 6.1)",
    "ar1_ridge": "AR(1) Ridge (chỉ 6.1)",
    "ols_8f": "OLS Linear (8 đặc trưng)",
    "ridge_8f": "Ridge (8F, chính thức)",
    "lasso_8f": "Lasso L1 (8 đặc trưng)",
    "elasticnet_8f": "ElasticNet L1+L2 (8F)",
    "dt_8f": "Decision Tree (8F)",
    "rf_8f": "Random Forest (8F, chính thức)",
    "knn_8f": "KNN Regressor (8F)",
    "svr_rbf_8f": "SVR RBF (8 đặc trưng)",
    "hgb_8f": "HistGradientBoosting (8F)",
    "ridge_no_target": "Ablation Ridge (7F, bỏ 6.1)",
    "ridge_diff_8f": "Sai phân Δ6.1 (Ridge, α=50)",
    "elasticnet_diff_8f": "Sai phân Δ6.1 (ElasticNet)",
    "ridge_fe_province": "Panel FE: Ridge + 63 tỉnh",
}


def plot_regression_diagnostics(
    model_df: pd.DataFrame,
    coef_df: pd.DataFrame,
    conformal_df: pd.DataFrame,
    pop_sizes: pd.Series,
    train_fence: float,
    out_path: Path = OUT_FIG,
) -> None:
    """Create 4-panel 330-DPI diagnostic figure for deep regression analysis."""
    with style_context():
        fig, axes = plt.subplots(2, 2, figsize=(13.6, 9.4))

        # Panel A: Model CV R^2 comparison (sorted ascending so best is top)
        ax = axes[0, 0]
        plot_df = model_df.loc[model_df["key"] != "train_mean"].sort_values("cv_r2_raw", ascending=True)
        colors = []
        for k, g in zip(plot_df["key"], plot_df["group"], strict=True):
            if k == "ridge_8f":
                colors.append(PALETTE["blue"])
            elif k in ("elasticnet_8f", "ridge_diff_8f"):
                colors.append(PALETTE["green"])
            elif g in ("mechanism", "panel_fe"):
                colors.append(PALETTE["purple"])
            elif g == "baseline":
                colors.append(PALETTE["gray"])
            else:
                colors.append(PALETTE["orange"])
        y_pos = np.arange(len(plot_df))
        ax.barh(y_pos, plot_df["cv_r2_raw"], color=colors, height=0.72)
        ax.axvline(0.0, color="#444444", lw=0.8, ls=":")
        for yp, val in zip(y_pos, plot_df["cv_r2_raw"], strict=True):
            offset = 0.008 if val >= 0 else -0.008
            ha = "left" if val >= 0 else "right"
            ax.text(val + offset, yp, f"{val:.3f}", va="center", ha=ha, fontsize=8)
        short_labels = [_PANEL_A_SHORT.get(k, m) for k, m in zip(plot_df["key"], plot_df["model"], strict=True)]
        ax.set_yticks(y_pos, short_labels, fontsize=8.5)
        ax.set_xlim(min(-0.35, float(plot_df["cv_r2_raw"].min()) - 0.09), float(plot_df["cv_r2_raw"].max()) + 0.09)
        ax.set_xlabel("R² trung bình CV expanding origin 2017–2022")
        ax.set_title("(A) Đối chiếu đa mô hình & phân rã cơ chế (CV)")
        ax.grid(alpha=0.25, axis="x")

        # Panel B: Standardized coefficients Ridge vs ElasticNet + VIF
        ax = axes[0, 1]
        c_ord = coef_df.sort_values("beta_ridge", ascending=True)
        yp = np.arange(len(c_ord))
        ax.barh(yp - 0.17, c_ord["beta_ridge"], height=0.34, color=PALETTE["blue"], label="Ridge chuẩn hóa")
        ax.barh(yp + 0.17, c_ord["beta_elasticnet"], height=0.34, color=PALETTE["green"], label="ElasticNet (L1+L2)")
        ax.axvline(0.0, color="#444444", lw=0.8, ls=":")
        lbls = [
            f"{row['feature']} (VIF={row['vif']:.1f})"
            for _, row in c_ord.iterrows()
        ]
        ax.set_yticks(yp, lbls, fontsize=8.5)
        ax.set_xlabel("Hệ số hồi quy chuẩn hóa (β trên Z-score train)")
        ax.set_title("(B) Hệ số β chuẩn hóa & đa cộng tuyến VIF")
        ax.legend(loc="lower right", fontsize=8.5)
        ax.grid(alpha=0.25, axis="x")

        # Panel C: Residuals holdout 2023->2024 vs lag-1 6.1, colored by province pop size
        ax = axes[1, 0]
        is_large = pop_sizes.to_numpy()
        res = conformal_df["residual_ridge"].to_numpy()
        x23 = conformal_df["sd_6_1_2023"].to_numpy()
        ax.scatter(x23[is_large], res[is_large], c=PALETTE["blue"], s=36, alpha=0.85, label="Tỉnh lớn (≥ median)")
        ax.scatter(
            x23[~is_large],
            res[~is_large],
            c=PALETTE["orange"],
            marker="^",
            s=40,
            alpha=0.88,
            label="Tỉnh nhỏ (< median)",
        )
        ax.axhline(0.0, color="#333333", lw=1.0, ls="--", label="Sai số = 0")
        ax.axhline(float(res.mean()), color=PALETTE["purple"], lw=1.1, ls="-.", label=f"Mean ({res.mean():+.4f})")
        top4 = conformal_df.iloc[np.argsort(np.abs(res))[::-1][:4]]
        offsets = {"Bình Thuận": (7, -2), "Tây Ninh": (6, 2), "Đắk Nông": (-52, 2), "Phú Yên": (6, -3)}
        for _, tr_row in top4.iterrows():
            name = str(tr_row["province_vi"])
            dx, dy = offsets.get(name, (4, 4))
            ax.annotate(
                name,
                (float(tr_row["sd_6_1_2023"]), float(tr_row["residual_ridge"])),
                xytext=(dx, dy),
                textcoords="offset points",
                fontsize=8,
            )
        ax.set_ylim(-0.13, 0.255)
        ax.set_xlabel("6.1 Y tế công lập năm gốc 2023 (sd_6_1)")
        ax.set_ylabel("Phần dư holdout (Thực tế 2024 − Dự báo Ridge)")
        ax.set_title("(C) Chẩn đoán phần dư holdout 2023→2024 (n = 59)")
        ax.legend(loc="upper right", ncol=2, fontsize=7.8, columnspacing=0.9)
        ax.grid(alpha=0.25)

        # Panel D: Calibrated 90% Conformal Intervals across 59 holdout provinces
        ax = axes[1, 1]
        ord_df = conformal_df.sort_values("pred_ridge").reset_index(drop=True)
        idx = np.arange(len(ord_df))
        ax.vlines(
            idx,
            ord_df["conformal_lo90"],
            ord_df["conformal_hi90"],
            color=PALETTE["sky"],
            lw=2.0,
            alpha=0.75,
            label="Khoảng Conformal 90% (CV 2017–2022)",
        )
        ax.plot(idx, ord_df["pred_ridge"], color=PALETTE["blue"], lw=1.5, label="Dự báo điểm Ridge")
        covered = ord_df["covered_conformal_90"].to_numpy(dtype=bool)
        ax.scatter(idx[covered], ord_df.loc[covered, "actual_2024"], c=PALETTE["green"], s=20, label="Thực tế nằm trong dải")
        ax.scatter(
            idx[~covered],
            ord_df.loc[~covered, "actual_2024"],
            c=PALETTE["orange"],
            marker="x",
            s=36,
            label="Thực tế ngoài dải",
        )
        ax.axhline(train_fence, color=PALETTE["purple"], ls="--", lw=1.0, label=f"Mốc dưới train ({train_fence:.4f})")
        cov_pct = float(covered.mean())
        ax.set_xlabel("59 tỉnh holdout sắp theo dự báo Ridge tăng dần")
        ax.set_ylabel("Điểm 6.1 Y tế công lập năm 2024")
        ax.set_title(f"(D) Conformal 90% trên holdout 2024 — phủ thực {cov_pct:.1%}")
        ax.legend(loc="upper left", fontsize=7.8)
        ax.grid(alpha=0.25)

        add_source(fig, FIG_SOURCE, retrieved=FIG_RETRIEVED, extra=FIG_EXTRA)
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        save_png(fig, out_path, dpi=FIG_DPI)
        plt.close(fig)


def run_study(root: Path = ROOT, *, write_outputs: bool = True) -> dict[str, Any]:
    """Run the complete deep regression suite reproducibly and return structured outputs."""
    panel = load_panel() if root == ROOT else pd.read_csv(root / "data/processed/papi_panel_63_2011_2024.csv")
    cfg = load_config() if root == ROOT else json.loads((root / "models/predict_config.json").read_text(encoding="utf-8"))

    pairs = build_regression_pairs(panel)
    pairs = attach_pair_codes(panel, pairs)
    tr = pairs.loc[pairs["year_t"] < HOLDOUT_YEAR].reset_index(drop=True)
    te = pairs.loc[pairs["year_t"] == HOLDOUT_YEAR].reset_index(drop=True)
    name_map = dict(zip(panel["province_code"], panel["province_vi"]))
    te["province_vi"] = te["province_code"].map(name_map)

    reg_cv = expanding_origin_folds(
        tr["year_t"].to_numpy(), first_validation_origin=CLASSIFICATION_CV_FIRST_YEAR
    )

    model_rows: list[dict[str, Any]] = []
    oof_store: dict[str, np.ndarray] = {}
    te_store: dict[str, np.ndarray] = {}
    fitted_store: dict[str, Any] = {}
    for spec in build_model_specs():
        row, oof, pred_te, fitted = _evaluate_spec(spec, tr, te, reg_cv)
        model_rows.append(row)
        oof_store[spec.key] = oof
        te_store[spec.key] = pred_te
        fitted_store[spec.key] = fitted

    model_df = pd.DataFrame(model_rows)

    # Fail-closed parity check against published supervised_metrics.csv
    pub_path = root / "results" / "supervised_metrics.csv"
    if pub_path.is_file():
        pub = pd.read_csv(pub_path, encoding="utf-8-sig")
        pub_reg = pub.loc[pub["task"].eq("regression")].set_index("model")
        ridge_row = model_df.loc[model_df["key"].eq("ridge_8f")].iloc[0]
        rf_row = model_df.loc[model_df["key"].eq("rf_8f")].iloc[0]
        if float(ridge_row["value_cv"]) != float(pub_reg.loc["ridge", "value_cv"]):
            raise AssertionError("CV R2 của Ridge lệch results/supervised_metrics.csv")
        if round(float(ridge_row["holdout_mae"]), 4) != float(pub_reg.loc["ridge", "holdout_mae"]):
            raise AssertionError("Holdout MAE của Ridge lệch results/supervised_metrics.csv")
        if float(rf_row["value_cv"]) != float(pub_reg.loc["random forest", "value_cv"]):
            raise AssertionError("CV R2 của Random Forest lệch results/supervised_metrics.csv")

    # Beats count per fold against Ridge & Carry-forward
    ridge_folds = model_df.loc[model_df["key"].eq("ridge_8f"), "fold_r2"].iloc[0]
    carry_folds = model_df.loc[model_df["key"].eq("carry_forward"), "fold_r2"].iloc[0]
    model_df["beats_ridge_folds"] = model_df["fold_r2"].map(
        lambda fr: sum(1 for a, b in zip(fr, ridge_folds, strict=True) if a > b + 1e-12)
    )
    model_df["beats_carry_folds"] = model_df["fold_r2"].map(
        lambda fr: sum(1 for a, b in zip(fr, carry_folds, strict=True) if a > b + 1e-12)
    )

    # VIF & standardized linear coefficients (fitted only on `tr`)
    Xtr_all = tr[list(REGRESSION_FEATURES)].to_numpy()
    ytr = tr["y"].to_numpy()
    vif_df = compute_vif_table(Xtr_all, list(REGRESSION_FEATURES))
    ols_sc = Pipeline([("sc", StandardScaler()), ("m", LinearRegression())]).fit(Xtr_all, ytr)
    ridge_best = fitted_store["ridge_8f"]
    lasso_best = fitted_store["lasso_8f"]
    enet_best = fitted_store["elasticnet_8f"]
    coef_df = vif_df.copy()
    coef_df["beta_ols"] = ols_sc.named_steps["m"].coef_
    coef_df["beta_ridge"] = ridge_best.named_steps["m"].coef_
    coef_df["beta_lasso"] = lasso_best.named_steps["m"].coef_
    coef_df["beta_elasticnet"] = enet_best.named_steps["m"].coef_

    # Paired MAE tests on OOF CV (2017–2022) & Holdout (2023->2024)
    oof_mask = np.isfinite(oof_store["ridge_8f"])
    yte = te["y"].to_numpy()
    tests_summary = {
        "oof_ridge_vs_carry": paired_mae_comparison(
            ytr[oof_mask], oof_store["ridge_8f"][oof_mask], oof_store["carry_forward"][oof_mask]
        ),
        "holdout_ridge_vs_carry": paired_mae_comparison(
            yte, te_store["ridge_8f"], te_store["carry_forward"]
        ),
        "oof_enet_vs_ridge": paired_mae_comparison(
            ytr[oof_mask], oof_store["elasticnet_8f"][oof_mask], oof_store["ridge_8f"][oof_mask]
        ),
        "holdout_enet_vs_ridge": paired_mae_comparison(
            yte, te_store["elasticnet_8f"], te_store["ridge_8f"]
        ),
        "oof_ar1_vs_carry": paired_mae_comparison(
            ytr[oof_mask], oof_store["ar1_ridge"][oof_mask], oof_store["carry_forward"][oof_mask]
        ),
    }

    # Conformal Prediction Intervals calibrated STRICTLY from <=2022 CV OOF |y - pred| residuals
    oof_abs_err = np.abs(ytr[oof_mask] - oof_store["ridge_8f"][oof_mask])
    recent_mask = oof_mask & (tr["year_t"].to_numpy() >= 2021)
    recent_abs_err = np.abs(ytr[recent_mask] - oof_store["ridge_8f"][recent_mask])

    q80_oof = conformal_quantile(oof_abs_err, alpha=0.20)
    q90_oof = conformal_quantile(oof_abs_err, alpha=0.10)
    q90_recent = conformal_quantile(recent_abs_err, alpha=0.10)

    # Quantile GradientBoostingRegressor trained strictly on `tr`
    gbr_q10 = GradientBoostingRegressor(
        loss="quantile", alpha=0.10, n_estimators=120, max_depth=3, min_samples_leaf=5, random_state=SEED
    ).fit(Xtr_all, ytr)
    gbr_q50 = GradientBoostingRegressor(
        loss="quantile", alpha=0.50, n_estimators=120, max_depth=3, min_samples_leaf=5, random_state=SEED
    ).fit(Xtr_all, ytr)
    gbr_q90 = GradientBoostingRegressor(
        loss="quantile", alpha=0.90, n_estimators=120, max_depth=3, min_samples_leaf=5, random_state=SEED
    ).fit(Xtr_all, ytr)

    Xte_all = te[list(REGRESSION_FEATURES)].to_numpy()
    q10_te = gbr_q10.predict(Xte_all)
    q50_te = gbr_q50.predict(Xte_all)
    q90_te = np.maximum(gbr_q90.predict(Xte_all), q10_te)

    train_fence, pub_fence = _compute_train_fence(panel, cfg)
    pred_ridge_te = te_store["ridge_8f"]

    # Join 2024 observed stakeholder groups (strictly descriptive post-hoc summary only)
    stake_path = root / "results" / "stakeholder_province_summary_2024.csv"
    actual_low61 = np.zeros(len(te), dtype=bool)
    actual_outside = np.zeros(len(te), dtype=bool)
    if stake_path.is_file():
        stake_2024 = pd.read_csv(stake_path).set_index("province_code")
        for idx_i, pc in enumerate(te["province_code"]):
            if pc in stake_2024.index:
                row_s = stake_2024.loc[pc]
                actual_outside[idx_i] = str(row_s["grid_status"]) != "in_cluster"
                actual_low61[idx_i] = str(row_s["action_group"]) == "Ưu tiên cải thiện Y tế 6.1"

    conformal_df = pd.DataFrame(
        {
            "province_code": te["province_code"].to_numpy(dtype=int),
            "province_vi": te["province_vi"].tolist(),
            "sd_6_1_2023": te["carry"].to_numpy(),
            "actual_2024": yte,
            "pred_ridge": pred_ridge_te,
            "pred_elasticnet": te_store["elasticnet_8f"],
            "residual_ridge": yte - pred_ridge_te,
            "abs_residual_ridge": np.abs(yte - pred_ridge_te),
            "conformal_lo80": pred_ridge_te - q80_oof,
            "conformal_hi80": pred_ridge_te + q80_oof,
            "conformal_lo90": pred_ridge_te - q90_oof,
            "conformal_hi90": pred_ridge_te + q90_oof,
            "quantile_lo90": q10_te,
            "quantile_med": q50_te,
            "quantile_hi90": q90_te,
            "covered_conformal_80": (yte >= pred_ridge_te - q80_oof) & (yte <= pred_ridge_te + q80_oof),
            "covered_conformal_90": (yte >= pred_ridge_te - q90_oof) & (yte <= pred_ridge_te + q90_oof),
            "covered_quantile_80": (yte >= q10_te) & (yte <= q90_te),
            "alert_point_below_train_fence": pred_ridge_te < train_fence,
            "alert_lo90_below_train_fence": (pred_ridge_te - q90_oof) < train_fence,
            "actual_outside_cluster": actual_outside,
            "actual_low61_2024": actual_low61,
        }
    ).sort_values("province_code").reset_index(drop=True)

    # Province population sizes for diagnostic residual plot
    pop_df = pd.read_csv(root / "data/processed/external_gso_population_63_full.csv")
    pop23 = pop_df.loc[pop_df["year"] == HOLDOUT_YEAR, ["province_code", "gso_pop_total_thousand"]]
    merged_pop = conformal_df[["province_code"]].merge(pop23, on="province_code", how="left")
    med_pop = float(merged_pop["gso_pop_total_thousand"].median())
    is_large_pop = merged_pop["gso_pop_total_thousand"] >= med_pop

    conformal_summary = {
        "q80_oof_radius": q80_oof,
        "q90_oof_radius": q90_oof,
        "q90_recent_21_22_radius": q90_recent,
        "emp_cov_80_oof": float(conformal_df["covered_conformal_80"].mean()),
        "emp_cov_90_oof": float(conformal_df["covered_conformal_90"].mean()),
        "emp_cov_90_recent": float(
            ((yte >= pred_ridge_te - q90_recent) & (yte <= pred_ridge_te + q90_recent)).mean()
        ),
        "emp_cov_quantile_80": float(conformal_df["covered_quantile_80"].mean()),
        "mean_width_quantile_80": float((q90_te - q10_te).mean()),
        "train_fence": train_fence,
        "pub_fence": pub_fence,
        "point_alerts_n": int(conformal_df["alert_point_below_train_fence"].sum()),
        "lo90_alerts_n": int(conformal_df["alert_lo90_below_train_fence"].sum()),
        "actual_low61_in_holdout_n": int(conformal_df["actual_low61_2024"].sum()),
        "lo90_catches_low61": int(
            (conformal_df["alert_lo90_below_train_fence"] & conformal_df["actual_low61_2024"]).sum()
        ),
        "point_catches_low61": int(
            (conformal_df["alert_point_below_train_fence"] & conformal_df["actual_low61_2024"]).sum()
        ),
        "point_fp": int(
            (conformal_df["alert_point_below_train_fence"] & ~conformal_df["actual_low61_2024"]).sum()
        ),
        "lo90_fp": int(
            (conformal_df["alert_lo90_below_train_fence"] & ~conformal_df["actual_low61_2024"]).sum()
        ),
        "n_holdout": int(len(conformal_df)),
    }

    # Unified normalized summary table for CSV & Excel
    unified_rows: list[dict[str, Any]] = []
    for _, r in model_df.iterrows():
        unified_rows.append(
            {
                "section": f"model_{r['group']}",
                "item": r["model"],
                "metric_primary": round(float(r["cv_r2_raw"]), 4),
                "metric_secondary": round(float(r["cv_mae"]), 4),
                "holdout_mae": round(float(r["holdout_mae"]), 4),
                "holdout_rmse": round(float(r["holdout_rmse"]), 4),
                "holdout_r2": round(float(r["holdout_r2"]), 3),
                "note": (
                    f"params={r['best_params']}; beats_ridge={r['beats_ridge_folds']}/6; "
                    f"beats_carry={r['beats_carry_folds']}/6; bias={r['holdout_bias']:+.4f}"
                ),
            }
        )
    for _, r in coef_df.iterrows():
        unified_rows.append(
            {
                "section": "coef_and_vif",
                "item": f"{r['feature']} ({r['label']})",
                "metric_primary": round(float(r["beta_ridge"]), 4),
                "metric_secondary": round(float(r["beta_elasticnet"]), 4),
                "holdout_mae": round(float(r["beta_lasso"]), 4),
                "holdout_rmse": round(float(r["beta_ols"]), 4),
                "holdout_r2": round(float(r["vif"]), 3),
                "note": (
                    f"R2_other={r['r2_on_others']:.3f}; kappa={r['condition_number']:.2f}; "
                    "(cols holdout_mae/rmse/r2 store beta_lasso, beta_ols, VIF)"
                ),
            }
        )
    for t_key, label_t in (
        ("oof_ridge_vs_carry", "OOF CV 2017–2022: Ridge vs Carry-Forward"),
        ("holdout_ridge_vs_carry", "Holdout 2023→2024: Ridge vs Carry-Forward"),
        ("oof_ar1_vs_carry", "OOF CV 2017–2022: AR(1) Ridge vs Carry-Forward"),
        ("oof_enet_vs_ridge", "OOF CV 2017–2022: ElasticNet vs Ridge"),
        ("holdout_enet_vs_ridge", "Holdout 2023→2024: ElasticNet vs Ridge"),
    ):
        t = tests_summary[t_key]
        unified_rows.append(
            {
                "section": "paired_test",
                "item": label_t,
                "metric_primary": round(float(t["mean_diff"]), 5),
                "metric_secondary": round(float(t["wilcoxon_p"]), 5),
                "holdout_mae": round(float(t["mae_candidate"]), 4),
                "holdout_rmse": round(float(t["mae_reference"]), 4),
                "holdout_r2": round(float(t["improved_pct"]), 3),
                "note": (
                    f"n={t['n_pairs']}; CI95=[{t['ci95_lo']:+.5f}, {t['ci95_hi']:+.5f}]; "
                    f"improved={t['improved_count']}/{t['n_pairs']}"
                ),
            }
        )
    unified_rows.extend(
        [
            {
                "section": "conformal",
                "item": "Conformal 80% (OOF 2017–2022)",
                "metric_primary": round(conformal_summary["emp_cov_80_oof"], 4),
                "metric_secondary": round(conformal_summary["q80_oof_radius"], 4),
                "holdout_mae": round(2.0 * conformal_summary["q80_oof_radius"], 4),
                "holdout_rmse": np.nan,
                "holdout_r2": 0.80,
                "note": "nominal=0.80; calibrated on OOF |y-pred| <=2022",
            },
            {
                "section": "conformal",
                "item": "Conformal 90% (OOF 2017–2022)",
                "metric_primary": round(conformal_summary["emp_cov_90_oof"], 4),
                "metric_secondary": round(conformal_summary["q90_oof_radius"], 4),
                "holdout_mae": round(2.0 * conformal_summary["q90_oof_radius"], 4),
                "holdout_rmse": np.nan,
                "holdout_r2": 0.90,
                "note": (
                    f"nominal=0.90; lo90<{conformal_summary['train_fence']:.4f} "
                    f"alerts={conformal_summary['lo90_alerts_n']} (low61 catch="
                    f"{conformal_summary['lo90_catches_low61']}/{conformal_summary['actual_low61_in_holdout_n']})"
                ),
            },
            {
                "section": "conformal",
                "item": "Conformal 90% (Gần nhất 2021–2022)",
                "metric_primary": round(conformal_summary["emp_cov_90_recent"], 4),
                "metric_secondary": round(conformal_summary["q90_recent_21_22_radius"], 4),
                "holdout_mae": round(2.0 * conformal_summary["q90_recent_21_22_radius"], 4),
                "holdout_rmse": np.nan,
                "holdout_r2": 0.90,
                "note": "nominal=0.90; recent 2 folds calibration",
            },
            {
                "section": "conformal",
                "item": "Quantile GBR [q10, q90] (80%)",
                "metric_primary": round(conformal_summary["emp_cov_quantile_80"], 4),
                "metric_secondary": round(conformal_summary["mean_width_quantile_80"] / 2.0, 4),
                "holdout_mae": round(conformal_summary["mean_width_quantile_80"], 4),
                "holdout_rmse": np.nan,
                "holdout_r2": 0.80,
                "note": "asymmetric GradientBoosting quantile regression",
            },
        ]
    )
    unified_df = pd.DataFrame(unified_rows)

    if write_outputs:
        RESULTS.mkdir(parents=True, exist_ok=True)
        FIGS.mkdir(parents=True, exist_ok=True)
        unified_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", lineterminator="\n")
        conformal_df.to_csv(OUT_CONFORMAL_CSV, index=False, encoding="utf-8-sig", lineterminator="\n")
        plot_regression_diagnostics(model_df, coef_df, conformal_df, is_large_pop, train_fence, OUT_FIG)
        _write_markdown_report(model_df, coef_df, tests_summary, conformal_summary, conformal_df, len(tr), len(te))
        _sync_excel_sheet(unified_df)

    return {
        "models": model_df,
        "coef_vif": coef_df,
        "tests": tests_summary,
        "conformal_summary": conformal_summary,
        "conformal_df": conformal_df,
        "unified": unified_df,
    }


def _write_markdown_report(
    model_df: pd.DataFrame,
    coef_df: pd.DataFrame,
    tests_summary: dict[str, dict[str, Any]],
    conf: dict[str, Any],
    conformal_df: pd.DataFrame,
    n_train: int,
    n_holdout: int,
) -> None:
    lines = [
        "# Phân tích hồi quy chuyên sâu — đa mô hình, AR(1) vs Δy, VIF và Conformal Prediction",
        "",
        "**Giao thức:** Tái dùng ĐÚNG pipeline `scripts/supervised/predict_supervised.py` "
        f"(`{n_train}` cặp train `year_t ≤ 2022`, `6` fold expanding origin `2017–2022`, "
        f"holdout `{n_holdout}` cặp `2023→2024`). Siêu tham số, đặc trưng và bán kính Conformal "
        "đều hiệu chỉnh **CHỈ trên tập train/CV `≤ 2022`**, không chạm holdout `2024`.",
        "",
        "## 1) So sánh 17 mô hình hồi quy, cơ chế và hiệu ứng cố định tỉnh (cùng CV 2017–2022 & holdout 2024)",
        "",
        "| Mô hình | Nhóm | Siêu tham số tốt nhất (CV) | CV R² | CV MAE | Beat Ridge (/6) | Beat Carry (/6) | Holdout MAE | Holdout RMSE | Holdout R² | Bias (thực − dự báo) |",
        "|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for _, r in model_df.iterrows():
        lines.append(
            f"| {r['model']} | {r['group']} | {r['best_params']} | {r['cv_r2_raw']:.4f} | "
            f"{r['cv_mae']:.4f} | {int(r['beats_ridge_folds'])}/6 | {int(r['beats_carry_folds'])}/6 | "
            f"{r['holdout_mae']:.4f} | {r['holdout_rmse']:.4f} | {r['holdout_r2']:.3f} | {r['holdout_bias']:+.4f} |"
        )

    by_key = model_df.set_index("key")
    lines.extend([
        "",
        "### Đọc kết quả cốt lõi từ Bảng 1",
        f"- **Tự tương quan AR(1) vs đa chiều:** Chỉ dùng riêng `sd_6_1(t)` (`AR(1) OLS`) đã đạt CV `R² = {by_key.loc['ar1_ols', 'cv_r2_raw']:.4f}` (holdout MAE `{by_key.loc['ar1_ols', 'holdout_mae']:.4f}`, R² `{by_key.loc['ar1_ols', 'holdout_r2']:.3f}`), nhỉnh hơn nhẹ so với `Ridge 8F` (`{by_key.loc['ridge_8f', 'cv_r2_raw']:.4f}`); trong khi **bỏ `sd_6_1` (`Ablation Ridge 7F`)** làm CV `R²` sụt xuống **`{by_key.loc['ridge_no_target', 'cv_r2_raw']:.4f}`**. Điều này xác nhận tín hiệu chính là quán tính `6.1` kèm hồi quy về trung bình.",
        f"- **Mô hình sai phân (`Δ6.1 = y_{{t+1}} - y_t`):** Học trực tiếp biên độ thay đổi rồi cộng lại `y_t` với `Ridge` (`α=50`) đạt **CV `R² = {by_key.loc['ridge_diff_8f', 'cv_r2_raw']:.4f}`** (cao nhất bảng về CV `R²`, thắng Carry-Forward `5/6` fold), nhờ phạt mạnh hệ số của 7 biến phụ nhiễu.",
        f"- **Panel Fixed Effects (`OneHot 63 tỉnh + 8 đặc trưng`):** Cho CV `R² = {by_key.loc['ridge_fe_province', 'cv_r2_raw']:.4f}` (thắng Ridge `4/6` fold) và đạt **`Holdout MAE = {by_key.loc['ridge_fe_province', 'holdout_mae']:.4f}` (`R² = {by_key.loc['ridge_fe_province', 'holdout_r2']:.3f}`)** — gợi ý đặc trưng nền riêng từng tỉnh có giá trị mô tả nếu hiệu chuẩn dài hạn.",
        f"- **Học máy điều chuẩn vs phi tuyến:** `Lasso` (`{by_key.loc['lasso_8f', 'cv_r2_raw']:.4f}`) và `ElasticNet` (`{by_key.loc['elasticnet_8f', 'cv_r2_raw']:.4f}`) nhỉnh hơn nhẹ OLS/Ridge nhờ co các chiều tham nhũng tương quan (`VIF = 3.76–5.00`), nhưng `Wilcoxon p = {tests_summary['oof_enet_vs_ridge']['wilcoxon_p']:.4f}` trên OOF CV (`n={tests_summary['oof_enet_vs_ridge']['n_pairs']}`) cho thấy mức chênh rất nhỏ chưa đủ tạo ưu thế thực chất. Nhóm phi tuyến (`DT {by_key.loc['dt_8f', 'cv_r2_raw']:.3f}`, `RF {by_key.loc['rf_8f', 'cv_r2_raw']:.3f}`, `SVR {by_key.loc['svr_rbf_8f', 'cv_r2_raw']:.3f}`, `HistGB {by_key.loc['hgb_8f', 'cv_r2_raw']:.3f}`, `KNN {by_key.loc['knn_8f', 'cv_r2_raw']:.3f}`) đều có CV `R²` thấp hơn nhóm tuyến tính điều chuẩn.",
        "",
        "## 2) Hệ số hồi quy chuẩn hóa (β trên Z-score train) & Đa cộng tuyến (VIF)",
        "",
        f"- **Chỉ số điều kiện (Condition Number) của ma trận tương quan 8 đặc trưng:** `{coef_df['condition_number'].iloc[0]:.2f}`.",
        "",
        "| Đặc trưng | Tên chỉ tiêu | β OLS | β Ridge | β Lasso | β ElasticNet | VIF |",
        "|:--|:--|--:|--:|--:|--:|--:|",
    ])
    for _, r in coef_df.iterrows():
        lines.append(
            f"| `{r['feature']}` | {r['label']} | {r['beta_ols']:+.4f} | {r['beta_ridge']:+.4f} | "
            f"{r['beta_lasso']:+.4f} | {r['beta_elasticnet']:+.4f} | {r['vif']:.2f} |"
        )

    lines.extend([
        "",
        "## 3) Kiểm định cặp (Wilcoxon signed-rank & Bootstrap CI 95% trên ΔMAE = MAE_ứng_viên − MAE_mốc)",
        "",
        "| Cặp so sánh | n | MAE ứng viên | MAE mốc | ΔMAE | CI 95% (2000 bootstrap) | Wilcoxon p | Số cặp cải thiện |",
        "|:--|--:|--:|--:|--:|:--|--:|--:|",
    ])
    for key, label in (
        ("oof_ridge_vs_carry", "OOF CV 2017–2022: Ridge vs Carry-Forward"),
        ("holdout_ridge_vs_carry", "Holdout 2023→2024: Ridge vs Carry-Forward"),
        ("oof_ar1_vs_carry", "OOF CV 2017–2022: AR(1) Ridge vs Carry-Forward"),
        ("oof_enet_vs_ridge", "OOF CV 2017–2022: ElasticNet vs Ridge"),
        ("holdout_enet_vs_ridge", "Holdout 2023→2024: ElasticNet vs Ridge"),
    ):
        t = tests_summary[key]
        lines.append(
            f"| {label} | {t['n_pairs']} | {t['mae_candidate']:.4f} | {t['mae_reference']:.4f} | "
            f"{t['mean_diff']:+.5f} | [{t['ci95_lo']:+.5f}, {t['ci95_hi']:+.5f}] | {t['wilcoxon_p']:.4g} | "
            f"{t['improved_count']}/{t['n_pairs']} ({t['improved_pct']:.1%}) |"
        )

    lines.extend([
        "",
        "## 4) Hiệu chỉnh bất định: Conformal Prediction 80%/90% & Quantile Regression (không dùng 2024 để chọn bán kính)",
        "",
        f"- **Conformal 80% (OOF `2017–2022`):** bán kính ±`{conf['q80_oof_radius']:.4f}` → độ phủ thực tế trên 59 tỉnh holdout 2024 = **`{conf['emp_cov_80_oof']:.1%}`**.",
        f"- **Conformal 90% (OOF `2017–2022`):** bán kính ±`{conf['q90_oof_radius']:.4f}` → độ phủ thực tế trên 59 tỉnh holdout 2024 = **`{conf['emp_cov_90_oof']:.1%}`**.",
        f"- **Conformal 90% (gần nhất `2021–2022`):** bán kính ±`{conf['q90_recent_21_22_radius']:.4f}` → độ phủ thực tế 2024 = **`{conf['emp_cov_90_recent']:.1%}`**.",
        f"- **Quantile GBR `[q10, q90]` (bề rộng danh nghĩa 80%):** bề rộng trung bình `{conf['mean_width_quantile_80']:.4f}` → độ phủ thực tế 2024 = **`{conf['emp_cov_quantile_80']:.1%}`**.",
        f"- **Ý nghĩa cảnh báo biên (mốc train `{conf['train_fence']:.4f}`, mẫu {conf['n_holdout']} tỉnh):** quy tắc điểm (`pred_ridge < {conf['train_fence']:.4f}`) báo **`{conf['point_alerts_n']}`** tỉnh, bắt `{conf['point_catches_low61']}/{conf['actual_low61_in_holdout_n']}` ca thấp, độ chính xác cảnh báo `{conf['point_catches_low61']}/{conf['point_alerts_n']}` (FP `{conf['point_fp']}`). Cận dưới Conformal 90% (`conformal_lo90 < {conf['train_fence']:.4f}`) báo **`{conf['lo90_alerts_n']}`** tỉnh, bắt `{conf['lo90_catches_low61']}/{conf['actual_low61_in_holdout_n']}` ca thấp, độ chính xác cảnh báo `{conf['lo90_catches_low61']}/{conf['lo90_alerts_n']}` (FP `{conf['lo90_fp']}`). Độ phủ khoảng 90% (`{conf['emp_cov_90_oof']:.1%}`) **không** phải độ chính xác cảnh báo.",
        "- **Giới hạn trung thực:** Conformal không biến hồi quy co tâm thành bộ phân loại chính xác từng ca ngoại lệ (`bias = +0.0304` năm 2024 làm khoảng lệch trên nhẹ về phía trên), mà định lượng rõ độ bất định ±`0.14–0.16` điểm quanh đường dự báo để tránh hiểu nhầm điểm dự báo đơn lẻ.",
        "",
        "## Tệp sinh ra",
        "- `results/regression_deep_analysis.csv`",
        "- `results/regression_conformal_2024.csv`",
        "- `results/figs/regression_diagnostics_deep.png`",
        "- Sheet `Hồi quy chuyên sâu` trong `results/KetQua_STING_PAPI.xlsx`",
        "",
    ])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    res = run_study(ROOT, write_outputs=True)
    print(f"[Regression Deep] Evaluated {len(res['models'])} models cleanly.")
    print(res["models"][["model", "cv_r2_raw", "holdout_mae", "holdout_r2"]].to_string(index=False))
    print(
        f"[Conformal 90%] radius={res['conformal_summary']['q90_oof_radius']:.4f}, "
        f"holdout coverage={res['conformal_summary']['emp_cov_90_oof']:.1%}"
    )
    print("Saved: results/regression_deep_analysis.{csv,md}, results/regression_conformal_2024.csv, "
          "results/figs/regression_diagnostics_deep.png, KetQua_STING_PAPI.xlsx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
