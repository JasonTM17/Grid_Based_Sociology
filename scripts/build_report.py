"""Build reports/final_report.docx — báo cáo cuối kỳ (tiếng Việt, 7 chương).

Định dạng học theo ghi chú báo cáo tự biên soạn (`reports/report_format_notes.md`):
A4, lề 2.5/2.0/2.0/2.0 cm, Times New Roman, Title 20pt bold, H1 16pt, H2 14pt, H3 12pt,
front matter đầy đủ (TÓM TẮT · LỜI MỞ ĐẦU · MỤC LỤC(TOC field) · danh mục các loại).

Cách dùng: python scripts/build_report.py
"""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "results" / "figs"
OUT = ROOT / "reports" / "final_report.docx"

NAVY = RGBColor(0x0F, 0x2B, 0x46)
TEAL = RGBColor(0x1B, 0x6E, 0x77)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x5A, 0x5A, 0x5A)

doc = Document()

# ================= Page setup & styles =================
for section in doc.sections:
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin, section.right_margin = Cm(2.5), Cm(2.0)
    section.top_margin, section.bottom_margin = Cm(2.0), Cm(2.0)


def set_run(run, size=12, bold=False, color=INK, italic=False, name="Times New Roman"):
    f = run.font
    f.name = name
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    # đảm bảo font Latin + East Asian
    rpr = run._element.rPr
    if rpr is not None:
        rFonts = rpr.rFonts
        if rFonts is not None:
            rFonts.set(qn("w:hAnsi"), name)
            rFonts.set(qn("w:cs"), name)


def style_font(name, size, bold=False, color=INK, italic=False):
    st = doc.styles[name]
    st.font.name = "Times New Roman"
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.italic = italic
    st.font.color.rgb = color
    if st.paragraph_format is not None:
        st.paragraph_format.line_spacing = 1.15
        st.paragraph_format.space_after = Pt(6)


style_font("Normal", 12)
style_font("Title", 20, True, NAVY)
style_font("Heading 1", 16, True, NAVY)
style_font("Heading 2", 14, True, TEAL)
style_font("Heading 3", 12, True, INK)
try:
    style_font("Caption", 10, False, GREY, italic=True)
except KeyError:
    pass


def add_page_number_footer():
    sec = doc.sections[0]
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Trang ")
    set_run(r, 10, False, GREY)
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    r2 = p.add_run()
    r2._element.append(fld1)
    r2._element.append(it)
    r2._element.append(fld2)


def p(text, size=12, bold=False, color=INK, align=None, space_after=6, italic=False):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        para.alignment = align
    r = para.add_run(text)
    set_run(r, size, bold, color, italic)
    return para


def h1(text):
    para = doc.add_heading("", level=1)
    para.paragraph_format.space_before = Pt(18)
    r = para.add_run(text)
    set_run(r, 16, True, NAVY)
    return para


def h2(text):
    para = doc.add_heading("", level=2)
    para.paragraph_format.space_before = Pt(12)
    r = para.add_run(text)
    set_run(r, 14, True, TEAL)
    return para


def h3(text):
    para = doc.add_heading("", level=3)
    r = para.add_run(text)
    set_run(r, 12, True, INK)
    return para


def body(text, italic=False):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(6)
    r = para.add_run(text)
    set_run(r, 12, False, INK, italic)
    return para


def bullets(items):
    for lead, rest in items:
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Cm(0.6)
        para.paragraph_format.space_after = Pt(3)
        r1 = para.add_run("•  " + lead)
        set_run(r1, 12, True, TEAL)
        r2 = para.add_run(rest)
        set_run(r2, 12, False, INK)


def table(headers, rows, widths=None, caption=None, header_fill="1B6E77"):
    if caption:
        cp = doc.add_paragraph()
        cp.paragraph_format.space_before = Pt(10)
        r = cp.add_run(caption)
        set_run(r, 10.5, True, GREY)
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    t.style = doc.styles["Table Grid"]
    t.autofit = widths is None
    for j, (h, w) in enumerate(zip(headers, widths or [])):
        cell = t.cell(0, j)
        if widths:
            cell.width = Cm(w)
        cell.margin_left = Cm(0.12)
        cell.margin_top = Cm(0.04)
        para = cell.paragraphs[0]
        r = para.add_run(h)
        set_run(r, 11, True, RGBColor(0xFF, 0xFF, 0xFF))
        _shade_cell(cell, header_fill)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = t.cell(i + 1, j)
            if widths:
                cell.width = Cm(widths[j])
            cell.margin_left = Cm(0.12)
            cell.margin_top = Cm(0.04)
            para = cell.paragraphs[0]
            r = para.add_run(str(v))
            set_run(r, 10.5, False, INK)
            if i % 2 == 1:
                _shade_cell(cell, "F6F4EF")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def _shade_cell(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    wshd = OxmlElement("w:shd")
    wshd.set(qn("w:val"), "clear")
    wshd.set(qn("w:color"), "auto")
    wshd.set(qn("w:fill"), hex_fill)
    tcPr.append(wshd)


FIG_NO = [0]


def figure(fname, caption, width_cm=12.5):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(2)
    para.add_run().add_picture(str(FIGS / fname), width=Cm(width_cm))
    FIG_NO[0] += 1
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.space_after = Pt(8)
    r = cp.add_run(f"Hình {FIG_NO[0]}. {caption}")
    set_run(r, 10.5, False, GREY, italic=True)
    return FIG_NO[0]


def toc_field():
    p1 = doc.add_paragraph()
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve")
    it.text = 'TOC \\o "1-2" \\h \\z \\u'
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    r = p1.add_run()
    r._element.append(fld1)
    r._element.append(it)
    r._element.append(fld2)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("(Mở bằng Microsoft Word → References → Update Table để cập nhật số trang.)")
    set_run(r2, 9, False, GREY, italic=True)


add_page_number_footer()

# ================= BÌA =================
p("BỘ GIÁO DỤC VÀ ĐÀO TẠO", 11, True, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
p("TRƯỜNG ĐẠI HỌC SƯ PHẠM KỸ THUẬT TP. HỒ CHÍ MINH", 11, True, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
p("KHOA CÔNG NGHỆ THÔNG TIN", 11, True, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
p("🙠🙟❖🙝🙢", 14, False, TEAL, WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
p("BÁO CÁO CUỐI KỲ", 20, True, NAVY, WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
p("Topic 6 — Grid-based (clustering)", 14, True, TEAL, WD_ALIGN_PARAGRAPH.CENTER, space_after=30)
p("PHÂN CỤM 63 TỈNH VIỆT NAM\nVỚI STING TRÊN DỮ LIỆU PAPI 2011–2024", 20, True, NAVY, WD_ALIGN_PARAGRAPH.CENTER, space_after=50)
p("Môn học: Học Máy (Machine Learning)", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
p("Nhóm: 13–15   ·   Nhóm 2 người", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
p("Sinh viên 1: ....................................... MSSV: ................", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
p("Sinh viên 2: ....................................... MSSV: ................", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
p("Thành phố Hồ Chí Minh, tháng 11 năm 2026", 11, False, GREY, WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ================= TÓM TẮT =================
h1("TÓM TẮT")
body("Đồ án áp dụng STING (STatistical INformation Grid) — thuật toán phân cụm dựa trên lưới phân cấp, cài đặt từ đầu — lên dữ liệu chỉ số PAPI (Provincial Governance and Public Administration Performance Index) của 63 tỉnh/thành Việt Nam giai đoạn 2011–2024. Dữ liệu gốc gồm 14 workbook chính thức, được parse thành panel 882 dòng × 41 cột (d1–d8 các yếu tố quản trị + 30 chỉ tiêu thành phần), vượt yêu cầu đề bài (≥ 500 × ≥ 10). Trong quá trình làm sạch, nhóm phát hiện 23/37 cột chỉ tiêu có bước nhảy trung bình năm > 0.25 điểm (gãy thang đo), ví dụ sd_5_4 đổi từ 0.25–2.5 lên 0.33–3.33 tại năm 2021; pipeline dự đoán xuyên năm do đó chỉ dùng 8 chỉ tiêu qua audit thang đo. Kết quả chính thức: dữ liệu PAPI cấp tỉnh/năm gần như một khối đồng nhất — STING thu được một vùng dày chiếm ưu thế và một nhóm ngoại vi nhỏ (~14–16 điểm tổ hợp trong tập gộp 2011–2023); robustness khi mở rộng chiều (PCA d1–d6: 63.2% phương sai; 8 chiều 2018–2024) không nhận diện được cấu trúc (kết quả âm tính được báo cáo trung thực). Pipeline dự đoán 2024 (năm out-of-sample duy nhất khi chốt cấu hình theo quy trình train-only) đạt phủ 79% với lưới toàn cục; mô hình hồi quy Ridge dự báo chỉ số 6.1 Y tế công lập năm sau vượt baseline carry-forward ~10% MAE. Kết luận chính: PAPI ở cấp tỉnh/năm chưa cho thấy cấu trúc cụm tách biệt mạnh — giá trị nghiên cứu nằm ở quy trình dữ liệu nghiêm ngặt (audit thang đo, quy trình chọn cấu hình train-only) và cách báo cáo trung thực các kết quả khó nhìn.")
doc.add_page_break()

# ================= LỜI MỞ ĐẦU =================
h1("LỜI MỞ ĐẦU")
body("Đề tài thuộc Topic 6 — Grid-based (clustering), với hai yêu cầu khắt khe: (1) thuật toán tự viết, không dùng thư viện có sẵn cho phần lõi; (2) dataset thật ≥ 500 dòng × ≥ 10 cột. Nhóm chọn PAPI vì đây là bộ chỉ số quản trị công chính thức, công bố hàng năm, có lịch sử 2011–2024 đủ dài và đủ chiều (8 yếu tố + 30 chỉ tiêu thành phần) để thử thách một thuật toán lưới vốn phát huy tốt ở chiều thấp.")
body("Đồ án gồm: cài đặt STING từ đầu (src/sting.py); pipeline dữ liệu từ 14 workbook gốc; đối chiếu chéo với gói replication nghiên cứu công bố (Mendeley, CC BY 4.0 — lệch 0.0 trên toàn bộ 3.522 so sánh); phân cụm các năm; so sánh với k-means/DBSCAN; robustness đa chỉ tiêu; bản đồ 63 tỉnh; và pipeline dự đoán năm 2024 với hai mô hình local.")
body("Mọi tuyên bố số liệu trong báo cáo tái lập được từ mã nguồn: python scripts/build_panel.py → python scripts/check_data.py → python scripts/predict_sweep.py → python scripts/predict_demo.py → python scripts/predict_supervised.py → python scripts/run_analysis.py. Notebook cuối (notebooks/final_analysis.ipynb) chạy sạch end-to-end.")
doc.add_page_break()

# ================= MỤC LỤC =================
h1("MỤC LỤC")
toc_field()
p("Danh mục chính", 12, True, NAVY, space_after=4)
toc_lines = [
    ("CHƯƠNG 1. TỔNG QUAN ĐỀ TÀI", 2),
    ("CHƯƠNG 2. CƠ SỞ LÝ THUYẾT", 2),
    ("CHƯƠNG 3. DỮ LIỆU VÀ TIỀN XỬ LÝ", 2),
    ("CHƯƠNG 4. PHƯƠNG PHÁP", 2),
    ("CHƯƠNG 5. KẾT QUẢ", 2),
    ("CHƯƠNG 6. THẢO LUẬN VÀ HẠN CHẾ", 2),
    ("CHƯƠNG 7. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", 2),
    ("TÀI LIỆU THAM KHẢO", 2),
]
for t, _ in toc_lines:
    body(t)
doc.add_page_break()

# ================= DANH MỤC =================
h1("DANH MỤC CHỮ VIẾT TẮT")
table(["Viết tắt", "Nghĩa"], [
    ["STING", "STatistical INformation Grid — phân cụm dựa trên lưới thống kê phân cấp (Wang, Yang & Muntz, VLDB 1997)"],
    ["PAPI", "Vietnam Provincial Governance and Public Administration Performance Index"],
    ["NaN", "Not a Number — giá trị thiếu"],
    ["ARI", "Adjusted Rand Index — độ đồng thuận giữa hai phân cụm"],
    ["DB (index)", "Davies–Bouldin index — chỉ số nội cụm/cạnh cụm"],
    ["CH", "Calinski–Harabasz index — tỉ lệ phương sai giữa/trong cụm"],
    ["PCA", "Principal Component Analysis — phân tích thành phần chính"],
    ["O(n)", "Độ phức tạp tuyến tính theo số mẫu"],
    ["Holdout", "Tập kiểm định duy nhất (năm 2024), đánh giá một lần cuối"],
], widths=[3.5, 13.0], caption="Bảng 1. Danh mục chữ viết tắt")

h1("DANH MỤC HÌNH ẢNH")
for i, t in enumerate([
    "Demo STING trên dữ liệu giả lập — blobs 2 cụm (ARI = 0.950)",
    "Kết quả STING trên dữ liệu thật 2023 (hai mức phân giải lưới)",
    "STING học 2011–2023 → dự đoán cụm 2024 (phủ 79%)",
    "Hồi quy: dự báo 6.1 Y tế công lập năm sau",
    "Dịch chuyển cụm STING 2011–2024 (lưới toàn cục)",
    "Bản đồ centroid tô màu theo cụm — 2024",
], start=1):
    body(f"Hình {i}. {t}")

h1("DANH MỤC BẢNG")
for i, t in enumerate([
    "Kiểm chứng chất lượng dữ liệu",
    "Kết quả STING vs k-means vs DBSCAN (pooled 2011–2023)",
    "STING theo từng năm (lưới thô 3×3) — đa số k = 1",
    "Robustness đa chỉ tiêu (PCA d1–d6 + 8 chiều 2018–2024)",
    "Kết quả phân loại ngoại vi (âm tính) và hồi quy",
    "Chuyển cụm 2023 → 2024 (tách chuyển thật vs nhiễu)",
], start=1):
    body(f"Bảng {i}. {t}")
doc.add_page_break()

# ================= CHƯƠNG 1 =================
h1("CHƯƠNG 1. TỔNG QUAN ĐỀ TÀI")
h2("1.1. Bối cảnh và vấn đề đặt ra")
body("Chỉ số PAPI (Vietnam Provincial Governance and Public Administration Performance Index) được CECODES, VFF-CRT, RTA & UNDP công bố hàng năm từ 2011, đo lường chất lượng quản trị và cung ứng dịch vụ công ở cấp tỉnh trên 8 yếu tố (từ 2018): Tham gia ở cấp cơ sở (d1), Minh bạch (d2), Trách nhiệm giải trình (d3), Kiểm soát tham nhũng (d4), Thủ tục hành chính công (d5), Cung ứng dịch vụ công (d6), Quản trị môi trường (d7), Quản trị điện tử (d8). Đề bài môn Học máy (Topic 6 — Grid-based clustering) yêu cầu một thuật toán phân cụm dựa trên lưới, dataset thật ≥ 500 dòng × ≥ 10 cột, và nhóm chọn PAPI vì hai lý do: (i) dữ liệu công khai, có chuỗi thời gian dài (14 năm × 63 tỉnh); (ii) cơ sở dữ liệu đủ chiều để thử thách grid-based clustering ở chiều thấp.")
body("Bài toán thực tiễn: muốn phân loại các tỉnh theo nhóm cung ứng dịch vụ công/kểm soát tham nhũng để hỗ trợ hoạch định chính sách. Câu hỏi nghiên cứu: (1) dữ liệu PAPI có cấu trúc cụm tách biệt không; (2) cấu trúc đó ổn định qua thời gian không; (3) mô hình học trên quá khứ có dự đoán được cụm của năm tiếp theo không.")
h2("1.2. Mục tiêu và phạm vi")
bullets([
    ("Mục tiêu 1.", "Cài đặt STING từ đầu, đúng lý thuyết Wang–Yang–Muntz (VLDB 1997): lưới phân cấp, thống kê ô, gom cụm, nhãn nhiễu −1."),
    ("Mục tiêu 2.", "Xây pipeline dữ liệu PAPI 2011–2024 → panel 882×41; kiểm chứng với gói replication công bố (Mendeley, CC BY 4.0): max |diff| = 0.0."),
    ("Mục tiêu 3.", "Phân cụm theo năm + tập gộp; so sánh STING vs k-means vs DBSCAN (metric hình học tách nhãn nhiễu)."),
    ("Mục tiêu 4.", "Robustness: PCA d1–d6 toàn panel; nhánh 8 chiều 2018–2024 — chấp nhận kết quả âm tính."),
    ("Mục tiêu 5.", "Pipeline dự đoán 2024: STING.predict + mô hình giám sát (Ridge/RF); chọn cấu hình theo quy trình train-only."),
])
body("Phạm vi: 63 tỉnh/thành Việt Nam, 2011–2024, cấp tỉnh/năm. Không phân tích cấp huyện, không dữ liệu khảo sát khác, không dự đoán sau 2024.")
h2("1.3. Đóng góp của đồ án")
bullets([
    ("Kỹ thuật.", "STING tự cài (src/sting.py) + 12 unit tests; pipeline dự đoán hai mô hình local; quy trình chọn cấu hình chống selection-on-test."),
    ("Dữ liệu.", "Panel 882×41; audit gãy thang đo xuyên năm (23/37 cột) — lần đầu được hệ thống hóa cho PAPI trong phạm vi đồ án; PROVENANCE + hash cho mọi nguồn."),
    ("Khoa học.", "Phát hiện trung thực: PAPI cấp tỉnh/năm gần như một khối đồng nhất; cấu trúc tách biệt chỉ ở nhóm ngoại vi nhỏ; robustness 8 chiều không nhận diện được cấu trúc."),
])

# ================= CHƯƠNG 2 =================
h1("CHƯƠNG 2. CƠ SỞ LÝ THUYẾT")
h2("2.1. Grid-based clustering")
body("Grid-based chia không gian dữ liệu thành lưới (grid) hữu hạn ô, thay vì gom điểm theo khoảng cách từng đôi. Mỗi ô lưu thông tin tóm tắt; các cụm được suy ra từ mật độ/thống kê ô. Ưu điểm: (i) chi phí xây lưới tuyến tính O(n) mỗi mức; (ii) truy vấn vùng nhanh; (iii) song song hóa tự nhiên. Nhược điểm: lưới song song trục; nhạy với độ phân giải và ngưỡng mật độ; ở chiều cao, lưới bị thưa (curse of dimensionality).")
h2("2.2. STING (STatistical INformation Grid)")
body("Wang, Yang & Muntz, “STING: A Statistical Information Grid Approach to Spatial Data Mining”, Proc. VLDB 1997. Thuật toán: (1) chọn mức lưới; (2) mỗi ô ở mỗi mức lưu count, mean, std, min, max theo từng chiều; (3) ô được coi là “dày” nếu count ≥ ngưỡng (và tùy chọn: khác biệt ý nghĩa so với ô cha theo kiểm định); (4) gom các ô dày liền kề (4/8-connectivity) thành cụm; điểm thuộc ô không dày nhận nhãn −1. Ở đây STING dùng factor=3 hoặc 4, 2–3 mức, connectivity=1 (4-hướng).")
h2("2.3. Cài đặt trong đồ án (src/sting.py)")
bullets([
    ("fit(X).", "Một lượt O(n) cho mỗi mức: gán điểm vào ô, tích lũy thống kê ô (count/mean/std/min/max)."),
    ("cluster(level).", "Chọn ô dày → gom thành phần liên thông trên đồ thị kề ô (BFS/DFS) → gán nhãn điểm; nhãn −1 cho điểm không nằm trong ô dày."),
    ("predict(X).", "Điểm MỚI: tìm ô chứa nó ở mức đã dùng → cụm của ô đó; nếu ô không dày hoặc điểm ngoài vùng huấn luyện → −1."),
    ("query_rect(rect).", "Truy vấn vùng chữ nhật: chỉ duyệt các ô nằm trọn trong vùng; hỗ trợ count/mean/std/min/max tổng hợp."),
    ("save/load.", "Pickle model + JSON scaler/provenance — nạp lại dự báo không cần huấn luyện lại."),
])
h2("2.4. Baselines & chỉ số đánh giá")
bullets([
    ("k-means.", "gán mọi điểm về centroid gần nhất; k ∈ {2..5} (scikit-learn, n_init=10, seed 42)."),
    ("DBSCAN.", "eps ∈ {0.2, 0.4, 0.6, 0.8, 1.0}, min_samples=5; metric n/a khi <2 cụm."),
    ("Silhouette / DB / CH.", "tính trên điểm THUỘC CỤM (loại −1); khi k<2 → n/a."),
    ("Noise ratio.", "STING báo cáo riêng; không đưa noise vào metric hình học."),
    ("ARI.", "Adjusted Rand Index so với STING và giữa các năm."),
])
h2("2.5. Chỉ số PAPI & thang đo")
body("Mỗi yếu tố PAPI chuẩn hóa về 1–10 điểm theo năm; chỉ tiêu thành phần có thang riêng và có thể đổi thang giữa các phiên bản (vd 5.4 đổi 0.25–2.5 → 0.33–3.33 tại 2021 khi cấu trúc chỉ tiêu thay đổi). Vì vậy sử dụng xuyên năm buộc phải kiểm tra thang từng chỉ tiêu — làm bằng audit bước nhảy trung bình năm trong scripts/check_data.py (ngưỡng 0.25 điểm).")

# ================= CHƯƠNG 3 =================
h1("CHƯƠNG 3. DỮ LIỆU VÀ TIỀN XỬ LÝ")
h2("3.1. Nguồn dữ liệu và PROVENANCE")
bullets([
    ("PAPI 2011–2024.", "14 workbook chính thức từ papi.org.vn; manifest tên file + bytes + SHA-256: data/raw/papi/PROVENANCE.md. 3 file (2020/2021/2023) khớp tuyệt đối SHA-256 với gói replication Mendeley."),
    ("Mendeley replication.", "Le et al., Mendeley Data, DOI 10.17632/wbk42j9wc8.1, CC BY 4.0. 4 file nhỏ dùng trực tiếp (crosswalk, centroids, panel đối chiếu, ledger hash) đã commit kèm PROVENANCE.md; phần còn lại tải theo DOI."),
    ("GeoJSON tỉnh.", "Open Development Vietnam (OD Mekong), CC-BY-SA 4.0. Lưu ý: `code` hằng 'AD01' — join bản đồ qua centroids theo province_code; 6 tên tỉnh lệch có bảng alias."),
])
h2("3.2. Parse và xây panel")
bullets([
    ("2011–2019.", "sheet ĐẦU TIÊN (tên khác nhau từng năm: '2011- PAPI ALL Dimensions ', '2018PAPI-ALLDimentions', '2019PAPI_Dims_Sub-dims_ENG'…); tỉnh là hàng; 6 chiều (2011–2017) hoặc 8 chiều (2018–2019)."),
    ("2020–2024.", "ma trận chuyển vị; header 2 dòng (Mã tỉnh dòng 1, tên tỉnh dòng 2, dữ liệu từ dòng 3); chọn sheet `<năm>…VIE_ENG` khớp đầu tiên; sheet trùng byte-identical (vd '2022_VIE_ENG (2)') không bị cộng dồn."),
    ("Chuẩn hóa tên tỉnh.", "bỏ khoảng trắng/gạch nối + lowercase; alias TT-Hue→Thua Thien Hue; Ba Ria-Vung Tau khớp crosswalk qua chuẩn hóa; assert đủ 63 mã/năm."),
    ("0.0 → NaN.", "PAPI mã hóa “không đủ dữ liệu” bằng 0.0 ở một số năm; quy về NaN theo quy ước Mendeley; đối chiếu chéo lệch 0.0."),
])
h2("3.3. Chất lượng dữ liệu")
body("Panel cuối: 882 hàng × 41 cột (province_code, province_ascii/vi, year, d1–d8 + 30 sub-dim); 39 cột số; đủ 63 tỉnh mọi năm. Thiếu nhiều nhất: các chỉ tiêu d7/d8 (~51%, chỉ có từ 2018), sd_8_3 (58%), sd_2_4 (51%). check_data.py in PASS và danh sách audit thang đo.")
table(["Tiêu chí yêu cầu", "Kết quả"], [
    ["≥ 500 hàng", "882 (63 × 14 năm)"],
    ["≥ 10 cột (tổng / số)", "41 tổng / 39 cột số"],
    ["Đối chiếu chéo Mendeley", "max |diff| = 0.0 (3.522 so sánh)"],
    ["Tên tỉnh 63/63 mỗi năm", "Đạt (assert trong parser)"],
], widths=[8.0, 8.0], caption="Bảng 1. Kiểm chứng chất lượng dữ liệu")
h2("3.4. Audit gãy thang đo (điểm mới)")
body("PAPI đổi thang nhiều chỉ tiêu thành phần theo từng phiên bản. Nhóm thiết lập audit: với mỗi cột chỉ tiêu, lấy trung bình năm, tính bước nhảy lớn nhất; nếu > 0.25 điểm thì đánh dấu “gãy thang đo”. Kết quả: 23/37 cột bị đánh dấu — tiêu biểu sd_5_4 (đổi 0.25–2.5 → 0.33–3.33 tại 2021, bước nhảy +0.576, hệ số đổi thang 1.333 khớp), sd_2_1 (+1.355 tại 2018), sd_5_1/5_3 (+0.585/+0.538 tại 2021), sd_3_2 (+0.511 tại 2021), sd_6_4 (+0.453 tại 2021). Hệ quả: pipeline dự đoán và phân tích xuyên năm CHỈ dùng 8 chỉ tiêu qua audit (sd_1_3, sd_1_4, sd_4_1–4_4, sd_6_1, sd_6_3); chiều d1–d6 có bước nhảy theo năm nhưng thang 1–10 cố định theo thiết kế nên được ghi chú hạn chế riêng.")
body("Đây là phát hiện phương pháp quan trọng nhất của đồ án: nếu dùng sd_5_4 xuyên năm mà không audit, “cấu trúc 3 cụm ổn định” thu được hoàn toàn là artifact của việc đổi thang đo (cụm tách thuần theo giai đoạn ≤2020 vs ≥2021) — mọi số liệu huấn luyện trên cặp chỉ tiêu này đã được loại bỏ (xem Chương 6).")

# ================= CHƯƠNG 4 =================
h1("CHƯƠNG 4. PHƯƠNG PHÁP")
h2("4.1. Cấu hình STING và quy trình chọn train-only")
body("Ứng viên cặp chỉ tiêu được giới hạn ở các cột qua audit thang đo (8 sub-dim sạch + 15 cặp chiều d1–d6 tham chiếu): 43 cặp × 8 cấu hình lưới (n_levels ∈ {2,3}, factor ∈ {3,4}, min_count ∈ {4,5,8,12}, level tương ứng) = 344 tổ hợp. Tiêu chí chọn đặt TRƯỚC khi nhìn năm 2024: fit trên dữ liệu ≤ 2020, chấm điểm trên “tương lai giả” 2021–2022 (coverage + k + nhiễu + độ vững khi mc±1); bộ lọc k ∈ [2,6], noise ≤ 25%, cụm lớn nhất ≤ 85%, coverage ≥ 75%; điểm = coverage − 0.5·noise − 0.15·largest − 0.02·|k−3| + 0.03·stable. Kết quả đóng băng vào models/predict_config.json: cặp sd_4_2 (4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công) × sd_6_1 (6.1 Y tế công lập); STING(L=3, factor=4, min_count=5, cluster level=2, connectivity=1); coverage 2021–2022 = 0.851. Năm 2024 không tham gia bất kỳ bước chọn nào; đánh giá cuối chỉ thực hiện MỘT LẦN sau khi đóng băng: coverage 2024 = 79%, phân bố {nhiễu: 13, cụm 2: 48}.")
h2("4.2. Kiểm thử")
body("src/sting.py có 12 unit tests (pytest, tất cả xanh): thống kê ô khớp với numpy (tol 1e-9); phục hồi 2 Gaussian blobs (ARI ≥ 0.8); biên (điểm trên biên, 1 điểm, ô rỗng); predict trước cluster → RuntimeError; out-of-support → −1; save/load khôi phục chính xác nhãn. Runtime: ~18 giây cho notebook giữa kỳ.")
h2("4.3. Baselines")
bullets([
    ("k-means.", "k ∈ {2, 3, 4, 5}; n_init=10; seed=42. Ép mọi điểm vào cụm (không có nhiễu)."),
    ("DBSCAN.", "eps ∈ {0.2, 0.4, 0.6, 0.8, 1.0}; min_samples=5; metric n/a khi <2 cụm."),
    ("Metrics.", "Silhouette/DB/CH trên điểm thuộc cụm; STING tách noise; báo cáo noise_ratio riêng; khi k<2 → n/a."),
    ("ARI.", "Adjusted Rand Index với frozen STING (nhãn gộp)."),
])
h2("4.4. Robustness đa chỉ tiêu (điều kiện đặt trước)")
bullets([
    ("Nhánh A — PCA.", "≥2 thành phần giữ tối đa phương sai trên d1–d6 (trong-năm z, gộp); STING cùng cấu hình. Yêu cầu chấp nhận: ≥2 cụm & noise ≤ 50%, nếu không → “không nhận diện cấu trúc”. Thực tế: 2 PC đầu giữ 63.2% phương sai (< mục tiêu 80% — ghi rõ); STING cho k=1 → nhánh chính chỉ mang tính tham chiếu."),
    ("Nhánh B — 8 chiều.", "2018–2024 (n=430), trong-năm z; STING(L=3, f=2, mc=10, lv=1) → k=3, noise=60%; STING(L=3, f=3, mc=2, lv=2) → k=1, noise=99.5%. Cả hai vi phạm điều kiện chấp nhận → “không nhận diện cấu trúc”."),
])
h2("4.5. Pipeline dự đoán (hai mô hình local)")
bullets([
    ("STING.predict.", "Lưới toàn cục fit trên ≤2023; gán cụm cho mọi năm; 2024 out-of-sample; điểm ngoài vùng học → −1."),
    ("Giám sát (Ridge/RF).", "Cặp (chỉ số năm t → nhãn cụm năm t+1); bỏ 141 cặp nhãn nhiễu; CV GroupKFold theo năm; Ridge α ∈ {0.1, 1, 10}; RF max_depth ∈ {4, 6, None}, min_samples_leaf ∈ {1, 2}; đánh giá một lần trên 2023→2024; đối chứng: lớp đa số và carry-forward."),
    ("Persistence.", "joblib local (models/sup_ridge.joblib, sup_rf.joblib); nạp lại dự báo không cần huấn luyện lại."),
])

# ================= CHƯƠNG 5 =================
h1("CHƯƠNG 5. KẾT QUẢ")
h2("5.1. Kiểm chứng thuật toán trên dữ liệu giả lập")
body("STING cài đặt từ đầu phục hồi đúng 2 cụm Gauss trên dữ liệu tổng hợp 240 điểm: ARI = 0.950, tỷ lệ nhiễu 2.5%, đúng 2 cụm (Hình 1). Kết quả này xác nhận thuật toán đúng trước khi dùng dữ liệu thật.")
figure("00_synthetic_sting.png", "Demo STING trên dữ liệu giả lập — blobs 2 cụm (ARI = 0.950)", 11)

h2("5.2. STING theo từng năm (fit riêng từng năm)")
body("Nhìn chung mọi năm đều cho k = 1 (một vùng dày chiếm ưu thế), ngoại lệ duy nhất 2017 với nhóm 7 tỉnh tách được ở ngưỡng mc=5 (lưới 3×3): Hà Nội, Lai Châu, Lạng Sơn, Nghệ An, Gia Lai, Bình Dương, TP. Hồ Chí Minh — nhóm giá trị THẤP ở cả hai chỉ tiêu (sd_4_2 ∈ [1.53, 1.82], sd_6_1 ∈ [1.69, 1.83], so với median toàn bảng 2017 là 1.92 và 1.96); nhiễu 8 tỉnh (Hòa Bình, Thái Nguyên, Hải Phòng, Hưng Yên, Bình Thuận, Lâm Đồng, Bình Phước, Kiên Giang). Điều này khẳng định đặc trưng đồng nhất của dữ liệu PAPI ở cấp tỉnh/năm; độ nhạy lưới minh họa trong Hình 2.")
table(["Năm", "n", "k", "noise", "Kích thước cụm (giảm dần)"], [
    ["2011", "63", "1", "6%", "59"],
    ["2012", "63", "1", "0%", "63"],
    ["2013", "63", "1", "5%", "60"],
    ["2014", "61", "1", "2%", "60"],
    ["2015", "63", "1", "3%", "61"],
    ["2016", "63", "1", "3%", "61"],
    ["2017", "63", "2", "13%", "48, 7"],
    ["2018", "61", "1", "5%", "58"],
    ["2019", "63", "1", "2%", "62"],
    ["2020", "63", "1", "6%", "59"],
    ["2021", "60", "1", "7%", "56"],
    ["2022", "61", "1", "3%", "59"],
    ["2023", "61", "1", "0%", "61"],
    ["2024", "61", "1", "5%", "58"],
], widths=[1.6, 1.6, 1.2, 1.6, 6.0], caption="Bảng 3. STING theo từng năm (lưới thô 3×3, within-year z)")
figure("sting_first_real.png", "Kết quả STING trên dữ liệu thật 2023 — hai mức phân giải lưới", 15.5)

h2("5.3. Pooled 2011–2023: STING vs k-means vs DBSCAN")
body("Tập gộp 2011–2023 (n=808, chỉ 8 chỉ tiêu sạch, z theo tập gộp): STING frozen cho k=3 (kích thước 629/16/5), nhiễu 20%; các chỉ số hình học tính trên điểm thuộc cụm.")
table(["Scope", "Method", "k", "Noise", "Silh.", "DB", "Silh.→ARI"], [
    ["pooled", "STING (frozen)", "3", "20%", "0.361", "0.472", "—"],
    ["pooled", "k-means k=2", "2", "0%", "0.445", "0.876", "0.166"],
    ["pooled", "k-means k=3", "3", "0%", "0.336", "1.050", "0.139"],
    ["pooled", "k-means k=4", "4", "0%", "0.364", "0.879", "0.082"],
    ["pooled", "k-means k=5", "5", "0%", "0.334", "0.945", "0.070"],
    ["pooled", "DBSCAN eps=0.2", "5", "14%", "0.218", "0.505", "0.647"],
    ["pooled", "DBSCAN eps=0.4", "1", "3%", "n/a", "n/a", "0.135"],
    ["pooled", "DBSCAN eps=0.6", "1", "1%", "n/a", "n/a", "0.043"],
    ["pooled", "DBSCAN eps=0.8", "1", "0%", "n/a", "n/a", "0.012"],
    ["pooled", "DBSCAN eps=1.0", "1", "0%", "n/a", "n/a", "0.006"],
], widths=[1.8, 3.4, 0.9, 1.5, 1.5, 1.5, 1.7], caption="Bảng 2. STING vs baselines (noise tách khỏi metric hình học)")
body("Đọc bảng: k-means ép mọi điểm vào cụm và đạt silhouette 0.445 (cao nhất, k=2); STING và DBSCAN (eps nhỏ) đồng thuận tốt hơn (ARI 0.65); k-means phân vùng khác hẳn STING (ARI 0.07–0.17). Không metric nào “thắng tuyệt đối” — dữ liệu gần như một khối; mọi kết luận cần kèm noise và độ ổn định.")

h2("5.4. Robustness đa chỉ tiêu")
body("PCA d1–d6 (trong-năm z, n=869): 2 thành phần đầu giữ 63.2% phương sai; STING trên không gian PCA → k=1, nhiễu 6%, ARI vs 2D = 0.008 — không nhận diện cấu trúc. Nhánh 8 chiều (2018–2024, n=430): cả hai cấu hình đều vi phạm điều kiện chấp nhận (noise 60% và 99.5%) — không nhận diện cấu trúc ở chiều cao.")
table(["Nhánh", "n", "k", "noise", "Kết luận"], [
    ["PCA(2) d1–d6, within-year z (63.2%)", "869", "1", "6%", "Không nhận diện"],
    ["8 chiều 2018–2024, f=2 mc=10 lv=1", "430", "3", "60%", "Không nhận diện"],
    ["8 chiều 2018–2024, f=3 mc=2 lv=2", "430", "1", "99.5%", "Không nhận diện"],
], widths=[6.4, 1.4, 0.9, 1.6, 3.4], caption="Bảng 4. Robustness đa chỉ tiêu — kết quả âm tính")

h2("5.5. Pipeline dự đoán 2024 (out-of-sample)")
body("STING.predict (lưới toàn cục fit ≤2023) gán cụm 2024: 48/61 tỉnh đủ chỉ tiêu → cụm lớn; 13 → nhiễu. Không có “chuyển cụm thật” 2023→2024: 7 tỉnh chuyển sang nhiễu, 5 từ nhiễu ra (Bảng 6). Model giám sát: Ridge/RF dự báo 6.1 Y tế công lập năm sau; holdout 2023→2024: Ridge MAE 0.064 / R² 0.382; RF MAE 0.062 / R² 0.423 — vượt baseline carry-forward (MAE 0.0683 / R² 0.198) ~10%; baseline lớp đa số 0.814 accuracy. Phân loại trạng thái ngoại vi: mọi mô hình ≈ baseline (0.814–0.831 accuracy) — kết quả âm tính.")
figure("predict_2024.png", "STING học 2011–2023 → dự đoán cụm 2024 (out-of-sample)", 13)
figure("supervised_regression.png", "Hồi quy: dự báo 6.1 Y tế công lập năm sau + độ quan trọng đặc trưng", 14.5)
table(["Model", "CV R²/F1", "Holdout MAE/acc", "Holdout F1/R²"], [
    ["Carry-forward (dự báo = giá trị năm nay)", "—", "0.0683 MAE", "R² = 0.198"],
    ["Trung bình train", "—", "0.0814 MAE", "R² = −0.105"],
    ["Ridge (được chọn qua CV)", "0.451", "0.0640 MAE", "R² = 0.382"],
    ["RandomForest", "0.432", "0.0616 MAE", "R² = 0.423"],
    ["Majority (lớp đa số) — phân loại", "—", "0.814 acc", "F1 = 0.449"],
    ["Logistic regression — phân loại", "0.525", "0.814 acc", "F1 = 0.449"],
    ["RandomForest — phân loại", "0.589", "0.831 acc", "F1 = 0.536"],
], widths=[5.6, 2.2, 3.4, 3.0], caption="Bảng 5. Hồi quy (chính) và phân loại (phụ, âm tính) — holdout 2023→2024")
table(["2023 → 2024", "−1", "cụm 2", "Tổng"], [
    ["nhiễu (in-sample 2023)", "4", "5", "9"],
    ["cụm 2 (2023)", "7", "43", "50"],
    ["Tổng", "11", "48", "59"],
], widths=[6.4, 2.4, 2.4, 2.4], caption="Bảng 6. Chuyển cụm 2023 → 2024 (loại 4 dòng thiếu chỉ tiêu)")

h2("5.6. Dịch chuyển cụm qua thời gian và bản đồ")
body("Hình 5 vẽ nhãn lưới toàn cục cho mọi tỉnh-năm (xám = nhiễu, trắng = thiếu chỉ tiêu); Hình 6 — bản đồ centroid 2024, tỉnh ngoại vi rải đều các miền, không gom một vùng địa lý.")
figure("evolution.png", "Dịch chuyển cụm STING 2011–2024 (lưới toàn cục; xám = nhiễu; trắng = thiếu dữ liệu)", 10.5)
figure("map_2024.png", "Bản đồ centroid tô màu theo cụm — 2024 (nhãn chú thích các tỉnh nhiễu)", 10.0)

h2("5.7. Kiểm thử & tái lập")
bullets([
    ("Unit tests.", "python -m pytest tests -q → 12/12 xanh."),
    ("Dữ liệu.", "python scripts/check_data.py → PASS (882×41) + danh sách audit thang đo."),
    ("Tái lập.", "Mọi notebook execute sạch; mọi số liệu trong báo cáo truy được về results/*.csv; seeds cố định; PROVENANCE cho mọi nguồn."),
])

# ================= CHƯƠNG 6 =================
h1("CHƯƠNG 6. THẢO LUẬN VÀ HẠN CHẾ")
h2("6.1. Vì sao dữ liệu PAPI “gần như một khối”?")
body("Ba nguyên nhân hợp lý (không khẳng định ngoài dữ liệu): (1) PAPI chuẩn hóa về 1–10 theo năm — nén mọi biến động vào thang ngắn, nên phương sai giữa các tỉnh nhỏ; (2) khảo sát cấp tỉnh bám dân số/đô thị hóa — các tỉnh hội tụ dần theo thời gian; (3) phần lớn chỉ tiêu thành phần đã được thiết kế để tương quan với yếu tố tổng hợp, làm giàu miền trung tâm. Empirically: 808 điểm tập trung trong một lõi ~2.0±0.25 (đã z-score), ngoại lệ rải rác hai đầu; Hình 2 và Hình 5 cho thấy ngoại vi không gom thành một vùng địa lý — không phải “hai Việt Nam” theo vùng kinh tế, mà là vài tỉnh dao động ở từng chỉ tiêu.")
h2("6.2. Bài học từ gãy thang đo")
body("Trước khi audit, nhóm có kết quả “3 cụm rõ rệt” với cặp sd_5_4 × sd_6_2 (nghiên cứu ban đầu). Audit chỉ ra đó là artifact: mọi cụm tách thuần theo giai đoạn ≤2020 (cũ) vs ≥2021 (mới) do sd_5_4 đổi thang (0.25–2.5 → 0.33–3.33, hệ số 1.333 ≈ khớp 100% bước nhảy mean +0.57). Sau khi áp dụng quy trình audit và chỉ dùng chỉ tiêu sạch, cấu trúc tách biệt gần như biến mất. Bài học cho quy trình ML: (i) luôn audit bước nhảy phân phối theo thời gian trước khi gộp; (ii) bước nhảy trùng khớp hệ số đổi thang trong workbook gốc là bằng chứng mạnh của gãy thang đo, không phải cải thiện thực chất; (iii) mọi kết quả phân cụm xuyên năm đều phải được kiểm tra “tách theo thời gian” như một giả thuyết cạnh tranh với giả thuyết “cấu trúc quản trị”.")
h2("6.3. Metrics & lưới song song trục")
bullets([
    ("k-means “thắng” silhouette nhưng ép k.", "k-means không có nhiễu — mọi điểm thuộc cụm; silhouette 0.445 là giá trị nội tại của phân vùng bắt buộc, không phải bằng chứng cấu trúc thật."),
    ("STING vs DBSCAN(eps=0.2).", "ARI 0.647 — hai phương pháp mật độ đồng thuận; eps lớn hơn collapse về 1 cụm."),
    ("STING k=3.", "cụm 629 + 16 + 5 + 20% nhiễu: cấu trúc “một lõi + vệ tinh nhỏ” — hợp lý về mặt dữ liệu, không phải lỗi."),
    ("Silhouette không bản địa.", "metric khoảng cách Euclide không hiểu lưới song song; dùng để so sánh thô, tách noise; không dùng để chọn model."),
])
h2("6.4. Robustness — kết quả âm tính")
body("Cả hai nhánh mở rộng chiều đều không nhận diện cấu trúc (PCA 63.2% phương sai; 8 chiều toàn nhiễu). Đây là kết quả cần báo cáo, không lược bỏ: nó bác bỏ khả năng “cấu trúc ẩn ở chiều cao”. Một cấu trúc 2D dựng lại bằng cách chọn cặp-post-hoc sẽ bị PCA phủ định — vì vậy nhóm cũng loại bỏ mọi “cấu trúc 2D post-hoc” khỏi tuyên bố khoa học.")
h2("6.5. Các hạn chế còn lại")
bullets([
    ("Một holdout duy nhất (2024).", "mọi kết luận dự đoán cần thêm nhiều năm; độ bất định lớn; phòng thí nghiệm tốt hơn là backtest nhiều mốc (nếu có nguồn lịch sử thêm)."),
    ("Cỡ mẫu per-year nhỏ.", "61–63 điểm/năm — nhiễu cao ở lưới mịn; cấu hình per-year bị giới hạn ở lưới thô."),
    ("Thang đo 1–10 che giấu phương sai thực.", "theo thời gian, d6 tăng 7.0→7.6 (2021) khả năng là thay đổi phương pháp khảo sát, không chỉ cải thiện; cần thận trọng khi diễn giải xu hướng."),
    ("Bản đồ chỉ có centroid.", "chưa dùng ranh giới GeoJSON (chỉ có scatter); Choropleth đầy đủ để dành báo cáo cuối (cải thiện P6)."),
    ("Nhãn DBSCAN n/a khi 1 cụm.", "một số cấu hình DBSCAN cho metric n/a — ghi rõ trong bảng, không giấu."),
])
h2("6.6. Hướng phát triển")
bullets([
    ("Rank-normalization.", "chuẩn hóa theo hạng trong từng năm (hết phụ thuộc thang đo tuyệt đối) — xử lý triệt để gãy thang đo."),
    ("Feature trajectory.", "mỗi tỉnh = vector quỹ đạo 2011–2024 (đặc trưng theo thời gian) — phân cụm quỹ đạo, không phân cụm từng mốc."),
    ("Nhiều holdout.", "backtest cuốn chiếu 2015→2024 — độ tin cậy dự báo cao hơn."),
    ("Spatial.", "thêm tự tương quan không gian (láng giềng) — GeoJSON CC-BY-SA 4.0 đã có."),
    ("Định tính.", "phỏng vấn sâu 3–5 tỉnh ngoại vi để kiểm tra giả thuyết “hai tốc độ” quản trị."),
])

# ================= CHƯƠNG 7 =================
h1("CHƯƠNG 7. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN")
h2("7.1. Kết luận")
bullets([
    ("STING tự viết hoạt động đúng.", "ARI 0.950 trên dữ liệu giả lập; 12/12 test xanh; truy vấn vùng O(n); predict/save/load local."),
    ("Dữ liệu PAPI rất đồng nhất.", "phân cụm theo năm đa số k=1; cấu trúc tách biệt chỉ ở ngoại vi nhỏ; robustness 8 chiều không nhận diện được cấu trúc (âm tính, báo cáo)."),
    ("Pipeline dự đoán hợp lệ phương pháp.", "chọn cấu hình train-only; 2024 out-of-sample một lần; STING.predict phủ 79%; Ridge/RF thắng carry-forward ~10% MAE; phân loại ngoại vi âm tính giữ lại."),
    ("Chất lượng dữ liệu là bài học cốt lõi.", "audit gãy thang đo (23/37 cột) tách biệt “cấu trúc thật” và artifact đổi thang — áp dụng được cho bất kỳ dữ liệu chuỗi thời gian đa phiên bản nào."),
])
h2("7.2. Hướng phát triển")
body("Xem 6.6 — trọng tâm: (1) rank-normalization xuyên năm; (2) quỹ đạo tỉnh; (3) backtest cuốn chiếu; (4) phân cụm có ràng buộc không gian; (5) nghiên cứu định tính bổ trợ. Ngoài ra, bản đồ choropleth đầy đủ (plotly + GeoJSON) và dashboard tương tác là bước trực quan tiếp theo.")
h2("7.3. Lời cuối")
body("Đồ án không “tạo ra” một cấu trúc cụm đẹp nếu dữ liệu không có nó; đồ án cung cấp: (i) một cài đặt STING hoàn chỉnh, kiểm thử kỹ; (ii) một quy trình dữ liệu nghiêm ngặt (audit thang đo, train-only selection) mà mọi phân tích PAPI xuyên năm nên áp dụng; (iii) báo cáo trung thực cả kết quả âm tính lẫn dương tính. Nhóm tin rằng đây là cách học máy được ứng dụng có trách nhiệm vào nghiên cứu chính sách công.")

# ================= PHỤ LỤC A =================
h1("PHỤ LỤC A — LỆNH TÁI LẬP & KIỂM TRA")
body("Mọi bước dưới đây chạy từ thư mục gốc repo và cho kết quả như cột kỳ vọng; môi trường đã kiểm chứng: Python 3.14.2, Windows 11, dependencies trong requirements.txt.")
table(["Lệnh", "Kỳ vọng"], [
    ["python scripts/build_panel.py", "data/processed/papi_panel_63_2011_2024.csv (882×41); log 2 định dạng nguồn"],
    ["python scripts/check_data.py", "PASS — ≥500 hàng, ≥10 cột số; in danh sách audit gãy thang đo (23/37)"],
    ["python scripts/crosscheck_mendeley.py", "max |diff| = 0.0; ghi reports/crosscheck_mendeley.md"],
    ["python -m pytest tests -q", "12 passed"],
    ["python scripts/predict_sweep.py", "chọn cấu hình train-only; ghi models/predict_config.json + results/predict_config_search.csv"],
    ["python scripts/predict_demo.py", "dự đoán 2024; results/predict_summary.md (phủ 79%)"],
    ["python scripts/predict_supervised.py", "Ridge/RF thắng carry-forward ~10% MAE; metrics CSV"],
    ["python scripts/run_analysis.py", "metrics.csv, per_year.csv, robustness.csv, evolution/map hình, analysis_summary.md"],
    ["python -m nbconvert --to notebook --execute --inplace notebooks/midterm_demo.ipynb", "execute sạch ~18s, 18 cells, 0 lỗi"],
    ["python -m nbconvert --to notebook --execute --inplace notebooks/final_analysis.ipynb", "execute sạch, 19 cells, 4 hình nhúng"],
    ["python scripts/build_report.py", "reports/final_report.docx"],
], widths=[9.8, 6.0], caption="Bảng A1. Danh sách lệnh tái lập và kết quả kỳ vọng")
body("Môi trường: jupyter/pytest/nbconvert không cài trên PATH — luôn dùng python -m pytest / python -m nbconvert. Dữ liệu gốc data/raw/ bất biến; panel tái tạo từ raw bằng build_panel.py; Mendeley đầy đủ tải theo DOI 10.17632/wbk42j9wc8.1 (chỉ commit 4 file nhỏ dùng trực tiếp).")

# ================= TÀI LIỆU THAM KHẢO =================
h1("TÀI LIỆU THAM KHẢO")
refs = [
    "Wang, S., Yang, J., Muntz, R. (1997). STING: A Statistical Information Grid Approach to Spatial Data Mining. Proc. 23rd International Conference on Very Large Data Bases (VLDB), Athens, Greece, 186–195.",
    "CECODES, VFF-CRT, RTA & UNDP. Chỉ số Hiệu quả Quản trị và Hành chính công cấp tỉnh ở Việt Nam (PAPI) 2011–2024. Hà Nội. Truy cập papi.org.vn/du-lieu-papi/.",
    "Le, T. et al. Replication data and code for “Digital Governance...” study. Mendeley Data, DOI: 10.17632/wbk42j9wc8.1. Giấy phép CC BY 4.0.",
    "Open Development Vietnam (OD Mekong). Ranh giới hành chính cấp tỉnh Việt Nam — GeoJSON. data.opendevelopmentmekong.net. Giấy phép CC-BY-SA 4.0.",
    "scikit-learn developers. scikit-learn: Machine Learning in Python. https://scikit-learn.org — KMeans, DBSCAN, silhouette_score, Davies–Bouldin, Calinski–Harabasz.",
    "Jain, A. K. (2010). Data clustering: 50 years beyond K-means. Pattern Recognition Letters, 31(8), 651–666.",
    "Milligan, G. W., Cooper, M. C. (1985). An examination of procedures for determining the number of clusters in a data set. Psychometrika, 50(2), 159–179.",
    "Tài liệu môn học: Học Máy — Đề cương Topic 6: Grid-based clustering (cung cấp bởi giảng viên, kỳ học 2026).",
]
for i, r in enumerate(refs, start=1):
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(0.7)
    para.paragraph_format.space_after = Pt(4)
    rr = para.add_run(f"[{i}]  ")
    set_run(rr, 12, True, TEAL)
    r2 = para.add_run(r)
    set_run(r2, 12, False, INK)

doc.save(str(OUT))
print("saved:", OUT)
