"""Build slides/submission.pptx — đúng 10 trang 16:9, tiếng Việt, ghi chú người nói.

Cách dùng: python scripts/build_slides_10.py
"""
from __future__ import annotations

import csv
import re
import sys
from io import BytesIO
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "scripts"))

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score

from fig_style import PALETTE, style_context
from sting import STING

ROOT = _ROOT
FIGS = ROOT / "results" / "figs"
OUT = ROOT / "slides" / "submission.pptx"
TOTAL = 10

# Số liệu đọc từ artifact (không hardcode số đo phân cụm)


def _read_results_csv(name: str) -> list[dict[str, str]]:
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pct(v: str | float) -> str:
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


def _f3(v: str | float) -> str:
    return f"{float(v):.3f}"


def _metric_row(method_sub: str) -> dict[str, str]:
    for r in _read_results_csv("metrics.csv"):
        if method_sub in r["method"]:
            return r
    raise KeyError(method_sub)


M_STING = _metric_row("STING (frozen)")
M_KM2 = _metric_row("k-means k=2")
M_DB = _metric_row("DBSCAN eps=0.2")

# Số đo tiền xử lý — đọc từ audit Day 4, không gõ tay.
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


PP_FACTS = (
    f"Đo trên PAPI: {N_DUP}/{N_ROWS} dòng trùng khóa · "
    f"{_sp(N_MISS)}/{_sp(N_CELLS)} ô thiếu ({100 * N_MISS / N_CELLS:.1f}%) giữ NaN, không nội suy · "
    f"{N_OUT} ô |z|>{Z_OUT} chỉ đánh dấu, không xóa"
)

# Demo tổng hợp — tái lập test_two_blobs (assert khớp hình 00_synthetic_sting.png)
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


def text_line(slide, x, y, w, h, spans, size=12.0, align=PP_ALIGN.LEFT):
    """Một dòng nhiều run khác định dạng (dải quy trình, nhấn tên bước)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    for t, bold, color in spans:
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = "Calibri"
    return tb


def header(slide, kicker, title, page_no):
    rect(slide, 0, 0, SW, 0.16, TEAL)
    text(slide, 0.55, 0.32, 10.5, 0.3, [(kicker, 12, True, TEAL)])
    text(slide, 0.55, 0.58, 12.2, 0.75, [(title, 26, True, NAVY)])
    rect(slide, 0.55, SH - 0.42, SW - 1.1, 0.012, RGBColor(0xD8, 0xD5, 0xCC))
    text(
        slide, 0.55, SH - 0.36, 9.5, 0.3,
        [("Topic 6 · STING × PAPI 2011–2024 · Nhóm 15", 10, False, GREY)],
    )
    text(
        slide, SW - 1.6, SH - 0.36, 1.1, 0.3,
        [(f"{page_no:02d} / {TOTAL}", 10, True, GREY)],
        align=PP_ALIGN.RIGHT,
    )


def note(slide, text_md: str):
    slide.notes_slide.notes_text_frame.text = text_md


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


# 1 — Bìa + thesis
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
for r in range(4):
    for c in range(4):
        x0, y0 = SW - 4.6 + c * 0.78, 1.05 + r * 0.78
        fill = GOLD if (r, c) in ((1, 1), (2, 2)) else RGBColor(0x1E, 0x3D, 0x5E)
        rect(s, x0, y0, 0.66, 0.66, fill)
text(s, 0.85, 1.15, 7.6, 0.4, [("HỌC MÁY · BÁO CÁO GIỮA KỲ", 13, True, GOLD)])
text(
    s, 0.85, 1.75, 8.6, 2.6,
    [
        ("Phân cụm dựa trên lưới", 40, True, WHITE),
        ("với thuật toán STING", 30, True, WHITE),
    ],
)
text(
    s, 0.85, 4.5, 8.4, 1.8,
    [
        ("Demo thuật toán và ứng dụng trên dữ liệu PAPI", 17, True, GOLD),
        ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 14, False, RGBColor(0xB9, 0xCD, 0xDE)),
        ("Nhóm 15 · Chủ đề 6 · Grid-based clustering", 13, False, RGBColor(0xB9, 0xCD, 0xDE)),
    ],
)
note(
    s,
    "Kính thưa thầy, nhóm 15 phụ trách chủ đề phân cụm dựa trên lưới và chọn thuật toán STING. "
    "Nhóm minh họa bằng lưới 3 × 3 và dữ liệu giả lập để giải thích cách đếm điểm, chọn ô dày "
    "và tạo cụm. Nhóm cũng đã chuẩn bị dữ liệu PAPI để minh họa thêm phần ứng dụng.",
)

# 2 — Bài toán & dữ liệu
s = slide_new()
header(s, "CHỦ ĐỀ VÀ DỮ LIỆU", "Grid-based clustering, STING và dữ liệu PAPI", 2)
bullets(
    s, 0.55, 1.45, 6.5, 4.15,
    [
        ("Chủ đề.", "Grid-based clustering — phân cụm dựa trên lưới."),
        ("Thuật toán.", "Nhóm chọn biến thể STING dùng ngưỡng số điểm trong ô."),
        ("Demo.", "Lưới 3 × 3 và dữ liệu giả lập có nhãn tham chiếu."),
        ("Ứng dụng.", "Dữ liệu PAPI. Mỗi quan sát là một tỉnh trong một năm."),
    ],
    size=15, gap_pt=32,
)
rect(s, 7.4, 1.4, 5.35, 4.22, LIGHT)
text(s, 7.65, 1.52, 4.9, 0.32, [("DỮ LIỆU PAPI ĐÃ CHUẨN BỊ", 12, True, TEAL)])
for i, (lbl, val) in enumerate([("Quan sát tỉnh–năm", "882"), ("Số cột", "41"), ("Giai đoạn", "2011–2024")]):
    y = 2.0 + i * 1.02
    rect(s, 7.65, y, 4.85, 0.86, WHITE)
    text(s, 7.8, y + 0.08, 3.2, 0.7, [(lbl, 12.5, False, GREY), (val, 21, True, NAVY)])
text(
    s, 7.65, 5.02, 4.85, 0.55,
    [("Hai chỉ tiêu dùng cho phân cụm được chuẩn hóa bằng thống kê của tập huấn luyện.", 12.5, False, GREY)],
)

# Dải tiền xử lý Day 4 — thứ tự dạy học + số đo audit, đọc từ preprocessing_audit.csv.
rect(s, 0.55, 5.7, 12.23, 1.2, LIGHT)
text(s, 0.72, 5.73, 11.8, 0.38, [
    ("TIỀN XỬ LÝ DỮ LIỆU", 12, True, TEAL),
])
text_line(
    s, 0.72, 6.11, 11.9, 0.33,
    [
        ("Làm sạch", True, NAVY),
        (" (trùng khóa, thiếu dữ liệu, ngoại lai)", False, INK),
        ("  →  ", False, GREY),
        ("Tích hợp", True, NAVY),
        (" (mã tỉnh, năm)", False, INK),
        ("  →  ", False, GREY),
        ("Biến đổi", True, NAVY),
        (" (chuẩn hóa)", False, INK),
    ],
    size=13,
)
text(s, 0.72, 6.49, 11.9, 0.34, [(PP_FACTS, 11, False, GREY)])
note(
    s,
    "Grid-based clustering là chủ đề chung. STING là thuật toán nhóm chọn, còn PAPI là dữ liệu ứng dụng. "
    "Giữa kỳ tập trung vào định nghĩa và demo cơ bản. Phần PAPI cho thấy hướng ứng dụng đã chuẩn bị. "
    "Bảng dữ liệu có 882 quan sát và 41 cột. Một điểm ứng với một tỉnh trong một năm, "
    "được biểu diễn bằng hai chỉ tiêu PAPI đã chuẩn hóa. Nguồn PAPI do CECODES, VFF-CRT, RTA và UNDP công bố. "
    "Nhóm kiểm tra trùng khóa tỉnh–năm, dữ liệu thiếu, tính nhất quán và ngoại lai, "
    "sau đó ghép dữ liệu theo mã tỉnh và chuẩn hóa. Các ô thiếu được giữ để ghi nhận "
    "độ phủ. Bước phân cụm chỉ dùng những dòng có đủ hai chỉ tiêu được chọn. "
    "Thống kê chuẩn hóa được ước lượng từ tập huấn luyện.",
)

# 3 — Các mức lưới
s = slide_new()
header(s, "LƯỚI THỐNG KÊ", "Lưới từ thô đến mịn", 3)
pic_bytes(s, _sting_hierarchy_figure_png(_syn_model, _X_SYN), 0.55, 1.32, w=SW - 1.1)
_, example_cell = _callout_cell(_syn_model, level=2)
bullets(
    s, 0.75, 5.02, 11.8, 1.76,
    [
        ("Cùng một tập điểm.", "Mức sau chia mỗi ô thành những ô nhỏ hơn."),
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

# 4 — Quy tắc gom cụm
s = slide_new()
header(s, "CƠ CHẾ", "Biến thể STING tạo cụm từ các ô dày", 4)
steps = [
    ("1. Đếm điểm", "Chọn một mức lưới và đọc số điểm trong từng ô."),
    ("2. Chọn ô dày", "Đánh dấu ô có số điểm đạt ngưỡng đã chọn."),
    ("3. Nối qua cạnh", "Các ô dày nối được qua cạnh thuộc cùng một cụm."),
]
for i, (title, description) in enumerate(steps):
    x = 0.6 + i * 4.12
    rect(s, x, 2.03, 3.86, 2.25, LIGHT)
    text(s, x + 0.2, 2.28, 3.46, 0.55, [(title, 21, True, TEAL)])
    text(s, x + 0.2, 3.03, 3.46, 0.95, [(description, 17, False, INK)])
text(s, 0.6, 4.95, 12.1, 0.52, [
    ("Điểm trong ô thưa nhận nhãn −1, tức nhiễu.", 19, True, NAVY),
])
note(
    s,
    "Trong cài đặt của nhóm, một ô được xem là dày khi số điểm trong ô đạt min_count. "
    "Tại mức lưới đã chọn, các ô dày liên thông qua cạnh được gom thành cụm. "
    "Điểm trong ô thưa nhận nhãn nhiễu −1. Đây là biến thể STING dùng ngưỡng số đếm. "
    "STING gốc còn mô hình hóa phân phối và dùng kiểm định thống kê để duyệt lưới từ trên xuống.",
)

# 5 — Đọc một lưới mẫu
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
text(s, 5.88, 2.17, 6.48, 0.52, [("Ngưỡng ô dày là 3 điểm", 21, True, NAVY)])
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
text(s, 0.85, 6.3, 11.8, 0.42, [
    ("Hai vùng màu chỉ chạm góc nên tách thành 2 cụm.", 17, True, NAVY),
])
note(
    s,
    "Ví dụ có 15 điểm và ngưỡng ô dày bằng 3. Cặp ô chứa 4 và 3 điểm ở hàng trên tạo cụm A. "
    "Cặp ô bên phải tạo cụm B. Hai vùng này chỉ chạm góc, nên với quy tắc nối qua cạnh "
    "chúng thuộc hai cụm khác nhau. Điểm trong ô chứa 1 điểm nhận nhãn nhiễu.",
)

# 6 — Kiểm tra trên dữ liệu giả lập
s = slide_new()
header(s, "DỮ LIỆU GIẢ LẬP", "Đối chiếu kết quả với hai cụm đã biết", 6)
pic(s, "00_synthetic_sting.png", 0.55, 1.55, h=4.65)
bullets(
    s, 7.85, 1.73, 4.9, 4.6,
    [
        ("Dữ liệu.", "240 điểm, biết trước hai cụm khi sinh dữ liệu."),
        ("Kết quả.", f"STING tìm {SYN_K} cụm, nhiễu {_pct(SYN_NOISE)}."),
        ("Độ khớp.", f"ARI {SYN_ARI_S} khi so với nhãn giả lập."),
    ],
    size=17, gap_pt=33,
)
note(
    s,
    "Với 240 điểm sinh từ hai phân bố Gauss, STING tìm được hai cụm và đánh dấu 2,5% điểm là nhiễu. "
    "ARI bằng 0,950 đo mức khớp giữa kết quả và nhãn đã biết khi sinh dữ liệu. "
    "Phép thử này kiểm tra cách cài đặt trên ví dụ có nhãn tham chiếu.",
)

# 7 — Ứng dụng PAPI
s = slide_new()
header(s, "ỨNG DỤNG", "Cùng dữ liệu PAPI, hai cách đặt lưới", 7)
pic(s, "sting_first_real.png", 0.55, 1.45, h=4.2)
bullets(
    s, 7.95, 1.57, 4.75, 4.8,
    [
        ("Dữ liệu 2023.", "61 tỉnh đủ hai chỉ tiêu được chọn."),
        ("Lưới 3 × 3.", "Ngưỡng 5, tìm 1 cụm và 10% nhiễu."),
        ("Lưới 9 × 9.", "Ngưỡng 2, tìm 3 cụm và 31% nhiễu."),
        ("Gán dữ liệu mới.", "Dùng lưới học từ 2011–2023 cho năm 2024."),
    ],
    size=16, gap_pt=26,
)
note(
    s,
    "Năm 2023 có 61 tỉnh đủ hai chỉ tiêu. Cấu hình lưới 3×3 với ngưỡng 5 cho một cụm và khoảng 10% nhiễu. "
    "Cấu hình 9×9 với ngưỡng 2 cho ba cụm và khoảng 31% nhiễu. Hai cấu hình thay đổi cả "
    "độ phân giải và ngưỡng mật độ. Phần sau khảo sát riêng ngưỡng mật độ.",
)

# 8 — Đối chứng phân cụm
s = slide_new()
header(s, "ĐÁNH GIÁ", "Kết quả STING và hai đối chứng", 8)
rows = [("Phương pháp", "Số cụm", "Nhiễu", "Silhouette")]
for label, result in [("STING", M_STING), ("K-means (k=2)", M_KM2), ("DBSCAN (ε=0.2)", M_DB)]:
    rows.append((label, result["k"], _pct(result["noise_ratio"]), _f3(result["silhouette"])))
tb = s.shapes.add_table(
    len(rows), 4, Inches(0.6), Inches(1.85), Inches(7.2), Inches(2.8)
).table
for j, width in enumerate([2.65, 1.2, 1.25, 2.1]):
    tb.columns[j].width = Inches(width)
for i, row in enumerate(rows):
    for j, value in enumerate(row):
        cell = tb.cell(i, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.text_frame.text = value
        run = cell.text_frame.paragraphs[0].runs[0]
        run.font.name = "Calibri"
        run.font.size = Pt(17)
        run.font.bold = i == 0
        run.font.color.rgb = WHITE if i == 0 else INK
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL if i == 0 else WHITE if i % 2 else LIGHT
text(s, 0.6, 4.98, 7.2, 0.6, [
    ("Hai chỉ tiêu PAPI · gộp 2011–2023", 14, False, GREY),
])
rect(s, 8.2, 1.85, 4.53, 3.75, LIGHT)
bullets(
    s, 8.43, 2.03, 4.0, 3.2,
    [
        ("K-means.", "Ấn định số cụm và gán mọi điểm."),
        ("STING và DBSCAN.", "Có thể đánh dấu ngoại vi là nhiễu."),
        ("Cách đọc.", "Xem silhouette cùng tỷ lệ nhiễu."),
    ],
    size=16, gap_pt=19,
)
note(
    s,
    "Ba phương pháp cùng dùng hai chỉ tiêu và giai đoạn 2011–2023. STING cho ba cụm "
    "với 19,6% nhiễu, K-means cho hai cụm và DBSCAN cho năm cụm ở các cấu hình đã nêu. "
    "Silhouette được tính trên điểm đã vào cụm, vì vậy mỗi phương pháp có thể được đánh giá "
    "trên tập điểm khác nhau. Khi so sánh cần đọc cùng tỷ lệ nhiễu.",
)

text(s, 0.65, 6.15, 12.0, 0.4, [("Silhouette tính trên điểm thuộc cụm; tập điểm của các phương pháp có thể khác nhau.", 12, False, GREY)])

# 9 — Tham số và giới hạn
s = slide_new()
header(s, "THAM SỐ", "Ngưỡng ô dày thay đổi kết quả ra sao?", 9)
rect(s, 0.6, 1.65, 6.1, 4.6, LIGHT)
text(s, 0.84, 1.86, 5.5, 0.55, [("THỬ TRÊN NOTEBOOK", 16, True, TEAL)])
bullets(
    s, 0.84, 2.55, 5.55, 3.5,
    [
        ("Giữ lưới cố định.", "Chỉ đổi ngưỡng số điểm tối thiểu mỗi ô."),
        ("Thử 3, 5 và 8.", "So số cụm và tỷ lệ tỉnh năm 2024 vào vùng dày."),
        ("Cách hiểu.", "Ngưỡng cao hơn làm ít ô đạt điều kiện dày hơn."),
    ],
    size=17, gap_pt=24,
)
text(s, 7.06, 1.86, 5.4, 0.55, [("GIỚI HẠN KẾT LUẬN", 16, True, TEAL)])
bullets(
    s, 7.06, 2.55, 5.45, 3.5,
    [
        ("Đặc trưng.", "Kết quả mô tả hai chỉ tiêu PAPI được chọn."),
        ("Dữ liệu thực.", "Một cụm lớn và hai cụm rất nhỏ."),
        ("Năm 2024.", "Minh họa gán điểm mới vào lưới đã học."),
    ],
    size=17, gap_pt=24,
)
note(
    s,
    "Khi giữ nguyên đặc trưng, biên và mức lưới, nhóm thử các ngưỡng 3, 5 và 8. "
    "Tỷ lệ tỉnh năm 2024 được gán vào cụm lần lượt khoảng 82%, 79% và 70%. "
    "Kết quả cho thấy việc chọn ngưỡng ảnh hưởng đến độ phủ. Cấu hình chính được chọn "
    "từ dữ liệu các năm trước, sau đó mới dùng để gán cụm cho năm 2024.",
)

# 10 — Kết luận
s = slide_new()
header(s, "KẾT LUẬN", "Kết quả thực nghiệm với STING", 10)
bullets(
    s, 0.55, 1.5, 12.0, 4.1,
    [
        ("Cài đặt.", "STING chia lưới, lưu thống kê ô và gom các ô dày liên thông."),
        ("PAPI 2011–2023.", "Trên hai chỉ tiêu đã chọn, có một cụm lớn gồm 629 điểm và hai cụm nhỏ gồm 16 và 5 điểm."),
        ("Đánh giá.", "Cần xem số cụm cùng kích thước cụm, tỷ lệ nhiễu và độ nhạy tham số."),
    ],
    size=16, gap_pt=42,
)
text(s, 0.6, 6.0, 12.1, 0.55, [("Cảm ơn thầy và các bạn đã lắng nghe", 20, True, NAVY)], align=PP_ALIGN.CENTER)
note(
    s,
    "Qua thực nghiệm, STING minh họa cách phân cụm bằng các ô dày liên thông. "
    "Trên hai chỉ tiêu PAPI giai đoạn 2011–2023, các cụm có kích thước chênh lệch lớn. "
    "Vì vậy, số cụm cần được đọc cùng tỷ lệ nhiễu và độ nhạy tham số. "
    "Nhóm xin kết thúc phần trình bày và cảm ơn thầy và các bạn đã lắng nghe. "
    "Nguồn phương pháp là Wang, Yang và Muntz, VLDB 1997. Nguồn dữ liệu là PAPI "
    "và gói đối chiếu Le cùng cộng sự, DOI 10.17632/wbk42j9wc8.1.",
)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
n_slides = len(prs.slides._sldIdLst)
assert n_slides == TOTAL, f"expected {TOTAL} slides, got {n_slides}"
print("saved:", OUT)
print("slides:", n_slides)
