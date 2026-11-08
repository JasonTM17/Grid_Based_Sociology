"""Build slides/final.pptx — 16 trang 16:9, tiếng Việt, có ghi chú người nói.

Cách dùng: python scripts/build_slides.py
"""
import csv
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "results" / "figs"
OUT = ROOT / "slides" / "final.pptx"

# ==== Số liệu đọc từ artifact do script khác sinh (không hardcode số đo) ====


def _read_results_csv(name):
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pct(v):
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


ROBUSTNESS = _read_results_csv("robustness.csv")


def _rob(branch_sub):
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


def _reg_cv(model_sub):
    for r in SUP_ROWS:
        if r["task"] == "regression" and model_sub in r["model"]:
            return r["value_cv"].strip()
    raise KeyError(model_sub)


CV_CARRY = _reg_cv("carry-forward")
CV_RIDGE = _reg_cv("ridge")

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


def header(slide, kicker, title, page_no):
    rect(slide, 0, 0, SW, 0.16, TEAL)
    text(slide, 0.55, 0.32, 10.5, 0.3, [(kicker, 12, True, TEAL)])
    text(slide, 0.55, 0.58, 12.2, 0.75, [(title, 26, True, NAVY)])
    # footer
    rect(slide, 0.55, SH - 0.42, SW - 1.1, 0.012, RGBColor(0xD8, 0xD5, 0xCC))
    text(slide, 0.55, SH - 0.36, 9.5, 0.3, [("Topic 6 · STING × PAPI 2011–2024 · Nhóm 15", 10, False, GREY)])
    text(slide, SW - 1.6, SH - 0.36, 1.1, 0.3, [(f"{page_no:02d} / 16", 10, True, GREY)], align=PP_ALIGN.RIGHT)


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


# ---------- Slide 1 — Bìa ----------
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
# lưới motif 4x4
for r in range(4):
    for c in range(4):
        x0, y0 = SW - 4.6 + c * 0.78, 1.05 + r * 0.78
        fill = GOLD if (r, c) in ((1, 1), (2, 2)) else RGBColor(0x1E, 0x3D, 0x5E)
        rect(s, x0, y0, 0.66, 0.66, fill)
text(s, 0.85, 1.15, 7.6, 0.4, [("ĐỒ ÁN MÔN HỌC MÁY", 13, True, GOLD)])
text(s, 0.85, 1.75, 8.6, 2.6, [("Phân cụm 63 tỉnh", 44, True, WHITE),
                               ("với STING trên dữ liệu PAPI 2011–2024", 30, True, WHITE)])
text(s, 0.85, 4.65, 8.4, 1.6, [
    ("Topic 6 · Grid-based (clustering) · Domain: Sociology / History", 15, True, GOLD),
    ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 12, False, RGBColor(0xB9, 0xCD, 0xDE)),
    ("15' trình bày + 5' Q&A", 12, False, RGBColor(0xB9, 0xCD, 0xDE)),
])
note(s, "Mở đầu: giới thiệu đề tài 20s; nêu thesis: dữ liệu PAPI khá đồng nhất — nhóm xin trình bày trung thực cả kết quả thuận lẫn robustness mở rộng chiều (PCA không nhận diện; nhánh 8 chiều đọc theo ablation OFAT — mc=2 đạt ngưỡng k/noise nhưng silhouette âm).")

# ---------- Slide 2 — Vì sao grid-based? ----------
s = slide_new()
header(s, "VẤN ĐỀ", "Vì sao grid-based? Vì sao STING?", 2)
bullets(s, 0.55, 1.5, 6.6, 5.4, [
    ("Bài toán.", "Nhóm cụm 63 tỉnh × 14 năm (882 dòng, ≥41 cột — vượt chuẩn ≥500×10)."),
    ("Grid-based.", "Chia không gian thành lưới; mỗi ô lưu thống kê; không giả định hình dạng cụm; O(n)."),
    ("STING.", "Lưới phân cấp theo factor; mỗi ô: count/mean/std/min/max; ô “dày” ghép cụm; điểm lẻ = nhiễu."),
    ("Khác biệt.", "DBSCAN gom theo mật độ điểm-kề; k-means ép mọi điểm về centroid; STING tách nhiễu trung thực."),
], size=16, gap_pt=44)
rect(s, 7.6, 1.45, 5.1, 5.6, LIGHT)
text(s, 7.9, 1.72, 4.6, 0.4, [("SO SÁNH NHANH", 12.5, True, TEAL)])
cmp_rows = [("STING", "lưới + thống kê ô", "O(n)"), ("k-means", "centroid, ép k", "O(n·k·i)"), ("DBSCAN", "mật độ kề điểm", "O(n log n)")]
for i, (a, b, c) in enumerate(cmp_rows):
    y = 2.25 + i * 1.55
    rect(s, 7.9, y, 4.5, 1.15, WHITE)
    text(s, 8.05, y + 0.18, 3.0, 0.7, [(a, 14, True, NAVY), (b, 11, False, GREY)])
    text(s, 10.6, y + 0.18, 1.6, 0.4, [(c, 11, True, TEAL)], align=PP_ALIGN.RIGHT)
note(s, "So sánh ngắn; nhấn mạnh lưới phân cấp + nhiễu tách riêng là lợi thế phương pháp.")

# ---------- Slide 3 — STING cơ chế ----------
s = slide_new()
header(s, "CƠ CHẾ", "STING trong 3 bước", 3)
steps = [
    ("1", "LƯỚI PHÂN CẤP", "Mức 0: 1 ô bao trùm;\nmỗi mức chia mỗi chiều\nthành factor ô mới."),
    ("2", "THỐNG KÊ Ô", "count, mean, std, min, max\ntheo từng chiều —\nquét dữ liệu 1 lượt/mức."),
    ("3", "GOM CỤM", "Ô “dày” (count ≥ min_count)\nliền kề → cụm;\nđiểm ở ô thưa → nhiễu (−1)."),
]
for i, (n, title, body) in enumerate(steps):
    x0 = 0.55 + i * 4.19
    rect(s, x0, 1.5, 3.85, 0.62, TEAL)
    text(s, x0, 1.56, 3.85, 0.4, [(f"BƯỚC {n} — {title}", 14, True, WHITE)], align=PP_ALIGN.CENTER)
    rect(s, x0, 2.12, 3.85, 2.55, LIGHT)
    text(s, x0 + 0.22, 2.62, 3.41, 1.9, [(body, 15.5, False, INK)])
text(s, 0.55, 5.35, 12.23, 1.6, [
    ("Chi phí xây lưới O(n) · truy vấn vùng dùng thống kê ô · không cần gán cụm trước", 15, True, NAVY),
    ("Nhược điểm: lưới song song trục, nhạy độ phân giải & min_count — nhóm đo độ nhạy, báo cáo trung thực.", 12.5, False, GREY),
])
note(s, "Vẽ 1 lần, chỉ tay 3 ô. Nhấn mạnh O(n) và tách nhiễu.")

# ---------- Slide 4 — Dữ liệu ----------
s = slide_new()
header(s, "DỮ LIỆU", "PAPI: 14 năm × 63 tỉnh, sạch và đã audit", 4)
bullets(s, 0.55, 1.5, 6.7, 5.3, [
    ("Nguồn.", "PAPI 2011–2024 (papi.org.vn) — 14 workbook, 2 định dạng (tỉnh-hàng / ma trận chuyển vị)."),
    ("Panel.", "882 × 41: d1–d6 (mọi năm) + d7/d8 (2018+) + 29 sub-dim; 39 cột số."),
    ("0.0 → NaN.", "“Không có dữ liệu” theo quy ước gói replication Mendeley (đối chiếu khớp 100%)."),
    ("PROVENANCE.", "URL + hash SHA-256 mọi nguồn trong repo — tái lập được."),
    ("Nguồn ngoài (kiểm chứng).", "PCI VCCI–USAID · GSO (dân số, GRDP) · OD Mekong y tế 2020 · WDI — chỉ dùng kiểm chứng ngoại lai, không đưa vào feature."),
], size=16, gap_pt=30)
rect(s, 7.55, 1.35, 5.2, 2.45, RGBColor(0xFD, 0xF3, 0xDC))
text(s, 7.85, 1.55, 4.7, 0.35, [("⚠ GÃY THANG ĐO (phát hiện khi làm sạch)", 13, True, RGBColor(0x8A, 0x5A, 0x00))])
text(s, 7.85, 2.1, 4.8, 1.6, [("23/37 cột chỉ tiêu có bước nhảy trung bình năm > 0.25 điểm (vd sd_5_4 đổi thang 2021; sd_2_1 đổi 2018).", 12.5, False, INK),
                              ("→ Pipeline xuyên năm chỉ dùng chỉ tiêu qua audit; báo cáo ghi rõ.", 12, True, RGBColor(0x8A, 0x5A, 0x00))])
rect(s, 7.55, 4.15, 5.2, 1.85, LIGHT)
text(s, 7.85, 4.4, 4.7, 0.35, [("VÍ DỤ CHỈ TIÊU SẠCH (dùng để phân cụm)", 12, True, TEAL)])
text(s, 7.85, 4.9, 4.8, 0.9, [("sd_4_2 · Kiểm soát tham nhũng dịch vụ công", 12, False, INK),
                              ("sd_6_1 · Y tế công lập — ổn định 2011–2024", 12, False, INK)])
note(s, "Nhấn mạnh: khác biệt dữ liệu thật so với dữ liệu làm sẵn — audit bắt buộc.")

# ---------- Slide 5 — Demo synthetic ----------
s = slide_new()
header(s, "DEMO 1", "STING thực thi đúng trên dữ liệu giả lập", 5)
pic(s, "00_synthetic_sting.png", 0.55, 1.7, h=4.55)
bullets(s, 7.9, 1.8, 4.85, 4.9, [
    ("Dữ liệu.", "2 blob Gauss, 240 điểm, seed 42."),
    ("Kết quả.", "ARI = 0.950 · nhiễu 2.5% · đúng 2 cụm."),
    ("Lưới.", "Factor=4, 3 mức; ô dày → gom cụm."),
    ("Kiểm thử.", "src/sting.py: 28 unit test (pytest) xanh — chính xác thống kê ô từng ô."),
], size=15.5, gap_pt=60)

note(s, "Show hình bên trái; nói ARI và tests.")

# ---------- Slide 6 — Dữ liệu thật 2023 ----------
s = slide_new()
header(s, "DEMO 2", "Kết quả thật: dữ liệu rất đồng nhất", 6)
pic(s, "sting_first_real.png", 0.55, 1.55, h=4.15)
bullets(s, 8.1, 1.75, 4.7, 4.9, [
    ("61 điểm/năm", "— không thể đòi cấu trúc tách biệt rõ."),
    ("(a) Lưới thô 3×3:", "k=1 · 55/61 trong vùng dày · nhiễu 10%."),
    ("(b) Lưới mịn 9×9:", "k=3 · nhiễu 31% — độ phân giải đổi quyết định!"),
    ("→ Kết luận:", "cấu trúc PAPI cấp tỉnh/năm khá đồng nhất — báo cáo trung thực, không ép cụm."),
], size=15, gap_pt=50)
note(s, "Đây là phát hiện quan trọng nhất về dữ liệu — trình bày như một kết quả nghiên cứu, không phải thất bại.")

# ---------- Slide 7 — Pipeline dự đoán ----------
s = slide_new()
header(s, "DỰ ĐOÁN", "Hai mô hình local, cùng nạp từ file", 7)
rect(s, 0.6, 1.85, 3.1, 0.72, TEAL)
text(s, 0.6, 1.91, 3.1, 0.4, [("TRAIN 2011–2023", 14, True, WHITE)], align=PP_ALIGN.CENTER)
rect(s, 4.5, 1.7, 3.3, 1.1, LIGHT)
text(s, 4.5, 1.82, 3.3, 0.9, [("models/", 13, True, NAVY), ("sting_predict_model.pkl\nsup_ridge.joblib", 11.5, False, GREY)], align=PP_ALIGN.CENTER)
rect(s, 8.6, 1.85, 3.1, 0.72, GOLD)
text(s, 8.6, 1.91, 3.1, 0.4, [("PREDICT 2024", 14, True, NAVY)], align=PP_ALIGN.CENTER)
for x0 in (3.7, 7.8):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x0), Inches(2.01), Inches(0.8), Inches(0.4))
    a.fill.solid()
    a.fill.fore_color.rgb = TEAL
    a.line.fill.background()
bullets(s, 0.6, 3.9, 12.1, 3.0, [
    ("STING.predict (không giám sát).", "Gán tính vào ô lưới đã học; điểm ngoài vùng học → −1. 2024 là năm out-of-sample duy nhất khi chọn cấu hình."),
    ("Chọn cấu hình train-only.", "Quét ứng viên ≤2020; kiểm trên tương lai giả 2021–2022; 2024 không tham gia chọn (tránh selection-on-test) — predict_sweep.py."),
    ("Model giám sát (Ridge/RF).", "Dự báo “6.1 Y tế công lập” năm sau từ 8 chỉ tiêu sạch năm nay; Ridge được chọn, MAE thấp hơn carry-forward 6.3%; RF 9.8% nhưng CV R² thấp hơn nên không chọn (holdout 2023→2024)."),
], size=14.5, gap_pt=28)
note(s, "Vẽ tay sơ đồ 3 khối; nhấn: không có dịch vụ ngoài — mọi model lưu local.")

# ---------- Slide 8 — Kết quả dự đoán ----------
s = slide_new()
header(s, "KẾT QUẢ DỰ ĐOÁN 2024", "48 tỉnh vào cụm lớn · 13 tỉnh ngoại vi", 8)
pic(s, "predict_2024.png", 0.55, 1.3, h=4.9)
bullets(s, 8.15, 1.75, 4.6, 5.0, [
    ("Phủ 79%", "(48/61 có đủ chỉ tiêu)."),
    ("13 tỉnh", "rơi vào ô thưa → nhiễu (không ép vào cụm)."),
    ("Độ nhạy", "coverage 82% (mc=3) → 79% (mc=5) → 70% (mc=8) — ngưỡng-phụ thuộc, báo cáo bảng."),
    ("Chuyển cụm", "0 “chuyển thật” (phát biểu rỗng — cả 2023 lẫn 2024 không có điểm cụm 0/1), 7 sang nhiễu, 5 từ nhiễu ra."),
], size=14, gap_pt=52)
note(s, "Đọc 4 con số chính; kết thúc: 2024 là năm test thật sự. Caveat: “0 chuyển thật” là phát biểu rỗng (vacuous) — cả 2023 lẫn 2024 không có điểm nào thuộc cụm 0/1, nên 0/59 không chứng minh độ ổn định nhãn (báo cáo §5.5).")

# ---------- Slide 9 — Model giám sát ----------
s = slide_new()
header(s, "MODEL GIÁM SÁT", "Ridge dự báo 6.1 Y tế công lập năm sau", 9)
pic(s, "supervised_regression.png", 0.55, 1.7, h=3.85)
bullets(s, 8.2, 1.75, 4.6, 5.0, [
    ("Đặc trưng.", "8 chỉ tiêu sạch năm t (sd 2011–2024 ổn định)."),
    ("CV train-only.", f"Expanding origin 2017–2022; chọn Ridge (CV R² 0.265; RF 0.197); hai baseline cũng có CV thật trên cùng fold — carry {CV_CARRY} vs ridge {CV_RIDGE}."),
    ("Holdout 2023→2024.", "MAE 0.0640 (Ridge, −6.3%) / 0.0616 (RF, −9.8%, không chọn) vs carry-forward 0.0683."),
    ("Phân loại pseudo-label STING.", "LR/RF vượt majority trên một holdout (acc 0.644/0.678 vs 0.186; F1 0.541/0.600 vs 0.157); một năm không kết luận tổng quát."),
], size=13, gap_pt=34)
note(s, f"Nhấn: cải thiện khiêm tốn, honest; 1 holdout duy nhất — cần thêm năm để chắc chắn. Nếu hỏi 'baseline có chạy CV không?': có — cùng 6 fold, carry {CV_CARRY} vs ridge {CV_RIDGE} (trung bình train âm), Ridge vẫn được chọn; caveat: một holdout không chứng minh tổng quát.")

# ---------- Slide 10 — Baselines ----------
s = slide_new()
header(s, "SO SÁNH", "STING vs k-means vs DBSCAN (pooled 2011–2023)", 10)
rows = [
    ("Method", "k", "Noise", "Silh.", "ARI vs STING"),
    ("STING (frozen)", "3", "20%", "0.361*", "—"),
    ("k-means k=2", "2", "0%", "0.445", "0.166"),
    ("k-means k=3", "3", "0%", "0.336", "0.139"),
    ("DBSCAN eps=0.2", "5", "14%", "0.218*", "0.647"),
    ("DBSCAN eps=0.4+", "1", "≤3%", "n/a", "≤0.135"),
]
tb = s.shapes.add_table(len(rows), 5, Inches(0.6), Inches(1.5), Inches(12.18), Inches(3.7)).table
tb.columns[0].width = Inches(3.3)
for c in range(1, 5):
    tb.columns[c].width = Inches(2.22)
tb.rows[0].height = Inches(0.6)
for r_i in range(1, len(rows)):
    tb.rows[r_i].height = Inches(0.62)
for i, row in enumerate(rows):
    for j, v in enumerate(row):
        cell = tb.cell(i, j)
        cell.margin_left = Inches(0.06)
        cell.margin_top = Inches(0.02)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.text = v
        p = tf.paragraphs[0]
        r = p.runs[0]
        r.font.size = Pt(13)
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
text(s, 0.6, 5.6, 12, 0.8, [
    ("* Metric hình học tính trên điểm thuộc cụm (loại −1). k-means ép mọi điểm vào cụm.", 12, False, GREY),
    ("STING ≈ DBSCAN khi eps nhỏ (ARI 0.65); k-means tách khác nhau — dữ liệu gần như một khối.", 12, False, GREY),
])
note(s, "Chỉ vào hàng STING; giải thích vì sao noise được tách.")

# ---------- Slide 11 — Bản đồ ----------
s = slide_new()
header(s, "BẢN ĐỒ", "61/63 tỉnh có điểm 2024 — 13 ngoại vi rải rác", 11)
pic(s, "map_2024.png", 0.55, 1.3, h=5.75)
bullets(s, 5.6, 1.8, 7.15, 4.9, [
    ("Join qua code.", "GeoJSON 'AD01' → centroids theo province_code (63/63). Vĩnh Phúc, Tiền Giang thiếu điểm 2024."),
    ("2024.", "48 tỉnh cụm lớn (xanh), 13 tỉnh nhiễu (xám, chú thích tên)."),
    ("2020 vs 2024.", "Hai mốc — cùng lưới toàn cục nên nhãn so sánh được giữa các năm."),
    ("Ý nghĩa.", "Nhóm ngoại vi rải đều các miền — không phải một vùng địa lý riêng."),
], size=15, gap_pt=56)
note(s, "Chỉ tay 2–3 tỉnh nhiễu rải rác (Quảng Ninh, Hà Nội, Cà Mau). 61 dot = 48 cụm lớn + 13 nhiễu; Vĩnh Phúc/Tiền Giang không có điểm 2024. Lào Cai, Điện Biên thuộc cụm lớn (xanh).")

# ---------- Slide 12 — Hạn chế ----------
s = slide_new()
header(s, "TRUNG THỰC", "Hạn chế — nói rõ trước khi được hỏi", 12)
bullets(s, 0.55, 1.7, 12.2, 5.2, [
    ("Đồng nhất.", "Dữ liệu PAPI cấp tỉnh/năm gần như một khối — cấu trúc tách biệt chỉ ở ngoại vi nhỏ."),
    ("Gãy thang đo.", "23/37 cột đổi thang giữa các năm; phân tích xuyên năm chỉ dùng chỉ tiêu qua audit."),
    ("Robustness OFAT.", f"PCA d1–d6 ({_pct(R_PCA['explained_var_total'])} phương sai) → không nhận diện; 8 chiều 2018–2024 so với gốc (k={R_GOC['k']}, nhiễu {_pct(R_GOC['noise_ratio'])}): f=3 → k={R_F3['k']}/{_pct(R_F3['noise_ratio'])}, lv=2 → k={R_LV2['k']}/100% → không nhận diện; mc=2 → k={R_MC2['k']}/{_pct(R_MC2['noise_ratio'])} đạt ngưỡng k/noise NHƯNG silhouette âm — tách yếu."),
    ("Metrics không bản địa.", "Silhouette/DB/CH với lưới song song trục chỉ để so sánh thô; noise tách riêng."),
    ("Một holdout.", "2024 là năm test duy nhất; Ridge (được chọn) thấp hơn carry-forward 6.3% MAE — cần thêm năm để khẳng định."),
], size=15.5, gap_pt=40)
note(s, "Đây là slide ghi điểm: tự nêu hạn chế trước, Q&A sẽ dễ trả lời.")

# ---------- Slide 13 — Kế hoạch cuối kỳ ----------
s = slide_new()
header(s, "LỘ TRÌNH", "Cuối kỳ: từ demo đến báo cáo", 13)
steps = [
    ("P5 · Cuối tháng 12", "Baselines đầy đủ · robustness PCA · bản đồ & evolution · bảng metrics"),
    ("P6 · Đầu tháng 1", "Báo cáo .docx (7 chương, tiếng Việt) · notebook cuối chạy sạch · Q&A ≥12 câu · mock defense"),
    ("P7 · Giữa tháng 1", "Buffer + nộp bài · tag v1.0-final · checklist nộp"),
]
for i, (a, b) in enumerate(steps):
    y = 1.5 + i * 1.5
    rect(s, 0.6, y, 3.1, 1.25, TEAL if i == 0 else (GOLD if i == 1 else RGBColor(0x33, 0x41, 0x55)))
    text(s, 0.72, y + 0.18, 2.9, 0.9, [(a, 15, True, WHITE)])
    rect(s, 3.7, y, 8.95, 1.25, LIGHT)
    text(s, 4.0, y + 0.14, 8.4, 1.0, [(b, 11.5, False, INK)])
note(s, "Nói ngắn: cuối kỳ làm gì, khi nào, deliverable gì.")

# ---------- Slide 14 — Kiểm chứng ngoại lai ----------
s = slide_new()
header(s, "KIỂM CHỨNG NGOẠI LAI", "Cụm STING khớp PCI — thước đo độc lập", 14)
pic(s, "external_pci_by_cluster.png", 0.55, 1.45, h=4.75)
bullets(s, 8.0, 1.5, 4.8, 4.8, [
    ("PCI.", "Khảo sát DOANH NGHIỆP (VCCI–USAID) — tách khỏi PAPI (hộ dân); chưa từng dùng khi học."),
    ("756 ô 2011–2022.", "Join 747 điểm có nhãn — {nhiễu: 149, cụm 0: 5, cụm 1: 16, cụm 2: 577}."),
    ("Ý nghĩa thống kê.", "ANOVA F(3,743) = 9.04, p = 6.9e-06 · Kruskal–Wallis H = 31.78, p = 5.8e-07."),
    ("Đọc thận trọng.", "Tương phản đáng tin: nhiễu vs cụm 2 (hai cụm nhỏ n=5/16); không chứng minh nhân quả."),
    ("Nguồn khác.", "Y tế/1.000 dân 2020 · GRDP 2018–2024 · WDI — results/external_validation.md."),
], size=13, gap_pt=32)
note(s, "External validation đúng nghĩa: cấu trúc học không giám sát khớp một thước đo độc lập chưa từng dùng khi học. Nhấn: PCI là khảo sát doanh nghiệp, PAPI là khảo sát hộ dân — hai đường ống dữ liệu khác nhau. Cụm 0/1 quá nhỏ để tự kết luận; đọc cặp nhiễu vs cụm 2; không chứng minh nhân quả. Chi tiết: results/external_validation.md; provenance: data/processed/external_provenance.md.")

# ---------- Slide 15 — Tài liệu ----------
s = slide_new()
header(s, "NGUỒN", "Tài liệu tham khảo & dữ liệu mở", 15)
bullets(s, 0.55, 1.35, 12.1, 5.4, [
    ("PAPI 2011–2024.", "CECODES/VFF-CRT/RTA/UNDP — papi.org.vn."),
    ("Gói replication.", "Le et al., Mendeley Data — DOI 10.17632/wbk42j9wc8.1 · CC BY 4.0 (4 file dùng trực tiếp đã commit)."),
    ("STING gốc.", "Wang, Yang & Muntz (1997), “STING: A Statistical Information Grid Approach to Spatial Data Mining”, VLDB."),
    ("GeoJSON ranh giới.", "Open Development Vietnam (OD Mekong) — CC-BY-SA 4.0."),
    ("Nguồn ngoài kiểm chứng.", "PCI VCCI–USAID (công khai) · GSO PX-Web (“Bản quyền: Không”) · OD Mekong Health 2020 (ODbL) · WDI (CC BY 4.0) — data/processed/external_provenance.md."),
    ("Code & dữ liệu.", "Repo gồm: src/sting.py (28 unit test) · scripts/ · tests/ · models/ · results/ · PROVENANCE.md từng nguồn."),
], size=14.5, gap_pt=40, gap_first=14)
note(s, "Nếu GV hỏi về nguồn: chỉ PROVENANCE.md trong repo (data/raw/*/PROVENANCE.md + data/processed/external_provenance.md).")

# ---------- Slide 16 — Q&A ----------
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
text(s, 0.2, 1.3, SW, 1.5, [("Q & A", 88, True, GOLD)], align=PP_ALIGN.CENTER)
text(s, 0.2, 3.0, SW, 0.6, [("5 phút phản biện — nhóm sẵn sàng cho mọi câu hỏi.", 26, True, WHITE)], align=PP_ALIGN.CENTER)
bullets(s, 2.0, 4.65, 9.53, 2.4, [
    ("Câu hỏi đầu tiên.", "“Vì sao grid-based?”"),
    ("Nghi thức phản biện.", "Nếu không chắc — nhóm nói thẳng “chưa chắc, sẽ kiểm và trả lời”."),
], size=19, color=WHITE, bold_first=True, lead_color=GOLD, align=PP_ALIGN.CENTER, hang_in=0, gap_pt=26)
note(s, "Kết thúc: cảm ơn + mời GV hỏi. Không đọc slide.")

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print("saved:", OUT)
print("slides:", len(prs.slides._sldIdLst))
