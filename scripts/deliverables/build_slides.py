"""Build slides/final.pptx — 11 trang 16:9, tiếng Việt, có ghi chú người nói.

Cách dùng: python scripts/deliverables/build_slides.py
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from statistics import mean

import matplotlib
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from scripts.common.midterm_clustering import DBSCAN_OPTIONS, KMEANS_OPTIONS, sting_steps_figure  # noqa: E402
from scripts.common.papi_pred_common import describe_grid_assignment, load_config, load_panel  # noqa: E402
from sting import STING  # noqa: E402

FIGS = ROOT / "results" / "figs"
OUT = ROOT / "slides" / "final.pptx"
SLIDE_COUNT = 11
REFERENCE_YEAR = 2023


def _read_results_csv(name):
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pct(v):
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


ASSIGNMENTS = _read_results_csv("predict_all_years.csv")
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
RECOMPUTED_LABELS = {
    (row.province_code, row.year): int(row.cluster)
    for row in GRID_RESULTS.dropna(subset=["cluster"]).itertuples(index=False)
}
SAVED_LABELS = {
    (int(row["province_code"]), int(row["year"])): int(row["pred_cluster"])
    for row in ASSIGNMENTS
}
assert RECOMPUTED_LABELS == SAVED_LABELS, "Kết quả gán lưới không khớp predict_all_years.csv"

REFERENCE = [row for row in ASSIGNMENTS if row["split"] == "train"]
PROFILES = defaultdict(list)
for row in REFERENCE:
    PROFILES[row["pred_cluster"]].append(row)
MAIN_CLUSTER = max((label for label in PROFILES if label != "-1"), key=lambda label: len(PROFILES[label]))
MAIN_SIZE = len(PROFILES[MAIN_CLUSTER])
REFERENCE_NOISE = len(PROFILES["-1"])
CLUSTERED = len(REFERENCE) - REFERENCE_NOISE
YEAR_COUNTS = defaultdict(Counter)
for row in ASSIGNMENTS:
    YEAR_COUNTS[int(row["year"])][row["pred_cluster"]] += 1
LABELS_2023 = {r["province_code"]: r["pred_cluster"] for r in ASSIGNMENTS if r["year"] == "2023"}
LABELS_2024 = {r["province_code"]: r["pred_cluster"] for r in ASSIGNMENTS if r["year"] == "2024"}
TRANSITIONS = Counter((LABELS_2023[p], LABELS_2024[p]) for p in LABELS_2023.keys() & LABELS_2024.keys())
assert all({left, right} <= {MAIN_CLUSTER, "-1"} for left, right in TRANSITIONS)
OBSERVED = _read_results_csv("papi_observed_grid_2024.csv")
MISSING_2024 = [row["province_vi"] for row in OBSERVED if row["grid_status"] == "missing_score"]

FORECAST = json.loads((ROOT / "results" / "papi_forecast_2024.json").read_text(encoding="utf-8"))
SCORES = {(row["target"], row["method"]): row for row in FORECAST["scores"]}
ZONES = {row["method"]: row for row in FORECAST["grid"]}
N_COMPARED = FORECAST["comparable_count"]
N_OUTSIDE = FORECAST["actual_outside"]


def _dec(value, digits=4):
    return f"{value:.{digits}f}".replace(".", ",")


def _dot_thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _comparison_on_shared_points():
    """Giữ nguyên nhãn đã học trên mẫu đầy đủ rồi tính silhouette trên tập giao."""
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
        for method, labels in (("STING", REFERENCE_LABELS), ("K-means (k = 2)", kmeans), ("DBSCAN (ε = 0,2)", dbscan))
    ]
    return rows, int(shared.sum())


AUDIT = _read_results_csv("preprocessing_audit.csv")


def _audit_row(stage_sub: str, test_sub: str) -> dict[str, str]:
    hits = [r for r in AUDIT if stage_sub in r["stage"] and test_sub in r["test"]]
    if len(hits) != 1:
        raise KeyError(f"{stage_sub} / {test_sub}: {len(hits)} dòng trong preprocessing_audit.csv")
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

assert N_DUP == 0, "preprocessing_audit.csv: kỳ vọng 0 dòng trùng khóa"
assert "KHÔNG nội suy" in _MISS_ROW["decision"], "preprocessing_audit.csv: quyết định ô thiếu đã đổi"
assert "chỉ đánh dấu" in _OUT_ROW["decision"], "preprocessing_audit.csv: quyết định ngoại lai đã đổi"

NAVY = RGBColor(0x0F, 0x2B, 0x46)
TEAL = RGBColor(0x1B, 0x6E, 0x77)
GOLD = RGBColor(0xE2, 0xB0, 0x4A)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x5A, 0x5A, 0x5A)
LIGHT = RGBColor(0xF6, 0xF4, 0xEF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

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
    """runs: list[(text, size, bold, color)] — mỗi phần tử là một dòng."""
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
    text(slide, 0.55, SH - 0.36, 9.5, 0.3, [(source, 10, False, GREY)])
    text(slide, SW - 1.6, SH - 0.36, 1.1, 0.3, [(f"{page_no:02d} / {SLIDE_COUNT}", 10, True, GREY)],
         align=PP_ALIGN.RIGHT)


def note(slide, text_md):
    slide.notes_slide.notes_text_frame.text = text_md


def bullets(slide, x, y, w, h, items, size=13, color=INK, gap_pt=6, bold_first=True,
            lead_color=TEAL, align=PP_ALIGN.LEFT, hang_in=0.22, gap_first=None):
    """items: list[(lead, rest)]. hang_in > 0 -> hanging indent: dòng wrap thụt vào
    sau dấu ▸ thay vì trở về lề trái; chỉ áp cho canh trái. gap_first: gap_pt riêng
    sau bullet đầu tiên (phân bố dọc tinh chỉnh)."""
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


def pic_bytes(slide, bio: BytesIO, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    slide.shapes.add_picture(bio, Inches(x), Inches(y), **kw)


def result_table(slide, rows, x, y, widths, row_height, size):
    table = slide.shapes.add_table(
        len(rows), len(widths), Inches(x), Inches(y), Inches(sum(widths)), Inches(len(rows) * row_height)
    ).table
    for col, width in zip(table.columns, widths):
        col.width = Inches(width)
    for i, row in enumerate(rows):
        table.rows[i].height = Inches(row_height)
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.09)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text_frame.text = str(value)
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            font = paragraph.runs[0].font
            font.size, font.name, font.bold = Pt(size), "Calibri", i == 0
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
text(s, 0.85, 1.15, 7.6, 0.4, [("HỌC MÁY · BÁO CÁO CUỐI KỲ", 15, True, GOLD)])
text(s, 0.85, 1.75, 7.7, 1.48, [("Phân cụm dựa trên lưới STING", 38, True, WHITE)])
text(s, 0.85, 3.42, 7.7, 0.6, [("Đặc điểm và biến động PAPI 2011–2024", 22, False, WHITE)])
text(s, 0.85, 4.9, 7.8, 1.3, [
    ("Nhóm 15 · Chủ đề 6 · Grid-based clustering", 15, True, GOLD),
    ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 15, False, RGBColor(0xB9, 0xCD, 0xDE)),
])
note(s, "Kính thưa thầy, nhóm 15 xin trình bày kết quả đồ án phân cụm dữ liệu PAPI bằng STING. "
     "Nhóm xây dựng lưới thống kê, kiểm tra trên dữ liệu giả lập, sau đó áp dụng lên hai chỉ tiêu "
     "PAPI của 63 tỉnh trong giai đoạn 2011–2024. Phần cuối trình bày giới hạn và các phân tích bổ trợ.")


s = slide_new()
header(s, "BÀI TOÁN", "Đặc điểm và biến động PAPI qua 14 năm", 2)
bullets(s, 0.6, 1.85, 6.5, 4.7, [
    ("Đặc điểm.", "Dùng STING để tìm vùng tập trung và vùng thưa trên hai chỉ tiêu PAPI."),
    ("Biến động.", "Theo dõi vị trí của từng tỉnh qua các năm trên cùng lưới, chú ý khi tỉnh đổi ô hoặc đổi trạng thái."),
    ("Đơn vị phân tích.", "Mỗi điểm là một quan sát tỉnh–năm."),
], size=20, gap_pt=24)
rect(s, 7.55, 1.7, 5.15, 4.72, LIGHT)
text(s, 7.82, 1.98, 4.62, 1.32, [
    (f"{N_ROWS} × 41", 34, True, NAVY),
    ("63 tỉnh/thành phố · 2011–2024", 16, False, GREY),
])
text(s, 7.82, 3.58, 4.62, 2.65, [
    ("HAI CHỈ TIÊU PHÂN CỤM", 15, True, TEAL),
    ("4.2  Kiểm soát tham nhũng trong cung ứng dịch vụ công", 18, False, INK),
    ("6.1  Y tế công lập", 18, False, INK),
], space_after=12)
note(s, "Panel PAPI gồm 63 đơn vị hành chính trong giai đoạn nghiên cứu, 14 năm và 41 cột. "
     "Hai trục lưới là điểm của chỉ tiêu 4.2 và 6.1. Vị trí địa lý dùng để vẽ bản đồ trong notebook. "
     "Hai câu hỏi chính là đặc điểm của vùng dày và sự dịch chuyển trên lưới qua các năm. "
     "Thử nghiệm dự báo được trình bày sau phần quan sát. https://papi.org.vn/du-lieu-papi/")


s = slide_new()
header(s, "TIỀN XỬ LÝ", "Một lưới tham chiếu để so sánh qua các năm", 3,
       "src/preprocessing.py · Notebook cuối kỳ §1")
text(s, 0.6, 1.42, 6.42, 0.52, [("run_preprocessing_pipeline(...)", 18, True, TEAL)])
bullets(s, 0.6, 2.00, 6.42, 3.46, [
    ("Làm sạch.", f"{N_DUP}/{N_ROWS} trùng khóa (province_code, year). Quy 0,0 về NaN, rà thang đo và đánh dấu cực trị."),
    ("Tích hợp.", "Thống nhất mã tỉnh và ghép 14 workbook thành panel 882 × 41."),
    ("Chọn mẫu STING.", f"dropna theo cặp chỉ tiêu. Giữ {len(RECOMPUTED_LABELS)} dòng đủ điểm, "
     f"{N_ROWS - len(RECOMPUTED_LABELS)} dòng thiếu vẫn có mặt trong panel."),
], size=16.5, gap_pt=13)
result_table(s, [
    ("Giai đoạn", "Đủ hai điểm", "StandardScaler"),
    ("2011–2023", len(REFERENCE), "fit rồi transform"),
    ("2024", len(LABELS_2024), "transform"),
], 7.18, 1.96, [1.49, 1.30, 2.72], 0.69, 16)
text(s, 7.18, 4.22, 5.51, 1.17, [
    ("z = (x − μ) / σ", 18, True, NAVY),
    ("Cả hai giai đoạn dùng μ và σ tính từ 808 dòng đến năm 2023.", 16, False, INK),
])
text(s, 0.6, 5.75, 12.09, 1.03, [
    ("Chọn cấu hình bằng dữ liệu đến 2020 và kiểm độ phủ ở 2021–2022. Dựng lưới trên 808 dòng đến 2023.", 16.5, True, NAVY),
    ("Lượt mô tả giữa kỳ dựng lưới trên 869 dòng, gồm cả các điểm đã đo năm 2024.", 15, False, GREY),
], space_after=6)
note(s, f"Pipeline sáu bước nằm trong Nhom15_TienXuLy_PAPI.ipynb. Bảng làm sạch có "
     f"{_dot_thousands(N_MISS)}/{_dot_thousands(N_CELLS)} ô thiếu trên 37 cột điểm "
     f"và {N_OUT} ô được đánh dấu |z| > {Z_OUT}. Các cực trị hợp lệ được giữ để bảo toàn biên lưới. "
     "Nhóm rà soát thang đo với bảng tính gốc. Ngưỡng biến động trung bình năm 0,25 chỉ là dấu hiệu cần đối chiếu. "
     "Nhóm khảo sát ứng viên bằng dữ liệu đến 2020 và đối chiếu độ phủ 2021–2022. "
     "Điểm chọn cấu hình dùng các tiêu chí mô tả do nhóm đặt. Sau khi chốt, chuẩn hóa và dựng lưới trên 2011–2023. "
     "Khi đưa điểm quan sát 2024 lên lưới, nhóm giữ nguyên biên ô và quy tắc gán. "
     "Số liệu truy từ results/preprocessing_audit.csv và models/predict_config.json.")


s = slide_new()
header(s, "CƠ CHẾ GRID-BASED", "Biến thể STING tạo cụm từ các ô dày", 4,
       "src/sting.py · Notebook cuối kỳ §1.1–1.2")
resolutions = ", ".join(str(GRID.factor ** level) for level in range(GRID.n_levels))
steps = [
    ("fit(X_train_z)",
     f"n_levels={GRID.n_levels}, factor={GRID.factor} ({resolutions} đoạn/trục). "
     "Ô lưu count, mean, std, min, max."),
    (f"cluster(level={LEVEL}, connectivity={CONNECTIVITY})",
     f"Giữ ô có count ≥ {MIN_COUNT}. Duyệt sâu (DFS) theo 4 hướng kề cạnh để gán nhãn cụm."),
    ("predict(X_2024_z)",
     "Dùng biên lưới đã dựng và tra nhãn theo ô. Điểm ngoài vùng dày nhận −1."),
]
for i, (title, body) in enumerate(steps):
    x = 0.57 + i * 4.17
    rect(s, x, 1.35, 3.85, 1.55, LIGHT)
    text(s, x + 0.14, 1.43, 3.55, 1.44, [
        (title, 15, True, TEAL),
        (body, 15, False, INK),
    ], space_after=6)
step_fig = sting_steps_figure(figsize=(12.2, 2.75), dpi=200)
step_bio = BytesIO()
step_fig.savefig(step_bio, format="png", dpi=200, facecolor="white")
plt.close(step_fig)
step_bio.seek(0)
pic_bytes(s, step_bio, 0.65, 2.98, w=12.03)
text(s, 0.6, 5.70, 12.1, 1.28, [
    ("_assign tính chỉ số ô mỗi trục bằng clip(floor((z − zmin) / Δ), 0, r − 1), với Δ = (zmax − zmin) / r.", 15, True, NAVY),
    (f"Hình dùng r = 3, ngưỡng 3. PAPI dùng r = {SIDE}, ngưỡng {MIN_COUNT} điểm mỗi ô và significance_z=None.", 14.5, False, INK),
    ("STING gốc xét phân phối và khoảng tin cậy khi chọn ô cho truy vấn từ trên xuống.", 14.5, False, GREY),
], space_after=3)
note(s, "Ví dụ 15 điểm gồm hai nhóm 7 điểm và một điểm trong ô thưa. Quy tắc kề 4 hướng chỉ nối ô chung cạnh. "
     "Ở mức l, r = factor^l. Khi điểm đúng biên trên, clip đưa chỉ số về ô cuối. "
     "_accumulate gom điểm cùng chỉ số để tính thống kê. Khi phân cụm, ngăn xếp duyệt từng vùng ô dày. "
     "predict kiểm tra biên trước khi gọi _assign rồi tra nhãn đã lưu. "
     "query_top_down minh họa ở notebook giữa kỳ §4.3.3 và cuối kỳ §1.2 để gộp các ô nằm trọn vùng truy vấn. "
     "Xem bài báo của Wang, Yang và Muntz tại https://www.vldb.org/conf/1997/P186.PDF")


s = slide_new()
header(s, "KIỂM CHỨNG", "STING tìm lại hai cụm giả lập", 5,
       "Notebook cuối kỳ §1.1 · tests/test_sting.py")
pic(s, "00_synthetic_sting.png", 0.55, 1.63, h=4.63)
bullets(s, 7.9, 1.54, 4.83, 5.39, [
    ("Mẫu thử.", "make_blobs sinh 240 điểm từ hai phân bố Gauss, seed 42."),
    ("Kết quả.", "2 cụm và 2,5% điểm trong ô thưa."),
    ("Độ khớp.", "adjusted_rand_score đạt 0,950 so với nhãn đã biết."),
    ("Assert.", "ARI ≥ 0,9 và tổng count ở mỗi mức luôn bằng 240."),
], size=17, gap_pt=16)
note(s, "Mẫu giả lập dùng seed 42. ARI đo mức khớp với nhãn tham chiếu của mẫu này. "
     "Bộ kiểm thử trong repo còn đối chiếu thống kê ô, quan hệ liên thông, biên lưới và gán điểm mới. "
     "Trên PAPI, silhouette và độ phủ dùng để đọc kết quả khi thiếu nhãn cụm tham chiếu.")


s = slide_new()
header(s, "ĐẶC ĐIỂM CỤM", "Một cụm lớn trên lưới PAPI 2011–2023", 6,
       "Notebook cuối kỳ §2 · results/predict_all_years.csv")
text(s, 0.61, 1.47, 5.5, 0.48, [("Trung bình trên điểm gốc theo cụm", 17, True, TEAL)])
profile_rows = [("Cụm", "Số điểm", "TB 4.2", "TB 6.1")]
for label, points in sorted(PROFILES.items()):
    if label == "-1":
        continue
    profile_rows.append((label, len(points), *(
        _dec(mean(float(row[feature]) for row in points), 2) for feature in ("sd_4_2", "sd_6_1")
    )))
result_table(s, profile_rows, 0.6, 2.03, [1.05, 1.46, 1.5, 1.5], 0.69, 16)
text(s, 6.47, 1.47, 6.24, 0.48, [("Đối chứng trên cùng hai chỉ tiêu", 17, True, TEAL)])
comparison_rows, n_shared = _comparison_on_shared_points()
result_table(s, [
    ("Phương pháp", "Số cụm", "Nhiễu¹", "Silhouette²"),
    *comparison_rows,
], 6.48, 2.03, [2.16, 1.10, 1.20, 1.75], 0.69, 15)
text(s, 0.6, 5.11, 5.53, 1.65, [
    (f"{len(GRID.label_of_)} ô dày tạo {GRID.n_clusters_} cụm. "
     f"Cụm {MAIN_CLUSTER} có {MAIN_SIZE}/{CLUSTERED} quan sát đã vào cụm.", 17, True, NAVY),
    (f"{REFERENCE_NOISE}/{len(REFERENCE)} quan sát ở ô thưa.", 16, False, INK),
], space_after=7)
text(s, 6.47, 5.11, 6.23, 1.71, [
    (f"¹ Tỷ lệ nhãn −1 trên {len(REFERENCE)} quan sát.", 15, False, GREY),
    ("² shared = (train_labels >= 0) & (dbscan_labels >= 0)", 14.5, False, GREY),
    (f"silhouette_score trên cùng {n_shared} điểm, giữ nhãn đã học.", 15, False, GREY),
], space_after=5)
note(s, "Hồ sơ tính từ results/predict_all_years.csv, chỉ lấy phần lưới tham chiếu 2011–2023. "
     "Cụm lớn có trung bình ở cả hai chỉ tiêu cao hơn hai cụm nhỏ theo cách nhóm này. "
     "K-means k=2 có silhouette cao nhất trong bảng, phản ánh độ gọn và độ tách theo Euclid trên tập giao. "
     "Phần giao giữ nguyên nhãn đã học, đủ 631 điểm. Các số 0,361, 0,445 và 0,218 trong notebook "
     "dùng tập điểm thuộc cụm riêng của từng phương pháp. Khi chỉ đổi kề 4 hướng thành kề 8 hướng, "
     "STING gộp ba cụm thành một và vẫn giữ 158 điểm nhiễu. Xem notebook cuối kỳ §1.1–2.")


s = slide_new()
header(s, "QUAN SÁT NĂM 2024", f"{YEAR_COUNTS[2024][MAIN_CLUSTER]} trong {len(LABELS_2024)} tỉnh đủ điểm vào cụm lớn", 7,
       "scripts/common/papi_pred_common.py · Notebook cuối kỳ §4")
pic(s, "predict_2024.png", 0.58, 1.53, w=7.95)
text(s, 8.72, 1.58, 4.04, 1.15, [
    ("describe_grid_assignment(...)", 16.5, True, TEAL),
    ("scaler.transform → sting.predict", 15.5, False, INK),
], space_after=5)
bullets(s, 8.72, 2.68, 4.04, 4.12, [
    ("Cụm lớn.", f"{YEAR_COUNTS[2024][MAIN_CLUSTER]} tỉnh cùng vào cụm {MAIN_CLUSTER}."),
    ("Ô thưa.", f"{YEAR_COUNTS[2024]['-1']} tỉnh ở ô có 0–3 điểm tham chiếu, nhận −1."),
    ("Thiếu điểm.", f"{' và '.join(MISSING_2024)} giữ nhãn trống."),
], size=16.5, gap_pt=15)
note(s, "Đây là phép gán hai điểm PAPI đã quan sát lên lưới cố định. "
     "Hình hiển thị điểm gốc để người xem đọc được thang PAPI. Dấu × đánh dấu điểm ở ngoài vùng dày. "
     "Cả 13 tỉnh đó vẫn ở trong biên lưới, trong các ô có 0–3 quan sát tham chiếu. "
     "Một số tỉnh ở ô thưa có điểm cao ở rìa phải hoặc rìa trên. "
     "Xem results/papi_observed_grid_2024.csv và notebook cuối kỳ §4.")


s = slide_new()
header(s, "BIẾN ĐỘNG", "Dịch chuyển qua các năm trên cùng lưới", 8,
       "Notebook cuối kỳ §4 · results/predict_all_years.csv")
text(s, 0.6, 1.43, 6.05, 0.46, [("Số tỉnh theo trạng thái ở các năm mốc", 17, True, TEAL)])
year_rows = [("Năm", "Cụm lớn", "2 cụm nhỏ", "Ô thưa", "Đủ điểm")]
for year in (2011, 2018, 2019, 2023, 2024):
    counts = YEAR_COUNTS[year]
    small = sum(n for label, n in counts.items() if label not in (MAIN_CLUSTER, "-1"))
    year_rows.append((year, counts[MAIN_CLUSTER], small, counts["-1"], counts.total()))
result_table(s, year_rows, 0.6, 1.91, [0.9, 1.18, 1.49, 1.10, 1.21], 0.46, 14.5)
text(s, 7.04, 1.43, 5.65, 0.46, [
    (f"{TRANSITIONS.total()} tỉnh có đủ điểm ở cả hai năm", 17, True, TEAL),
])
result_table(s, [
    ("2023 → 2024", "Cụm lớn", "Ô thưa"),
    ("Cụm lớn", TRANSITIONS[MAIN_CLUSTER, MAIN_CLUSTER], TRANSITIONS[MAIN_CLUSTER, "-1"]),
    ("Ô thưa", TRANSITIONS["-1", MAIN_CLUSTER], TRANSITIONS["-1", "-1"]),
], 7.04, 1.91, [2.41, 1.57, 1.57], 0.53, 15)
text(s, 7.04, 3.70, 5.55, 0.91, [
    (f"{TRANSITIONS[MAIN_CLUSTER, '-1']} tỉnh sang ô thưa, {TRANSITIONS['-1', MAIN_CLUSTER]} tỉnh vào cụm lớn.", 16, True, NAVY),
    ("Ghép theo province_code, dùng chung lưới và scaler.", 14.5, False, GREY),
], space_after=6)
text(s, 0.6, 4.88, 12.0, 0.43, [("Lạng Sơn trên lưới 2011–2023", 17, True, TEAL)])
province = GRID_RESULTS.loc[GRID_RESULTS.province_vi.eq("Lạng Sơn") & GRID_RESULTS.year.isin([2023, 2024])].sort_values("year")
trace_rows = [("Năm", "Điểm PAPI 4.2 / 6.1", "z-score 4.2 / 6.1", "Ô lưới", "Số điểm tham chiếu", "Nhãn")]
for observation, z in zip(province.itertuples(index=False), SCALER.transform(province[FEATURES]), strict=True):
    raw = " / ".join(_dec(getattr(observation, feature), 3) for feature in FEATURES)
    transformed = " / ".join(_dec(value, 3) for value in z)
    label = "−1 (ô thưa)" if observation.cluster == -1 else f"{observation.cluster} (cụm lớn)"
    trace_rows.append((observation.year, raw, transformed, observation.grid_cell, observation.reference_count, label))
result_table(s, trace_rows, 0.6, 5.35, [0.94, 2.57, 2.41, 1.30, 2.72, 2.05], 0.49, 14.5)
note(s, "Bảng bên trái trích các mốc từ results/predict_all_years.csv. Mọi năm dùng chung lưới. "
     "Hai cụm nhỏ chỉ có quan sát đến 2018. Số tỉnh ở cụm lớn thay đổi qua từng năm. "
     "Các năm đến 2023 nằm trong giai đoạn dựng lưới. Năm 2024 được gán sau khi lưới đã cố định. "
     "Ma trận bên phải đọc theo hàng 2023 và cột 2024. Bảng Lạng Sơn được dựng lại bằng describe_grid_assignment "
     "và bộ chuẩn hóa học đến 2023. Chỉ số ô bắt đầu từ 0. Hai chỉ tiêu cùng quyết định ô mới trên lưới. "
     "Mục 4.8 notebook giữa kỳ in cả chỉ số ô và số điểm tham chiếu ở hai năm. "
     "Nếu đối chiếu ô (12, 10) có 17 điểm ở mục 4.3 giữa kỳ, số đếm đó thuộc lưới mô tả dựng từ cả 869 dòng.")


s = slide_new()
header(s, "THỬ NGHIỆM BỔ TRỢ", "Dự báo điểm bỏ sót các tỉnh ngoài vùng dày", 9,
       "scripts/common/papi_forecast.py · Notebook cuối kỳ §4.1–4.3")
text(s, 0.6, 1.31, 12.0, 0.76, [
    ("forecast_from_history(history, cfg[\"sting\"]) → score_forecast(run, observed)", 16.5, True, TEAL),
    (f"Sáu lượt kiểm định với năm đích 2018–2023 chọn Ridge. Dự báo từ tám chỉ tiêu năm 2023, đối chiếu {N_COMPARED} tỉnh.", 14.5, False, INK),
], space_after=3)
pic(s, "papi_forecast_grid.png", 0.6, 2.15, w=7.05)
result_table(s, [
    ("Chỉ tiêu", "MAE Ridge", "MAE giữ điểm 2023"),
    ("4.2", _dec(SCORES["sd_4_2", "forecast"]["mae"]), _dec(SCORES["sd_4_2", "carry"]["mae"])),
    ("6.1", _dec(SCORES["sd_6_1", "forecast"]["mae"]), _dec(SCORES["sd_6_1", "carry"]["mae"])),
], 7.98, 2.08, [1.07, 1.35, 2.27], 0.62, 16)
text(s, 8.0, 4.19, 4.65, 2.42, [
    (f"Ridge nhận ra {ZONES['forecast']['out_correct']}/{N_OUTSIDE} tỉnh ngoài vùng dày.", 18, True, NAVY),
    (f"Giữ điểm 2023 nhận ra {ZONES['carry']['out_correct']}/{N_OUTSIDE}, gán ngoài nhầm "
     f"{ZONES['carry']['false_out']} tỉnh.", 16, False, INK),
    ("RMSE của chỉ tiêu 4.2 tăng nhẹ với Ridge.", 15.5, False, GREY),
], space_after=8)
text(s, 0.64, 5.9, 7.0, 0.81, [
    ("Cùng lưới 2011–2023. Dấu × chỉ điểm ngoài vùng dày. Kết quả hồi cứu trên một năm.", 15, False, GREY),
])
note(s, f"Chọn Ridge theo MAE trung bình qua sáu lượt kiểm định với năm đích 2018–2023. "
     f"Có {FORECAST['train_pairs']} cặp lịch sử và {FORECAST['forecast_count']} tỉnh có dự báo. "
     f"Đối chiếu điểm thực tế trên {N_COMPARED} tỉnh đủ dữ liệu ở cả hai phía. "
     f"RMSE của 4.2 là {_dec(SCORES['sd_4_2', 'forecast']['rmse'])} với Ridge và "
     f"{_dec(SCORES['sd_4_2', 'carry']['rmse'])} với giữ điểm 2023. "
     f"Dự báo điểm đưa mọi tỉnh vào cụm lớn. Độ đúng cân bằng theo vùng là "
     f"{_pct(ZONES['forecast']['balanced_zone_accuracy'])}. "
     f"Kịch bản dựa trên {FORECAST['scenario_count']} cặp sai số ngoài lượt kiểm định cho AUC xếp hạng "
     f"thăm dò {_dec(FORECAST['scenario_auc'], 3)} trên một năm hồi cứu. "
     "Xem results/papi_forecast_2024.json và notebook cuối kỳ §4.1–4.3.")


s = slide_new()
header(s, "KẾT LUẬN", "Kết quả chính và giới hạn", 10)
bullets(s, 0.66, 1.63, 12.0, 4.06, [
    ("Đặc điểm.", f"Một vùng dày chiếm {_dec(100 * MAIN_SIZE / CLUSTERED, 1)}% số quan sát đã vào cụm đến 2023."),
    ("Biến động.", f"Hai cụm nhỏ chỉ có quan sát đến 2018. Trong {TRANSITIONS.total()} tỉnh đủ điểm ở 2023 và 2024, "
     f"{TRANSITIONS[MAIN_CLUSTER, '-1'] + TRANSITIONS['-1', MAIN_CLUSTER]} tỉnh đổi trạng thái."),
    ("Độ nhạy.", "Đổi connectivity từ 1 sang 2 gộp ba cụm thành một, vẫn còn 158 điểm nhiễu trên 808 dòng."),
], size=20, gap_pt=20)
rect(s, 0.66, 5.47, 12.0, 1.34, LIGHT)
text(s, 0.82, 5.6, 11.67, 1.03, [
    ("TÀI LIỆU CHÍNH", 13.5, True, TEAL),
    ("Wang, Yang & Muntz (VLDB 1997) · PAPI 2011–2024 (CECODES, VFF-CRT, RTA, UNDP)", 15, False, INK),
    ("Đối chiếu dữ liệu Le và cộng sự (Mendeley Data, DOI 10.17632/wbk42j9wc8.1)", 15, False, INK),
], space_after=3)
note(s, "Phân tích này mô tả cấu trúc mật độ trên hai tiểu chỉ tiêu. Các quan sát có thể lặp tỉnh qua các năm. "
     "Thử nghiệm PCI trong phụ lục C của notebook ghép được 747 quan sát. "
     "Kết quả kiểm định gộp mang tính tham khảo do chưa hiệu chỉnh sự phụ thuộc theo tỉnh và năm. "
     "Hướng tiếp theo là kiểm tra thêm các năm và các chỉ tiêu có thang đo so sánh được. "
     "Nộp kèm Nhom15_CuoiKy_STING_PAPI.docx và Nhom15_CuoiKy_STING_PAPI.ipynb. "
     "https://www.vldb.org/conf/1997/P186.PDF · https://papi.org.vn/du-lieu-papi/ · "
     "https://data.mendeley.com/datasets/wbk42j9wc8/1. Tài liệu dự báo theo thời gian của "
     "Hyndman và Athanasopoulos (2021), Forecasting: Principles and Practice.")


s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
text(s, 0.55, 3.1, 12.23, 1.2, [
    ("Cảm ơn thầy và các bạn đã lắng nghe", 40, True, GOLD),
], align=PP_ALIGN.CENTER)
note(s, "Phần trình bày của nhóm đến đây là kết thúc. Nhóm xin cảm ơn thầy và các bạn đã lắng nghe. "
     "Nhóm mong nhận được câu hỏi, góp ý về phương pháp cũng như kết quả thực nghiệm.")

assert len(prs.slides) == SLIDE_COUNT
OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print("saved:", OUT)
print("slides:", len(prs.slides))
