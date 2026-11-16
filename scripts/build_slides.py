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

# Số liệu đọc từ artifact do script khác sinh (không hardcode số đo)


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
text(s, 0.85, 1.15, 7.6, 0.4, [("HỌC MÁY · BÁO CÁO CUỐI KỲ", 13, True, GOLD)])
text(s, 0.85, 1.75, 8.6, 2.6, [("Phân cụm dữ liệu PAPI", 40, True, WHITE),
                               ("bằng thuật toán STING", 30, True, WHITE)])
text(s, 0.85, 4.65, 8.4, 1.6, [
    ("Phân cụm dựa trên lưới · 63 tỉnh · 2011–2024", 17, True, GOLD),
    ("Nguyễn Tiến Sơn (24110054) · Trần Thị Ngọc Quyên (24110051)", 14, False, RGBColor(0xB9, 0xCD, 0xDE)),
    ("Nhóm 15 · Chủ đề 6 · Grid-based clustering", 13, False, RGBColor(0xB9, 0xCD, 0xDE)),
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
    ("Đối chiếu.", "Các giá trị giai đoạn 2011–2022 khớp gói dữ liệu Le và cộng sự."),
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

# Slide 7 — Pipeline dự đoán
s = slide_new()
header(s, "GÁN CỤM NGOÀI MẪU", "Dùng lưới 2011–2023 cho dữ liệu năm 2024", 7)
rect(s, 0.6, 1.85, 3.1, 0.72, TEAL)
text(s, 0.6, 1.91, 3.1, 0.4, [("DỮ LIỆU 2011–2023", 14, True, WHITE)], align=PP_ALIGN.CENTER)
rect(s, 4.5, 1.7, 3.3, 1.1, LIGHT)
text(s, 4.5, 1.82, 3.3, 0.9, [("LƯỚI STING ĐÃ HỌC", 14, True, NAVY),
                             ("Biên lưới và các ô dày", 13, False, GREY)], align=PP_ALIGN.CENTER)
rect(s, 8.6, 1.85, 3.1, 0.72, GOLD)
text(s, 8.6, 1.91, 3.1, 0.4, [("GÁN CỤM NĂM 2024", 14, True, NAVY)], align=PP_ALIGN.CENTER)
for x0 in (3.7, 7.8):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x0), Inches(2.01), Inches(0.8), Inches(0.4))
    a.fill.solid()
    a.fill.fore_color.rgb = TEAL
    a.line.fill.background()
bullets(s, 0.6, 3.9, 12.1, 3.0, [
    ("Chọn cấu hình.", "Dùng dữ liệu đến 2020 và đối chiếu trên các năm 2021–2022."),
    ("Học lưới.", "Fit cấu hình đã chọn trên các quan sát đủ dữ liệu giai đoạn 2011–2023."),
    ("Năm 2024.", "Dùng lại bộ chuẩn hóa và lưới đã học để gán điểm mới vào cụm hoặc nhãn nhiễu."),
], size=17, gap_pt=24)
note(s, "Cấu hình được chọn từ dữ liệu các năm trước, sau đó nhóm học lưới trên giai đoạn "
     "2011–2023. Năm 2024 dùng bộ chuẩn hóa và biên lưới này. Điểm mới nằm trong ô dày được "
     "gán nhãn cụm tương ứng. Các điểm còn lại nhận nhãn −1. Kết quả thể hiện việc gán "
     "dữ liệu mới vào các vùng đã học.")

# Slide 8 — Kết quả dự đoán
s = slide_new()
header(s, "KẾT QUẢ NĂM 2024", "48 tỉnh được gán cụm, 13 tỉnh nhận nhãn nhiễu", 8)
pic(s, "predict_2024.png", 0.55, 1.3, h=4.9)
bullets(s, 8.15, 1.75, 4.6, 5.0, [
    ("Đủ dữ liệu.", "61/63 tỉnh có hai chỉ tiêu được chọn."),
    ("Gán cụm.", "48 tỉnh vào cụm lớn, tương đương khoảng 79% trong 61 tỉnh."),
    ("Nhiễu.", "13 tỉnh nằm ngoài các ô dày của lưới đã học."),
    ("Độ nhạy.", "Ngưỡng 3, 5, 8 cho tỷ lệ gán cụm khoảng 82%, 79%, 70%."),
], size=17, gap_pt=25)
note(s, "Trong 61 tỉnh đủ dữ liệu năm 2024, có 48 tỉnh vào cụm lớn và 13 tỉnh nhận nhãn nhiễu. "
     "Hai tỉnh thiếu chỉ tiêu được để trống. Trên 59 tỉnh có đủ dữ liệu ở cả hai năm 2023 và "
     "2024, có 7 tỉnh từ cụm sang nhiễu và 5 tỉnh từ nhiễu vào cụm. Cả hai năm đều chỉ có "
     "điểm thuộc cụm lớn hoặc nhiễu, vì vậy cần thận trọng khi diễn giải mức ổn định của nhãn.")

# Slide 9 — Model giám sát
s = slide_new()
header(s, "PHÂN TÍCH BỔ TRỢ", "Dự báo chỉ tiêu y tế công lập bằng Ridge", 9)
pic(s, "supervised_regression.png", 0.55, 1.7, h=3.85)
bullets(s, 8.2, 1.75, 4.6, 5.0, [
    ("Đầu vào.", "8 chỉ tiêu năm hiện tại để dự báo chỉ tiêu y tế năm sau."),
    ("Chọn mô hình.", f"Kiểm định theo thời gian 2017–2022 chọn Ridge, với R² bằng {CV_RIDGE}."),
    ("Kết quả 2024.", "MAE bằng 0,0640, so với 0,0683 của cách giữ giá trị năm trước."),
    ("Phạm vi.", "Đánh giá trên 59 cặp tỉnh–năm của giai đoạn 2023→2024."),
], size=16, gap_pt=26)
note(s, f"Đây là phân tích bổ trợ về học có giám sát. Nhóm dự báo chỉ tiêu y tế năm sau "
     f"từ tám chỉ tiêu năm hiện tại. Kiểm định theo thời gian dùng sáu lần chia có năm huấn luyện "
     f"đứng trước năm kiểm định. Ridge có R² kiểm định {CV_RIDGE}, so với {CV_CARRY} của cách "
     "giữ giá trị năm trước. MAE trên 59 cặp của 2023→2024 giảm khoảng 6,3%. Random Forest "
     "có MAE trên năm này thấp hơn, nhưng điểm kiểm định theo thời gian thấp hơn Ridge. "
     "Kết quả hiện giới hạn ở một năm đánh giá.")

# Slide 10 — Baselines
s = slide_new()
header(s, "ĐỐI CHỨNG PHÂN CỤM", "STING, K-means và DBSCAN trên PAPI 2011–2023", 10)
rows = [
    ("Phương pháp", "Số cụm", "Nhiễu", "Silhouette", "ARI với STING"),
    ("STING", "3", "19.6%", "0.361*", "—"),
    ("k-means k=2", "2", "0%", "0.445", "0.166"),
    ("k-means k=3", "3", "0%", "0.336", "0.139"),
    ("DBSCAN eps=0.2", "5", "14.2%", "0.218*", "0.647"),
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
    ("* Silhouette được tính trên các điểm thuộc cụm. Cần đọc cùng tỷ lệ nhiễu.", 14, False, GREY),
    ("ARI với DBSCAN ở eps=0,2 bằng 0,647, cho biết mức đồng thuận giữa hai cách phân cụm.", 14, False, GREY),
])
note(s, "Bảng đối chiếu các cấu hình trên cùng hai chỉ tiêu PAPI của giai đoạn 2011–2023. "
     "STING cho ba cụm với 19,6% nhiễu. Silhouette chỉ tính trên điểm thuộc cụm, nên "
     "phạm vi điểm được chấm có thể khác giữa các phương pháp. ARI mô tả mức đồng thuận "
     "giữa hai cách phân cụm và cần được đọc trong cấu hình cụ thể.")

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

# Slide 12 — Hạn chế
s = slide_new()
header(s, "THẢO LUẬN", "Giới hạn của kết quả phân cụm", 12)
bullets(s, 0.55, 1.7, 12.2, 5.2, [
    ("Phạm vi đặc trưng.", "Kết quả chính mô tả hai chỉ tiêu PAPI được chọn."),
    ("Kích thước cụm.", "Giai đoạn 2011–2023 có một cụm 629 điểm và hai cụm 16, 5 điểm."),
    ("Tham số.", "Độ phân giải và ngưỡng mật độ làm thay đổi số cụm, tỷ lệ nhiễu."),
    ("Mở rộng số chiều.", "Các nhánh PCA và 8 chiều cho kết quả nhạy với cấu hình."),
    ("Đánh giá ngoài mẫu.", "Năm 2024 là mốc đánh giá hiện có. Cần thêm các năm để khảo sát độ ổn định."),
], size=18, gap_pt=25)
note(s, f"Kết quả cần được đọc trong phạm vi hai chỉ tiêu và các cấu hình đã thử. "
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
    ("THỰC NGHIỆM", "Đối chiếu trên dữ liệu giả lập, áp dụng lên PAPI và khảo sát ảnh hưởng của tham số."),
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
     "và đối chiếu thêm các bộ chỉ tiêu có thang đo tương thích. Tài liệu chi tiết kèm theo "
     "gồm final_report.docx, final_analysis.ipynb và bản trình chiếu final.pptx.")

# Slide 14 — Kiểm chứng bên ngoài
s = slide_new()
header(s, "PHÂN TÍCH BỔ TRỢ", "Đối chiếu các nhóm STING với dữ liệu PCI", 14)
pic(s, "external_pci_by_cluster.png", 0.55, 1.45, h=4.75)
bullets(s, 8.0, 1.5, 4.8, 4.8, [
    ("Nguồn đối chiếu.", "PCI khảo sát doanh nghiệp, do VCCI–USAID công bố."),
    ("Dữ liệu ghép.", "747 quan sát có nhãn STING trong giai đoạn 2011–2022."),
    ("Kiểm định.", "ANOVA cho F=9,04, p<0,001. Kruskal–Wallis cho H=31,78, p<0,001."),
    ("Giới hạn.", "Hai cụm nhỏ chỉ có 5 và 16 điểm, nên cần thận trọng khi diễn giải khác biệt."),
], size=16, gap_pt=28)
note(
    s,
    "PCI cung cấp nguồn đối chiếu về cảm nhận của doanh nghiệp. Nhóm ghép được 747 quan sát "
    "có nhãn STING, gồm 149 điểm nhiễu, 5 điểm cụm 0, 16 điểm cụm 1 và 577 điểm cụm 2. "
    "Hai kiểm định cho thấy có khác biệt thống kê giữa các nhóm trong mẫu ghép này. "
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
    ("GeoJSON ranh giới.", "Open Development Vietnam (OD Mekong) — CC-BY-SA 4.0."),
    ("Nguồn bổ trợ.", "PCI VCCI–USAID, GSO PX-Web, Open Development Vietnam và World Bank WDI."),
], size=17, gap_pt=29)
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
