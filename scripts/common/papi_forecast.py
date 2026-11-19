"""Dự báo hai điểm PAPI rồi chiếu kết quả lên lưới STING của mốc xuất phát."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, roc_auc_score, root_mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from scripts.common.papi_pred_common import REGRESSION_FEATURES
from sting import STING

TARGETS = ("sd_4_2", "sd_6_1")
FEATURES = list(REGRESSION_FEATURES)
ORIGIN_YEAR = 2023
FIRST_VALIDATION_ORIGIN = 2017
MODEL_NAMES = {
    "carry": "Giữ điểm năm trước",
    "ridge": "Ridge",
    "forest": "Random Forest",
    "blend": "Trung bình Ridge và Random Forest",
}
FOREST_OPTIONS = {"n_estimators": 96, "max_depth": 6, "min_samples_leaf": 5, "random_state": 42}


@dataclass
class ForecastRun:
    origin_year: int
    train_pairs: int
    scenario_count: int
    selection: dict[str, str]
    validation: pd.DataFrame
    predictions: pd.DataFrame
    scaler: StandardScaler
    grid: STING


def _training_pairs(history: pd.DataFrame) -> pd.DataFrame:
    keys = ["province_code", "year"]
    target_columns = {target: f"{target}_next" for target in TARGETS}
    previous = history[keys + FEATURES].dropna(subset=FEATURES)
    following = history[keys + list(TARGETS)].dropna(subset=list(TARGETS))
    following = following.rename(columns=target_columns).assign(year=lambda df: df.year - 1)
    return previous.merge(following, on=keys, validate="one_to_one").sort_values(keys)


def _candidate_predictions(train: pd.DataFrame, features: pd.DataFrame, target: str) -> dict[str, np.ndarray]:
    y = train[f"{target}_next"]
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    forest = RandomForestRegressor(**FOREST_OPTIONS)
    ridge_values = ridge.fit(train[FEATURES], y).predict(features[FEATURES])
    forest_values = forest.fit(train[FEATURES], y).predict(features[FEATURES])
    return {
        "carry": features[target].to_numpy(),
        "ridge": ridge_values,
        "forest": forest_values,
        "blend": (ridge_values + forest_values) / 2,
    }


def _temporal_validation(pairs: pd.DataFrame, final_origin: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    residuals = []
    for origin in range(FIRST_VALIDATION_ORIGIN, final_origin):
        train = pairs.loc[pairs.year < origin]
        validation = pairs.loc[pairs.year == origin]
        if train.empty or validation.empty:
            raise ValueError(f"Thiếu cặp đánh giá theo thời gian tại mốc {origin}.")
        # Năm đích của một cặp train là năm đặc trưng + 1, tối đa đến mốc origin.
        last_target = int(train.year.max()) + 1
        validation_errors = validation[["province_code", "year"]].copy()
        for target in TARGETS:
            measured = validation[f"{target}_next"]
            for method, values in _candidate_predictions(train, validation, target).items():
                validation_errors[f"{target}_{method}"] = measured.to_numpy() - values
                rows.append((origin, origin + 1, last_target, len(train), len(validation), target,
                             method, mean_absolute_error(measured, values)))
        residuals.append(validation_errors)
    scores = pd.DataFrame(rows, columns=[
        "origin_year", "target_year", "last_train_target_year", "n_train", "n_validation",
        "target", "method", "mae",
    ])
    return scores, pd.concat(residuals, ignore_index=True)


def forecast_from_history(history: pd.DataFrame, grid_params: dict, origin_year: int = ORIGIN_YEAR) -> ForecastRun:
    """Chọn và fit từ lịch sử. Bảng truyền vào kết thúc tại origin_year."""
    if history.empty or history.year.max() != origin_year or origin_year <= FIRST_VALIDATION_ORIGIN:
        raise ValueError("Lịch sử phải kết thúc đúng tại mốc xuất phát sau các năm khởi động.")
    if history.duplicated(["province_code", "year"]).any():
        raise ValueError("Khóa tỉnh–năm trong lịch sử phải duy nhất.")

    pairs = _training_pairs(history)
    cv, residuals = _temporal_validation(pairs, origin_year)
    average = cv.groupby(["target", "method"]).mae.mean()
    selection = {target: min(MODEL_NAMES, key=lambda method: average.loc[target, method]) for target in TARGETS}

    inputs = history.loc[history.year == origin_year].dropna(subset=FEATURES).sort_values("province_code")
    if inputs.empty:
        raise ValueError(f"Không có tỉnh đủ đặc trưng tại mốc {origin_year}.")
    forecasts = inputs[["province_code", "province_vi"]].copy()
    forecasts["target_year"] = origin_year + 1
    for target, method in selection.items():
        candidates = _candidate_predictions(pairs, inputs, target)
        forecasts[f"forecast_{target}"] = candidates[method]
        forecasts[f"carry_{target}"] = candidates["carry"]

    known_scores = history.dropna(subset=list(TARGETS))[list(TARGETS)]
    scaler = StandardScaler().fit(known_scores)
    grid = STING(n_levels=grid_params["n_levels"], factor=grid_params["factor"],
                 min_count=grid_params["min_count"]).fit(scaler.transform(known_scores))
    labels = grid.cluster(level=grid_params["cluster_level"], connectivity=grid_params["connectivity"])
    grouped = labels[labels >= 0]
    if grouped.size == 0:
        raise ValueError("Lưới STING cần ít nhất một vùng dày để đối chiếu dự báo.")
    for method in ("forecast", "carry"):
        forecasts[f"{method}_cluster"] = _grid_labels(forecasts, method, scaler, grid)
    forecasts["majority_cluster"] = int(np.bincount(grouped).argmax())

    errors = residuals[[f"{target}_{selection[target]}" for target in TARGETS]].to_numpy()
    predicted = forecasts[[f"forecast_{target}" for target in TARGETS]].to_numpy()
    scenarios = (predicted[:, None, :] + errors[None, :, :]).reshape(-1, len(TARGETS))
    scenario_frame = pd.DataFrame(scenarios, columns=list(TARGETS))
    scenario_labels = grid.predict(scaler.transform(scenario_frame)).reshape(len(predicted), len(errors))
    forecasts["outside_scenario_share"] = (scenario_labels == -1).mean(axis=1)

    return ForecastRun(origin_year, len(pairs), len(errors), selection, cv, forecasts, scaler, grid)


def _grid_labels(frame: pd.DataFrame, prefix: str, scaler: StandardScaler, grid: STING) -> np.ndarray:
    coordinates = frame[[f"{prefix}_{target}" for target in TARGETS]].copy()
    coordinates.columns = list(TARGETS)
    return grid.predict(scaler.transform(coordinates))


def score_forecast(run: ForecastRun, observed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ghép điểm thực tế vào các dự báo đã có và tính sai số trên cùng tỉnh."""
    year = run.origin_year + 1
    if observed.empty or not observed.year.eq(year).all() or observed.province_code.duplicated().any():
        raise ValueError(f"Bảng đối chiếu phải chứa mã tỉnh duy nhất của năm {year}.")
    targets = list(TARGETS)
    actuals = observed[["province_code", *targets]].rename(columns={t: f"actual_{t}" for t in targets})
    rows = run.predictions.merge(actuals, on="province_code", how="left", validate="one_to_one")
    eligible = rows[[f"actual_{t}" for t in targets]].notna().all(axis=1)
    if not eligible.any():
        raise ValueError("Không có tỉnh vừa có dự báo vừa đủ hai điểm thực tế.")
    comparable = rows.loc[eligible]
    actual_labels = _grid_labels(comparable, "actual", run.scaler, run.grid)
    rows["actual_cluster"] = pd.Series(actual_labels, index=comparable.index, dtype="Int64")
    values_metrics = []
    for target in targets:
        known = comparable[f"actual_{target}"]
        for method in ("forecast", "carry"):
            predicted = comparable[f"{method}_{target}"]
            values_metrics.append((target, method, len(known), mean_absolute_error(known, predicted),
                                   root_mean_squared_error(known, predicted), float((predicted - known).mean())))
    metrics = pd.DataFrame(values_metrics, columns=["target", "method", "n", "mae", "rmse", "bias"])

    grid_metrics = []
    out = actual_labels == -1
    for method in ("forecast", "carry", "majority"):
        predicted = comparable[f"{method}_cluster"].to_numpy()
        pred_out = predicted == -1
        tp = int((out & pred_out).sum())
        tn = int((~out & ~pred_out).sum())
        fp = int((~out & pred_out).sum())
        fn = int((out & ~pred_out).sum())
        recall_out = tp / (tp + fn) if tp + fn else np.nan
        recall_in = tn / (tn + fp) if tn + fp else np.nan
        grid_metrics.append((method, len(out), tp, tn, fp, fn, float((predicted == actual_labels).mean()),
                             recall_out, (recall_out + recall_in) / 2))
    grid_table = pd.DataFrame(grid_metrics, columns=[
        "method", "n", "out_correct", "in_correct", "false_out", "missed_out",
        "exact_label_agreement", "out_recall", "balanced_zone_accuracy",
    ])
    return rows, metrics, grid_table


def scenario_auc(scored: pd.DataFrame) -> float | None:
    """Đo thứ hạng ngoài vùng dày từ tỷ lệ kịch bản, trên các tỉnh đối chiếu được."""
    known = scored.dropna(subset=["actual_cluster"])
    is_outside = known.actual_cluster.eq(-1).to_numpy(dtype=bool)
    if np.unique(is_outside).size < 2:
        return None
    return float(roc_auc_score(is_outside, known.outside_scenario_share))
