"""Build slides/submission.pptx — 10 trang đầu và một trang cảm ơn.

Cách dùng: python scripts/deliverables/build_slides_10.py
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from matplotlib import pyplot as plt
from sklearn.cluster import DBSCAN, KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from scripts.common.fig_style import PALETTE, style_context
from scripts.common.midterm_clustering import (
    FEATURES, GRID, THRESHOLDS, K_CANDIDATES, KMEANS_OPTIONS, DBSCAN_OPTIONS,
    fit_grid, comparison_figure, raw_dbscan_radius, reference_grid_assignments, sting_steps_figure,
)
from scripts.common.papi_pred_common import load_panel
from sting import STING

ROOT = _ROOT
FIGS = ROOT / "results" / "figs"
OUT = ROOT / "slides" / "submission.pptx"
TOTAL = 11

def _read_results_csv(name: str) -> list[dict[str, str]]:
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))



PAPI_PANEL = load_panel()
PAPI_COMPLETE = PAPI_PANEL.dropna(subset=FEATURES)
PAPI_COUNT = len(PAPI_COMPLETE)
PAPI_RAW = PAPI_COMPLETE[list(FEATURES)].to_numpy()
PAPI_SCALER = StandardScaler().fit(PAPI_RAW)
PAPI_Z = PAPI_SCALER.transform(PAPI_RAW)
PAPI_GRID, PAPI_LABELS = fit_grid(PAPI_Z)
PAPI_GRID_SIZE = GRID["factor"] ** GRID["cluster_level"]
PAPI_SIZES = sorted((n for label, n in Counter(PAPI_LABELS).items() if label >= 0), reverse=True)
PAPI_NOISE = int((PAPI_LABELS == -1).sum())
DENSE_COMPONENTS = sorted(Counter(PAPI_GRID.label_of_.values()).values())

KM_MODELS = {k: KMeans(n_clusters=k, **KMEANS_OPTIONS).fit(PAPI_Z) for k in K_CANDIDATES}
KM_SCORES = {k: silhouette_score(PAPI_Z, model.labels_) for k, model in KM_MODELS.items()}
BEST_K = max(KM_SCORES, key=KM_SCORES.get)
KM_MODEL = KM_MODELS[BEST_K]
DB_LABELS = DBSCAN(**DBSCAN_OPTIONS).fit_predict(PAPI_Z)
DB_EPS_RAW = raw_dbscan_radius(PAPI_SCALER.scale_)
DB_RAW = DBSCAN(eps=DB_EPS_RAW, min_samples=DBSCAN_OPTIONS['min_samples']).fit_predict(PAPI_RAW)
DB_NOISE_CHANGED = int(((DB_RAW == -1) != (DB_LABELS == -1)).sum())
COMMON = (PAPI_LABELS >= 0) & (KM_MODEL.labels_ >= 0) & (DB_LABELS >= 0)
N_COMMON = int(COMMON.sum())
DBSCAN_NOISE = int((DB_LABELS == -1).sum())
BOTH_NOISE = int(((PAPI_LABELS == -1) & (DB_LABELS == -1)).sum())
LARGEST = Counter(PAPI_LABELS[PAPI_LABELS >= 0]).most_common(1)[0][0]

RAW_GRID, RAW_LABELS = fit_grid(PAPI_RAW)
GRID_LEVEL = PAPI_GRID.cluster_level_
SAME_BIN = int((RAW_GRID.point_cell_index(GRID_LEVEL) == PAPI_GRID.point_cell_index(GRID_LEVEL)).all(axis=1).sum())
SAME_LABEL = int((RAW_LABELS == PAPI_LABELS).sum())
KM2_RAW = KMeans(n_clusters=2, **KMEANS_OPTIONS).fit_predict(PAPI_RAW)
KMEANS2_SAME_ID = int((KM2_RAW == KM_MODELS[2].labels_).sum())
KMEANS2_CHANGED = min(KMEANS2_SAME_ID, PAPI_COUNT - KMEANS2_SAME_ID)

SENSITIVITY = {}
for threshold in THRESHOLDS:
    trial, _ = fit_grid(PAPI_Z, min_count=threshold)
    SENSITIVITY[threshold] = trial.n_clusters_


AUDIT = _read_results_csv("preprocessing_audit.csv")


def _audit_row(stage_sub: str, test_sub: str) -> dict[str, str]:
    hits = [r for r in AUDIT if stage_sub in r["stage"] and test_sub in r["test"]]
    if len(hits) != 1:
        raise KeyError(f"{stage_sub} / {test_sub}: {len(hits)} dòng trong preprocessing_audit.csv")
    return hits[0]


def _nums(pattern: str, text: str) -> tuple[int, ...]:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"không khớp {pattern!r} trong: {text}")
    return tuple(int(group) for group in match.groups())


_DUP_ROW = _audit_row("(a) trùng khóa", "dedup")
_MISS_ROW = _audit_row("(b) giá trị thiếu", "Ô thiếu trong 37 cột")
_OUT_ROW = _audit_row("(d) ngoại lai", "z-score")

N_DUP, N_ROWS = _nums(r"(\d+) dòng trùng / (\d+) dòng", _DUP_ROW["result"])
N_MISS, N_CELLS = _nums(r"(\d+)/(\d+) ô", _MISS_ROW["result"])
(N_OUT,) = _nums(r"^(\d+) ô", _OUT_ROW["result"])
(Z_OUT,) = _nums(r"z-score > (\d+)", _OUT_ROW["test"])

assert N_DUP == 0, "preprocessing_audit.csv: kỳ vọng 0 dòng trùng khóa"
assert "KHÔNG nội suy" in _MISS_ROW["decision"], "preprocessing_audit.csv: quyết định ô thiếu đã đổi"
assert "chỉ đánh dấu" in _OUT_ROW["decision"], "preprocessing_audit.csv: quyết định ngoại lai đã đổi"


def _sp(n: int) -> str:
    """Tách hàng nghìn bằng khoảng trắng (4 649) — không lẫn với dấu thập phân."""
    return f"{n:,}".replace(",", " ")


_X_SYN, _Y_SYN = make_blobs(
    n_samples=240, centers=[(-6, -6), (6, 6)], cluster_std=0.6, random_state=42
)
_syn_model = STING(n_levels=3, factor=4, min_count=3).fit(_X_SYN)
_syn_labels = _syn_model.cluster(level=2, connectivity=1)
SYN_ARI = adjusted_rand_score(_Y_SYN, _syn_labels)
SYN_NOISE = float((_syn_labels == -1).mean())
SYN_K = int(_syn_model.n_clusters_)
assert SYN_ARI >= 0.9
assert SYN_NOISE <= 0.05
assert SYN_K == 2
SYN_ARI_S = f"{SYN_ARI:.3f}"

def _callout_cell(model: STING, level: int = 2) -> tuple[tuple[int, ...], object]:
    """Ô dày đại diện trên demo tổng hợp (số thật từ fit slide build)."""
    cells = model.cells_[level]
    dense = [(k, c) for k, c in cells.items() if c.count >= model.min_count_]
    key, cell = max(dense, key=lambda kv: kv[1].count)
    return key, cell


NAVY = RGBColor(0x0F, 0x2B, 0x46)
TEAL = RGBColor(0x1B, 0x6E, 0x77)
GOLD = RGBColor(0xE2, 0xB0, 0x4A)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x5A, 0x5A, 0x5A)
LIGHT = RGBColor(0xF6, 0xF4, 0xEF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRID_HI = RGBColor(0xD4, 0xE8, 0xEA)
GRID_LO = RGBColor(0xE8, 0xEC, 0xF0)

SW, SH = 13.333, 7.5

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


def slide_new():
    return prs.slides.add_slide(BLANK)


def rect(slide, x, y, w, h, fill, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    return shp


def text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, space_after=4):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
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
    rect(slide, 0, 0, SW, 0.16, TEAL)
    text(slide, 0.55, 0.32, 10.5, 0.3, [(kicker, 12, True, TEAL)])
    text(slide, 0.55, 0.58, 12.2, 0.75, [(title, 26, True, NAVY)])
    rect(slide, 0.55, SH - 0.42, SW - 1.1, 0.012, RGBColor(0xD8, 0xD5, 0xCC))
    text(
        slide, 0.55, SH - 0.36, 9.5, 0.3,
        [(source, 10, False, GREY)],
    )
    text(
        slide, SW - 1.6, SH - 0.36, 1.1, 0.3,
        [(f"{page_no:02d} / {TOTAL}", 10, True, GREY)],
        align=PP_ALIGN.RIGHT,
    )


def note(slide, text_md: str):
    slide.notes_slide.notes_text_frame.text = text_md


def ari_fraction(group, x, y, label, numerator, denominator, label_w, fraction_w):
    """An editable fraction built from PowerPoint text and a horizontal bar."""
    part_x = x + label_w
    for value, left, top, width in (
        (label, x, y + 0.16, label_w),
        (numerator, part_x, y, fraction_w),
        (denominator, part_x, y + 0.34, fraction_w),
    ):
        box = text(group, left, top, width, 0.34, [(value, 19, False, NAVY)], align=PP_ALIGN.CENTER)
        frame = box.text_frame
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = Pt(0)
        frame.paragraphs[0].runs[0].font.name = "Cambria Math"
    rect(group, part_x, y + 0.326, fraction_w, 0.012, NAVY)


def bullets(slide, x, y, w, h, items, size=13, color=INK, gap_pt=6, bold_first=True,
            lead_color=TEAL, align=PP_ALIGN.LEFT, hang_in=0.22, gap_first=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (lead, rest) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(gap_first if (i == 0 and gap_first is not None) else gap_pt)
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


def pic(slide, path, x, y, w=None, h=None):
    p = FIGS / path
    assert p.exists(), f"missing {p}"
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    slide.shapes.add_picture(str(p), Inches(x), Inches(y), **kw)


def _sting_hierarchy_figure_png(model: STING, X: np.ndarray) -> BytesIO:
    """Ba panel STING mức 0/1/2 — độ phân giải factor**level (1×1, 4×4, 16×16 khi f=4)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    lo, hi = model.bounds_min_, model.bounds_max_
    span = hi - lo
    f = model.factor
    panels = [
        (f ** 0, "Mức 0 (1×1)"),
        (f ** 1, f"Mức 1 ({f}×{f})"),
        (f ** 2, f"Mức 2 ({f ** 2}×{f ** 2})"),
    ]
    level2_res = f ** 2
    bio = BytesIO()
    with style_context():
        fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.35), dpi=200)
        for level, (ax, (res, title)) in enumerate(zip(axes, panels)):
            cells = model.cells_[level]
            max_count = max(cell.count for cell in cells.values())
            step = span / res
            for cell in cells.values():
                x0, y0 = cell.bounds_min
                alpha = 0.1 + 0.65 * cell.count / max_count
                ax.add_patch(
                    Rectangle(
                        (x0, y0),
                        step[0],
                        step[1],
                        facecolor=PALETTE["sky"],
                        alpha=alpha,
                        edgecolor=PALETTE["gray"],
                        linewidth=0.45,
                        zorder=1,
                    )
                )
            for k in range(1, res):
                vx = lo[0] + k * step[0]
                vy = lo[1] + k * step[1]
                ax.axvline(vx, color=PALETTE["blue"], linewidth=0.7, alpha=0.85, zorder=2)
                ax.axhline(vy, color=PALETTE["blue"], linewidth=0.7, alpha=0.85, zorder=2)
            ax.scatter(X[:, 0], X[:, 1], s=9, c="#1a1a1a", alpha=0.55, zorder=3, linewidths=0)
            ax.set_xlim(lo[0], hi[0])
            ax.set_ylim(lo[1], hi[1])
            ax.set_aspect("equal", adjustable="box")
            ax.set_title(title, fontsize=11, pad=6)
            ax.tick_params(labelsize=7)
            if res == level2_res:
                key, _cell = _callout_cell(model, level=2)
                ix, iy = int(key[0]), int(key[1])
                cx0, cy0 = lo[0] + ix * step[0], lo[1] + iy * step[1]
                highlight = Rectangle(
                    (cx0, cy0),
                    step[0],
                    step[1],
                    fill=False,
                    edgecolor=PALETTE["orange"],
                    linewidth=1.8,
                    zorder=4,
                )
                ax.add_patch(highlight)
                p_ix, p_iy = ix // f, iy // f
                px0, py0 = lo[0] + p_ix * (span[0] / f), lo[1] + p_iy * (span[1] / f)
                pstep = span / f
                ax.add_patch(
                    Rectangle(
                        (px0, py0),
                        pstep[0],
                        pstep[1],
                        fill=False,
                        edgecolor=PALETTE["blue"],
                        linewidth=1.0,
                        linestyle="--",
                        zorder=4,
                    )
                )
                ax.annotate(
                    f"ô mức 2: {_cell.count} điểm",
                    xy=(cx0 + step[0] * 0.5, cy0 + step[1] * 0.5),
                    xytext=(px0 + pstep[0] * 0.15, py0 + pstep[1] * 1.05),
                    fontsize=8.5,
                    color="#333333",
                    arrowprops=dict(arrowstyle="->", color=PALETTE["orange"], lw=1.0),
                    zorder=5,
                )
        fig.subplots_adjust(left=0.04, right=0.99, top=0.88, bottom=0.12, wspace=0.22)
        fig.savefig(bio, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    bio.seek(0)
    return bio


def pic_bytes(slide, bio: BytesIO, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    slide.shapes.add_picture(bio, Inches(x), Inches(y), **kw)


def result_table(slide, rows, x, y, widths, row_height, font_size=16):
    table = slide.shapes.add_table(
        len(rows), len(widths), Inches(x), Inches(y), Inches(sum(widths)), Inches(len(rows) * row_height)
    ).table
    for column, width in zip(table.columns, widths, strict=True):
        column.width = Inches(width)
    for i, row in enumerate(rows):
        table.rows[i].height = Inches(row_height)
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text_frame.text = str(value)
            paragraph = cell.text_frame.paragraphs[0]
            if j > 0:
                paragraph.alignment = PP_ALIGN.CENTER
            font = paragraph.runs[0].font
            font.name, font.size, font.bold = "Calibri", Pt(font_size), i == 0
            font.color.rgb = WHITE if i == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL if i == 0 else WHITE if i % 2 else LIGHT


s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
for r in range(4):
    for c in range(4):
        x0, y0 = SW - 4.6 + c * 0.78, 1.05 + r * 0.78
        fill = GOLD if (r, c) in ((1, 1), (2, 2)) else RGBColor(0x1E, 0x3D, 0x5E)
        rect(s, x0, y0, 0.66, 0.66, fill)
text(s, 0.85, 1.15, 7.6, 0.4, [("HỌC MÁY · BÁO CÁO GIỮA KỲ", 15, True, GOLD)])
text(
    s, 0.85, 1.80, 7.6, 2.95,
    [
        ("PHÂN CỤM DỰA TRÊN LƯỚI STING", 34, True, WHITE),
        ("Đặc điểm và biến động PAPI tại 63 tỉnh, thành phố giai đoạn 2011–2024", 22, False, WHITE),
        ("APPLICATION OF STING GRID-BASED CLUSTERING TO PAPI DATA", 12, False, RGBColor(0xB9, 0xCD, 0xDE)),
    ],
    space_after=10,
)
text(
    s, 0.85, 4.7, 7.8, 1.9,
    [
        ("Nhóm 15 · Chủ đề 6 · Grid-based clustering", 16, True, GOLD),
        ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 15, False, RGBColor(0xB9, 0xCD, 0xDE)),
    ],
)
note(
    s,
    "Kính thưa thầy, nhóm 15 phụ trách chủ đề phân cụm dựa trên lưới và chọn thuật toán STING. "
    "Nhóm minh họa bằng lưới 3 × 3 và dữ liệu giả lập để giải thích cách đếm điểm, chọn ô dày "
    "và tạo cụm. Nhóm cũng đã chuẩn bị dữ liệu PAPI để minh họa thêm phần ứng dụng.",
)


s = slide_new()
header(s, "CHỦ ĐỀ VÀ DỮ LIỆU", "Phân cụm trên hai chỉ tiêu PAPI", 2,
       "src/preprocessing.py · Notebook giữa kỳ §4.1")
rect(s, 0.6, 1.52, 5.22, 4.56, LIGHT)
text(s, 0.86, 1.75, 4.71, 1.38, [
    (f"{N_ROWS} × 41", 34, True, NAVY),
    ("63 tỉnh, thành phố · 2011–2024", 17, False, GREY),
])
text(s, 0.86, 3.43, 4.71, 2.35, [
    ("HAI TRỤC CỦA LƯỚI", 14, True, TEAL),
    ("4.2  Kiểm soát tham nhũng trong cung ứng dịch vụ công", 17.5, False, INK),
    ("6.1  Y tế công lập", 17.5, False, INK),
], space_after=9)
text(s, 6.2, 1.53, 6.53, 0.48, [("run_preprocessing_pipeline(...)", 18, True, TEAL)])
bullets(s, 6.2, 2.1, 6.53, 4.06, [
    ("Làm sạch.", f"{N_DUP}/{N_ROWS} khóa tỉnh–năm trùng. Kiểm tra thiếu, thang đo và cực trị."),
    ("Tích hợp.", "Chuẩn hóa mã tỉnh, ghép 14 bảng tính năm."),
    ("Chọn mẫu.", f"dropna theo cặp 4.2 và 6.1. Còn {PAPI_COUNT} quan sát tỉnh–năm cho phân cụm mô tả."),
    ("Chuẩn hóa.", "StandardScaler tính z = (x − μ) / σ riêng cho từng chỉ tiêu."),
], size=16.5, gap_pt=14)
text(s, 0.6, 6.23, 12.1, 0.59, [
    (f"{_sp(N_MISS)}/{_sp(N_CELLS)} ô thiếu được giữ trong panel. Giữ nguyên {N_OUT} ô được gắn cờ |z| > {Z_OUT}.",
     15, False, GREY),
])
note(
    s,
    "STING là phương pháp nhóm chọn để tìm các vùng có nhiều điểm gần nhau trên hai chỉ tiêu PAPI. "
    "Mỗi quan sát là một tỉnh trong một năm. Mục tiêu ứng dụng là mô tả đặc điểm vùng dày và "
    "theo dõi sự dịch chuyển của tỉnh khi dùng chung lưới. "
    "Notebook chạy sáu bước tiền xử lý từ dữ liệu gốc và đối chiếu panel 882 × 41. "
    "Số ô thiếu và số ô được gắn cờ trên slide tính trên 37 cột điểm, trước khi lấy hai chỉ tiêu. "
    f"Phân cụm mô tả dùng {PAPI_COUNT} dòng, gồm điểm đã đo năm 2024. "
    "Phép gán riêng ở slide 10 dùng scaler và lưới dựng trên các năm đến 2023. "
    "Dữ liệu PAPI do CECODES, VFF-CRT, RTA và UNDP công bố. https://papi.org.vn/du-lieu-papi/",
)


s = slide_new()
header(s, "LƯỚI THỐNG KÊ", "Lưới từ thô đến mịn", 3,
       "src/sting.py · Notebook giữa kỳ §4.3.2")
pic_bytes(s, _sting_hierarchy_figure_png(_syn_model, _X_SYN), 0.55, 1.32, w=SW - 1.1)
_, example_cell = _callout_cell(_syn_model, level=2)
bullets(
    s, 0.75, 5.02, 11.8, 1.76,
    [
        ("Độ mịn.", "Mức l có r = factorˡ đoạn mỗi trục. Với factor = 4, các mức có 1, 4 và 16 đoạn."),
        ("Thống kê theo ô.", f"Ô viền cam chứa {example_cell.count} điểm. Mỗi ô còn lưu trung bình, "
         "độ lệch chuẩn, giá trị nhỏ nhất và lớn nhất."),
    ],
    size=17, gap_pt=14,
)
note(
    s,
    "Ba hình thể hiện cùng một tập điểm ở các mức lưới khác nhau. Mức 0 có một ô, "
    "mức 1 có lưới 4×4 và mức 2 có lưới 16×16. Ô viền cam minh họa số đếm do chương trình "
    "tính từ dữ liệu. Ý tưởng lưới phân cấp và thống kê ô dựa trên "
    "Wang, Yang & Muntz (VLDB 1997).",
)


s = slide_new()
header(s, "CƠ CHẾ", "Biến thể STING tạo cụm từ các ô dày", 4,
       "src/sting.py · Notebook giữa kỳ §1–2")
steps = [
    ("fit(X)", "_assign và _accumulate",
     "Tính chỉ số ô và lưu số điểm, trung bình, độ lệch chuẩn, cực trị."),
    ("cluster(level, connectivity=1)", "count ≥ min_count",
     "Duyệt sâu qua các ô dày kề cạnh để gán nhãn cho mỗi vùng liên thông."),
    ("predict(X_moi)", "Tra nhãn ô",
     "Giữ nguyên lưới và tra nhãn. Điểm ngoài vùng dày nhận −1."),
]
for i, (title, rule, description) in enumerate(steps):
    x = 0.6 + i * 4.12
    rect(s, x, 1.30, 3.86, 1.78, LIGHT)
    text(s, x + 0.16, 1.39, 3.54, 0.34, [(title, 15, True, TEAL)])
    rect(s, x + 0.20, 1.77, 3.46, 0.38, WHITE)
    text(s, x + 0.20, 1.81, 3.46, 0.32, [(rule, 14, True, NAVY)], align=PP_ALIGN.CENTER)
    text(s, x + 0.16, 2.21, 3.54, 0.80, [(description, 13, False, INK)])
step_fig = sting_steps_figure(figsize=(12.2, 2.95), dpi=200)
step_bio = BytesIO()
step_fig.savefig(step_bio, format="png", dpi=200, facecolor="white")
plt.close(step_fig)
step_bio.seek(0)
pic_bytes(s, step_bio, 0.96, 3.16, w=11.41)
text(s, 0.63, 6.02, 12.04, 0.40, [
    ("Chỉ số ô mỗi trục = clip(floor((z − zmin) / Δ), 0, r − 1), với Δ = (zmax − zmin) / r.", 15, True, NAVY),
])
text(s, 0.63, 6.46, 12.04, 0.42, [
    ("STING gốc dùng phân phối và khoảng tin cậy khi truy vấn từ trên xuống. Xem mục 4.3.3.", 14.5, False, GREY),
])
note(
    s,
    "Trong cài đặt của nhóm, một ô được xem là dày khi số điểm trong ô đạt min_count. "
    "Tại mức lưới đã chọn, chương trình duyệt từ một ô dày sang các ô dày chung cạnh "
    "cho đến khi hết ô có thể đi tới. Các ô đã duyệt tạo thành một cụm. "
    "Hình bốn bước bên dưới minh họa đầy đủ quy trình từ 15 điểm thô đến chia lưới 3×3, "
    "chọn ô dày (≥ 3), gắn nhãn −1 cho ô thưa (1 điểm) và nối kề 4 hướng (chạm góc không nối). "
    "Điểm trong ô thưa nhận nhãn nhiễu −1. Phần phân cụm PAPI chọn một mức lưới. "
    "Ở ví dụ 3×3, notebook gọi fit trên 15 điểm và cluster(level=1, connectivity=1). "
    "Dưới hình, r là số ô trên một trục và Δ là bề rộng một ô. Lấy tọa độ trừ biên dưới "
    "rồi chia cho Δ để đo điểm đã đi qua bao nhiêu độ rộng ô. Floor(1,7) cho ô chỉ số 1, "
    "tức ô thứ hai. Ở đúng biên trên, clip đưa chỉ số r về r−1. Khi gán điểm mới, "
    "predict kiểm tra biên trước và trả −1 cho điểm ngoài lưới.\n\n"
    "Mục 5 của bài báo dùng phân phối và khoảng tin cậy để xét ô nào còn liên quan, rồi đi "
    "xuống ô con. Mục 4.3.3 trong notebook minh họa query_top_down. Hàm thống kê 322 điểm "
    "trong các ô nằm trọn vùng, còn lọc trực tiếp từng điểm cho 348. "
    "Xem Wang, Yang và Muntz (VLDB 1997) tại https://www.vldb.org/conf/1997/P186.PDF",
)


s = slide_new()
header(s, "VÍ DỤ", "Đọc cụm từ bảng đếm 3 × 3", 5)
text(s, 0.85, 1.43, 6.1, 0.45, [("Số trong ô là số điểm", 17, True, NAVY)])
for row, values in enumerate(((4, 3, 0), (1, 0, 4), (0, 0, 3))):
    for col, count in enumerate(values):
        x, y = 0.85 + col * 1.35, 2.0 + row * 1.35
        fill = (TEAL if row == 0 else NAVY) if count >= 3 else GOLD if count else GRID_LO
        rect(s, x, y, 1.29, 1.29, fill)
        text(s, x, y + 0.35, 1.29, 0.62, [
            (str(count), 26, True, WHITE if count >= 3 else INK),
        ], align=PP_ALIGN.CENTER)
rect(s, 5.6, 1.96, 7.08, 4.05, LIGHT)
text(s, 5.88, 2.17, 6.48, 0.52, [("15 điểm · ngưỡng 3 điểm/ô", 21, True, NAVY)])
for i, (label, fill, detail) in enumerate((
    ("Cụm A", TEAL, "Hai ô chung cạnh, tổng 7 điểm."),
    ("Cụm B", NAVY, "Hai ô chung cạnh, tổng 7 điểm."),
    ("Nhiễu", GOLD, "Ô có 1 điểm dưới ngưỡng, nhận nhãn −1."),
)):
    y = 2.98 + i * 0.76
    rect(s, 5.9, y + 0.12, 0.27, 0.27, fill)
    text(s, 6.35, y, 5.95, 0.58, [
        (f"{label}. {detail}", 17, False, INK),
    ])
text(s, 5.88, 5.42, 6.48, 0.38, [("model.cluster(level=1, connectivity=1)", 14.5, True, TEAL)])
text(s, 0.85, 6.3, 11.8, 0.42, [
    ("Hai vùng màu chỉ chạm góc nên tách thành 2 cụm.", 17, True, NAVY),
])
note(
    s,
    "Ví dụ có 15 điểm và ngưỡng ô dày bằng 3. Cặp ô chứa 4 và 3 điểm ở hàng trên tạo cụm A. "
    "Cặp ô bên phải tạo cụm B. Hai vùng này chỉ chạm góc, nên với quy tắc nối qua cạnh "
    "chúng thuộc hai cụm khác nhau. Điểm trong ô chứa 1 điểm nhận nhãn nhiễu.",
)


s = slide_new()
header(s, "DỮ LIỆU GIẢ LẬP", "Đối chiếu kết quả với hai cụm đã biết", 6)
pic(s, "00_synthetic_sting.png", 0.55, 1.55, h=4.65)
bullets(
    s, 7.85, 1.73, 4.9, 4.6,
    [
        ("Dữ liệu.", "240 điểm, biết trước hai cụm khi sinh dữ liệu."),
        ("Kết quả.", f"STING tìm {SYN_K} cụm, nhiễu {SYN_NOISE:.1%}."),
        ("Độ khớp.", f"ARI {SYN_ARI_S} khi so với nhãn giả lập."),
    ],
    size=17, gap_pt=24,
)
ari = s.shapes.add_group_shape()
ari.name = "Công thức ARI"
ari._element.xpath("./p:nvGrpSpPr/p:cNvPr")[0].set(
    "descr",
    "E = (A × B) / C(n, 2). ARI = (T − E) / ((A + B)/2 − E).",
)
text(ari, 7.85, 3.97, 4.9, 0.34, [("Công thức ARI", 16, True, TEAL)])
ari_fraction(ari, 7.97, 4.38, "E =", "A × B", "C(n, 2)", 0.47, 1.14)
ari_fraction(ari, 9.83, 4.38, "ARI =", "T − E", "(A + B)/2 − E", 0.78, 2.08)
text(
    ari, 7.85, 5.20, 4.9, 1.32,
    [
        ("A, B đếm cặp cùng nhóm theo từng bộ nhãn.", 14, False, INK),
        ("T đếm cặp cùng nhóm theo cả hai bộ nhãn.", 14, False, INK),
        ("E là số cặp kỳ vọng khi xáo nhãn.", 14, False, INK),
        ("C(n, 2) là tổng số cặp điểm.", 14, False, INK),
    ],
    space_after=3,
)
note(
    s,
    "Với 240 điểm sinh từ hai phân bố Gauss, STING tìm được hai cụm và đánh dấu 2,5% điểm là nhiễu. "
    "ARI bằng 0,950 đo mức khớp giữa kết quả và nhãn đã biết khi sinh dữ liệu. "
    "Phép thử này kiểm tra cách cài đặt trên ví dụ có nhãn tham chiếu.\n\n"
    "Chỉ vào hai phân số. A đếm cặp cùng nhóm theo nhãn lúc sinh, B đếm theo nhãn STING và T đếm cặp cùng nhóm ở cả hai bộ nhãn. "
    "C(n, 2) là số cách chọn 2 điểm trong n điểm. Khi xáo nhãn STING và giữ kích thước các nhóm, E là số cặp cùng nhóm kỳ vọng. "
    "ARI lấy T trừ E rồi chia cho mốc chuẩn hóa (A + B)/2 − E. Kết quả của nhóm khoảng 0,9504.",
)


s = slide_new()
header(s, "ỨNG DỤNG", "Cùng dữ liệu PAPI, hai cách tạo cụm", 7)
text(s, 0.65, 1.26, 12.0, 0.34, [
    (f"{PAPI_COUNT} quan sát tỉnh–năm · 2011–2024 · Hai trục hiển thị theo z-score", 14, True, TEAL),
], align=PP_ALIGN.CENTER)
figure = comparison_figure(PAPI_Z, PAPI_GRID, PAPI_LABELS, KM_MODEL)
image = BytesIO()
figure.savefig(image, format="png", dpi=200)
plt.close(figure)
image.seek(0)
pic_bytes(s, image, 0.7, 1.64, w=11.9)
text(s, 0.65, 6.55, 12.0, 0.33, [
    ("STING nối các ô dày. Đường đứt ở hình K-means đi qua vị trí cách đều hai tâm.", 13, False, GREY),
], align=PP_ALIGN.CENTER)
note(
    s,
    f"Phân cụm mô tả dùng {PAPI_COUNT} quan sát đủ hai chỉ tiêu, gồm "
    f"{PAPI_COMPLETE.year.eq(2024).sum()} quan sát năm 2024. Bên trái, viền màu đánh dấu "
    f"các ô có ít nhất {GRID['min_count']} điểm. Bên phải, dấu X chỉ tâm cụm, mỗi điểm được gán "
    "cho tâm gần nhất. Đường đứt là ranh giới giữa hai nhóm do K-means tạo. "
    "Màu và tên cụm dùng riêng trong từng hình. Trục ngang là chỉ tiêu 4.2, trục dọc là chỉ tiêu 6.1. "
    "Giá trị z thể hiện khoảng cách tới trung bình của chỉ tiêu theo đơn vị độ lệch chuẩn.",
)


s = slide_new()
header(s, "ĐÁNH GIÁ", f"Vì sao STING có {PAPI_GRID.n_clusters_} cụm, K-means dùng k = {BEST_K}?", 8)
text(s, 0.6, 1.37, 12.16, 0.34, [
    (f"Số cụm và nhiễu trên {PAPI_COUNT} quan sát · Silhouette trên cùng {N_COMMON} điểm", 14, True, TEAL),
])
rows = [("Phương pháp", "Số cụm", "Điểm nhiễu", "Silhouette")]
for name, labels in (
    ("STING", PAPI_LABELS),
    (f"K-means (k={BEST_K})", KM_MODEL.labels_),
    ("K-means (k=3)", KM_MODELS[3].labels_),
    (f"DBSCAN (ε={DBSCAN_OPTIONS['eps']})", DB_LABELS),
):
    counts = Counter(labels)
    n_noise = counts.pop(-1, 0)
    rows.append((name, str(len(counts)), f"{n_noise} ({n_noise / PAPI_COUNT:.1%})",
                 f"{silhouette_score(PAPI_Z[COMMON], labels[COMMON]):.4f}"))
result_table(s, rows, 0.6, 1.9, [2.36, 1.05, 1.94, 1.92], 0.66, font_size=15)
text(s, 0.6, 5.43, 7.25, 1.07, [
    (f"{N_COMMON} điểm được cả ba cách gán cụm. Silhouette đo độ gọn và độ tách trên nhóm điểm này.",
     15, False, GREY),
])
largest_split = sorted(Counter(KM_MODEL.labels_[PAPI_LABELS == LARGEST]).values(), reverse=True)
split_text = " và ".join(map(str, largest_split))
rect(s, 8.19, 1.9, 4.56, 4.76, LIGHT)
bullets(
    s, 8.42, 2.13, 4.09, 4.13,
    [
        ("STING.", f"{sum(DENSE_COMPONENTS)} ô dày tạo {len(DENSE_COMPONENTS)} vùng kề cạnh, "
         f"gồm {', '.join(map(str, DENSE_COMPONENTS))} ô."),
        ("K-means.", f"Thử k = 2–5. k = {BEST_K} có silhouette cao nhất trên mẫu đầy đủ."),
        ("Đối chiếu.", f"K-means k = {BEST_K} chia vùng STING lớn nhất ({PAPI_SIZES[0]} điểm) "
         f"thành {split_text} điểm."),
    ],
    size=16, gap_pt=13,
)
note(
    s,
    f"STING dùng lưới {PAPI_GRID_SIZE} × {PAPI_GRID_SIZE} và ngưỡng {GRID['min_count']} điểm mỗi ô. "
    f"Quy tắc kề cạnh tạo {len(DENSE_COMPONENTS)} cụm. K-means cần đặt k trước khi chạy. "
    f"Trên {PAPI_COUNT} điểm, các kết quả K-means khi dò k là "
    + ", ".join(f"k={k} đạt {score:.4f}" for k, score in KM_SCORES.items())
    + f". Bảng trên slide giữ các nhãn đã có và tính silhouette Euclid trên cùng {N_COMMON} điểm "
      f"được cả STING, K-means và DBSCAN gán cụm. Trong {PAPI_COUNT} điểm, có {PAPI_NOISE} nhiễu STING, "
      f"{DBSCAN_NOISE} nhiễu DBSCAN và {BOTH_NOISE} điểm bị cả hai gắn nhãn nhiễu. "
      f"Trừ hợp của hai tập nhiễu được {N_COMMON} điểm. Cột số cụm và nhiễu lấy trên mẫu đầy đủ. "
      "K-means k=3 là đối chứng cùng số cụm với STING. Bảng chéo trong notebook cho thấy cách chia khác "
      "kể cả khi cùng có ba cụm. DBSCAN dùng ε=0,2 trên tọa độ z-score, với tối thiểu 5 điểm "
      "trong lân cận tính cả điểm đang xét. Silhouette mô tả hình học trên phần giao. "
      "Tỷ lệ nhiễu và kích thước cụm cho thấy phần còn lại của dữ liệu.",
)


s = slide_new()
header(s, "CHUẨN HÓA", "Z-score thay đổi điều gì?", 9)
rect(s, 2.74, 1.37, 7.86, 0.68, TEAL)
text(s, 2.74, 1.51, 7.86, 0.37, [
    (f"{PAPI_COUNT} quan sát · Chạy trên điểm gốc và điểm chuẩn hóa", 16, True, WHITE),
], align=PP_ALIGN.CENTER)
rect(s, 6.657, 2.05, 0.018, 0.25, TEAL)
rect(s, 2.55, 2.28, 8.25, 0.018, TEAL)

cards = (
    ("STING", "Ô dày chung cạnh, biên lưới theo min–max.",
     f"{SAME_BIN}/{PAPI_COUNT} điểm cùng ô", f"{SAME_LABEL} nhãn trùng · {PAPI_NOISE} điểm nhiễu"),
    ("K-means k = 2", "Khoảng cách Euclid đến tâm cụm.",
     f"{KMEANS2_CHANGED} điểm đổi cụm", f"Silhouette cùng thang z  {silhouette_score(PAPI_Z, KM2_RAW):.4f} → {KM_SCORES[2]:.4f}"),
    ("DBSCAN", "Lân cận ε, ít nhất 5 điểm.",
     f"{DB_NOISE_CHANGED} điểm đổi trạng thái nhiễu",
     f"{len(set(DB_RAW[DB_RAW >= 0]))} → {len(set(DB_LABELS[DB_LABELS >= 0]))} cụm  ·  "
     f"{int((DB_RAW == -1).sum())} → {int((DB_LABELS == -1).sum())} nhiễu"),
)
for index, (name, rule, result, detail) in enumerate(cards):
    x = 0.63 + index * 4.12
    arrow = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(x + 1.80), Inches(2.29),
                               Inches(0.24), Inches(0.39))
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = TEAL
    arrow.line.fill.background()
    rect(s, x, 2.68, 3.86, 2.73, LIGHT)
    text(s, x + 0.16, 2.82, 3.54, 0.38, [(name, 18, True, TEAL)])
    text(s, x + 0.16, 3.34, 3.54, 0.64, [(rule, 14.5, False, INK)])
    text(s, x + 0.16, 4.08, 3.54, 0.52, [(result, 16, True, NAVY)])
    text(s, x + 0.16, 4.76, 3.54, 0.53, [(detail, 13, False, GREY)])

code_box = rect(s, 0.63, 5.67, 12.10, 0.55, NAVY)
code_frame = code_box.text_frame
code_frame.word_wrap = False
code_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
code_frame.margin_left = Inches(0.20)
paragraph = code_frame.paragraphs[0]
paragraph.alignment = PP_ALIGN.LEFT
run = paragraph.add_run()
run.text = "print((idx_raw == idx_z).all(axis=1).sum())"
run.font.name = "Consolas"
run.font.size = Pt(14)
run.font.color.rgb = WHITE
text(s, 0.63, 6.42, 12.10, 0.44, [
    (f"DBSCAN dùng ε gốc ≈ {DB_EPS_RAW:.4f} và ε z = {DBSCAN_OPTIONS['eps']}. Xem 6 hình đối chiếu ở mục 4.6.",
     14, False, GREY),
])
threshold_line = ", ".join(f"{value} điểm/ô cho {SENSITIVITY[value]} cụm" for value in THRESHOLDS)
note(
    s,
    "Trên mỗi trục của STING, điểm và hai biên cùng đổi thang nên (x − min) / (max − min) giữ nguyên "
    "với trục có độ lệch chuẩn dương. K-means dùng khoảng cách đến tâm, ghép tên cụm 0/1 trước "
    "khi đếm điểm đổi nhóm. DBSCAN chạy với min_samples = 5. Vòng ε gốc có cùng diện tích với elip "
    "tương ứng của ε z nhưng khác hình dạng. Mục 4.6 hiển thị nhãn của cả hai lượt trên cùng tọa độ z. "
    f"Khảo sát ngưỡng STING. {threshold_line}. Mục 4.7 cũng giữ ngưỡng 5 "
    "và đổi riêng mức lưới để xem số cụm và số điểm nhiễu.",
)


s = slide_new()
header(s, "QUAN SÁT VÀ KẾT LUẬN", "Điểm PAPI năm 2024 trên lưới cố định", 10,
       "Notebook giữa kỳ §4.8 và §5 · PAPI 2011–2024")
assigned = PAPI_COUNT - PAPI_NOISE
assignments, n_reference = reference_grid_assignments(PAPI_PANEL, reference_year=2023)
observed_2024 = assignments.loc[assignments.year.eq(2024)]
clustered_2024 = observed_2024.loc[observed_2024.cluster.ge(0)]
outside_2024 = int(observed_2024.cluster.eq(-1).sum())
eligible_2024 = observed_2024.cluster.count()
occupied_cells = clustered_2024.grid_cell.nunique()
represented_clusters = clustered_2024.cluster.nunique()
eligible = assignments.dropna(subset=["cluster"])
paired = eligible.pivot(index="province_code", columns="year", values="cluster").dropna()
to_sparse = int((paired[2023].ge(0) & paired[2024].eq(-1)).sum())
to_cluster = int((paired[2023].eq(-1) & paired[2024].ge(0)).sum())
text(s, 0.6, 1.42, 12.0, 1.19, [
    (f"{len(clustered_2024)}/{eligible_2024} tỉnh nằm ở {occupied_cells} ô dày thuộc "
     f"{represented_clusters} cụm trên lưới 2011–2023.", 18, True, NAVY),
    (f"{n_reference} dòng dựng lưới. Năm 2024 có {outside_2024} tỉnh ở ô thưa và "
     f"{len(observed_2024) - eligible_2024} tỉnh thiếu chỉ tiêu.", 16, False, INK),
], space_after=7)
text(s, 0.6, 2.74, 12.0, 0.44, [
    ("Lạng Sơn chuyển từ ô thưa vào cụm lớn", 17, True, TEAL),
])
lang_son = assignments.loc[assignments.province_vi.eq("Lạng Sơn")].sort_values("year")
province_rows = [("Năm", "Điểm 4.2 / 6.1", "Ô lưới", "Số điểm tham chiếu", "Nhãn")]
for row in lang_son.itertuples(index=False):
    pair = f"{row.sd_4_2:.3f} / {row.sd_6_1:.3f}".replace(".", ",")
    label = "−1 (ô thưa)" if row.cluster == -1 else f"{row.cluster} (cụm lớn)"
    province_rows.append((row.year, pair, row.grid_cell, row.reference_count, label))
result_table(s, province_rows, 0.6, 3.2, [1.13, 2.73, 1.65, 3.4, 3.1], 0.61)
text(s, 0.6, 5.28, 12.12, 1.02, [
    (f"Ghép cùng {len(paired)} tỉnh. {to_sparse} tỉnh sang ô thưa, {to_cluster} tỉnh từ ô thưa vào cụm.", 16, True, NAVY),
    (f"Lưới mô tả {PAPI_COUNT} dòng có cụm lớn {PAPI_SIZES[0]}/{assigned} điểm đã vào cụm "
     f"và {PAPI_NOISE / PAPI_COUNT:.1%} điểm ở ô thưa.", 15, False, GREY),
], space_after=7)
text(s, 0.60, 6.48, 12.1, 0.36, [
    ("Wang, Yang & Muntz (VLDB 1997) · CECODES, VFF-CRT, RTA và UNDP (papi.org.vn)", 13, False, GREY),
])
note(
    s,
    "Bảng dùng dữ liệu đã quan sát, với scaler và lưới chung từ 2011–2023. "
    "Mục 4.8 tính mã ô, số quan sát tham chiếu và nhãn cho từng tỉnh. "
    "48 tỉnh vào cụm lớn, 13 tỉnh đủ điểm ở ô thưa, Vĩnh Phúc và Tiền Giang thiếu chỉ tiêu. "
    "Ghép theo province_code. Quảng Ninh và Bình Dương thiếu điểm 2023 nên chỉ có 59 tỉnh ở mẫu ghép. "
    "Ô (12, 10) của Lạng Sơn có 12 điểm tham chiếu ở lưới này. Mục 4.3 đếm 17 điểm trong cùng "
    "chỉ số ô trên lưới mô tả gồm cả dữ liệu 2024. Điểm 4.2 của Lạng Sơn giảm và 6.1 tăng. "
    "Số đếm theo cụm phụ thuộc vào hai trục PAPI đã chọn và cấu hình lưới. "
    "Nguồn phương pháp https://www.vldb.org/conf/1997/P186.PDF và nguồn dữ liệu https://papi.org.vn/du-lieu-papi/",
)


s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
text(s, 0.55, 3.1, 12.23, 1.2, [
    ("Cảm ơn thầy và các bạn đã lắng nghe", 40, True, GOLD),
], align=PP_ALIGN.CENTER)
note(s, "Nhóm em cảm ơn thầy và các bạn đã lắng nghe. Nhóm sẵn sàng trả lời câu hỏi.")


OUT.parent.mkdir(parents=True, exist_ok=True)
n_slides = len(prs.slides)
assert n_slides == TOTAL, f"expected {TOTAL} slides, got {n_slides}"
prs.save(str(OUT))
print("saved:", OUT)
print("slides:", n_slides)
