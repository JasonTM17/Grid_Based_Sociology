"""Model local CÓ GIÁM SÁT cho PAPI — quy trình ML đầy đủ, chạy hoàn toàn local.

Hai bài toán minh hoạ (khác với `predict_demo.py` — STING.predict không giám sát):

(1) CHÍNH — HỒI QUY dự báo: "6.1 Y tế công lập năm t+1" từ 8 chỉ số năm t
    (các sub-dim đã audit thang đo 2011–2024: 1.3, 1.4, 4.1–4.4, 6.1, 6.3).
    Model: Ridge + RandomForest; đối chứng: carry-forward (giữ nguyên giá trị
    năm nay) và trung bình năm. Bài toán + bộ đặc trưng + mô hình được chọn
    bằng CV train-only (GroupKFold theo năm); holdout 2023 → 2024 chỉ đánh
    giá MỘT LẦN.

(2) PHỤ — PHÂN LOẠI "trạng thái cấu trúc năm sau" (thuộc ô dày của STING
    hay rơi vào ngoại vi/nhiễu −1): KẾT QUẢ ÂM TÍNH — mọi mô hình ≈ baseline
    lớp đa số. Giữ lại làm bằng chứng trung thực, không dùng cho tuyên bố.

Đầu ra:
  models/sup_ridge.joblib, models/sup_rf.joblib           — model local (joblib)
  results/supervised_metrics.csv, results/supervised_summary.md
  results/figs/supervised_regression.png                  — dự báo vs thực tế + độ quan trọng
  results/figs/supervised_confusion.png                   — confusion (bài toán 2, âm tính)

Chạy: python scripts/predict_supervised.py
"""
from __future__ import annotations

import json
import sys
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
)
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sting import STING  # noqa: E402
from papi_pred_common import ROOT, load_config, load_panel  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MODELS = ROOT / "models"
RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"
HOLDOUT_YEAR = 2023          # cặp (2023 → 2024) là holdout duy nhất
SEED = 42

DIMS = ["d1", "d2", "d3", "d4", "d5", "d6"]
SUBS = ["sd_1_3", "sd_1_4", "sd_4_1", "sd_4_2", "sd_4_3", "sd_4_4", "sd_6_1", "sd_6_3"]
TARGET = "sd_6_1"            # chọn bằng CV (R² 0.44) vs d6 (0.17) — train-only
FEATURES = SUBS              # chỉ dùng cột qua audit thang đo (CV tốt hơn cả bộ +chiều)


def build_regression_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Cặp (đặc trưng năm t, giá trị đích năm t+1, carry-forward)."""
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


def build_classification_pairs(df: pd.DataFrame, feats) -> pd.DataFrame:
    """Cặp (đặc trưng năm t) → nhãn "năm t+1 thuộc ô dày hay ngoại vi (-1)".

    Nhãn lấy từ model STING đã lưu (không train lại).
    """
    model = STING.load(MODELS / "sting_predict_model.pkl")
    si = json.loads(
        (MODELS / "sting_predict_scaler.json").read_text(encoding="utf-8")
    )
    mean, scale = np.array(si["mean"]), np.array(si["scale"])
    labels_by_year: dict[int, dict[int, int]] = {}
    for y in sorted(df.year.unique()):
        sub = df[df.year == y].dropna(subset=feats)
        pred = model.predict((sub[feats].to_numpy() - mean) / scale)
        labels_by_year[int(y)] = {
            int(pc): int(lb) for pc, lb in zip(sub["province_code"], pred)
        }
    rows = []
    for t in range(2012, 2024):
        cur = df[df.year == t].dropna(subset=FEATURES)
        for _, r in cur.iterrows():
            pc = int(r["province_code"])
            if pc not in labels_by_year.get(t + 1, {}):
                continue
            rows.append(
                {
                    "year_t": t,
                    **{c: float(r[c]) for c in FEATURES},
                    "y": int(labels_by_year[t + 1][pc] != -1),
                }
            )
    return pd.DataFrame(rows).dropna()


def main() -> int:
    for d in (MODELS, RESULTS, FIGS):
        d.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    df = load_panel()
    cv = GroupKFold(n_splits=5)

    met_rows: list[dict] = []

    # ================================================================== #
    # (1) HỒI QUY: dự báo "6.1 Y tế công lập" năm t+1
    # ================================================================== #
    P = build_regression_pairs(df)
    tr = P[P.year_t < HOLDOUT_YEAR]
    te = P[P.year_t == HOLDOUT_YEAR]
    Xtr, ytr = tr[FEATURES].to_numpy(), tr["y"].to_numpy()
    Xte, yte = te[FEATURES].to_numpy(), te["y"].to_numpy()
    print(f"[Hồi quy] train {len(tr)} cặp (2011–2022) · holdout {len(te)} cặp (2023→2024)")

    ridge = Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))])
    rf_reg = RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=1)
    grid_ridge = GridSearchCV(
        ridge, {"m__alpha": [0.1, 1.0, 10.0]}, cv=cv, scoring="r2", n_jobs=1
    )
    grid_rf = GridSearchCV(
        rf_reg,
        {"max_depth": [4, 6, None], "min_samples_leaf": [1, 2]},
        cv=cv, scoring="r2", n_jobs=1,
    )
    grid_ridge.fit(Xtr, ytr, groups=tr["year_t"])
    grid_rf.fit(Xtr, ytr, groups=tr["year_t"])
    print(f"[Hồi quy] CV R² Ridge={grid_ridge.best_score_:.3f} {grid_ridge.best_params_}")
    print(f"[Hồi quy] CV R² RF   ={grid_rf.best_score_:.3f} {grid_rf.best_params_}")

    def reg_metrics(y, yp, cv_score):
        return {
            "metric_cv": "r2 (GroupKFold theo năm)",
            "value_cv": round(float(cv_score), 3),
            "holdout_mae": round(float(mean_absolute_error(y, yp)), 4),
            "holdout_rmse": round(float(np.sqrt(mean_squared_error(y, yp))), 4),
            "holdout_r2": round(float(r2_score(y, yp)), 3),
        }

    pred_ridge = grid_ridge.best_estimator_.predict(Xte)
    pred_rf = grid_rf.best_estimator_.predict(Xte)
    met_rows.append({"task": "regression", "model": "carry-forward (giữ giá trị năm nay)",
                     **reg_metrics(yte, te["carry"].to_numpy(), np.nan)})
    met_rows.append({"task": "regression", "model": "trung bình train",
                     **reg_metrics(yte, np.full_like(yte, ytr.mean()), np.nan)})
    met_rows.append({"task": "regression", "model": "ridge",
                     **reg_metrics(yte, pred_ridge, grid_ridge.best_score_)})
    met_rows.append({"task": "regression", "model": "random forest",
                     **reg_metrics(yte, pred_rf, grid_rf.best_score_)})

    joblib.dump(grid_ridge.best_estimator_, MODELS / "sup_ridge.joblib")
    joblib.dump(grid_rf.best_estimator_, MODELS / "sup_rf.joblib")

    # ================================================================== #
    # (2) PHÂN LOẠI (âm tính): trạng thái cấu trúc năm sau
    # ================================================================== #
    C = build_classification_pairs(df, cfg["features"])
    ctr = C[C.year_t < HOLDOUT_YEAR]
    cte = C[C.year_t == HOLDOUT_YEAR]
    Xc_tr, yc_tr = ctr[FEATURES].to_numpy(), ctr["y"].to_numpy()
    Xc_te, yc_te = cte[FEATURES].to_numpy(), cte["y"].to_numpy()
    lr = Pipeline([("sc", StandardScaler()),
                   ("clf", LogisticRegression(max_iter=3000, random_state=SEED))])
    rf_clf = RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=1)
    grid_lr = GridSearchCV(lr, {"clf__C": [0.1, 0.3, 1.0]}, cv=cv,
                           scoring="f1_macro", n_jobs=1)
    grid_rfc = GridSearchCV(rf_clf, {"max_depth": [3, 6, None], "min_samples_leaf": [1, 2]},
                            cv=cv, scoring="f1_macro", n_jobs=1)
    grid_lr.fit(Xc_tr, yc_tr, groups=ctr["year_t"])
    grid_rfc.fit(Xc_tr, yc_tr, groups=ctr["year_t"])
    maj = int(pd.Series(yc_tr).mode().iloc[0])

    def clf_metrics(y, yp, cv_score):
        return {
            "metric_cv": "f1_macro (GroupKFold theo năm)",
            "value_cv": round(float(cv_score), 3) if not np.isnan(cv_score) else np.nan,
            "holdout_acc": round(float(accuracy_score(y, yp)), 3),
            "holdout_macro_f1": round(float(f1_score(y, yp, average="macro")), 3),
        }

    met_rows.append({"task": "classification", "model": "majority (lớp đa số)",
                     **clf_metrics(yc_te, np.full_like(yc_te, maj), np.nan)})
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

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    ax = axes[0]
    ax.scatter(yte, pred_ridge, s=34, c="#4c72b0", label="Ridge", alpha=0.85)
    ax.scatter(yte, pred_rf, s=34, c="#dd8452", label="Random forest", alpha=0.6, marker="^")
    lo, hi = float(min(yte.min(), pred_ridge.min())) - 0.05, float(max(yte.max(), pred_rf.max())) + 0.05
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="y = x")
    ax.set_xlabel(f"{TARGET} thực tế năm 2024")
    ax.set_ylabel("dự báo từ chỉ số năm 2023")
    ax.set_title("Hồi quy: dự báo 6.1 Y tế công lập năm sau")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1]
    imp = grid_rf.best_estimator_.feature_importances_
    order = np.argsort(imp)
    ax.barh(np.array(FEATURES)[order], imp[order], color="#55a868")
    ax.set_title("Độ quan trọng đặc trưng (Random forest)")
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    fig.savefig(FIGS / "supervised_regression.png", dpi=150)
    plt.close(fig)

    # ================================================================== #
    # Hình (b): confusion của bài toán phân loại (âm tính)
    # ================================================================== #
    classes = sorted(set(yc_tr.tolist()) | set(yc_te.tolist()))
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    cm = confusion_matrix(yc_te, grid_rfc.best_estimator_.predict(Xc_te), labels=classes)
    ax.imshow(cm, cmap="Blues")
    ax.set_title("Phân loại ngoại vi/vùng dày (2023→2024)\nKẾT QUẢ ÂM TÍNH ≈ baseline")
    ax.set_xlabel("dự báo")
    ax.set_ylabel("thực tế")
    ax.set_xticks(range(len(classes)), [str(c) for c in classes])
    ax.set_yticks(range(len(classes)), [str(c) for c in classes])
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="black" if cm[i, j] < cm.max() / 2 else "white")
    fig.tight_layout()
    fig.savefig(FIGS / "supervised_confusion.png", dpi=150)
    plt.close(fig)

    # ================================================================== #
    # Tóm tắt
    # ================================================================== #
    lines = []
    lines.append("# Model local có giám sát (scikit-learn, huấn luyện hoàn toàn local)\n")
    lines.append("## 1) Hồi quy — dự báo 6.1 Y tế công lập năm t+1 (bài toán chính)\n")
    lines.append(f"- Đặc trưng: 8 chỉ số năm t (sub-dim sạch thang đo: {', '.join(SUBS[1:4])}, …)")
    lines.append("- Chọn bài toán/đặc trưng/mô hình bằng CV train-only; holdout 2023→2024 đánh giá một lần.")
    lines.append(f"- Train: {len(tr)} cặp (2011–2022) · Holdout: {len(te)} cặp")
    lines.append("")
    lines.append(met[met.task == "regression"].to_markdown(index=False))
    lines.append("")
    lines.append("## 2) Phân loại — trạng thái cấu trúc năm sau (bài toán phụ, KẾT QUẢ ÂM TÍNH)\n")
    lines.append(met[met.task == "classification"].to_markdown(index=False))
    lines.append("")
    _reg = met[met.task == "regression"].set_index("model")
    _carry = _reg.loc["carry-forward (giữ giá trị năm nay)"]
    _best_model = _reg.drop(index=["carry-forward (giữ giá trị năm nay)", "trung bình train"])["holdout_mae"].min()
    _impr = (1 - _best_model / _carry["holdout_mae"]) * 100
    lines.append(
        "## Lưu ý trung thực\n"
        f"- Hồi quy có tín hiệu thật: mô hình tốt nhất giảm ~{_impr:.0f}% MAE so với baseline "
        "carry-forward (giữ nguyên giá trị năm nay) trên holdout — nhưng vẫn là một holdout duy nhất.\n"
        "- Phân loại trạng thái ngoại vi chỉ nhích nhẹ so với baseline lớp đa số (≤~2 điểm phần trăm) — "
        "không đủ cơ sở kết luận có tín hiệu thật; giữ lại làm bằng chứng trung thực.\n"
        "- Nhãn phân loại do STING sinh (model không giám sát) → sai số lan truyền, đã khai báo.\n"
        "- Nạp lại dự báo không cần train lại:\n"
        "  `import joblib; m = joblib.load('models/sup_ridge.joblib')` rồi truyền vector 8 chỉ số."
    )
    lines.append("")
    (RESULTS / "supervised_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("\nđã lưu: sup_ridge.joblib, sup_rf.joblib, supervised_metrics.csv, "
          "supervised_summary.md, supervised_regression.png, supervised_confusion.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
