"""Model local CÓ GIÁM SÁT cho PAPI — quy trình ML đầy đủ, chạy hoàn toàn local.

Hai bài toán minh hoạ (khác với `predict_demo.py` — STING.predict không giám sát):

(1) CHÍNH — HỒI QUY dự báo: "6.1 Y tế công lập năm t+1" từ 8 sub-dimension năm t
    trong allowlist đã sàng lọc của pipeline.
    Model: Ridge + RandomForest; đối chứng: carry-forward (giữ nguyên giá trị
    năm nay) và trung bình năm. Chọn model bằng CV train-only expanding origin
    2017–2022, warm-up 2011–2016; metric `r2 (expanding origin 2017–2022)`.
    Holdout 2023 → 2024 chỉ đánh giá MỘT LẦN và không dùng để chọn model.

(2) PHỤ — PHÂN LOẠI pseudo-label: dự báo target năm t+1 có được STING fit
    đến cutoff t gán vào vùng dày hay không. Nhãn cho từng origin được dựng
    riêng theo cutoff; CV expanding theo thời gian. Đây không phải ground truth.

Đầu ra:
  models/sup_ridge.joblib, models/sup_rf.joblib           — model local (joblib)
  models/sup_classifier.joblib                            — classifier được CV chọn (joblib)
  results/supervised_metrics.csv, results/supervised_summary.md
  results/figs/supervised_regression.png                  — dự báo vs thực tế + độ quan trọng
  results/figs/supervised_confusion.png                   — confusion (bài toán 2, model chọn bằng CV)

Chạy: python scripts/predict_supervised.py
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    make_scorer,
)
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sting import STING  # noqa: E402
from papi_pred_common import (
    FEATURE_LABELS,
    PANEL_PATH,
    REGRESSION_FEATURES,
    REGRESSION_TARGET,
    ROOT,
    load_config,
    load_panel,
    select_model_by_cv,
)  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MODELS = ROOT / "models"
RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"
HOLDOUT_YEAR = 2023          # cặp (2023 → 2024) là holdout duy nhất
SEED = 42
CLASSIFICATION_CV_FIRST_YEAR = 2017  # warm-up cố định: origins 2011–2016
CLASSIFICATION_CV_YEARS = tuple(range(CLASSIFICATION_CV_FIRST_YEAR, HOLDOUT_YEAR))
CLASSIFICATION_SCORER = make_scorer(
    f1_score, average="macro", labels=[0, 1], zero_division=0
)

SUBS = REGRESSION_FEATURES
TARGET = REGRESSION_TARGET
FEATURES = REGRESSION_FEATURES

# Dòng nguồn cho hình — theo data/raw/papi/PROVENANCE.md (ngày tải của dữ liệu
# gốc, KHÔNG phải ngày render hình); panel dùng để train là file phái sinh.
FIG_SOURCE = "PAPI — CECODES, VFF-CRT, RTA & UNDP"
FIG_RETRIEVED = "2026-11-03"  # data/raw/papi/PROVENANCE.md
FIG_EXTRA = f"panel phái sinh: {PANEL_PATH.name}"
# DPI khi lưu PNG: chuẩn in là ~300 DPI hiệu dụng ở chiều rộng chữ A4 (~16 cm).
# Sau tight bbox hình còn ~5.9–9 inch, nên dùng 330 DPI để mọi hình của script
# này đạt >= 300 DPI hiệu dụng ở 16 cm khi in (chuẩn in báo cáo).
FIG_DPI = 330
# Tên hiển thị hai lớp pseudo-label của bài toán (2): nhãn sinh trong
# `build_classification_pairs` là `y = int(labels[pc] != -1)` — STING gán điểm
# vào cụm (vùng dày) => 1, còn lại nhãn nhiễu (ngoại vi) => 0. Chỉ là tên
# hiển thị cho ngữ nghĩa đã có trong code, không đổi dữ liệu.
CLASS_NAMES = {0: "ngoại vi", 1: "vùng dày"}


def build_regression_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Cặp (đặc trưng năm t, giá trị đích năm t+1, carry-forward)."""
    if df.duplicated(["province_code", "year"]).any():
        raise ValueError("Panel có province_code/year trùng; không thể ghép cặp an toàn.")
    base = df[["province_code", "year"] + FEATURES].copy()  # TARGET nằm trong FEATURES
    rows = []
    for t in range(2011, 2024):
        cur = base[base.year == t].dropna(subset=FEATURES)
        nxt = base[base.year == t + 1].set_index("province_code")
        for _, r in cur.iterrows():
            pc = int(r["province_code"])
            if pc not in nxt.index or pd.isna(nxt.loc[pc, TARGET]):
                continue
            rows.append(
                {
                    "year_t": t,
                    **{c: float(r[c]) for c in FEATURES},
                    "carry": float(r[TARGET]),
                    "y": float(nxt.loc[pc, TARGET]),
                }
            )
    return pd.DataFrame(rows).dropna()


def expanding_origin_folds(
    origin_years, first_validation_origin: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create expanding folds with one validation origin per year."""
    years = np.asarray(origin_years, dtype=int)
    validation_years = tuple(range(first_validation_origin, HOLDOUT_YEAR))
    present_years = set(years.tolist())
    missing = [year for year in validation_years if year not in present_years]
    if missing:
        raise ValueError(f"Thiếu origin years cho regression CV: {missing}.")

    splits = []
    for validation_year in validation_years:
        train_idx = np.flatnonzero(years < validation_year)
        validation_idx = np.flatnonzero(years == validation_year)
        if train_idx.size == 0:
            raise ValueError(
                f"Không có origin train trước năm validation {validation_year}."
            )
        if validation_idx.size == 0:
            raise ValueError(
                f"Không có dòng validation ở origin {validation_year}."
            )
        splits.append((train_idx, validation_idx))
    return splits


def fit_sting_labeler(
    df: pd.DataFrame, cutoff_year: int, feats, sting_params: dict
):
    """Fit scaler/STING usando đúng dữ liệu có tại cutoff, bao gồm năm origin."""
    if df.duplicated(["province_code", "year"]).any():
        raise ValueError("Panel có province_code/year trùng; không thể tạo nhãn an toàn.")
    history = df[df.year <= cutoff_year].dropna(subset=feats)
    if history.empty:
        raise ValueError(f"Không có feature đủ dữ liệu tới cutoff {cutoff_year}.")
    scaler = StandardScaler().fit(history[feats])
    model = STING(
        n_levels=sting_params["n_levels"],
        factor=sting_params["factor"],
        min_count=sting_params["min_count"],
    ).fit(scaler.transform(history[feats]))
    model.cluster(
        level=sting_params["cluster_level"],
        connectivity=sting_params["connectivity"],
    )
    return scaler, model


def predict_sting_labels_for_origin(
    df: pd.DataFrame, origin_year: int, feats, sting_params: dict
) -> dict[int, int]:
    """Gán nhãn t+1 bằng STING/scaler chỉ fit trên dữ liệu ≤ origin t."""
    scaler, model = fit_sting_labeler(df, origin_year, feats, sting_params)
    target = df[df.year == origin_year + 1].dropna(subset=feats)
    if target.empty:
        return {}
    pred = model.predict(scaler.transform(target[feats]))
    return {
        int(pc): int(label)
        for pc, label in zip(target["province_code"], pred)
    }


def build_classification_pairs(
    df: pd.DataFrame, feats, sting_params: dict
) -> pd.DataFrame:
    """Cặp X(t) → pseudo-label STING(t+1) với labeler fit tới cutoff t."""
    if df.duplicated(["province_code", "year"]).any():
        raise ValueError("Panel có province_code/year trùng; không thể ghép cặp an toàn.")
    rows = []
    years = sorted(int(year) for year in df.year.dropna().unique())
    for t in years:
        if t + 1 not in years:
            continue
        labels = predict_sting_labels_for_origin(df, t, feats, sting_params)
        cur = df[df.year == t].dropna(subset=FEATURES)
        for _, r in cur.iterrows():
            pc = int(r["province_code"])
            if pc not in labels:
                continue
            rows.append(
                {
                    "year_t": t,
                    **{c: float(r[c]) for c in FEATURES},
                    "y": int(labels[pc] != -1),
                }
            )
    return pd.DataFrame(rows).dropna()


def expanding_year_splits(year_t, y) -> list[tuple[np.ndarray, np.ndarray]]:
    """Tạo forward validation theo origin; validation chỉ ở 2017–2022."""
    years = np.asarray(year_t, dtype=int)
    target = np.asarray(y, dtype=int)
    splits = []
    present_years = set(years.tolist())
    missing = [year for year in CLASSIFICATION_CV_YEARS if year not in present_years]
    if missing:
        raise ValueError(f"Thiếu origin years cho classification CV: {missing}.")
    for validation_year in CLASSIFICATION_CV_YEARS:
        train_idx = np.flatnonzero(years < validation_year)
        validation_idx = np.flatnonzero(years == validation_year)
        if np.unique(target[train_idx]).size < 2:
            raise ValueError(
                f"Classification CV tới origin {validation_year} chỉ có một lớp train."
            )
        if validation_idx.size == 0:
            raise ValueError(f"Không có dòng validation ở origin {validation_year}.")
        splits.append((train_idx, validation_idx))
    return splits


def expanding_majority_f1(y, splits) -> float:
    """Macro-F1 baseline dùng mode của riêng training history trong mỗi fold."""
    target = np.asarray(y, dtype=int)
    scores = []
    for train_idx, validation_idx in splits:
        majority = int(pd.Series(target[train_idx]).mode().iloc[0])
        prediction = np.full(validation_idx.size, majority, dtype=int)
        scores.append(
            f1_score(
                target[validation_idx], prediction,
                average="macro", labels=[0, 1], zero_division=0,
            )
        )
    if not scores:
        raise ValueError("Không có fold để tính majority baseline.")
    return float(np.mean(scores))


def main() -> int:
    for d in (MODELS, RESULTS, FIGS):
        d.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    df = load_panel()

    met_rows: list[dict] = []

    # ================================================================== #
    # (1) HỒI QUY: dự báo "6.1 Y tế công lập" năm t+1
    # ================================================================== #
    P = build_regression_pairs(df)
    tr = P[P.year_t < HOLDOUT_YEAR]
    te = P[P.year_t == HOLDOUT_YEAR]
    Xtr, ytr = tr[FEATURES].to_numpy(), tr["y"].to_numpy()
    Xte, yte = te[FEATURES].to_numpy(), te["y"].to_numpy()
    reg_cv = expanding_origin_folds(
        tr["year_t"].to_numpy(), first_validation_origin=CLASSIFICATION_CV_FIRST_YEAR
    )
    print(f"[Hồi quy] train {len(tr)} cặp (2011–2022) · holdout {len(te)} cặp (2023→2024)")

    ridge = Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))])
    rf_reg = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=1)
    grid_ridge = GridSearchCV(
        ridge, {"m__alpha": [0.1, 1.0, 10.0]}, cv=reg_cv, scoring="r2", n_jobs=1
    )
    grid_rf = GridSearchCV(
        rf_reg,
        {"max_depth": [4, 6, None], "min_samples_leaf": [1, 2]},
        cv=reg_cv, scoring="r2", n_jobs=1,
    )
    grid_ridge.fit(Xtr, ytr)
    grid_rf.fit(Xtr, ytr)
    print(f"[Hồi quy] CV R² Ridge={grid_ridge.best_score_:.3f} {grid_ridge.best_params_}")
    print(f"[Hồi quy] CV R² RF   ={grid_rf.best_score_:.3f} {grid_rf.best_params_}")

    # Baseline hồi quy chấm CV THẬT trên CÙNG fold expanding origin 2017–2022
    # (reg_cv) thay vì để trống: quy ước điểm trùng GridSearchCV scoring="r2" —
    # R² trên từng fold validation, lấy mean làm value_cv. Trong mỗi fold,
    # "train" là phần lịch sử của fold nên trung bình train là mean của
    # ytr[train_idx] (song song với expanding_majority_f1 của phân loại).
    # Baseline vẫn không tranh selection (vẫn bị loại khỏi select_model_by_cv).
    _carry_all = tr["carry"].to_numpy()
    _carry_fold_r2 = []
    _mean_fold_r2 = []
    for _tr_idx, _va_idx in reg_cv:
        _y_val = ytr[_va_idx]
        _carry_fold_r2.append(r2_score(_y_val, _carry_all[_va_idx]))
        _mean_fold_r2.append(
            r2_score(_y_val, np.full_like(_y_val, ytr[_tr_idx].mean()))
        )
    carry_cv = float(np.mean(_carry_fold_r2))
    mean_train_cv = float(np.mean(_mean_fold_r2))

    def reg_metrics(y, yp, cv_score):
        return {
            "metric_cv": "r2 (expanding origin 2017–2022)",
            "value_cv": round(float(cv_score), 3),
            "holdout_mae": round(float(mean_absolute_error(y, yp)), 4),
            "holdout_rmse": round(float(np.sqrt(mean_squared_error(y, yp))), 4),
            "holdout_r2": round(float(r2_score(y, yp)), 3),
        }

    pred_ridge = grid_ridge.best_estimator_.predict(Xte)
    pred_rf = grid_rf.best_estimator_.predict(Xte)
    met_rows.append({"task": "regression", "model": "carry-forward (giữ giá trị năm nay)",
                     **reg_metrics(yte, te["carry"].to_numpy(), carry_cv)})
    met_rows.append({"task": "regression", "model": "trung bình train",
                     **reg_metrics(yte, np.full_like(yte, ytr.mean()), mean_train_cv)})
    met_rows.append({"task": "regression", "model": "ridge",
                     **reg_metrics(yte, pred_ridge, grid_ridge.best_score_)})
    met_rows.append({"task": "regression", "model": "random forest",
                     **reg_metrics(yte, pred_rf, grid_rf.best_score_)})

    joblib.dump(grid_ridge.best_estimator_, MODELS / "sup_ridge.joblib")
    joblib.dump(grid_rf.best_estimator_, MODELS / "sup_rf.joblib")

    # ================================================================== #
    # (2) PHÂN LOẠI pseudo-label STING, với forward CV
    # ================================================================== #
    C = build_classification_pairs(df, cfg["features"], cfg["sting"])
    ctr = C[C.year_t < HOLDOUT_YEAR]
    cte = C[C.year_t == HOLDOUT_YEAR]
    Xc_tr, yc_tr = ctr[FEATURES].to_numpy(), ctr["y"].to_numpy()
    Xc_te, yc_te = cte[FEATURES].to_numpy(), cte["y"].to_numpy()
    clf_cv = expanding_year_splits(ctr["year_t"].to_numpy(), yc_tr)
    majority_cv = expanding_majority_f1(yc_tr, clf_cv)
    lr = Pipeline([("sc", StandardScaler()),
                   ("clf", LogisticRegression(max_iter=3000, random_state=SEED))])
    rf_clf = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=1)
    grid_lr = GridSearchCV(lr, {"clf__C": [0.1, 0.3, 1.0]}, cv=clf_cv,
                           scoring=CLASSIFICATION_SCORER, n_jobs=1)
    grid_rfc = GridSearchCV(rf_clf, {"max_depth": [3, 6, None], "min_samples_leaf": [1, 2]},
                            cv=clf_cv, scoring=CLASSIFICATION_SCORER, n_jobs=1)
    grid_lr.fit(Xc_tr, yc_tr)
    grid_rfc.fit(Xc_tr, yc_tr)
    maj = int(pd.Series(yc_tr).mode().iloc[0])

    def clf_metrics(y, yp, cv_score):
        return {
            "metric_cv": "f1_macro (expanding origin 2017–2022)",
            "value_cv": round(float(cv_score), 3) if not np.isnan(cv_score) else np.nan,
            "holdout_acc": round(float(accuracy_score(y, yp)), 3),
            "holdout_macro_f1": round(
                float(f1_score(y, yp, average="macro", labels=[0, 1], zero_division=0)), 3
            ),
        }

    met_rows.append({"task": "classification", "model": "majority (lớp đa số)",
                     **clf_metrics(yc_te, np.full_like(yc_te, maj), majority_cv)})
    met_rows.append({"task": "classification", "model": "logistic regression",
                     **clf_metrics(yc_te, grid_lr.best_estimator_.predict(Xc_te),
                                   grid_lr.best_score_)})
    met_rows.append({"task": "classification", "model": "random forest",
                     **clf_metrics(yc_te, grid_rfc.best_estimator_.predict(Xc_te),
                                   grid_rfc.best_score_)})
    met = pd.DataFrame(met_rows)
    met.to_csv(RESULTS / "supervised_metrics.csv", index=False, encoding="utf-8-sig")
    print("\n" + met.to_string(index=False))

    # ================================================================== #
    # Hình (a): dự báo vs thực tế + độ quan trọng đặc trưng
    # ================================================================== #
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from fig_style import (
        PALETTE,
        add_source,
        new_fig,
        save_png,
        style_context,
    )

    # Hình (a) — bố cục 2 panel ngang, đặt trên slide 16:9 (build_slides.py)
    # nên dùng preset "slide" (9 x 5.0625 in) cho đủ chỗ cho tiêu đề panel.
    with style_context():
        fig, axes = new_fig(target="slide", ncols=2)
        ax = axes[0]
        ax.scatter(yte, pred_ridge, s=34, c=PALETTE["blue"], label="Ridge", alpha=0.85)
        # Random forest: cam đặc (không alpha) để RGB của marker khớp ĐÚNG màu
        # thanh độ quan trọng ở panel phải — một đối tượng một màu trong hình.
        ax.scatter(
            yte, pred_rf, s=34, c=PALETTE["orange"],
            label="Random forest", marker="^",
        )
        lo, hi = float(min(yte.min(), pred_ridge.min())) - 0.05, float(max(yte.max(), pred_rf.max())) + 0.05
        ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="y = x")
        # Đơn vị trục: sd_* là điểm chỉ số PAPI nhưng thang đo CHƯA đối chiếu
        # workbook (data/processed/papi_panel_scale_metadata.csv), nên chỉ ghi
        # họ đơn vị "điểm PAPI", không gắn thang điểm cụ thể.
        # Nhãn xuống 2 dòng: nhãn 1 dòng (~4.3 in) rộng hơn panel trái mà
        # tight_layout ép hẹp (panel phải chiếm chỗ cho tên đặc trưng dài), nên
        # nhãn tràn qua mép trái canvas và bbox_inches="tight" cắt mất ký tự đầu
        # (matplotlib chỉ tính tâm nhãn trục, không tính bề ngang, khi gộp
        # tight bbox — Axes.get_tightbbox gọi _get_tightbbox_for_layout_only).
        # Wrap 30 ký tự như tên đặc trưng panel phải, giữ nguyên nội dung + đơn vị.
        ax.set_xlabel(
            textwrap.fill(
                f"{FEATURE_LABELS[TARGET]} ({TARGET}) thực tế năm {HOLDOUT_YEAR + 1}"
                " (điểm PAPI)",
                30,
            )
        )
        ax.set_ylabel(f"Dự báo từ chỉ số năm {HOLDOUT_YEAR} (điểm PAPI)")
        ax.set_title("Hồi quy: dự báo 6.1 Y tế công lập năm sau")
        ax.legend()
        ax.grid(alpha=0.25)

        ax = axes[1]
        imp = grid_rf.best_estimator_.feature_importances_
        order = np.argsort(imp)
        # Màu cam = màu Random forest ở panel trái: cùng một đối tượng dùng
        # một màu trong cùng hình (palette Okabe–Ito, scripts/fig_style.py).
        ax.barh(np.arange(len(imp)), imp[order], color=PALETTE["orange"])
        # Tên hiển thị tiếng Việt của từng mã chỉ tiêu (papi_pred_common.py).
        imp_names = [FEATURE_LABELS[c] for c in np.array(FEATURES)[order]]
        ax.set_yticks(
            np.arange(len(imp)), [textwrap.fill(name, 30) for name in imp_names]
        )
        ax.set_title("Độ quan trọng đặc trưng (Random forest)")
        # Đơn vị trục x: feature_importances_ của sklearn (MDI — Mean Decrease
        # in Impurity), chuẩn hoá để tổng trên tất cả đặc trưng bằng 1.
        ax.set_xlabel("Tầm quan trọng (MDI chuẩn hoá, tổng = 1)")
        ax.grid(alpha=0.25, axis="x")
        add_source(fig, FIG_SOURCE, retrieved=FIG_RETRIEVED, extra=FIG_EXTRA)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_png(fig, FIGS / "supervised_regression.png", dpi=FIG_DPI)
        plt.close(fig)

    # ================================================================== #
    # Hình (b): confusion của bài toán phân loại (model chọn bằng CV)
    # ================================================================== #
    _clf_rows = met[met.task == "classification"]
    _clf = _clf_rows.set_index("model")
    _clf_models = _clf_rows[_clf_rows.model != "majority (lớp đa số)"]
    _selected_clf_name = select_model_by_cv(_clf_models)
    _selected_clf = _clf.loc[_selected_clf_name]
    _majority_clf = _clf.loc["majority (lớp đa số)"]
    _clf_grids = {
        "logistic regression": grid_lr,
        "random forest": grid_rfc,
    }
    _selected_clf_grid = _clf_grids[_selected_clf_name]
    joblib.dump(_selected_clf_grid.best_estimator_, MODELS / "sup_classifier.joblib")
    classes = sorted(set(yc_tr.tolist()) | set(yc_te.tolist()))
    with style_context():
        fig, ax = new_fig()  # preset "docx": 6.5 x 4.3 in — đủ chỗ cho tiêu đề 2 dòng
        cm = confusion_matrix(
            yc_te, _selected_clf_grid.best_estimator_.predict(Xc_te), labels=classes
        )
        im = ax.imshow(cm, cmap="Blues")
        ax.set_title(
            "Phân loại ngoại vi/vùng dày (2023→2024)\n"
            f"{_selected_clf_name}: macro-F1 {_selected_clf['holdout_macro_f1']:.3f}"
            f" vs majority {_majority_clf['holdout_macro_f1']:.3f}"
        )
        ax.set_xlabel("dự báo")
        ax.set_ylabel("thực tế")
        # Nối tick số với tên lớp (xem CLASS_NAMES): 0 = ngoại vi (nhãn nhiễu
        # STING), 1 = vùng dày (được STING gán vào cụm).
        class_tick = [f"{c} – {CLASS_NAMES.get(c, str(c))}" for c in classes]
        ax.set_xticks(range(len(classes)), class_tick)
        ax.set_yticks(range(len(classes)), class_tick)
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="black" if cm[i, j] < cm.max() / 2 else "white")
        # Đơn vị của giá trị trong ô: số tỉnh (thể hiện bằng colorbar có nhãn).
        fig.colorbar(im, ax=ax, label="Số tỉnh", fraction=0.046, pad=0.04)
        add_source(fig, FIG_SOURCE, retrieved=FIG_RETRIEVED, extra=FIG_EXTRA)
        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_png(fig, FIGS / "supervised_confusion.png", dpi=FIG_DPI)
        plt.close(fig)

    # ================================================================== #
    # Tóm tắt
    # ================================================================== #
    lines = []
    lines.append("# Model local có giám sát (scikit-learn, huấn luyện hoàn toàn local)\n")
    lines.append("## 1) Hồi quy — dự báo 6.1 Y tế công lập năm t+1 (bài toán chính)\n")
    lines.append(f"- Đặc trưng: 8 chỉ số năm t (sub-dim sạch thang đo: {', '.join(SUBS[1:4])}, …)")
    lines.append(
        "- Hồi quy: chọn model bằng CV expanding origin 2017–2022 thuần train; holdout 2023→2024 đánh giá "
        "một lần. Phân loại: đặc trưng (2 cột) và tham số STING của nhãn do predict_sweep.py chọn bằng cách "
        "chấm coverage trên 2021–2022 — trùng 2 fold CV cuối của phân loại, nên CV score phân loại hơi lạc quan."
    )
    lines.append(f"- Train: {len(tr)} cặp (2011–2022) · Holdout: {len(te)} cặp")
    lines.append("")
    lines.append(met[met.task == "regression"].to_markdown(index=False))
    lines.append("")
    lines.append(
        "- Baseline hồi quy có CV thật trên cùng fold, không tranh selection: "
        f"(CV: carry {carry_cv:.3f} vs ridge {grid_ridge.best_score_:.3f})."
    )
    lines.append("")
    lines.append("## 2) Phân loại — pseudo-label STING năm sau (bài toán phụ)\n")
    lines.append(met[met.task == "classification"].to_markdown(index=False))
    lines.append("")
    _reg_rows = met[met.task == "regression"]
    _reg = _reg_rows.set_index("model")
    _carry = _reg.loc["carry-forward (giữ giá trị năm nay)"]
    _reg_models = _reg_rows[~_reg_rows.model.isin(
        ["carry-forward (giữ giá trị năm nay)", "trung bình train"]
    )]
    _selected_reg_name = select_model_by_cv(_reg_models)
    _selected_reg = _reg.loc[_selected_reg_name]
    _impr = (1 - _selected_reg["holdout_mae"] / _carry["holdout_mae"]) * 100
    _acc_delta = (_selected_clf["holdout_acc"] - _majority_clf["holdout_acc"]) * 100
    _f1_delta = (_selected_clf["holdout_macro_f1"] - _majority_clf["holdout_macro_f1"]) * 100

    # --- Số liệu cho phần disclosure: tính từ chính dữ liệu/fold/grid của script này ---
    _prev = C.groupby("year_t")["y"].mean()
    _val_prev = _prev.loc[list(CLASSIFICATION_CV_YEARS)]
    _train_majority: list[int] = []
    _always_one: list[float] = []
    for _tr_idx, _va_idx in clf_cv:
        _train_majority.append(int(pd.Series(yc_tr[_tr_idx]).mode().iloc[0]))
        _always_one.append(
            f1_score(
                yc_tr[_va_idx],
                np.ones(_va_idx.size, dtype=int),
                average="macro",
                labels=[0, 1],
                zero_division=0,
            )
        )
    _always1_f1 = float(np.mean(_always_one))
    _tm_txt = (
        f"{_train_majority[0]} ở cả {len(_train_majority)} fold"
        if len(set(_train_majority)) == 1
        else str(_train_majority)
    )
    _ridge_spread = float(
        grid_ridge.cv_results_["mean_test_score"].max()
        - grid_ridge.cv_results_["mean_test_score"].min()
    )
    _feats_no_target = [f for f in FEATURES if f != TARGET]
    _grid_no_target = GridSearchCV(
        ridge, {"m__alpha": [0.1, 1.0, 10.0]}, cv=reg_cv, scoring="r2", n_jobs=1
    )
    _grid_no_target.fit(tr[_feats_no_target].to_numpy(), ytr)
    _cv_no_target = float(_grid_no_target.best_score_)
    _corr_carry = float(np.corrcoef(pred_ridge, te["carry"].to_numpy())[0, 1])

    lines.append(
        "## Lưu ý trung thực\n"
        f"- Chọn hồi quy theo CV train-only ({_selected_reg_name}, R²={_selected_reg['value_cv']:.3f}); "
        f"trên holdout 2023→2024 MAE={_selected_reg['holdout_mae']:.4f} so với carry-forward "
        f"{_carry['holdout_mae']:.4f} ({_impr:.1f}% thấp hơn). RF có MAE holdout thấp hơn nhưng không được "
        "chọn vì R² CV thấp hơn; một holdout không chứng minh tổng quát hóa.\n"
        "- Regression CV là expanding origin 2017–2022 với warm-up 2011–2016; holdout không được dùng để chọn mô hình.\n"
        f"- Chọn classifier theo forward CV ({_selected_clf_name}, macro-F1={_selected_clf['value_cv']:.3f}; "
        f"majority={_majority_clf['value_cv']:.3f}); so với baseline majority có chênh lệch holdout "
        f"accuracy {_acc_delta:+.1f} điểm % và macro-F1 {_f1_delta:+.1f} điểm %; CV dùng expanding origins "
        "2017–2022, warm-up origins 2011–2016. Đây là nhãn do STING fit tại từng cutoff sinh, không phải ground truth.\n"
        "- Nhãn phân loại phụ thuộc allowlist + tham số STING do predict_sweep.py chọn bằng cách chấm coverage "
        f"trên đúng 2021–2022 — trùng 2 fold CV cuối, nên macro-F1 CV {_selected_clf['value_cv']:.3f} hơi lạc quan.\n"
        f"- Prevalence nhãn 1 trôi mạnh theo năm: {_prev.min():.3f} ({_prev.idxmin()}) → {_prev.max():.3f} "
        f"({_prev.idxmax()}); trong mọi fold CV ({min(CLASSIFICATION_CV_YEARS)}–{max(CLASSIFICATION_CV_YEARS)}) "
        f"lớp đa số train là {_tm_txt} còn validation luôn đa số 1 (prevalence {_val_prev.min():.0%}–"
        f"{_val_prev.max():.0%}), nên macro-F1 CV phần lớn phản ánh việc model học drift độ phủ; baseline mù "
        f"thời gian “always dự đoán 1” đạt macro-F1 {_always1_f1:.3f} (chỉ thấp hơn LR "
        f"{_selected_clf['value_cv'] - _always1_f1:.3f}).\n"
        f"- value_cv là best_score_ của GridSearchCV — hiệu năng CV trung bình của combo TỐT NHẤT được chọn trên "
        f"chính các fold đó (không nested CV), nên hơi lạc quan; bias nhỏ vì lưới thô (spread điểm trong lưới "
        f"Ridge alpha {{0.1, 1, 10}} ≈ {_ridge_spread:.3f}).\n"
        f"- REGRESSION_TARGET (sd_6_1) nằm trong REGRESSION_FEATURES (scripts/papi_pred_common.py:19-23): không "
        f"leakage thời gian (target lấy từ năm t+1) nhưng lợi thế {_impr:.1f}% so với carry-forward chủ yếu là "
        f"thông tin lag-1 của chính target — bỏ sd_6_1 khỏi features, CV R² {_selected_reg['value_cv']:.3f} → "
        f"{_cv_no_target:.3f}; corr(dự báo, carry-forward) holdout = {_corr_carry:.2f}.\n"
        "- Một holdout 2023→2024 và pseudo-label không đủ để khẳng định năng lực dự báo xã hội tổng quát.\n"
        "- Nạp lại dự báo không cần train lại:\n"
        "  `import joblib; m = joblib.load('models/sup_ridge.joblib')` rồi truyền vector 8 chỉ số; "
        f"classifier tương tự qua `models/sup_classifier.joblib` ({_selected_clf_name}, nhãn 0/1)."
    )
    lines.append("")
    (RESULTS / "supervised_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("\nđã lưu: sup_ridge.joblib, sup_rf.joblib, sup_classifier.joblib, "
          "supervised_metrics.csv, supervised_summary.md, supervised_regression.png, "
          "supervised_confusion.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
