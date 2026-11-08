"""Ứng viên phân loại (lane CLF) — tái dùng NGUYÊN VĂN protocol ``predict_supervised.py``.

CHỈ chấm trên CV train expanding origin 2017–2022 — holdout 2023→2024 KHÔNG fit,
KHÔNG chọn, KHÔNG chấm, KHÔNG nhìn (kể cả cột ``holdout_*`` của
``results/supervised_metrics.csv`` — chỉ đọc cột ``value_cv`` của task
classification để đối chiếu baseline).

Protocol tái dụng (import trực tiếp, KHÔNG sao chép code):
- ``build_classification_pairs`` (scripts/predict_supervised.py:187-211) với cfg
  đọc từ ``models/predict_config.json`` (CHỈ ĐỌC): features sd_4_2+sd_6_1,
  STING n_levels=3/factor=4/min_count=5/cluster_level=2, connectivity=1 —
  ``feats`` quyết định KHÔNG GIAN NHÃN STING; ma trận X của classifier là 8 cột
  ``FEATURES`` theo đúng pipeline (:199, :207, :338).
- ``expanding_year_splits`` (:214-233) → 6 fold validation origin 2017–2022
  (warm-up 2011–2016).
- ``CLASSIFICATION_SCORER`` (:75-77) = ``make_scorer(f1_score, average="macro",
  labels=[0, 1], zero_division=0)`` — nguyên văn, không đổi.
- Baseline tái lập IN-MEMORY trên cùng fold (không hardcode số từ CSV):
  LR lưới C {0.1, 0.3, 1.0} (:342-346), RF max_depth {3, 6, None} ×
  min_samples_leaf {1, 2} (:344, :347-348), majority = ``expanding_majority_f1``
  (:236-251), "always dự đoán 1" nguyên văn :530-542. Mean được đối chiếu với
  ``results/supervised_metrics.csv`` (và 0.400 của always-1 với
  ``results/supervised_summary.md:31``) TRƯỚC khi so ứng viên — LỆCH → DỪNG.

Ứng viên (3, theo đề bài pre-registered):
- C1 ``LogisticRegression(class_weight="balanced")`` — lưới C {0.1, 0.3, 1.0}
  Y HỆT lưới công bố (chênh điểm chỉ do class_weight).
- C2 ``LogisticRegression`` — lưới C {0.03, 0.1, 0.3, 1.0, 3.0, 10.0} (superset
  chứa đủ 3 giá trị công bố → optimum đã công bố vẫn đạt được trong lưới).
- C3 ``RandomForestClassifier(class_weight="balanced", n_estimators=300,
  random_state=42, n_jobs=1)`` — lưới RF công bố Y HỆT.

Không đổi cặp dữ liệu, nhãn, fold, scorer — mọi khác biệt điểm số chỉ có thể do
class_weight/siêu tham số. Seed: model giữ ``random_state=42`` (đặc tả công bố,
scripts/predict_supervised.py:72); seed lane 11 được khai báo nhưng mọi bước
(StandardScaler, STING lưới thống kê, LogisticRegression lbfgs, GridSearchCV
n_jobs=1) đều tất định nên seed lane không tác động kết quả.

Output (2 tệp MỚI — KHÔNG ghi models/, KHÔNG ghi đè artifact đóng băng):
  results/candidates_classification.md · results/candidates_classification.csv

Chạy: python -E scripts/candidates_classification.py   (từ thư mục gốc repo)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from papi_pred_common import (  # noqa: E402
    CONFIG_PATH,
    PANEL_PATH,
    ROOT,
    load_config,
    load_panel,
)
from predict_supervised import (  # noqa: E402
    CLASSIFICATION_CV_YEARS,
    CLASSIFICATION_SCORER,
    FEATURES,
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
OUT_MD = RESULTS / "candidates_classification.md"
OUT_CSV = RESULTS / "candidates_classification.csv"
PUBLISHED_METRICS = RESULTS / "supervised_metrics.csv"

LANE_SEED = 11  # seed lane theo quy ước đợt phân tích — mọi bước tất định, không tác động kết quả
# Mốc "always dự đoán 1" đã công bố — results/supervised_summary.md:31
# ("baseline mù thời gian "always dự đoán 1" đạt macro-F1 0.400").
PUBLISHED_ALWAYS1 = 0.400
MIN_FOLD_BEAT = 4  # ngưỡng (ii) pre-registered: beat per-fold LR-best trên >= 4/6 fold


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


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(":--" if i == 0 else "--:" for i in range(len(headers))) + "|")
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def lr_pipeline(class_weight: str | None = None) -> Pipeline:
    """Spec LR nguyên văn pipeline (:342-343), chỉ class_weight là tham số."""
    return Pipeline([
        ("sc", StandardScaler()),
        ("clf", LogisticRegression(max_iter=3000, random_state=SEED, class_weight=class_weight)),
    ])


def rf_pipeline(class_weight: str | None = None) -> RandomForestClassifier:
    """Spec RF nguyên văn pipeline (:344), chỉ class_weight là tham số."""
    return RandomForestClassifier(
        n_estimators=300, random_state=SEED, n_jobs=1, class_weight=class_weight
    )


def fit_grid(estimator, grid: dict, cv: list[tuple[np.ndarray, np.ndarray]]) -> GridSearchCV:
    """GridSearchCV đúng protocol: cv=fold pipeline, scorer nguyên văn, n_jobs=1.

    ``refit=False``: chỉ cần best_score_/best_index_/cv_results_ trên CV —
    không fit thêm model cuối nào, không có gì để chấm trên holdout.
    """
    return GridSearchCV(
        estimator, grid, cv=cv, scoring=CLASSIFICATION_SCORER, n_jobs=1, refit=False
    )


def per_fold_scores(grid: GridSearchCV) -> np.ndarray:
    """Điểm per-fold của combo best (best_index_) — fold i = origin 2017+i."""
    cvr = grid.cv_results_
    return np.array([
        float(cvr[f"split{i}_test_score"][grid.best_index_])
        for i in range(len(CLASSIFICATION_CV_YEARS))
    ])


def combo_means(grid: GridSearchCV, params: list[str]) -> list[tuple[tuple[object, ...], float]]:
    """(giá trị tham số, mean CV) của TỪNG combo trong lưới, theo thứ tự lưới."""
    cvr = grid.cv_results_
    return [
        (tuple(cvr[f"param_{p}"][i] for p in params), float(cvr["mean_test_score"][i]))
        for i in range(cvr["mean_test_score"].size)
    ]


def lr_label(key: tuple[object, ...]) -> str:
    return f"C={float(key[0]):g}"


def rf_label(key: tuple[object, ...]) -> str:
    depth, leaf = key
    return f"depth={depth}, leaf={leaf}"


def best_combo_label(name: str, grid: GridSearchCV) -> str:
    """Nhãn combo best của một ứng viên (từ best_params_, tất định)."""
    if name in ("C1", "C2"):
        return f"C={float(grid.best_params_['clf__C']):g}"
    return f"depth={grid.best_params_['max_depth']}, leaf={grid.best_params_['min_samples_leaf']}"


def verdict_text(cond_i: bool, cond_ii: bool) -> str:
    if cond_i and cond_ii:
        return "VƯỢT NGƯỠNG [THAM KHẢO — CHƯA DUYỆT GV]"
    reasons = []
    if not cond_i:
        reasons.append("value_cv không vượt mốc LR công bố")
    if not cond_ii:
        reasons.append(f"beat per-fold LR-best < {MIN_FOLD_BEAT}/6 fold")
    return "KHÔNG VƯỢT — " + "; ".join(reasons)


# --------------------------------------------------------------------- main --
def main() -> int:
    cfg = load_config()          # CHỈ ĐỌC cấu hình đóng băng — không ghi lại
    df = load_panel()

    # ---- Ghép cặp + fold ĐÚNG pipeline (predict_supervised.py:335-341) ----
    C = build_classification_pairs(df, cfg["features"], cfg["sting"])
    ctr = C[C.year_t < HOLDOUT_YEAR]          # CHỈ train-side; holdout không tạo biến
    Xc_tr = ctr[FEATURES].to_numpy()          # 8 cột REGRESSION_FEATURES — đúng :338
    yc_tr = ctr["y"].to_numpy()
    clf_cv = expanding_year_splits(ctr["year_t"].to_numpy(), yc_tr)
    print(f"[Cặp] phân loại train {len(ctr)} cặp (year_t ≤ {HOLDOUT_YEAR - 1}) · "
          f"{len(FEATURES)} đặc trưng · fold origin {min(CLASSIFICATION_CV_YEARS)}–"
          f"{max(CLASSIFICATION_CV_YEARS)} · holdout {HOLDOUT_YEAR}→{HOLDOUT_YEAR + 1} KHÔNG đụng")

    # ---- Cấu trúc fold (đa số train / prevalence validation) ----
    fold_info = []
    for tr_idx, va_idx in clf_cv:
        origin = int(ctr["year_t"].iloc[va_idx[0]])
        fold_info.append({
            "origin": origin,
            "n_train": int(tr_idx.size),
            "n_val": int(va_idx.size),
            "train_majority": int(pd.Series(yc_tr[tr_idx]).mode().iloc[0]),
            "val_prev": float(np.mean(yc_tr[va_idx])),
        })

    # ---- Baseline tái lập IN-MEMORY trên cùng fold (không hardcode CSV) ----
    majority_cv = expanding_majority_f1(yc_tr, clf_cv)   # :236-251 nguyên văn
    majority_folds = []
    for tr_idx, va_idx in clf_cv:                        # per-fold cùng công thức :241-248
        maj = int(pd.Series(yc_tr[tr_idx]).mode().iloc[0])
        majority_folds.append(f1_score(
            yc_tr[va_idx], np.full(va_idx.size, maj, dtype=int),
            average="macro", labels=[0, 1], zero_division=0,
        ))
    always_one_folds = [                                  # :530-542 nguyên văn
        f1_score(
            yc_tr[va_idx], np.ones(va_idx.size, dtype=int),
            average="macro", labels=[0, 1], zero_division=0,
        )
        for _, va_idx in clf_cv
    ]
    always_one_cv = float(np.mean(always_one_folds))

    lr_pub = fit_grid(lr_pipeline(), {"clf__C": [0.1, 0.3, 1.0]}, clf_cv)   # :342-346
    lr_pub.fit(Xc_tr, yc_tr)
    rf_pub = fit_grid(
        rf_pipeline(), {"max_depth": [3, 6, None], "min_samples_leaf": [1, 2]}, clf_cv
    )
    rf_pub.fit(Xc_tr, yc_tr)                                                # :344, :347-348

    # ---- GATE đối chiếu mốc công bố trước khi so ứng viên (đề bài mục 6) ----
    if not PUBLISHED_METRICS.exists():
        print(f"[DỪNG] Không tìm thấy {PUBLISHED_METRICS} — không đối chiếu được baseline.")
        return 1
    pub = pd.read_csv(PUBLISHED_METRICS, encoding="utf-8-sig")
    pub_clf = pub[pub.task == "classification"].set_index("model")
    checks = [
        {"key": "lr_published_grid", "name": "LR lưới công bố",
         "inmem": float(lr_pub.best_score_),
         "pub": float(pub_clf.loc["logistic regression", "value_cv"]),
         "src": "supervised_metrics.csv"},
        {"key": "rf_published_grid", "name": "RF lưới công bố",
         "inmem": float(rf_pub.best_score_),
         "pub": float(pub_clf.loc["random forest", "value_cv"]),
         "src": "supervised_metrics.csv"},
        {"key": "majority", "name": "majority",
         "inmem": majority_cv,
         "pub": float(pub_clf.loc["majority (lớp đa số)", "value_cv"]),
         "src": "supervised_metrics.csv"},
        {"key": "always_one", "name": "always dự đoán 1",
         "inmem": always_one_cv, "pub": PUBLISHED_ALWAYS1,
         "src": "supervised_summary.md:31"},
    ]
    gate_ok = all(round(c["inmem"], 3) == round(c["pub"], 3) for c in checks)
    for c in checks:
        ok = round(c["inmem"], 3) == round(c["pub"], 3)
        print(f"[Kiểm đối] {c['name']}: in-memory {c['inmem']:.4f} vs công bố {c['pub']:.3f} "
              f"({c['src']}) → {'KHỚP' if ok else 'LỆCH'}")
    if not gate_ok:
        print("[DỪNG] Đối chiếu baseline LỆCH — theo đề bài mục 6: không tin so sánh, "
              "không ghi kết quả ứng viên.")
        return 1

    # ---- Ứng viên (3) ----
    cand_specs = [
        ("C1", lr_pipeline("balanced"), {"clf__C": [0.1, 0.3, 1.0]}),
        ("C2", lr_pipeline(None), {"clf__C": [0.03, 0.1, 0.3, 1.0, 3.0, 10.0]}),
        ("C3", rf_pipeline("balanced"),
         {"max_depth": [3, 6, None], "min_samples_leaf": [1, 2]}),
    ]
    grids: dict[str, GridSearchCV] = {}
    for name, est, grid in cand_specs:
        g = fit_grid(est, grid, clf_cv)
        g.fit(Xc_tr, yc_tr)
        grids[name] = g
        print(f"[{name}] value_cv={g.best_score_:.4f} best={g.best_params_}")

    # ---- Kiểm tra nội bộ: C2 là superset — điểm tại C dùng chung phải trùng LR công bố ----
    lr_pub_map = {float(k[0]): m for k, m in combo_means(lr_pub, ["clf__C"])}
    c2_map = {float(k[0]): m for k, m in combo_means(grids["C2"], ["clf__C"])}
    shared_cs = (0.1, 0.3, 1.0)
    shared_ok = all(np.isclose(c2_map[c], lr_pub_map[c], rtol=0.0, atol=1e-12) for c in shared_cs)
    if not shared_ok:
        print("[DỪNG] Điểm C2 tại C dùng chung {0.1, 0.3, 1.0} lệch LR lưới công bố "
              "> 1e-12 — protocol drift, không tin so sánh.")
        return 1
    print("[Kiểm tra] C2 superset: điểm tại C∈{0.1, 0.3, 1.0} trùng LR công bố (≤1e-12) → "
          "optimum đã công bố vẫn đạt được trong lưới C2")

    # ---- Verdict theo ngưỡng pre-registered ----
    ref_lr_mean = float(lr_pub.best_score_)
    ref_lr_folds = per_fold_scores(lr_pub)
    ref_rf_folds = per_fold_scores(rf_pub)
    ref_majority = majority_cv
    verdicts: dict[str, dict] = {}
    for name, _, _ in cand_specs:
        g = grids[name]
        mean = float(g.best_score_)
        folds = per_fold_scores(g)
        beats = [bool(f > r) for f, r in zip(folds, ref_lr_folds)]  # chặt: hoà không tính
        n_beat = int(sum(beats))
        cond_i = bool(mean > ref_lr_mean)
        cond_ii = bool(n_beat >= MIN_FOLD_BEAT)
        verdicts[name] = {
            "mean": mean, "folds": folds, "n_beat": n_beat, "beats": beats,
            "cond_i": cond_i, "cond_ii": cond_ii,
            "text": verdict_text(cond_i, cond_ii),
        }
        print(f"[{name}] Δ vs LR {mean - ref_lr_mean:+.4f} · Δ vs majority "
              f"{mean - ref_majority:+.4f} · beat LR-best {n_beat}/6 → {verdicts[name]['text']}")

    # ================================ CSV (long) =============================
    csv_rows: list[tuple[str, str, str, str]] = []

    def csv_add(section: str, key: str, metrics: dict[str, object]) -> None:
        for mname, value in metrics.items():
            csv_rows.append(
                (section, key, mname, value if isinstance(value, str) else fmt(value, 6))
            )

    for c in checks:
        csv_add("baseline_check", c["key"], {
            "value_cv_inmemory": c["inmem"],
            "value_cv_published": c["pub"],
            "published_source": c["src"],
            "match": "KHOP" if round(c["inmem"], 3) == round(c["pub"], 3) else "LECH",
        })
    for f in fold_info:
        csv_add("fold_structure", f"origin={f['origin']}", {
            "n_train_pairs": f["n_train"], "n_val_pairs": f["n_val"],
            "train_majority_class": f["train_majority"],
            "val_prevalence_label1": f["val_prev"],
        })
    baseline_folds = {
        "lr_best_published": ref_lr_folds,
        "rf_best_published": ref_rf_folds,
        "majority": np.asarray(majority_folds, dtype=float),
        "always_one": np.asarray(always_one_folds, dtype=float),
    }
    for bname, arr in baseline_folds.items():
        for f, v in zip(fold_info, arr):
            csv_add("baseline_folds", f"{bname}|origin={f['origin']}", {"f1_macro": v})
    for section, grid, params, kind in (
        ("grid_lr_published", lr_pub, ["clf__C"], "lr"),
        ("grid_c1", grids["C1"], ["clf__C"], "lr"),
        ("grid_c2", grids["C2"], ["clf__C"], "lr"),
        ("grid_rf_published", rf_pub, ["max_depth", "min_samples_leaf"], "rf"),
        ("grid_c3", grids["C3"], ["max_depth", "min_samples_leaf"], "rf"),
    ):
        for key, mean in combo_means(grid, params):
            lbl = lr_label(key) if kind == "lr" else rf_label(key)
            csv_add(section, lbl, {"mean_cv": mean})
    for name, _, _ in cand_specs:
        v = verdicts[name]
        for f, val, beat in zip(fold_info, v["folds"], v["beats"]):
            csv_add("candidate_folds", f"{name}|origin={f['origin']}", {
                "f1_macro": val, "beats_lr_best": int(beat),
            })
        csv_add("verdict", name, {
            "value_cv": v["mean"],
            "delta_vs_lr_best_inmemory": v["mean"] - ref_lr_mean,
            "delta_vs_majority_inmemory": v["mean"] - ref_majority,
            "folds_beat_lr_best": v["n_beat"],
            "cond_i_value_cv_gt_milestone": int(v["cond_i"]),
            "cond_ii_beat_ge_4_of_6": int(v["cond_ii"]),
            "verdict": v["text"],
        })
    pd.DataFrame(csv_rows, columns=["section", "key", "metric", "value"]).to_csv(
        OUT_CSV, index=False, encoding="utf-8-sig", lineterminator="\n"
    )
    print(f"[Ghi] {OUT_CSV} ({len(csv_rows)} dòng)")

    # ================================ MARKDOWN ===============================
    spec_text = {
        "C1": "LogisticRegression(class_weight='balanced') — lưới C {0.1, 0.3, 1.0} y hệt lưới công bố",
        "C2": "LogisticRegression — lưới C {0.03, 0.1, 0.3, 1.0, 3.0, 10.0} (superset của lưới công bố)",
        "C3": "RandomForestClassifier(class_weight='balanced', n_estimators=300, random_state=42, "
              "n_jobs=1) — lưới max_depth {3, 6, None} × min_samples_leaf {1, 2} y hệt lưới công bố",
    }
    lines: list[str] = []
    lines.append("# Ứng viên phân loại (lane CLF) — chỉ CV train, holdout không tham gia\n")
    lines.append(
        "**Trạng thái: [THAM KHẢO — CHƯA DUYỆT GV]** — số dưới đây là đầu vào cho quyết định, "
        "không phải quyết định (quy ước `reports/model_deep_dive.md:9-14`); thay spec/config công "
        "bố thuộc nhóm (b) — cần GV duyệt và re-run theo quy trình đóng băng "
        "(`reports/model_deep_dive.md:293-299`).\n"
    )
    lines.append(
        "- Script: `scripts/candidates_classification.py`, tái dùng NGUYÊN VĂN pipeline "
        "`scripts/predict_supervised.py` qua import: `build_classification_pairs` (:187-211), "
        "`expanding_year_splits` (:214-233), `expanding_majority_f1` (:236-251), "
        "`CLASSIFICATION_SCORER` (:75-77), spec + lưới LR/RF (:342-348), seed model (:72). "
        "Cấu hình đóng băng `models/predict_config.json` CHỈ ĐỌC — features sd_4_2+sd_6_1 và "
        "STING 3/4/5/2, connectivity=1 là không gian NHÃN STING; ma trận X của classifier là "
        "8 cột REGRESSION_FEATURES theo đúng pipeline (:338)."
    )
    lines.append(
        f"- Provenance (sha256 12 ký tự đầu): panel `{PANEL_PATH.name}` `{sha256_short(PANEL_PATH)}` · "
        f"config `{CONFIG_PATH.name}` `{sha256_short(CONFIG_PATH)}` (chỉ đọc)."
    )
    lines.append(
        f"- Seed: model giữ random_state={SEED} (đặc tả công bố); seed lane {LANE_SEED} khai báo "
        "theo quy ước — mọi bước (StandardScaler, STING lưới thống kê, LogisticRegression lbfgs, "
        "GridSearchCV n_jobs=1) đều tất định nên seed lane không tác động kết quả. "
        "`refit=False` cho mọi GridSearchCV: không fit model cuối nào ngoài CV."
    )
    lines.append(
        f"- Phạm vi CHỈ CV train: {len(ctr)} cặp year_t ≤ {HOLDOUT_YEAR - 1} (warm-up 2011–2016), "
        f"{len(CLASSIFICATION_CV_YEARS)} fold expanding origin {min(CLASSIFICATION_CV_YEARS)}–"
        f"{max(CLASSIFICATION_CV_YEARS)}; nhãn y = 1 nếu STING gán cụm (vùng dày), 0 nếu nhiễu "
        "(ngoại vi) — pseudo-label, không phải ground truth (:208). Holdout 2023→2024 (59 cặp, "
        "theo `results/supervised_summary.md:7`) KHÔNG fit, KHÔNG chọn, KHÔNG chấm, KHÔNG nhìn; "
        "cột holdout_* của `results/supervised_metrics.csv` không được tham chiếu khi quyết định "
        "ứng viên."
    )
    lines.append(
        "- Số combo chấm CV: 15 combo ứng viên (3 + 6 + 6) + 9 combo baseline tái lập lưới công "
        "bố (3 LR + 6 RF) = 24 combo × 6 fold = 144 fit. Đây là phân tích exploratory — KHÔNG "
        "tuyên bố p-value hay hiệu chỉnh alpha hình thức; guard chống fishing là ngưỡng "
        "pre-registered (mục 3) + duyệt GV.\n"
    )

    lines.append("## 1) Baseline tái lập in-memory trên cùng fold — gate trước khi so\n")
    lines.append(
        "Baseline KHÔNG hardcode từ CSV — tính lại bằng refit đúng lưới công bố (:342-348) trên "
        "đúng fold + đúng scorer. Đối chiếu round(mean, 3) với cột `value_cv` (task=classification) "
        "của `results/supervised_metrics.csv`; always-1 đối chiếu mốc 0.400 từ "
        "`results/supervised_summary.md:31`. Lệch → script dừng, không ghi kết quả ứng viên.\n"
    )
    check_desc = {
        "lr_published_grid": "GridSearchCV C {0.1, 0.3, 1.0} (:342-346)",
        "rf_published_grid": "GridSearchCV depth {3, 6, None} × leaf {1, 2} (:344, :347-348)",
        "majority": "expanding_majority_f1 (:236-251)",
        "always_one": "f1(ones) từng fold, nguyên văn :530-542",
    }
    lines.append(md_table(
        ["Baseline", "Cách tính", "In-memory", "Công bố", "Nguồn mốc", "Khớp"],
        [[c["name"], check_desc[c["key"]], fmt(c["inmem"]), fmt(c["pub"], 3), c["src"],
          "KHỚP" if round(c["inmem"], 3) == round(c["pub"], 3) else "LỆCH"] for c in checks],
    ))
    lines.append("")

    lines.append("## 2) Cấu trúc fold và điểm từng fold (macro-F1, cùng scorer)\n")
    lines.append(md_table(
        ["Fold origin", "n train", "n val", "Đa số train", "Prevalence nhãn 1 (val)",
         "LR-best", "RF-best", "majority", "always-1", "C1", "C2", "C3"],
        [[str(f["origin"]), str(f["n_train"]), str(f["n_val"]), str(f["train_majority"]),
          f"{f['val_prev']:.0%}",
          fmt(ref_lr_folds[i]), fmt(ref_rf_folds[i]), fmt(majority_folds[i]),
          fmt(always_one_folds[i]),
          fmt(verdicts["C1"]["folds"][i]), fmt(verdicts["C2"]["folds"][i]),
          fmt(verdicts["C3"]["folds"][i])]
         for i, f in enumerate(fold_info)]
        + [["**mean (value_cv)**", "", "", "", "",
            f"**{fmt(ref_lr_mean)}**", f"**{fmt(float(rf_pub.best_score_))}**",
            f"**{fmt(majority_cv)}**", f"**{fmt(always_one_cv)}**",
            f"**{fmt(verdicts['C1']['mean'])}**", f"**{fmt(verdicts['C2']['mean'])}**",
            f"**{fmt(verdicts['C3']['mean'])}**"]],
    ))
    lines.append("")

    lines.append("## 3) Verdict ứng viên — ngưỡng pre-registered trước khi chạy\n")
    lines.append(
        f"Ứng viên thắng CHỈ khi: **(i)** value_cv (mean 6 fold của combo best) > mốc LR công bố "
        f"0.434 — đối chiếu bằng LR tái lập in-memory trên cùng fold (KHỚP 3 số lẻ, mục 1; so "
        f"sánh dùng mean chưa làm tròn của refit đó) — VÀ **(ii)** nhất quán từng fold: beat "
        f"per-fold của LR-best tái lập trên ≥ {MIN_FOLD_BEAT}/6 fold (đếm chặt: hoà không tính là "
        "beat). Cấm trích 1 fold đẹp; cấm đổi metric/fold sau khi thấy số. Delta tính theo refit "
        "in-memory; mốc đã công bố hiển thị trong tiêu đề cột.\n"
    )
    lines.append(md_table(
        ["Ứng viên", "Spec", "Best combo", "macro-F1 CV", "Δ vs LR 0.434",
         "Δ vs majority 0.228", "Beat LR-best (fold)", "Verdict"],
        [[name, spec_text[name], best_combo_label(name, grids[name]),
          fmt(v["mean"]), f"{v['mean'] - ref_lr_mean:+.4f}", f"{v['mean'] - ref_majority:+.4f}",
          f"{v['n_beat']}/6", v["text"]]
         for name, _, _ in cand_specs for v in [verdicts[name]]],
    ))
    lines.append("")

    lines.append("### 3.1 Chi tiết lưới — chênh điểm chỉ do class_weight / siêu tham số\n")
    lines.append("#### C1 vs LR công bố (cùng lưới, khác class_weight)\n")
    c1_means = {float(k[0]): m for k, m in combo_means(grids["C1"], ["clf__C"])}
    lines.append(md_table(
        ["C", "LR công bố (mean CV)", "C1 balanced (mean CV)", "Δ"],
        [[f"{c:g}", fmt(lr_pub_map[c]), fmt(c1_means[c]), f"{c1_means[c] - lr_pub_map[c]:+.4f}"]
         for c in shared_cs],
    ))
    lines.append("")
    lines.append("#### C2 — C mở rộng (superset; điểm tại C dùng chung trùng LR công bố ≤1e-12)\n")
    c2_spread = float(max(c2_map.values()) - min(c2_map.values()))
    lr_pub_spread = float(max(lr_pub_map.values()) - min(lr_pub_map.values()))
    lines.append(md_table(
        ["C", "Trong lưới công bố?", "LR công bố (mean CV)", "C2 (mean CV)", "Δ vs LR-best"],
        [[f"{c:g}", "có" if c in shared_cs else "mới",
          fmt(lr_pub_map[c]) if c in shared_cs else "—",
          fmt(c2_map[c]), f"{c2_map[c] - ref_lr_mean:+.4f}"]
         for c in (0.03, 0.1, 0.3, 1.0, 3.0, 10.0)],
    ))
    lines.append(
        f"- Spread điểm trong lưới C2 = {c2_spread:.4f} (lưới công bố 3 điểm: {lr_pub_spread:.4f}) "
        "— đo độ nhạy siêu tham số; đối chiếu ghi chú bias lạc quan value_cv ở "
        "`results/supervised_summary.md:32`.\n"
    )
    lines.append("#### C3 vs RF công bố (cùng lưới, khác class_weight)\n")
    rf_pub_map = {
        rf_label(k): m for k, m in combo_means(rf_pub, ["max_depth", "min_samples_leaf"])
    }
    c3_means = {
        rf_label(k): m for k, m in combo_means(grids["C3"], ["max_depth", "min_samples_leaf"])
    }
    lines.append(md_table(
        ["max_depth, min_samples_leaf", "RF công bố (mean CV)", "C3 balanced (mean CV)", "Δ"],
        [[lbl, fmt(rf_pub_map[lbl]), fmt(c3_means[lbl]), f"{c3_means[lbl] - rf_pub_map[lbl]:+.4f}"]
         for lbl in rf_pub_map],
    ))
    lines.append("")

    lines.append("## Phạm vi & trung thực\n")
    lines.append(
        "- KHÔNG có số holdout nào trong tài liệu này: holdout 2023→2024 không fit, không chọn, "
        "không chấm cho bất kỳ ứng viên nào; `select_model_by_cv` vốn chỉ đọc `value_cv` "
        "(`scripts/papi_pred_common.py:60-66`) — mọi quyết định ở đây chỉ dùng CV train.\n"
        "- Exploratory: 24 combo × 6 fold — nhiều combo sẽ vượt mốc do may rủi; verdict ở mục 3 "
        "theo đúng ngưỡng pre-registered, không chọn lại sau khi thấy số.\n"
        f"- Baseline 'always dự đoán 1' ({fmt(always_one_cv)}) và majority ({fmt(majority_cv)}) "
        "là sàn mù: mọi ứng viên phải đối chiếu cả hai, vì prevalence nhãn 1 trong validation "
        f"trôi {min(f['val_prev'] for f in fold_info):.0%}–"
        f"{max(f['val_prev'] for f in fold_info):.0%} theo năm (bảng mục 2).\n"
        "- Biến thể RF `class_weight='balanced_subsample'` được đề bài nêu là TUỲ CHỌN ('có thể "
        "chạy song song, không thay C3') — KHÔNG chạy trong pha này để giữ đúng bộ 3 ứng viên "
        "pre-registered; nếu GV yêu cầu thì chạy như combo bổ sung đánh dấu riêng (NOT_RUN).\n"
        "- Script này chỉ ghi 2 tệp mới (`results/candidates_classification.md`, `.csv`); KHÔNG "
        "ghi `models/predict_config.json`, `results/supervised_metrics.csv`, "
        "`results/predict_all_years.csv`, KHÔNG ghi models/*.pkl|joblib, KHÔNG chạy "
        "`scripts/predict_sweep.py`, KHÔNG đổi số đã công bố (Ridge 0.265, carry 0.145, "
        "LR 0.434, k=3).\n"
        "- Ứng viên vượt ngưỡng (nếu có) vẫn chỉ là kết quả THAM KHẢO [CHƯA DUYỆT GV] — adoption "
        "thuộc quyền GV theo nhóm (b) của `reports/model_deep_dive.md:293-299`.\n"
    )

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"[Ghi] {OUT_MD} ({len(lines)} dòng)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
