"""Compare fixed-budget PAPI review shortlists; do not infer review outcomes."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from scripts.common.papi_pred_common import CONFIG_PATH, PANEL_PATH, ROOT, describe_grid_assignment
from src.sting import STING

FEATURES = ("sd_4_2", "sd_6_1")
YEARS = tuple(range(2018, 2025))
BUDGETS = (5, 10)
RULES = ("health_only", "sting_only", "combined")
REVIEW_YEAR = 2024
REVIEW_BUDGET = 5


def fit_grid(history: pd.DataFrame, params: dict) -> tuple[StandardScaler, STING]:
    scores = history[list(FEATURES)]
    scaler = StandardScaler().fit(scores)
    grid = STING(
        n_levels=params["n_levels"], factor=params["factor"], min_count=params["min_count"]
    ).fit(scaler.transform(scores))
    grid.cluster(level=params["cluster_level"], connectivity=params["connectivity"])
    return scaler, grid


def ranked(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    keys = {
        "health_only": ["sd_6_1"],
        "sting_only": ["zone_order", "cell_support"],
        "combined": ["zone_order", "sd_6_1"],
    }[rule]
    return frame.sort_values([*keys, "province_code"])


def overlap(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    left, right = set(a.province_code), set(b.province_code)
    return {"intersection": len(left & right), "union": len(left | right)}


def assign(target: pd.DataFrame, fitted: tuple[StandardScaler, STING]) -> pd.DataFrame:
    frame = describe_grid_assignment(target, FEATURES, *fitted)
    frame["zone_order"] = frame.grid_status.map(
        {"outside_grid": 0, "sparse_cell": 1, "in_cluster": 2}
    )
    if frame.zone_order.isna().any():
        raise ValueError("Unexpected grid status for finite scores")
    frame["cell_support"] = frame.reference_count.fillna(0)
    return frame


def analyze(panel: pd.DataFrame, params: dict) -> tuple[pd.DataFrame, dict]:
    if panel.duplicated(["year", "province_code"]).any():
        raise ValueError("Duplicate province-year keys")
    finite = np.isfinite(panel[list(FEATURES)].to_numpy(dtype=float)).all(axis=1)
    complete = panel.loc[finite].sort_values(["year", "province_code"])
    frames: dict[int, pd.DataFrame] = {}
    annual, across_years, changed_grid = [], [], []
    for year in YEARS:
        observed = panel.loc[panel.year.eq(year)]
        history = complete.loc[complete.year.lt(year)]
        target = complete.loc[complete.year.eq(year)]
        if len(target) < max(BUDGETS) or history.empty:
            raise ValueError(f"Insufficient history or target coverage for {year}")
        frame = assign(target, fit_grid(history, params))
        frames[year] = frame
        annual.append({
            "year": year,
            "period": "post_configuration_selection" if year >= 2023 else "retrospective",
            "fit_through": int(history.year.max()),
            "history_rows": len(history),
            "known_provinces": len(observed),
            "eligible": len(frame),
            "status_counts": {str(k): int(v) for k, v in frame.grid_status.value_counts().items()},
            "comparisons": {
                str(k): {
                    f"{a}__{b}": overlap(ranked(frame, a).head(k), ranked(frame, b).head(k))
                    for a, b in itertools.combinations(RULES, 2)
                }
                for k in BUDGETS
            },
        })
        if year == YEARS[0]:
            continue
        previous = frames[year - 1]
        common = set(previous.province_code) & set(frame.province_code)
        if len(common) < max(BUDGETS):
            raise ValueError(f"Insufficient common cohort for {year}")
        left = previous.loc[previous.province_code.isin(common)]
        right = frame.loc[frame.province_code.isin(common)]
        across_years.append({
            "from": year - 1, "to": year, "common_provinces": len(common),
            "comparisons": {
                str(k): {rule: overlap(ranked(left, rule).head(k), ranked(right, rule).head(k))
                         for rule in RULES}
                for k in BUDGETS
            },
        })
        older_history = history.loc[history.year.lt(year - 1)]
        if older_history.empty:
            raise ValueError(f"Missing earlier grid for {year}")
        frozen = assign(target, fit_grid(older_history, params))
        changed_grid.append({
            "year": year,
            "earlier_fit_through": int(older_history.year.max()),
            "updated_fit_through": int(history.year.max()),
            "eligible": len(frame),
            "status_changes": int(frame.grid_status.ne(frozen.grid_status).sum()),
            "comparisons": {
                str(k): {rule: overlap(ranked(frozen, rule).head(k), ranked(frame, rule).head(k))
                         for rule in RULES}
                for k in BUDGETS
            },
        })
    audit = pd.concat(frames.values(), ignore_index=True)
    for rule in RULES:
        order = ranked(audit, rule)
        audit[f"rank_{rule}"] = order.groupby("year").cumcount().add(1)
    return audit.sort_values(["year", "province_code"]), {
        "years": YEARS, "budgets": BUDGETS, "annual": annual,
        "across_years_common_cohort": across_years, "same_year_grid_refresh": changed_grid,
    }


def prepare_review(audit: pd.DataFrame, output: Path) -> None:
    """Prepare the blinded reviewer sheet separately from the restricted selection key."""
    frame = audit.loc[audit.year.eq(REVIEW_YEAR)].copy()
    flags = [f"selected_{rule}" for rule in RULES]
    for rule, flag in zip(RULES, flags, strict=True):
        frame[flag] = frame[f"rank_{rule}"].le(REVIEW_BUDGET)
    frame["in_pool"] = frame[flags].any(axis=1)
    frame["review_order"] = frame.province_code.map(
        lambda code: hashlib.sha256(f"papi-review-v1:{REVIEW_YEAR}:{code}".encode()).hexdigest()
    )
    outside = frame.loc[~frame.in_pool].sort_values("review_order")
    if len(outside) < REVIEW_BUDGET:
        raise ValueError("Too few cases outside the review pool")
    frame["audit_sample"] = frame.index.isin(outside.head(REVIEW_BUDGET).index)
    chosen = frame.loc[frame.in_pool | frame.audit_sample].sort_values("review_order").copy()
    chosen["case_id"] = [f"R{i:02d}" for i in range(1, len(chosen) + 1)]
    reviewer = chosen[["case_id", "province_vi", "year"]].assign(
        outcome="", evidence_ref="", rationale=""
    )
    key = chosen[["case_id", "province_code", *flags, "audit_sample"]]
    # Fail closed if a prior round already exists; never overwrite completed reviews.
    output.mkdir(parents=True, exist_ok=False)
    (output / "for-reviewers").mkdir()
    (output / "restricted").mkdir()
    reviewer.to_csv(output / "for-reviewers" / "cases.csv", index=False, lineterminator="\n")
    key.to_csv(output / "restricted" / "selection_key.csv", index=False, lineterminator="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--review-dir", type=Path, help="New directory for optional blind review packet")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if tuple(config["features"]) != FEATURES:
        raise ValueError("Published feature pair changed; review the study protocol")
    audit, summary = analyze(pd.read_csv(PANEL_PATH), config["sting"])
    summary["panel_sha256"] = hashlib.sha256(PANEL_PATH.read_bytes()).hexdigest()
    summary["config_sha256"] = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    if args.review_dir is not None:
        prepare_review(audit, args.review_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit.to_csv(args.output_dir / "review_shortlist_ranks.csv", index=False, lineterminator="\n")
    (args.output_dir / "review_shortlist_backtest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
