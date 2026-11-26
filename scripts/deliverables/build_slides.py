"""Build slides/Nhom15_STING_PAPI.pptx — bộ slide bảo vệ cuối kỳ thống nhất 11 trang 16:9, tiếng Việt.

Hợp nhất mạch trình bày giữa kỳ (cơ chế STING 3×3, dữ liệu giả lập, z-score & đối chứng)
với kết quả cuối kỳ (lưới cố định 2011–2023, thống kê bàn giao 63 tỉnh cho khách hàng,
dự báo thăm dò, kiểm chứng ngoại lai, độ bền đa chiều & đề xuất cải thiện).

Cách dùng:
    python scripts/deliverables/build_slides.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

import matplotlib
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from scripts.analysis.stakeholder_summary import build_stakeholder_tables  # noqa: E402
from scripts.common.midterm_clustering import (  # noqa: E402
    DBSCAN_OPTIONS,
    KMEANS_OPTIONS,
    sting_steps_figure,
)
from scripts.common.papi_pred_common import (  # noqa: E402
    describe_grid_assignment,
    load_config,
    load_panel,
)
from sting import STING  # noqa: E402

FIGS = ROOT / "results" / "figs"
OUT = ROOT / "slides" / "Nhom15_STING_PAPI.pptx"
SLIDE_COUNT = 11
REFERENCE_YEAR = 2023


def _read_results_csv(name: str) -> list[dict[str, str]]:
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pct(v: str | float) -> str:
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


def _dec(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _dot_thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


PAPI_CONFIG = load_config()
FEATURES, GRID_PARAMS = PAPI_CONFIG["features"], PAPI_CONFIG["sting"]
LEVEL = GRID_PARAMS["cluster_level"]
CONNECTIVITY = GRID_PARAMS["connectivity"]
MIN_COUNT = GRID_PARAMS["min_count"]
SIDE = GRID_PARAMS["factor"] ** LEVEL
PANEL = load_panel()
REFERENCE_SCORES = PANEL.loc[PANEL.year.le(REFERENCE_YEAR), FEATURES].dropna()
SCALER = StandardScaler().fit(REFERENCE_SCORES)
REFERENCE_Z = SCALER.transform(REFERENCE_SCORES)
GRID = STING(n_levels=GRID_PARAMS["n_levels"], factor=GRID_PARAMS["factor"], min_count=MIN_COUNT).fit(REFERENCE_Z)
REFERENCE_LABELS = GRID.cluster(level=LEVEL, connectivity=CONNECTIVITY)
GRID_RESULTS = describe_grid_assignment(PANEL, FEATURES, SCALER, GRID)
COMPLETE_GRID = GRID_RESULTS.dropna(subset=["cluster"]).copy()
COMPLETE_GRID["cluster_str"] = COMPLETE_GRID["cluster"].astype(int).astype(str)

# Thống kê mẫu đầy đủ 869 quan sát (2011–2024) cho mạch so sánh bất biến z-score
ALL_SCORES = PANEL[FEATURES].dropna()
ALL_XRAW = ALL_SCORES.to_numpy(dtype=float)
ALL_Z = StandardScaler().fit_transform(ALL_XRAW)
FULL_GRID = STING(n_levels=GRID_PARAMS["n_levels"], factor=GRID_PARAMS["factor"], min_count=MIN_COUNT).fit(ALL_Z)
FULL_LABELS = FULL_GRID.cluster(level=LEVEL, connectivity=CONNECTIVITY)
FULL_RAW_GRID = STING(n_levels=GRID_PARAMS["n_levels"], factor=GRID_PARAMS["factor"], min_count=MIN_COUNT).fit(ALL_XRAW)
FULL_RAW_LABELS = FULL_RAW_GRID.cluster(level=LEVEL, connectivity=CONNECTIVITY)
FULL_SAME_CELLS = int((FULL_RAW_GRID.point_cell_index(LEVEL) == FULL_GRID.point_cell_index(LEVEL)).all(axis=1).sum())
KM2_RAW = KMeans(n_clusters=2, **KMEANS_OPTIONS).fit_predict(ALL_XRAW)
KM2_Z = KMeans(n_clusters=2, **KMEANS_OPTIONS).fit_predict(ALL_Z)
KM2_ALIGN = KM2_Z if int((KM2_RAW == KM2_Z).sum()) >= len(KM2_Z) // 2 else 1 - KM2_Z
KM2_CHANGED = int((KM2_RAW != KM2_ALIGN).sum())

REFERENCE_ROWS = COMPLETE_GRID.loc[COMPLETE_GRID.year.le(REFERENCE_YEAR)]
PROFILES: dict[str, list] = defaultdict(list)
for row in REFERENCE_ROWS.itertuples(index=False):
    PROFILES[row.cluster_str].append(row)
MAIN_CLUSTER = max((label for label in PROFILES if label != "-1"), key=lambda label: len(PROFILES[label]))
MAIN_SIZE = len(PROFILES[MAIN_CLUSTER])
REFERENCE_NOISE = len(PROFILES["-1"])
CLUSTERED = len(REFERENCE_ROWS) - REFERENCE_NOISE
YEAR_COUNTS: dict[int, Counter[str]] = defaultdict(Counter)
for row in COMPLETE_GRID.itertuples(index=False):
    YEAR_COUNTS[int(row.year)][row.cluster_str] += 1
LABELS_2023 = {
    int(r.province_code): r.cluster_str
    for r in COMPLETE_GRID.loc[COMPLETE_GRID.year.eq(2023)].itertuples(index=False)
}
LABELS_2024 = {
    int(r.province_code): r.cluster_str
    for r in COMPLETE_GRID.loc[COMPLETE_GRID.year.eq(2024)].itertuples(index=False)
}
TRANSITIONS = Counter((LABELS_2023[p], LABELS_2024[p]) for p in LABELS_2023.keys() & LABELS_2024.keys())
assert all({left, right} <= {MAIN_CLUSTER, "-1"} for left, right in TRANSITIONS)
MISSING_2024 = GRID_RESULTS.loc[
    GRID_RESULTS.year.eq(2024) & GRID_RESULTS.grid_status.eq("missing_score"), "province_vi"
].tolist()
ACTIVE_2024_CELLS = int(
    COMPLETE_GRID.loc[COMPLETE_GRID.year.eq(2024) & COMPLETE_GRID.cluster_str.eq(MAIN_CLUSTER), "grid_cell"].nunique()
)

FORECAST = json.loads((ROOT / "results" / "papi_forecast_2024.json").read_text(encoding="utf-8"))
SCORES = {(row["target"], row["method"]): row for row in FORECAST["scores"]}
ZONES = {row["method"]: row for row in FORECAST["grid"]}
N_COMPARED = FORECAST["comparable_count"]
N_OUTSIDE = FORECAST["actual_outside"]

STAKE = build_stakeholder_tables(ROOT)
STAKE_GROUPS = STAKE["group_stats"].set_index("action_group")
STAKE_BENCH = STAKE["bench"]
STAKE_14Y = STAKE["benchmarks_14y"]
STAKE_WATCH = STAKE["watchlist"]
STAKE_TRANS = dict(zip(STAKE["transitions"]["transition_2023_2024"], STAKE["transitions"]["n_provinces"]))

AUDIT = _read_results_csv("preprocessing_audit.csv")
ROBUSTNESS = _read_results_csv("robustness.csv")
EXT_VAL = _read_results_csv("external_validation.csv")
POV_VAL = _read_results_csv("poverty_validation.csv")


def _audit_row(stage_sub: str, test_sub: str) -> dict[str, str]:
    hits = [r for r in AUDIT if stage_sub in r["stage"] and test_sub in r["test"]]
    if len(hits) != 1:
        raise KeyError(f"{stage_sub} / {test_sub}: {len(hits)} dòng")
    return hits[0]


def _nums(pattern: str, raw_text: str) -> tuple[int, ...]:
    match = re.search(pattern, raw_text)
    if match is None:
        raise ValueError(f"không khớp {pattern!r} trong: {raw_text}")
    return tuple(int(group) for group in match.groups())


_DUP_ROW = _audit_row("(a) trùng khóa", "dedup")
_MISS_ROW = _audit_row("(b) giá trị thiếu", "Ô thiếu trong 37 cột")
_OUT_ROW = _audit_row("(d) ngoại lai", "z-score")

N_DUP, N_ROWS = _nums(r"(\d+) dòng trùng / (\d+) dòng", _DUP_ROW["result"])
N_MISS, N_CELLS = _nums(r"(\d+)/(\d+) ô", _MISS_ROW["result"])
(N_OUT,) = _nums(r"^(\d+) ô", _OUT_ROW["result"])
(Z_OUT,) = _nums(r"z-score > (\d+)", _OUT_ROW["test"])


def _comparison_on_shared_points() -> tuple[list[tuple[str, int, str, str]], int]:
    kmeans = KMeans(n_clusters=2, **KMEANS_OPTIONS).fit_predict(REFERENCE_Z)
    dbscan = DBSCAN(**DBSCAN_OPTIONS).fit_predict(REFERENCE_Z)
    shared = (REFERENCE_LABELS >= 0) & (dbscan >= 0)
    rows = [
        (
            method,
            len(set(labels[labels >= 0])),
            _dec(100 * (labels == -1).mean(), 1) + "%",
            _dec(silhouette_score(REFERENCE_Z[shared], labels[shared]), 3),
        )
        for method, labels in (
            ("STING", REFERENCE_LABELS),
            ("K-means (k = 2)", kmeans),
            ("DBSCAN (ε = 0,2)", dbscan),
        )
    ]
    return rows, int(shared.sum())


# --- Bảng màu & hằng số bố cục ---
NAVY = RGBColor(0x0F, 0x2B, 0x46)
NAVY_MID = RGBColor(0x1E, 0x3D, 0x5E)
TEAL = RGBColor(0x1B, 0x6E, 0x77)
GOLD = RGBColor(0xE2, 0xB0, 0x4A)
GOLD_DEEP = RGBColor(0xA6, 0x76, 0x16)
GREEN = RGBColor(0x00, 0x7A, 0x5E)
BLUE = RGBColor(0x00, 0x66, 0x99)
CORAL = RGBColor(0xC8, 0x52, 0x00)
INK = RGBColor(0x1A, 0x1F, 0x24)
GREY = RGBColor(0x5A, 0x64, 0x70)
LIGHT = RGBColor(0xF6, 0xF5, 0xF1)
BORDER = RGBColor(0xD8, 0xDF, 0xE6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT_TEAL = RGBColor(0xEC, 0xF5, 0xF6)
SOFT_CORAL = RGBColor(0xFD, 0xF3, 0xEC)
SOFT_BLUE = RGBColor(0xEE, 0xF5, 0xFB)
SOFT_GOLD = RGBColor(0xFB, 0xF6, 0xE9)
SOFT_GREEN = RGBColor(0xEC, 0xF7, 0xF3)

SW, SH = 13.333, 7.5
prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


def slide_new():
    return prs.slides.add_slide(BLANK)


def rect(slide, x, y, w, h, fill, line=None, line_pt=0.75):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_pt)
    shp.shadow.inherit = False
    return shp


def card(slide, x, y, w, h, fill=LIGHT, border=BORDER, accent=None, accent_side="top", accent_thick=0.055):
    """Vẽ thẻ nội dung phẳng viền mảnh kèm thanh nhấn màu ở cạnh trên hoặc trái."""
    box = rect(slide, x, y, w, h, fill, line=border, line_pt=0.75)
    if accent is not None:
        if accent_side == "top":
            rect(slide, x, y, w, accent_thick, accent)
        elif accent_side == "left":
            rect(slide, x, y, accent_thick, h, accent)
    return box


def kpi_card(slide, x, y, w, h, value, label, sub="", accent=TEAL, fill=WHITE):
    """Vẽ thẻ chỉ số KPI gọn có số liệu nổi bật và nhãn phụ."""
    card(slide, x, y, w, h, fill=fill, border=BORDER, accent=accent, accent_side="top", accent_thick=0.055)
    runs = [
        (value, 18.5, True, accent),
        (label, 11.2, True, NAVY),
    ]
    if sub:
        runs.append((sub, 9.8, False, GREY))
    tb = slide.shapes.add_textbox(Inches(x + 0.14), Inches(y + 0.10), Inches(w - 0.28), Inches(h - 0.14))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, (t, size, bold, color) in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(1.5 if i < len(runs) - 1 else 0)
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = "Calibri"
    return tb


def text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, space_after=4, margin=0.04):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(margin * 0.5)
    for i, (t, size, bold, color) in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = "Calibri"
    return tb


def header(slide, kicker, title, page_no, source="Topic 6 · STING × PAPI 2011–2024 · Nhóm 15"):
    rect(slide, 0, 0, SW, 0.14, TEAL)
    rect(slide, 0.55, 0.26, 0.08, 0.80, GOLD)
    text(slide, 0.72, 0.24, 11.8, 0.26, [(kicker, 11, True, TEAL)], space_after=0, margin=0.01)
    text(slide, 0.72, 0.49, 12.0, 0.62, [(title, 23.5, True, NAVY)], space_after=0, margin=0.01)
    rect(slide, 0.55, SH - 0.42, SW - 1.1, 0.012, BORDER)
    text(slide, 0.55, SH - 0.37, 9.8, 0.28, [(source, 9.8, False, GREY)], space_after=0, margin=0.01)
    badge = rect(slide, SW - 1.38, SH - 0.36, 0.83, 0.24, SOFT_TEAL, line=BORDER, line_pt=0.5)
    tf = badge.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = f"{page_no:02d} / {SLIDE_COUNT}"
    r.font.size = Pt(9.5)
    r.font.bold = True
    r.font.color.rgb = NAVY
    r.font.name = "Calibri"


def note(slide, text_md: str):
    slide.notes_slide.notes_text_frame.text = text_md


def bullets(slide, x, y, w, h, items, size=13, color=INK, gap_pt=6, bold_first=True,
            lead_color=TEAL, align=PP_ALIGN.LEFT, hang_in=0.20):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.03)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, (lead, rest) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(gap_pt)
        if align == PP_ALIGN.LEFT and hang_in > 0:
            pPr = p._p.get_or_add_pPr()
            emu = str(int(Inches(hang_in)))
            pPr.set("marL", emu)
            pPr.set("indent", "-" + emu)
        if lead:
            r1 = p.add_run()
            r1.text = "▸  " + lead + " "
            r1.font.bold = bold_first
            r1.font.size = Pt(size)
            r1.font.color.rgb = lead_color
            r1.font.name = "Calibri"
        r2 = p.add_run()
        r2.text = rest
        r2.font.size = Pt(size)
        r2.font.color.rgb = color
        r2.font.name = "Calibri"
    return tb


def pic_fit(slide, source: Path | BytesIO, x, y, max_w, max_h):
    """Chèn ảnh vừa khít khung (max_w, max_h) theo đúng tỉ lệ gốc và căn giữa."""
    if isinstance(source, Path):
        assert source.exists(), f"missing {source}"
        raw_bytes = source.read_bytes()
    else:
        source.seek(0)
        raw_bytes = source.read()

    with Image.open(BytesIO(raw_bytes)) as img:
        iw, ih = img.size

    scale = min(max_w / iw, max_h / ih)
    w_in = iw * scale
    h_in = ih * scale
    px = x + (max_w - w_in) / 2
    py = y + (max_h - h_in) / 2
    slide.shapes.add_picture(BytesIO(raw_bytes), Inches(px), Inches(py), width=Inches(w_in), height=Inches(h_in))


def pic(slide, filename: str, x, y, max_w, max_h):
    return pic_fit(slide, FIGS / filename, x, y, max_w, max_h)


def result_table(slide, rows, x, y, widths, row_height, size, left_cols=(0,), header_fill=TEAL):
    table = slide.shapes.add_table(
        len(rows), len(widths), Inches(x), Inches(y), Inches(sum(widths)), Inches(len(rows) * row_height)
    ).table
    for col, width in zip(table.columns, widths):
        col.width = Inches(width)
    for i, row in enumerate(rows):
        table.rows[i].height = Inches(row_height)
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text_frame.word_wrap = True
            cell.text_frame.text = str(value)
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.LEFT if j in left_cols else PP_ALIGN.CENTER
            font = paragraph.runs[0].font
            font.size, font.name, font.bold = Pt(size), "Calibri", i == 0
            font.color.rgb = WHITE if i == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if i == 0 else WHITE if i % 2 else LIGHT
    return table


# --- SLIDE 1: TITLE (BẢO VỆ ĐỒ ÁN CUỐI KỲ) ---
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, 0, SW, 0.08, TEAL)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
for r in range(4):
    for c in range(4):
        x0, y0 = SW - 4.45 + c * 0.80, 1.18 + r * 0.80
        if (r, c) in ((1, 1), (2, 2)):
            fill = GOLD
        elif (r, c) in ((1, 2), (2, 1)):
            fill = TEAL
        else:
            fill = NAVY_MID
        rect(s, x0, y0, 0.68, 0.68, fill)

text(s, 0.85, 0.95, 8.2, 0.36, [("HỌC MÁY · BẢO VỆ ĐỒ ÁN CUỐI KỲ (BẢN THỐNG NHẤT)", 14.5, True, GOLD)])
text(s, 0.85, 1.48, 8.2, 1.30, [("Phân cụm dựa trên lưới STING", 38, True, WHITE)])
text(s, 0.85, 2.86, 8.2, 0.85, [
    ("Đặc điểm, biến động PAPI 2011–2024 & Thống kê bàn giao 63 tỉnh", 19.5, False, RGBColor(0xE6, 0xEE, 0xF5)),
])

pills = [
    ("63 tỉnh × 14 năm (882×41)", 0.85, 2.55),
    ("STING tự cài đặt · ARI = 0,950", 3.55, 2.75),
    ("4 nhóm hành động bàn giao", 6.45, 2.40),
]
for label, px, pw in pills:
    rect(s, px, 4.02, pw, 0.42, NAVY_MID, line=RGBColor(0x36, 0x5C, 0x82), line_pt=0.75)
    text(s, px + 0.08, 4.08, pw - 0.16, 0.32, [(label, 12, True, GOLD)], align=PP_ALIGN.CENTER, space_after=0, margin=0.01)

rect(s, 0.85, 4.86, 8.0, 0.015, RGBColor(0x2D, 0x4F, 0x73))
text(s, 0.85, 5.05, 8.2, 1.30, [
    ("Nhóm 15 · Chủ đề 6 · Grid-based clustering (STING)", 15, True, GOLD),
    ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051) · GVHD: ThS. Lê Minh Tân", 14.2, False, RGBColor(0xC2, 0xD4, 0xE3)),
])
note(s, "Bản trình bày bảo vệ cuối kỳ thống nhất toàn đồ án (gộp phần cơ chế giữa kỳ, phân tích cuối kỳ, thống kê bàn giao 63 tỉnh và đề xuất cải thiện). "
     "Hồ sơ đồng bộ: Nhom15_BaoCao_STING_PAPI.docx, Nhom15_STING_PAPI.ipynb và Nhom15_TienXuLy_PAPI.ipynb.")


# --- SLIDE 2: BÀI TOÁN & TIỀN XỬ LÝ ---
s = slide_new()
header(s, "BÀI TOÁN & TIỀN XỬ LÝ", "Từ 14 workbook PAPI (882×41) đến lưới tham chiếu chống rò rỉ", 2,
       "src/preprocessing.py · Nhom15_TienXuLy_PAPI.ipynb")

kpi_card(s, 0.55, 1.24, 3.92, 0.88, f"{N_ROWS} × 41", "Panel PAPI 63 tỉnh × 14 năm", "39 cột chỉ tiêu số · hợp nhất 2011–2024", accent=TEAL)
kpi_card(s, 4.70, 1.24, 3.92, 0.88, f"{N_DUP} / {N_ROWS}", "Trùng khóa · Lệch Mendeley 0,0", f"Quy 0,0 → NaN ({_dot_thousands(N_MISS)} ô thiếu, không nội suy)", accent=BLUE)
kpi_card(s, 8.85, 1.24, 3.92, 0.88, f"{len(COMPLETE_GRID)} / {N_ROWS}", "Dòng đủ cả hai trục 4.2 & 6.1", f"{len(REFERENCE_ROWS)} train (≤2023) + {len(LABELS_2024)} quan sát (2024)", accent=GREEN)

card(s, 0.55, 2.28, 6.45, 2.86, fill=WHITE, border=BORDER, accent=TEAL, accent_side="left")
bullets(s, 0.72, 2.38, 6.15, 2.68, [
    ("Hai chỉ tiêu chốt sau audit.", "4.2 Kiểm soát tham nhũng dịch vụ công và 6.1 Y tế công lập đo vùng tập trung & dịch chuyển 63 tỉnh (2011–2024)."),
    ("Pipeline làm sạch 6 bước.", f"Dedup trước → quy 0,0 về NaN → giữ {N_OUT} cực trị |z| > {Z_OUT} để không làm co biên lưới STING."),
    ("Chống rò rỉ dữ liệu.", "Chỉ fit StandardScaler và lưới STING trên 2011–2023; năm 2024 dùng transform & predict độc lập."),
], size=13.8, gap_pt=9)

result_table(s, [
    ("Giai đoạn", "Số dòng", "StandardScaler & Lưới STING"),
    ("2011–2024 (mô tả)", len(COMPLETE_GRID), "Khảo sát toàn kỳ & bất biến z-score"),
    ("2011–2023 (huấn luyện)", len(REFERENCE_ROWS), "fit scaler & STING (chống rò rỉ)"),
    ("2024 (quan sát mới)", len(LABELS_2024), "transform & predict trên lưới 2011–2023"),
], 7.18, 2.28, [1.95, 0.98, 2.66], 0.715, 12.8)

card(s, 0.55, 5.30, 12.22, 1.50, fill=SOFT_TEAL, border=BORDER, accent=TEAL, accent_side="left")
text(s, 0.76, 5.40, 11.85, 1.32, [
    ("CHỐT CẤU HÌNH TRAIN-ONLY (≤ 2020 CHỌN, 2021–2022 CHẤM ĐỘ PHỦ) · MODELS/PREDICT_CONFIG.JSON", 12.5, True, TEAL),
    ("Audit thang đo: 23/37 cột có bước nhảy ≥ 0,25 điểm qua các năm → chỉ đưa 8 sub-dim đồng nhất vào allowlist khảo sát.", 13.8, False, INK),
    ("Đối chiếu Mendeley CC BY 4.0 (DOI 10.17632/wbk42j9wc8.1): độ lệch tuyệt đối tối đa = 0,0 trên toàn bộ 5.118 cặp giao.", 13.8, False, GREY),
], space_after=4)
note(s, "Slide 2 gộp bài toán và 6 bước PREPROCESSING_PIPELINE trong src/preprocessing.py. "
     "Xóa 7 cực trị trên tập train làm co biên lưới khiến nhiễu STING tăng từ 19,6% lên 24,6%, nên đồ án chỉ gắn cờ chứ không xóa.")


# --- SLIDE 3: CƠ CHẾ STING & KIỂM CHỨNG GIẢ LẬP ---
s = slide_new()
header(s, "CƠ CHẾ & KIỂM CHỨNG", "STING phân cấp lưới, ví dụ 3×3 và kiểm chứng giả lập (ARI = 0,950)", 3,
       "src/sting.py · tests/test_sting.py · Notebook §1")

card(s, 0.55, 1.24, 7.62, 2.86, fill=WHITE, border=BORDER)
card(s, 8.32, 1.24, 4.45, 2.86, fill=WHITE, border=BORDER)

step_fig = sting_steps_figure(figsize=(12.2, 3.60), dpi=200)
step_bio = BytesIO()
step_fig.savefig(step_bio, format="png", dpi=200, facecolor="white", bbox_inches="tight", pad_inches=0.06)
plt.close(step_fig)
step_bio.seek(0)
pic_fit(s, step_bio, 0.63, 1.30, 7.46, 2.74)
pic(s, "00_synthetic_sting.png", 8.40, 1.30, 4.30, 2.74)

card(s, 0.55, 4.24, 7.62, 2.58, fill=LIGHT, border=BORDER, accent=TEAL, accent_side="top")
bullets(s, 0.70, 4.36, 7.34, 2.38, [
    ("Chia ô & gán nhãn.", f"clip(floor((z − zmin) / Δ), 0, r − 1). PAPI dùng 3 tầng (1, 4, {SIDE}), giữ ô count ≥ {MIN_COUNT} tại mức 2 rồi nối DFS kề 4 hướng."),
    ("Ví dụ 3 × 3 (15 điểm).", "Ngưỡng ≥ 3 cho đúng 2 cụm 7 điểm và 1 nhiễu (−1); chạm góc tại (1, 1) không nối."),
    ("Khác biệt với STING gốc (VLDB 1997).", "STING gốc duyệt top-down theo phân phối chuẩn & tin cậy (hỗ trợ bởi query_top_down); biến thể gom cụm chọn ô dày tại một tầng xác định."),
], size=12.8, gap_pt=7)

card(s, 8.32, 4.24, 4.45, 2.58, fill=SOFT_BLUE, border=BORDER, accent=BLUE, accent_side="top")
bullets(s, 8.47, 4.36, 4.18, 2.38, [
    ("Dữ liệu giả lập 240 điểm.", "2 cụm Gauss (make_blobs, seed 42): khôi phục đủ 2 cụm, 2,5% nhiễu, ARI = 0,950."),
    ("Bảo toàn số đếm phân cấp.", "Tổng count ở mọi tầng cây phân cấp luôn bằng đúng 240 (khớp bất biến thống kê ô)."),
], size=13.0, gap_pt=10, lead_color=BLUE)
note(s, "Slide 3 trình bày cả cơ chế cài đặt từ đầu (lưới 3×3) lẫn kiểm chứng định lượng 240 điểm giả lập ARI=0,950.")


# --- SLIDE 4: KẾT QUẢ PAPI, ĐỐI CHỨNG & BẤT BIẾN Z-SCORE ---
s = slide_new()
header(s, "PHÂN CỤM PAPI & ĐỐI CHỨNG", "Một cụm lớn chiếm ưu thế, so sánh công bằng & vai trò z-score", 4,
       "Notebook §3 · results/predict_all_years.csv")
comparison_rows, n_shared = _comparison_on_shared_points()
result_table(s, [
    ("Phương pháp (2011–2023, n=808)", "Cụm", "Nhiễu", f"Silh. ({n_shared} giao)"),
    *comparison_rows,
], 0.55, 1.32, [2.70, 0.65, 1.05, 1.45], 0.59, 12.2)

result_table(s, [
    ("Cấu hình STING", "Ô dày", "Cụm", "Kích thước cụm", "Nhiễu"),
    ("Toàn kỳ (2011–2024, n=869)", len(FULL_GRID.label_of_), FULL_GRID.n_clusters_, "677 / 16 / 5", f"{int((FULL_LABELS == -1).sum())} ({_pct((FULL_LABELS == -1).mean()).replace('.', ',')})"),
    ("Lưới cố định (≤2023, n=808)", len(GRID.label_of_), GRID.n_clusters_, f"{MAIN_SIZE} / 16 / 5", f"{REFERENCE_NOISE} ({_pct(REFERENCE_NOISE / len(REFERENCE_ROWS)).replace('.', ',')})"),
], 6.58, 1.32, [2.25, 0.68, 0.60, 1.22, 1.44], 0.68, 12.0)

cards_s4 = [
    (
        "1. Phản biện nhãn nhiễu (−1)",
        "162/171 điểm −1 vẫn nằm trong khung |z| ≤ 3 — đây là ô thưa hợp lệ, không phải lỗi làm sạch.\nXóa 9 điểm |z| > 3 làm co biên lưới, khiến tỉ lệ nhiễu tăng từ 19,7% lên 20,1%.",
        CORAL, SOFT_CORAL,
    ),
    (
        "2. So sánh trên cùng tập giao",
        "Trên 680 điểm giao toàn kỳ (869): STING = 0,380, K-means k=2 = 0,461, DBSCAN = 0,274; trên 631 điểm giao (808): 0,366 vs 0,457 vs 0,258.\nCụm lớn STING bị K-means k=2 chẻ thành 482 + 195 điểm.",
        TEAL, SOFT_TEAL,
    ),
    (
        "3. Bất biến chuẩn hóa z-score",
        f"Dựng lại lưới đều giúp STING giữ nguyên {FULL_SAME_CELLS}/869 ô và nhãn.\nCùng k = 2, K-means đổi nhóm {KM2_CHANGED}/869 điểm (ARI = {_dec(adjusted_rand_score(KM2_RAW, KM2_Z), 4)}); DBSCAN đổi 8 điểm trạng thái nhiễu.",
        BLUE, SOFT_BLUE,
    ),
]
for idx, (ctitle, cbody, cacc, cfill) in enumerate(cards_s4):
    cx = 0.55 + idx * 4.14
    card(s, cx, 4.02, 3.94, 2.80, fill=cfill, border=BORDER, accent=cacc, accent_side="top")
    text(s, cx + 0.14, 4.14, 3.66, 2.58, [
        (ctitle, 13.8, True, cacc),
        (cbody, 12.6, False, INK),
    ], space_after=6)

note(s, "Slide 4 giải đáp trọn vẹn mọi câu hỏi phản biện thuật toán giữa kỳ + cuối kỳ: cấu trúc 1 cụm lớn, đối chứng silhouette cùng mẫu giao và lý do z-score không làm đổi ô STING.")


# --- SLIDE 5: GÁN NĂM 2024 & DỊCH CHUYỂN TRÊN LƯỚI CỐ ĐỊNH ---
s = slide_new()
header(s, "QUAN SÁT NĂM 2024", f"{YEAR_COUNTS[2024][MAIN_CLUSTER]}/{len(LABELS_2024)} tỉnh đủ điểm vào cụm lớn trên lưới 2011–2023", 5,
       "Notebook §4 · results/papi_observed_grid_2024.csv")
card(s, 0.52, 1.32, 7.30, 5.48, fill=WHITE, border=BORDER)
pic(s, "predict_2024.png", 0.58, 1.38, 7.18, 5.36)

result_table(s, [
    ("2023 → 2024 (n = 59)", "Cụm 2", "Ô thưa (−1)"),
    ("Cụm 2 (vùng dày)", TRANSITIONS[MAIN_CLUSTER, MAIN_CLUSTER], TRANSITIONS[MAIN_CLUSTER, "-1"]),
    ("Ô thưa (−1)", TRANSITIONS["-1", MAIN_CLUSTER], TRANSITIONS["-1", "-1"]),
], 8.00, 1.32, [2.35, 1.21, 1.21], 0.56, 13.0)

province = GRID_RESULTS.loc[GRID_RESULTS.province_vi.eq("Lạng Sơn") & GRID_RESULTS.year.isin([2023, 2024])].sort_values("year")
trace_rows = [("Lạng Sơn", "4.2 / 6.1", "Ô lưới", "Tham chiếu", "Nhãn")]
for obs, _z in zip(province.itertuples(index=False), SCALER.transform(province[FEATURES]), strict=True):
    raw = " / ".join(_dec(getattr(obs, f), 2) for f in FEATURES)
    lbl = "−1" if obs.cluster == -1 else f"Cụm {obs.cluster}"
    trace_rows.append((obs.year, raw, obs.grid_cell, obs.reference_count, lbl))
result_table(s, trace_rows, 8.00, 3.22, [0.90, 1.24, 1.03, 0.90, 0.70], 0.52, 12.0)

CELL_2023 = {
    int(r.province_code): r.grid_cell
    for r in COMPLETE_GRID.loc[COMPLETE_GRID.year.eq(2023)].itertuples(index=False)
}
CELL_2024 = {
    int(r.province_code): r.grid_cell
    for r in COMPLETE_GRID.loc[COMPLETE_GRID.year.eq(2024)].itertuples(index=False)
}
STAY_MAIN_COUNT = TRANSITIONS[MAIN_CLUSTER, MAIN_CLUSTER]
STAY_DIFF_CELL = sum(
    1 for p in LABELS_2023.keys() & LABELS_2024.keys()
    if LABELS_2023[p] == MAIN_CLUSTER and LABELS_2024[p] == MAIN_CLUSTER and CELL_2023.get(p) != CELL_2024.get(p)
)

card(s, 8.00, 4.96, 4.77, 1.84, fill=SOFT_TEAL, border=BORDER, accent=TEAL, accent_side="left")
bullets(s, 8.15, 5.05, 4.52, 1.68, [
    (f"Đủ điểm 2024 ({len(LABELS_2024)}/63).", f"{YEAR_COUNTS[2024][MAIN_CLUSTER]} tỉnh vào {ACTIVE_2024_CELLS} ô dày Cụm 2; {YEAR_COUNTS[2024]['-1']} tỉnh ở ô thưa (0–3 điểm tham chiếu, |z| ≤ 2,13); {' và '.join(MISSING_2024)} thiếu điểm."),
    ("Dịch chuyển.", f"{TRANSITIONS[MAIN_CLUSTER, '-1']} tỉnh sang ô thưa, {TRANSITIONS['-1', MAIN_CLUSTER]} tỉnh vào cụm lớn; {STAY_DIFF_CELL}/{STAY_MAIN_COUNT} tỉnh giữ cụm nhưng đổi ô."),
], size=12.4, gap_pt=6)
note(s, "Slide 5 chiếu 61 điểm 2024 lên lưới cố định 2011–2023 và truy vết ca Lạng Sơn dịch chuyển từ (13,9) [2 điểm] sang (12,10) [12 điểm].")


# --- SLIDE 6: THỐNG KÊ BÀN GIAO CHO KHÁCH HÀNG (1/2) ---
s = slide_new()
header(s, "THỐNG KÊ BÀN GIAO KHÁCH HÀNG (1/2)", "Biến mã kỹ thuật (−1, 2) thành 4 nhóm hành động trên 63 tỉnh năm 2024", 6,
       "scripts/analysis/stakeholder_summary.py · results/stakeholder_summary.md")

kpi_specs = [
    ("Biên bứt phá vượt chuẩn", "Biên bứt phá vượt chuẩn", "4.2 > med lõi · khảo sát nhân rộng", BLUE, SOFT_BLUE),
    ("Vùng lõi ổn định (Cụm 2)", "Vùng lõi ổn định (Cụm 2)", f"Gồm {len(STAKE_14Y)} tỉnh chuẩn 14/14 năm", GREEN, SOFT_GREEN),
    ("Ưu tiên cải thiện Y tế 6.1", "Ưu tiên cải thiện Y tế 6.1", f"6.1 < {_dec(STAKE_BENCH['lower_61_fence'], 3)} · quá tải đô thị", CORAL, SOFT_CORAL),
    ("Thiếu dữ liệu 2024", "Thiếu dữ liệu 2024", "Kiểm toán thu thập · không nội suy", GREY, LIGHT),
]
for idx, (grp_key, title_txt, sub_txt, acc_col, fill_col) in enumerate(kpi_specs):
    row_g = STAKE_GROUPS.loc[grp_key]
    n_prov = int(row_g["n_provinces"])
    share_str = _dec(float(row_g["share_63_pct"]), 1)
    kpi_card(
        s, 0.55 + idx * 3.11, 1.22, 2.91, 0.88,
        f"{n_prov} tỉnh ({share_str}%)", title_txt, sub_txt, accent=acc_col, fill=fill_col,
    )

# Cắt phần tiêu đề lặp trên cùng của ảnh stakeholder_quadrants_2024.png ngay trong bộ nhớ (không sửa file gốc)
with Image.open(FIGS / "stakeholder_quadrants_2024.png") as raw_img:
    w_px, h_px = raw_img.size
    cropped = raw_img.crop((0, int(h_px * 0.072), w_px, h_px))
    cropped_bio = BytesIO()
    cropped.save(cropped_bio, format="PNG")
    cropped_bio.seek(0)

card(s, 0.55, 2.20, 12.22, 4.66, fill=WHITE, border=BORDER)
pic_fit(s, cropped_bio, 0.62, 2.24, 12.08, 4.58)
note(s, "Slide 6 trả lời trực diện câu hỏi của giảng viên: phân cụm xong cuối cùng thống kê được gì cho khách hàng? "
     "Không đánh đồng 13 tỉnh mã -1 là yếu kém: tách thành 8 tỉnh Biên bứt phá vượt chuẩn và 5 tỉnh Cần ưu tiên Y tế công lập 6.1, "
     "cùng 48 tỉnh Vùng lõi ổn định (5 chuẩn tham chiếu 14/14 năm) và 2 tỉnh cần kiểm toán thiếu dữ liệu 2024.")


# --- SLIDE 7: THỐNG KÊ BÀN GIAO CHO KHÁCH HÀNG (2/2) ---
s = slide_new()
header(s, "THỐNG KÊ BÀN GIAO KHÁCH HÀNG (2/2)", "Bảng chỉ tiêu bàn giao, phân tách dịch chuyển & nghịch lý đô thị–y tế", 7,
       "results/stakeholder_province_summary_2024.csv · 63 tỉnh năm 2024")
stake_df = STAKE["summary"]
stake_rows = [("Nhóm hành động (63 tỉnh 2024)", "Tỉnh", "Med 4.2 / 6.1", "GRDP 24", "Khuyến nghị hành động cho khách hàng")]
rec_short = {
    "Biên bứt phá vượt chuẩn": "Khảo sát điển hình tốt để chia sẻ kinh nghiệm (không gộp là 'yếu').",
    "Vùng lõi ổn định (Cụm 2)": f"Duy trì cân bằng; theo dõi {len(stake_df.loc[stake_df['action_subtier'].eq('Trong cụm nhưng rìa dưới Y tế 6.1')])} tỉnh rìa dưới 6.1 & {len(STAKE_14Y)} chuẩn 14/14 năm.",
    "Ưu tiên cải thiện Y tế 6.1": "Chẩn đoán lệch pha quá tải y tế công 6.1 dù 4.2 & GRDP cao.",
    "Thiếu dữ liệu 2024": "Kiểm tra, bổ sung thu thập mẫu PAPI 2024 trước khi xếp loại.",
}
for grp in ("Biên bứt phá vượt chuẩn", "Vùng lõi ổn định (Cụm 2)", "Ưu tiên cải thiện Y tế 6.1", "Thiếu dữ liệu 2024"):
    if grp not in STAKE_GROUPS.index:
        continue
    r = STAKE_GROUPS.loc[grp]
    m42 = "—" if str(r["median_sd_4_2"]) == "nan" else f"{_dec(float(r['median_sd_4_2']), 2)} / {_dec(float(r['median_sd_6_1']), 2)}"
    grd = "—" if str(r["median_grdp_2024_mil"]) == "nan" else f"{_dec(float(r['median_grdp_2024_mil']), 1)} tr"
    stake_rows.append((grp, int(r["n_provinces"]), m42, grd, rec_short[grp]))
result_table(s, stake_rows, 0.55, 1.30, [3.05, 0.68, 1.55, 1.15, 5.80], 0.60, 12.8, left_cols=(0, 4))

up_names = ", ".join(
    "BR-VT" if p == "Bà Rịa - Vũng Tàu" else p
    for p in stake_df.loc[stake_df["transition_2023_2024"].eq("Rời Cụm 2 lên biên bứt phá"), "province_vi"]
)
down_names = ", ".join(
    stake_df.loc[stake_df["transition_2023_2024"].eq("Rời Cụm 2 xuống rìa Y tế 6.1"), "province_vi"]
)
watch_top4 = ", ".join(
    f"{r['province_vi']} ({_dec(100 * r['risk_outside_scenario_share'], 1)}%)"
    for _, r in STAKE_WATCH.head(4).iterrows()
)
watch_next3 = ", ".join(STAKE_WATCH.iloc[4:7]["province_vi"].tolist())
prio_sub = stake_df.loc[stake_df["action_group"].eq("Ưu tiên cải thiện Y tế 6.1")]
prio_names = ", ".join(prio_sub["province_vi"].tolist())
prio_61_range = f"{_dec(float(prio_sub['sd_6_1'].min()), 2)}–{_dec(float(prio_sub['sd_6_1'].max()), 2)}"

card(s, 0.55, 4.52, 6.00, 2.30, fill=SOFT_GREEN, border=BORDER, accent=GREEN, accent_side="left")
bullets(s, 0.72, 4.64, 5.70, 2.08, [
    (f"{len(STAKE_14Y)} chuẩn bền vững 14/14 năm.", f"{', '.join(STAKE_14Y['province_vi'].tolist())} (0 năm nhiễu suốt 2011–2024)."),
    ("Tách 7 tỉnh rời Cụm 2 (2023→2024).", f"{STAKE_TRANS.get('Rời Cụm 2 lên biên bứt phá', 0)} tỉnh lên Biên bứt phá ({up_names}); chỉ {STAKE_TRANS.get('Rời Cụm 2 xuống rìa Y tế 6.1', 0)} tỉnh xuống rìa 6.1 ({down_names})."),
], size=13.2, gap_pt=10, lead_color=GREEN)

card(s, 6.77, 4.52, 6.00, 2.30, fill=SOFT_CORAL, border=BORDER, accent=CORAL, accent_side="left")
bullets(s, 6.94, 4.64, 5.70, 2.08, [
    (f"Top cảnh báo trượt vùng (AUC={_dec(FORECAST['scenario_auc'], 3)}).", f"{watch_top4} (kế tiếp: {watch_next3})."),
    ("Nghịch lý Đô thị – Y tế 6.1.", f"Nhóm ưu tiên Y tế ({prio_names}) có GRDP/người trung vị {_dec(float(STAKE_GROUPS.loc['Ưu tiên cải thiện Y tế 6.1', 'median_grdp_2024_mil']), 1)} triệu đ (vượt vùng lõi {_dec(float(STAKE_GROUPS.loc['Vùng lõi ổn định (Cụm 2)', 'median_grdp_2024_mil']), 1)}), nhưng 6.1 tụt sâu ({prio_61_range})."),
], size=13.2, gap_pt=10, lead_color=CORAL)
note(s, "Bảng thống kê 63 tỉnh là đầu ra bàn giao trực tiếp cho cơ quan quản lý địa phương / khách hàng: "
     "gồm phân nhóm hành động, top 5 chuẩn 14/14 năm, hướng dịch chuyển 2023-2024 và watchlist cảnh báo sớm.")


# --- SLIDE 8: THÍ NGHIỆM DỰ BÁO BỔ TRỢ ---
s = slide_new()
header(s, "THÍ NGHIỆM DỰ BÁO 2024", "Dự báo điểm giảm MAE nhưng bỏ sót vùng rìa → cần xếp hạng kịch bản", 8,
       "scripts/common/papi_forecast.py · Notebook §6.1")
text(s, 0.55, 1.24, 12.2, 0.45, [
    (f"Ridge (chọn theo 6 lượt CV 2018–2023) dự báo 4.2 và 6.1 từ 8 chỉ tiêu năm 2023; đối chiếu {N_COMPARED} tỉnh đủ dữ liệu năm 2024.", 14.0, False, INK),
], margin=0.01)
card(s, 0.55, 1.76, 7.18, 5.04, fill=WHITE, border=BORDER)
pic(s, "papi_forecast_grid.png", 0.62, 1.82, 7.04, 4.92)

result_table(s, [
    ("Chỉ tiêu", "MAE Ridge", "MAE giữ 2023", "RMSE Ridge"),
    ("4.2", _dec(SCORES["sd_4_2", "forecast"]["mae"]), _dec(SCORES["sd_4_2", "carry"]["mae"]), _dec(SCORES["sd_4_2", "forecast"]["rmse"])),
    ("6.1", _dec(SCORES["sd_6_1", "forecast"]["mae"]), _dec(SCORES["sd_6_1", "carry"]["mae"]), _dec(SCORES["sd_6_1", "forecast"]["rmse"])),
], 7.90, 1.76, [0.92, 1.25, 1.38, 1.32], 0.58, 13.0)

card(s, 7.90, 3.68, 4.87, 1.48, fill=SOFT_CORAL, border=BORDER, accent=CORAL, accent_side="left")
bullets(s, 8.05, 3.80, 4.60, 1.26, [
    ("Hạn chế dự báo điểm.", f"Ridge nhận ra {ZONES['forecast']['out_correct']}/{N_OUTSIDE} tỉnh ngoài vùng dày (độ đúng cân bằng 50%) vì dự báo co về trung bình."),
], size=13.4, gap_pt=4, lead_color=CORAL)

card(s, 7.90, 5.32, 4.87, 1.48, fill=SOFT_TEAL, border=BORDER, accent=TEAL, accent_side="left")
bullets(s, 8.05, 5.44, 4.60, 1.26, [
    ("Giải pháp kịch bản sai số.", f"Cộng {FORECAST['scenario_count']} cặp phần dư CV lịch sử vào dự báo điểm để tính tỉ lệ kịch bản rời vùng → AUC thăm dò = {_dec(FORECAST['scenario_auc'], 3)}."),
], size=13.4, gap_pt=4, lead_color=TEAL)
note(s, "Thí nghiệm dự báo chứng minh không thể chỉ dùng giá trị dự báo điểm để cảnh báo tỉnh rời vùng dày; phải kèm phân phối sai số lịch sử.")


# --- SLIDE 9: KIỂM CHỨNG NGOẠI LAI & ĐỘ BỀN ĐA CHIỀU ---
s = slide_new()
header(s, "KIỂM CHỨNG NGOẠI LAI & ĐỘ BỀN", "Đối chiếu dữ liệu độc lập ngoài PAPI & thử nghiệm đa chiều PCA / 8D", 9,
       "results/external_validation.md · results/poverty_validation.md · results/robustness.csv")

text(s, 0.55, 1.14, 12.2, 0.25, [("A. ĐỐI CHIẾU 4 NGUỒN DỮ LIỆU ĐỘC LẬP NGOÀI PAPI (CHỈ MÔ TẢ, KHÔNG SUY NHÂN QUẢ)", 11.0, True, TEAL)], space_after=0, margin=0.01)
result_table(s, [
    ("Nguồn độc lập ngoài PAPI", "Mẫu (n)", "Kiểm định giữa nhóm STING", "Kết luận mô tả (không suy nhân quả)"),
    ("PCI weighted (2011–2022)", "747", "Kruskal H=31,78, p=5,84e-07", "Cụm 2 (62,16) cao hơn nhiễu −1 (59,16); p tham khảo"),
    ("GRDP/người (2018–2024)", "430", "Kruskal H=9,50, p=0,00867", "Nhiễu (68,31 tr) cao hơn Cụm 2 (61,55 tr)"),
    ("Mật độ Y tế ODM (2020)", "63", "Kruskal H=2,01, p=0,156", "Không khác biệt (10 tỉnh không có điểm nguồn)"),
    ("Nghèo GSO (2012–2024)", "805", "Thô p=0,198 | Trừ năm p=1,26e-4", "Gộp thô không khác biệt; hiệu ứng yếu (η²=0,012)"),
], 0.55, 1.40, [2.75, 0.90, 3.05, 5.53], 0.39, 11.8)

text(s, 0.55, 3.46, 12.2, 0.25, [("B. KIỂM TRA ĐỘ BỀN ĐA CHIỀU (PCA 6 CHIỀU & 8 CHIỀU OFAT 2018–2024)", 11.0, True, NAVY)], space_after=0, margin=0.01)
rob_rows = [("Thử nghiệm đa chiều (Robustness)", "n", "k", "Nhiễu", "Silhouette", "Kết luận")]
for r in ROBUSTNESS:
    sil_raw = r["silhouette"].strip()
    sil = "n/a" if not sil_raw else _dec(float(sil_raw), 3)
    verdict = r["verdict"]
    if verdict == "có cấu trúc" and sil_raw and float(sil_raw) < 0:
        verdict = "đạt ngưỡng k/nhiễu (silh. âm, tách yếu)"
    rob_rows.append((r["branch"], r["n"], r["k"], _pct(r["noise_ratio"]).replace(".", ","), sil, verdict))
result_table(s, rob_rows, 0.55, 3.72, [4.85, 0.65, 0.50, 0.90, 1.15, 4.18], 0.39, 10.8, header_fill=NAVY_MID)

card(s, 0.55, 6.42, 12.23, 0.44, fill=SOFT_GOLD, border=BORDER, accent=GOLD, accent_side="left")
text(s, 0.72, 6.48, 11.95, 0.32, [
    ("Thông điệp cốt lõi: Phân cụm STING 2D phản ánh đúng khác biệt PCI/GRDP độc lập; mở rộng trực tiếp lên 8D OFAT làm lưới thưa nhanh do lời nguyền số chiều.", 11.5, False, INK),
], space_after=0, margin=0.01)
note(s, "Slide 9 tổng hợp đối chứng ngoại lai (PCI, GRDP, Y tế, Nghèo GSO) và kiểm tra robustness PCA / 8D OFAT.")


# --- SLIDE 10: KẾT LUẬN, GIỚI HẠN & ĐỀ XUẤT CẢI THIỆN ---
s = slide_new()
header(s, "KẾT LUẬN, GIỚI HẠN & HƯỚNG MỞ RỘNG", "Đóng góp phương pháp, giá trị khách hàng, giới hạn & đề xuất cải thiện", 10)

quad_cards = [
    (
        0.55, 1.24, TEAL, SOFT_TEAL,
        "1. Đóng góp thuật toán (STING)",
        f"• Cài đặt từ đầu đạt ARI = 0,950 (240 điểm giả lập), bảo toàn tổng count mọi tầng.\n"
        f"• Trên PAPI 2011–2023 tạo 1 cụm lớn ({_dec(100 * MAIN_SIZE / CLUSTERED, 1)}% điểm vào cụm), bất biến 869/869 ô dưới z-score tuyến tính.",
    ),
    (
        6.78, 1.24, BLUE, SOFT_BLUE,
        "2. Giá trị bàn giao khách hàng",
        "• Phân loại 63 tỉnh 2024 thành 4 nhóm hành động: 48 Vùng lõi (5 chuẩn 14/14 năm), 8 Biên bứt phá, 5 Ưu tiên Y tế 6.1, 2 Thiếu dữ liệu.\n"
        "• Vạch rõ nghịch lý GRDP cao (104,3 tr) – Y tế 6.1 thấp & watchlist cảnh báo sớm (AUC = 0,816).",
    ),
    (
        0.55, 3.44, CORAL, SOFT_CORAL,
        "3. Giới hạn trung thực",
        "• Số cụm nhạy tham số lưới; Cụm 0/1 (n = 5, 16) quá nhỏ chỉ để mô tả.\n"
        "• Audit 23/37 cột có bước nhảy thang đo; 1 năm holdout 2023→2024 & kiểm định gộp chưa chứng minh nhân quả.",
    ),
    (
        6.78, 3.44, GOLD_DEEP, SOFT_GOLD,
        "4. Đề xuất cải thiện tiếp theo",
        "• Mô hình: Cân bằng lớp (class_weight='balanced') nâng macro-F1 CV lên 0,524 (chờ GV duyệt holdout); lưới phân vị thích nghi & Conformal.\n"
        "• Sản phẩm: Bản đồ 63 tỉnh theo 4 nhóm trên Tab 6 Streamlit, xuất Phiếu chẩn đoán PDF từng tỉnh & cập nhật PAPI 2025.",
    ),
]
for qx, qy, qacc, qfill, qtitle, qbody in quad_cards:
    card(s, qx, qy, 6.00, 2.04, fill=qfill, border=BORDER, accent=qacc, accent_side="top")
    text(s, qx + 0.16, qy + 0.12, 5.68, 1.82, [
        (qtitle, 14.0, True, qacc),
        (qbody, 12.2, False, INK),
    ], space_after=5)

card(s, 0.55, 5.64, 12.23, 1.20, fill=LIGHT, border=BORDER, accent=NAVY, accent_side="left")
text(s, 0.74, 5.73, 11.90, 1.02, [
    ("TÀI LIỆU THAM KHẢO CHÍNH", 12.5, True, TEAL),
    ("Wang, Yang & Muntz (VLDB 1997) · PAPI 2011–2024 (CECODES, VFF-CRT, RTA, UNDP) · Mendeley DOI 10.17632/wbk42j9wc8.1", 13.4, False, INK),
    ("VCCI–USAID PCI · GSO PX-Web (GRDP, Dân số, Nghèo) · OD Mekong Health Facilities · Hyndman & Athanasopoulos (2021)", 13.4, False, GREY),
], space_after=3)
note(s, "Slide 10 tóm tắt đóng góp, giá trị khách hàng, giới hạn trung thực và 2 nhánh đề xuất cải thiện cho phiên bản tiếp theo. "
     "Hồ sơ nộp thống nhất: Nhom15_BaoCao_STING_PAPI.docx, Nhom15_STING_PAPI.pptx, Nhom15_STING_PAPI.ipynb và Nhom15_TienXuLy_PAPI.ipynb.")


# --- SLIDE 11: THANK YOU ---
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, 0, SW, 0.08, TEAL)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
for x_sq, y_sq, fill_sq in (
    (0.60, 0.60, NAVY_MID), (1.18, 0.60, TEAL), (0.60, 1.18, GOLD),
    (SW - 1.10, SH - 1.32, GOLD), (SW - 1.68, SH - 1.32, NAVY_MID), (SW - 1.10, SH - 1.90, TEAL),
):
    rect(s, x_sq, y_sq, 0.46, 0.46, fill_sq)
text(s, 0.55, 3.05, 12.23, 1.25, [
    (r"Cảm ơn thầy và các bạn đã lắng nghe", 40, True, GOLD),
], align=PP_ALIGN.CENTER)
note(s, "Phần trình bày kết thúc. Nhóm xin cảm ơn thầy và các bạn đã lắng nghe và mong nhận được câu hỏi phản biện.")

assert len(prs.slides) == SLIDE_COUNT
OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print("saved:", OUT)
print("slides:", len(prs.slides))
