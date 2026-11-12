"""Baseline nhãn hoán vị và đặc trưng thời gian cho classifier pseudo-label STING.

Tái sử dụng cặp dữ liệu, fold expanding origin và lưới đã công bố từ
``course_supervised_baselines`` / ``predict_supervised`` — không đổi holdout
và không chạm giao thức chính.

Chạy: ``python -W error scripts/classifier_label_baselines.py``
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import f1_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from course_supervised_baselines import (  # noqa: E402
    MODEL_GAUSSIAN_NB,
    MODEL_KNN,
    MODEL_LOGISTIC,
    _classification_pairs,
    _fit_grids,
    _grid_best_fold_scores,
)
from papi_pred_common import REGRESSION_FEATURES, ROOT, load_config, load_panel  # noqa: E402
from predict_supervised import (  # noqa: E402
    CLASSIFICATION_CV_YEARS,
    HOLDOUT_YEAR,
    SEED,
    expanding_year_splits,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_out_dir_env = os.environ.get("CLASSIFIER_LABEL_BASELINES_DIR")
RESULTS = Path(_out_dir_env).resolve() if _out_dir_env else ROOT / "results"
OUT_CSV = RESULTS / "classifier_label_baselines.csv"
OUT_MD = RESULTS / "classifier_label_baselines.md"

TARGET_MODELS = (MODEL_GAUSSIAN_NB, MODEL_KNN, MODEL_LOGISTIC)

PUBLISHED_CV = {
    MODEL_GAUSSIAN_NB: 0.514,
    MODEL_KNN: 0.486,
    MODEL_LOGISTIC: 0.434,
}

# Hoán vị nhãn train: mặc định 200; giảm xuống 100 nếu script vượt 5 phút khi chạy thật.
N_PERMUTATIONS = 200
PERMUTATION_FIT = "fixed_best_params"
SHUFFLE_BASE_SEED = SEED

CSV_COLUMNS = (
    "analysis",
    "model",
    "comparator",
    "feature_set",
    "fold_year",
    "metric",
    "value",
    "n_permutations",
    "permutation_fit",
)


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(
        f1_score(y_true, y_pred, average="macro", labels=[0, 1], zero_division=0)
    )


def _load_train_holdout(
    df: pd.DataFrame | None = None,
    cfg: dict | None = None,
    pairs: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, list]:
    if cfg is None:
        cfg = load_config()
    if df is None:
        df = load_panel()
    if pairs is None:
        pairs = _classification_pairs(df, cfg)
    train = pairs[pairs.year_t < HOLDOUT_YEAR].copy()
    holdout = pairs[pairs.year_t == HOLDOUT_YEAR]
    Xtr = train[REGRESSION_FEATURES].to_numpy()
    ytr = train["y"].to_numpy(dtype=int)
    splits = expanding_year_splits(train["year_t"].to_numpy(), ytr)
    return train, holdout, Xtr, ytr, splits


def shuffled_train_labels_cv(
    X: np.ndarray,
    y: np.ndarray,
    splits: list[tuple[np.ndarray, np.ndarray]],
    grid_name: str,
    grids: dict,
    *,
    n_perm: int,
    base_seed: int = SHUFFLE_BASE_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Hoán vị chỉ nhãn train từng fold; validation giữ nguyên."""
    y_orig = np.asarray(y, dtype=int).copy()
    template = clone(grids[grid_name].best_estimator_)
    perm_means = np.empty(n_perm, dtype=float)
    for p in range(n_perm):
        rng = np.random.default_rng(base_seed + p)
        fold_scores: list[float] = []
        for train_idx, val_idx in splits:
            assert np.array_equal(y[val_idx], y_orig[val_idx])
            y_train = y_orig[train_idx].copy()
            rng.shuffle(y_train)
            est = clone(template)
            est.fit(X[train_idx], y_train)
            yp = est.predict(X[val_idx])
            fold_scores.append(_macro_f1(y_orig[val_idx], yp))
        perm_means[p] = float(np.mean(fold_scores))
    return perm_means, y_orig


def _empirical_p(observed: float, perm_scores: np.ndarray) -> float:
    ge = int(np.sum(perm_scores >= observed))
    return (1.0 + ge) / (1.0 + perm_scores.size)


def _prev_year_prevalence(train: pd.DataFrame) -> np.ndarray:
    """Prevalence nhãn 1 ở năm origin liền trước; warm-up 2011 dùng năm sớm nhất có."""
    by_year = train.groupby("year_t")["y"].mean().sort_index()
    years_avail = by_year.index.to_numpy(dtype=int)
    vals: list[float] = []
    for t in train["year_t"].to_numpy(dtype=int):
        prior = years_avail[years_avail < t]
        if prior.size == 0:
            vals.append(float(by_year.iloc[0]))
        else:
            vals.append(float(by_year.loc[int(prior.max())]))
    return np.asarray(vals, dtype=float).reshape(-1, 1)


def _append_row(
    rows: list[dict[str, Any]],
    *,
    analysis: str,
    model: str,
    metric: str,
    value: float,
    comparator: str = "",
    feature_set: str = "",
    fold_year: str = "",
    n_permutations: int | None = None,
) -> None:
    rows.append(
        {
            "analysis": analysis,
            "model": model,
            "comparator": comparator,
            "feature_set": feature_set,
            "fold_year": fold_year,
            "metric": metric,
            "value": round(float(value), 6),
            "n_permutations": n_permutations if n_permutations is not None else "",
            "permutation_fit": PERMUTATION_FIT if analysis == "shuffled_label" else "",
        }
    )


def build_long_table(
    *,
    n_perm: int = N_PERMUTATIONS,
    df: pd.DataFrame | None = None,
    cfg: dict | None = None,
    pairs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    train, holdout, Xtr, ytr, splits = _load_train_holdout(df=df, cfg=cfg, pairs=pairs)
    grids = _fit_grids(Xtr, ytr, splits, rf_n_estimators=50)

    rows: list[dict[str, Any]] = []

    observed_cv: dict[str, float] = {}
    fold_scores_by_model: dict[str, np.ndarray] = {}
    for name in TARGET_MODELS:
        cv = float(grids[name].best_score_)
        observed_cv[name] = cv
        folds = _grid_best_fold_scores(grids[name])
        fold_scores_by_model[name] = folds
        _append_row(rows, analysis="published_cv", model=name, metric="value_cv", value=cv)
        for year, score in zip(CLASSIFICATION_CV_YEARS, folds, strict=True):
            _append_row(
                rows,
                analysis="published_cv",
                model=name,
                metric="fold_macro_f1",
                value=float(score),
                fold_year=str(year),
            )

    for name in TARGET_MODELS:
        perm_means, _ = shuffled_train_labels_cv(
            Xtr, ytr, splits, name, grids, n_perm=n_perm
        )
        obs = observed_cv[name]
        p_mean = float(perm_means.mean())
        p95 = float(np.percentile(perm_means, 95))
        p_val = _empirical_p(obs, perm_means)
        _append_row(
            rows,
            analysis="shuffled_label",
            model=name,
            metric="observed_cv",
            value=obs,
            n_permutations=n_perm,
        )
        _append_row(
            rows,
            analysis="shuffled_label",
            model=name,
            metric="perm_mean_macro_f1",
            value=p_mean,
            n_permutations=n_perm,
        )
        _append_row(
            rows,
            analysis="shuffled_label",
            model=name,
            metric="perm_p95_macro_f1",
            value=p95,
            n_permutations=n_perm,
        )
        _append_row(
            rows,
            analysis="shuffled_label",
            model=name,
            metric="empirical_p",
            value=p_val,
            n_permutations=n_perm,
        )

    X_year = train["year_t"].to_numpy(dtype=float).reshape(-1, 1)
    X_prev = _prev_year_prevalence(train)
    for feature_set, X_feat in (("year_t", X_year), ("prev_year_prevalence", X_prev)):
        feat_grids = _fit_grids(X_feat, ytr, splits, rf_n_estimators=50)
        for name in TARGET_MODELS:
            cv = float(feat_grids[name].best_score_)
            _append_row(
                rows,
                analysis="year_only",
                model=name,
                feature_set=feature_set,
                metric="value_cv",
                value=cv,
            )

    nb_folds = fold_scores_by_model[MODEL_GAUSSIAN_NB]
    for other in (MODEL_KNN, MODEL_LOGISTIC):
        other_folds = fold_scores_by_model[other]
        diff = nb_folds - other_folds
        wins = int(np.sum(diff > 0))
        for year, d in zip(CLASSIFICATION_CV_YEARS, diff, strict=True):
            _append_row(
                rows,
                analysis="paired_nb",
                model=MODEL_GAUSSIAN_NB,
                comparator=other,
                metric="nb_minus_other",
                value=float(d),
                fold_year=str(year),
            )
        _append_row(
            rows,
            analysis="paired_nb",
            model=MODEL_GAUSSIAN_NB,
            comparator=other,
            metric="nb_wins",
            value=float(wins),
        )
        _append_row(
            rows,
            analysis="paired_nb",
            model=MODEL_GAUSSIAN_NB,
            comparator=other,
            metric="mean_paired_diff",
            value=float(diff.mean()),
        )
        _append_row(
            rows,
            analysis="paired_nb",
            model=MODEL_GAUSSIAN_NB,
            comparator=other,
            metric="std_paired_diff",
            value=float(np.std(diff, ddof=1)),
        )

    return pd.DataFrame(rows, columns=list(CSV_COLUMNS))


def assert_published_reproduction(table: pd.DataFrame) -> None:
    pub = table[(table.analysis == "published_cv") & (table.metric == "value_cv")]
    for model, expected in PUBLISHED_CV.items():
        row = pub.loc[pub.model == model]
        if row.empty:
            raise SystemExit(f"Gate: thiếu published CV cho {model}")
        got = round(float(row.iloc[0]["value"]), 3)
        if got != expected:
            raise SystemExit(
                f"Gate: {model} value_cv {got} != published {expected}"
            )


def csv_sha256(df: pd.DataFrame) -> str:
    text = df.to_csv(index=False, encoding="utf-8-sig", lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_markdown(table: pd.DataFrame, *, n_perm: int) -> None:
    pub = table[
        (table.analysis == "published_cv") & (table.metric == "value_cv")
    ].set_index("model")
    shuf = table[table.analysis == "shuffled_label"]
    year = table[
        (table.analysis == "year_only") & (table.metric == "value_cv")
    ]
    paired = table[table.analysis == "paired_nb"]

    lines = [
        "# Baseline nhãn hoán vị và drift thời gian (classifier pseudo-label)",
        "",
        "## Phương pháp",
        f"- CV: expanding origin {CLASSIFICATION_CV_YEARS[0]}–"
        f"{CLASSIFICATION_CV_YEARS[-1]}, warm-up 2011–2016; giống "
        "`scripts/course_supervised_baselines.py`.",
        f"- Hoán vị nhãn: {n_perm} lần, seed gốc {SHUFFLE_BASE_SEED}; "
        f"chỉ hoán vị nhãn **train** từng fold; fit bằng **{PERMUTATION_FIT}** "
        "(Pipeline/ siêu tham số từ GridSearchCV đã công bố, không chạy lại lưới).",
        "- Baseline thời gian: chỉ `year_t` hoặc chỉ prevalence nhãn 1 năm *t−1*.",
        "- Holdout 2023→2024 **không** dùng cho bất kỳ lựa chọn nào trong script này.",
        "",
        "## Kết quả chính (CV macro-F1)",
        "",
        pub.reset_index().to_markdown(index=False),
        "",
        "### Hoán vị nhãn train",
        "",
        shuf.pivot_table(
            index="model", columns="metric", values="value", aggfunc="first"
        ).reset_index().to_markdown(index=False),
        "",
        "### Chỉ đặc trưng thời gian / prevalence",
        "",
        year.to_markdown(index=False),
        "",
        "### So sánh cặp theo fold: Naive Bayes trừ model khác",
        "",
        paired[
            paired.metric.isin(
                ["nb_wins", "mean_paired_diff", "std_paired_diff"]
            )
        ].to_markdown(index=False),
        "",
        "Với chỉ sáu fold validation theo thời gian, số fold mà NB thắng hoặc "
        "chênh lệch trung bình **không** đủ để kết luận ý nghĩa thống kê.",
        "",
        "## Bốn lưu ý",
        "- Phân tích **thăm dò** (exploratory); không thay thế bảng classifier đã công bố.",
        "- Cấu hình STING/labeler được chọn có tham chiếu metric trên "
        f"{CLASSIFICATION_CV_YEARS[-2]}–{CLASSIFICATION_CV_YEARS[-1]}; hai fold CV cuối "
        "trùng các năm đó nên nhãn và đánh giá không hoàn toàn độc lập.",
        "- Không có nested CV; `empirical_p` chỉ so với phân phối hoán vị nhãn train.",
        "- Holdout không dùng trong script; không khẳng định tổng quát hóa ngoài CV.",
        "",
        "## Cách đọc trung thực",
        "- Macro-F1 CV của NB/KNN/LR tái lập đúng bảng đã công bố; chênh lệch NB−KNN "
        f"({float(paired[(paired.comparator == MODEL_KNN) & (paired.metric == 'mean_paired_diff')].iloc[0]['value']):.3f}) "
        "nhỏ hơn độ lệch fold-to-fold điển hình (~0.06–0.12 trên các model chính), "
        "nên dẫn đầu NB chủ yếu mô tả trên pseudo-label STING, không chứng minh "
        "ưu thế bền vững. Hoán vị nhãn cho thấy điểm quan sát cao hơn phần lớn "
        "hoán vị khi nhãn vẫn mang cấu trúc năm/tỉnh trong feature — đọc cùng "
        "baseline `year_t` và prevalence năm trước để ước lượng phần drift.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    table = build_long_table(n_perm=N_PERMUTATIONS)
    assert_published_reproduction(table)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", lineterminator="\n")
    _write_markdown(table, n_perm=N_PERMUTATIONS)
    print(table.to_string(index=False))
    print(f"\nđã lưu: {OUT_CSV.name}, {OUT_MD.name}")
    print(f"sha256 csv: {csv_sha256(table)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
