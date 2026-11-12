"""So sánh classifier theo nội dung học phần trên bài phân loại pseudo-label STING.

Cùng tác vụ và quy trình thời gian với ``scripts/predict_supervised.py`` (bài 2):
dự báo nhãn STING năm t+1 từ chỉ tiêu năm t; CV expanding origin 2017–2022,
warm-up 2011–2016; holdout duy nhất 2023→2024 chỉ để báo cáo.

Chạy: ``python scripts/course_supervised_baselines.py``
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    make_scorer,
)
from sklearn.model_selection import GridSearchCV
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from papi_pred_common import (  # noqa: E402
    REGRESSION_FEATURES,
    ROOT,
    load_config,
    load_panel,
    select_model_by_cv,
)
from predict_supervised import (  # noqa: E402
    FIG_DPI,
    FIG_EXTRA,
    FIG_RETRIEVED,
    FIG_SOURCE,
    HOLDOUT_YEAR,
    SEED,
    build_classification_pairs,
    expanding_majority_f1,
    expanding_year_splits,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"
FEATURES = REGRESSION_FEATURES
METRIC_CV_LABEL = "f1_macro (expanding origin 2017–2022)"

CLASSIFICATION_SCORER = make_scorer(
    f1_score, average="macro", labels=[0, 1], zero_division=0
)

# Tên hiển thị — khớp convention ``predict_supervised.py``.
MODEL_GAUSSIAN_NB = "gaussian naive bayes"
MODEL_KNN = "knn"
MODEL_SVM_LINEAR = "svm (linear)"
MODEL_SVM_RBF = "svm (rbf)"
MODEL_DECISION_TREE = "decision tree"
MODEL_RANDOM_FOREST = "random forest"
MODEL_MAJORITY = "majority (lớp đa số)"
MODEL_LOGISTIC = "logistic regression"

COURSE_MODELS = (
    MODEL_GAUSSIAN_NB,
    MODEL_KNN,
    MODEL_SVM_LINEAR,
    MODEL_SVM_RBF,
    MODEL_DECISION_TREE,
    MODEL_RANDOM_FOREST,
)

# Tiêu đề panel trên hình — đọc được khi chiếu slide (tránh rút gọn kiểu svm-L).
PANEL_TITLES: dict[str, str] = {
    MODEL_GAUSSIAN_NB: "Naive Bayes Gauss",
    MODEL_KNN: "KNN",
    MODEL_SVM_LINEAR: "SVM tuyến tính",
    MODEL_SVM_RBF: "SVM RBF",
    MODEL_DECISION_TREE: "Cây quyết định",
    MODEL_RANDOM_FOREST: "Random forest",
}

CLASS_LEGEND = "0 = ngoại vi (nhiễu STING), 1 = vùng dày"

# Tránh fit STING lặp lại trong cùng một tiến trình (kiểm thử / determinism).
_PAIRS_CACHE: pd.DataFrame | None = None


def _classification_pairs(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    global _PAIRS_CACHE
    if _PAIRS_CACHE is None:
        _PAIRS_CACHE = build_classification_pairs(
            df, cfg["features"], cfg["sting"]
        )
    return _PAIRS_CACHE


def _clf_metrics(y: np.ndarray, yp: np.ndarray, cv_score: float) -> dict[str, Any]:
    return {
        "metric_cv": METRIC_CV_LABEL,
        "value_cv": round(float(cv_score), 3),
        "holdout_acc": round(float(accuracy_score(y, yp)), 3),
        "holdout_macro_f1": round(
            float(
                f1_score(y, yp, average="macro", labels=[0, 1], zero_division=0)
            ),
            3,
        ),
    }


def _fit_grids(
    Xtr: np.ndarray,
    ytr: np.ndarray,
    clf_cv: list[tuple[np.ndarray, np.ndarray]],
    *,
    rf_n_estimators: int = 300,
) -> dict[str, GridSearchCV]:
    """Huấn luyện lưới siêu tham số nhỏ; scaler chỉ fit trên phần train mỗi fold."""
    grids: dict[str, GridSearchCV] = {}

    pipe_gnb = Pipeline([("sc", StandardScaler()), ("clf", GaussianNB())])
    grids[MODEL_GAUSSIAN_NB] = GridSearchCV(
        pipe_gnb, {}, cv=clf_cv, scoring=CLASSIFICATION_SCORER, n_jobs=1
    )

    pipe_knn = Pipeline([("sc", StandardScaler()), ("clf", KNeighborsClassifier())])
    grids[MODEL_KNN] = GridSearchCV(
        pipe_knn,
        {"clf__n_neighbors": [3, 5, 7, 9]},
        cv=clf_cv,
        scoring=CLASSIFICATION_SCORER,
        n_jobs=1,
    )

    pipe_svm_lin = Pipeline(
        [
            ("sc", StandardScaler()),
            ("clf", SVC(kernel="linear", random_state=SEED)),
        ]
    )
    grids[MODEL_SVM_LINEAR] = GridSearchCV(
        pipe_svm_lin,
        {"clf__C": [0.1, 1.0, 10.0]},
        cv=clf_cv,
        scoring=CLASSIFICATION_SCORER,
        n_jobs=1,
    )

    pipe_svm_rbf = Pipeline(
        [
            ("sc", StandardScaler()),
            ("clf", SVC(kernel="rbf", random_state=SEED)),
        ]
    )
    grids[MODEL_SVM_RBF] = GridSearchCV(
        pipe_svm_rbf,
        {"clf__C": [0.1, 1.0, 10.0]},
        cv=clf_cv,
        scoring=CLASSIFICATION_SCORER,
        n_jobs=1,
    )

    pipe_dt = Pipeline(
        [("sc", StandardScaler()), ("clf", DecisionTreeClassifier(random_state=SEED))]
    )
    grids[MODEL_DECISION_TREE] = GridSearchCV(
        pipe_dt,
        {"clf__max_depth": [2, 3, 4, 5]},
        cv=clf_cv,
        scoring=CLASSIFICATION_SCORER,
        n_jobs=1,
    )

    grids[MODEL_RANDOM_FOREST] = GridSearchCV(
        RandomForestClassifier(
            n_estimators=rf_n_estimators, random_state=SEED, n_jobs=1
        ),
        {"max_depth": [3, 6, None], "min_samples_leaf": [1, 2]},
        cv=clf_cv,
        scoring=CLASSIFICATION_SCORER,
        n_jobs=1,
    )

    pipe_lr = Pipeline(
        [
            ("sc", StandardScaler()),
            ("clf", LogisticRegression(max_iter=3000, random_state=SEED)),
        ]
    )
    grids[MODEL_LOGISTIC] = GridSearchCV(
        pipe_lr,
        {"clf__C": [0.1, 0.3, 1.0]},
        cv=clf_cv,
        scoring=CLASSIFICATION_SCORER,
        n_jobs=1,
    )

    for grid in grids.values():
        grid.fit(Xtr, ytr)

    return grids


def build_metrics_table(
    df: pd.DataFrame | None = None,
    cfg: dict | None = None,
    *,
    seed: int = SEED,
    pairs: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, GridSearchCV], np.ndarray, np.ndarray]:
    """Dựng bảng metric và các grid đã fit (dùng cho script chính và kiểm thử)."""
    if cfg is None:
        cfg = load_config()
    if df is None:
        df = load_panel()

    np.random.seed(seed)

    synthetic_pairs = pairs is not None
    if pairs is None:
        pairs = _classification_pairs(df, cfg)
    train = pairs[pairs.year_t < HOLDOUT_YEAR]
    holdout = pairs[pairs.year_t == HOLDOUT_YEAR]
    Xtr, ytr = train[FEATURES].to_numpy(), train["y"].to_numpy()
    Xte, yte = holdout[FEATURES].to_numpy(), holdout["y"].to_numpy()
    clf_cv = expanding_year_splits(train["year_t"].to_numpy(), ytr)
    majority_cv = expanding_majority_f1(ytr, clf_cv)
    maj = int(pd.Series(ytr).mode().iloc[0])

    # Dữ liệu thật: 50 cây (trùng kết quả CSV đã lưu). Synthetic test: ít cây hơn, cùng grid.
    rf_n_estimators = 25 if synthetic_pairs else 50

    grids = _fit_grids(
        Xtr,
        ytr,
        clf_cv,
        rf_n_estimators=rf_n_estimators,
    )

    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "model": MODEL_MAJORITY,
            **_clf_metrics(yte, np.full_like(yte, maj), majority_cv),
        }
    )

    for name, grid in grids.items():
        yp = grid.best_estimator_.predict(Xte)
        rows.append({"model": name, **_clf_metrics(yte, yp, grid.best_score_)})

    metrics = pd.DataFrame(rows)
    return metrics, grids, yte, Xte


def _write_csv(metrics: pd.DataFrame) -> Path:
    out = RESULTS / "course_supervised_baselines.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(out, index=False, encoding="utf-8-sig")
    return out


def _write_markdown(
    metrics: pd.DataFrame,
    n_train: int,
    n_holdout: int,
    yte: np.ndarray,
) -> Path:
    selectable = metrics[~metrics.model.isin([MODEL_MAJORITY])]
    selected = select_model_by_cv(selectable)
    selected_row = metrics.set_index("model").loc[selected]

    lines = [
        "# Baseline classifier theo nội dung học phần (pseudo-label STING)",
        "",
        "## Quy trình",
        "- Nhãn: STING fit tới cutoff năm *t* gán tỉnh năm *t+1* vào **vùng dày** (1) "
        "hay **ngoại vi** (0) — pseudo-label, không phải ground truth khảo sát.",
        "- Đặc trưng: cùng 8 chỉ tiêu sub-dimension năm *t* như "
        "`scripts/predict_supervised.py`.",
        f"- Huấn luyện/CV: expanding origin {min(range(2017, HOLDOUT_YEAR))}–"
        f"{HOLDOUT_YEAR - 1}, warm-up 2011–2016; scaler trong Pipeline, fit chỉ "
        "trên phần train từng fold.",
        f"- Holdout: một lần duy nhất cặp {HOLDOUT_YEAR}→{HOLDOUT_YEAR + 1} "
        f"({n_holdout} tỉnh); **không** dùng để chọn model.",
        "- Chọn model theo macro-F1 CV (cột `value_cv`); so sánh với majority và "
        "logistic regression có sẵn trong repo.",
        "",
        "## Kết quả",
        "",
        metrics.to_markdown(index=False),
        "",
        f"- Model cao nhất theo CV (không tính majority): **{selected}** "
        f"(macro-F1 CV = {selected_row['value_cv']:.3f}).",
        "",
        "## Hình",
        "- **Hình:** `results/figs/course_confusion_matrix.png` — ma trận nhầm lẫn "
        "holdout cho từng classifier học phần.",
        "- Đọc ma trận nhầm lẫn (bài Day 2–3): **hàng** = nhãn STING thực tế, "
        "**cột** = nhãn dự báo; ô trên đường chéo là dự đoán đúng.",
        f"- Cân bằng lớp holdout {HOLDOUT_YEAR}→{HOLDOUT_YEAR + 1}: "
        f"lớp 0 = {int((yte == 0).sum())} tỉnh, "
        f"lớp 1 = {int((yte == 1).sum())} tỉnh "
        f"(baseline majority luôn dự báo lớp chiếm đa số).",
        "",
        "## Cách đọc",
        "- `value_cv`: macro-F1 trung bình trên các fold validation thời gian.",
        "- `holdout_acc` / `holdout_macro_f1`: đánh giá một năm giữ lại; "
        "độ đồng thuận với nhãn STING, không khẳng định độ chính xác "
        "thực tế ngoài đời.",
        "",
        "## Lưu ý",
        "- Một holdout không chứng minh mô hình nào vượt trội tổng quát.",
        "- Nhãn phụ thuộc cấu hình STING đóng băng trong `models/predict_config.json`.",
        f"- Train: {n_train} cặp · Holdout: {n_holdout} cặp.",
    ]
    out = RESULTS / "course_supervised_baselines.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _plot_confusion_grid(
    grids: dict[str, GridSearchCV],
    yte: np.ndarray,
    Xte: np.ndarray,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from fig_style import add_source, new_fig, save_png, style_context

    classes = [0, 1]
    class_tick = [str(c) for c in classes]
    n_models = len(COURSE_MODELS)
    ncols = 3
    nrows = int(np.ceil(n_models / ncols))

    with style_context():
        fig, axes = new_fig(target="slide", nrows=nrows, ncols=ncols)
        axes_flat = np.atleast_1d(axes).ravel()

        for ax, name in zip(axes_flat, COURSE_MODELS, strict=False):
            yp = grids[name].best_estimator_.predict(Xte)
            cm = confusion_matrix(yte, yp, labels=classes)
            im = ax.imshow(cm, cmap="Blues")
            title = PANEL_TITLES.get(name, name)
            ax.set_title(textwrap.fill(title, 22), fontsize=10)
            ax.set_xticks(range(len(classes)), class_tick, fontsize=9)
            ax.set_yticks(range(len(classes)), class_tick, fontsize=9)
            ax.set_xlabel("dự báo", fontsize=9)
            ax.set_ylabel("thực tế", fontsize=9)
            for i in range(len(classes)):
                for j in range(len(classes)):
                    color = (
                        "white"
                        if cm[i, j] >= cm.max() / 2 and cm.max() > 0
                        else "black"
                    )
                    ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)

        for ax in axes_flat[n_models:]:
            ax.set_visible(False)

        fig.suptitle(
            f"Ma trận nhầm lẫn holdout {HOLDOUT_YEAR}→{HOLDOUT_YEAR + 1} "
            f"(pseudo-label STING)\n{CLASS_LEGEND}",
            fontsize=11,
            y=1.03,
        )
        add_source(fig, FIG_SOURCE, retrieved=FIG_RETRIEVED, extra=FIG_EXTRA)
        fig.tight_layout(rect=(0, 0.06, 1, 0.94))
        out = FIGS / "course_confusion_matrix.png"
        save_png(fig, out, dpi=FIG_DPI)
        plt.close(fig)
    return out


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    df = load_panel()
    pairs = _classification_pairs(df, cfg)
    n_train = int((pairs.year_t < HOLDOUT_YEAR).sum())
    n_holdout = int((pairs.year_t == HOLDOUT_YEAR).sum())

    metrics, grids, yte, Xte = build_metrics_table(df, cfg)
    print(metrics.to_string(index=False))

    csv_path = _write_csv(metrics)
    md_path = _write_markdown(metrics, n_train, n_holdout, yte)
    fig_path = _plot_confusion_grid(grids, yte, Xte)

    print(
        f"\nđã lưu: {csv_path.name}, {md_path.name}, {fig_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
