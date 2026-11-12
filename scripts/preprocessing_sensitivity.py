"""Độ nhạy tiền xử lý (imputation, winsorize) — CHỈ trên CV, không đổi protocol công bố.

So sánh ba biến thể trên CÙNG fold expanding origin 2017–2022 (warm-up 2011–2016):
  A — dropna đặc trưng như ``predict_supervised.py`` (baseline công bố);
  B — ``SimpleImputer(median)`` trong Pipeline, giữ dòng thiếu đặc trưng;
  C — winsorize z=3 theo thống kê fold-train, clip fold-test bằng biên train.

Mô hình: Ridge (lưới alpha công bố); logistic regression + Gaussian NB (cài đặt học phần).
Holdout 2023→2024 chỉ báo cáo một cột riêng, không dùng chọn.

Chạy: ``python -W error scripts/preprocessing_sensitivity.py``
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import f1_score, r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from course_supervised_baselines import (  # noqa: E402
    CLASSIFICATION_SCORER,
    MODEL_GAUSSIAN_NB,
    MODEL_LOGISTIC,
    SEED,
    _cv_spread_columns,
    _grid_best_fold_scores,
)
from papi_pred_common import (  # noqa: E402
    REGRESSION_TARGET,
    ROOT as REPO_ROOT,
    load_config,
    load_panel,
)
from predict_supervised import (  # noqa: E402
    CLASSIFICATION_CV_FIRST_YEAR,
    FEATURES,
    HOLDOUT_YEAR,
    build_classification_pairs,
    build_regression_pairs,
    expanding_origin_folds,
    expanding_year_splits,
    predict_sting_labels_for_origin,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS = REPO_ROOT / "results"
CSV_PATH = RESULTS / "preprocessing_sensitivity.csv"
MD_PATH = RESULTS / "preprocessing_sensitivity.md"

METRIC_REG = "r2 (expanding origin 2017–2022)"
METRIC_CLF = "f1_macro (expanding origin 2017–2022)"

PUBLISHED_GATE = {
    ("regression", "ridge", "A"): 0.265,
    ("classification", MODEL_LOGISTIC, "A"): 0.434,
    ("classification", MODEL_GAUSSIAN_NB, "A"): 0.514,
}

VARIANTS = ("A", "B", "C")
WINSOR_Z = 3.0

CSV_COLUMNS = (
    "task",
    "model",
    "variant",
    "metric_cv",
    "value_cv",
    "cv_std",
    "n_train_pairs",
    "delta_vs_A",
    "verdict",
    "holdout_value",
)


class TrainFoldWinsorizer(BaseEstimator, TransformerMixin):
    """Winsorize theo z-score: fit mean/std trên fold-train, clip ±z trên mọi tập."""

    def __init__(self, z: float = WINSOR_Z) -> None:
        self.z = float(z)

    def fit(self, X, y=None):  # noqa: ANN001, D102
        X = np.asarray(X, dtype=float)
        self.mean_ = np.nanmean(X, axis=0)
        self.std_ = np.nanstd(X, axis=0, ddof=0)
        self.std_[self.std_ == 0] = 1.0
        self.lower_ = self.mean_ - self.z * self.std_
        self.upper_ = self.mean_ + self.z * self.std_
        return self

    def transform(self, X):  # noqa: ANN001, D102
        X = np.asarray(X, dtype=float)
        return np.clip(X, self.lower_, self.upper_)


def build_regression_pairs_keep_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Cặp hồi quy giữ dòng thiếu đặc trưng năm t (chỉ bỏ khi thiếu đích t+1)."""
    if df.duplicated(["province_code", "year"]).any():
        raise ValueError("Panel có province_code/year trùng; không thể ghép cặp an toàn.")
    base = df[["province_code", "year"] + FEATURES].copy()
    rows: list[dict[str, Any]] = []
    for t in range(2011, 2024):
        cur = base[base.year == t]
        nxt = base[base.year == t + 1].set_index("province_code")
        for _, r in cur.iterrows():
            pc = int(r["province_code"])
            if pc not in nxt.index or pd.isna(nxt.loc[pc, REGRESSION_TARGET]):
                continue
            rows.append(
                {
                    "year_t": t,
                    **{c: float(r[c]) if pd.notna(r[c]) else np.nan for c in FEATURES},
                    "carry": float(r[REGRESSION_TARGET]) if pd.notna(r[REGRESSION_TARGET]) else np.nan,
                    "y": float(nxt.loc[pc, REGRESSION_TARGET]),
                }
            )
    frame = pd.DataFrame(rows)
    return frame.dropna(subset=["y"])


def build_classification_pairs_keep_missing(
    df: pd.DataFrame, feats: list[str], sting_params: dict
) -> pd.DataFrame:
    """Cặp phân loại giữ thiếu đặc trưng năm t (nhãn STING vẫn cần đủ feat để gán)."""
    if df.duplicated(["province_code", "year"]).any():
        raise ValueError("Panel có province_code/year trùng; không thể ghép cặp an toàn.")
    rows: list[dict[str, Any]] = []
    years = sorted(int(year) for year in df.year.dropna().unique())
    for t in years:
        if t + 1 not in years:
            continue
        labels = predict_sting_labels_for_origin(df, t, feats, sting_params)
        cur = df[df.year == t]
        for _, r in cur.iterrows():
            pc = int(r["province_code"])
            if pc not in labels:
                continue
            rows.append(
                {
                    "year_t": t,
                    **{c: float(r[c]) if pd.notna(r[c]) else np.nan for c in FEATURES},
                    "y": int(labels[pc] != -1),
                }
            )
    return pd.DataFrame(rows).dropna(subset=["y"])


def _regression_fold_scores(grid: GridSearchCV, n_folds: int) -> np.ndarray:
    best_index = int(grid.best_index_)
    res = grid.cv_results_
    return np.asarray(
        [float(res[f"split{i}_test_score"][best_index]) for i in range(n_folds)],
        dtype=float,
    )


def _make_regression_pipeline(variant: str) -> tuple[Pipeline, dict[str, list[float]]]:
    steps: list[tuple[str, Any]] = []
    if variant == "B":
        steps.append(("impute", SimpleImputer(strategy="median")))
    elif variant == "C":
        steps.append(("winsor", TrainFoldWinsorizer(z=WINSOR_Z)))
    steps.extend([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))])
    pipe = Pipeline(steps)
    grid = {"m__alpha": [0.1, 1.0, 10.0]}
    return pipe, grid


def _make_classification_pipeline(
    model_name: str, variant: str
) -> tuple[Pipeline, dict[str, Any]]:
    steps: list[tuple[str, Any]] = []
    if variant == "B":
        steps.append(("impute", SimpleImputer(strategy="median")))
    elif variant == "C":
        steps.append(("winsor", TrainFoldWinsorizer(z=WINSOR_Z)))
    steps.append(("sc", StandardScaler()))
    if model_name == MODEL_LOGISTIC:
        steps.append(
            ("clf", LogisticRegression(max_iter=3000, random_state=SEED))
        )
        grid = {"clf__C": [0.1, 0.3, 1.0]}
    elif model_name == MODEL_GAUSSIAN_NB:
        steps.append(("clf", GaussianNB()))
        grid = {}
    else:
        raise ValueError(f"Model không hỗ trợ: {model_name}")
    return Pipeline(steps), grid


def _holdout_regression(y: np.ndarray, yp: np.ndarray) -> float:
    return round(float(r2_score(y, yp)), 3)


def _holdout_classification(y: np.ndarray, yp: np.ndarray) -> float:
    return round(
        float(
            f1_score(y, yp, average="macro", labels=[0, 1], zero_division=0)
        ),
        3,
    )


def _verdict(delta: float, cv_std_a: float) -> str:
    if np.isnan(delta) or np.isnan(cv_std_a):
        return "không khác biệt"
    if abs(delta) < cv_std_a:
        return "không khác biệt"
    return "khác biệt đáng kể"


def run_sensitivity() -> pd.DataFrame:
    """Chạy toàn bộ lưới task × model × variant; trả DataFrame đã làm tròn."""
    df = load_panel()
    cfg = load_config()

    pairs_reg_a = build_regression_pairs(df)
    pairs_reg_b = build_regression_pairs_keep_missing(df)
    pairs_clf_a = build_classification_pairs(df, cfg["features"], cfg["sting"])
    pairs_clf_b = build_classification_pairs_keep_missing(
        df, cfg["features"], cfg["sting"]
    )

    rows: list[dict[str, Any]] = []
    baseline_cv: dict[tuple[str, str], tuple[float, float]] = {}

    def run_regression(variant: str) -> None:
        pairs = pairs_reg_a if variant in ("A", "C") else pairs_reg_b
        train = pairs[pairs.year_t < HOLDOUT_YEAR].reset_index(drop=True)
        holdout = pairs[pairs.year_t == HOLDOUT_YEAR]
        Xtr, ytr = train[FEATURES].to_numpy(dtype=float), train["y"].to_numpy(dtype=float)
        Xte, yte = holdout[FEATURES].to_numpy(dtype=float), holdout["y"].to_numpy(dtype=float)
        reg_cv = expanding_origin_folds(
            train["year_t"].to_numpy(), first_validation_origin=CLASSIFICATION_CV_FIRST_YEAR
        )
        pipe, grid = _make_regression_pipeline(variant)
        search = GridSearchCV(pipe, grid, cv=reg_cv, scoring="r2", n_jobs=1)
        search.fit(Xtr, ytr)
        fold_scores = _regression_fold_scores(search, len(reg_cv))
        spread = _cv_spread_columns(fold_scores)
        value_cv = round(float(search.best_score_), 3)
        cv_std = spread["cv_std"]
        holdout_v = _holdout_regression(yte, search.best_estimator_.predict(Xte))
        key = ("regression", "ridge")
        delta = 0.0 if variant == "A" else value_cv - baseline_cv[key][0]
        if variant == "A":
            baseline_cv[key] = (value_cv, float(cv_std))
        verdict = "—" if variant == "A" else _verdict(delta, baseline_cv[key][1])
        rows.append(
            {
                "task": "regression",
                "model": "ridge",
                "variant": variant,
                "metric_cv": METRIC_REG,
                "value_cv": value_cv,
                "cv_std": cv_std,
                "n_train_pairs": int(len(train)),
                "delta_vs_A": round(float(delta), 3) if variant != "A" else 0.0,
                "verdict": verdict,
                "holdout_value": holdout_v,
            }
        )

    def run_classification(model_name: str, variant: str) -> None:
        pairs = pairs_clf_a if variant in ("A", "C") else pairs_clf_b
        train = pairs[pairs.year_t < HOLDOUT_YEAR].reset_index(drop=True)
        holdout = pairs[pairs.year_t == HOLDOUT_YEAR]
        Xtr, ytr = train[FEATURES].to_numpy(dtype=float), train["y"].to_numpy(dtype=int)
        Xte, yte = holdout[FEATURES].to_numpy(dtype=float), holdout["y"].to_numpy(dtype=int)
        clf_cv = expanding_year_splits(train["year_t"].to_numpy(), ytr)
        pipe, grid = _make_classification_pipeline(model_name, variant)
        search = GridSearchCV(
            pipe, grid, cv=clf_cv, scoring=CLASSIFICATION_SCORER, n_jobs=1
        )
        search.fit(Xtr, ytr)
        fold_scores = _grid_best_fold_scores(search)
        spread = _cv_spread_columns(fold_scores)
        value_cv = round(float(search.best_score_), 3)
        cv_std = spread["cv_std"]
        holdout_v = _holdout_classification(yte, search.best_estimator_.predict(Xte))
        key = ("classification", model_name)
        delta = 0.0 if variant == "A" else value_cv - baseline_cv[key][0]
        if variant == "A":
            baseline_cv[key] = (value_cv, float(cv_std))
        verdict = "—" if variant == "A" else _verdict(delta, baseline_cv[key][1])
        rows.append(
            {
                "task": "classification",
                "model": model_name,
                "variant": variant,
                "metric_cv": METRIC_CLF,
                "value_cv": value_cv,
                "cv_std": cv_std,
                "n_train_pairs": int(len(train)),
                "delta_vs_A": round(float(delta), 3) if variant != "A" else 0.0,
                "verdict": verdict,
                "holdout_value": holdout_v,
            }
        )

    for variant in VARIANTS:
        run_regression(variant)
    for model_name in (MODEL_LOGISTIC, MODEL_GAUSSIAN_NB):
        for variant in VARIANTS:
            run_classification(model_name, variant)

    return pd.DataFrame(rows)[list(CSV_COLUMNS)]


def verify_published_gate(frame: pd.DataFrame) -> bool:
    ok = True
    for key, expected in PUBLISHED_GATE.items():
        task, model, variant = key
        row = frame[
            (frame.task == task)
            & (frame.model == model)
            & (frame.variant == variant)
        ]
        if row.empty:
            print(f"[Gate] Thiếu dòng {key}")
            ok = False
            continue
        got = float(row.iloc[0]["value_cv"])
        match = round(got, 3) == expected
        ok = ok and match
        print(
            f"[Gate] {task}/{model}/{variant}: CV={got:.3f} "
            f"(công bố {expected}) → {'KHỚP' if match else 'LỆCH'}"
        )
    return ok


def write_markdown(frame: pd.DataFrame) -> None:
    lines = [
        "# Độ nhạy tiền xử lý trên CV (tham khảo)",
        "",
        "So sánh biến thể A (dropna như công bố), B (impute median trong Pipeline), "
        "C (winsorize z=3 theo fold-train) trên cùng fold expanding origin 2017–2022.",
        "",
        frame.to_markdown(index=False),
        "",
        "## Cách đọc",
        "- `value_cv` / `cv_std`: metric CV và độ lệch fold-to-fold của cấu hình được chọn.",
        "- `delta_vs_A` so với biến thể A; `verdict` mô tả: "
        "«không khác biệt» khi |delta| < cv_std của A, ngược lại «khác biệt đáng kể».",
        "- `holdout_value`: R² holdout (hồi quy) hoặc macro-F1 holdout (phân loại); "
        "không dùng để chọn biến thể.",
        "",
        "## Lưu ý (bốn điểm)",
        "1. Phân tích **mang tính khám phá** — không thay `build_regression_pairs` / "
        "pipeline công bố đã đóng băng.",
        "2. Nhãn phân loại do STING gán theo cutoff; **hai fold CV cuối** có thể "
        "chồng lấn thông tin với cùng bộ tham số STING đóng băng.",
        "3. **Không có nested CV** — lưới siêu tham số và tiền xử lý được đánh giá "
        "trên cùng các fold expanding (giống script gốc).",
        "4. Holdout 2023→2024 **không** tham gia chọn imputation hay winsorize; "
        "chỉ báo cáo minh họa.",
    ]
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def csv_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    frame = run_sensitivity()
    if not verify_published_gate(frame):
        print("[Gate] Biến thể A không tái lập số công bố — thoát 1, không ghi tệp.")
        return 1
    frame.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    write_markdown(frame)
    print("\n" + frame.to_string(index=False))
    print(f"\n[OK] {CSV_PATH}")
    print(f"[OK] {MD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
