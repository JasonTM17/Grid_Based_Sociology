"""Ứng viên hồi quy CÙNG-GIAO-THỨC cho model đã đóng băng — [THAM KHẢO — CHƯA DUYỆT GV].

Lane nghiên cứu (KHÔNG production): tái dùng ĐÚNG protocol của
`scripts/predict_supervised.py` qua IMPORT (không sao chép):

- `build_regression_pairs` (predict_supervised.py:99-120) → 740 cặp train
  (year_t 2011–2022) + 59 cặp holdout (2023→2024). Holdout KHÔNG fit, KHÔNG
  chọn, KHÔNG chấm, KHÔNG nhìn — mọi so sánh chỉ trên CV train.
- `expanding_origin_folds(tr.year_t, first_validation_origin=2017)`
  (predict_supervised.py:123-147) → 6 fold validation origin 2017–2022,
  warm-up 2011–2016.
- GridSearchCV(cv=folds, scoring='r2', n_jobs=1) như predict_supervised.py:278-285;
  cột báo cáo theo `reg_metrics` (predict_supervised.py:309-316):
  metric_cv='r2 (expanding origin 2017–2022)', value_cv = best_score_ làm tròn 3.
- Baseline tái lập IN-MEMORY bằng refit ĐÚNG lưới công bố (ridge alpha
  {0.1, 1, 10}; RF max_depth {4, 6, None} × min_samples_leaf {1, 2}) trên cùng
  fold, đối chiếu mean với results/supervised_metrics.csv (ridge 0.265 /
  random forest 0.197 / carry-forward 0.145). Lệch → DỪNG, không so sánh.
- Ứng viên ≤6 combo mỗi cái: R1 ElasticNet, R2 HistGradientBoosting,
  R3 KNeighbors, R4 Ridge + biến ngoài (quy tắc pre-registered: cột ngoài thiếu
  >30% trên 740 cặp train → bị LOẠI khỏi ma trận cùng-protocol; lý do loại
  được ghi rõ trong output, không loại im lặng).
- Ngưỡng thắng (pre-registered): (i) value_cv > ridge 0.265 VÀ (ii) beat
  per-fold ridge-best trên ≥4/6 fold → verdict beat / noise / worse.

CHỈ ghi tệp phân tích MỚI: results/candidates_regression.{md,csv}. CẤM ghi
models/predict_config.json, models/*.joblib, results/supervised_metrics.csv,
results/predict_all_years.csv và mọi artifact đóng băng. KHÔNG đưa PCI vào
features (giữ vai trò external validation độc lập đã công bố,
reports/model_deep_dive.md:53); KHÔNG chạy ablation bỏ sd_6_1 (đổi spec công bố
— đề xuất (b).1 chờ GV, reports/model_deep_dive.md:295).

Chạy: python -E scripts/candidates_regression.py   (từ thư mục gốc repo)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from papi_pred_common import REGRESSION_FEATURES, REGRESSION_TARGET, load_panel  # noqa: E402
from predict_supervised import (  # noqa: E402
    HOLDOUT_YEAR,
    build_regression_pairs,
    expanding_origin_folds,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS = ROOT / "results"
MD_PATH = RESULTS / "candidates_regression.md"
CSV_PATH = RESULTS / "candidates_regression.csv"

SEED = 11  # seed môi trường (phòng hờ); mọi estimator dưới đây đều deterministic
N_TRAIN_PAIRS = 740   # year_t 2011–2022 (đối chiếu design)
N_HOLDOUT_PAIRS = 59  # year_t 2023 (chỉ kiểm tra kích thước, KHÔNG chấm)
FIRST_VALIDATION_ORIGIN = 2017  # predict_supervised.py:123-147 + CLASSIFICATION_CV_FIRST_YEAR

# Số CÔNG BỐ trong results/supervised_metrics.csv — chỉ dùng làm MỐC so sánh
# (selection luôn theo value_cv, scripts/papi_pred_common.py:60-66).
PUBLISHED_RIDGE = 0.265
PUBLISHED_RF = 0.197
PUBLISHED_CARRY = 0.145
PUBLISHED_CSV = ROOT / "results" / "supervised_metrics.csv"

METRIC_CV = "r2 (expanding origin 2017–2022)"  # chuỗi y hệt reg_metrics:309-316

# Biến ngoài: (tên cột, tệp, tên ứng viên) — join theo (province_code, year_t),
# KHÔNG BAO GIỜ join năm t+1 (chống tin tức tương lai).
EXTERNAL_COLUMNS = [
    (
        "poverty_rate_pct",
        ROOT / "data" / "processed" / "external_poverty_63.csv",
        "R4 Ridge+poverty",
    ),
    (
        "grdp_per_capita_million_vnd",
        ROOT / "data" / "processed" / "external_gso_grdp_63.csv",
        "R4 Ridge+GRDP",
    ),
    (
        "gso_urban_residence_pct_derived",
        ROOT / "data" / "processed" / "external_gso_population_63_full.csv",
        "R4 Ridge+urban",
    ),
]
MISSING_EXCLUDE_FRAC = 0.30  # quy tắc pre-registered: thiếu >30% trên 740 cặp train → LOẠI

FOLD_YEARS = tuple(range(FIRST_VALIDATION_ORIGIN, HOLDOUT_YEAR))  # 2017..2022 = 6 fold
FOLDS_BEAT_MIN = 4  # điều kiện (ii) của ngưỡng thắng


def fold_best_scores(grid: GridSearchCV, n_folds: int) -> list[float]:
    """Per-fold R² của COMBO BEST (best_index_) — fit fold-train, chấm fold-val."""
    best_index = int(grid.best_index_)
    res = grid.cv_results_
    return [float(res[f"split{i}_test_score"][best_index]) for i in range(n_folds)]


def reproduce_baselines(X: np.ndarray, y: np.ndarray, reg_cv) -> tuple[GridSearchCV, GridSearchCV]:
    """Refit ĐÚNG lưới công bố của predict_supervised.py:276-285 trên cùng fold."""
    ridge = Pipeline([("sc", StandardScaler()), ("m", Ridge(random_state=42))])
    grid_ridge = GridSearchCV(
        ridge, {"m__alpha": [0.1, 1.0, 10.0]}, cv=reg_cv, scoring="r2", n_jobs=1
    )
    rf_reg = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=1)
    grid_rf = GridSearchCV(
        rf_reg,
        {"max_depth": [4, 6, None], "min_samples_leaf": [1, 2]},
        cv=reg_cv, scoring="r2", n_jobs=1,
    )
    grid_ridge.fit(X, y)
    grid_rf.fit(X, y)
    return grid_ridge, grid_rf


def candidate_specs(ext_col: str | None) -> list[dict]:
    """Ứng viên — mỗi cái ≤6 combo (bias chọn-lưới tương đương lưới công bố)."""
    specs: list[dict] = [
        {
            "name": "R1 ElasticNet",
            "model": Pipeline(
                [("sc", StandardScaler()), ("m", ElasticNet(random_state=42))]
            ),
            "grid": {"m__alpha": [0.01, 0.1, 1.0], "m__l1_ratio": [0.2, 0.8]},
            "ext_col": None,
            "note": "Pipeline [StandardScaler, ElasticNet] — kiểm tra trộn L1 vào L2",
        },
        {
            "name": "R2 HistGradientBoosting",
            "model": HistGradientBoostingRegressor(
                random_state=42, early_stopping=False, max_iter=200
            ),
            "grid": {"max_leaf_nodes": [8, 15, 31], "learning_rate": [0.05, 0.1]},
            "ext_col": None,
            "note": "boosting (bias quy nạp khác RF bagging); early_stopping=False "
            "tránh split validation nội bộ, giữ giao thức thuần",
        },
        {
            "name": "R3 KNeighbors",
            "model": Pipeline([("sc", StandardScaler()), ("m", KNeighborsRegressor())]),
            "grid": {"m__n_neighbors": [5, 10, 20], "m__weights": ["uniform", "distance"]},
            "ext_col": None,
            "note": "quy nạp cục bộ trong không gian 8 chiều đã scale",
        },
    ]
    if ext_col is not None:
        specs.append(
            {
                "name": "R4 Ridge+poverty",
                "model": Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("sc", StandardScaler()),
                        ("m", Ridge(random_state=42)),
                    ]
                ),
                "grid": {"m__alpha": [0.1, 1.0, 10.0]},  # GIỐNG HỆT lưới ridge công bố
                "ext_col": ext_col,
                "note": "Pipeline [SimpleImputer(median, add_indicator), StandardScaler, "
                "Ridge] — delta tiền xử lý có imputer so với pipeline công bố",
            }
        )
    return specs


def load_external_column(keys: pd.DataFrame, col: str, path: Path) -> np.ndarray:
    """Cột ngoài join theo (province_code, year_t) — không bao giờ năm t+1."""
    ext = pd.read_csv(path)
    if ext.duplicated(["province_code", "year"]).any():
        raise ValueError(f"{path.name}: có (province_code, year) trùng — không join an toàn.")
    joined = keys[["province_code", "year_t"]].merge(
        ext[["province_code", "year", col]],
        left_on=["province_code", "year_t"],
        right_on=["province_code", "year"],
        how="left",
    )
    if len(joined) != len(keys):
        raise ValueError(f"{path.name}: merge làm thay đổi số dòng {len(keys)}.")
    return joined[col].to_numpy(dtype=float)


def external_missingness(keys: pd.DataFrame) -> list[dict]:
    """% thiếu của từng cột ngoài trên ĐÚNG 740 cặp train (quy tắc pre-registered).

    `keys` đã qua gate `verify_key_alignment` — khớp position-wise với frame
    cặp `tr`, nên % thiếu tính trên keys == % thiếu trên 740 cặp train.
    """
    out = []
    for col, path, cand in EXTERNAL_COLUMNS:
        ext = pd.read_csv(path)
        joined = keys[["province_code", "year_t"]].merge(
            ext[["province_code", "year", col]],
            left_on=["province_code", "year_t"],
            right_on=["province_code", "year"],
            how="left",
        )
        n_missing = int(joined[col].isna().sum())
        out.append(
            {
                "candidate": cand,
                "column": col,
                "source": path.name,
                "n_missing": n_missing,
                "n_pairs": len(keys),
                "frac": n_missing / len(keys),
            }
        )
    return out


def pair_join_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Dựng lại (province_code, year_t) của từng cặp để join biến ngoài.

    `build_regression_pairs` (predict_supervised.py:99-120) không trả
    province_code trong frame cặp. Hàm này dựng lại tập key (province_code,
    year_t) theo ĐÚNG điều kiện cặp hợp lệ của builder (features năm t đủ,
    target năm t+1 đủ), rồi `verify_key_alignment` so từng phần tử với frame
    cặp thật trước khi bất kỳ join nào được phép chạy — nếu lệch, script DỪNG.
    """
    tgt = df[["province_code", "year", REGRESSION_TARGET]].rename(
        columns={"year": "year_t", REGRESSION_TARGET: "y_next"}
    )
    tgt["year_t"] = tgt["year_t"] - 1  # target năm t+1 gán về origin t
    tgt = tgt.dropna(subset=["y_next"])
    cur = df[["province_code", "year"] + REGRESSION_FEATURES].rename(
        columns={"year": "year_t"}
    )
    keys = cur.merge(tgt, on=["province_code", "year_t"], how="inner")
    keys = keys[keys["year_t"] < HOLDOUT_YEAR].dropna(subset=REGRESSION_FEATURES)
    keys = keys.sort_values("year_t", kind="stable").reset_index(drop=True)
    return keys


def verify_key_alignment(keys: pd.DataFrame, tr: pd.DataFrame) -> bool:
    """Kiểm chứng position-wise: key đúng thứ tự cặp của build_regression_pairs."""
    if len(keys) != len(tr):
        return False
    checks = [
        np.array_equal(
            keys[REGRESSION_FEATURES].to_numpy(dtype=float),
            tr[REGRESSION_FEATURES].to_numpy(dtype=float),
        ),
        np.array_equal(
            keys[REGRESSION_TARGET].to_numpy(dtype=float),
            tr["carry"].to_numpy(dtype=float),
        ),
        np.array_equal(
            keys["y_next"].to_numpy(dtype=float), tr["y"].to_numpy(dtype=float)
        ),
        np.array_equal(
            keys["year_t"].to_numpy(dtype=int), tr["year_t"].to_numpy(dtype=int)
        ),
    ]
    return all(checks)


def fmt_params(params: dict) -> str:
    return " ".join(f"{k}={params[k]}" for k in sorted(params))


def verdict_label(value_cv: float, folds_beat: int) -> str:
    """Verdict pre-registered: beat = (i)+(ii); noise = đúng một; worse = không cái nào."""
    above = value_cv > PUBLISHED_RIDGE          # (i) vượt mốc ridge 0.265
    consistent = folds_beat >= FOLDS_BEAT_MIN   # (ii) beat per-fold ridge ≥4/6
    if above and consistent:
        return "beat"
    if above or consistent:
        return "noise"
    return "worse"


def main() -> int:
    np.random.seed(SEED)
    RESULTS.mkdir(exist_ok=True)

    # ---------------- Giao thức: import đúng từ predict_supervised.py -------- #
    df = load_panel()
    pairs = build_regression_pairs(df)
    tr = pairs[pairs.year_t < HOLDOUT_YEAR].reset_index(drop=True)
    te = pairs[pairs.year_t == HOLDOUT_YEAR]
    if len(tr) != N_TRAIN_PAIRS or len(te) != N_HOLDOUT_PAIRS:
        print(
            f"[GATE] Kích thước cặp lệch design: train {len(tr)} (cần {N_TRAIN_PAIRS}), "
            f"holdout {len(te)} (cần {N_HOLDOUT_PAIRS}) — DỪNG."
        )
        return 1
    # te (holdout 2023→2024) CHỈ được kiểm tra kích thước phía trên — không chấm.

    # Join-key (province_code, year_t) phải khớp position-wise với frame cặp
    # của build_regression_pairs trước khi biến ngoài được join — lệch thì DỪNG.
    keys = pair_join_keys(df)
    if not verify_key_alignment(keys, tr):
        print(
            "[GATE] Join-key (province_code, year_t) KHÔNG khớp position-wise với "
            "frame cặp của build_regression_pairs — DỪNG, không join biến ngoài."
        )
        return 1
    print(
        f"[Gate] join-key khớp position-wise {len(keys)}/{len(tr)} cặp "
        "(features + carry + y + year_t so từng phần tử)."
    )

    X = tr[REGRESSION_FEATURES].to_numpy()
    y = tr["y"].to_numpy()
    reg_cv = expanding_origin_folds(
        tr["year_t"].to_numpy(), first_validation_origin=FIRST_VALIDATION_ORIGIN
    )
    n_folds = len(reg_cv)
    val_years = [int(tr["year_t"].to_numpy()[va][0]) for _, va in reg_cv]
    if n_folds != len(FOLD_YEARS) or tuple(val_years) != FOLD_YEARS:
        print(f"[GATE] Fold lệch design: origins {val_years} — DỪNG.")
        return 1
    train_sizes = [int(len(tr_idx)) for tr_idx, _ in reg_cv]
    print(
        f"[Protocol] train {len(tr)} cặp (2011–2022) · holdout {len(te)} cặp "
        f"(KHÔNG chấm) · {n_folds} fold origin {val_years[0]}–{val_years[-1]}, "
        f"warm-up 2011–{val_years[0] - 1}"
    )

    # ---------------- Baseline tái lập IN-MEMORY trên cùng fold -------------- #
    grid_ridge, grid_rf = reproduce_baselines(X, y, reg_cv)
    ridge_raw = float(grid_ridge.best_score_)
    rf_raw = float(grid_rf.best_score_)
    ridge_folds = fold_best_scores(grid_ridge, n_folds)
    rf_folds = fold_best_scores(grid_rf, n_folds)

    carry_all = tr["carry"].to_numpy()
    carry_folds = [float(r2_score(y[va], carry_all[va])) for _, va in reg_cv]
    carry_raw = float(np.mean(carry_folds))

    # GATE quy tắc pre-registered số 6: đối chiếu với số công bố trước khi so.
    gate = [
        ("ridge", ridge_raw, PUBLISHED_RIDGE),
        ("random forest", rf_raw, PUBLISHED_RF),
        ("carry-forward", carry_raw, PUBLISHED_CARRY),
    ]
    gate_ok = True
    for name, raw, published in gate:
        ok = round(raw, 3) == published
        gate_ok = gate_ok and ok
        print(
            f"[Gate] {name}: tái lập {raw:.6f} → round 3 = {round(raw, 3)} | "
            f"công bố ({PUBLISHED_CSV.name}) = {published} | {'KHỚP' if ok else 'LỆCH'}"
        )
    if not gate_ok:
        print(
            "[Gate] Baseline tái lập LỆCH số công bố — DỪNG theo quy tắc số 6: "
            "không tin so sánh ứng viên. Không ghi tệp output."
        )
        return 1

    # ---------------- Biến ngoài: áp quy tắc loại pre-registered ------------- #
    miss = external_missingness(keys)
    kept_ext: list[dict] = []
    excluded_ext: list[dict] = []
    for m in miss:
        if m["frac"] > MISSING_EXCLUDE_FRAC:
            excluded_ext.append(m)
            print(
                f"[Exclude] {m['candidate']} — cột {m['column']} thiếu "
                f"{m['frac']:.1%} ({m['n_missing']}/{m['n_pairs']} cặp train) > "
                f"{MISSING_EXCLUDE_FRAC:.0%} → LOẠI (quy tắc pre-registered)."
            )
        else:
            kept_ext.append(m)
            print(
                f"[Keep] {m['candidate']} — cột {m['column']} thiếu "
                f"{m['frac']:.1%} ({m['n_missing']}/{m['n_pairs']} cặp train) ≤ "
                f"{MISSING_EXCLUDE_FRAC:.0%} → GIỮ, impute trong fold."
            )

    ext_col = kept_ext[0]["column"] if kept_ext else None

    # ---------------- Chạy ứng viên trên cùng fold --------------------------- #
    rows: list[dict] = []

    def add_row(
        name: str,
        n_combos: int,
        best_params: str,
        raw: float | None,
        folds: list[float] | None,
        folds_beat: int | None,
        verdict: str,
        note: str,
    ) -> None:
        value_cv = round(raw, 3) if raw is not None else None
        rows.append(
            {
                "candidate": name,
                "metric_cv": METRIC_CV,
                "n_combos": n_combos,
                "best_params": best_params,
                "value_cv_raw": "" if raw is None else f"{raw:.6f}",
                "value_cv": "" if value_cv is None else f"{value_cv:.3f}",
                **{
                    f"fold_{yr}": "" if folds is None else f"{folds[i]:.4f}"
                    for i, yr in enumerate(FOLD_YEARS)
                },
                "folds_beat_ridge_of6": "" if folds_beat is None else f"{folds_beat}/6",
                "delta_vs_ridge_0265": ""
                if value_cv is None
                else f"{value_cv - PUBLISHED_RIDGE:+.3f}",
                "delta_vs_carry_0145": ""
                if value_cv is None
                else f"{value_cv - PUBLISHED_CARRY:+.3f}",
                "verdict": verdict,
                "note": note,
            }
        )

    add_row(
        "baseline: ridge (lưới công bố, tái lập)",
        3,
        fmt_params(grid_ridge.best_params_),
        ridge_raw,
        ridge_folds,
        None,
        "baseline",
        f"mốc công bố {PUBLISHED_RIDGE}; per-fold dùng làm mốc nhất quán (ii)",
    )
    add_row(
        "baseline: random forest (lưới công bố, tái lập)",
        6,
        fmt_params(grid_rf.best_params_),
        rf_raw,
        rf_folds,
        None,
        "baseline",
        f"mốc công bố {PUBLISHED_RF}",
    )
    add_row(
        "baseline: carry-forward (giữ giá trị năm nay)",
        1,
        "",
        carry_raw,
        carry_folds,
        None,
        "baseline",
        f"mốc công bố {PUBLISHED_CARRY}; không fit",
    )

    kept_cols = {m["column"] for m in kept_ext}
    ext_arrays = {
        c: load_external_column(keys, c, p)
        for c, p, _cand in EXTERNAL_COLUMNS
        if c in kept_cols
    }

    for spec in candidate_specs(ext_col):
        if spec["ext_col"] is not None:
            Xs = np.column_stack([X, ext_arrays[spec["ext_col"]]])
        else:
            Xs = X
        n_combos = int(np.prod([len(v) for v in spec["grid"].values()]))
        print(f"[Candidate] {spec['name']}: fit GridSearchCV ({n_combos} combo)…")
        grid = GridSearchCV(spec["model"], spec["grid"], cv=reg_cv, scoring="r2", n_jobs=1)
        grid.fit(Xs, y)
        raw = float(grid.best_score_)
        folds = fold_best_scores(grid, n_folds)
        folds_beat = sum(1 for a, b in zip(folds, ridge_folds) if a > b)
        add_row(
            spec["name"],
            n_combos,
            fmt_params(grid.best_params_),
            raw,
            folds,
            folds_beat,
            verdict_label(raw, folds_beat),
            spec["note"],
        )
        print(
            f"[Candidate] {spec['name']}: value_cv={round(raw, 3)} "
            f"(raw {raw:.6f}) best={fmt_params(grid.best_params_)} | "
            f"beat ridge per-fold {folds_beat}/{n_folds} → "
            f"{verdict_label(raw, folds_beat)}"
        )

    for m in excluded_ext:
        add_row(
            m["candidate"],
            3,
            "",
            None,
            None,
            None,
            "EXCLUDED",
            f"LOẠI theo quy tắc pre-registered: cột {m['column']} thiếu "
            f"{m['frac']:.1%} ({m['n_missing']}/{m['n_pairs']} cặp train) > "
            f"{MISSING_EXCLUDE_FRAC:.0%} — nguồn {m['source']}",
        )

    # ---------------- Ghi output (chỉ 2 tệp phân tích MỚI) ------------------- #
    csv_header = list(rows[0].keys())
    with open(CSV_PATH, "w", encoding="utf-8", newline="\n") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(csv_header)
        for r in rows:
            writer.writerow([r[k] for k in csv_header])

    md = build_markdown(
        rows=rows,
        ridge_raw=ridge_raw,
        rf_raw=rf_raw,
        carry_raw=carry_raw,
        ridge_folds=ridge_folds,
        rf_folds=rf_folds,
        carry_folds=carry_folds,
        val_years=val_years,
        train_sizes=train_sizes,
        miss=miss,
        excluded=excluded_ext,
        kept=kept_ext,
        n_train=len(tr),
        n_holdout=len(te),
    )
    with open(MD_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)

    print(f"\nđã lưu: {CSV_PATH.name}, {MD_PATH.name} (chỉ tệp phân tích MỚI)")
    return 0


def build_markdown(
    rows: list[dict],
    ridge_raw: float,
    rf_raw: float,
    carry_raw: float,
    ridge_folds: list[float],
    rf_folds: list[float],
    carry_folds: list[float],
    val_years: list[int],
    train_sizes: list[int],
    miss: list[dict],
    excluded: list[dict],
    kept: list[dict],
    n_train: int,
    n_holdout: int,
) -> str:
    """Sinh results/candidates_regression.md — mọi số truyền vào đã tính ở main()."""
    f4 = lambda v: f"{v:.4f}"  # noqa: E731
    ran_rows = [r for r in rows if r["candidate"].startswith("R") and r["verdict"] != "EXCLUDED"]
    n_combos_total = sum(int(r["n_combos"]) for r in ran_rows)
    lines: list[str] = []
    lines.append("# Ứng viên hồi quy cùng-giao-thức — [THAM KHẢO — CHƯA DUYỆT GV]\n")
    lines.append(
        "**Trạng thái:** lane nghiên cứu ứng viên — KHÔNG thay model production, KHÔNG ghi "
        "artifact đóng băng (`models/predict_config.json`, `results/supervised_metrics.csv`, "
        "`results/predict_all_years.csv`, `models/*.joblib`). Nhãn theo quy ước "
        "`reports/model_deep_dive.md:9-14`; việc thay spec/config công bố (chọn model mới, "
        "thêm feature ngoài, đổi thuật toán cụm) thuộc nhóm (b) — cần GV duyệt và re-run "
        "theo quy trình đóng băng (`reports/model_deep_dive.md:293-299`).\n"
    )
    lines.append(
        f"**Tính EXPLORATORY — không phải kết luận:** ma trận hồi quy này gồm "
        f"{n_combos_total} combo ("
        + " + ".join(str(int(r["n_combos"])) for r in ran_rows)
        + "), mỗi combo chấm 6 fold — nhiều nơi có thể vượt mốc do may rủi. KHÔNG tuyên bố "
        "p-value hay hiệu chỉnh alpha hình thức; guard chống fishing là quy tắc nhất quán "
        "pre-registered (mục 4) + duyệt GV.\n"
    )

    lines.append("## 1) Giao thức — tái dùng qua import (không sao chép)\n")
    lines.append(
        f"- `build_regression_pairs` (`scripts/predict_supervised.py:99-120`) → {n_train} cặp "
        f"**train** (year_t 2011–2022) + {n_holdout} cặp holdout (2023→2024). Holdout: KHÔNG "
        "fit, KHÔNG chọn, KHÔNG chấm, KHÔNG nhìn — script chỉ kiểm tra kích thước 59 cặp theo "
        "design; số holdout của `results/supervised_metrics.csv` không được tham chiếu khi "
        "quyết định ứng viên (`select_model_by_cv` vốn chỉ đọc `value_cv`, "
        "`scripts/papi_pred_common.py:60-66`)."
    )
    lines.append(
        f"- Folds: `expanding_origin_folds(tr.year_t, first_validation_origin=2017)` "
        f"(`scripts/predict_supervised.py:123-147`) → {len(val_years)} fold validation origin "
        f"{val_years[0]}–{val_years[-1]}, warm-up 2011–{val_years[0] - 1}; kích thước fold-train: "
        + ", ".join(str(s) for s in train_sizes)
        + "."
    )
    lines.append(
        "- Chấm điểm: `GridSearchCV(cv=folds, scoring='r2', n_jobs=1)` như "
        "`scripts/predict_supervised.py:278-285`; cột báo cáo y hệt `reg_metrics` "
        "(`scripts/predict_supervised.py:309-316`): `metric_cv` = "
        f"'{METRIC_CV}', `value_cv` = best_score_ làm tròn 3."
    )
    lines.append(
        f"- Đặc trưng: 8 cột `REGRESSION_FEATURES` (`scripts/papi_pred_common.py:19-22`), target "
        f"`{REGRESSION_TARGET}` năm t+1. KHÔNG đưa PCI vào features (giữ vai trò external "
        "validation độc lập đã công bố, H=31.7751 — `reports/model_deep_dive.md:53`). KHÔNG "
        "chạy ablation bỏ `sd_6_1` (đổi spec công bố — đề xuất (b).1 chờ GV, "
        "`reports/model_deep_dive.md:295`).\n"
    )

    lines.append("## 2) Gate tái lập baseline (quy tắc pre-registered số 6)\n")
    lines.append(
        "Mọi baseline được TÍNH LẠI in-memory trên cùng fold bằng refit ĐÚNG lưới công bố "
        "(`scripts/predict_supervised.py:276-285`) — không hardcode số từ CSV. Đối chiếu mean "
        "với `results/supervised_metrics.csv` trước khi so ứng viên; nếu lệch → script DỪNG, "
        "không ghi output.\n"
    )
    lines.append("| Baseline | Tái lập (raw) | round 3 | Công bố CSV | Kết quả |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, raw, published in (
        ("ridge — alpha {0.1, 1, 10}", ridge_raw, PUBLISHED_RIDGE),
        ("random forest — depth {4,6,None} × leaf {1,2}", rf_raw, PUBLISHED_RF),
        ("carry-forward (không fit)", carry_raw, PUBLISHED_CARRY),
    ):
        ok = "KHỚP" if round(raw, 3) == published else "LỆCH → DỪNG"
        lines.append(f"| {name} | {raw:.6f} | {round(raw, 3):.3f} | {published:.3f} | {ok} |")
    lines.append("")
    lines.append(
        "Per-fold R² của combo best (mốc cho điều kiện nhất quán (ii)):"
    )
    lines.append("")
    lines.append("| Baseline | " + " | ".join(f"origin {yr}" for yr in val_years) + " | mean |")
    lines.append("| --- | " + " | ".join("---" for _ in val_years) + " | --- |")
    for name, folds, raw in (
        ("ridge-best", ridge_folds, ridge_raw),
        ("RF-best", rf_folds, rf_raw),
        ("carry-forward", carry_folds, carry_raw),
    ):
        lines.append(
            f"| {name} | " + " | ".join(f4(v) for v in folds) + f" | {raw:.4f} |"
        )
    lines.append("")

    lines.append("## 3) Biến ngoài — quy tắc loại pre-registered\n")
    lines.append(
        f"Quy tắc (pre-registered trước khi chạy): cột ngoài thiếu >{MISSING_EXCLUDE_FRAC:.0%} "
        f"trên {n_train} cặp train → ứng viên ĐÓ BỊ LOẠI khỏi ma trận cùng-protocol. Join theo "
        "(province_code, year_t) — KHÔNG BAO GIỜ join năm t+1 (chống tin tức tương lai). "
        "`build_regression_pairs` không trả province_code trong frame cặp "
        "(`scripts/predict_supervised.py:112-119`), nên script dựng lại join-key (province_code, "
        "year_t) theo đúng điều kiện cặp hợp lệ của builder và gate `verify_key_alignment` so "
        "từng phần tử (8 features + carry + y + year_t, position-wise) với frame cặp thật — "
        "khớp 740/740 thì join mới được phép chạy, lệch thì script DỪNG.\n"
    )
    lines.append("| Ứng viên | Cột | Nguồn | Thiếu trên 740 cặp | % | Quy tắc |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for m in miss:
        action = (
            "GIỮ — impute trong fold" if m in kept else "LOẠI — lý do ghi rõ, không loại im lặng"
        )
        lines.append(
            f"| {m['candidate']} | `{m['column']}` | {m['source']} | "
            f"{m['n_missing']}/{m['n_pairs']} | {m['frac']:.1%} | {action} |"
        )
    lines.append("")
    if excluded:
        for m in excluded:
            lines.append(
                f"- **LOẠI {m['candidate']}:** cột `{m['column']}` thiếu {m['frac']:.1%} "
                f"({m['n_missing']}/{m['n_pairs']} cặp train) > {MISSING_EXCLUDE_FRAC:.0%} "
                f"(nguồn {m['source']}) — KHÔNG chạy, không im lặng."
            )
    if kept:
        m = kept[0]
        lines.append(
            f"- **GIỮ {m['candidate']}:** cột `{m['column']}` thiếu {m['frac']:.1%} "
            f"({m['n_missing']}/{m['n_pairs']} cặp train) ≤ {MISSING_EXCLUDE_FRAC:.0%} "
            "(nguồn " + m['source'] + ") — được chạy với impute trong fold."
        )
    lines.append(
        "\n**Delta tiền xử lý được khai báo:** pipeline R4 có `SimpleImputer(strategy='median', "
        "add_indicator=True)` — pipeline công bố KHÔNG có imputer. Imputer nằm trong Pipeline "
        "nên GridSearchCV refit từng fold = imputer fit trên fold-train thôi → không rò rỉ. "
        "Lưới alpha của R4 GIỐNG HỆT lưới ridge công bố ({0.1, 1.0, 10.0}) để tách đúng hiệu "
        "ứng ĐẶC TRÙNG khỏi hiệu ứng siêu tham số.\n"
    )

    lines.append("## 4) Ngưỡng thắng (pre-registered trước khi chạy)\n")
    lines.append(
        f"Ứng viên thắng CHỈ khi (i) `value_cv` > mốc đã công bố trên CÙNG metric (ridge R² "
        f"{PUBLISHED_RIDGE:.3f}) VÀ (ii) nhất quán từng fold: beat per-fold score của ridge-best "
        f"(tái lập in-memory, mục 2) trên ≥ {FOLDS_BEAT_MIN}/6 fold. "
        f"Verdict: `beat` = (i)+(ii) đều đạt; `noise` = đúng một trong hai; `worse` = không "
        "cái nào. Cấm trích 1 fold đẹp; cấm đổi metric/fold sau khi thấy số. So thêm với "
        f"carry-forward {PUBLISHED_CARRY:.3f} (mốc yếu hơn) chỉ để tham khảo.\n"
    )

    lines.append("## 5) Bảng kết quả (CV train expanding origin 2017–2022)\n")
    lines.append(
        "| Ứng viên | combos | best combo | R² CV | "
        + " | ".join(f"{yr}" for yr in val_years)
        + " | beat ridge /6 | Δ vs ridge 0.265 | Δ vs carry 0.145 | Verdict |"
    )
    lines.append(
        "| --- | --- | --- | --- | "
        + " | ".join("---" for _ in val_years)
        + " | --- | --- | --- | --- |"
    )
    for r in rows:
        fold_cells = " | ".join(r[f"fold_{yr}"] for yr in val_years)
        lines.append(
            f"| {r['candidate']} | {r['n_combos']} | {r['best_params'] or '—'} | "
            f"{r['value_cv'] or '—'} | {fold_cells} | {r['folds_beat_ridge_of6'] or '—'} | "
            f"{r['delta_vs_ridge_0265'] or '—'} | {r['delta_vs_carry_0145'] or '—'} | "
            f"**{r['verdict']}** |"
        )
    lines.append("")

    lines.append("## 6) Ghi chú nguồn cột ứng viên (lý do thiết kế)\n")
    lines.append(
        "- **R1 ElasticNet:** Ridge (best CV 0.265) là thuần L2; ElasticNet kiểm tra xem trộn L1 "
        "có cắt bớt 7 đặc trưng nhiễu (mỗi cái chỉ đóng góp 0.006–0.031 theo permutation, "
        "`reports/model_deep_dive.md:244-246`) và tổng quát hóa tốt hơn không, cùng pipeline "
        "chuẩn hóa."
    )
    lines.append(
        "- **R2 HistGradientBoosting:** boosting là bias quy nạp khác RF (bagging) — kiểm tra "
        "trực tiếp liệu nonlinear/interaction có vượt RF CV 0.197 và ridge 0.265 hay không; "
        "n≈740 dễ overfit nên lưới ngắn + cố định số vòng (max_iter=200) + "
        "early_stopping=False."
    )
    lines.append(
        "- **R3 KNeighbors:** quy nạp cục bộ (hàng xóm trong không gian 8 chiều đã scale) — "
        "bias hoàn toàn khác linear toàn cục và cây; dự kiến yếu trong 8-D n nhỏ nhưng rẻ và "
        "đủ để loại trừ giả thuyết."
    )
    lines.append(
        "- **R4 Ridge+poverty:** tách hiệu ứng đặc trưng ngoài (tỉ lệ nghèo GSO) khỏi hiệu ứng "
        "siêu tham số bằng cách giữ nguyên lưới alpha công bố; imputer trong pipeline (delta "
        "tiền xử lý — khai báo ở mục 3).\n"
    )

    lines.append("## 7) Trung thực + determinism\n")
    lines.append(
        "- `value_cv` là best_score_ của GridSearchCV trên chính 6 fold (không nested CV) → hơi "
        "lạc quan, đúng disclosure đã công bố trong `results/supervised_summary.md`."
    )
    beat_rows = [r for r in ran_rows if r["verdict"] == "beat"]
    worse_rows = [r for r in ran_rows if r["verdict"] == "worse"]
    if beat_rows:
        lines.append(
            "- **Đọc kết quả `beat` biên mỏng:** "
            + "; ".join(
                f"{r['candidate']} raw {r['value_cv_raw']} (Δ vs ridge-best tái lập = "
                f"{float(r['value_cv_raw']) - ridge_raw:+.4f}, beat "
                f"{r['folds_beat_ridge_of6']})"
                for r in beat_rows
            )
            + " — đạt ngưỡng pre-registered nhưng biên nằm trong vùng nhiễu của "
            "best_score_ (bullet trên) và thua ridge ở 1–2 fold origin sớm; verdict `beat` ở "
            "đây là ĐẠT NGƯỠNG KỸ THUẬT, KHÔNG phải bằng chứng superiority. Adoption vẫn "
            "thuộc GV (nhóm (b))."
        )
    if worse_rows:
        lines.append(
            "- **Ứng viên kém — ghi kém, không làm đẹp:** "
            + "; ".join(
                f"{r['candidate']} value_cv {r['value_cv']} (Δ vs ridge "
                f"{r['delta_vs_ridge_0265']}, beat {r['folds_beat_ridge_of6']})"
                for r in worse_rows
            )
            + "."
        )
    lines.append(
        "- Kết quả là **THAM KHẢO [CHƯA DUYỆT GV]** — adoption cần GV duyệt (nhóm (b)); script "
        "KHÔNG ghi bất kỳ artifact đóng băng nào."
    )
    lines.append(
        f"- Determinism: numpy seed {SEED} (phòng hờ); estimator dùng đúng `random_state=42` "
        "theo thiết kế ứng viên và khớp SEED công bố (`scripts/predict_supervised.py:72`) cho "
        "baseline RF; ElasticNet (coordinate descent), HGB (early_stopping=False), KNN, Ridge "
        "đều deterministic và không tiêu thụ seed tự do. Yêu cầu kiểm chứng: chạy 2 lần → "
        "md/csv sha256 byte-giống (kiểm chứng do verify lane thực hiện ngoài tệp này)."
    )
    lines.append(
        f"- Môi trường chạy: python {sys.version.split()[0]}, sklearn {sklearn.__version__}, "
        f"pandas {pd.__version__}, numpy {np.__version__}."
    )
    lines.append(
        "- Tệp ghi: `results/candidates_regression.csv` + tệp này. Không tệp khác.\n"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
