"""Local, read-only Streamlit dashboard for the saved PAPI/STING results."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.check_data import scale_audit
from scripts.dashboard_data import (
    PCI_TOP30_WINDOW,
    DashboardDataError,
    ensure_external_pci_consistency,
    external_pci_group_stats,
    external_section_frame,
    filter_regression_holdout,
    format_p_value,
    format_poverty_window,
    load_classifier_model,
    load_dashboard_assets,
    load_external_validation_assets,
    load_poverty_assets,
    load_regression_models,
    poverty_cluster_tests,
    poverty_noise_vs_c2,
    prepare_classification_holdout,
    prepare_external_pci_view,
    prepare_poverty_cluster_view,
    select_classification_model,
    prepare_regression_holdout,
    prepare_sting_view,
    select_regression_model,
)
from scripts.fig_style import CLUSTER_COLORS
from scripts.papi_pred_common import FEATURE_LABELS, ROOT


st.set_page_config(
    page_title="PAPI · Phân tích STING",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #f7f9fc; color: #172033; }
      [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #e5eaf2; border-radius: 14px;
        padding: 14px 16px;
      }
      [data-testid="stMetricLabel"] { color: #536179 !important; }
      [data-testid="stMetricValue"] { color: #172033 !important; }
      .block-container { padding-top: 1.8rem; padding-bottom: 2.5rem; }
      div[data-testid="stAlert"] { border-radius: 12px; }
      div[data-testid="stAlert"] [data-testid="stMarkdownContainer"],
      div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
        color: #172033 !important;
      }
      .eyebrow { color: #2563eb; font-weight: 700; letter-spacing: .08em;
        text-transform: uppercase; font-size: .78rem; }
      .muted { color: #64748b; }
    </style>
    """,
    unsafe_allow_html=True,
)


_ASSET_FILES = (
    "data/processed/papi_panel_63_2011_2024.csv",
    "models/predict_config.json",
    "results/predict_all_years.csv",
    "results/supervised_metrics.csv",
)
_REGRESSION_MODEL_FILES = (
    "models/sup_ridge.joblib",
    "models/sup_rf.joblib",
)
_CLASSIFIER_MODEL_FILES = ("models/sup_classifier.joblib",)
_EXTERNAL_FILES = (
    "data/processed/external_pci_63_full.csv",
    "results/external_validation.csv",
)
_POVERTY_FILES = ("data/processed/external_poverty_63.csv",)


def artifact_identity(relative_paths: tuple[str, ...]) -> tuple[tuple[str, int | None, int | None], ...]:
    """(path, mtime_ns, size) for each file, including paths that are missing."""
    identity: list[tuple[str, int | None, int | None]] = []
    for relative in relative_paths:
        path = ROOT / relative
        if path.is_file():
            stat = path.stat()
            identity.append((relative, stat.st_mtime_ns, stat.st_size))
        else:
            identity.append((relative, None, None))
    return tuple(identity)


@st.cache_resource(show_spinner="Đang đọc dữ liệu PAPI đã lưu…")
def get_assets(artifact_identity: tuple[tuple[str, int | None, int | None], ...]) -> dict:
    del artifact_identity
    return load_dashboard_assets(include_models=False)


@st.cache_resource(show_spinner="Đang nạp model hồi quy…")
def get_regression_models(artifact_identity: tuple[tuple[str, int | None, int | None], ...]) -> dict:
    del artifact_identity
    return load_regression_models()


@st.cache_resource(show_spinner="Đang nạp model phân loại…")
def get_classifier_model(artifact_identity: tuple[tuple[str, int | None, int | None], ...]):
    del artifact_identity
    return load_classifier_model()


@st.cache_resource(show_spinner="Đang đọc artifact kiểm chứng ngoại lai…")
def get_external_assets(artifact_identity: tuple[tuple[str, int | None, int | None], ...]) -> dict:
    del artifact_identity
    return load_external_validation_assets()


@st.cache_resource(show_spinner="Đang đọc artifact nghèo GSO…")
def get_poverty_assets(artifact_identity: tuple[tuple[str, int | None, int | None], ...]) -> dict:
    del artifact_identity
    return load_poverty_assets()


def feature_label(feature: str, config: dict) -> str:
    return config.get("feature_labels", {}).get(feature, FEATURE_LABELS.get(feature, feature))


def province_name_map(panel: pd.DataFrame) -> dict[int, str]:
    names = panel[["province_code", "province_vi"]].drop_duplicates()
    return {int(row.province_code): str(row.province_vi) for row in names.itertuples()}


def cluster_label(value: int | str) -> str:
    if value == "Tất cả":
        return value
    cluster = int(value)
    return "Nhiễu (-1)" if cluster == -1 else f"Cụm {cluster}"


def render_empty(message: str) -> None:
    st.info(message)


st.markdown('<div class="eyebrow">PAPI · 63 tỉnh · 2011–2024</div>', unsafe_allow_html=True)
st.title("Khám phá kết quả STING và dự báo PAPI")
st.caption(
    "Dashboard local chỉ đọc dữ liệu và model đã lưu. App không huấn luyện lại, "
    "không ghi artifact và không gửi dữ liệu ra ngoài."
)

try:
    assets = get_assets(artifact_identity(_ASSET_FILES))
except DashboardDataError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"Không đọc được artifact local: {exc}")
    st.stop()

panel = assets["panel"]
config = assets["config"]
assignments = assets["assignments"]
metrics = assets["metrics"]
features = list(config["features"])
names = province_name_map(panel)
years = sorted(int(year) for year in assignments.year.dropna().unique())
if not years:
    st.error("Artifact assignment không có năm hợp lệ.")
    st.stop()

with st.sidebar:
    st.header("Bộ lọc STING")
    selected_year = st.selectbox("Năm assignment", years, index=years.index(max(years)))
    province_options = sorted(
        int(code)
        for code in panel.loc[panel.year.eq(selected_year), "province_code"].dropna().unique()
    )
    selected_provinces = st.multiselect(
        "Tỉnh / thành phố",
        options=province_options,
        default=[],
        format_func=lambda code: names.get(int(code), str(code)),
        placeholder="Chọn tỉnh/thành phố…",
        help="Để trống để xem tất cả tỉnh trong năm đang chọn.",
    )
    year_clusters = sorted(
        int(cluster)
        for cluster in assignments.loc[
            assignments.year.eq(selected_year), "pred_cluster"
        ].dropna().unique()
    )
    selected_cluster = st.selectbox(
        "Cụm STING",
        options=["Tất cả", *year_clusters],
        format_func=cluster_label,
        help="-1 là điểm nhiễu, không phải một cụm thông thường.",
    )
    st.divider()
    st.caption("Năm và cụm ở đây chỉ lọc các mục STING; không lọc holdout hồi quy.")

sting_view, sting_counts = prepare_sting_view(
    panel,
    assignments,
    selected_year,
    province_codes=set(selected_provinces) if selected_provinces else None,
    cluster_codes=None if selected_cluster == "Tất cả" else {int(selected_cluster)},
    required_features=features,
)

_, regression_counts = prepare_regression_holdout(panel, assignments)
holdout_pair_count = regression_counts["holdout_pairs"]
try:
    selected_model = select_regression_model(metrics)
except ValueError as exc:
    st.error(str(exc))
    selected_model = ""
overview_tab, sting_tab, regression_tab, external_tab, audit_tab = st.tabs(
    [
        "Tổng quan",
        "STING theo năm",
        "Hồi quy 2023 → 2024",
        "Kiểm chứng ngoại lai",
        "Audit dữ liệu",
    ],
    key="dashboard_tabs",
    on_change="rerun",
)

with overview_tab:
    st.subheader(f"Ảnh chụp dữ liệu năm {selected_year}")
    eligible = sting_counts["eligible_assignments"]
    coverage = sting_counts["covered_rows"] / eligible if eligible else 0.0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tỉnh trong panel", f"{sting_counts['source_rows']}")
    col2.metric("Có assignment", f"{eligible}", help="Dòng có assignment trong artifact STING.")
    col3.metric("Nằm trong cụm", f"{coverage:.0%}", help="Không tính điểm nhiễu -1 là covered.")
    col4.metric("Nhiễu (-1)", f"{sting_counts['noise_rows']}")

    if selected_year == 2024:
        st.info(
            "Kết quả STING 2024 là assignment ngoài mẫu vào lưới đã fit bằng dữ liệu đến 2023. "
            "Đây không phải accuracy dự báo so với nhãn xã hội chuẩn."
        )
    else:
        st.caption("Các năm 2011–2023 là dữ liệu train/in-sample của lưới STING đã lưu.")

    selected_clf_name = ""
    try:
        selected_clf_name = select_classification_model(metrics)
    except ValueError:
        pass
    reg_kpi = metrics.loc[
        metrics.task.eq("regression")
        & metrics.model.isin([selected_model, "carry-forward (giữ giá trị năm nay)"])
    ]
    clf_kpi = metrics.loc[
        metrics.task.eq("classification")
        & metrics.model.isin([selected_clf_name, "majority (lớp đa số)"])
    ]
    if (
        len(reg_kpi) == 2
        and reg_kpi.holdout_mae.notna().all()
        and len(clf_kpi) == 2
        and clf_kpi.holdout_acc.notna().all()
        and clf_kpi.holdout_macro_f1.notna().all()
    ):
        st.markdown("#### Kết quả chính — holdout 2023 → 2024")
        reg_sel = reg_kpi.loc[reg_kpi.model.eq(selected_model)].iloc[0]
        reg_carry = reg_kpi.loc[reg_kpi.model.str.startswith("carry-forward")].iloc[0]
        clf_sel = clf_kpi.loc[clf_kpi.model.eq(selected_clf_name)].iloc[0]
        clf_maj = clf_kpi.loc[clf_kpi.model.str.startswith("majority")].iloc[0]
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(f"{selected_model.capitalize()} · CV R²", f"{reg_sel.value_cv:.3f}")
        kpi2.metric(
            "MAE holdout",
            f"{reg_sel.holdout_mae:.4f}",
            delta=f"{reg_sel.holdout_mae / reg_carry.holdout_mae - 1:.1%} so carry-forward",
            delta_color="inverse",
        )
        kpi3.metric(
            "Accuracy pseudo-label",
            f"{clf_sel.holdout_acc:.3f}",
            delta=f"{clf_sel.holdout_acc - clf_maj.holdout_acc:+.2f} so majority",
        )
        kpi4.metric(
            "Macro-F1 pseudo-label",
            f"{clf_sel.holdout_macro_f1:.3f}",
            delta=f"{clf_sel.holdout_macro_f1 - clf_maj.holdout_macro_f1:+.2f} so majority",
        )
        st.caption(
            f"Model chọn bằng CV train-only: hồi quy {selected_model}, phân loại "
            f"{selected_clf_name}. Delta so với baseline trên cùng {holdout_pair_count} cặp "
            "holdout; bảng chi tiết ở tab Hồi quy và Audit."
        )

    st.markdown("#### Phạm vi đang xem")
    st.write(
        f"Bộ lọc STING hiện giữ **{sting_counts['filtered_rows']}** dòng. "
        f"Có **{sting_counts['filtered_missing_feature_rows']}** dòng thiếu feature và "
        f"**{sting_counts['filtered_unassigned_artifact_rows']}** dòng đủ feature nhưng không có assignment "
        "trong artifact."
    )
    st.markdown("#### Hồi quy được đánh giá riêng")
    model_phrase = (
        f"Chọn theo CV train-only: **{selected_model.title()}**."
        if selected_model
        else "Không chọn được model hồi quy từ CV."
    )
    st.write(
        f"Holdout cố định: **2023 → 2024**, {holdout_pair_count} cặp tỉnh. "
        f"{model_phrase} "
        "Bộ lọc năm/cụm STING ở sidebar không áp dụng cho holdout."
    )
    st.warning(
        "Kết quả hồi quy chỉ có một năm holdout; nhãn phân loại là pseudo-label STING. "
        "Không dùng các chỉ số này để khẳng định năng lực dự báo xã hội tổng quát."
    )

with sting_tab:
    st.subheader(f"Phân bố assignment STING · {selected_year}")
    if len(features) < 2:
        st.error("Cấu hình cần ít nhất 2 feature để vẽ scatter.")
    elif sting_view.empty:
        render_empty("0 dòng phù hợp. Hãy mở rộng bộ lọc tỉnh hoặc chọn một cụm khác.")
    else:
        st.caption(
            f"Trục X: {feature_label(features[0], config)} · "
            f"Trục Y: {feature_label(features[1], config)}. "
            "Bảng bên dưới giữ cả dòng thiếu feature hoặc thiếu assignment."
        )
        plot_data = sting_view.dropna(subset=features + ["pred_cluster"]).copy()
        if plot_data.empty:
            render_empty("Các dòng đang lọc chưa có đủ feature và assignment để vẽ biểu đồ.")
        else:
            plot_data["Cụm"] = plot_data.pred_cluster.map(
                lambda value: "Nhiễu (-1)" if int(value) == -1 else f"Cụm {int(value)}"
            )
            palette = {"Nhiễu (-1)": "#64748b"}
            palette.update(
                {f"Cụm {code}": color for code, color in zip(sorted(year_clusters), px.colors.qualitative.Safe)}
            )
            figure = px.scatter(
                plot_data,
                x=features[0],
                y=features[1],
                color="Cụm",
                color_discrete_map=palette,
                hover_name="province_vi",
                hover_data={"province_code": True, "year": True, "Cụm": True},
                labels={
                    features[0]: feature_label(features[0], config),
                    features[1]: feature_label(features[1], config),
                },
                title="Mỗi điểm là một tỉnh có feature và assignment",
            )
            figure.update_traces(marker={"size": 11, "opacity": 0.82, "line": {"width": 0.7, "color": "white"}})
            figure.update_traces(
                marker={"line": {"width": 0.7, "color": "#172033"}},
                selector={"name": "Nhiễu (-1)"},
            )
            figure.update_layout(
                template="plotly_white",
                height=470,
                legend_title_text="Assignment",
                margin={"t": 70, "r": 20, "b": 20, "l": 20},
            )
            st.plotly_chart(figure, width="stretch")

        st.caption(
            f"{sting_counts['filtered_rows']} dòng sau lọc · "
            f"{sting_counts['filtered_noise_rows']} nhiễu · "
            f"{sting_counts['filtered_missing_feature_rows']} thiếu feature · "
            f"{sting_counts['filtered_unassigned_artifact_rows']} không có assignment trong artifact."
        )
        display_columns = [
            "province_code", "province_vi", "year", *features,
            "pred_cluster", "cluster_label", "assignment_state", "split",
        ]
        st.dataframe(
            sting_view[[column for column in display_columns if column in sting_view.columns]],
            hide_index=True,
            width="stretch",
            column_config={
                "province_code": st.column_config.NumberColumn("Mã tỉnh", format="%d"),
                "province_vi": "Tỉnh / thành phố",
                "year": st.column_config.NumberColumn("Năm", format="%d"),
                "pred_cluster": st.column_config.NumberColumn("Mã cụm", format="%d"),
                "cluster_label": "Nhãn hiển thị",
                "assignment_state": "Trạng thái dữ liệu",
                "split": "Tập STING",
            },
        )

if regression_tab.open:
    with regression_tab:
        try:
            regression_models = get_regression_models(artifact_identity(_REGRESSION_MODEL_FILES))
            regression, regression_counts = prepare_regression_holdout(
                panel,
                assignments,
                regression_models["ridge"],
                regression_models["random_forest"],
            )
        except DashboardDataError as exc:
            st.error(str(exc))
            st.info("Phần STING và Tổng quan vẫn dùng được. Làm theo hướng dẫn trong thông báo rồi làm mới ứng dụng.")
        except Exception as exc:
            st.error(f"Không thể nạp hoặc áp dụng model hồi quy local: {exc}")
            st.info("Phần STING và Tổng quan vẫn dùng được. Chạy lại `python scripts/predict_supervised.py`, rồi làm mới ứng dụng.")
        else:
            st.subheader("Holdout hồi quy cố định: 2023 → 2024")
            st.caption(
                "Bộ lọc dưới đây chỉ chọn nhóm để xem bảng/biểu đồ. Các metric trong artifact "
                "luôn tính trên toàn bộ holdout và không được tính lại từ nhóm đã lọc."
            )
            holdout_names = province_name_map(regression)
            reg_col1, reg_col2 = st.columns([2, 1])
            with reg_col1:
                regression_provinces = st.multiselect(
                    "Tỉnh / thành phố (holdout)",
                    options=sorted(int(code) for code in regression.province_code.unique()),
                    default=[],
                    format_func=lambda code: holdout_names.get(int(code), str(code)),
                    placeholder="Chọn tỉnh/thành phố…",
                    help="Để trống để xem tất cả cặp holdout.",
                )
            with reg_col2:
                origin_clusters = sorted(
                    int(code) for code in regression.origin_cluster_2023.dropna().unique()
                )
                regression_clusters = st.multiselect(
                    "Cụm STING tại năm gốc 2023",
                    options=origin_clusters,
                    default=[],
                    format_func=cluster_label,
                    placeholder="Chọn cụm STING…",
                    help="Chỉ dùng assignment năm 2023; không lọc theo cụm 2024 vì có thể điều kiện hóa trên target.",
                )
            regression_view, filter_counts = filter_regression_holdout(
                regression,
                province_codes=set(regression_provinces) if regression_provinces else None,
                origin_clusters=set(regression_clusters) if regression_clusters else None,
            )

            overall_regression = metrics.loc[
                metrics.task.eq("regression")
                & metrics.model.isin(["carry-forward (giữ giá trị năm nay)", "ridge", "random forest"])
            ].copy()
            overall_regression["Được chọn theo CV"] = overall_regression.model.eq(selected_model)
            st.markdown("#### So sánh trên toàn bộ holdout")
            st.dataframe(
                overall_regression[["model", "value_cv", "holdout_mae", "holdout_rmse", "holdout_r2", "Được chọn theo CV"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "model": "Mô hình / baseline",
                    "value_cv": st.column_config.NumberColumn("CV train-only · R²", format="%.3f"),
                    "holdout_mae": st.column_config.NumberColumn(
                        f"MAE · {regression_counts['holdout_pairs']} cặp", format="%.4f"
                    ),
                    "holdout_rmse": st.column_config.NumberColumn(
                        f"RMSE · {regression_counts['holdout_pairs']} cặp", format="%.4f"
                    ),
                    "holdout_r2": st.column_config.NumberColumn(
                        f"R² · {regression_counts['holdout_pairs']} cặp", format="%.3f"
                    ),
                    "Được chọn theo CV": st.column_config.CheckboxColumn("Chọn bằng CV"),
                },
            )
            # Bảng cố tình chỉ so baseline carry-forward + 2 họ đã tune; các dòng
            # regression khác trong artifact được liệt kê tường minh ở đây thay vì
            # lọc im lặng (đổi tên model trong CSV sẽ lộ ra chỗ này).
            dropped_regression_rows = metrics.loc[
                metrics.task.eq("regression")
                & ~metrics.model.isin(overall_regression.model)
            ]
            if not dropped_regression_rows.empty:
                st.caption(
                    "Bảng trên chỉ so sánh baseline giữ nguyên giá trị và 2 họ model "
                    "được tune. Dòng regression khác trong supervised_metrics.csv nhưng "
                    "không thuộc bảng so sánh: "
                    + ", ".join(dropped_regression_rows.model.astype(str)) + "."
                )
            st.warning(
                "R² CV hồi quy là điểm chọn họ model bằng expanding origin 2017–2022 "
                "(warm-up 2011–2016); holdout không tham gia chọn model. "
                "Holdout 2023→2024 chỉ đánh giá một lần."
            )

            reg_m1, reg_m2, reg_m3, reg_m4 = st.columns(4)
            reg_m1.metric("Cặp holdout sau lọc", f"{len(regression_view)}")
            reg_m2.metric("Thiếu feature origin", f"{regression_counts['missing_origin_feature_rows']}")
            reg_m3.metric("Thiếu target 2024", f"{regression_counts['missing_target_for_complete_origin']}")
            reg_m4.metric("Thiếu cụm origin 2023", f"{filter_counts['missing_origin_cluster_after_province_filter']}")

            if regression_view.empty:
                render_empty("0 cặp tỉnh phù hợp. Hãy mở rộng bộ lọc tỉnh hoặc cụm origin năm 2023.")
            else:
                values = pd.concat(
                    [regression_view.actual_2024, regression_view.prediction_ridge, regression_view.prediction_random_forest]
                )
                low, high = float(values.min()), float(values.max())
                figure = go.Figure()
                figure.add_trace(go.Scatter(
                    x=[low, high], y=[low, high], mode="lines", name="Dự báo hoàn hảo (y=x)",
                    line={"color": "#94a3b8", "dash": "dash"},
                ))
                for column, base_label, model_name, color in [
                    ("prediction_ridge", "Ridge", "ridge", "#2563eb"),
                    ("prediction_random_forest", "Random Forest", "random forest", "#d97706"),
                ]:
                    label = f"{base_label} · chọn bằng CV" if selected_model == model_name else base_label
                    figure.add_trace(go.Scatter(
                        x=regression_view.actual_2024,
                        y=regression_view[column],
                        mode="markers",
                        name=label,
                        marker={"color": color, "size": 10, "opacity": 0.8},
                        text=regression_view.province_vi,
                        customdata=regression_view[["province_code", "origin_cluster_label"]],
                        hovertemplate=(
                            "%{text}<br>Thực tế 2024: %{x:.3f}<br>Dự báo: %{y:.3f}"
                            "<br>Mã tỉnh: %{customdata[0]}<br>Cụm gốc: %{customdata[1]}<extra></extra>"
                        ),
                    ))
                figure.update_layout(
                    template="plotly_white",
                    height=460,
                    xaxis_title="Giá trị thực sd_6_1 năm 2024",
                    yaxis_title="Giá trị dự báo sd_6_1",
                    legend_title_text="Model",
                    margin={"t": 30, "r": 20, "b": 20, "l": 20},
                )
                st.plotly_chart(figure, width="stretch")
                table = regression_view[[
                    "province_code", "province_vi", "origin_cluster_label", "sd_6_1",
                    "actual_2024", "carry_forward", "prediction_ridge", "prediction_random_forest",
                ]].rename(columns={
                    "province_code": "Mã tỉnh",
                    "province_vi": "Tỉnh / thành phố",
                    "origin_cluster_label": "Cụm STING 2023",
                    "sd_6_1": "sd_6_1 thực 2023",
                    "actual_2024": "sd_6_1 thực 2024",
                    "carry_forward": "Baseline giữ nguyên 2023",
                    "prediction_ridge": "Dự báo Ridge",
                    "prediction_random_forest": "Dự báo Random Forest",
                })
                st.dataframe(table, hide_index=True, width="stretch")

if external_tab.open:
    with external_tab:
        try:
            external_assets = get_external_assets(artifact_identity(_EXTERNAL_FILES))
            pci_view, pci_counts = prepare_external_pci_view(
                external_assets["pci"], assignments
            )
            pci_tests = ensure_external_pci_consistency(
                pci_view, external_assets["validation"]
            )
            top_view, top_counts = prepare_external_pci_view(
                external_assets["pci"], assignments, *PCI_TOP30_WINDOW
            )
            top_tests = ensure_external_pci_consistency(
                top_view, external_assets["validation"], section="pci_top30_2023_2024"
            )
        except DashboardDataError as exc:
            st.error(str(exc))
            st.info(
                "Phần STING, Tổng quan và Hồi quy vẫn dùng được. "
                "Chạy lại `python scripts/external_validation.py`, rồi làm mới ứng dụng."
            )
        except Exception as exc:
            st.error(f"Không đọc được artifact kiểm chứng ngoại lai: {exc}")
            st.info("Phần còn lại của dashboard vẫn dùng được.")
        else:
            st.subheader("Kiểm chứng ngoại lai bằng nguồn độc lập với PAPI")
            st.caption(
                "PCI (VCCI–USAID, khảo sát **doanh nghiệp**) và các nguồn GSO / OD Mekong tách "
                "hoàn toàn khỏi PAPI (khảo sát hộ dân). Nhãn cụm lấy từ model STING đóng băng "
                "(`results/predict_all_years.csv`). Bộ lọc sidebar không áp dụng cho tab này — "
                "số liệu luôn tính trên toàn bộ lưới để khớp artifact đã công bố."
            )

            ext_m1, ext_m2, ext_m3, ext_m4 = st.columns(4)
            ext_m1.metric("Ô PCI có điểm 2011–2022", f"{pci_counts['window_cells']}")
            ext_m2.metric(
                "Điểm vào kiểm định",
                f"{pci_counts['tested_points']}",
                help="Ô có điểm PCI và có nhãn cụm từ model đóng băng.",
            )
            ext_m3.metric(
                "Có điểm nhưng thiếu nhãn",
                f"{pci_counts['missing_label_cells']}",
                help="Panel PAPI thiếu sd_4_2/sd_6_1 các năm đó nên không có nhãn — không nội suy.",
            )
            ext_m4.metric("Nhóm so sánh", f"{len(pci_counts['clusters'])}")

            palette = {"Nhiễu (-1)": "#64748b"}
            palette.update(
                {
                    f"Cụm {code}": color
                    for code, color in zip(sorted(pci_counts["clusters"]), px.colors.qualitative.Safe)
                }
            )
            cluster_order = [cluster_label(code) for code in sorted(pci_counts["clusters"])]
            pci_figure = px.box(
                pci_view,
                x="cluster_label",
                y="pci_weighted_score",
                color="cluster_label",
                category_orders={"cluster_label": cluster_order},
                color_discrete_map=palette,
                points="all",
                hover_name="province_vi",
                hover_data={"province_code": True, "year": True, "cluster_label": False},
                labels={"cluster_label": "Nhãn cụm STING", "pci_weighted_score": "PCI điểm tổng"},
                title="PCI (VCCI–USAID) theo cụm STING — lưới đầy 2011–2022",
            )
            pci_figure.update_traces(
                marker={"size": 5, "opacity": 0.45, "line": {"width": 0.5, "color": "white"}}
            )
            pci_figure.update_layout(
                template="plotly_white",
                height=470,
                showlegend=False,
                xaxis_title="Nhãn cụm STING (pred_cluster)",
                yaxis_title="PCI điểm tổng (VCCI–USAID)",
                margin={"t": 70, "r": 20, "b": 20, "l": 20},
            )
            st.plotly_chart(pci_figure, width="stretch")

            st.markdown("#### Kiểm định khác biệt PCI giữa các nhóm")
            tests_table = pd.DataFrame([
                {
                    "Kiểm định": f"One-way ANOVA F({pci_tests['df1']},{pci_tests['df2']})",
                    "Giá trị": f"{pci_tests['f']:.4f}",
                    "p-value": format_p_value(pci_tests["p_anova"]),
                    "n": pci_tests["n"],
                },
                {
                    "Kiểm định": "Kruskal–Wallis H",
                    "Giá trị": f"{pci_tests['h']:.4f}",
                    "p-value": format_p_value(pci_tests["p_kw"]),
                    "n": pci_tests["n"],
                },
                {
                    "Kiểm định": "Eta² (SS giữa / SS tổng)",
                    "Giá trị": f"{pci_tests['eta_sq']:.4f}",
                    "p-value": "—",
                    "n": pci_tests["n"],
                },
            ])
            st.dataframe(tests_table, hide_index=True, width="stretch")
            st.caption(
                "Tính lại bằng scipy trên chính các điểm ở biểu đồ trên, rồi tự đối chiếu với "
                "`results/external_validation.csv` — nếu lệch vượt sai số làm tròn, tab này dừng "
                "thay vì hiển thị một số khác số đã công bố."
            )

            st.markdown("#### Thống kê theo nhóm")
            pci_group_table = external_pci_group_stats(pci_view)
            st.dataframe(
                pci_group_table[["cluster_label", "n", "mean", "median", "std", "min", "max"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "cluster_label": "Nhóm",
                    "n": st.column_config.NumberColumn("n", format="%d"),
                    "mean": st.column_config.NumberColumn("Mean", format="%.3f"),
                    "median": st.column_config.NumberColumn("Median", format="%.3f"),
                    "std": st.column_config.NumberColumn("Std (ddof=1)", format="%.3f"),
                    "min": st.column_config.NumberColumn("Min", format="%.2f"),
                    "max": st.column_config.NumberColumn("Max", format="%.2f"),
                },
            )

            pci_all = external_assets["pci"]
            top_window = pci_all.year.isin(PCI_TOP30_WINDOW)
            top_scored = int((top_window & pci_all.pci_weighted_score.notna()).sum())
            top_empty = int((top_window & pci_all.pci_weighted_score.isna()).sum())
            st.warning(
                f"**Caveat chọn mẫu:** PCI 2023–2024 nhà xuất bản chỉ công bố Top-30 tỉnh tốt — "
                f"{top_empty} ô trống trong hai năm đó, KHÔNG nội suy; {top_scored} ô có điểm chỉ "
                "dùng cho kiểm tra phụ bên dưới và không được ghép vào kiểm định chính 2011–2022."
            )

            st.markdown("#### Kiểm tra phụ: Top-30 2023–2024")
            top_sets = {
                year: set(
                    pci_all.loc[
                        pci_all.year.eq(year) & pci_all.pci_weighted_score.notna(),
                        "province_ascii",
                    ]
                )
                for year in PCI_TOP30_WINDOW
            }
            st.caption(
                "Chỉ đọc như kiểm tra phụ: mẫu chọn theo thành tích nên mean bị kéo lên; "
                f"{top_counts['window_cells']} ô có điểm, {top_counts['tested_points']} ô có nhãn "
                f"(thiếu nhãn {top_counts['missing_label_cells']}); "
                f"{len(top_sets[2023] & top_sets[2024])} tỉnh chung hai năm; chỉ 2023 có: "
                f"{', '.join(sorted(top_sets[2023] - top_sets[2024])) or '—'}; chỉ 2024 có: "
                f"{', '.join(sorted(top_sets[2024] - top_sets[2023])) or '—'}."
            )
            top_table = pd.DataFrame([
                {
                    "Kiểm định": f"One-way ANOVA F({top_tests['df1']},{top_tests['df2']})",
                    "Giá trị": f"{top_tests['f']:.4f}",
                    "p-value": format_p_value(top_tests["p_anova"]),
                    "n": top_tests["n"],
                },
                {
                    "Kiểm định": "Kruskal–Wallis H",
                    "Giá trị": f"{top_tests['h']:.4f}",
                    "p-value": format_p_value(top_tests["p_kw"]),
                    "n": top_tests["n"],
                },
            ])
            st.dataframe(top_table, hide_index=True, width="stretch")

            st.markdown("#### Mật độ cơ sở y tế 2020 theo cụm")
            health = external_section_frame(external_assets["validation"], "odm_health_2020")
            st.dataframe(
                health[["cluster_label", "n", "mean", "median", "std", "min", "max", "note"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "cluster_label": "Nhóm",
                    "n": st.column_config.NumberColumn("Số tỉnh", format="%d"),
                    "mean": st.column_config.NumberColumn("Mean · cơ sở/1.000 dân", format="%.6f"),
                    "median": st.column_config.NumberColumn("Median", format="%.6f"),
                    "std": st.column_config.NumberColumn("Std", format="%.6f"),
                    "min": st.column_config.NumberColumn("Min", format="%.6f"),
                    "max": st.column_config.NumberColumn("Max", format="%.6f"),
                    "note": "Quy mô nhóm (tổng cơ sở / dân số → tỷ trọng)",
                },
            )
            st.caption(
                "Mean/Median tính trên các tỉnh trong nhóm; cột 'Quy mô nhóm' là tỷ trọng tính trên "
                "tổng quy mô nhóm. Nguồn: ODM Health Facilities 2020 (ODbL) point-in-polygon trên "
                "ranh giới 63 tỉnh + dân số GSO 2020. Snapshot một năm, đếm số ĐIỂM y tế chứ không "
                "phải số giường; các tỉnh có count = 0 là 0-thật (nguồn điểm không phủ — xem "
                "`results/external_validation.md`). Chỉ dùng làm external check một lần, không đưa vào feature."
            )

            st.markdown("#### GRDP/người theo cụm — chỉ cửa sổ 2018–2024")
            grdp = external_section_frame(external_assets["validation"], "grdp_2018_2024")
            grdp = grdp.loc[grdp.year.notna()].copy()
            if grdp.empty:
                render_empty("Không có dữ liệu GRDP theo năm trong artifact.")
            else:
                grdp["year"] = grdp.year.astype(int)
                grdp_figure = px.line(
                    grdp,
                    x="year",
                    y="median",
                    color="cluster_label",
                    markers=True,
                    color_discrete_map=palette,
                    hover_data={"n": True, "mean": True, "cluster_label": False},
                    labels={
                        "cluster_label": "Nhóm",
                        "year": "Năm",
                        "median": "GRDP/người (triệu đồng, trung vị)",
                    },
                    title="GRDP/người theo cụm STING — trung vị nhóm",
                )
                grdp_figure.update_layout(
                    template="plotly_white",
                    height=430,
                    xaxis={"dtick": 1, "title": "Năm"},
                    yaxis_title="GRDP/người (triệu đồng, trung vị nhóm)",
                    legend_title_text="Nhóm",
                    margin={"t": 70, "r": 20, "b": 20, "l": 20},
                )
                st.plotly_chart(grdp_figure, width="stretch")
            st.caption(
                "Nguồn GSO pxweb V03.12 chỉ phủ 2018–2024 — không nội suy 2011–2017; 2024 = Sơ bộ "
                "(chưa chính thức, có thể được sửa sau). Trong cửa sổ này gần như chỉ còn nhiễu vs "
                "cụm 2 (cụm 0 rỗng, cụm 1 còn ít điểm)."
            )

            # ----- Block bổ trợ: nghèo cấp tỉnh GSO V14.47 (thứ hai sau PCI).
            # try/except RIÊNG để lỗi artifact poverty không che 4 section kiểm
            # chứng phía trên; số hiển thị đều tự tính từ CSV (không hardcode).
            try:
                poverty_assets = get_poverty_assets(artifact_identity(_POVERTY_FILES))
                poverty_view, poverty_counts = prepare_poverty_cluster_view(
                    poverty_assets["poverty"], assignments
                )
                pov_tests_raw = poverty_cluster_tests(poverty_view, "poverty_rate_pct")
                pov_tests_dm = poverty_cluster_tests(poverty_view, "pov_dm")
                pov_mw_raw = poverty_noise_vs_c2(poverty_view, "poverty_rate_pct")
                pov_mw_dm = poverty_noise_vs_c2(poverty_view, "pov_dm")
            except DashboardDataError as exc:
                st.error(str(exc))
                st.info(
                    "Bốn section kiểm chứng phía trên vẫn dùng được. "
                    "Tạo lại artifact poverty theo hướng dẫn trong thông báo, rồi làm mới ứng dụng."
                )
            except Exception as exc:
                st.error(f"Không đọc được artifact nghèo GSO: {exc}")
                st.info("Bốn section kiểm chứng phía trên vẫn dùng được.")
            else:
                window_text = format_poverty_window(poverty_counts["overlap_years"])
                st.markdown(f"#### Nghèo cấp tỉnh (GSO V14.47) — cửa sổ giao {window_text}")
                pov_m1, pov_m2 = st.columns(2)
                pov_m1.metric(
                    "Ô poverty trong cửa sổ giao",
                    f"{poverty_counts['window_cells']}",
                    help=(
                        f"Cửa sổ giao poverty ↔ nhãn cụm: {window_text}; trong đó "
                        f"{poverty_counts['valid_cells']} ô có giá trị poverty."
                    ),
                )
                pov_m2.metric(
                    "Ô vào kiểm định theo cụm",
                    f"{poverty_counts['panel_rows']}",
                    help=(
                        "Ô có giá trị poverty VÀ có nhãn cụm từ model đóng băng — "
                        "dùng cho boxplot và kiểm định bên dưới."
                    ),
                )

                poverty_palette = {
                    cluster_label(code): CLUSTER_COLORS.get(code, "#64748b")
                    for code in poverty_counts["clusters"]
                }
                poverty_order = [cluster_label(code) for code in poverty_counts["clusters"]]
                poverty_figure = px.box(
                    poverty_view,
                    x="cluster_label",
                    y="poverty_rate_pct",
                    color="cluster_label",
                    category_orders={"cluster_label": poverty_order},
                    color_discrete_map=poverty_palette,
                    points="all",
                    hover_name="province_vi",
                    hover_data={"province_code": True, "year": True, "cluster_label": False},
                    labels={
                        "cluster_label": "Nhãn cụm STING",
                        "poverty_rate_pct": "Tỷ lệ hộ nghèo (%)",
                    },
                    title=f"Tỷ lệ hộ nghèo GSO theo cụm STING — cửa sổ giao {window_text}",
                )
                poverty_figure.update_traces(
                    marker={"size": 5, "opacity": 0.45, "line": {"width": 0.5, "color": "white"}}
                )
                poverty_figure.update_layout(
                    template="plotly_white",
                    height=470,
                    showlegend=False,
                    xaxis_title="Nhãn cụm STING (pred_cluster)",
                    yaxis_title="Tỷ lệ hộ nghèo (%)",
                    margin={"t": 70, "r": 20, "b": 20, "l": 20},
                )
                st.plotly_chart(poverty_figure, width="stretch")

                st.markdown("#### Hai kiểm định poverty — phải đọc CÙNG nhau")
                poverty_table = pd.DataFrame([
                    {
                        "Kiểm định": "Kruskal–Wallis H (gộp thô — nhiễm hiệu ứng năm)",
                        "Giá trị": f"{pov_tests_raw['h']:.4f}",
                        "p-value": format_p_value(pov_tests_raw["p_kw"]),
                        "n": pov_tests_raw["n"],
                    },
                    {
                        "Kiểm định": "Kruskal–Wallis H (đã trừ median trong năm)",
                        "Giá trị": f"{pov_tests_dm['h']:.4f}",
                        "p-value": format_p_value(pov_tests_dm["p_kw"]),
                        "n": pov_tests_dm["n"],
                    },
                    {
                        "Kiểm định": "Mann–Whitney U — nhiễu vs cụm 2 (thô)",
                        "Giá trị": f"{pov_mw_raw['u']:.0f}",
                        "p-value": format_p_value(pov_mw_raw["p"]),
                        "n": pov_mw_raw["n"],
                    },
                    {
                        "Kiểm định": "Mann–Whitney U — nhiễu vs cụm 2 (đã trừ median năm)",
                        "Giá trị": f"{pov_mw_dm['u']:.0f}",
                        "p-value": format_p_value(pov_mw_dm["p"]),
                        "n": pov_mw_dm["n"],
                    },
                ])
                st.dataframe(poverty_table, hide_index=True, width="stretch")

                med_by_year = poverty_view.groupby("year").poverty_rate_pct.median()
                noise_by_year = poverty_counts["noise_by_year"]
                first_year = poverty_counts["overlap_years"][0]
                recent_years = [year for year in poverty_counts["overlap_years"] if year >= 2020]
                recent_noise = [noise_by_year[year] for year in recent_years if year in noise_by_year]
                drift_phrase = (
                    f" với tỷ trọng cụm trôi theo năm (nhiễu {noise_by_year.get(first_year, 0)} ô "
                    f"năm {first_year} → {min(recent_noise)}–{max(recent_noise)} ô các năm "
                    f"{recent_years[0]}–{recent_years[-1]})"
                    if recent_noise
                    else ""
                )
                n_cluster_0 = poverty_counts["n_by_cluster"].get(0, 0)
                n_cluster_1 = poverty_counts["n_by_cluster"].get(1, 0)
                st.warning(
                    "**Đọc cả hai kết quả cùng nhau** — chuẩn nghèo ĐỔI theo giai đoạn nên so MỨC "
                    "tuyệt đối xuyên năm không like-for-like, chỉ so GIỮA CỤM trong cùng một năm "
                    f"hợp lệ: KW gộp thô {format_p_value(pov_tests_raw['p_kw'])} (không đáng kể) "
                    f"trong khi đã-trừ-median-năm {format_p_value(pov_tests_dm['p_kw'])} (đáng kể). "
                    "Test gộp thô phối trộn hiệu ứng năm (median nghèo "
                    f"{med_by_year.iloc[0]:.1f}% năm {int(med_by_year.index[0])} → "
                    f"{med_by_year.iloc[-1]:.1f}% năm {int(med_by_year.index[-1])}"
                    + drift_phrase + ")."
                )
                st.caption(
                    f"Cụm 0 (n={n_cluster_0}) và cụm 1 (n={n_cluster_1}) quá nhỏ để tự kết luận — "
                    f"cặp tương phản đáng tin duy nhất là nhiễu vs cụm 2 (Mann–Whitney: "
                    f"{format_p_value(pov_mw_raw['p'])} thô / "
                    f"{format_p_value(pov_mw_dm['p'])} đã-trừ-median-năm). Poverty là kiểm chứng bổ "
                    "trợ thứ hai sau PCI: thước đo độc lập GSO (thống kê chính thức, tách khỏi PAPI "
                    "khảo sát hộ dân), KHÔNG đưa vào feature, KHÔNG chứng minh nhân quả — không "
                    "thay thế kiểm định chính PCI."
                )
                missing_source_txt = "; ".join(
                    f"{cell['province_vi']} {int(cell['year'])} (code {int(cell['province_code'])})"
                    for cell in poverty_counts["missing_source_cells"]
                ) or "—"
                no_label_txt = "; ".join(
                    f"{cell['province_vi']} {int(cell['year'])}"
                    for cell in poverty_counts["no_label_cells"]
                ) or "—"
                st.caption(
                    f"Nguồn: GSO pxweb V14.47 → `data/processed/external_poverty_63.csv` "
                    f"(tạo lại bằng `python scripts/build_poverty_63.py`), nhãn cụm "
                    f"`results/predict_all_years.csv`; màu cụm theo `scripts/fig_style.py`. "
                    f"Thiếu phía nguồn — KHÔNG nội suy: {missing_source_txt}. "
                    f"{len(poverty_counts['no_label_cells'])} ô có poverty nhưng KHÔNG có nhãn cụm "
                    f"(mask tường minh, không vẽ không test): {no_label_txt}. Ngoài cửa sổ: năm "
                    f"poverty-only {poverty_counts['pov_only_years']} (không có nhãn cụm) và năm "
                    f"{poverty_counts['label_only_years']} (bảng pxweb V14.47 không có cột poverty)."
                )

            st.caption(
                "Nguồn local: `data/processed/external_pci_63_full.csv` (PCI VCCI–USAID — provenance "
                "`data/processed/external_provenance.md`, `data/raw/*/PROVENANCE.md`) và "
                "`results/external_validation.csv`; tạo lại bằng `python scripts/external_validation.py`."
            )

if audit_tab.open:
    with audit_tab:
        st.subheader("Feature, missingness và giới hạn thang đo")
        flags = scale_audit(panel)
        indicator_columns = [
            column for column in panel.columns
            if column.startswith(("d", "sd_")) and pd.api.types.is_numeric_dtype(panel[column])
        ]
        flag_col1, flag_col2, flag_col3 = st.columns(3)
        flag_col1.metric("Mean-jump heuristic", f"{len(flags)} / {len(indicator_columns)}")
        flag_col2.metric("Feature STING đang dùng", f"{len(features)}")
        flag_col3.metric(f"Thiếu feature toàn năm {selected_year}", f"{sting_counts['missing_feature_rows']}")
        st.warning(
            "Mean-jump > 0.25 điểm là heuristic để rà soát; nó không tự chứng minh gãy thang đo. "
            "Danh sách dưới đây tính trên toàn panel 2011–2024; quy tắc sweep eligibility dùng train đến 2020."
        )

        st.markdown("#### Cặp feature STING đã chốt")
        feature_rows = []
        for feature in features:
            feature_rows.append({
                "Feature": feature,
                "Chỉ tiêu": feature_label(feature, config),
                "Mean-jump flag toàn panel": any(row[0] == feature for row in flags),
                "Thiếu trong panel": int(panel[feature].isna().sum()),
            })
        st.dataframe(pd.DataFrame(feature_rows), hide_index=True, width="stretch")
        st.caption(f"Cấu hình đóng băng: STING(L={config['sting']['n_levels']}, factor={config['sting']['factor']}, min_count={config['sting']['min_count']}); không tối ưu từ giao diện.")

        flag_frame = pd.DataFrame(flags, columns=["Feature", "Max mean jump", "Năm lớn nhất"])
        if flag_frame.empty:
            render_empty("Không có cột nào vượt heuristic trên panel hiện tại.")
        else:
            st.markdown("#### Các cột có cờ heuristic")
            st.dataframe(flag_frame, hide_index=True, width="stretch")

        classification = metrics.loc[metrics.task.eq("classification")].copy()
        if not classification.empty:
            try:
                classifier = select_classification_model(metrics)
            except ValueError as exc:
                st.error(str(exc))
            else:
                classification["Được chọn theo CV"] = classification.model.eq(classifier)
                st.markdown("#### Phân loại pseudo-label STING")
                st.caption(
                    "Nhãn được dựng tại từng cutoff; CV expanding 2017–2022 sau warm-up 2011–2016. "
                    "Điểm đo mức khớp nhãn STING, không phải ground truth xã hội."
                )
                st.dataframe(
                    classification[["model", "value_cv", "holdout_acc", "holdout_macro_f1", "Được chọn theo CV"]],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "model": "Mô hình / baseline",
                        "value_cv": st.column_config.NumberColumn("CV · macro-F1", format="%.3f"),
                        "holdout_acc": st.column_config.NumberColumn("Accuracy pseudo-label", format="%.3f"),
                        "holdout_macro_f1": st.column_config.NumberColumn("Macro-F1 pseudo-label", format="%.3f"),
                        "Được chọn theo CV": st.column_config.CheckboxColumn("Chọn bằng CV"),
                    },
                )

                try:
                    classifier_model = get_classifier_model(
                        artifact_identity(_CLASSIFIER_MODEL_FILES)
                    )
                    clf_pairs, clf_counts = prepare_classification_holdout(
                        panel, assignments, classifier_model
                    )
                except DashboardDataError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Không thể nạp hoặc áp dụng classifier local: {exc}")
                else:
                    st.markdown("#### Dự báo nhãn từng tỉnh — holdout 2023 → 2024")
                    st.caption(
                        f"Artifact `models/sup_classifier.joblib` ({classifier}) dự báo "
                        "pseudo-label từ 8 chỉ số năm 2023. Nhãn thực tế lấy từ "
                        "`results/predict_all_years.csv` — cùng phép gán nhãn STING "
                        "của pipeline, không fit lại labeler."
                    )
                    clf_col1, clf_col2, clf_col3 = st.columns(3)
                    clf_col1.metric("Cặp holdout", clf_counts["holdout_pairs"])
                    clf_col2.metric(
                        "Dự báo đúng",
                        f"{clf_counts['correct']} · "
                        f"{clf_counts['correct'] / clf_counts['holdout_pairs']:.0%}",
                    )
                    clf_col3.metric(
                        "Vùng dày (dự báo / thực tế)",
                        f"{clf_counts['predicted_dense']} / {clf_counts['actual_dense']}",
                    )
                    label_names = {0: "ngoại vi", 1: "vùng dày"}
                    clf_view = clf_pairs.assign(
                        predicted=clf_pairs.predicted_label.map(label_names),
                        actual=clf_pairs.actual_label.map(label_names),
                    )
                    st.dataframe(
                        clf_view[["province_vi", "predicted", "actual", "correct"]],
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "province_vi": "Tỉnh / thành phố",
                            "predicted": "Nhãn dự báo",
                            "actual": "Nhãn thực tế (pseudo-label)",
                            "correct": st.column_config.CheckboxColumn("Đúng"),
                        },
                    )

st.divider()
st.caption(
    "Nguồn local: `data/processed/papi_panel_63_2011_2024.csv`, "
    "`results/predict_all_years.csv`, `results/supervised_metrics.csv` và model trong `models/`."
)
