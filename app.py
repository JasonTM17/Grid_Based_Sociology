"""Local, read-only Streamlit dashboard for the saved PAPI/STING results."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scripts.data.check_data import scale_audit
from scripts.analysis.dashboard_data import (
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
    load_high_dim_sting_assets,
    load_panel_inference_assets,
    load_poverty_assets,
    load_regression_deep_assets,
    load_regression_models,
    load_stakeholder_summary,
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
from scripts.analysis.client_product import (
    CUSTOMER_GROUP_COLORS,
    build_action_choropleth_figure,
    build_province_scorecard_html,
    customer_display_frame,
    load_vietnam_geojson,
    scorecard_filename,
)
from scripts.common.fig_style import CLUSTER_COLORS
from scripts.common.papi_pred_common import FEATURE_LABELS, ROOT


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
      @media (max-width: 1320px) {
        [data-testid="stMetric"] { padding: 10px 12px !important; }
        [data-testid="stMetricLabel"] { font-size: 0.82rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.45rem !important; }
      }
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
_GEOJSON_FILES = ("data/raw/boundaries/diaphantinh.geojson",)
_REGRESSION_DEEP_FILES = (
    "results/regression_deep_analysis.csv",
    "results/regression_conformal_2024.csv",
)
_HIGH_DIM_FILES = (
    "results/high_dim_sting.csv",
    "results/high_dim_sting_subspaces.csv",
)
_PANEL_INFERENCE_FILES = ("results/panel_inference.csv",)


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


@st.cache_resource(show_spinner="Đang nạp bản đồ ranh giới 63 tỉnh…")
def get_vietnam_geojson(artifact_identity: tuple[tuple[str, int | None, int | None], ...]) -> dict:
    del artifact_identity
    return load_vietnam_geojson(ROOT / "data" / "raw" / "boundaries" / "diaphantinh.geojson")


@st.cache_resource(show_spinner="Đang đọc phân tích hồi quy chuyên sâu…")
def get_regression_deep_assets(
    artifact_identity: tuple[tuple[str, int | None, int | None], ...],
) -> dict[str, pd.DataFrame] | None:
    del artifact_identity
    return load_regression_deep_assets()


@st.cache_resource(show_spinner="Đang đọc phân tích STING đa chiều…")
def get_high_dim_sting_assets(
    artifact_identity: tuple[tuple[str, int | None, int | None], ...],
) -> dict[str, pd.DataFrame] | None:
    del artifact_identity
    return load_high_dim_sting_assets()


@st.cache_resource(show_spinner="Đang đọc kiểm định suy luận bảng & FDR…")
def get_panel_inference_assets(
    artifact_identity: tuple[tuple[str, int | None, int | None], ...],
) -> pd.DataFrame | None:
    del artifact_identity
    return load_panel_inference_assets()


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


def cluster_palette(cluster_codes) -> dict[str, str]:
    """Consistent Okabe-Ito cluster colors with Safe fallback for cluster >= 3."""
    fallback = px.colors.qualitative.Safe
    palette: dict[str, str] = {}
    extra_index = 0
    for code in sorted({int(c) for c in cluster_codes}):
        label = cluster_label(code)
        if code in CLUSTER_COLORS:
            palette[label] = CLUSTER_COLORS[code]
        else:
            palette[label] = fallback[extra_index % len(fallback)]
            extra_index += 1
    return palette


def render_empty(message: str) -> None:
    st.info(message)


st.markdown('<div class="eyebrow">PAPI · 63 tỉnh · 2011–2024</div>', unsafe_allow_html=True)
st.title("Khám phá kết quả STING và dự báo PAPI")
st.caption(
    "Xem dữ liệu PAPI 2011–2024, lọc tỉnh và xuất bảng hoặc phiếu rà soát. "
    "Để bắt đầu, mở tab Thống kê khách hàng; các kết quả phản ánh phạm vi dữ liệu lịch sử."
)
with st.expander("Hướng dẫn đọc và nhận kết quả"):
    st.markdown(
        "1. Mở **Thống kê khách hàng** để xem đủ 63 tỉnh năm 2024, gồm cả hai tỉnh thiếu dữ liệu.\n"
        "2. Chọn tỉnh ở thanh bên hoặc nhóm mô tả trong tab, rồi đọc điểm 4.2, 6.1 và gợi ý rà soát.\n"
        "3. Tải CSV của các tỉnh đang lọc hoặc phiếu HTML của một tỉnh; mở HTML và dùng chức năng in để lưu PDF.\n\n"
        "Nhãn cụm không phải xếp hạng chất lượng. Tỉ lệ kịch bản ngoài vùng là kết quả hồi kiểm 2024, "
        "chưa phải xác suất cảnh báo. Hướng dẫn cài đặt, ý nghĩa từng cột và tình huống thường gặp: "
        "`reports/customer_guide.md`."
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
    st.caption(
        "Năm và cụm chỉ lọc phần Tổng quan/STING. Bộ lọc tỉnh cũng áp dụng cho "
        "bảng khách hàng; tab khách hàng luôn dùng năm 2024. Hồi quy giữ kỳ đánh giá 2023→2024."
    )

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
overview_tab, sting_tab, regression_tab, external_tab, audit_tab, client_tab = st.tabs(
    [
        "Tổng quan",
        "STING theo năm",
        "Hồi quy 2023 → 2024",
        "Kiểm chứng ngoại lai",
        "Audit dữ liệu",
        "Thống kê khách hàng",
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

    fw_bt_path = ROOT / "results" / "future_work_backtest.csv"
    fw_sp_path = ROOT / "results" / "future_work_spatial.csv"
    fw_tr_path = ROOT / "results" / "future_work_trajectory.csv"
    if fw_bt_path.is_file() and fw_sp_path.is_file() and fw_tr_path.is_file():
        with st.expander(
            "Mở rộng đã tích hợp: Quỹ đạo 2011–2024, Backtest cuốn chiếu & Không gian 2024",
            expanded=False,
        ):
            fw_bt = pd.read_csv(fw_bt_path)
            fw_sp = pd.read_csv(fw_sp_path)
            fw_tr = pd.read_csv(fw_tr_path)
            r42 = fw_bt.loc[fw_bt.target.eq("sd_4_2")]
            r61 = fw_bt.loc[fw_bt.target.eq("sd_6_1")]
            top_up = ", ".join(
                f"{r.province_vi} ({r.slope_6_1:+.4f})"
                for r in fw_tr.nlargest(3, "slope_6_1").itertuples()
            )
            top_dn = ", ".join(
                f"{r.province_vi} ({r.slope_6_1:+.4f})"
                for r in fw_tr.nsmallest(3, "slope_6_1").itertuples()
            )
            sp_61 = fw_sp.loc[fw_sp.variable.eq("sd_6_1")].iloc[0]
            sp_42 = fw_sp.loc[fw_sp.variable.eq("sd_4_2")].iloc[0]
            st.markdown(
                f"- **Backtest cuốn chiếu 2018→2023 (6 mốc):** Ridge thắng carry-forward về MAE ở "
                f"**{int((r42.mae_gain > 0).sum())}/{len(r42)}** năm với `sd_4_2` "
                f"(TB `{r42.mae_forecast.mean():.4f}` vs `{r42.mae_carry.mean():.4f}`) và "
                f"**{int((r61.mae_gain > 0).sum())}/{len(r61)}** năm với `sd_6_1` "
                f"(TB `{r61.mae_forecast.mean():.4f}` vs `{r61.mae_carry.mean():.4f}`); "
                f"`out_recall` TB `{fw_bt.out_recall_forecast.mean():.3f}` vs `{fw_bt.out_recall_carry.mean():.3f}`.\n"
                f"- **Quỹ đạo OLS 2011–2024 ({len(fw_tr)} tỉnh):** Top-3 tăng `6.1`: {top_up}; "
                f"Top-3 giảm/chậm: {top_dn}.\n"
                f"- **Tự tương quan không gian Queen 2024:** `sd_6_1` Moran's I = `{sp_61.moran_I:.4f}` "
                f"(`p_perm = {sp_61.p_perm:.4f}`), `sd_4_2` Moran's I = `{sp_42.moran_I:.4f}` "
                f"(`p_perm = {sp_42.p_perm:.4f}`). Chi tiết: `results/future_work.md`."
            )
            st.caption(
                "Nhánh rank-normalization trong từng năm (`E1`) giữ ở mức đối chiếu vì chia lưới "
                "thành 25 cụm và 54,1% nhiễu; cấu hình STING `3/4/5/2` giữ làm chuẩn chính."
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
            plot_data["Cụm"] = plot_data.pred_cluster.map(cluster_label)
            palette = cluster_palette(plot_data.pred_cluster)
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

        high_dim = get_high_dim_sting_assets(artifact_identity(_HIGH_DIM_FILES))
        if high_dim is not None:
            hd_sum = high_dim["summary"]
            with st.expander(
                "Mở rộng STING đa chiều: Thang thưa lưới, Subspace CLIQUE & Quantile STING",
                expanded=False,
            ):
                st.caption(
                    "Đối chiếu ngoài không gian 2D đóng băng (3/4/5/2 vẫn là mô hình chính): "
                    "mọi biên quantile, lựa chọn đặc trưng 2D/3D và đơn vị dày CLIQUE đều chỉ khớp trên ≤ 2023, "
                    "đánh giá độc lập trên holdout 2024 và kiểm định ngoài khử hiệu ứng năm."
                )
                spar = hd_sum.loc[hd_sum["section"] == "sparsity_ladder"].copy()
                if not spar.empty:
                    fig_spar = go.Figure()
                    for grid_lbl, grp in spar.groupby(spar["method"].str.extract(r"\((.*)\)$")[0]):
                        sub_s = grp.loc[~grp["verdict"].str.contains("Bùng nổ", na=False)].sort_values("dims_d")
                        if sub_s.empty:
                            continue
                        fig_spar.add_trace(
                            go.Scatter(
                                x=sub_s["dims_d"],
                                y=100.0 * sub_s["noise_ratio"],
                                mode="lines+markers",
                                name=str(grid_lbl),
                            )
                        )
                    fig_spar.update_layout(
                        title="Lời nguyền số chiều: Tỷ lệ nhiễu (%) khi tăng số chiều d trên 8 tiểu chỉ tiêu",
                        xaxis_title="Số chiều d",
                        yaxis_title="Tỷ lệ nhiễu (%)",
                        height=300,
                        margin={"t": 45, "r": 20, "b": 35, "l": 50},
                    )
                    st.plotly_chart(fig_spar, width="stretch")

                comp_hd = hd_sum.loc[
                    hd_sum["section"].isin(
                        ["baseline_robustness", "feature_selection", "subspace_clique", "adaptive_quantile", "pca_followup"]
                    )
                ].copy()
                comp_hd["Nhiễu (%)"] = (100.0 * comp_hd["noise_ratio"]).round(1)
                comp_hd["Phủ 2024 (%)"] = comp_hd["holdout_2024_cov"].map(
                    lambda v: "—" if pd.isna(v) else f"{100.0 * float(v):.1f}%"
                )
                comp_hd["Silhouette"] = comp_hd["silhouette_orig"].map(
                    lambda v: "—" if pd.isna(v) else f"{float(v):.3f}"
                )
                comp_hd["p PCI (khử năm)"] = comp_hd["ext_pci_dm_p"].map(
                    lambda v: "—" if pd.isna(v) else f"{float(v):.4g}"
                )
                disp_hd = comp_hd[
                    [
                        "section",
                        "method",
                        "dims_d",
                        "n_clusters",
                        "Nhiễu (%)",
                        "Silhouette",
                        "Phủ 2024 (%)",
                        "p PCI (khử năm)",
                        "verdict",
                    ]
                ].rename(
                    columns={
                        "section": "Nhánh",
                        "method": "Phương pháp / Cấu hình",
                        "dims_d": "d",
                        "n_clusters": "k",
                        "verdict": "Kết luận",
                    }
                )
                st.markdown(disp_hd.to_markdown(index=False))

                hd_sub = high_dim["subspaces"]
                top_clq = (
                    hd_sub.loc[(hd_sub["kind"] == "clique_subspace") & (hd_sub["n_clusters"] >= 2)]
                    .sort_values(["k_dim", "silhouette_orig"], ascending=[False, False])
                    .head(6)
                    .copy()
                )
                if not top_clq.empty:
                    st.markdown("**Top không gian con đa cụm (Subspace CLIQUE Apriori)**")
                    top_clq["Phủ train (%)"] = (100.0 * top_clq["coverage_train"]).round(1)
                    top_clq["Phủ 2024 (%)"] = top_clq["holdout_2024_cov"].map(
                        lambda v: "—" if pd.isna(v) else f"{100.0 * float(v):.1f}%"
                    )
                    top_clq["Silhouette"] = top_clq["silhouette_orig"].map(
                        lambda v: "—" if pd.isna(v) else f"{float(v):.3f}"
                    )
                    disp_clq = top_clq[
                        [
                            "dataset",
                            "adaptive",
                            "k_dim",
                            "features",
                            "Phủ train (%)",
                            "Silhouette",
                            "Phủ 2024 (%)",
                            "cluster_sizes",
                        ]
                    ].rename(
                        columns={
                            "dataset": "Tập dữ liệu",
                            "adaptive": "Quantile",
                            "k_dim": "d",
                            "features": "Không gian con",
                            "cluster_sizes": "Kích thước cụm",
                        }
                    )
                    st.markdown(disp_clq.to_markdown(index=False))

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
            st.info("Phần STING và Tổng quan vẫn dùng được. Chạy lại `python scripts/supervised/predict_supervised.py`, rồi làm mới ứng dụng.")
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

                deep_reg = get_regression_deep_assets(artifact_identity(_REGRESSION_DEEP_FILES))
                if deep_reg is not None:
                    deep_sum = deep_reg["summary"]
                    conf_2024 = deep_reg["conformal"]
                    with st.expander(
                        "Phân tích hồi quy chuyên sâu: Đa mô hình, AR(1) vs Δy, Hệ số β/VIF & Conformal 90%",
                        expanded=False,
                    ):
                        st.caption(
                            "Chạy đồng nhất trên 740 cặp train 2011–2022 (6 fold expanding origin 2017–2022); "
                            "holdout 59 tỉnh (2023→2024) và bán kính Conformal KHÔNG tham gia hiệu chỉnh trước."
                        )
                        model_rows = deep_sum.loc[deep_sum["section"].str.startswith("model_")].copy()
                        model_rows = model_rows.loc[model_rows["item"] != "Trung bình tập huấn luyện"].sort_values(
                            "metric_primary", ascending=True
                        )
                        fig_cv = go.Figure(
                            go.Bar(
                                x=model_rows["metric_primary"],
                                y=model_rows["item"],
                                orientation="h",
                                marker_color=[
                                    "#009E73" if "Sai phân" in m or "ElasticNet" in m else (
                                        "#2563eb" if "Ridge (8" in m else (
                                            "#94a3b8" if "carry-forward" in m else "#d97706"
                                        )
                                    )
                                    for m in model_rows["item"]
                                ],
                                text=[f"{v:.3f}" for v in model_rows["metric_primary"]],
                                textposition="outside",
                            )
                        )
                        fig_cv.update_layout(
                            template="plotly_white",
                            height=430,
                            title="So sánh R² CV (2017–2022) giữa 16 cấu hình hồi quy & cơ chế",
                            xaxis_title="R² CV (expanding origin 2017–2022)",
                            yaxis_title="",
                            margin={"t": 42, "r": 45, "b": 30, "l": 10},
                        )
                        st.plotly_chart(fig_cv, width="stretch")

                        conf_view = conf_2024.loc[
                            conf_2024["province_code"].isin(regression_view["province_code"])
                        ].sort_values("pred_ridge")
                        if not conf_view.empty:
                            fig_conf = go.Figure()
                            fig_conf.add_trace(
                                go.Scatter(
                                    x=conf_view["province_vi"],
                                    y=conf_view["pred_ridge"],
                                    mode="lines+markers",
                                    name="Dự báo Ridge ± Conformal 90%",
                                    line={"color": "#2563eb"},
                                    error_y={
                                        "type": "data",
                                        "symmetric": False,
                                        "array": (conf_view["conformal_hi90"] - conf_view["pred_ridge"]).tolist(),
                                        "arrayminus": (conf_view["pred_ridge"] - conf_view["conformal_lo90"]).tolist(),
                                        "color": "#93c5fd",
                                        "thickness": 1.6,
                                    },
                                )
                            )
                            fig_conf.add_trace(
                                go.Scatter(
                                    x=conf_view["province_vi"],
                                    y=conf_view["actual_2024"],
                                    mode="markers",
                                    name="Thực tế 2024",
                                    marker={"color": "#059669", "size": 7},
                                )
                            )
                            fig_conf.update_layout(
                                template="plotly_white",
                                height=380,
                                title="Khoảng dự báo Conformal 90% (CV 2017–2022) so với thực tế 2024",
                                xaxis_title="Tỉnh sắp theo dự báo Ridge",
                                yaxis_title="Điểm 6.1 (2024)",
                                margin={"t": 42, "r": 20, "b": 40, "l": 20},
                            )
                            st.plotly_chart(fig_conf, width="stretch")

                        coef_tbl = deep_sum.loc[deep_sum["section"] == "coef_and_vif", [
                            "item", "metric_primary", "metric_secondary", "holdout_mae", "holdout_rmse", "holdout_r2"
                        ]].rename(columns={
                            "item": "Chỉ tiêu",
                            "metric_primary": "β Ridge",
                            "metric_secondary": "β ElasticNet",
                            "holdout_mae": "β Lasso",
                            "holdout_rmse": "β OLS",
                            "holdout_r2": "VIF",
                        })
                        test_tbl = deep_sum.loc[deep_sum["section"] == "paired_test", [
                            "item", "metric_primary", "metric_secondary", "holdout_r2", "note"
                        ]].rename(columns={
                            "item": "Kiểm định cặp",
                            "metric_primary": "ΔMAE",
                            "metric_secondary": "Wilcoxon p",
                            "holdout_r2": "Tỷ lệ cải thiện",
                            "note": "CI 95% & số cặp",
                        })
                        conf_tbl = deep_sum.loc[deep_sum["section"] == "conformal", [
                            "item", "metric_primary", "metric_secondary", "holdout_mae", "note"
                        ]].rename(columns={
                            "item": "Khoảng dự báo",
                            "metric_primary": "Phủ thực tế 2024",
                            "metric_secondary": "Bán kính (±)",
                            "holdout_mae": "Độ rộng TB",
                            "note": "Chi tiết hiệu chỉnh",
                        })
                        st.markdown("**1. Hệ số hồi quy chuẩn hóa (Z-score train) & VIF**")
                        st.markdown(coef_tbl.to_markdown(index=False))
                        st.markdown("**2. Kiểm định cặp Wilcoxon & Bootstrap CI 95% trên ΔMAE**")
                        st.markdown(test_tbl.to_markdown(index=False))
                        st.markdown("**3. Hiệu chỉnh Conformal & Quantile Regression (<=2022 → holdout 2024)**")
                        st.markdown(conf_tbl.to_markdown(index=False))

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
                "Chạy lại `python scripts/analysis/external_validation.py`, rồi làm mới ứng dụng."
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

            palette = cluster_palette(pci_counts["clusters"])
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
                    color_discrete_map=cluster_palette(grdp.pred_cluster),
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

                poverty_palette = cluster_palette(poverty_counts["clusters"])
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
                    f"(tạo lại bằng `python scripts/data/build_poverty_63.py`), nhãn cụm "
                    f"`results/predict_all_years.csv`; màu cụm theo `scripts/common/fig_style.py`. "
                    f"Thiếu phía nguồn — KHÔNG nội suy: {missing_source_txt}. "
                    f"{len(poverty_counts['no_label_cells'])} ô có poverty nhưng KHÔNG có nhãn cụm "
                    f"(mask tường minh, không vẽ không test): {no_label_txt}. Ngoài cửa sổ: năm "
                    f"poverty-only {poverty_counts['pov_only_years']} (không có nhãn cụm) và năm "
                    f"{poverty_counts['label_only_years']} (bảng pxweb V14.47 không có cột poverty)."
                )

            panel_inf_df = get_panel_inference_assets(
                artifact_identity(_PANEL_INFERENCE_FILES)
            )
            if panel_inf_df is not None and not panel_inf_df.empty:
                with st.expander(
                    "Suy luận bảng chuẩn hóa năm (Year-FE CR1 / TWFE), Kiểm soát FDR 383 không gian con & Moran's I",
                    expanded=False,
                ):
                    st.caption(
                        "Xử lý phụ thuộc quan sát lặp theo 63 tỉnh và xu hướng vĩ mô theo năm qua phép chiếu FWL + "
                        "sai số chuẩn Liang–Zeger CR1, Wild Cluster Bootstrap (B=1.999) và hiệu chỉnh đa kiểm định Holm/BH/BY."
                    )
                    prim_inf = panel_inf_df.loc[panel_inf_df["section"] == "primary_panel"].copy()
                    if not prim_inf.empty:
                        disp_inf = prim_inf[[
                            "branch", "outcome", "n_obs", "g_provinces", "naive_mwu_raw_p",
                            "beta_yrfe", "se_cr1_yrfe", "p_cr1_yrfe", "p_wcr_yrfe", "p_cr1_twfe", "holm_p_family", "holm_p_global", "verdict"
                        ]].copy()
                        disp_inf.columns = [
                            "Nhánh", "Biến ngoài", "n", "G tỉnh", "p gộp thô",
                            "β Year-FE", "SE CR1", "p CR1", "p WCR", "p TWFE", "Holm nhánh", "Holm 6 phép", "Kết luận suy luận"
                        ]
                        st.dataframe(
                            disp_inf,
                            hide_index=True,
                            width="stretch",
                            column_config={
                                "n": st.column_config.NumberColumn("n", format="%d"),
                                "G tỉnh": st.column_config.NumberColumn("G tỉnh", format="%d"),
                                "β Year-FE": st.column_config.NumberColumn("β Year-FE", format="%.3f"),
                                "SE CR1": st.column_config.NumberColumn("SE CR1", format="%.3f"),
                                "p gộp thô": st.column_config.NumberColumn("p gộp thô", format="%.4g"),
                                "p CR1": st.column_config.NumberColumn("p CR1", format="%.4f"),
                                "p WCR": st.column_config.NumberColumn("p WCR", format="%.4f"),
                                "p TWFE": st.column_config.NumberColumn("p TWFE", format="%.4f"),
                                "Holm nhánh": st.column_config.NumberColumn("Holm nhánh", format="%.4f"),
                                "Holm 6 phép": st.column_config.NumberColumn("Holm 6 phép", format="%.4f"),
                            },
                        )
                    fdr_inf = panel_inf_df.loc[panel_inf_df["section"] == "subspace_fdr"]
                    spat_inf = panel_inf_df.loc[panel_inf_df["section"] == "spatial_residual"]
                    if not fdr_inf.empty:
                        fdr_pci = fdr_inf.loc[fdr_inf["hypothesis_id"] == "subspace_pci"]
                        if not fdr_pci.empty:
                            st.info(
                                f"**Sàng lọc thăm dò FDR (PCI, KW xếp chồng):** {fdr_pci.iloc[0]['verdict']} "
                                f"(`{fdr_pci.iloc[0]['overlap_window']}`)."
                            )
                    if not spat_inf.empty:
                        st.markdown("**Chẩn đoán tự tương quan không gian phần dư Holdout 2024 (Moran's I, 1.999 hoán vị)**")
                        st.dataframe(
                            spat_inf[["outcome", "n_obs", "beta_yrfe", "p_cr1_yrfe", "verdict"]].rename(
                                columns={
                                    "outcome": "Chuỗi năm 2024",
                                    "n_obs": "n",
                                    "beta_yrfe": "Moran's I",
                                    "p_cr1_yrfe": "p hoán vị",
                                    "verdict": "Kết luận không gian",
                                }
                            ),
                            hide_index=True,
                            width="stretch",
                            column_config={
                                "n": st.column_config.NumberColumn("n", format="%d"),
                                "Moran's I": st.column_config.NumberColumn("Moran's I", format="%+.4f"),
                                "p hoán vị": st.column_config.NumberColumn("p hoán vị", format="%.4f"),
                            },
                        )

            st.caption(
                "Nguồn local: `data/processed/external_pci_63_full.csv` (PCI VCCI–USAID — provenance "
                "`data/processed/external_provenance.md`, `data/raw/*/PROVENANCE.md`) và "
                "`results/external_validation.csv`; tạo lại bằng `python scripts/analysis/external_validation.py`."
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

with client_tab:
    if client_tab.open:
        st.subheader("Thống kê bàn giao cho khách hàng · 63 tỉnh (năm 2024)")
        st.caption(
            "Bốn nhóm mô tả vị trí của điểm PAPI 2024 trên lưới dựng từ dữ liệu đến 2023, "
            "kèm gợi ý đối chiếu tại địa phương. Tab này cố định ở năm 2024; bộ lọc năm và cụm "
            "ở thanh bên không thay đổi bảng này."
        )
        try:
            stakeholder = load_stakeholder_summary()
        except DashboardDataError as exc:
            st.error(str(exc))
        else:
            s_df = customer_display_frame(stakeholder["summary"])
            g_df = customer_display_frame(stakeholder["group_stats"])
            bench = stakeholder["bench"]
            watchlist = stakeholder["watchlist"]
            benchmarks_14y = stakeholder["benchmarks_14y"]

            counts_map = dict(zip(g_df["action_group"], g_df["n_provinces"]))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(
                "Trong vùng dày (Cụm 2)",
                f"{counts_map.get('Trong vùng dày (Cụm 2)', 0)} / {len(s_df)}",
                help=f"{len(benchmarks_14y)} tỉnh giữ nhãn Cụm 2 trong 14/14 năm; điều này không chứng minh điểm số ổn định.",
            )
            c2.metric(
                "Ngoài vùng dày phía điểm cao",
                f"{counts_map.get('Ngoài vùng dày phía điểm cao', 0)}",
                help="Ô thưa có 4.2 từ trung vị vùng dày trở lên và 6.1 từ mốc rà soát trở lên; không phải chuẩn quốc gia.",
            )
            c3.metric(
                "Ngoài vùng dày, 6.1 thấp",
                f"{counts_map.get('Ngoài vùng dày, 6.1 thấp', 0)}",
                help=f"Ô thưa có 6.1 < Q25 − 0.5×IQR ({bench['lower_61_fence']:.3f}).",
            )
            c4.metric(
                "Thiếu dữ liệu 2024",
                f"{counts_map.get('Thiếu dữ liệu 2024', 0)}",
            )

            st.info(
                f"Vùng dày là các ô có ít nhất {config['sting']['min_count']} quan sát tham chiếu, "
                "không phải vùng địa lý hay mức chất lượng. Nhãn −1 có cả điểm cao và điểm thấp. "
                f"Mốc rà soát 6.1 = {bench['lower_61_fence']:.4f} tính hồi cứu từ {int(bench['n_core'])} "
                "tỉnh trong vùng dày năm 2024, chưa được kiểm chứng độc lập. "
                "Tỉ lệ kịch bản ngoài vùng dùng để đọc thứ hạng thăm dò, không phải xác suất dự báo."
            )
            st.markdown("#### Tổng hợp 4 nhóm mô tả trên 63 tỉnh năm 2024")
            g_display = g_df[
                [
                    "action_group",
                    "n_provinces",
                    "share_63_pct",
                    "median_sd_4_2",
                    "median_sd_6_1",
                    "median_years_c2",
                    "median_risk_outside_pct",
                    "median_grdp_2024_mil",
                    "median_pci_2022",
                ]
            ].copy()
            for col_name, fmt in (
                ("share_63_pct", "{:.1f}"),
                ("median_sd_4_2", "{:.3f}"),
                ("median_sd_6_1", "{:.3f}"),
                ("median_years_c2", "{:.1f}"),
                ("median_risk_outside_pct", "{:.1f}"),
                ("median_grdp_2024_mil", "{:.2f}"),
                ("median_pci_2022", "{:.2f}"),
            ):
                g_display[col_name] = pd.to_numeric(g_display[col_name], errors="coerce").map(
                    lambda v, _fmt=fmt: _fmt.format(v) if pd.notna(v) else "—"
                )
            st.dataframe(
                g_display,
                hide_index=True,
                width="stretch",
                column_config={
                    "action_group": st.column_config.TextColumn("Nhóm mô tả", width=205),
                    "n_provinces": st.column_config.NumberColumn("Tỉnh", width=55),
                    "share_63_pct": st.column_config.TextColumn("Tỉ lệ (%)", width=80, alignment="right"),
                    "median_sd_4_2": st.column_config.TextColumn("Med 4.2", width=78, alignment="right"),
                    "median_sd_6_1": st.column_config.TextColumn("Med 6.1", width=78, alignment="right"),
                    "median_years_c2": st.column_config.TextColumn("Năm C2", width=78, alignment="right"),
                    "median_risk_outside_pct": st.column_config.TextColumn(
                        "Kịch bản ngoài vùng (%)", width=165, alignment="right"
                    ),
                    "median_grdp_2024_mil": st.column_config.TextColumn(
                        "GRDP 24", width=92, alignment="right"
                    ),
                    "median_pci_2022": st.column_config.TextColumn("PCI 22", width=78, alignment="right"),
                },
            )

            ctrl_col1, ctrl_col2 = st.columns([2.4, 1.0], vertical_alignment="bottom")
            with ctrl_col1:
                selected_action_groups = st.multiselect(
                    "Lọc theo nhóm mô tả",
                    options=g_df["action_group"].tolist(),
                    default=[],
                    placeholder="Tất cả nhóm mô tả…",
                    key="client_action_groups",
                    help="Lọc biểu đồ, danh sách và tệp tải theo một hoặc nhiều nhóm mô tả.",
                )

            filtered_s = s_df
            if selected_provinces:
                filtered_s = filtered_s.loc[filtered_s["province_code"].isin(selected_provinces)]
            if selected_action_groups:
                filtered_s = filtered_s.loc[filtered_s["action_group"].isin(selected_action_groups)]

            export_cols = [
                "province_code",
                "province_vi",
                "action_group",
                "action_subtier",
                "sd_4_2",
                "sd_6_1",
                "grid_cell",
                "reference_count",
                "years_cluster2_2011_2024",
                "years_noise_2011_2024",
                "transition_2023_2024",
                "risk_outside_scenario_share",
                "grdp_2024_mil_vnd",
                "pci_2022",
                "poverty_2024_pct",
                "client_recommendation",
            ]
            csv_bytes = filtered_s[export_cols].to_csv(index=False).encode("utf-8-sig")
            with ctrl_col2:
                st.download_button(
                    f"Tải CSV bàn giao ({len(filtered_s)} tỉnh)",
                    data=csv_bytes,
                    file_name="sting_papi_ban_giao_2024.csv",
                    mime="text/csv",
                    width="stretch",
                    key="client_download_csv",
                )

            if selected_provinces or selected_action_groups:
                st.caption(
                    f"Các thẻ và bảng nhóm phía trên phản ánh toàn bộ {len(s_df)} tỉnh; "
                    f"biểu đồ và bảng chi tiết bên dưới đang lọc còn {len(filtered_s)} tỉnh."
                )

            chart_mode = st.radio(
                "Chế độ trực quan 63 tỉnh",
                options=["Bản đồ Việt Nam 63 tỉnh", "Biểu đồ phân tán 2D (4.2 × 6.1)"],
                horizontal=True,
                key="client_chart_mode",
            )

            plot_df = filtered_s.loc[filtered_s["grid_status"].ne("missing_score")]
            if filtered_s.empty:
                render_empty("Không có tỉnh nào khớp bộ lọc tỉnh và nhóm mô tả đang chọn.")
            else:
                if plot_df.empty:
                    st.info(
                        "Các tỉnh đang lọc thuộc nhóm **Thiếu dữ liệu 2024** (chưa có đủ chỉ tiêu 4.2 và 6.1 "
                        "để vẽ lên bản đồ 2D); xem khuyến nghị kiểm toán mẫu ở bảng bên dưới."
                    )

                rendered_map = False
                if chart_mode == "Bản đồ Việt Nam 63 tỉnh":
                    try:
                        geojson = get_vietnam_geojson(artifact_identity(_GEOJSON_FILES))
                        hi_codes = (
                            set(filtered_s["province_code"].dropna().astype(int))
                            if (selected_provinces or selected_action_groups)
                            else None
                        )
                        fig_map = build_action_choropleth_figure(
                            s_df, geojson, highlight_codes=hi_codes
                        )
                    except Exception:
                        st.warning("Không nạp được bản đồ ranh giới tỉnh; chuyển sang biểu đồ 2D.")
                    else:
                        st.plotly_chart(fig_map, width="stretch")
                        rendered_map = True

                if not rendered_map and not plot_df.empty:
                    fig_client = px.scatter(
                        plot_df,
                        x="sd_4_2",
                        y="sd_6_1",
                        color="action_group",
                        color_discrete_map=CUSTOMER_GROUP_COLORS,
                        hover_name="province_vi",
                        hover_data={
                            "action_subtier": True,
                            "years_cluster2_2011_2024": True,
                            "grdp_2024_mil_vnd": ":.2f",
                            "risk_outside_scenario_share": ":.1%",
                        },
                        labels={
                            "sd_4_2": "4.2 Kiểm soát tham nhũng (2024)",
                            "sd_6_1": "6.1 Y tế công lập (2024)",
                            "action_group": "Nhóm mô tả",
                        },
                        title="Nhóm mô tả theo hai chỉ tiêu PAPI năm 2024",
                    )
                    fig_client.add_vline(x=bench["med_42"], line_dash="dash", line_color="#009E73")
                    fig_client.add_hline(y=bench["lower_61_fence"], line_dash="dot", line_color="#D55E00")
                    fig_client.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
                    st.plotly_chart(fig_client, width="stretch")

            st.markdown("#### Danh sách theo tỉnh và gợi ý rà soát")
            detail_view_mode = st.radio(
                "Chế độ hiển thị bảng chi tiết",
                options=[
                    "Phân nhóm & chỉ số chính",
                    "Khuyến nghị & dịch chuyển",
                    "Đầy đủ 10 cột",
                ],
                horizontal=True,
                key="client_detail_view_mode",
                help=(
                    "Hai chế độ đầu chia bảng theo nhóm chỉ số hoặc khuyến nghị để dễ đọc hết chữ; "
                    "chế độ thứ ba gộp đủ 10 cột kèm ghim tên tỉnh."
                ),
            )
            if not filtered_s.empty:
                detail_base = filtered_s[
                    [
                        "province_vi",
                        "action_group",
                        "action_subtier",
                        "sd_4_2",
                        "sd_6_1",
                        "years_cluster2_2011_2024",
                        "transition_2023_2024",
                        "risk_outside_scenario_share",
                        "grdp_2024_mil_vnd",
                        "pci_2022",
                        "poverty_2024_pct",
                        "client_recommendation",
                    ]
                ].copy()
                for score_col in ("sd_4_2", "sd_6_1"):
                    detail_base[score_col] = pd.to_numeric(
                        detail_base[score_col], errors="coerce"
                    ).map(lambda v: f"{v:.3f}" if pd.notna(v) else "—")
                detail_base["years_cluster2_2011_2024"] = pd.to_numeric(
                    detail_base["years_cluster2_2011_2024"], errors="coerce"
                ).map(lambda v: f"{int(round(v))}" if pd.notna(v) else "—")
                detail_base["risk_outside_scenario_share"] = pd.to_numeric(
                    detail_base["risk_outside_scenario_share"], errors="coerce"
                ).map(lambda v: f"{100.0 * v:.1f}%" if pd.notna(v) else "—")
                detail_base["grdp_2024_mil_vnd"] = pd.to_numeric(
                    detail_base["grdp_2024_mil_vnd"], errors="coerce"
                ).map(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
                detail_base["pci_2022"] = pd.to_numeric(
                    detail_base["pci_2022"], errors="coerce"
                ).map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
                detail_base["poverty_2024_pct"] = pd.to_numeric(
                    detail_base["poverty_2024_pct"], errors="coerce"
                ).map(lambda v: f"{v:.1f}%" if pd.notna(v) else "—")
                for text_col in ("action_subtier", "transition_2023_2024", "client_recommendation"):
                    detail_base[text_col] = detail_base[text_col].map(
                        lambda v: str(v).strip() if pd.notna(v) and str(v).strip() else "—"
                    )

                if detail_view_mode == "Phân nhóm & chỉ số chính":
                    view_cols = [
                        "province_vi",
                        "action_group",
                        "action_subtier",
                        "sd_4_2",
                        "sd_6_1",
                        "years_cluster2_2011_2024",
                        "risk_outside_scenario_share",
                        "grdp_2024_mil_vnd",
                    ]
                    col_cfg = {
                        "province_vi": st.column_config.TextColumn("Tỉnh / TP", width=130),
                        "action_group": st.column_config.TextColumn("Nhóm mô tả", width=205),
                        "action_subtier": st.column_config.TextColumn("Phân tầng", width=270),
                        "sd_4_2": st.column_config.TextColumn("4.2", width=64, alignment="right"),
                        "sd_6_1": st.column_config.TextColumn("6.1", width=64, alignment="right"),
                        "years_cluster2_2011_2024": st.column_config.TextColumn(
                            "Năm C2", width=72, alignment="right"
                        ),
                        "risk_outside_scenario_share": st.column_config.TextColumn(
                            "Kịch bản 2024", width=92, alignment="right"
                        ),
                        "grdp_2024_mil_vnd": st.column_config.TextColumn(
                            "GRDP 24 (tr.đ)", width=112, alignment="right"
                        ),
                    }
                elif detail_view_mode == "Khuyến nghị & dịch chuyển":
                    view_cols = [
                        "province_vi",
                        "transition_2023_2024",
                        "pci_2022",
                        "poverty_2024_pct",
                        "client_recommendation",
                    ]
                    col_cfg = {
                        "province_vi": st.column_config.TextColumn("Tỉnh / TP", width=130),
                        "transition_2023_2024": st.column_config.TextColumn(
                            "Dịch chuyển 23→24", width=190
                        ),
                        "pci_2022": st.column_config.TextColumn("PCI 22", width=65, alignment="right"),
                        "poverty_2024_pct": st.column_config.TextColumn(
                            "Nghèo 24", width=83, alignment="right"
                        ),
                        "client_recommendation": st.column_config.TextColumn(
                            "Khuyến nghị bàn giao", width=510
                        ),
                    }
                else:
                    view_cols = [
                        "province_vi",
                        "action_group",
                        "action_subtier",
                        "sd_4_2",
                        "sd_6_1",
                        "years_cluster2_2011_2024",
                        "transition_2023_2024",
                        "risk_outside_scenario_share",
                        "grdp_2024_mil_vnd",
                        "client_recommendation",
                    ]
                    col_cfg = {
                        "province_vi": st.column_config.TextColumn(
                            "Tỉnh / TP", width=135, pinned=True
                        ),
                        "action_group": st.column_config.TextColumn("Nhóm mô tả", width=205),
                        "action_subtier": st.column_config.TextColumn("Phân tầng", width=270),
                        "sd_4_2": st.column_config.TextColumn(
                            "4.2 (2024)", width=74, alignment="right"
                        ),
                        "sd_6_1": st.column_config.TextColumn(
                            "6.1 (2024)", width=74, alignment="right"
                        ),
                        "years_cluster2_2011_2024": st.column_config.TextColumn(
                            "Năm C2", width=72, alignment="right"
                        ),
                        "transition_2023_2024": st.column_config.TextColumn("Dịch chuyển", width=195),
                        "risk_outside_scenario_share": st.column_config.TextColumn(
                            "Kịch bản 2024", width=92, alignment="right"
                        ),
                        "grdp_2024_mil_vnd": st.column_config.TextColumn(
                            "GRDP 24 (tr.đ)", width=112, alignment="right"
                        ),
                        "client_recommendation": st.column_config.TextColumn(
                            "Khuyến nghị bàn giao", width=510
                        ),
                    }

                st.dataframe(
                    detail_base[view_cols],
                    hide_index=True,
                    width="stretch",
                    column_config=col_cfg,
                )
            st.caption(
                f"{len(benchmarks_14y)} tỉnh giữ nhãn Cụm 2 trong 14/14 năm: "
                f"{', '.join(benchmarks_14y['province_vi'].tolist())}. "
                f"Top 3 tỉ lệ kịch bản ngoài vùng (hồi kiểm 2023→2024): "
                + ", ".join(
                    f"{r['province_vi']} ({100.0 * r['risk_outside_scenario_share']:.1f}%)"
                    if pd.notna(r["risk_outside_scenario_share"])
                    else f"{r['province_vi']} (—)"
                    for _, r in watchlist.head(3).iterrows()
                )
                + ". Giữ nhãn không chứng minh điểm số ổn định. Tỉ lệ kịch bản không phải xác suất dự báo."
            )

            if not filtered_s.empty:
                st.markdown("#### Phiếu rà soát tỉnh (in PDF và bàn giao)")
                scorecard_pool = filtered_s
                pool_names = scorecard_pool["province_vi"].tolist()
                default_idx = (
                    pool_names.index("Hà Nội")
                    if (not (selected_provinces or selected_action_groups) and "Hà Nội" in pool_names)
                    else 0
                )
                sc_col1, sc_col2 = st.columns([2.0, 1.2], vertical_alignment="bottom")
                with sc_col1:
                    selected_scorecard_prov = st.selectbox(
                        "Chọn tỉnh để xuất phiếu rà soát khổ A4",
                        options=pool_names,
                        index=default_idx,
                        key="client_scorecard_province",
                    )
                sc_rows = s_df.loc[s_df["province_vi"].eq(selected_scorecard_prov)]
                if sc_rows.empty:
                    st.warning("Không tìm thấy dữ liệu tỉnh để tạo phiếu rà soát tỉnh.")
                else:
                    sc_row = sc_rows.iloc[0]
                    sc_code = int(sc_row["province_code"])
                    sc_html = build_province_scorecard_html(
                        sc_code, s_df, assignments, bench, benchmarks_14y
                    )
                    with sc_col2:
                        st.download_button(
                            f"Tải Phiếu rà soát tỉnh ({selected_scorecard_prov} · HTML)",
                            data=sc_html.encode("utf-8"),
                            file_name=scorecard_filename(selected_scorecard_prov),
                            mime="text/html",
                            width="stretch",
                            key="client_download_scorecard",
                        )
                    sc_42 = f"{float(sc_row['sd_4_2']):.3f}" if pd.notna(sc_row["sd_4_2"]) else "—"
                    sc_61 = f"{float(sc_row['sd_6_1']):.3f}" if pd.notna(sc_row["sd_6_1"]) else "—"
                    st.caption(
                        f"**{selected_scorecard_prov}** · {sc_row['action_group']} ({sc_row['action_subtier']}) · "
                        f"4.2 = {sc_42}, 6.1 = {sc_61}. Khuyến nghị: {sc_row['client_recommendation']} "
                        "Mở tệp HTML đã tải bằng trình duyệt rồi nhấn Ctrl+P → Save as PDF để in trang A4."
                    )

st.divider()
st.caption(
    "Nguồn local: `data/processed/papi_panel_63_2011_2024.csv`, "
    "`results/predict_all_years.csv`, `results/supervised_metrics.csv` và model trong `models/`."
)
