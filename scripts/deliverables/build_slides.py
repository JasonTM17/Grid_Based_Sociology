"""Build slides/final.pptx — 16 trang 16:9, tiếng Việt, có ghi chú người nói.

Cách dùng: python scripts/deliverables/build_slides.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

ROOT = Path(__file__).resolve().parents[2]
FIGS = ROOT / "results" / "figs"
OUT = ROOT / "slides" / "final.pptx"

# Số liệu đọc từ artifact do script khác sinh (không hardcode số đo)


def _read_results_csv(name):
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pct(v):
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


ROBUSTNESS = _read_results_csv("robustness.csv")
ASSIGNMENTS = _read_results_csv("predict_all_years.csv")
MAIN_CLUSTER = Counter(r["pred_cluster"] for r in ASSIGNMENTS
                       if r["split"] == "train" and r["pred_cluster"] != "-1").most_common(1)[0][0]
LABELS_2023 = {r["province_code"]: r["pred_cluster"] for r in ASSIGNMENTS if r["year"] == "2023"}
LABELS_2024 = {r["province_code"]: r["pred_cluster"] for r in ASSIGNMENTS if r["year"] == "2024"}
TRANSITIONS = Counter((LABELS_2023[p], LABELS_2024[p]) for p in LABELS_2023.keys() & LABELS_2024.keys())
assert all({left, right} <= {MAIN_CLUSTER, "-1"} for left, right in TRANSITIONS)


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

FORECAST = json.loads((ROOT / "results" / "papi_forecast_2024.json").read_text(encoding="utf-8"))
SCORES = {(row["target"], row["method"]): row for row in FORECAST["scores"]}
ZONES = {row["method"]: row for row in FORECAST["grid"]}
N_COMPARED = FORECAST["comparable_count"]
N_OUTSIDE = FORECAST["actual_outside"]


def _dec(value, digits=4):
    return f"{value:.{digits}f}".replace(".", ",")


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


# Slide 1 — Bìa
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
# lưới motif 4x4
for r in range(4):
    for c in range(4):
        x0, y0 = SW - 4.6 + c * 0.78, 1.05 + r * 0.78
        fill = GOLD if (r, c) in ((1, 1), (2, 2)) else RGBColor(0x1E, 0x3D, 0x5E)
        rect(s, x0, y0, 0.66, 0.66, fill)
text(s, 0.85, 1.15, 7.6, 0.4, [("HỌC MÁY · BÁO CÁO CUỐI KỲ", 15, True, GOLD)])
text(s, 0.85, 1.75, 7.7, 1.48, [("Phân cụm dựa trên lưới STING", 38, True, WHITE)])
text(s, 0.85, 3.42, 7.7, 0.6, [("Phân tích dữ liệu PAPI 2011–2024", 22, False, WHITE)])
text(s, 0.85, 4.9, 7.8, 1.3, [
    ("Nhóm 15 · Chủ đề 6 · Grid-based clustering", 15, True, GOLD),
    ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 15, False, RGBColor(0xB9, 0xCD, 0xDE)),
])
note(s, "Kính thưa thầy, nhóm 15 xin trình bày kết quả đồ án phân cụm dữ liệu PAPI bằng STING. "
     "Nhóm xây dựng lưới thống kê, kiểm tra trên dữ liệu giả lập, sau đó áp dụng lên hai chỉ tiêu "
     "PAPI của 63 tỉnh trong giai đoạn 2011–2024. Phần cuối trình bày giới hạn và các phân tích bổ trợ.")

# Slide 2 — Vì sao grid-based?
s = slide_new()
header(s, "BÀI TOÁN", "Phân cụm các quan sát tỉnh–năm theo PAPI", 2)
bullets(s, 0.55, 1.5, 6.6, 5.4, [
    ("Dữ liệu.", "882 quan sát. Mỗi quan sát là một tỉnh trong một năm."),
    ("Mục tiêu.", "Tìm các nhóm gần nhau trên hai chỉ tiêu PAPI được chọn."),
    ("STING rút gọn.", "Chia không gian thành lưới, lưu thống kê và gom ô dày liên thông."),
    ("Đối chứng.", "So sánh STING với K-means và DBSCAN trên cùng hai chỉ tiêu."),
], size=17, gap_pt=34)
rect(s, 7.6, 1.45, 5.1, 5.6, LIGHT)
text(s, 7.9, 1.72, 4.6, 0.4, [("CƠ SỞ TẠO CỤM", 13, True, TEAL)])
cmp_rows = [("STING", "Ô lưới", "Mật độ ô"),
            ("K-means", "Tâm cụm", "Khoảng cách"),
            ("DBSCAN", "Lân cận điểm", "Mật độ điểm")]
for i, (a, b, c) in enumerate(cmp_rows):
    y = 2.25 + i * 1.55
    rect(s, 7.9, y, 4.5, 1.15, WHITE)
    text(s, 8.05, y + 0.18, 3.0, 0.7, [(a, 14, True, NAVY), (b, 11, False, GREY)])
    text(s, 10.6, y + 0.18, 1.6, 0.4, [(c, 11, True, TEAL)], align=PP_ALIGN.RIGHT)
note(s, "Đơn vị phân tích là quan sát tỉnh–năm. Nhóm dùng biến thể STING rút gọn, xác định "
     "vùng dày bằng số điểm trong ô lưới. K-means dựa vào khoảng cách đến tâm cụm, còn DBSCAN "
     "dựa vào mật độ lân cận từng điểm. Ba cách tạo cụm được đối chiếu trong phần thực nghiệm.")

# Slide 3 — STING cơ chế
s = slide_new()
header(s, "CƠ CHẾ GRID-BASED", "Biến thể STING của nhóm trong 3 bước", 3)
steps = [
    ("1", "LƯỚI PHÂN CẤP", "Mức 0 có một ô bao trùm.\nMỗi mức tiếp theo chia nhỏ\ncác ô của mức trước."),
    ("2", "THỐNG KÊ Ô", "Lưu số điểm, trung bình,\nđộ lệch chuẩn và các\ngiá trị nhỏ nhất, lớn nhất."),
    ("3", "GOM CỤM", "Ô có số điểm ≥ min_count\nđược nối qua cạnh.\nÔ thưa nhận nhãn nhiễu −1."),
]
for i, (n, title, body) in enumerate(steps):
    x0 = 0.55 + i * 4.19
    rect(s, x0, 1.5, 3.85, 0.62, TEAL)
    text(s, x0, 1.56, 3.85, 0.4, [(f"BƯỚC {n} — {title}", 14, True, WHITE)], align=PP_ALIGN.CENTER)
    rect(s, x0, 2.12, 3.85, 2.55, LIGHT)
    text(s, x0 + 0.22, 2.62, 3.41, 1.9, [(body, 15.5, False, INK)])
text(s, 0.55, 5.35, 12.23, 1.6, [
    ("Số cụm được xác định từ các vùng ô dày liên thông tại mức lưới đã chọn.", 16, True, NAVY),
    ("Độ phân giải lưới và ngưỡng min_count ảnh hưởng đến số cụm và tỷ lệ nhiễu.", 15, False, GREY),
    ("Cài đặt dùng ngưỡng số đếm. STING gốc còn dùng phân phối và kiểm định thống kê.", 14, False, GREY),
])
note(s, "Cài đặt gồm ba bước. Đầu tiên chia không gian thành lưới phân cấp, tiếp theo tính thống kê "
     "cho từng ô, cuối cùng gom các ô đạt min_count và liên thông qua cạnh. Nhóm chọn một mức lưới "
     "để phân cụm. STING gốc của Wang, Yang và Muntz còn mô hình hóa loại phân phối và "
     "dùng kiểm định thống kê để duyệt từ trên xuống. Biến thể này dùng ngưỡng số đếm.")

# Slide 4 — Dữ liệu
s = slide_new()
header(s, "DỮ LIỆU", "PAPI 2011–2024 và lựa chọn chỉ tiêu", 4)
bullets(s, 0.55, 1.5, 6.7, 5.3, [
    ("Nguồn.", "14 workbook PAPI do CECODES, VFF-CRT, RTA và UNDP công bố."),
    ("Bảng dữ liệu.", "882 dòng và 41 cột. Có 8 chiều nội dung và 29 chỉ tiêu thành phần."),
    ("Giá trị thiếu.", "Chuyển điểm 0 theo quy ước nguồn về NaN và chọn dòng đủ hai chỉ tiêu."),
    ("Chuẩn hóa.", "Ước lượng trung bình và độ lệch chuẩn từ dữ liệu huấn luyện."),
    ("Đối chiếu.", "5.118 cặp giá trị hợp lệ trên 8 chỉ số nội dung 2011–2022 khớp gói dữ liệu Le và cộng sự."),
], size=16, gap_pt=25)
rect(s, 7.55, 1.35, 5.2, 2.45, RGBColor(0xFD, 0xF3, 0xDC))
text(s, 7.85, 1.55, 4.7, 0.35, [("KIỂM TRA TÍNH SO SÁNH QUA CÁC NĂM", 13, True, RGBColor(0x8A, 0x5A, 0x00))])
text(s, 7.85, 2.1, 4.65, 1.5, [
    ("23/37 chỉ tiêu có biến động trung bình giữa hai năm liên tiếp vượt 0,25.", 14, False, INK),
    ("Nhóm đối chiếu thang đo với workbook trước khi chọn chỉ tiêu.", 14, True, RGBColor(0x8A, 0x5A, 0x00)),
])
rect(s, 7.55, 4.15, 5.2, 1.85, LIGHT)
text(s, 7.85, 4.4, 4.7, 0.35, [("HAI CHỈ TIÊU DÙNG CHO PHÂN CỤM", 13, True, TEAL)])
text(s, 7.85, 4.9, 4.8, 0.9, [("sd_4_2 · Kiểm soát tham nhũng dịch vụ công", 14, False, INK),
                              ("sd_6_1 · Y tế công lập", 14, False, INK)])
note(s, "Nhóm thống nhất hai định dạng workbook thành bảng tỉnh–năm. Các chiều d7 và d8 chỉ có "
     "từ năm 2018, vì vậy cần kiểm tra độ phủ trước khi mở rộng đặc trưng. Quy tắc chênh lệch "
     "trung bình lớn hơn 0,25 giúp nhận diện chỉ tiêu cần rà soát. Đây là dấu hiệu để đối chiếu "
     "nguồn, chưa đủ để kết luận mọi chỉ tiêu bị đánh dấu đều đổi thang. Ví dụ sd_5_4 đổi thang "
     "năm 2021 đã được đối chiếu với workbook.")

# Slide 5 — Demo synthetic
s = slide_new()
header(s, "DỮ LIỆU GIẢ LẬP", "Đối chiếu kết quả với hai cụm đã biết", 5)
pic(s, "00_synthetic_sting.png", 0.55, 1.7, h=4.55)
bullets(s, 7.9, 1.8, 4.85, 4.9, [
    ("Dữ liệu.", "240 điểm từ hai phân bố Gauss, seed 42."),
    ("Kết quả.", "Tìm được 2 cụm và 2,5% điểm nhiễu."),
    ("Đối chiếu.", "ARI bằng 0,950 so với nhãn đã biết khi sinh dữ liệu."),
    ("Kiểm thử.", "Đối chiếu thống kê ô, liên thông, biên lưới và tái lập nhãn bằng pytest."),
], size=17, gap_pt=25)

note(s, "Trên ví dụ 240 điểm, STING tìm được hai cụm với ARI bằng 0,950 và tỷ lệ nhiễu 2,5%. "
     "Các kiểm thử khác đối chiếu thống kê ô, quan hệ liên thông và điểm nằm trên biên. "
     "Kết quả này cho phép kiểm tra cách cài đặt trước khi áp dụng cho dữ liệu PAPI.")

# Slide 6 — Dữ liệu thật 2023
s = slide_new()
header(s, "PAPI NĂM 2023", "Hai cấu hình lưới cho kết quả khác nhau", 6)
pic(s, "sting_first_real.png", 0.55, 1.55, h=4.15)
bullets(s, 8.1, 1.75, 4.7, 4.9, [
    ("Dữ liệu.", "61 tỉnh có đủ hai chỉ tiêu trong năm 2023."),
    ("Lưới 3 × 3.", "Ngưỡng 5 cho 1 cụm, với 55/61 điểm trong vùng dày."),
    ("Lưới 9 × 9.", "Ngưỡng 2 cho 3 cụm và khoảng 31% nhiễu."),
    ("Nhận xét.", "Số cụm và tỷ lệ nhiễu phụ thuộc cấu hình lưới."),
], size=17, gap_pt=28)
note(s, "Hai hình dùng cùng dữ liệu 2023. Lưới 3×3 với ngưỡng 5 cho một cụm, "
     "trong khi lưới 9×9 với ngưỡng 2 cho ba cụm. Cả độ phân giải và ngưỡng đều thay đổi "
     "giữa hai phép thử, nên cần khảo sát riêng từng tham số để đọc ảnh hưởng của chúng.")

# Slide 7 — Quy trình dự báo và lưới STING
s = slide_new()
header(s, "HỌC CÓ GIÁM SÁT VÀ STING", "Dự báo hai điểm PAPI rồi đối chiếu theo vùng", 7)
stages = [
    ("1. DỮ LIỆU ĐẾN 2023", "Tám chỉ tiêu năm t để tạo cặp với điểm năm t+1."),
    ("2. DỰ BÁO NĂM 2024", "Từ điểm năm 2023, dự báo chỉ tiêu 4.2 và 6.1 cho từng tỉnh."),
    ("3. ĐỐI CHIẾU TRÊN LƯỚI", "Đặt điểm dự báo và điểm PAPI thực tế vào cùng lưới STING."),
]
for index, (label, detail) in enumerate(stages):
    x = 0.58 + index * 4.18
    rect(s, x, 1.65, 3.88, 2.35, LIGHT)
    text(s, x + 0.17, 1.89, 3.5, 0.56, [(label, 16, True, TEAL)])
    text(s, x + 0.17, 2.58, 3.53, 1.18, [(detail, 17, False, INK)])
bullets(s, 0.61, 4.35, 12.09, 2.25, [
    ("Chọn theo thời gian.", "Sáu lượt kiểm định cho các năm đích 2018–2023. So với giữ điểm năm trước."),
    ("Lưới cố định.", "STING dùng hai chỉ tiêu đến 2023, mức lưới 16 × 16 và tối thiểu 5 điểm/ô."),
    ("Đánh giá hồi cứu.", "Dùng điểm PAPI 2024 để đối chiếu sau khi đã có dự báo."),
], size=16, gap_pt=14)
note(s, "Bốn ứng viên là giữ điểm năm trước, Ridge, Random Forest, và trung bình của hai mô hình. "
     "Chọn riêng từng chỉ tiêu theo trung bình MAE của sáu lượt kiểm định theo thời gian. "
     "Ở mỗi lượt, năm đích huấn luyện cuối cùng không vượt mốc xuất phát. Hai điểm dự báo năm 2024 "
     "được sinh từ tám điểm năm 2023. Điểm thực tế 2024 dùng để đánh giá sai số và đối chiếu nhãn trên lưới.")

# Slide 8 — Kết quả dự báo liên tục
s = slide_new()
header(s, "DỰ BÁO ĐIỂM", "Sai số dự báo hai chỉ tiêu PAPI năm 2024", 8)
text(s, 0.66, 1.28, 12.0, 0.43, [
    (f"{FORECAST['train_pairs']} cặp lịch sử · {FORECAST['forecast_count']} tỉnh có dự báo · "
     f"{N_COMPARED} tỉnh đối chiếu được", 15, True, TEAL),
], align=PP_ALIGN.CENTER)
pic(s, "papi_forecast_values.png", 0.54, 1.8, w=8.36)
rect(s, 9.07, 1.94, 3.65, 4.45, LIGHT)
bullets(s, 9.25, 2.09, 3.24, 4.04, [
    ("Chỉ tiêu 4.2.", f"MAE {_dec(SCORES['sd_4_2', 'forecast']['mae'])} · "
                     f"giữ điểm 2023 {_dec(SCORES['sd_4_2', 'carry']['mae'])}."),
    ("Chỉ tiêu 6.1.", f"MAE {_dec(SCORES['sd_6_1', 'forecast']['mae'])} · "
                     f"giữ điểm 2023 {_dec(SCORES['sd_6_1', 'carry']['mae'])}."),
    ("Sai số lớn.", "RMSE của chỉ tiêu 4.2 tăng nhẹ."),
], size=15.5, gap_pt=18)
text(s, 0.62, 6.15, 8.4, 0.65, [
    ("Đường chéo biểu thị dự báo bằng điểm thực tế. Hai phương pháp dùng cùng các tỉnh.", 14, False, GREY),
])
note(s, f"Ridge được chọn cho hai chỉ tiêu ở lần kiểm định trước 2024. Trên cùng {N_COMPARED} tỉnh, "
     f"RMSE 4.2 là {_dec(SCORES['sd_4_2', 'forecast']['rmse'])} so với {_dec(SCORES['sd_4_2', 'carry']['rmse'])}. "
     f"RMSE 6.1 là {_dec(SCORES['sd_6_1', 'forecast']['rmse'])} so với {_dec(SCORES['sd_6_1', 'carry']['rmse'])}. "
     "RMSE nhạy với sai số lớn hơn MAE. Kết quả mô tả một năm hồi cứu.")

# Slide 9 — Đối chiếu trên lưới và độ nhạy
s = slide_new()
header(s, "ĐỐI CHIẾU TRÊN LƯỚI", "Dự báo điểm bỏ sót các tỉnh ngoài vùng dày", 9)
text(s, 0.67, 1.28, 12.03, 0.42, [
    (f"Cùng lưới đến 2023 · Cùng {N_COMPARED} tỉnh có đủ hai điểm thực tế", 15, True, TEAL),
], align=PP_ALIGN.CENTER)
pic(s, "papi_forecast_grid.png", 0.54, 1.87, w=8.46)
rect(s, 9.15, 1.86, 3.61, 4.93, LIGHT)
bullets(s, 9.34, 2.06, 3.18, 4.51, [
    ("Dự báo điểm.", f"{ZONES['forecast']['out_correct']}/{N_OUTSIDE} tỉnh ngoài vùng dày được nhận ra."),
    ("Giữ điểm 2023.", f"Nhận ra {ZONES['carry']['out_correct']}/{N_OUTSIDE} tỉnh ngoài vùng, "
                       f"với {ZONES['carry']['false_out']} trường hợp gán ngoài nhầm."),
    ("Kịch bản sai số.", f"AUC xếp hạng {_dec(FORECAST['scenario_auc'], 3)} trên năm 2024."),
], size=15, gap_pt=15)
text(s, 0.62, 6.1, 8.48, 0.64, [
    ("Ô tô nhạt là vùng dày của lưới lịch sử. Dấu × là điểm ngoài vùng dày.", 14, False, GREY),
])
note(s, f"Mọi dự báo điểm rơi vào cụm lớn. Trùng nhãn lưới {_pct(ZONES['forecast']['exact_label_agreement'])}, "
     "bằng đối chứng luôn chọn cụm lớn. Trên 59 tỉnh, điểm dự báo bỏ sót 11 tỉnh có PAPI thực tế "
     f"ngoài vùng dày. Độ đúng cân bằng hai vùng là {_pct(ZONES['forecast']['balanced_zone_accuracy'])}, "
     f"so với {_pct(ZONES['carry']['balanced_zone_accuracy'])} khi giữ điểm 2023. "
     f"Cho từng tỉnh, {FORECAST['scenario_count']} cặp sai số ngoài lượt kiểm định năm 2018–2023 "
     "được cộng vào dự báo và đưa qua lưới. Tỷ lệ kịch bản ngoài vùng dùng để xếp hạng trong phân tích "
     "thăm dò trên năm 2024. Tỷ lệ kịch bản là thước đo độ nhạy theo sai số quá khứ.")

# Slide 10 — Baselines
s = slide_new()
header(s, "ĐỐI CHỨNG PHÂN CỤM", "STING, K-means và DBSCAN trên PAPI 2011–2023", 10)
result_table(s, [
    ("Phương pháp", "Số cụm", "Nhiễu", "Điểm thuộc cụm", "Silhouette riêng", "Silhouette trên tập giao"),
    ("STING", 3, "19,6%", 650, "0,361", "0,366"),
    ("K-means (k = 2)", 2, "0%", 808, "0,445", "0,457"),
    ("DBSCAN (eps = 0,2)", 5, "14,2%", 693, "0,218", "0,258"),
], 0.6, 1.67, [2.62, 1.24, 1.3, 2.06, 2.16, 2.8], 0.71, 15)
text(s, 0.6, 4.88, 12, 0.92, [
    ("Cùng một tập giao gồm 631/808 điểm được cả STING và DBSCAN gán vào cụm.", 16, True, NAVY),
    ("ARI STING–DBSCAN là 0,647 trên toàn mẫu và 0,431 trên tập giao.", 15, False, GREY),
])
note(s, "Bảng đối chiếu các cấu hình trên cùng hai chỉ tiêu PAPI của giai đoạn 2011–2023. "
     "Silhouette riêng dùng mẫu thuộc cụm của từng phương pháp. Cột cuối giữ các nhãn "
     "đã học và chấm ba phương pháp trên cùng 631 điểm, tức giao các điểm được cả STING "
     "và DBSCAN gán cụm. ARI đo mức đồng thuận giữa phân hoạch STING và DBSCAN. "
     "Trên toàn mẫu, giá trị này tính cả nhãn nhiễu. Notebook tính lại hai phép đối chiếu.")

# Slide 11 — Bản đồ
s = slide_new()
header(s, "BẢN ĐỒ NĂM 2024", "Phân bố các tỉnh theo nhãn STING", 11)
pic(s, "map_2024.png", 0.55, 1.3, h=5.75)
bullets(s, 5.6, 1.8, 7.15, 4.9, [
    ("Cụm lớn.", "48 tỉnh được biểu diễn bằng màu xanh."),
    ("Nhiễu.", "13 tỉnh màu xám nằm rải rác ở nhiều vùng."),
    ("Thiếu dữ liệu.", "Vĩnh Phúc và Tiền Giang thiếu một trong hai chỉ tiêu."),
    ("Cách đọc.", "Vị trí trên bản đồ thể hiện địa lý. Nhãn cụm được xác định từ hai chỉ tiêu PAPI."),
], size=17, gap_pt=29)
note(s, "Bản đồ nối nhãn STING với vị trí tỉnh thông qua mã tỉnh. Màu xanh biểu diễn 48 tỉnh "
     "thuộc cụm lớn, màu xám biểu diễn 13 tỉnh nhiễu. Vĩnh Phúc và Tiền Giang thiếu dữ liệu "
     "để gán nhãn. Các tỉnh nhiễu phân bố ở nhiều vùng. Đặc trưng phân cụm là hai chỉ tiêu PAPI, "
     "còn tọa độ địa lý dùng để trình bày kết quả trên bản đồ.")

# Slide 12 — Dịch chuyển và giới hạn
s = slide_new()
header(s, "THẢO LUẬN", "Dịch chuyển trên cùng lưới STING từ 2023 sang 2024", 12)
result_table(s, [
    ("Năm 2023 / Năm 2024", "Cụm lớn", "Nhiễu"),
    ("Cụm lớn", TRANSITIONS[MAIN_CLUSTER, MAIN_CLUSTER], TRANSITIONS[MAIN_CLUSTER, "-1"]),
    ("Nhiễu", TRANSITIONS["-1", MAIN_CLUSTER], TRANSITIONS["-1", "-1"]),
], 0.6, 1.85, [3.05, 1.48, 1.48], 0.82, 16)
text(s, 0.6, 4.7, 6.0, 1.0, [
    (f"{TRANSITIONS.total()} tỉnh có đủ dữ liệu ở cả hai năm.", 16, True, NAVY),
    ("Bảng dùng cùng bộ chuẩn hóa và lưới đã học.", 15, False, GREY),
])
bullets(s, 6.95, 1.88, 5.75, 4.55, [
    ("Chuyển trạng thái.", f"{TRANSITIONS[MAIN_CLUSTER, '-1']} tỉnh sang nhiễu, "
     f"{TRANSITIONS['-1', MAIN_CLUSTER]} tỉnh vào cụm lớn."),
    ("Hai cụm nhỏ.", "Chỉ có điểm giai đoạn 2011–2018."),
    ("Phạm vi.", "Dịch chuyển phản ánh hai chỉ tiêu PAPI trên lưới cố định."),
], size=17, gap_pt=25)
note(s, f"Trong {TRANSITIONS.total()} tỉnh đủ dữ liệu cả hai năm, 47 tỉnh giữ trạng thái và 12 tỉnh đổi trạng thái. "
     "Nhãn nhiễu biểu thị vị trí ngoài vùng ô dày; điểm gần biên có thể đổi trạng thái khi chỉ tiêu biến động nhỏ. "
     "Hai năm cuối chỉ có quan sát thuộc cụm lớn hoặc nhiễu. "
     f"Kết quả cần được đọc trong phạm vi hai chỉ tiêu và các cấu hình đã thử. "
     f"Hai thành phần PCA đầu giữ {_pct(R_PCA['explained_var_total'])} phương sai. "
     f"Ở nhánh 8 chiều, cấu hình gốc cho {R_GOC['k']} cụm và {_pct(R_GOC['noise_ratio'])} nhiễu. "
     f"Khi chỉ thay factor thành 3, kết quả còn {R_F3['k']} cụm và {_pct(R_F3['noise_ratio'])} nhiễu. "
     f"Đổi mức lưới cho {R_LV2['k']} cụm. Giảm ngưỡng còn 2 cho {R_MC2['k']} cụm "
     f"với {_pct(R_MC2['noise_ratio'])} nhiễu, nhưng silhouette âm. "
     "Các phép thử bổ sung cho thấy cần thận trọng khi diễn giải cụm ở số chiều cao hơn.")

# Slide 13 — Kế hoạch cuối kỳ
s = slide_new()
header(s, "KẾT LUẬN", "Kết quả chính và hướng phát triển", 13)
steps = [
    ("PHƯƠNG PHÁP", "Cài đặt STING dựa trên lưới phân cấp, thống kê ô và liên thông giữa các ô dày."),
    ("THỰC NGHIỆM", "Dự báo hai điểm và đo sai số. Khi chiếu lên lưới, dự báo điểm nghiêng về cụm lớn."),
    ("HƯỚNG PHÁT TRIỂN", "Đánh giá trên thêm các năm dữ liệu và các bộ chỉ tiêu có thang đo tương thích."),
]
for i, (a, b) in enumerate(steps):
    y = 1.5 + i * 1.5
    rect(s, 0.6, y, 3.1, 1.25, TEAL if i == 0 else (GOLD if i == 1 else RGBColor(0x33, 0x41, 0x55)))
    text(s, 0.72, y + 0.18, 2.9, 0.9, [(a, 15, True, WHITE)])
    rect(s, 3.7, y, 8.95, 1.25, LIGHT)
    text(s, 4.0, y + 0.14, 8.4, 1.0, [(b, 18, False, INK)])
note(s, "Nhóm đã cài đặt biến thể STING và kiểm tra cách chia lưới, thống kê ô, gom cụm và gán "
     "điểm mới. Trên hai chỉ tiêu PAPI, kích thước cụm chênh lệch và độ nhạy tham số là những "
     "yếu tố cần chú ý khi đọc kết quả. Hướng tiếp theo là mở rộng mốc thời gian đánh giá "
     "và đối chiếu thêm các bộ chỉ tiêu có thang đo tương thích. Hai tệp nộp chính là "
     "Nhom15_CuoiKy_STING_PAPI.docx và Nhom15_CuoiKy_STING_PAPI.ipynb.")

# Slide 14 — Kiểm chứng bên ngoài
s = slide_new()
header(s, "PHÂN TÍCH BỔ TRỢ", "Đối chiếu các nhóm STING với dữ liệu PCI", 14)
pic(s, "external_pci_by_cluster.png", 0.55, 1.45, h=4.75)
bullets(s, 8.0, 1.5, 4.8, 4.8, [
    ("Nguồn đối chiếu.", "PCI khảo sát doanh nghiệp, do VCCI–USAID công bố."),
    ("Dữ liệu ghép.", "747 quan sát có nhãn STING trong giai đoạn 2011–2022."),
    ("Kiểm định.", "ANOVA cho F=9,04, p<0,001. Kruskal–Wallis cho H=31,78, p<0,001."),
    ("Giới hạn.", "Kiểm định gộp chưa hiệu chỉnh quan sát lặp theo tỉnh và năm; hai cụm nhỏ chỉ có 5 và 16 điểm."),
], size=16, gap_pt=28)
note(
    s,
    "PCI cung cấp nguồn đối chiếu về cảm nhận của doanh nghiệp. Nhóm ghép được 747 quan sát "
    "có nhãn STING, gồm 149 điểm nhiễu, 5 điểm cụm 0, 16 điểm cụm 1 và 577 điểm cụm 2. "
    "Các p-value gộp chỉ mang tính tham khảo vì chưa hiệu chỉnh sự phụ thuộc giữa các quan sát cùng tỉnh và giữa các năm. "
    "Cỡ cụm chênh lệch lớn và phép thử hiện gộp nhiều năm, nên kết quả chỉ là bằng chứng "
    "mô tả bổ sung. Nguồn số liệu là results/external_validation.md.",
)

# Slide 15 — Tài liệu
s = slide_new()
header(s, "TÀI LIỆU THAM KHẢO", "Nguồn phương pháp và dữ liệu", 15)
bullets(s, 0.55, 1.35, 12.1, 5.4, [
    ("PAPI 2011–2024.", "CECODES/VFF-CRT/RTA/UNDP — papi.org.vn."),
    ("Dữ liệu đối chiếu.", "Le và cộng sự, Mendeley Data, DOI 10.17632/wbk42j9wc8.1."),
    ("STING gốc.", "Wang, Yang & Muntz (1997), “STING: A Statistical Information Grid Approach to Spatial Data Mining”, VLDB."),
    ("Dự báo theo thời gian.", "Hyndman & Athanasopoulos (2021), Forecasting: Principles and Practice."),
    ("GeoJSON ranh giới.", "Open Development Vietnam (OD Mekong) — CC-BY-SA 4.0."),
    ("Nguồn bổ trợ.", "PCI VCCI–USAID, GSO PX-Web, Open Development Vietnam và World Bank WDI."),
], size=17, gap_pt=20)
note(s, "Phương pháp dựa trên bài STING của Wang, Yang và Muntz tại VLDB 1997. Dữ liệu chính "
     "là PAPI 2011–2024. Gói Le và cộng sự dùng để đối chiếu dữ liệu. Bản đồ và các phân tích "
     "bổ trợ có nguồn riêng được ghi trong báo cáo và hồ sơ nguồn dữ liệu kèm dự án.")

# Slide 16 — Q&A
s = slide_new()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, SH - 0.18, SW, 0.18, GOLD)
text(s, 0.55, 3.1, 12.23, 1.2, [
    ("Cảm ơn thầy và các bạn đã lắng nghe", 40, True, GOLD),
], align=PP_ALIGN.CENTER)
note(s, "Phần trình bày của nhóm đến đây là kết thúc. Nhóm xin cảm ơn thầy và các bạn đã lắng nghe. "
     "Nhóm mong nhận được câu hỏi, góp ý về phương pháp cũng như kết quả thực nghiệm.")

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(OUT))
print("saved:", OUT)
print("slides:", len(prs.slides._sldIdLst))
