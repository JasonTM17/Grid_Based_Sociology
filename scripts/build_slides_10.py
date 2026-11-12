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

# ==== Số liệu đọc từ artifact (không hardcode số đo clustering / supervised) ====


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


ROBUSTNESS = _read_results_csv("robustness.csv")


def _rob(branch_sub: str) -> dict[str, str]:
    for r in ROBUSTNESS:
        if branch_sub in r["branch"]:
            return r
    raise KeyError(branch_sub)


R_PCA = _rob("PCA(2)")
R_GOC = _rob("(gốc OFAT)")
R_F3 = _rob("OFAT f=3")
R_MC2 = _rob("OFAT mc=2")
R_LV2 = _rob("OFAT lv=2")

SUP_ROWS = _read_results_csv("supervised_metrics.csv")


def _reg_cv(model_sub: str) -> str:
    for r in SUP_ROWS:
        if r["task"] == "regression" and model_sub in r["model"]:
            return r["value_cv"].strip()
    raise KeyError(model_sub)


def _reg_holdout_mae(model_sub: str) -> str:
    for r in SUP_ROWS:
        if r["task"] == "regression" and model_sub in r["model"]:
            return r["holdout_mae"].strip()
    raise KeyError(model_sub)


CV_CARRY = _reg_cv("carry-forward")
CV_RIDGE = _reg_cv("ridge")
MAE_CARRY = _reg_holdout_mae("carry-forward")
MAE_RIDGE = _reg_holdout_mae("ridge")
MAE_RF = _reg_holdout_mae("random forest")

M_STING = _metric_row("STING (frozen)")
M_KM2 = _metric_row("k-means k=2")
M_KM3 = _metric_row("k-means k=3")
M_DB = _metric_row("DBSCAN eps=0.2")

# Bảng classifier theo nội dung học phần (Day 2–3): nhãn pseudo-label STING.
COURSE_CLF = _read_results_csv("course_supervised_baselines.csv")
COURSE_METRIC = "f1_macro (expanding origin 2017–2022)"
# Tên hiển thị trên slide; khoá là tên model trong CSV.
COURSE_LABELS = (
    ("majority", "majority"),
    ("gaussian naive bayes", "Naive Bayes"),
    ("knn", "KNN"),
    ("svm (linear)", "SVM tuyến tính"),
    ("svm (rbf)", "SVM RBF"),
    ("decision tree", "Cây quyết định"),
    ("random forest", "Random forest"),
)


def _course_row(model_sub: str) -> dict[str, str]:
    hits = [r for r in COURSE_CLF if model_sub in r["model"]]
    if len(hits) != 1:
        raise KeyError(f"{model_sub}: {len(hits)} dòng trong course_supervised_baselines.csv")
    return hits[0]


assert all(r["metric_cv"] == COURSE_METRIC for r in COURSE_CLF), (
    "course_supervised_baselines.csv: cột metric_cv đã đổi"
)
COURSE_ROWS = []
for _key, _label in COURSE_LABELS:
    _row = _course_row(_key)
    COURSE_ROWS.append((_label, _f3(_row["value_cv"]), _f3(_row["holdout_macro_f1"])))

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


def _fmt_cell_callout(cell) -> list[str]:
    m0, m1 = float(cell.mean[0]), float(cell.mean[1])
    s0, s1 = float(cell.std[0]), float(cell.std[1])
    lo0, lo1 = float(cell.min_[0]), float(cell.min_[1])
    hi0, hi1 = float(cell.max_[0]), float(cell.max_[1])
    return [
        f"n = {cell.count}",
        f"μ = ({m0:.2f}, {m1:.2f})",
        f"σ = ({s0:.3f}, {s1:.3f})",
        f"min = ({lo0:.2f}, {lo1:.2f})",
        f"max = ({hi0:.2f}, {hi1:.2f})",
        "loại phân phối: bỏ (đơn giản hóa)",
    ]


_CALLOUT_KEY, _CALLOUT_CELL = _callout_cell(_syn_model, level=2)
CALLOUT_LINES = _fmt_cell_callout(_CALLOUT_CELL)

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


def _cell_counts_2d(X: np.ndarray, lo: np.ndarray, hi: np.ndarray, res: int) -> dict[tuple[int, int], int]:
    span = hi - lo
    idx = np.floor((X - lo) / span * res).astype(np.int64)
    np.clip(idx, 0, res - 1, out=idx)
    counts: dict[tuple[int, int], int] = {}
    for i in range(X.shape[0]):
        key = (int(idx[i, 0]), int(idx[i, 1]))
        counts[key] = counts.get(key, 0) + 1
    return counts


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
        for ax, (res, title) in zip(axes, panels):
            counts = _cell_counts_2d(X, lo, hi, res)
            max_c = max(counts.values()) if counts else 1
            step = span / res
            for (ix, iy), cnt in counts.items():
                x0, y0 = lo[0] + ix * step[0], lo[1] + iy * step[1]
                alpha = min(0.1 + 0.65 * (cnt / max_c), 0.85)
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
                    f"ô cha → {f ** 2} ô con",
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


# ---------- 1 — Bìa + thesis ----------
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
for r in range(4):
    for c in range(4):
        x0, y0 = SW - 4.6 + c * 0.78, 1.05 + r * 0.78
        fill = GOLD if (r, c) in ((1, 1), (2, 2)) else RGBColor(0x1E, 0x3D, 0x5E)
        rect(s, x0, y0, 0.66, 0.66, fill)
text(s, 0.85, 1.15, 7.6, 0.4, [("ĐỒ ÁN MÔN HỌC MÁY · TRÌNH BÀY 15'", 13, True, GOLD)])
text(
    s, 0.85, 1.75, 8.6, 2.6,
    [
        ("STING trên dữ liệu PAPI", 40, True, WHITE),
        ("Lý thuyết grid-based + minh họa 63 tỉnh × 14 năm", 26, True, WHITE),
    ],
)
text(
    s, 0.85, 4.5, 8.4, 1.8,
    [
        ("Luận điểm: dữ liệu PAPI cấp tỉnh/năm rất đồng nhất — nhóm báo cáo trung thực.", 14, True, GOLD),
        ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 12, False, RGBColor(0xB9, 0xCD, 0xDE)),
        ("Topic 6 · Grid-based clustering · Sociology", 12, False, RGBColor(0xB9, 0xCD, 0xDE)),
    ],
)
note(
    s,
    "Mở đầu ~20 giây: giới thiệu nhóm và đề tài. Thesis trung tâm: PAPI không cho cấu trúc cụm "
    "tách mạnh ở cấp tỉnh — đó là phát hiện, không phải thất bại. Hứa với GV: mọi con số lấy từ "
    "results/ và model đã audit; phần notebook tách riêng. Chuyển sang bài toán.",
)

# ---------- 2 — Bài toán & dữ liệu ----------
s = slide_new()
header(s, "BÀI TOÁN", "Phân cụm tỉnh theo PAPI — panel 882 × 41", 2)
bullets(
    s, 0.55, 1.45, 6.5, 4.15,
    [
        ("Mục tiêu.", "Khám phá cấu trúc không gian chỉ tiêu hành chính; so STING với baseline; dự đoán/giám sát holdout."),
        ("Phạm vi.", "63 tỉnh × 14 năm (2011–2024) → 882 quan sát; 41 cột (d1–d8 + 29 sub-dim; 39 số)."),
        ("Nguồn.", "PAPI (CECODES/VFF-CRT/RTA/UNDP) — audit 0.0→NaN, PROVENANCE trong repo."),
        ("Grid-based.", "Không giả định hình dạng cụm; mỗi ô lưới lưu thống kê — phù hợp dữ liệu không gian/tabular."),
    ],
    size=15, gap_pt=32,
)
rect(s, 7.4, 1.4, 5.35, 4.22, LIGHT)
text(s, 7.65, 1.52, 4.9, 0.32, [("MA TRẬN DỮ LIỆU", 12, True, TEAL)])
for i, (lbl, val) in enumerate([("Hàng (tỉnh×năm)", "882"), ("Cột", "41"), ("Số đo chính", "≥500×10 ✓")]):
    y = 2.0 + i * 1.02
    rect(s, 7.65, y, 4.85, 0.86, WHITE)
    text(s, 7.8, y + 0.08, 3.2, 0.7, [(lbl, 12.5, False, GREY), (val, 21, True, NAVY)])
text(
    s, 7.65, 5.02, 4.85, 0.55,
    [("Minh họa thuật toán: tập 2-D tổng hợp · Ứng dụng: chuẩn hóa trong-năm + lưới STING", 12.5, False, GREY)],
)

# Dải tiền xử lý Day 4 — thứ tự dạy học + số đo audit, đọc từ preprocessing_audit.csv.
rect(s, 0.55, 5.7, 12.23, 1.2, LIGHT)
text(s, 0.72, 5.74, 11.8, 0.26, [
    ("TIỀN XỬ LÝ THEO DAY 4 — MỖI BƯỚC: TEST → DECIDE", 11, True, TEAL),
])
text_line(
    s, 0.72, 5.99, 11.9, 0.34,
    [
        ("Làm sạch", True, NAVY),
        (" (trùng khóa → thiếu → nhất quán → ngoại lai, để cuối)", False, INK),
        ("  →  ", False, GREY),
        ("Tích hợp", True, NAVY),
        (" (join, rò rỉ)", False, INK),
        ("  →  ", False, GREY),
        ("Biến đổi", True, NAVY),
        (" (scale)", False, INK),
    ],
    size=13,
)
text(s, 0.72, 6.36, 11.9, 0.34, [(PP_FACTS, 11, False, GREY)])
note(
    s,
    "Giải thích vì sao đủ lớn cho đồ án: 882 dòng vượt chuẩn. Nhấn đây là dữ liệu thật đã làm sạch, "
    "không phải toy CSV. Dải dưới theo đúng thứ tự Day 4: làm sạch (trùng khóa trước, ngoại lai để cuối) "
    "→ tích hợp (join one-to-one, kiểm tra rò rỉ) → biến đổi (scale đóng băng); mỗi bước Test → Decide, "
    "số đo đọc từ results/preprocessing_audit.csv. 1.5 phút: liên hệ Topic 6 grid-based.",
)

# ---------- 3 — STING lý thuyết I ----------
FIG3_W = SW - 1.1
FIG3_H = FIG3_W * (3.35 / 12.2)
FIG3_Y = 1.32
FIG3_BOT = FIG3_Y + FIG3_H
s = slide_new()
header(s, "LÝ THUYẾT I", "STING — lưới thống kê phân cấp", 3)
_hier_png = _sting_hierarchy_figure_png(_syn_model, _X_SYN)
pic_bytes(s, _hier_png, 0.55, FIG3_Y, w=FIG3_W)
_btm_h = SH - 0.42 - FIG3_BOT - 0.08
bullets(
    s, 0.55, FIG3_BOT + 0.1, 7.35, _btm_h,
    [
        ("Ý tưởng.", "Chia không gian đa chiều thành lưới lồng nhau; không cần k cố định trước."),
        ("Ô lưới.", "Mỗi ô lưu n, μ, σ, min, max; bỏ loại phân phối (đơn giản hóa) — quét O(n) mỗi mức."),
        ("Minh họa.", "Scatter 2-D tổng hợp (240 điểm, seed 42) — thống kê ô từ STING.fit."),
        ("Tham số (slide 5).", "n_levels=3 · factor=4 · min_count=3."),
    ],
    size=14, gap_pt=14,
)
rect(s, 8.15, FIG3_BOT + 0.08, 4.65, _btm_h, WHITE, line=TEAL)
text(s, 8.3, FIG3_BOT + 0.18, 4.35, 0.32, [
    ("Thống kê một ô (level 2)", 14, True, NAVY),
])
_stats_lines = CALLOUT_LINES
text(
    s, 8.3, FIG3_BOT + 0.48, 4.35, _btm_h - 0.55,
    [(ln, 14, False, INK) for ln in _stats_lines],
)
note(
    s,
    "Dùng sơ đồ bên phải: chỉ tay từ mức thô xuống mịn. Giải thích ô dày đủ thống kê. "
    "Gốc STING lưu thêm loại phân phối; Cell trong src/sting.py chỉ count/mean/std/min/max. "
    "fit() xây lưới lần lượt từng mức trực tiếp từ điểm, không duyệt top-down cắt tỉa như VLDB 1997. "
    "~90 giây.",
)

# ---------- 4 — STING lý thuyết II ----------
s = slide_new()
header(s, "LÝ THUYẾT II", "Gom cụm · truy vấn vùng · độ phức tạp", 4)
steps = [
    (
        "TRUY VẤN",
        "query_rect: gộp thống kê ô\nnằm trọn trong vùng —\ntại một level đã chọn.",
        "Không duyệt cây top-down\ncắt tỉa như STING gốc.",
    ),
    (
        "GOM CỤM",
        "Ô dày (count ≥ min_count)\nliền kề → một cụm;\nđiểm ô thưa → nhiễu (−1).",
        "Một level cố định: DFS\nô dense + connectivity.",
    ),
    (
        "STING GỐC",
        "VLDB 1997: top-down —\nkiểm định độ tin cậy,\nchỉ hạ vào ô con liên quan.",
        "Ta: từng mức dựng từ điểm;\ncluster/query chọn level L.",
    ),
]
for i, (title, body, step) in enumerate(steps):
    x0 = 0.55 + i * 4.19
    rect(s, x0, 1.45, 3.85, 0.5, TEAL)
    text(s, x0, 1.48, 3.85, 0.38, [(title, 14, True, WHITE)], align=PP_ALIGN.CENTER)
    rect(s, x0, 1.95, 3.85, 1.75, LIGHT)
    text(
        s, x0 + 0.18, 2.08, 3.5, 1.55,
        [(body, 14, False, INK), (step, 13, True, TEAL)],
    )
cmp_rows = [
    ("Phương pháp", "Độ phức tạp", "Giả định chính"),
    ("STING", "O(n) xây lưới + gom ô", "Không cố định k; hình dạng cụm tự do"),
    ("k-means", "O(n·k·i)", "k cho trước; cụm gần cầu"),
    ("DBSCAN", "O(n log n) (index)", "Mật độ đồng nhất; ε, minPts"),
]
tb4 = s.shapes.add_table(
    len(cmp_rows), 3, Inches(0.55), Inches(3.85), Inches(12.23), Inches(1.55)
).table
for c, wd in enumerate([2.4, 2.85, 6.85]):
    tb4.columns[c].width = Inches(wd)
for i, row in enumerate(cmp_rows):
    for j, v in enumerate(row):
        cell = tb4.cell(i, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.text = v
        r = tf.paragraphs[0].runs[0]
        r.font.size = Pt(14)
        r.font.name = "Calibri"
        if i == 0:
            r.font.bold = True
            r.font.color.rgb = WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL
        else:
            r.font.color.rgb = INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else LIGHT
text(
    s, 0.55, 5.52, 12.1, 0.85,
    [
        (
            "Điều chỉnh STING: n_levels, factor, min_count, cluster_level, connectivity — "
            "OFAT/sweep trên panel PAPI (robustness.csv).",
            14,
            False,
            GREY,
        ),
    ],
)
note(
    s,
    "Slide cầu nối lý thuyết–thực hành: nhấn O(n) và tách nhiễu so k-means. "
    "Phân biệt rõ: Wang et al. truy vấn/Phân vùng top-down có pruning; "
    "src/sting.py query_rect và cluster() chỉ dùng ô tại một level — đơn giản hóa có chủ đích. "
    "min_count quay lại ở slide PAPI. ~90 giây.",
)

# ---------- 5 — Ví dụ tổng hợp ----------
s = slide_new()
header(s, "DEMO", f"Chạy tay: 2-D tổng hợp — ARI = {SYN_ARI_S}", 5)
pic(s, "00_synthetic_sting.png", 0.55, 1.55, h=4.65)
bullets(
    s, 7.85, 1.65, 4.9, 4.9,
    [
        ("Dữ liệu.", "2 blob Gauss, 240 điểm, seed 42 (khớp tests/test_sting.py)."),
        ("Kết quả.", f"ARI = {SYN_ARI_S} · nhiễu {_pct(SYN_NOISE)} · k = {SYN_K}."),
        ("Lưới.", "n_levels=3, factor=4, cluster_level=2, min_count=3."),
        ("Kiểm chứng.", "bộ test STING (tests/test_sting.py) pass — thống kê ô khớp numpy."),
    ],
    size=15, gap_pt=52,
)
note(
    s,
    f"Trái: hình đã sinh trong repo. Phải: ARI {SYN_ARI_S} vừa tái lập khi build slide (assert). "
    "Mục đích: chứng minh implementation đúng trước khi đụng PAPI. ~90 giây.",
)

# ---------- 6 — Ứng dụng PAPI ----------
s = slide_new()
header(s, "ỨNG DỤNG", "Pipeline PAPI: chuẩn hóa · lưới thô · đa số k≈1", 6)
pic(s, "sting_first_real.png", 0.55, 1.45, h=4.2)
bullets(
    s, 7.95, 1.55, 4.75, 5.0,
    [
        ("(a) n_levels=2, 3×3, mc=5:", "k=1 · 55/61 trong vùng dày · nhiễu 10% · đặc trưng thô, năm 2023 (61 tỉnh)."),
        ("(b) n_levels=3, 9×9, mc=2:", "k=3 · nhiễu 31% · cùng năm/không gian — nhiễu tăng."),
        ("Đóng băng.", "STING(3,4,5) level=2 · pooled z (fit 2011–2023); holdout 2024 một lần."),
        ("Cặp đặc trưng.", "sd_4_2 × sd_6_1 (allowlist audit)."),
    ],
    size=14.5, gap_pt=44,
)
note(
    s,
    "Phát hiện chính: PAPI rất đồng nhất — đa số năm k=1. So sánh (a) vs (b) để giải thích sensitivity. "
    "Không gọi là fail. ~90 giây.",
)

# ---------- 7 — Đánh giá clustering + supervised ----------
s = slide_new()
header(s, "ĐÁNH GIÁ", "So baseline · classifier học phần · Ridge holdout", 7)
rows = [
    ("Phương pháp", "k", "Nhiễu", "Silh.", "ARI"),
    (
        "STING",
        M_STING["k"],
        _pct(M_STING["noise_ratio"]),
        _f3(M_STING["silhouette"]),
        "—",
    ),
    (
        "k-means k=2",
        M_KM2["k"],
        _pct(M_KM2["noise_ratio"]),
        _f3(M_KM2["silhouette"]),
        _f3(M_KM2["ari_vs_sting"]),
    ),
    (
        "k-means k=3",
        M_KM3["k"],
        _pct(M_KM3["noise_ratio"]),
        _f3(M_KM3["silhouette"]),
        _f3(M_KM3["ari_vs_sting"]),
    ),
    (
        "DBSCAN ε=0.2",
        M_DB["k"],
        _pct(M_DB["noise_ratio"]),
        _f3(M_DB["silhouette"]),
        _f3(M_DB["ari_vs_sting"]),
    ),
]
tb = s.shapes.add_table(
    len(rows), 5, Inches(0.55), Inches(1.42), Inches(5.75), Inches(2.65)
).table
for c, wd in enumerate([2.0, 0.45, 0.75, 0.7, 0.7]):
    tb.columns[c].width = Inches(wd)
for i, row in enumerate(rows):
    for j, v in enumerate(row):
        cell = tb.cell(i, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.text = v
        r = tf.paragraphs[0].runs[0]
        r.font.size = Pt(14)
        r.font.name = "Calibri"
        if i == 0:
            r.font.bold = True
            r.font.color.rgb = WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL
        else:
            r.font.color.rgb = INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else LIGHT
text(s, 0.55, 4.18, 5.6, 0.55, [
    ("Pooled 2011–2023 · metrics.csv · STING ≈ DBSCAN (ARI 0.647); k-means khác vùng.", 14, False, GREY),
])
rect(s, 6.55, 1.38, 6.25, 5.55, LIGHT)
# Cột phải xếp dọc: hình Ridge (thu nhỏ) → chú thích hình → tiêu đề bảng → bảng classifier.
pic(s, "supervised_regression.png", 7.0, 1.46, w=5.35)
text(s, 6.66, 4.45, 6.0, 0.22, [
    ("Hình: Ridge holdout 2023→2024 (một lần)", 11, False, GREY),
])
text(s, 6.62, 4.68, 6.05, 0.24, [
    ("PHÂN LOẠI HỌC PHẦN · nhãn pseudo-label STING · một năm holdout 2023→2024", 11, True, TEAL),
])
clf_rows = [("Mô hình", "CV macro-F1", "Holdout")] + list(COURSE_ROWS)
tb7 = s.shapes.add_table(
    len(clf_rows), 3, Inches(6.62), Inches(4.96), Inches(6.0), Inches(1.86)
).table
for c, wd in enumerate([2.25, 1.55, 2.2]):
    tb7.columns[c].width = Inches(wd)
for i, row in enumerate(clf_rows):
    for j, v in enumerate(row):
        cell = tb7.cell(i, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_top = cell.margin_bottom = Inches(0.01)
        tf = cell.text_frame
        tf.text = v
        r = tf.paragraphs[0].runs[0]
        r.font.size = Pt(12.5)
        r.font.name = "Calibri"
        if i == 0:
            r.font.bold = True
            r.font.color.rgb = WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL
        else:
            r.font.color.rgb = INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else LIGHT
bullets(
    s, 0.55, 4.75, 5.75, 2.25,
    [
        ("Mục tiêu.", "Dự báo sd_6_1 năm t+1 · 8 feature sạch."),
        ("CV.", f"Ridge R² {CV_RIDGE} vs carry {CV_CARRY} (expanding origin 2017–2022)."),
        ("Holdout.", f"MAE Ridge {MAE_RIDGE} vs carry {MAE_CARRY} · RF {MAE_RF} (không chọn)."),
    ],
    size=14, gap_pt=20,
)
note(
    s,
    "Bảng trái đọc từ metrics.csv. Bảng phải: course_supervised_baselines.csv — 6 classifier học phần "
    "(Naive Bayes, KNN, SVM, cây quyết định, random forest) trên nhãn pseudo-label STING, chọn theo "
    "macro-F1 CV; majority chỉ để so. Holdout 2023→2024 báo cáo một lần, không dùng để chọn. "
    "Ridge: supervised_metrics.csv — chọn theo CV. ~100 giây.",
)

# ---------- 8 — Kiểm chứng · robustness · hạn chế ----------
s = slide_new()
header(s, "TRUNG THỰC", "Kiểm chứng ngoài · robustness · hạn chế", 8)
rect(s, 0.55, 1.42, 4.85, 3.95, LIGHT)
text(s, 0.7, 1.5, 4.5, 0.3, [("PCI vs cụm STING (external)", 14, True, TEAL)])
pic(s, "external_pci_by_cluster.png", 0.65, 1.82, w=4.65)
text(s, 0.65, 5.02, 4.65, 0.28, [("Nguồn: results/figs/external_pci_by_cluster.png", 14, False, GREY)])
bullets(
    s, 5.65, 1.45, 7.15, 3.85,
    [
        ("PCI (doanh nghiệp).", "747 điểm join · ANOVA p≈6.9e-06 · đọc nhiễu vs cụm 2."),
        (
            "Kiểm chứng bên ngoài độc lập (PCI):",
            "liên hệ giữa các nhóm, không phải nhân quả — PCI không dùng khi học STING.",
        ),
    ],
    size=14, gap_pt=28,
)
bullets(
    s, 0.55, 5.75, 12.1, 1.45,
    [
        ("Robustness.", f"PCA d1–d6 {_pct(R_PCA['explained_var_total'])} PV → k={R_PCA['k']}; "
         f"OFAT gốc k={R_GOC['k']}, nhiễu {_pct(R_GOC['noise_ratio'])}; "
         f"f=3 → k={R_F3['k']}/{_pct(R_F3['noise_ratio'])}; lv=2 → k={R_LV2['k']}/100%; "
         f"mc=2 k={R_MC2['k']}/{_pct(R_MC2['noise_ratio'])} sil {_f3(R_MC2['silhouette'])} âm."),
        (
            "Hạn chế.",
            "Một holdout 2024; 23/37 chỉ tiêu bị đánh dấu bởi kiểm tra heuristic "
            "(bước nhảy trung bình > 0.25); chưa chứng minh là đổi thang "
            "(vd sd_5_4 — PROVENANCE); metric hình học chỉ so sánh thô.",
        ),
    ],
    size=14, gap_pt=22,
)
note(
    s,
    "Slide điểm Q&A: tự nêu hạn chế. PCI là doanh nghiệp vs PAPI hộ dân — kiểm chứng bên ngoài độc lập "
    "(PCI): liên hệ giữa các nhóm, không phải nhân quả; không nói quá thành kiểm chứng nhân quả. "
    "23/37 là cờ scale_audit (check_data.py) — heuristic, chưa tự chứng minh đổi thang; "
    "sd_5_4 (0.25–2.5 → 0.33–3.33, 2021) đã đối chiếu workbook. Robustness từ robustness.csv. ~90 giây.",
)

# ---------- 9 — Kết luận ----------
s = slide_new()
header(s, "KẾT LUẬN", "Đóng góp · hướng phát triển", 9)
bullets(
    s, 0.55, 1.5, 12.0, 5.3,
    [
        ("Thuật toán.", "STING tự viết + test suite; O(n); tách nhiễu trung thực trên panel thật."),
        ("Phát hiện.", "PAPI cấp tỉnh gần một khối — cấu trúc chỉ ở ngoại vi; không ép k cụm."),
        ("Pipeline.", "Chọn cấu hình train-only; dự đoán 2024; Ridge cải thiện khiêm tốn vs carry-forward."),
        ("Hướng tới.", "Thêm năm holdout; mở rộng external; notebook/ứng dụng tách (không trên slide)."),
    ],
    size=16, gap_pt=42,
)
note(
    s,
    "Tóm 4 ý trong 60 giây; dành 30 giây nhấn trung thực khoa học. Chuyển tài liệu + Q&A.",
)

# ---------- 10 — Tài liệu + Q&A ----------
s = slide_new()
header(s, "NGUỒN", "Tài liệu tham khảo", 10)
bullets(
    s, 0.55, 1.35, 7.0, 4.5,
    [
        ("PAPI 2011–2024.", "papi.org.vn · CECODES/VFF-CRT/RTA/UNDP."),
        ("Replication.", "Le et al., Mendeley DOI 10.17632/wbk42j9wc8.1."),
        ("STING.", "Wang, Yang & Muntz (1997), VLDB."),
        ("Repo.", "src/sting.py · scripts/ · results/ · PROVENANCE.md."),
    ],
    size=14, gap_pt=36,
)
rect(s, 7.85, 1.35, 4.9, 5.5, NAVY)
text(s, 7.95, 2.0, 4.7, 1.2, [("Q & A", 52, True, GOLD)], align=PP_ALIGN.CENTER)
text(
    s, 7.95, 3.35, 4.7, 1.0,
    [("5 phút phản biện", 20, True, WHITE)],
    align=PP_ALIGN.CENTER,
)
text(
    s, 7.95, 4.55, 4.7, 1.8,
    [("Sẵn sàng: vì sao grid-based?\nĐồng nhất PAPI?\nChọn Ridge?\nRobustness OFAT?", 14, False, RGBColor(0xB9, 0xCD, 0xDE))],
    align=PP_ALIGN.CENTER,
)
note(
    s,
    "Không đọc slide 10 — mời hỏi. Nếu hỏi nguồn: PROVENANCE.md. Cảm ơn.",
)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
n_slides = len(prs.slides._sldIdLst)
assert n_slides == TOTAL, f"expected {TOTAL} slides, got {n_slides}"
print("saved:", OUT)
print("slides:", n_slides)
