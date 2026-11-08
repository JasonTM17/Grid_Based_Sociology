"""Chẩn đoán chuyên sâu (lane C) cho phần supervised — CHỈ MÔ TẢ, không chọn model.

Script TÁI DÙNG đúng pipeline ``scripts/predict_supervised.py``: ghép cặp đặc
trưng/đích bằng ``build_regression_pairs`` (:99), fold expanding origin bằng
``expanding_origin_folds`` (:123), nhãn STING cho bài toán phân loại bằng
``build_classification_pairs`` (:187) với cấu hình đóng băng
``models/predict_config.json`` (CHỈ ĐỌC), spec model Ridge/LR/RF và lưới
GridSearchCV y hệt (:276-285, :342-348). Thêm BA phân tích chẩn đoán mới:

(1) Learning curve expanding origin 2016→2022: với mỗi origin validation v,
    train trên mọi cặp year_t < v (cửa sổ mở rộng, warm-up 2011–2015), chấm
    R² (Ridge) và macro-F1 (LogisticRegression) trên đúng origin v. Holdout
    2023→2024 KHÔNG tham gia bước nào của mục này.
(2) Permutation importance cho RF hồi quy trên 8 đặc trưng:
    ``sklearn.inspection.permutation_importance``, seed 11, n_repeats=30,
    scoring R² — chạy trên train 2011–2022 (in-sample) và trên holdout
    2023→2024; cả hai CHỈ MÔ TẢ, không dùng chọn gì.
(3) Residual diagnostics của Ridge trên holdout 2023→2024: phân bố residual,
    theo năm, theo tỉnh lớn/nhỏ (median dân số GSO năm origin 2023), top-5
    tỉnh lệch nhất. Chỉ mô tả, KHÔNG sửa dữ liệu.

Siêu tham số ba model được TÍNH LẠI trong bộ nhớ bằng đúng lưới + fold
CV train-only 2017–2022 của pipeline (không đọc model đã lưu, không ghi
models/*) rồi GIỮ CỐ ĐỊNH trên mọi cửa sổ learning curve — spec trùng model
đã công bố, không chọn lại gì trên holdout.

Output (file MỚI, không đụng artifact cũ):
  results/supervised_depth.csv · results/supervised_depth.md
  results/figs/supervised_learning_curve.png
  results/figs/supervised_importance.png

Chạy: python -E scripts/supervised_depth.py   (từ thư mục gốc repo)
"""
from __future__ import annotations

import hashlib
import sys
import textwrap
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.metrics import f1_score, mean_absolute_error, r2_score  # noqa: E402
from sklearn.model_selection import GridSearchCV  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fig_style import PALETTE, add_source, new_fig, save_png, style_context  # noqa: E402
from papi_pred_common import (  # noqa: E402
    CONFIG_PATH,
    FEATURE_LABELS,
    PANEL_PATH,
    REGRESSION_FEATURES,
    REGRESSION_TARGET,
    ROOT,
    load_config,
    load_panel,
)
from predict_supervised import (  # noqa: E402
    CLASSIFICATION_CV_FIRST_YEAR,
    CLASSIFICATION_SCORER,
    FIG_DPI,
    FIG_RETRIEVED,
    FIG_SOURCE,
    HOLDOUT_YEAR,
    SEED,
    build_classification_pairs,
    build_regression_pairs,
    expanding_origin_folds,
    expanding_year_splits,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS = ROOT / "results"
FIGS = RESULTS / "figs"
# Dân số tỉnh từ GSO (phái sinh có provenance, xem data/processed/external_provenance.md).
POP_PATH = ROOT / "data" / "processed" / "external_gso_population_63_full.csv"
PUBLISHED_METRICS = RESULTS / "supervised_metrics.csv"

LC_FIRST_ORIGIN = 2016                 # origin validation ĐẦU TIÊN của learning curve
PERM_SEED = 11                         # seed bắt buộc của lane cho phân tích ngẫu nhiên
PERM_REPEATS = 30
SIZE_LARGE, SIZE_SMALL = "lớn", "nhỏ"

OUT_MD = RESULTS / "supervised_depth.md"
OUT_CSV = RESULTS / "supervised_depth.csv"
OUT_FIG_LC = FIGS / "supervised_learning_curve.png"
OUT_FIG_IMP = FIGS / "supervised_importance.png"


# ------------------------------------------------------------------ helpers --
def fmt(value: object, nd: int = 4) -> str:
    """Số thập phân cố định; NaN/None → chuỗi rỗng (ổn định byte khi chạy lại)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return f"{float(value):.{nd}f}"


def sha256_short(path: Path, n: int = 12) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def attach_pair_codes(df: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Gắn ``province_code`` vào cặp theo ĐÚNG thứ tự lặp của
    ``build_regression_pairs`` (scripts/predict_supervised.py:105-118) rồi
    KIỂM TRA CHÉO: mọi cột đặc trưng và y phải khớp panel theo (code, năm).
    """
    base = df[["province_code", "year"] + REGRESSION_FEATURES].copy()
    codes: list[int] = []
    for t in range(2011, 2024):
        cur = base[base.year == t].dropna(subset=REGRESSION_FEATURES)
        nxt = base[base.year == t + 1].set_index("province_code")
        for _, r in cur.iterrows():
            pc = int(r["province_code"])
            if pc not in nxt.index or pd.isna(nxt.loc[pc, REGRESSION_TARGET]):
                continue
            codes.append(pc)
    out = pairs.copy()
    if len(codes) != len(out):
        raise RuntimeError(
            f"Số code ghép được ({len(codes)}) khác số cặp ({len(out)}) — logic lệch pipeline."
        )
    out["province_code"] = codes
    panel_idx = df.set_index(["province_code", "year"])
    for c in REGRESSION_FEATURES:
        expected = np.array(
            [float(panel_idx.loc[(pc, yt), c]) for pc, yt in zip(codes, out["year_t"])]
        )
        if not np.allclose(out[c].to_numpy(), expected):
            raise RuntimeError(f"Cột {c} không khớp panel khi gắn province_code.")
    y_expected = np.array(
        [float(panel_idx.loc[(pc, yt + 1), REGRESSION_TARGET]) for pc, yt in zip(codes, out["year_t"])]
    )
    if not np.allclose(out["y"].to_numpy(), y_expected):
        raise RuntimeError("Cột y không khớp panel khi gắn province_code.")
    return out


def rank_desc(mean: np.ndarray) -> list[int]:
    """Thứ tự hạng theo mean giảm dần; hoà phá vỡ bằng index (tất định)."""
    return sorted(range(len(mean)), key=lambda i: (-float(mean[i]), i))


def resid_stats(resid: np.ndarray) -> dict[str, float]:
    return {
        "n": float(len(resid)),
        "resid_mean": float(np.mean(resid)),
        "resid_median": float(np.median(resid)),
        "resid_std": float(np.std(resid, ddof=1)) if len(resid) > 1 else np.nan,
        "resid_min": float(np.min(resid)),
        "resid_max": float(np.max(resid)),
        "abs_resid_mean": float(np.mean(np.abs(resid))),
    }


def csv_add(rows: list[tuple[str, str, str, str]], section: str, key: str, metrics: dict[str, object]) -> None:
    for name, value in metrics.items():
        rows.append((section, key, name, value if isinstance(value, str) else fmt(value, 6)))


def md_table(headers: list[str], rows: Iterable[Iterable[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(":--" if i == 0 else "--:" for i in range(len(headers))) + "|")
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------- main --
def main() -> int:
    for d in (RESULTS, FIGS):
        d.mkdir(parents=True, exist_ok=True)

    cfg = load_config()          # CHỈ ĐỌC cấu hình đóng băng — không ghi lại
    df = load_panel()

    # ---- ghép cặp đúng pipeline, gắn code tỉnh (kiểm tra chéo giá trị) ----
    P = attach_pair_codes(df, build_regression_pairs(df))
    tr = P[P.year_t < HOLDOUT_YEAR]
    te = P[P.year_t == HOLDOUT_YEAR]
    Xtr, ytr = tr[REGRESSION_FEATURES].to_numpy(), tr["y"].to_numpy()
    Xte, yte = te[REGRESSION_FEATURES].to_numpy(), te["y"].to_numpy()
    print(f"[Cặp] train {len(tr)} (2011–2022) · holdout {len(te)} (2023→2024)")

    # ---- siêu tham số: TÍNH LẠI đúng lưới + fold CV train-only 2017–2022 ----
    reg_cv_select = expanding_origin_folds(
        tr["year_t"].to_numpy(), first_validation_origin=CLASSIFICATION_CV_FIRST_YEAR
    )
    grid_ridge = GridSearchCV(
        Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))]),
        {"m__alpha": [0.1, 1.0, 10.0]}, cv=reg_cv_select, scoring="r2", n_jobs=1,
    )
    grid_ridge.fit(Xtr, ytr)
    best_alpha = float(grid_ridge.best_params_["m__alpha"])

    grid_rf = GridSearchCV(
        RandomForestRegressor(n_estimators=300, random_state=SEED, n_jobs=1),
        {"max_depth": [4, 6, None], "min_samples_leaf": [1, 2]},
        cv=reg_cv_select, scoring="r2", n_jobs=1,
    )
    grid_rf.fit(Xtr, ytr)
    rf_best = grid_rf.best_estimator_

    C = build_classification_pairs(df, cfg["features"], cfg["sting"])
    ctr = C[C.year_t < HOLDOUT_YEAR]
    Xc_tr, yc_tr = ctr[REGRESSION_FEATURES].to_numpy(), ctr["y"].to_numpy()
    clf_cv_select = expanding_year_splits(ctr["year_t"].to_numpy(), yc_tr)
    grid_lr = GridSearchCV(
        Pipeline([("sc", StandardScaler()), ("clf", LogisticRegression(max_iter=3000, random_state=SEED))]),
        {"clf__C": [0.1, 0.3, 1.0]}, cv=clf_cv_select, scoring=CLASSIFICATION_SCORER, n_jobs=1,
    )
    grid_lr.fit(Xc_tr, yc_tr)
    best_c = float(grid_lr.best_params_["clf__C"])
    print(f"[Spec cố định] Ridge alpha={best_alpha:g} · LR C={best_c:g} · RF {grid_rf.best_params_}")

    # ---- kiểm đối: tái tính trong bộ nhớ phải khớp artifact đã công bố ----
    repro_note = "không có file results/supervised_metrics.csv — bỏ qua kiểm đối"
    repro_ok: bool | None = None
    ridge_mae_holdout = float(mean_absolute_error(yte, grid_ridge.best_estimator_.predict(Xte)))
    if PUBLISHED_METRICS.exists():
        pub = pd.read_csv(PUBLISHED_METRICS, encoding="utf-8-sig")
        pub_ridge = pub[(pub.task == "regression") & (pub.model == "ridge")].iloc[0]
        pub_rf = pub[(pub.task == "regression") & (pub.model == "random forest")].iloc[0]
        repro_ok = bool(
            round(float(grid_ridge.best_score_), 3) == float(pub_ridge["value_cv"])
            and round(float(grid_rf.best_score_), 3) == float(pub_rf["value_cv"])
            and round(ridge_mae_holdout, 4) == float(pub_ridge["holdout_mae"])
        )
        repro_note = (
            f"tái tính trong bộ nhớ cho ridge CV R²={grid_ridge.best_score_:.3f} / "
            f"holdout MAE={ridge_mae_holdout:.4f} và RF CV R²={grid_rf.best_score_:.3f} — "
            + ("KHỚP" if repro_ok else "LỆCH")
            + f" results/supervised_metrics.csv (công bố: {pub_ridge['value_cv']} / "
            f"{pub_ridge['holdout_mae']} / {pub_rf['value_cv']})"
        )
    print(f"[Kiểm đối] {repro_note}")

    # =================== (1) LEARNING CURVE expanding origin =================
    # Cặp hồi quy (740 train) và cặp phân loại (738 train) là HAI tập dòng
    # khác nhau → mỗi tập có fold expanding riêng, cùng các origin 2016→2022.
    lc_folds = expanding_origin_folds(tr["year_t"].to_numpy(), first_validation_origin=LC_FIRST_ORIGIN)
    lc_folds_clf = expanding_origin_folds(ctr["year_t"].to_numpy(), first_validation_origin=LC_FIRST_ORIGIN)
    reg_lc: list[dict] = []
    clf_lc: list[dict] = []
    expanding_resid: dict[int, np.ndarray] = {}
    for train_idx, val_idx in lc_folds:
        origin = int(tr["year_t"].iloc[val_idx[0]])
        n_years = int(tr["year_t"].iloc[train_idx].nunique())

        ridge_w = Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=SEED))])
        ridge_w.set_params(m__alpha=best_alpha)
        ridge_w.fit(Xtr[train_idx], ytr[train_idx])
        pred_w = ridge_w.predict(Xtr[val_idx])
        reg_lc.append({
            "origin": origin,
            "n_train_years": n_years,
            "n_train_pairs": int(train_idx.size),
            "n_val_pairs": int(val_idx.size),
            "metric": float(r2_score(ytr[val_idx], pred_w)),
        })
        expanding_resid[origin] = ytr[val_idx] - pred_w

    for train_idx, val_idx in lc_folds_clf:
        origin = int(ctr["year_t"].iloc[val_idx[0]])
        n_years = int(ctr["year_t"].iloc[train_idx].nunique())
        if np.unique(yc_tr[train_idx]).size < 2:
            clf_lc.append({
                "origin": origin, "n_train_years": n_years,
                "n_train_pairs": int(train_idx.size), "n_val_pairs": int(val_idx.size),
                "metric": np.nan,
            })
        else:
            lr_w = Pipeline([("sc", StandardScaler()), ("clf", LogisticRegression(max_iter=3000, random_state=SEED))])
            lr_w.set_params(clf__C=best_c)
            lr_w.fit(Xc_tr[train_idx], yc_tr[train_idx])
            pred_c = lr_w.predict(Xc_tr[val_idx])
            clf_lc.append({
                "origin": origin, "n_train_years": n_years,
                "n_train_pairs": int(train_idx.size), "n_val_pairs": int(val_idx.size),
                "metric": float(f1_score(yc_tr[val_idx], pred_c, average="macro", labels=[0, 1], zero_division=0)),
            })
    for r in reg_lc:
        print(f"[LC] Ridge origin {r['origin']}: năm train={r['n_train_years']} R²={r['metric']:.4f}")
    for r in clf_lc:
        m = "nan" if np.isnan(r["metric"]) else f"{r['metric']:.4f}"
        print(f"[LC] LR    origin {r['origin']}: năm train={r['n_train_years']} macro-F1={m}")

    # =============== (2) PERMUTATION IMPORTANCE — RF hồi quy =================
    imp_sets: dict[str, dict] = {}
    for name, X, y in (("train", Xtr, ytr), ("holdout", Xte, yte)):
        imp = permutation_importance(
            rf_best, X, y, scoring="r2",
            n_repeats=PERM_REPEATS, random_state=PERM_SEED, n_jobs=1,
        )
        mean, std = imp.importances_mean, imp.importances_std
        lo = imp.importances.min(axis=1)
        hi = imp.importances.max(axis=1)
        order = rank_desc(mean)
        imp_sets[name] = {"mean": mean, "std": std, "lo": lo, "hi": hi, "order": order}
        top = ", ".join(f"{FEATURE_LABELS[REGRESSION_FEATURES[i]]}={mean[i]:.4f}" for i in order[:3])
        print(f"[Perm/{name}] top-3: {top}")

    # =================== (3) RESIDUAL DIAGNOSTICS — holdout ==================
    pred_te = grid_ridge.best_estimator_.predict(Xte)
    resid_te = yte - pred_te
    hold = pd.DataFrame({
        "province_code": te["province_code"].to_numpy(),
        "year_t": te["year_t"].to_numpy(),
        "y": yte,
        "pred": pred_te,
        "resid": resid_te,
    })
    hold_stats = resid_stats(resid_te)
    print(f"[Resid] holdout n={hold_stats['n']:.0f} mean={hold_stats['resid_mean']:.4f} "
          f"sd={hold_stats['resid_std']:.4f}")

    # Dân số năm origin 2023 → median split lớn/nhỏ (mô tả, không suy luận)
    pop = pd.read_csv(POP_PATH)
    pop_year = pop[pop.year == HOLDOUT_YEAR][["province_code", "gso_pop_total_thousand"]]
    hold = hold.merge(pop_year, on="province_code", how="left", validate="one_to_one")
    if hold["gso_pop_total_thousand"].isna().any():
        raise RuntimeError("Có tỉnh holdout thiếu dân số — không chia nhóm lớn/nhỏ được.")
    pop_median = float(hold["gso_pop_total_thousand"].median())
    hold["nhom"] = np.where(hold["gso_pop_total_thousand"] >= pop_median, SIZE_LARGE, SIZE_SMALL)

    names = df[df.year == HOLDOUT_YEAR].set_index("province_code")["province_vi"].to_dict()
    hold["province_vi"] = hold["province_code"].map(names)

    by_size = (
        hold.groupby("nhom", sort=True)["resid"]
        .agg(n="size", mean="mean", median="median", std=lambda s: s.std(ddof=1))
        .reindex([SIZE_LARGE, SIZE_SMALL])
    )
    size_pop_median = hold.groupby("nhom")["gso_pop_total_thousand"].median().reindex([SIZE_LARGE, SIZE_SMALL])
    size_abs_mean = hold.groupby("nhom")["resid"].apply(lambda s: s.abs().mean()).reindex([SIZE_LARGE, SIZE_SMALL])
    for g in (SIZE_LARGE, SIZE_SMALL):
        print(f"[Resid/{g}] n={int(by_size.loc[g, 'n'])} mean={by_size.loc[g, 'mean']:.4f}")

    top_order = sorted(range(len(hold)), key=lambda i: (-abs(float(resid_te[i])), int(hold["province_code"].iloc[i])))[:5]
    top5 = hold.iloc[top_order].reset_index(drop=True)

    # ============================== CSV (long) ===============================
    csv_rows: list[tuple[str, str, str, str]] = []
    for r in reg_lc:
        csv_add(csv_rows, "learning_curve_ridge", f"origin={r['origin']}", {
            "n_train_years": r["n_train_years"],
            "n_train_pairs": r["n_train_pairs"],
            "n_val_pairs": r["n_val_pairs"],
            "r2": r["metric"],
        })
    for r in clf_lc:
        csv_add(csv_rows, "learning_curve_lr", f"origin={r['origin']}", {
            "n_train_years": r["n_train_years"],
            "n_train_pairs": r["n_train_pairs"],
            "n_val_pairs": r["n_val_pairs"],
            "f1_macro": r["metric"],
        })
    for section, key_suffix in (("perm_importance_train", "train"), ("perm_importance_holdout", "holdout")):
        s = imp_sets[key_suffix]
        for rank, i in enumerate(s["order"], start=1):
            csv_add(csv_rows, section, REGRESSION_FEATURES[i], {
                "rank": rank,
                "importance_mean": s["mean"][i],
                "importance_std": s["std"][i],
                "importance_min": s["lo"][i],
                "importance_max": s["hi"][i],
            })
    hs = hold_stats
    csv_add(csv_rows, "residual_holdout_by_year", f"origin={HOLDOUT_YEAR}", {
        "target_year": HOLDOUT_YEAR + 1,
        "n_pairs": int(hs["n"]),
        **{k: hs[k] for k in ("resid_mean", "resid_median", "resid_std", "resid_min", "resid_max")},
    })
    for origin in sorted(expanding_resid):
        st = resid_stats(expanding_resid[origin])
        csv_add(csv_rows, "residual_expanding_by_year", f"origin={origin}", {
            "n_pairs": int(st["n"]),
            "is_holdout": 1 if origin == HOLDOUT_YEAR else 0,
            **{k: st[k] for k in ("resid_mean", "resid_median", "resid_std", "resid_min", "resid_max")},
        })
    for g in (SIZE_LARGE, SIZE_SMALL):
        csv_add(csv_rows, "residual_holdout_by_size", g, {
            "n_provinces": int(by_size.loc[g, "n"]),
            "pop_median_thousand": float(size_pop_median.loc[g]),
            "resid_mean": float(by_size.loc[g, "mean"]),
            "resid_median": float(by_size.loc[g, "median"]),
            "resid_std": float(by_size.loc[g, "std"]),
            "abs_resid_mean": float(size_abs_mean.loc[g]),
        })
    for i, r in top5.iterrows():
        csv_add(csv_rows, "residual_holdout_top5", f"{i + 1:02d}|{int(r['province_code'])}", {
            "province": str(r["province_vi"]),
            "pop_thousand": float(r["gso_pop_total_thousand"]),
            "size_group": str(r["nhom"]),
            "y_actual": float(r["y"]),
            "y_pred": float(r["pred"]),
            "resid": float(r["resid"]),
            "abs_resid": abs(float(r["resid"])),
        })
    pd.DataFrame(csv_rows, columns=["section", "key", "metric", "value"]).to_csv(
        OUT_CSV, index=False, encoding="utf-8-sig", lineterminator="\n"
    )
    print(f"[Ghi] {OUT_CSV} ({len(csv_rows)} dòng)")

    # ===================== HÌNH 1 — learning curve ===========================
    with style_context():
        fig, axes = new_fig(target="slide", ncols=2)
        ax = axes[0]
        xs = [r["n_train_years"] for r in reg_lc]
        ax.plot(xs, [r["metric"] for r in reg_lc], "o-", color=PALETTE["blue"])
        for r in reg_lc:
            ax.annotate(str(r["origin"]), (r["n_train_years"], r["metric"]),
                        textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
        ax.set_xlabel("Số năm train (cửa sổ mở rộng, warm-up 2011–2015)")
        ax.set_ylabel("R² trên origin validation")
        ax.set_title(f"Ridge hồi quy — R² (alpha={best_alpha:g})")
        ax.grid(alpha=0.25)

        ax = axes[1]
        xs = [r["n_train_years"] for r in clf_lc]
        ys = [np.nan if np.isnan(r["metric"]) else r["metric"] for r in clf_lc]
        ax.plot(xs, ys, "o-", color=PALETTE["orange"])
        for r in clf_lc:
            if not np.isnan(r["metric"]):
                ax.annotate(str(r["origin"]), (r["n_train_years"], r["metric"]),
                            textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
        ax.set_xlabel("Số năm train (cửa sổ mở rộng, warm-up 2011–2015)")
        ax.set_ylabel("macro-F1 trên origin validation")
        ax.set_title(f"LogisticRegression — macro-F1 (C={best_c:g})")
        ax.grid(alpha=0.25)

        fig.suptitle("Learning curve expanding origin 2016→2022 — holdout 2023→2024 không tham gia")
        add_source(fig, FIG_SOURCE, retrieved=FIG_RETRIEVED,
                   extra=f"panel phái sinh: {PANEL_PATH.name}; seed model = {SEED} (pipeline) — chỉ mô tả")
        fig.tight_layout(rect=(0, 0.06, 1, 0.92))
        save_png(fig, OUT_FIG_LC, dpi=FIG_DPI)
        plt.close(fig)
    print(f"[Ghi] {OUT_FIG_LC}")

    # ===================== HÌNH 2 — permutation importance ===================
    with style_context():
        # Nhãn tiếng Việt dài (3 dòng) × 8 tick: cần canvas cao hơn preset slide
        # để tick không đè nhau; new_fig(target=None) nhận figsize riêng.
        fig, axes = new_fig(target=None, figsize=(9.0, 6.8), ncols=2)
        for ax, name, color, title in (
            (axes[0], "train", PALETTE["blue"], "Trên train 2011–2022 (in-sample)"),
            (axes[1], "holdout", PALETTE["orange"], "Trên holdout 2023→2024"),
        ):
            s = imp_sets[name]
            order = np.array(s["order"])[::-1]  # ascending → hạng cao nhất trên cùng
            vals = s["mean"][order]
            errs = s["std"][order]
            ax.barh(np.arange(len(vals)), vals, xerr=errs, color=color,
                    error_kw={"lw": 1, "capsize": 2})
            labels = [textwrap.fill(FEATURE_LABELS[REGRESSION_FEATURES[i]], 22) for i in order]
            ax.set_yticks(np.arange(len(vals)), labels)
            ax.set_title(title)
            ax.set_xlabel("Giảm R² khi hoán vị (mean ± sd)")
            ax.grid(alpha=0.25, axis="x")
        fig.suptitle(f"Permutation importance — Random forest hồi quy (seed {PERM_SEED}, n_repeats={PERM_REPEATS})")
        add_source(fig, FIG_SOURCE, retrieved=FIG_RETRIEVED,
                   extra=f"panel phái sinh: {PANEL_PATH.name}; RF spec pipeline (seed {SEED})")
        fig.tight_layout(rect=(0, 0.06, 1, 0.92))
        save_png(fig, OUT_FIG_IMP, dpi=FIG_DPI)
        plt.close(fig)
    print(f"[Ghi] {OUT_FIG_IMP}")

    # ============================== MARKDOWN =================================
    lines: list[str] = []
    lines.append("# Chẩn đoán chuyên sâu phần supervised — chỉ mô tả, không chọn model\n")
    lines.append(
        "- Script: `scripts/supervised_depth.py`, tái dùng pipeline "
        "`scripts/predict_supervised.py` (`build_regression_pairs` :99, "
        "`expanding_origin_folds` :123, `build_classification_pairs` :187, spec model :276-285 "
        "và :342-348; hằng số `scripts/papi_pred_common.py:15-23`)."
    )
    lines.append(
        f"- Provenance (sha256 12 ký tự đầu): panel `{PANEL_PATH.name}` `{sha256_short(PANEL_PATH)}` · "
        f"config `{CONFIG_PATH.name}` `{sha256_short(CONFIG_PATH)}` (chỉ đọc) · "
        f"dân số `{POP_PATH.name}` `{sha256_short(POP_PATH)}`."
    )
    lines.append(
        f"- Seed: model giữ seed {SEED} của pipeline; permutation importance dùng seed {PERM_SEED}, "
        f"n_repeats={PERM_REPEATS} (theo yêu cầu lane). Mọi số tự tính trong bộ nhớ từ CSV provenance."
    )
    lines.append(
        f"- Siêu tham số CỐ ĐỊNH (chọn một lần bởi CV train-only expanding origin "
        f"{CLASSIFICATION_CV_FIRST_YEAR}–{HOLDOUT_YEAR - 1} của pipeline, tính lại trong bộ nhớ): "
        f"Ridge alpha={best_alpha:g}, LogisticRegression C={best_c:g}, RF "
        f"max_depth={grid_rf.best_params_['max_depth']}, min_samples_leaf={grid_rf.best_params_['min_samples_leaf']}. "
        "Không chọn lại theo từng cửa sổ, không dựa vào holdout."
    )
    lines.append(f"- Kiểm đối pipeline: {repro_note}.\n")

    lines.append("## 1) Learning curve expanding origin 2016→2022 (không đụng holdout)\n")
    lines.append(
        "Mỗi điểm = train trên mọi cặp `year_t < v` rồi chấm trên đúng origin `v` "
        "(cùng kiểu fold với `expanding_origin_folds` của pipeline, chỉ dịch gốc lên 2016). "
        "Trục x là số năm train (origin years 2011–v−1); fold đầu warm-up 2011–2015.\n"
    )
    lines.append("### Ridge hồi quy — R²\n")
    lines.append(md_table(
        ["Origin v", "Số năm train", "n cặp train", "n cặp validation", "R²"],
        [[str(r["origin"]), str(r["n_train_years"]), str(r["n_train_pairs"]),
          str(r["n_val_pairs"]), fmt(r["metric"])] for r in reg_lc],
    ))
    lines.append("")
    lines.append("### LogisticRegression — macro-F1 (nhãn pseudo-label STING, cấu hình đóng băng)\n")
    lines.append(md_table(
        ["Origin v", "Số năm train", "n cặp train", "n cặp validation", "macro-F1"],
        [[str(r["origin"]), str(r["n_train_years"]), str(r["n_train_pairs"]),
          str(r["n_val_pairs"]), fmt(r["metric"])] for r in clf_lc],
    ))
    lines.append("")
    lines.append("- Hình: `results/figs/supervised_learning_curve.png`.\n")

    lines.append(f"## 2) Permutation importance — RF hồi quy (seed {PERM_SEED}, n_repeats={PERM_REPEATS})\n")
    lines.append(
        "`permutation_importance` (scoring R²) của RF spec pipeline, xếp hạng theo mean giảm dần; "
        "khoảng biến thiên = [min, max] trên các lần hoán vị. Bảng train là in-sample; bảng holdout "
        "chỉ mô tả ngoài mẫu — KHÔNG dùng để chọn gì.\n"
    )
    for name, title in (("train", "Trên train 2011–2022 (in-sample)"), ("holdout", "Trên holdout 2023→2024")):
        s = imp_sets[name]
        lines.append(f"### {title}\n")
        lines.append(md_table(
            ["Hạng", "Đặc trưng", "mean", "sd", "[min, max]"],
            [[str(rank), f"`{REGRESSION_FEATURES[i]}` {FEATURE_LABELS[REGRESSION_FEATURES[i]]}",
              fmt(s["mean"][i]), fmt(s["std"][i]), f"[{fmt(s['lo'][i])}, {fmt(s['hi'][i])}]"]
             for rank, i in enumerate(s["order"], start=1)],
        ))
        lines.append("")
    lines.append("- Hình: `results/figs/supervised_importance.png`.\n")

    lines.append("## 3) Residual diagnostics — Ridge trên holdout 2023→2024 (mô tả, không sửa dữ liệu)\n")
    lines.append(
        f"- Holdout {int(hs['n'])} cặp (origin {HOLDOUT_YEAR} → đích {HOLDOUT_YEAR + 1}): "
        f"residual mean {fmt(hs['resid_mean'])}, median {fmt(hs['resid_median'])}, "
        f"sd {fmt(hs['resid_std'])}, min {fmt(hs['resid_min'])}, max {fmt(hs['resid_max'])}, "
        f"MAE {fmt(ridge_mae_holdout)} (residual = thực tế − dự báo).\n"
    )
    lines.append("### 3a) Residual theo năm\n")
    lines.append(
        f"Holdout chỉ có MỘT origin year ({HOLDOUT_YEAR}) nên 'theo năm' trên holdout suy biến "
        "thành một nhóm. Bổ sung bảng out-of-sample theo năm từ chính các cửa sổ learning curve "
        "(Ridge refit trên year_t < v) để thấy trôi theo thời gian — tất cả chỉ mô tả.\n"
    )
    lines.append(md_table(
        ["Origin", "Nguồn", "n cặp", "resid mean", "resid median", "resid sd", "mean abs resid"],
        [[f"{HOLDOUT_YEAR}", "holdout (Ridge fit 2011–2022)", str(int(hs["n"])),
          fmt(hs["resid_mean"]), fmt(hs["resid_median"]), fmt(hs["resid_std"]), fmt(hs["abs_resid_mean"])]]
        + [[str(o), "cửa sổ expanding (refit < o)", str(int(resid_stats(expanding_resid[o])["n"])),
            fmt(resid_stats(expanding_resid[o])["resid_mean"]),
            fmt(resid_stats(expanding_resid[o])["resid_median"]),
            fmt(resid_stats(expanding_resid[o])["resid_std"]),
            fmt(resid_stats(expanding_resid[o])["abs_resid_mean"])]
           for o in sorted(expanding_resid)],
    ))
    lines.append("")
    lines.append("### 3b) Residual theo tỉnh lớn/nhỏ (median dân số GSO năm origin 2023)\n")
    lines.append(
        f"Median dân số 2023 (của chính {int(hs['n'])} tỉnh holdout) = {fmt(pop_median, 2)} nghìn "
        f"người (`{POP_PATH.name}`, cột `gso_pop_total_thousand`); nhóm 'lớn' = ≥ median này, "
        "'nhỏ' = < median.\n"
    )
    lines.append(md_table(
        ["Nhóm", "n tỉnh", "median dân số (nghìn)", "resid mean", "resid median", "resid sd", "mean abs resid"],
        [[g, str(int(by_size.loc[g, "n"])), fmt(float(size_pop_median.loc[g]), 2),
          fmt(float(by_size.loc[g, "mean"])), fmt(float(by_size.loc[g, "median"])),
          fmt(float(by_size.loc[g, "std"])), fmt(float(size_abs_mean.loc[g]))]
         for g in (SIZE_LARGE, SIZE_SMALL)],
    ))
    lines.append("")
    lines.append("### 3c) Top-5 tỉnh lệch nhất theo |residual| (holdout)\n")
    lines.append(md_table(
        ["Hạng", "Tỉnh", "Dân số 2023 (nghìn)", "Nhóm", "Thực tế 2024", "Dự báo", "Residual"],
        [[str(i + 1), str(r["province_vi"]), fmt(float(r["gso_pop_total_thousand"]), 1),
          str(r["nhom"]), fmt(float(r["y"])), fmt(float(r["pred"])), fmt(float(r["resid"]))]
         for i, r in top5.iterrows()],
    ))
    lines.append("")

    lines.append("## Phạm vi & trung thực\n")
    lines.append(
        "- KHÔNG chọn gì trên holdout 2023→2024: không chọn model, không chọn siêu tham số, "
        "không chọn đặc trưng; holdout chỉ xuất hiện ở mục 2/3 với vai trò mô tả.\n"
        f"- Caveat: siêu tham số cố định được chọn bằng CV 2017–2022 của pipeline nên với cửa sổ "
        "learning curve có origin sớm (2016–2017) thông tin đó nằm trong tương lai của cửa sổ — "
        "đây là đặc tả model đã công bố, không phải quy trình chọn lại.\n"
        "- Holdout chỉ 1 năm → mọi kết luận residual ngoài mẫu chỉ mô tả cho (2023→2024), không "
        "khái quát; bảng 3a mở rộng chỉ là mô tả trên các năm CV.\n"
        "- Permutation importance trên train là in-sample; trên holdout chỉ 59 cặp nên khoảng "
        "biến thiên rộng.\n"
        f"- Script này KHÔNG ghi `models/*`, KHÔNG chạy `scripts/predict_sweep.py`, KHÔNG sửa dữ "
        f"liệu, KHÔNG ghi đè artifact đã công bố — chỉ thêm 4 file: `{OUT_MD.name}`, "
        f"`{OUT_CSV.name}`, `{OUT_FIG_LC.name}`, `{OUT_FIG_IMP.name}`.\n"
        f"- Kiểm đối tái lập: "
        f"{ {True: 'ĐẠT', False: 'KHÔNG ĐẠT'}.get(repro_ok, 'NOT_RUN') } — {repro_note}."
    )

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"[Ghi] {OUT_MD} ({len(lines)} dòng)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
