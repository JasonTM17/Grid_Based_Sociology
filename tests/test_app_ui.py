"""UI regression tests cho app.py qua streamlit.testing.v1.AppTest (Streamlit 1.58).

Nguyên tắc số học: mọi kỳ vọng số ĐỌC TỪ artifact qua CÙNG hàm mà dashboard
dùng (scripts/dashboard_data.py) — không hardcode giá trị kỳ vọng. Các chuỗi
duy nhất được phép hardcode là nhãn UI/tiêu đề và thông điệp lỗi (hợp đồng của
app), không phải số liệu.

Ứng normal-run: AppTest chạy app.py trong-process; tab lazy (`if tab.open:`,
app.py:314/448/684) được mở bằng `session_state['dashboard_tabs'] = <nhãn tab>`
vì `st.tabs(on_change='rerun')` đọc nhãn tab hiện tại từ widget state
(streamlit/elements/layouts.py: current_tab_label = tabs_state.value).
"""

from __future__ import annotations

import logging
import math
import re
import shutil

import numpy as np
import pandas as pd
import plotly.express as px
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from scripts import dashboard_data as dd
from scripts.check_data import scale_audit
from scripts.dashboard_data import (
    PCI_TOP30_WINDOW,
    ensure_external_pci_consistency,
    external_pci_group_stats,
    external_section_frame,
    format_p_value,
    load_dashboard_assets,
    load_external_validation_assets,
    prepare_external_pci_view,
    prepare_regression_holdout,
    prepare_sting_view,
    published_external_pci_tests,
    select_classification_model,
    select_regression_model,
)
from scripts.papi_pred_common import REGRESSION_FEATURES, ROOT

# Nhãn UI của app (app.py:130, 193-203).
APP_TITLE = "Khám phá kết quả STING và dự báo PAPI"
TAB_LABELS = [
    "Tổng quan",
    "STING theo năm",
    "Hồi quy 2023 → 2024",
    "Kiểm chứng ngoại lai",
    "Audit dữ liệu",
]
TAB_REGRESSION = "Hồi quy 2023 → 2024"
TAB_EXTERNAL = "Kiểm chứng ngoại lai"
TAB_AUDIT = "Audit dữ liệu"

# Hằng số HÀNH VI của app (không phải số liệu): bộ tên model hardcode mà app.py:365
# và scripts/dashboard_data.py:275-277/280-286 dùng để lọc bảng so sánh.
APP_HOLDOUT_TABLE_MODELS = (
    "carry-forward (giữ giá trị năm nay)",
    "ridge",
    "random forest",
)
APP_TUNED_CLASSIFIERS = ("logistic regression", "random forest")
NO_CV_SCORE_MESSAGE = "Không có CV score để chọn model."  # papi_pred_common.py:64

APP_PATH = ROOT / "app.py"
RUN_TIMEOUT_S = 120
_DASHBOARD_PANEL_CSV = "data/processed/papi_panel_63_2011_2024.csv"
_DASHBOARD_ASSIGNMENTS_CSV = "results/predict_all_years.csv"
_EXTERNAL_PCI_CSV = "data/processed/external_pci_63_full.csv"
_EXTERNAL_VALIDATION_CSV = "results/external_validation.csv"

logging.getLogger("streamlit").setLevel(logging.ERROR)


@pytest.fixture(autouse=True)
def _fresh_streamlit_caches():
    """st.cache_resource là process-global; xóa để mỗi test thấy artifact của mình."""
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture(scope="module")
def assets() -> dict:
    return load_dashboard_assets(include_models=False)


@pytest.fixture(scope="module")
def external_assets() -> dict:
    return load_external_validation_assets()


def run_app(tab_label: str | None = None) -> AppTest:
    app_test = AppTest.from_file(str(APP_PATH), default_timeout=RUN_TIMEOUT_S)
    if tab_label is not None:
        app_test.session_state["dashboard_tabs"] = tab_label
    app_test.run(timeout=RUN_TIMEOUT_S)
    return app_test


def metric_values(tab) -> dict[str, str]:
    return {metric.label: metric.value for metric in tab.metric}


def container_texts(tab) -> list[str]:
    texts: list[str] = []
    for child in tab.children.values():
        if child.type == "plotly_chart":
            continue  # element plotly ném KeyError khi đọc .value trong AppTest
        value = getattr(child, "value", None)
        if isinstance(value, str):
            texts.append(value)
    return texts


def stage_dashboard_artifacts(tmp_path, metrics_frame: pd.DataFrame) -> None:
    """Artifact tree tối thiểu cho load_dashboard_assets, với metrics đã biến đổi."""
    for relative in (_DASHBOARD_PANEL_CSV, _DASHBOARD_ASSIGNMENTS_CSV):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    config_target = tmp_path / "models" / "predict_config.json"
    config_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "models" / "predict_config.json", config_target)
    metrics_target = tmp_path / "results" / "supervised_metrics.csv"
    metrics_frame.to_csv(metrics_target, index=False)


def stage_external_artifacts(tmp_path, pci_frame=None, validation_frame=None) -> None:
    pci_target = tmp_path / _EXTERNAL_PCI_CSV
    validation_target = tmp_path / _EXTERNAL_VALIDATION_CSV
    pci_target.parent.mkdir(parents=True, exist_ok=True)
    validation_target.parent.mkdir(parents=True, exist_ok=True)
    if pci_frame is None:
        shutil.copy2(ROOT / _EXTERNAL_PCI_CSV, pci_target)
    else:
        pci_frame.to_csv(pci_target, index=False, encoding="utf-8")
    if validation_frame is None:
        shutil.copy2(ROOT / _EXTERNAL_VALIDATION_CSV, validation_target)
    else:
        validation_frame.to_csv(validation_target, index=False, encoding="utf-8")


def patch_dashboard_assets(monkeypatch, root) -> None:
    real_load = dd.load_dashboard_assets

    def load_from_tmp(include_models: bool = False) -> dict:
        return real_load(root=root, include_models=include_models)

    monkeypatch.setattr(dd, "load_dashboard_assets", load_from_tmp)


def patch_external_assets(monkeypatch, root) -> None:
    real_load = dd.load_external_validation_assets

    def load_external_from_tmp() -> dict:
        return real_load(root=root)

    monkeypatch.setattr(dd, "load_external_validation_assets", load_external_from_tmp)


def expected_external_tables(external: dict, assignments: pd.DataFrame) -> dict:
    view, counts = prepare_external_pci_view(external["pci"], assignments)
    tests = ensure_external_pci_consistency(view, external["validation"])
    top_view, top_counts = prepare_external_pci_view(
        external["pci"], assignments, *PCI_TOP30_WINDOW
    )
    top_tests = ensure_external_pci_consistency(
        top_view, external["validation"], section="pci_top30_2023_2024"
    )
    return {
        "view": view,
        "counts": counts,
        "tests": tests,
        "top_counts": top_counts,
        "top_tests": top_tests,
    }


def expected_poverty_tables(assignments: pd.DataFrame) -> dict:
    """Kỳ vọng block nghèo GSO — cùng hàm dashboard dùng trên artifact thật."""
    poverty = dd.load_poverty_assets()
    view, counts = dd.prepare_poverty_cluster_view(poverty["poverty"], assignments)
    return {
        "view": view,
        "counts": counts,
        "raw": dd.poverty_cluster_tests(view, "poverty_rate_pct"),
        "dm": dd.poverty_cluster_tests(view, "pov_dm"),
        "mw_raw": dd.poverty_noise_vs_c2(view, "poverty_rate_pct"),
        "mw_dm": dd.poverty_noise_vs_c2(view, "pov_dm"),
    }


# --------------------------------------------------------------------- #
# Happy path — từng section trong danh sách của ask
# --------------------------------------------------------------------- #


def test_app_renders_clean_with_title_tabs_and_sidebar_filters(assets):
    at = run_app()

    assert not at.exception
    assert not at.error
    assert at.title[0].value == APP_TITLE
    assert [tab.label for tab in at.tabs] == TAB_LABELS

    panel, assignments = assets["panel"], assets["assignments"]
    expected_years = sorted(int(year) for year in assignments.year.dropna().unique())
    expected_year = max(expected_years)
    expected_clusters = sorted(
        int(code)
        for code in assignments.loc[
            assignments.year.eq(expected_year), "pred_cluster"
        ].dropna().unique()
    )
    expected_provinces = int(
        panel.loc[panel.year.eq(expected_year), "province_code"].dropna().nunique()
    )

    sidebar = at.sidebar
    assert [header.value for header in sidebar.header] == ["Bộ lọc STING"]
    by_label = {box.label: box for box in sidebar.selectbox}
    assert set(by_label) == {"Năm assignment", "Cụm STING"}
    year_box = by_label["Năm assignment"]
    assert int(year_box.value) == expected_year
    assert {int(option) for option in year_box.options} == set(expected_years)
    cluster_box = by_label["Cụm STING"]
    assert cluster_box.value == "Tất cả"
    expected_cluster_labels = {
        "Tất cả",
        *{"Nhiễu (-1)" if code == -1 else f"Cụm {code}" for code in expected_clusters},
    }
    assert set(cluster_box.options) == expected_cluster_labels
    assert len(sidebar.multiselect) == 1
    province_box = sidebar.multiselect[0]
    assert province_box.label == "Tỉnh / thành phố"
    assert province_box.value == []
    assert len(province_box.options) == expected_provinces


def test_tab1_tong_quan_renders_metrics_from_artifacts(assets):
    at = run_app()
    assert not at.exception
    assert not at.error

    panel, config = assets["panel"], assets["config"]
    assignments, metrics = assets["assignments"], assets["metrics"]
    year = max(int(value) for value in assignments.year.dropna().unique())
    _, counts = prepare_sting_view(
        panel, assignments, year, required_features=list(config["features"])
    )
    _, holdout_counts = prepare_regression_holdout(panel, assignments)
    selected_model = select_regression_model(metrics)

    overview = at.tabs[0]
    assert overview.subheader[0].value == f"Ảnh chụp dữ liệu năm {year}"
    values = metric_values(overview)
    assert values["Tỉnh trong panel"] == f"{counts['source_rows']}"
    assert values["Có assignment"] == f"{counts['eligible_assignments']}"
    eligible = counts["eligible_assignments"]
    coverage = counts["covered_rows"] / eligible if eligible else 0.0
    assert values["Nằm trong cụm"] == f"{coverage:.0%}"
    assert values["Nhiễu (-1)"] == f"{counts['noise_rows']}"

    text = "\n".join(container_texts(overview))
    assert f"**{counts['filtered_rows']}** dòng" in text
    assert f"**{counts['filtered_missing_feature_rows']}** dòng thiếu feature" in text
    assert f"**{counts['filtered_unassigned_artifact_rows']}** dòng đủ feature" in text
    assert f"{holdout_counts['holdout_pairs']} cặp tỉnh" in text
    assert f"**{selected_model.title()}**" in text
    assert "một năm holdout" in text


def test_tab2_sting_theo_nam_renders_plot_and_table(assets):
    at = run_app()
    assert not at.exception
    assert not at.error

    panel, config = assets["panel"], assets["config"]
    assignments = assets["assignments"]
    year = max(int(value) for value in assignments.year.dropna().unique())
    sting_view, counts = prepare_sting_view(
        panel, assignments, year, required_features=list(config["features"])
    )

    sting = at.tabs[1]
    assert sting.subheader[0].value == f"Phân bố assignment STING · {year}"
    child_types = [child.type for child in sting.children.values()]
    assert "plotly_chart" in child_types
    assert len(sting.dataframe) == 1
    display = sting.dataframe[0].value
    assert len(display) == counts["filtered_rows"]
    assert {"province_code", "pred_cluster", "assignment_state"} <= set(display.columns)
    text = "\n".join(container_texts(sting))
    assert f"{counts['filtered_rows']} dòng sau lọc" in text
    assert f"{counts['filtered_noise_rows']} nhiễu" in text


def test_tab3_hoi_quy_holdout_table_matches_metrics_csv(assets):
    at = run_app(TAB_REGRESSION)
    assert not at.exception
    assert not at.error

    panel, assignments = assets["panel"], assets["assignments"]
    metrics = assets["metrics"]
    expected_rows = metrics.loc[
        metrics.task.eq("regression") & metrics.model.isin(APP_HOLDOUT_TABLE_MODELS)
    ]
    selected_model = select_regression_model(metrics)
    _, holdout_counts = prepare_regression_holdout(panel, assignments)

    regression = at.tabs[2]
    assert regression.subheader[0].value == "Holdout hồi quy cố định: 2023 → 2024"
    values = metric_values(regression)
    assert values["Cặp holdout sau lọc"] == f"{holdout_counts['holdout_pairs']}"

    assert len(regression.dataframe) == 2
    comparison = regression.dataframe[0].value
    assert comparison["model"].tolist() == expected_rows["model"].tolist()
    for column in ("value_cv", "holdout_mae", "holdout_rmse", "holdout_r2"):
        for got, want in zip(comparison[column], expected_rows[column]):
            assert float(got) == pytest.approx(float(want), abs=1e-12)
    chosen = comparison.loc[comparison["Được chọn theo CV"], "model"].tolist()
    assert chosen == [selected_model]

    detailed = regression.dataframe[1].value
    assert len(detailed) == holdout_counts["holdout_pairs"]

    # Dòng regression trong artifact nhưng ngoài bảng so sánh phải được liệt
    # kê tường minh (fix risk #2 — không còn lọc im lặng).
    compared = set(APP_HOLDOUT_TABLE_MODELS)
    dropped = [
        model
        for model in metrics.loc[metrics.task.eq("regression"), "model"]
        if model not in compared
    ]
    assert dropped  # artifact thật có ít nhất 'trung bình train' ngoài bảng
    text = "\n".join(container_texts(regression))
    assert "không thuộc bảng so sánh" in text
    for model in dropped:
        assert model in text


def test_tab4_kiem_ngoai_numbers_match_external_validation_csv(assets, external_assets):
    at = run_app(TAB_EXTERNAL)
    assert not at.exception
    assert not at.error

    expected = expected_external_tables(external_assets, assets["assignments"])
    counts, tests = expected["counts"], expected["tests"]
    validation = external_assets["validation"]
    published = published_external_pci_tests(validation, "pci_2011_2022")
    published_top = published_external_pci_tests(validation, "pci_top30_2023_2024")
    pov = expected_poverty_tables(assets["assignments"])

    # Số hiển thị khớp artifact theo đúng dung sai gate của dashboard
    # (dashboard_data.py:540-552): 5.1e-5 cho F/H/eta², rel_tol 0.006 cho p.
    assert abs(tests["f"] - published["f"]) <= 5.1e-5
    assert abs(tests["h"] - published["h"]) <= 5.1e-5
    assert abs(tests["eta_sq"] - published["eta_sq"]) <= 5.1e-5
    assert math.isclose(tests["p_anova"], published["p_anova"], rel_tol=0.006)
    assert math.isclose(tests["p_kw"], published["p_kw"], rel_tol=0.006)
    assert tests["n"] == published["n"]

    external = at.tabs[3]
    assert external.subheader[0].value == (
        "Kiểm chứng ngoại lai bằng nguồn độc lập với PAPI"
    )
    values = metric_values(external)
    assert values["Ô PCI có điểm 2011–2022"] == f"{counts['window_cells']}"
    assert values["Điểm vào kiểm định"] == f"{counts['tested_points']}"
    assert values["Có điểm nhưng thiếu nhãn"] == f"{counts['missing_label_cells']}"
    assert values["Nhóm so sánh"] == f"{len(counts['clusters'])}"
    assert values["Ô poverty trong cửa sổ giao"] == f"{pov['counts']['window_cells']}"
    assert values["Ô vào kiểm định theo cụm"] == f"{pov['counts']['panel_rows']}"

    assert len(external.dataframe) == 5
    tests_table = external.dataframe[0].value
    anova_row, kruskal_row, eta_row = (tests_table.iloc[index] for index in range(3))
    assert anova_row["Kiểm định"] == f"One-way ANOVA F({tests['df1']},{tests['df2']})"
    assert anova_row["Giá trị"] == f"{tests['f']:.4f}"
    assert float(anova_row["Giá trị"]) == pytest.approx(published["f"], abs=1e-4)
    assert anova_row["p-value"] == format_p_value(tests["p_anova"])
    assert int(anova_row["n"]) == published["n"]
    assert kruskal_row["Giá trị"] == f"{tests['h']:.4f}"
    assert float(kruskal_row["Giá trị"]) == pytest.approx(published["h"], abs=1e-4)
    assert kruskal_row["p-value"] == format_p_value(tests["p_kw"])
    assert eta_row["Giá trị"] == f"{tests['eta_sq']:.4f}"

    group_table = external.dataframe[1].value
    expected_group = external_pci_group_stats(expected["view"])
    assert group_table["cluster_label"].tolist() == expected_group["cluster_label"].tolist()
    for column in ("n", "mean", "median", "std", "min", "max"):
        for got, want in zip(group_table[column], expected_group[column]):
            if pd.isna(want):
                assert pd.isna(got)
            else:
                assert float(got) == pytest.approx(float(want), abs=1e-9)

    top_table = external.dataframe[2].value
    assert top_table.iloc[0]["Giá trị"] == f"{expected['top_tests']['f']:.4f}"
    assert float(top_table.iloc[0]["Giá trị"]) == pytest.approx(
        published_top["f"], abs=1e-4
    )
    assert top_table.iloc[1]["Giá trị"] == f"{expected['top_tests']['h']:.4f}"

    health_table = external.dataframe[3].value
    health = external_section_frame(validation, "odm_health_2020")
    assert health_table["cluster_label"].tolist() == health["cluster_label"].tolist()
    assert [int(value) for value in health_table["n"]] == list(health["n"])
    text = "\n".join(container_texts(external))
    assert "GRDP/người" in text  # section GRDP render (px.line sau bảng y tế)

    # Block bổ trợ nghèo GSO (dataframe[4], sau GRDP; boxplot là chart thứ 3)
    poverty_table = external.dataframe[4].value
    assert poverty_table["Kiểm định"].tolist() == [
        "Kruskal–Wallis H (gộp thô — nhiễm hiệu ứng năm)",
        "Kruskal–Wallis H (đã trừ median trong năm)",
        "Mann–Whitney U — nhiễu vs cụm 2 (thô)",
        "Mann–Whitney U — nhiễu vs cụm 2 (đã trừ median năm)",
    ]
    assert poverty_table.iloc[0]["Giá trị"] == f"{pov['raw']['h']:.4f}"
    assert poverty_table.iloc[0]["p-value"] == format_p_value(pov["raw"]["p_kw"])
    assert poverty_table.iloc[1]["Giá trị"] == f"{pov['dm']['h']:.4f}"
    assert poverty_table.iloc[1]["p-value"] == format_p_value(pov["dm"]["p_kw"])
    assert poverty_table.iloc[2]["Giá trị"] == f"{pov['mw_raw']['u']:.0f}"
    assert int(poverty_table.iloc[2]["n"]) == pov["mw_raw"]["n"]
    assert poverty_table.iloc[3]["Giá trị"] == f"{pov['mw_dm']['u']:.0f}"
    assert int(poverty_table.iloc[3]["n"]) == pov["mw_dm"]["n"]
    assert "Nghèo cấp tỉnh (GSO V14.47)" in text
    assert "python scripts/build_poverty_63.py" in text  # caption nguồn block
    assert "không vẽ không test" in text  # 11 ô không nhãn được liệt kê tường minh


def test_tab5_audit_renders_scale_flags_and_classification_from_csv(assets):
    at = run_app(TAB_AUDIT)  # tab Audit lazy (fix rủi ro DOM-nonslazy vòng 1)
    assert not at.exception
    assert not at.error

    panel, config = assets["panel"], assets["config"]
    assignments, metrics = assets["assignments"], assets["metrics"]
    year = max(int(value) for value in assignments.year.dropna().unique())
    flags = scale_audit(panel)
    indicator_columns = [
        column
        for column in panel.columns
        if column.startswith(("d", "sd_"))
        and pd.api.types.is_numeric_dtype(panel[column])
    ]
    _, counts = prepare_sting_view(
        panel, assignments, year, required_features=list(config["features"])
    )

    audit = at.tabs[4]
    assert audit.subheader[0].value == "Feature, missingness và giới hạn thang đo"
    values = metric_values(audit)
    assert values["Mean-jump heuristic"] == f"{len(flags)} / {len(indicator_columns)}"
    assert values["Feature STING đang dùng"] == f"{len(config['features'])}"
    assert values[f"Thiếu feature toàn năm {year}"] == f"{counts['missing_feature_rows']}"

    assert len(audit.dataframe) == 4
    feature_table = audit.dataframe[0].value
    for _, row in feature_table.iterrows():
        assert int(row["Thiếu trong panel"]) == int(panel[row["Feature"]].isna().sum())
        expected_flag = any(item[0] == row["Feature"] for item in flags)
        assert bool(row["Mean-jump flag toàn panel"]) == expected_flag

    classification_csv = metrics.loc[metrics.task.eq("classification")]
    classifier = select_classification_model(metrics)
    classification_table = next(
        frame.value
        for frame in audit.dataframe
        if "holdout_acc" in frame.value.columns
    )
    assert classification_table["model"].tolist() == classification_csv["model"].tolist()
    for column in ("value_cv", "holdout_acc", "holdout_macro_f1"):
        for got, want in zip(classification_table[column], classification_csv[column]):
            assert float(got) == pytest.approx(float(want), abs=1e-12)
    chosen = classification_table.loc[
        classification_table["Được chọn theo CV"], "model"
    ].tolist()
    assert chosen == [classifier]

    prediction_table = next(
        frame.value
        for frame in audit.dataframe
        if {"predicted", "actual", "correct"} <= set(frame.value.columns)
    )
    origin_codes = panel.loc[
        panel.year.eq(2023) & panel[REGRESSION_FEATURES].notna().all(axis=1),
        "province_code",
    ]
    expected_pairs = assignments.loc[
        assignments.year.eq(2024)
        & assignments.pred_cluster.notna()
        & assignments.province_code.isin(origin_codes)
    ]
    assert len(prediction_table) == len(expected_pairs)
    assert set(prediction_table["predicted"]) <= {"ngoại vi", "vùng dày"}
    assert set(prediction_table["actual"]) <= {"ngoại vi", "vùng dày"}


def test_tab5_audit_content_is_lazy_until_tab_opened(assets):
    """Tab 5 Audit phải lazy như Tab 3/4: ở lần load mặc định (chưa mở tab)
    panel Audit KHÔNG có dataframe nào trong DOM (fix vòng 1 — trước đây
    `with audit_tab:` không bọc Tab.open nên các dataframe render sẵn 0-kết quả)."""
    at_default = run_app()
    assert not at_default.exception
    assert not at_default.error
    assert len(at_default.tabs[4].dataframe) == 0

    at_open = run_app(TAB_AUDIT)
    assert not at_open.exception
    assert not at_open.error
    assert len(at_open.tabs[4].dataframe) == 4


# --------------------------------------------------------------------- #
# Widget-test cho các rủi ro scout nêu (mục 1-11)
# --------------------------------------------------------------------- #


def test_risk1_metrics_without_regression_cv_rows_crash_app_uncaught(
    assets, tmp_path, monkeypatch
):
    """Thiếu hàng CV regression → st.error, app vẫn chạy."""
    tampered = assets["metrics"].loc[assets["metrics"].task.ne("regression")]
    with pytest.raises(ValueError, match="Không có CV score"):
        select_regression_model(tampered)
    stage_dashboard_artifacts(tmp_path, tampered)
    patch_dashboard_assets(monkeypatch, tmp_path)

    at = run_app()

    assert not at.exception
    error_messages = [element.value for element in at.error]
    assert any(NO_CV_SCORE_MESSAGE in message for message in error_messages)


def test_risk1b_classification_baseline_only_crashes_audit_tab_uncaught(
    assets, tmp_path, monkeypatch
):
    """Chỉ baseline phân loại → tab Audit báo st.error, không crash."""
    tampered = assets["metrics"].loc[
        ~(
            assets["metrics"].task.eq("classification")
            & assets["metrics"].model.isin(APP_TUNED_CLASSIFIERS)
        )
    ]
    remaining = tampered.loc[tampered.task.eq("classification")]
    assert not remaining.empty
    with pytest.raises(ValueError, match="Không có CV score"):
        select_classification_model(tampered)
    stage_dashboard_artifacts(tmp_path, tampered)
    patch_dashboard_assets(monkeypatch, tmp_path)

    at = run_app(TAB_AUDIT)  # tab Audit lazy — mở như tab 3/4

    assert not at.exception
    error_messages = [element.value for element in at.error]
    assert any(NO_CV_SCORE_MESSAGE in message for message in error_messages)


def test_risk2_renamed_regression_model_surfaced_by_holdout_table_caption(
    assets, tmp_path, monkeypatch
):
    """Đổi nhãn model → dòng mất khỏi bảng so sánh (app.py:365 lọc isin
    hardcode, đúng thiết kế) NHƯNG phải hiện tường minh trong caption liệt kê
    các dòng regression ngoài bảng — không còn mất im lặng."""
    tampered = assets["metrics"].copy()
    tampered.loc[tampered.model.eq("ridge"), "model"] = "ridge (đổi tên)"
    assert select_regression_model(tampered) == "random forest"
    expected_models = tampered.loc[
        tampered.task.eq("regression") & tampered.model.isin(APP_HOLDOUT_TABLE_MODELS),
        "model",
    ].tolist()
    assert "ridge (đổi tên)" not in expected_models
    stage_dashboard_artifacts(tmp_path, tampered)
    patch_dashboard_assets(monkeypatch, tmp_path)

    at = run_app(TAB_REGRESSION)

    assert not at.exception
    assert not at.error
    comparison = at.tabs[2].dataframe[0].value
    assert "ridge (đổi tên)" not in comparison["model"].tolist()
    assert comparison["model"].tolist() == expected_models
    chosen = comparison.loc[comparison["Được chọn theo CV"], "model"].tolist()
    assert chosen == ["random forest"]
    text = "\n".join(container_texts(at.tabs[2]))
    assert "không thuộc bảng so sánh" in text
    assert "ridge (đổi tên)" in text  # model bị loại giờ hiển thị rõ


def test_risk3_holdout_pairs_label_in_source_matches_artifact_pairs(assets):
    """Nhãn holdout trong column_config phải lấy holdout_pairs từ dữ liệu,
    không hardcode số cặp."""
    panel, assignments = assets["panel"], assets["assignments"]
    _, counts = prepare_regression_holdout(panel, assignments)
    source = APP_PATH.read_text(encoding="utf-8")
    assert counts["holdout_pairs"] > 0
    assert "regression_counts['holdout_pairs']" in source
    assert not re.findall(r'(?:MAE|RMSE|R²) · \d+ cặp', source)


def test_risk4_tampered_external_validation_fails_closed_and_hides_sections(
    external_assets, tmp_path, monkeypatch
):
    """Sửa 1 số F trong external_validation.csv → gate raise DashboardDataError
    ('KHÔNG khớp artifact'); tab chỉ hiện st.error, MẤT cả section y tế 2020 và
    GRDP (app.py:464-469 dừng toàn bộ tab); phần còn lại vẫn dùng được."""
    validation = external_assets["validation"].copy()
    published_f = published_external_pci_tests(validation, "pci_2011_2022")["f"]
    anova_mask = validation.section.eq("pci_2011_2022") & validation.group.str.startswith(
        "ANOVA"
    )
    validation.loc[anova_mask, "note"] = re.sub(
        r"F = [0-9.eE+-]+",
        f"F = {published_f + 0.5:.4f}",
        validation.loc[anova_mask, "note"].iloc[0],
    )
    stage_external_artifacts(tmp_path, validation_frame=validation)
    patch_external_assets(monkeypatch, tmp_path)

    at = run_app(TAB_EXTERNAL)

    assert not at.exception  # fail-closed: bắt lỗi, không crash app
    error_messages = [element.value for element in at.error]
    assert any("KHÔNG khớp artifact" in message for message in error_messages)
    text = "\n".join(container_texts(at.tabs[3]))
    assert "Mật độ cơ sở y tế 2020" not in text
    assert "GRDP/người" not in text
    assert "Nghèo cấp tỉnh" not in text  # block poverty cũng ẩn khi gate PCI fail
    assert metric_values(at.tabs[0])  # tab Tổng quan vẫn render


def test_risk5_pci_without_province_ascii_loads_but_crashes_app(
    external_assets, tmp_path, monkeypatch
):
    """PCI thiếu province_ascii → fail-closed st.error khi nạp tab ngoại lai."""
    pci = external_assets["pci"].drop(columns=["province_ascii"])
    stage_external_artifacts(tmp_path, pci_frame=pci)
    with pytest.raises(dd.DashboardDataError, match="province_ascii"):
        load_external_validation_assets(tmp_path)
    patch_external_assets(monkeypatch, tmp_path)

    at = run_app(TAB_EXTERNAL)

    assert not at.exception
    error_messages = [element.value for element in at.error]
    assert any("province_ascii" in message for message in error_messages)
    text = "\n".join(container_texts(at.tabs[3]))
    assert "Kiểm định khác biệt PCI" not in text
    assert metric_values(at.tabs[0])  # tab Tổng quan vẫn render


def test_risk6_single_feature_config_crashes_sting_tab_uncaught(
    assets, tmp_path, monkeypatch
):
    """Config < 2 feature → DashboardDataError khi nạp, st.error, không crash."""
    import json

    config = json.loads((ROOT / "models" / "predict_config.json").read_text(encoding="utf-8"))
    config["features"] = config["features"][:1]
    tampered_metrics = assets["metrics"]
    stage_dashboard_artifacts(tmp_path, tampered_metrics)
    config_target = tmp_path / "models" / "predict_config.json"
    config_target.write_text(json.dumps(config), encoding="utf-8")
    patch_dashboard_assets(monkeypatch, tmp_path)

    at = run_app()

    assert not at.exception
    error_messages = [element.value for element in at.error]
    assert any("2 feature" in message for message in error_messages)


def test_risk7_assignments_without_any_year_crash_sidebar_uncaught(
    assets, tmp_path, monkeypatch
):
    """Assignment không có năm → st.error và dừng, không ValueError từ max([])."""
    empty_assignments = assets["assignments"].iloc[0:0]
    assert empty_assignments.year.dropna().empty
    stage_dashboard_artifacts(tmp_path, assets["metrics"])
    assignments_target = tmp_path / _DASHBOARD_ASSIGNMENTS_CSV
    empty_assignments.to_csv(assignments_target, index=False)
    patch_dashboard_assets(monkeypatch, tmp_path)

    at = run_app()

    assert not at.exception
    error_messages = [element.value for element in at.error]
    assert any("năm" in message.lower() for message in error_messages)


def test_risk8_wdi_excluded_from_external_tab_intentionally(external_assets):
    """WDI bị loại khỏi Tab 4 CỐ Ý (owner chốt vòng fix 1): WDI là dữ liệu
    CẤP QUỐC GIA (một giá trị/năm cho cả nước) — vai bối cảnh vĩ mô/year
    effects theo reports/external_data_expansion.md §5.4, khác bản chất cấp
    tỉnh của 4 section kiểm chứng theo cụm; không trộn hai cấp phân tích trên
    cùng một màn. WDI đã có chỗ trình bày đúng vai trong báo cáo
    (results/figs/external_wdi_panel.png). Nếu sau này muốn hiển thị trên
    dashboard thì phải là block riêng 'Bối cảnh vĩ mô', không phải section
    kiểm chứng theo cụm — đổi _REQUIRED_VALIDATION_SECTIONS cùng lúc."""
    sections = set(
        external_assets["validation"].section.dropna().astype(str).str.strip()
    )
    assert "wdi_2010_2024" in sections  # artifact vẫn sinh đủ 5 section
    # Gate cố ý chỉ yêu cầu đúng 4 section kiểm chứng theo cụm:
    assert set(dd._REQUIRED_VALIDATION_SECTIONS) == {
        "pci_2011_2022",
        "pci_top30_2023_2024",
        "odm_health_2020",
        "grdp_2018_2024",
    }
    assert "wdi" not in APP_PATH.read_text(encoding="utf-8").lower()

    at = run_app(TAB_EXTERNAL)
    assert not at.exception
    assert not at.error
    text = "\n".join(container_texts(at.tabs[3]))
    for header in (
        "Kiểm định khác biệt PCI",
        "Kiểm tra phụ: Top-30 2023–2024",
        "Mật độ cơ sở y tế 2020",
        "GRDP/người",
    ):
        assert header in text  # Tab 4 render đúng 4 section theo cụm
    assert "WDI" not in text
    assert "World Bank" not in text


def test_risk9_streamlit_runtime_matches_requirements_pin():
    """app.py dùng API mới (st.tabs on_change='rerun', Tab.open, width='stretch')
    chỉ có ở Streamlit neo trong requirements.txt; test chạy phải đúng pin."""
    pin = next(
        line.split("==")[1].strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.startswith("streamlit==")
    )
    assert st.__version__ == pin
    # Tái hiện StreamlitAPIException bằng phiên bản thấp hơn pin: NOT_RUN —
    # môi trường cấm pip install (ràng buộc của ask).


def test_risk10_cluster_counts_fit_within_plotly_palette(assets, external_assets):
    """app.py:260/500 zip(sorted(clusters), px.colors.qualitative.Safe): cụm
    thứ 8+ sẽ rơi ra ngoài palette. Đọc số cụm từ artifact — rerun STING sinh
    thêm cụm sẽ làm test này lộ."""
    palette_size = len(px.colors.qualitative.Safe)
    assignments = assets["assignments"]
    per_year_clusters = assignments.groupby("year")["pred_cluster"].nunique(dropna=True)
    assert int(per_year_clusters.max()) <= palette_size
    _, counts = prepare_external_pci_view(external_assets["pci"], assignments)
    assert len(counts["clusters"]) <= palette_size


def test_risk11_grdp_rows_without_year_render_silently(external_assets, tmp_path, monkeypatch):
    """GRDP không có year → st.info thay chart rỗng, không crash."""
    validation = external_assets["validation"].copy()
    validation.loc[validation.section.eq("grdp_2018_2024"), "year"] = np.nan
    stage_external_artifacts(tmp_path, validation_frame=validation)
    patch_external_assets(monkeypatch, tmp_path)

    at = run_app(TAB_EXTERNAL)

    assert not at.exception
    assert not at.error
    external = at.tabs[3]
    text = "\n".join(container_texts(external))
    assert "Mật độ cơ sở y tế 2020" in text  # section y tế vẫn render trước
    assert "GRDP/người" in text  # section GRDP vẫn render
    info_messages = [element.value for element in at.info]
    assert any("GRDP" in message for message in info_messages)
    plotly_charts = [child for child in external.children.values() if child.type == "plotly_chart"]
    assert len(plotly_charts) == 2  # box PCI + box poverty (không line GRDP rỗng)
