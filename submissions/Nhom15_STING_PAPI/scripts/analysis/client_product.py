"""Công cụ bàn giao trực quan cho khách hàng: bản đồ Choropleth 63 tỉnh & Phiếu chẩn đoán 1 trang.

Module dùng thuần thư viện chuẩn Python + pandas + plotly (không phụ thuộc shapely hay map tile ngoài),
tương thích 100% với gói nộp độc lập `submissions/Nhom15_STING_PAPI.zip`.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from scripts.analysis.stakeholder_summary import ACTION_GROUP_COLORS, ACTION_GROUP_ORDER

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GEOJSON_PATH = ROOT / "data" / "raw" / "boundaries" / "diaphantinh.geojson"

GEOJSON_PROVINCE_ALIAS: dict[str, str] = {
    "Bà Rịa -Vũng Tàu": "Bà Rịa - Vũng Tàu",
    "Cần Thơn": "Cần Thơ",
    "Quản Bình": "Quảng Bình",
    "Kien Giang": "Kiên Giang",
    "Đăk Lăk": "Đắk Lắk",
    "Đăk Nông": "Đắk Nông",
}

_CLUSTER_LABELS = {
    -1: "Ô thưa (−1)",
    0: "Cụm 0",
    1: "Cụm 1",
    2: "Cụm 2 (Vùng lõi)",
}


def _round_point(pt: list[float] | tuple[float, ...], coord_decimals: int) -> list[float]:
    return [round(float(pt[0]), coord_decimals), round(float(pt[1]), coord_decimals)]


def _simplify_ring(ring: list, simplify_step: int, coord_decimals: int) -> list[list[float]]:
    if not ring:
        return []
    rounded = [_round_point(pt, coord_decimals) for pt in ring]
    deduped = [pt for idx, pt in enumerate(rounded) if idx == 0 or pt != rounded[idx - 1]]
    if len(deduped) > 1 and deduped[0] == deduped[-1]:
        body = deduped[:-1]
    else:
        body = deduped
    if len(body) < 3:
        return rounded

    if simplify_step > 1:
        sampled = body[::simplify_step]
        if len(sampled) < 3:
            sampled = body[:3]
    else:
        sampled = body
    return [*sampled, list(sampled[0])]


def _simplify_geometry(geom: dict, simplify_step: int, coord_decimals: int) -> dict:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if gtype == "Polygon" and isinstance(coords, list):
        return {
            "type": "Polygon",
            "coordinates": [_simplify_ring(ring, simplify_step, coord_decimals) for ring in coords],
        }
    if gtype == "MultiPolygon" and isinstance(coords, list):
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [_simplify_ring(ring, simplify_step, coord_decimals) for ring in poly]
                for poly in coords
            ],
        }
    return geom


def load_vietnam_geojson(
    path: Path = DEFAULT_GEOJSON_PATH,
    *,
    simplify_step: int = 3,
    coord_decimals: int = 3,
) -> dict:
    """Đọc GeoJSON 63 tỉnh Việt Nam, chuẩn hóa `province_vi` và đơn giản hóa đỉnh đa giác."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    features = raw.get("features")
    if not isinstance(features, list) or len(features) != 63:
        n_feat = len(features) if isinstance(features, list) else 0
        raise ValueError(f"GeoJSON phải có đúng 63 tỉnh/thành, nhận được {n_feat}.")

    normalized_features: list[dict] = []
    for feat in features:
        if not isinstance(feat, dict):
            raise ValueError("GeoJSON feature không hợp lệ.")
        props = dict(feat.get("properties") or {})
        raw_name = str(props.get("ten_tinh", "")).strip()
        props["province_vi"] = GEOJSON_PROVINCE_ALIAS.get(raw_name, raw_name)
        raw_geom = feat.get("geometry")
        if not isinstance(raw_geom, dict) or not raw_geom.get("type"):
            raise ValueError(f"Thiếu geometry hợp lệ cho tỉnh {raw_name or '<unknown>'}.")
        geom = _simplify_geometry(raw_geom, simplify_step, coord_decimals)
        normalized_features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": geom,
            }
        )
    return {
        "type": "FeatureCollection",
        "features": normalized_features,
    }


def _is_missing_scalar(value: object) -> bool:
    if value is None or isinstance(value, (list, tuple, set, dict)):
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def _fmt_num(value: object, fmt: str, suffix: str = "") -> str:
    if _is_missing_scalar(value):
        return "—"
    try:
        return f"{format(float(value), fmt)}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(value: object, digits: int = 1) -> str:
    if _is_missing_scalar(value):
        return "—"
    try:
        return f"{100.0 * float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_int(value: object) -> str:
    if _is_missing_scalar(value):
        return "—"
    try:
        return str(int(round(float(value))))
    except (TypeError, ValueError):
        return "—"


def _fmt_str(value: object) -> str:
    if _is_missing_scalar(value):
        return "—"
    s = str(value).strip()
    return s if s else "—"


def build_action_choropleth_figure(
    summary_df: pd.DataFrame,
    geojson: dict,
    *,
    highlight_codes: set[int] | None = None,
) -> go.Figure:
    """Tạo bản đồ Choropleth offline 63 tỉnh tô màu theo 4 nhóm hành động STING."""
    geo_names = {
        str((feat.get("properties") or {}).get("province_vi", "")).strip()
        for feat in geojson.get("features", [])
        if isinstance(feat, dict)
    }
    df_names = {str(v).strip() for v in summary_df["province_vi"].dropna()}
    missing_geo = sorted(df_names - geo_names)
    if missing_geo:
        raise ValueError(f"GeoJSON thiếu hoặc lệch tên tỉnh: {missing_geo}")

    df = summary_df.copy()
    df["province_txt"] = df["province_vi"].map(lambda v: html.escape(_fmt_str(v), quote=True))
    df["group_txt"] = df["action_group"].map(lambda v: html.escape(_fmt_str(v), quote=True))
    df["sd_4_2_txt"] = df["sd_4_2"].map(lambda v: _fmt_num(v, ".3f"))
    df["sd_6_1_txt"] = df["sd_6_1"].map(lambda v: _fmt_num(v, ".3f"))
    df["risk_txt"] = df["risk_outside_scenario_share"].map(lambda v: _fmt_pct(v, 1))
    df["grdp_txt"] = df["grdp_2024_mil_vnd"].map(lambda v: _fmt_num(v, ".1f", " tr.đ"))
    df["years_c2_txt"] = df["years_cluster2_2011_2024"].map(_fmt_int)
    df["transition_txt"] = df["transition_2023_2024"].map(
        lambda v: html.escape(_fmt_str(v), quote=True)
    )
    df["subtier_txt"] = df["action_subtier"].map(lambda v: html.escape(_fmt_str(v), quote=True))

    present_groups = [g for g in ACTION_GROUP_ORDER if g in set(df["action_group"].dropna())]
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="province_vi",
        featureidkey="properties.province_vi",
        color="action_group",
        category_orders={"action_group": present_groups or ACTION_GROUP_ORDER},
        color_discrete_map=ACTION_GROUP_COLORS,
        custom_data=[
            "province_txt",
            "group_txt",
            "subtier_txt",
            "sd_4_2_txt",
            "sd_6_1_txt",
            "years_c2_txt",
            "risk_txt",
            "grdp_txt",
            "transition_txt",
        ],
        labels={"action_group": "Nhóm hành động"},
        title="Bản đồ phân nhóm hành động 63 tỉnh năm 2024 (tách 2 cực trong nhãn −1)",
    )

    hover_tpl = (
        "<b>%{customdata[0]}</b><br>"
        "Nhóm: %{customdata[1]}<br>"
        "Phân tầng: %{customdata[2]}<br>"
        "4.2 Tham nhũng: %{customdata[3]} · 6.1 Y tế: %{customdata[4]}<br>"
        "Số năm Cụm 2: %{customdata[5]}/14 · Kịch bản ngoài vùng 2024: %{customdata[6]}<br>"
        "GRDP 24: %{customdata[7]} · Dịch chuyển: %{customdata[8]}"
        "<extra></extra>"
    )

    code_by_name = {
        str(r["province_vi"]): int(r["province_code"])
        for _, r in df.iterrows()
        if pd.notna(r["province_code"])
    }

    if highlight_codes is not None:
        hi_set = {int(c) for c in highlight_codes}
        for trace in fig.data:
            raw_locs = getattr(trace, "locations", None)
            locs = [] if raw_locs is None else list(raw_locs)
            selected = [idx for idx, loc in enumerate(locs) if code_by_name.get(str(loc)) in hi_set]
            trace.update(
                selectedpoints=selected,
                selected={"marker": {"opacity": 0.96}},
                unselected={"marker": {"opacity": 0.22}},
                marker_line_color="#0F2B46",
                marker_line_width=1.0,
                hovertemplate=hover_tpl,
            )
    else:
        fig.update_traces(
            marker_opacity=0.92,
            marker_line_color="#FFFFFF",
            marker_line_width=0.75,
            hovertemplate=hover_tpl,
        )

    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(
        height=520,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        geo_bgcolor="rgba(0,0,0,0)",
        legend={"title_text": "Nhóm hành động", "orientation": "h", "y": -0.02, "x": 0.0},
    )
    return fig


def scorecard_filename(province_vi: str) -> str:
    """Tạo tên tệp ASCII an toàn từ tên tỉnh tiếng Việt."""
    text = str(province_vi).replace("Đ", "D").replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only).strip("_") or "tinh"
    return f"phieu_chan_doan_{slug}_2024.html"


def _format_cluster_label(cluster_val: object) -> str:
    if cluster_val is None or pd.isna(cluster_val):
        return "—"
    code = int(round(float(cluster_val)))
    return _CLUSTER_LABELS.get(code, f"Cụm {code}")


def build_province_scorecard_html(
    province_code: int,
    summary_df: pd.DataFrame,
    all_years_df: pd.DataFrame,
    bench: dict[str, float],
    benchmarks_14y: pd.DataFrame,
) -> str:
    """Xuất Phiếu chẩn đoán 1 trang tự chứa (HTML5 + CSS in A4) cho một tỉnh."""
    matches = summary_df.loc[summary_df["province_code"].eq(int(province_code))]
    if matches.empty:
        raise ValueError(f"Không tìm thấy tỉnh có mã {province_code} trong bảng tổng hợp.")
    row = matches.iloc[0]

    prov_name = _fmt_str(row["province_vi"])
    action_group = _fmt_str(row["action_group"])
    action_subtier = _fmt_str(row["action_subtier"])
    grid_cell = _fmt_str(row["grid_cell"])
    transition = _fmt_str(row["transition_2023_2024"])
    recommendation = _fmt_str(row["client_recommendation"])
    badge_color = ACTION_GROUP_COLORS.get(action_group, "#1B6E77")

    sd42_str = _fmt_num(row["sd_4_2"], ".3f")
    sd61_str = _fmt_num(row["sd_6_1"], ".3f")
    delta42_str = _fmt_num(row["delta_vs_core_med_4_2"], "+.3f")
    delta61_str = _fmt_num(row["delta_vs_core_med_6_1"], "+.3f")
    years_c2_str = f"{_fmt_int(row['years_cluster2_2011_2024'])} / 14"
    years_scored_str = f"{_fmt_int(row['years_scored_2011_2024'])} / 14 năm có điểm"
    risk_str = _fmt_pct(row["risk_outside_scenario_share"], 1)

    grdp_str = _fmt_num(row["grdp_2024_mil_vnd"], ".2f", " tr.đ")
    pci_str = _fmt_num(row["pci_2022"], ".2f")
    poverty_str = _fmt_num(row["poverty_2024_pct"], ".1f", "%")
    pop_str = _fmt_num(row["pop_2024_thousand"], ",.1f", " nghìn")

    bench_list = ", ".join(str(x) for x in benchmarks_14y["province_vi"].tolist()) or "—"

    traj = all_years_df.loc[all_years_df["province_code"].eq(int(province_code))].sort_values("year")
    traj_rows_html: list[str] = []
    for _, tr in traj.iterrows():
        yr = _fmt_int(tr["year"])
        v42 = _fmt_num(tr["sd_4_2"], ".3f")
        v61 = _fmt_num(tr["sd_6_1"], ".3f")
        lbl = _format_cluster_label(tr["pred_cluster"])
        traj_rows_html.append(
            "<tr>"
            f"<td>{html.escape(yr, quote=True)}</td>"
            f"<td class='num'>{html.escape(v42, quote=True)}</td>"
            f"<td class='num'>{html.escape(v61, quote=True)}</td>"
            f"<td>{html.escape(lbl, quote=True)}</td>"
            "</tr>"
        )
    if not traj_rows_html:
        traj_rows_html.append("<tr><td colspan='4'>Chưa có dữ liệu quỹ đạo 2011–2024.</td></tr>")

    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Phiếu chẩn đoán STING × PAPI 2024 — {e(prov_name)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 20px;
      font-family: "Segoe UI", Arial, sans-serif;
      color: #172033;
      background: #f4f6f9;
      line-height: 1.45;
    }}
    .sheet {{
      max-width: 920px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d8dfe6;
      border-radius: 10px;
      padding: 22px 26px;
    }}
    .header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      border-bottom: 2px solid #0f2b46;
      padding-bottom: 12px;
      margin-bottom: 16px;
    }}
    .kicker {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #1b6e77;
    }}
    h1 {{
      margin: 4px 0 4px;
      font-size: 24px;
      color: #0f2b46;
    }}
    .meta {{
      font-size: 13px;
      color: #4b5563;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 12px;
      border-radius: 999px;
      color: #ffffff;
      font-weight: 700;
      font-size: 13px;
      background: {e(badge_color)};
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .kpi {{
      border: 1px solid #d8dfe6;
      border-top: 3px solid #1b6e77;
      border-radius: 8px;
      padding: 10px 12px;
      background: #f9fbfd;
    }}
    .kpi-label {{
      font-size: 11.5px;
      color: #536179;
      font-weight: 600;
    }}
    .kpi-val {{
      font-size: 20px;
      font-weight: 700;
      color: #0f2b46;
      margin: 3px 0 2px;
    }}
    .kpi-sub {{
      font-size: 11.5px;
      color: #64748b;
    }}
    .box {{
      border: 1px solid #d8dfe6;
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 12px;
    }}
    .box-rec {{
      background: #ecf5f6;
      border-left: 4px solid #1b6e77;
    }}
    .box-title {{
      font-size: 12.5px;
      font-weight: 700;
      text-transform: uppercase;
      color: #0f2b46;
      margin-bottom: 5px;
    }}
    .socio-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 6px;
    }}
    .socio-item strong {{
      display: block;
      font-size: 15px;
      color: #0f2b46;
    }}
    .socio-item span {{
      font-size: 11.5px;
      color: #536179;
    }}
    .note {{
      font-size: 11.5px;
      color: #64748b;
      margin-top: 6px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
      margin-top: 6px;
    }}
    th, td {{
      border: 1px solid #d8dfe6;
      padding: 5px 8px;
      text-align: left;
    }}
    th {{
      background: #0f2b46;
      color: #ffffff;
      font-weight: 600;
    }}
    tr:nth-child(even) td {{
      background: #f8fafc;
    }}
    td.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .footer {{
      margin-top: 12px;
      font-size: 11px;
      color: #64748b;
      display: flex;
      justify-content: space-between;
    }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .sheet {{ border: none; border-radius: 0; padding: 10px 12px; max-width: none; }}
    }}
    @media (max-width: 720px) {{
      .kpi-grid, .socio-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main class="sheet">
    <header class="header">
      <div>
        <div class="kicker">Phiếu chẩn đoán bàn giao khách hàng · STING × PAPI 2024</div>
        <h1>{e(prov_name)} <span style="font-size:15px;font-weight:500;color:#64748b;">(Mã tỉnh: {e(int(province_code))})</span></h1>
        <div class="meta">Phân tầng: <strong>{e(action_subtier)}</strong> · Ô lưới 2024: <code>{e(grid_cell)}</code> · Dịch chuyển 2023→2024: <strong>{e(transition)}</strong></div>
      </div>
      <div>
        <span class="badge">{e(action_group)}</span>
      </div>
    </header>

    <section class="kpi-grid">
      <div class="kpi">
        <div class="kpi-label">4.2 Kiểm soát tham nhũng (2024)</div>
        <div class="kpi-val">{e(sd42_str)}</div>
        <div class="kpi-sub">So với trung vị lõi: {e(delta42_str)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">6.1 Y tế công lập (2024)</div>
        <div class="kpi-val">{e(sd61_str)}</div>
        <div class="kpi-sub">So với trung vị lõi: {e(delta61_str)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Số năm Cụm 2 (2011–2024)</div>
        <div class="kpi-val">{e(years_c2_str)}</div>
        <div class="kpi-sub">{e(years_scored_str)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Kịch bản ngoài vùng 2024</div>
        <div class="kpi-val">{e(risk_str)}</div>
        <div class="kpi-sub">Hồi kiểm 2023→2024; không phải xác suất</div>
      </div>
    </section>

    <section class="box box-rec">
      <div class="box-title">Khuyến nghị hành động bàn giao</div>
      <div>{e(recommendation)}</div>
    </section>

    <section class="box">
      <div class="box-title">Đối sánh mốc chuẩn Cụm 2 năm 2024 (n = {e(int(bench['n_core']))} tỉnh vùng lõi)</div>
      <div style="font-size:13px;">
        Trung vị lõi: <strong>4.2 = {e(f"{bench['med_42']:.3f}")}</strong> ·
        <strong>6.1 = {e(f"{bench['med_61']:.3f}")}</strong> ·
        Ngưỡng rìa dưới 6.1 (Q25 − 0,5×IQR) = <strong>{e(f"{bench['lower_61_fence']:.3f}")}</strong>.
      </div>
      <div class="note">5 tỉnh chuẩn tham chiếu bền vững 14/14 năm Cụm 2: {e(bench_list)}.</div>
    </section>

    <section class="box">
      <div class="box-title">Bối cảnh kinh tế – xã hội độc lập</div>
      <div class="socio-grid">
        <div class="socio-item"><span>GRDP / người 2024 (Sơ bộ)</span><strong>{e(grdp_str)}</strong></div>
        <div class="socio-item"><span>PCI 2022 (VCCI–USAID)</span><strong>{e(pci_str)}</strong></div>
        <div class="socio-item"><span>Tỉ lệ nghèo GSO 2024</span><strong>{e(poverty_str)}</strong></div>
        <div class="socio-item"><span>Dân số GSO 2024</span><strong>{e(pop_str)}</strong></div>
      </div>
      <div class="note">Chỉ mô tả bối cảnh kinh tế–xã hội độc lập, không suy diễn nhân quả.</div>
    </section>

    <section class="box">
      <div class="box-title">Quỹ đạo PAPI & nhãn STING giai đoạn 2011–2024</div>
      <table>
        <thead>
          <tr><th>Năm</th><th class="num">4.2 Tham nhũng</th><th class="num">6.1 Y tế công lập</th><th>Nhãn lưới STING</th></tr>
        </thead>
        <tbody>
          {"".join(traj_rows_html)}
        </tbody>
      </table>
    </section>

    <footer class="footer">
      <span>Nhóm 15 · Chủ đề 6 · STING × PAPI (2011–2024)</span>
      <span>Nguồn: results/stakeholder_province_summary_2024.csv &amp; results/predict_all_years.csv</span>
    </footer>
  </main>
</body>
</html>
"""
