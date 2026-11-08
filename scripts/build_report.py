"""Build reports/final_report.docx — báo cáo cuối kỳ (tiếng Việt, 7 chương).

Định dạng học theo ghi chú báo cáo tự biên soạn (`reports/report_format_notes.md`):
A4, lề 2.5/2.0/2.0/2.0 cm, Times New Roman, Title 20pt bold, H1 16pt, H2 14pt, H3 12pt,
front matter đầy đủ (TÓM TẮT · LỜI MỞ ĐẦU · MỤC LỤC(TOC field) · danh mục các loại).

Cách dùng: python scripts/build_report.py
"""
import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "results" / "figs"
OUT = ROOT / "reports" / "final_report.docx"

# ==== Số liệu đọc từ artifact do script khác sinh (không hardcode số đo) ====


def _read_results_csv(name):
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


SUP_ROWS = _read_results_csv("supervised_metrics.csv")
ROBUSTNESS = _read_results_csv("robustness.csv")


def _vn(v):
    """Hiển thị số âm với dấu trừ kiểu typography (U+2212) khớp phần còn lại của báo cáo."""
    return str(v).replace("-", "−")


def _pct(v):
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


def _f3(v):
    v = (v or "").strip()
    return "n/a" if v == "" else _vn(f"{float(v):.3f}")


def _reg_cv(model_sub):
    for r in SUP_ROWS:
        if r["task"] == "regression" and model_sub in r["model"]:
            return r["value_cv"].strip()
    raise KeyError(model_sub)


def _rob(branch_sub):
    for r in ROBUSTNESS:
        if branch_sub in r["branch"]:
            return r
    raise KeyError(branch_sub)


CV_CARRY = _reg_cv("carry-forward")
CV_MEAN = _reg_cv("trung bình train")
CV_RIDGE = _reg_cv("ridge")
R_PCA = _rob("PCA(2)")
R_GOC = _rob("(gốc OFAT)")
R_F3 = _rob("OFAT f=3")
R_MC2 = _rob("OFAT mc=2")
R_LV2 = _rob("OFAT lv=2")
N8 = R_GOC["n"]

POV_ROWS = _read_results_csv("poverty_validation.csv")


def _pov_note(section, group):
    """Note kiểm định do scripts/poverty_validation.py tự tính (không hardcode)."""
    for r in POV_ROWS:
        if r["section"] == section and r["group"] == group:
            return r["note"]
    raise KeyError(f"poverty_validation.csv thiếu {section}/{group}")


def _note_val(note, key):
    """'H = 3.4415; p = 0.328' + 'H = ' → '3.4415' — đọc đúng chuỗi script ghi."""
    for part in note.split(";"):
        part = part.strip()
        if part.startswith(key):
            return part[len(key):].strip()
    raise KeyError(f"{key!r} không có trong note {note!r}")


def _note_eta(note):
    """'eta² = 0.0058 (SS giữa / SS tổng)' → '0.0058'."""
    return _note_val(note, "eta² = ").split(" (")[0]


POV_GROUPS = [r for r in POV_ROWS if r["section"] == "poverty_pooled_raw"
              and str(r["mean"]).strip() != ""]
POV_GROUPS_DM = [r for r in POV_ROWS if r["section"] == "poverty_pooled_demeaned"
                 and str(r["mean"]).strip() != ""]
assert len(POV_GROUPS) == len(POV_GROUPS_DM) == 4, "thiếu dòng nhóm poverty"
POV_KW_RAW = _pov_note("poverty_pooled_raw", "Kruskal–Wallis")
POV_KW_DM = _pov_note("poverty_pooled_demeaned", "Kruskal–Wallis")
POV_ANOVA_RAW = next(r for r in POV_ROWS
                     if r["section"] == "poverty_pooled_raw"
                     and r["group"].startswith("ANOVA"))
POV_ANOVA_DM = next(r for r in POV_ROWS
                    if r["section"] == "poverty_pooled_demeaned"
                    and r["group"].startswith("ANOVA"))
POV_MW_RAW = next(r for r in POV_ROWS if r["section"] == "test_mw_noise_vs_c2"
                  and "(thô)" in r["group"])
POV_MW_DM = next(r for r in POV_ROWS if r["section"] == "test_mw_noise_vs_c2"
                 and "trừ" in r["group"])


def _pov_group_n(sub):
    return int(next(r["n"] for r in POV_GROUPS if sub in r["group"]))


# Cửa sổ thiết kế — giao thức kiểm định (poverty_validation.py DESIGN_WINDOW tự
# assert khớp cửa sổ giao tự tính từ dữ liệu). Số ĐẾM dưới đây tính trực tiếp
# từ 2 CSV provenance, rồi đối chiếu với poverty_validation.csv — không
# hardcode số đếm. 2017–2019 nằm trong chuỗi nghèo từ 2026-11-08 (điền từ NGTK
# 2020/2021 — scripts/build_poverty_gap.py).
POV_WINDOW = {2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
              2020, 2021, 2022, 2023, 2024}

with open(ROOT / "data" / "processed" / "external_poverty_63.csv",
          encoding="utf-8-sig", newline="") as _f:
    _pov_src = list(csv.DictReader(_f))
with open(ROOT / "results" / "predict_all_years.csv",
          encoding="utf-8-sig", newline="") as _f:
    _pov_lab_keys = {(int(r["year"]), int(r["province_code"]))
                     for r in csv.DictReader(_f)}
_pov_win = [r for r in _pov_src if int(r["year"]) in POV_WINDOW]
POV = {
    "n_win": len(_pov_win),
    "n_val": sum(1 for r in _pov_win if str(r["poverty_rate_pct"]).strip() != ""),
    "missing_txt": "; ".join(f"{r['province_vi']} {r['year']}" for r in _pov_win
                             if str(r["poverty_rate_pct"]).strip() == ""),
}
POV["n_join"] = sum(1 for r in _pov_win
                    if str(r["poverty_rate_pct"]).strip() != ""
                    and (int(r["year"]), int(r["province_code"])) in _pov_lab_keys)
POV["n_no_label"] = POV["n_val"] - POV["n_join"]
assert POV["n_join"] == sum(int(r["n"]) for r in POV_GROUPS) == \
    int(POV_ANOVA_RAW["n"]), "số ô join không khớp poverty_validation.csv"

# Notebook cuối kỳ — đếm cell/hình nhúng trực tiếp từ file đã execute (bảng A1).
_nb = json.loads((ROOT / "notebooks" / "final_analysis.ipynb").read_text(
    encoding="utf-8"))
NB_CELLS = len(_nb["cells"])
NB_IMGS = sum(1 for c in _nb["cells"] for out in c.get("outputs", [])
              if isinstance(out.get("data"), dict) and "image/png" in out["data"])

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
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = "PAGE"
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
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
        r1 = para.add_run("•  " + lead + " ")
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
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = 'TOC \\o "1-2" \\h \\z \\u'
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
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
p("—  ◆  —", 14, False, TEAL, WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
p("BÁO CÁO CUỐI KỲ", 20, True, NAVY, WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
p("Topic 6 — Grid-based (clustering)", 14, True, TEAL, WD_ALIGN_PARAGRAPH.CENTER, space_after=30)
p("PHÂN CỤM 63 TỈNH VIỆT NAM\nVỚI STING TRÊN DỮ LIỆU PAPI 2011–2024", 20, True, NAVY, WD_ALIGN_PARAGRAPH.CENTER, space_after=50)
p("Môn học: Học Máy (Machine Learning)", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
p("Nhóm: 15", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
p("Sinh viên 1: Nguyễn Tiến Sơn — MSSV: 24110054", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
p("Sinh viên 2: Trần Thị Ngọc Quyên — MSSV: 24110051", 12, False, INK, WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
p("Thành phố Hồ Chí Minh, tháng 11 năm 2026", 11, False, GREY, WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ================= TÓM TẮT =================
h1("TÓM TẮT")
body(f"Đồ án áp dụng STING (STatistical INformation Grid) — thuật toán phân cụm dựa trên lưới phân cấp, cài đặt từ đầu — lên dữ liệu chỉ số PAPI (Provincial Governance and Public Administration Performance Index) [2] của 63 tỉnh/thành Việt Nam giai đoạn 2011–2024. Dữ liệu gốc gồm 14 workbook chính thức, được parse thành panel 882 dòng × 41 cột (d1–d8 các yếu tố quản trị + 29 chỉ tiêu thành phần), vượt yêu cầu đề bài (≥ 500 × ≥ 10) [8]. Trong quá trình làm sạch, nhóm phát hiện 23/37 cột chỉ tiêu có bước nhảy trung bình năm > 0.25 điểm (gãy thang đo), ví dụ sd_5_4 đổi từ 0.25–2.5 lên 0.33–3.33 tại năm 2021; pipeline dự đoán xuyên năm do đó chỉ dùng 8 chỉ tiêu qua audit thang đo. Kết quả chính thức: dữ liệu PAPI cấp tỉnh/năm gần như một khối đồng nhất — STING thu được một vùng dày chiếm ưu thế và hai cụm nhỏ 16 và 5 điểm (tổng 21) trong tập gộp 2011–2023; robustness khi mở rộng chiều: PCA d1–d6 ({_pct(R_PCA['explained_var_total'])} phương sai) → k={R_PCA['k']} — không nhận diện; nhánh 8 chiều 2018–2024 đọc theo ablation OFAT — gốc k={R_GOC['k']} nhiễu {_pct(R_GOC['noise_ratio'])}, f=3 → k={R_F3['k']}/{_pct(R_F3['noise_ratio'])}, lv=2 → k={R_LV2['k']} toàn nhiễu, riêng mc=2 đạt ngưỡng k/noise (k={R_MC2['k']}, nhiễu {_pct(R_MC2['noise_ratio'])}) nhưng silhouette âm — tách yếu (Bảng 4; kết quả được báo cáo trung thực). Pipeline dự đoán 2024 (năm out-of-sample duy nhất khi chốt cấu hình theo quy trình train-only) đạt phủ 79% với lưới toàn cục; mô hình hồi quy Ridge (được chọn qua CV — hai baseline hồi quy cũng có CV thật trên cùng fold: carry {_vn(CV_CARRY)} vs ridge {_vn(CV_RIDGE)}) dự báo chỉ số 6.1 Y tế công lập năm sau có MAE holdout 0.0640, thấp hơn carry-forward 0.0683 là 6.3%. Kết luận chính: PAPI ở cấp tỉnh/năm chưa cho thấy cấu trúc cụm tách biệt mạnh — giá trị nghiên cứu nằm ở quy trình dữ liệu nghiêm ngặt (audit thang đo, quy trình chọn cấu hình train-only) và cách báo cáo trung thực các kết quả khó nhìn.")
doc.add_page_break()

# ================= LỜI MỞ ĐẦU =================
h1("LỜI MỞ ĐẦU")
body("Đề tài thuộc Topic 6 — Grid-based (clustering), với hai yêu cầu khắt khe: (1) thuật toán tự viết, không dùng thư viện có sẵn cho phần lõi; (2) dataset thật ≥ 500 dòng × ≥ 10 cột. Nhóm chọn PAPI vì đây là bộ chỉ số quản trị công chính thức, công bố hàng năm, có lịch sử 2011–2024 đủ dài và đủ chiều (8 yếu tố + 29 chỉ tiêu thành phần) để thử thách một thuật toán lưới vốn phát huy tốt ở chiều thấp.")
body("Đồ án gồm: cài đặt STING từ đầu (src/sting.py); pipeline dữ liệu từ 14 workbook gốc; đối chiếu chéo với gói replication nghiên cứu công bố (Mendeley, CC BY 4.0 — lệch 0.0 trên toàn bộ 3.522 so sánh) [3]; phân cụm các năm; so sánh với k-means/DBSCAN; robustness đa chỉ tiêu; bản đồ 63 tỉnh; và pipeline dự đoán năm 2024 với hai mô hình local.")
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
    ["STING", "STatistical INformation Grid — phân cụm dựa trên lưới thống kê phân cấp (Wang, Yang & Muntz, VLDB 1997) [1]"],
    ["PAPI", "Vietnam Provincial Governance and Public Administration Performance Index"],
    ["NaN", "Not a Number — giá trị thiếu"],
    ["ARI", "Adjusted Rand Index — độ đồng thuận giữa hai phân cụm"],
    ["DB (index)", "Davies–Bouldin index — chỉ số nội cụm/cạnh cụm"],
    ["CH", "Calinski–Harabasz index — tỉ lệ phương sai giữa/trong cụm"],
    ["PCA", "Principal Component Analysis — phân tích thành phần chính"],
    ["O(n)", "Độ phức tạp tuyến tính theo số mẫu"],
    ["Holdout", "Tập kiểm định duy nhất (năm 2024), đánh giá một lần cuối"],
], widths=[3.5, 13.0])

h1("DANH MỤC HÌNH ẢNH")
for i, t in enumerate([
    "Demo STING trên dữ liệu giả lập — blobs 2 cụm (ARI = 0.950)",
    "Kết quả STING trên dữ liệu thật 2023 (hai mức phân giải lưới)",
    "STING học 2011–2023 → dự đoán cụm 2024 (phủ 79%)",
    "Hồi quy: dự báo 6.1 Y tế công lập năm sau",
    "Dịch chuyển cụm STING 2011–2024 (lưới toàn cục)",
    "Bản đồ centroid tô màu theo cụm — 2024",
    "PCI theo nhãn cụm STING 2011–2022 — kiểm chứng ngoại lai (ANOVA/Kruskal–Wallis)",
    "Mật độ cơ sở y tế/1.000 dân theo cụm STING — 2020 (ODM + GSO dân số)",
    "GRDP/người theo cụm STING — cửa sổ 2018–2024 (GSO pxweb; 2024 = Sơ bộ)",
    "Bối cảnh vĩ mô quốc gia 2010–2024 (World Bank WDI — chuỗi không đều phía nguồn)",
    "Tỷ lệ hộ nghèo GSO theo cụm STING — cửa sổ giao 2012–2024 (GSO pxweb V14.47 + NGTK 2020/2021)",
], start=1):
    body(f"Hình {i}. {t}")

h1("DANH MỤC BẢNG")
for i, t in enumerate([
    "Kiểm chứng chất lượng dữ liệu",
    "STING theo từng năm (lưới thô 3×3) — đa số k = 1",
    "Kết quả STING vs k-means vs DBSCAN (pooled 2011–2023)",
    "Robustness đa chỉ tiêu (PCA d1–d6 + OFAT 8 chiều 2018–2024)",
    "Hồi quy và phân loại pseudo-label STING — holdout 2023→2024",
    "Chuyển cụm 2023 → 2024 (tách chuyển thật vs nhiễu)",
    "Kiểm chứng ngoại lai — PCI theo nhãn cụm STING (2011–2022)",
    "Nghèo GSO theo nhãn cụm STING — cửa sổ giao 2012–2024 (thô và đã-trừ-median-năm)",
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
    ("Mục tiêu 4.", "Robustness: PCA d1–d6 toàn panel; nhánh 8 chiều 2018–2024 — ablation OFAT, đổi đúng một tham số mỗi lần so với cấu hình gốc."),
    ("Mục tiêu 5.", "Pipeline dự đoán 2024: STING.predict + mô hình giám sát (Ridge/RF); chọn cấu hình theo quy trình train-only."),
])
body("Phạm vi: 63 tỉnh/thành Việt Nam, 2011–2024, cấp tỉnh/năm. Không phân tích cấp huyện, không dự đoán sau 2024; các nguồn khảo sát ngoài (PCI, GSO, OD Mekong, WDI — mục 3.1) chỉ dùng để kiểm chứng ngoại lai, không đưa vào huấn luyện (mục 6.5).")
h2("1.3. Đóng góp của đồ án")
bullets([
    ("Kỹ thuật.", "STING tự cài (src/sting.py) + 28 unit tests (tests/test_sting.py; 55 test toàn suite); pipeline dự đoán hai mô hình local; quy trình chọn cấu hình chống selection-on-test."),
    ("Dữ liệu.", "Panel 882×41; audit gãy thang đo xuyên năm (23/37 cột) — lần đầu được hệ thống hóa cho PAPI trong phạm vi đồ án; PROVENANCE + hash cho mọi nguồn."),
    ("Khoa học.", f"Phát hiện trung thực: PAPI cấp tỉnh/năm gần như một khối đồng nhất; cấu trúc tách biệt chỉ ở nhóm ngoại vi nhỏ; robustness 8 chiều đọc theo ablation OFAT — lv=2 sập toàn nhiễu, f=3 cho {_pct(R_F3['noise_ratio'])} nhiễu, riêng mc=2 đạt ngưỡng k/noise nhưng silhouette âm — không có cấu trúc tách mạnh."),
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
    ("k-means.", "gán mọi điểm về centroid gần nhất; k ∈ {2..5} (scikit-learn [5], n_init=10, seed 42)."),
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
    ("GeoJSON tỉnh.", "Open Development Vietnam (OD Mekong), CC-BY-SA 4.0 [4]. Lưu ý: `code` hằng 'AD01' — join bản đồ qua centroids theo province_code; 6 tên tỉnh lệch có bảng alias."),
    ("PCI 2011–2024.", "Chỉ số Năng lực cạnh tranh cấp tỉnh — VCCI – USAID: workbook + trang xếp hạng từ pcivietnam.vn (dữ liệu công khai, ghi nguồn VCCI–USAID) [9]. Đủ 63 tỉnh × 12 năm 2011–2022 = 756 ô; 2023–2024 chỉ công bố Top-30 (chỉ dùng kiểm tra phụ, cảnh báo chọn mẫu). raw: data/raw/pci/PROVENANCE.md; chuẩn hóa: data/processed/external_provenance.md."),
    ("GSO/NSO — dân số & GRDP.", "PX-Web chính thức pxweb.nso.gov.vn (“Bản quyền: Không”) + Niên giám Thống kê [10]: dân số theo tỉnh đủ 882 tỉnh-năm (2 vintage — 378 dòng pxweb + 504 dòng Niên giám — giữ nguyên từng vintage, không trộn bình quân); GRDP/người 441 ô 2018–2024 (2024 = Sơ bộ). raw: data/raw/gso/PROVENANCE.md."),
    ("OD Mekong — Health Facilities 2020.", "2.169 điểm cơ sở y tế các nước Mekong (ODbL) [11]; 423 điểm rơi vào Việt Nam qua point-in-polygon với GeoJSON 63 tỉnh; 10 tỉnh count=0 là 0-thật (nguồn điểm không phủ tỉnh đó), không phải dữ liệu thiếu."),
    ("World Bank WDI.", "4 chỉ số vĩ mô quốc gia VNM 2010–2024, CC BY 4.0 [12] — dùng làm bối cảnh, không phải feature cấp tỉnh."),
    ("Bảng master nối nguồn.", "scripts/build_external_master.py nối panel PAPI + các nguồn trên theo khóa (papi_province_code, year) — validate one-to-one giữ đúng 882 dòng, cột mask thiếu tường minh từng nguồn (PCI 816/882; dân số 882/882; GRDP 441/882; y tế 63/882; rác thải 305/882, trống hoàn toàn 2018), không nội suy: data/processed/external_master_63_2011_2024.csv (882×59)."),
])
body('Báo cáo tường thuật PAPI 2024 nêu khảo sát 18.894 người dân ở 61 tỉnh, thành phố (trang 10), trong khi panel của repo này là workbook 63 tỉnh theo câu “toàn bộ 63 tỉnh/thành phố từ năm 2011” (trang 15; data/raw/papi/PROVENANCE.md).')
h2("3.2. Parse và xây panel")
bullets([
    ("2011–2019.", "sheet ĐẦU TIÊN (tên khác nhau từng năm: '2011- PAPI ALL Dimensions ', '2018PAPI-ALLDimentions', '2019PAPI_Dims_Sub-dims_ENG'…); tỉnh là hàng; 6 chiều (2011–2017) hoặc 8 chiều (2018–2019)."),
    ("2020–2024.", "ma trận chuyển vị; header 2 dòng (Mã tỉnh dòng 1, tên tỉnh dòng 2, dữ liệu từ dòng 3); chọn sheet `<năm>…VIE_ENG` khớp đầu tiên; sheet trùng byte-identical (vd '2022_VIE_ENG (2)') không bị cộng dồn."),
    ("Chuẩn hóa tên tỉnh.", "bỏ khoảng trắng/gạch nối + lowercase; alias TT-Hue→Thua Thien Hue; Ba Ria-Vung Tau khớp crosswalk qua chuẩn hóa; assert đủ 63 mã/năm."),
    ("0.0 → NaN.", "PAPI mã hóa “không đủ dữ liệu” bằng 0.0 ở một số năm; quy về NaN theo quy ước Mendeley; đối chiếu chéo lệch 0.0."),
])
h2("3.3. Chất lượng dữ liệu")
body("Panel cuối: 882 hàng × 41 cột (province_code, province_ascii/vi, year, d1–d8 + 29 sub-dim); 39 cột số; 882 hàng = 63 tỉnh × 14 năm (đủ 63 tỉnh ở cấp hàng). Theo điểm có đủ hai chỉ tiêu pipeline (sd_4_2 × sd_6_1), 6 năm thiếu 1–3 tỉnh: 2014/2018: 61, 2021: 60, 2022/2023/2024: 61 (2021 nằm trong cửa sổ validation của sweep). Thiếu nhiều nhất: các chỉ tiêu d7/d8 (~51%, chỉ có từ 2018), sd_8_3 (58%), sd_2_4 (51%). check_data.py in PASS — PASS chỉ xác nhận shape ≥ 500 hàng × ≥ 10 cột theo yêu cầu môn, kèm danh sách audit thang đo.")
table(["Tiêu chí yêu cầu", "Kết quả"], [
    ["≥ 500 hàng", "882 (63 × 14 năm)"],
    ["≥ 10 cột (tổng / số)", "41 tổng / 39 cột số"],
    ["Đối chiếu chéo Mendeley", "max |diff| = 0.0 (3.522 so sánh)"],
    ["Tên tỉnh 63/63 mỗi năm", "Đạt (assert trong parser)"],
], widths=[8.0, 8.0], caption="Bảng 1. Kiểm chứng chất lượng dữ liệu")
h2("3.4. Audit gãy thang đo (điểm mới)")
body("PAPI đổi thang nhiều chỉ tiêu thành phần theo từng phiên bản. Nhóm thiết lập audit: với mỗi cột chỉ tiêu, lấy trung bình năm, tính bước nhảy lớn nhất; nếu > 0.25 điểm thì đánh dấu “gãy thang đo” — đây là heuristic sàng lọc, không tự chứng minh gãy thang. Kết quả: 23/37 cột bị đánh dấu. Các ví dụ có bằng chứng workbook gốc: sd_5_4 (đổi 0.25–2.5 → 0.33–3.33 tại 2021, bước nhảy +0.576, hệ số đổi thang 1.333 khớp), sd_2_1 (+1.355 tại 2018), sd_5_1/5_3 (+0.585/+0.538 tại 2021). Các flag còn lại — trong đó sd_3_2 (+0.511 tại 2021) và sd_6_4 (+0.453 tại 2021) — là heuristic, chưa đối chiếu thang: workbook gốc cho thấy hai cột này giữ nguyên thang 1–10, bước nhảy là biến động dữ liệu thực. Hệ quả: pipeline dự đoán và phân tích xuyên năm CHỈ dùng 8 chỉ tiêu qua audit (sd_1_3, sd_1_4, sd_4_1–4_4, sd_6_1, sd_6_3); chiều d1–d6 có bước nhảy theo năm nhưng thang 1–10 cố định theo thiết kế nên được ghi chú hạn chế riêng.")
body("Đây là phát hiện phương pháp quan trọng nhất của đồ án: nếu dùng sd_5_4 xuyên năm mà không audit, “cấu trúc 3 cụm ổn định” thu được hoàn toàn là artifact của việc đổi thang đo (cụm tách thuần theo giai đoạn ≤2020 vs ≥2021) — mọi số liệu huấn luyện trên cặp chỉ tiêu này đã được loại bỏ (xem Chương 6).")

# ================= CHƯƠNG 4 =================
h1("CHƯƠNG 4. PHƯƠNG PHÁP")
h2("4.1. Cấu hình STING và quy trình chọn train-only")
body("Ứng viên cặp chỉ tiêu được giới hạn ở các cột qua audit thang đo: 28 cặp từ 8 sub-dim sạch × 8 cấu hình lưới (n_levels ∈ {2,3}, factor ∈ {3,4}, min_count ∈ {4,5,8,12}, level tương ứng) = 224 tổ hợp (d1–d6 bị loại khỏi sweep — thang 1–10 chưa chứng minh tương đương xuyên năm). Tiêu chí chọn đặt TRƯỚC khi nhìn năm 2024 và PHÂN RÃ THEO BÀI TOÁN: hồi quy chọn model bằng CV expanding origin 2017–2022 thuần train; cặp chỉ tiêu + tham số STING (cho cả STING.predict và nhãn phân loại) do sweep chọn bằng cách fit ≤ 2020 và chấm coverage trên “tương lai giả” 2021–2022 (kèm k, nhiễu, độ vững mc±1) — 2 năm này trùng 2 fold CV cuối của phân loại, nên CV score phân loại hơi lạc quan. Allowlist của sweep dùng cả kiến thức ngoại sinh về PAPI 2021: sd_5_1/5_3/5_4 bị loại vì bước nhảy 2021 nằm ngoài giai đoạn train, heuristic train-only không tự bắt được. Hàm điểm = coverage − 0.5·noise − 0.15·largest − 0.02·|k−3| + 0.03·stable là heuristic chỉnh tay, không có dẫn xuất; bảo đảm chính nằm ở bộ lọc cứng (k ∈ [2,6], noise ≤ 25%, cụm lớn nhất ≤ 85%, coverage ≥ 75%) — cấu hình thoái hóa k=1 đạt điểm 0.84 cao hơn winner 0.6213 và chỉ bị chặn bởi bộ lọc này; margin top-1/top-2 = 0.018, nhỏ hơn một thành phần điểm đơn lẻ; stable_mc_pm1 = false của cấu hình thắng được đo (−0.03 điểm) nhưng không có ứng viên stable nào qua lọc, nên không dùng làm gate. Kết quả đóng băng vào models/predict_config.json: cặp sd_4_2 (4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công) × sd_6_1 (6.1 Y tế công lập); STING(L=3, factor=4, min_count=5, cluster level=2, connectivity=1); coverage 2021–2022 = 0.851. Năm 2024 không tham gia bất kỳ bước chọn nào; đánh giá cuối chỉ thực hiện MỘT LẦN sau khi đóng băng: coverage 2024 = 79%, phân bố {nhiễu: 13, cụm 2: 48}.")
h2("4.2. Kiểm thử")
body("src/sting.py có 28 unit tests (pytest, tất cả xanh; toàn suite 55 test, coverage 98% cho src/sting.py đo bằng pytest --cov): thống kê ô khớp với numpy (tol 1e-9); phục hồi 2 Gaussian blobs (ARI ≥ 0.8); biên (điểm trên biên, 1 điểm, ô rỗng); predict trước cluster → RuntimeError; out-of-support → −1; save/load khôi phục chính xác nhãn. Runtime: ~18 giây cho notebook giữa kỳ.")
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
    ("Nhánh B — 8 chiều (OFAT).", f"2018–2024 (n={N8}), trong-năm z; cấu hình gốc STING(L=3, f=2, mc=10, lv=1) + 3 nhánh OFAT đổi đúng MỘT tham số mỗi lần (f=3; mc=2; lv=2). Quy tắc chấp nhận giữ nguyên cho mọi nhánh: k≥2 & noise ≤ 50% → “có cấu trúc”, nếu không → “không nhận diện”; silhouette/db/ch tính tại từng nhánh (k<2 → n/a). Kết quả ở mục 5.4."),
])
h2("4.5. Pipeline dự đoán (hai mô hình local)")
bullets([
    ("STING.predict.", "Lưới toàn cục fit trên ≤2023; gán cụm cho mọi năm; 2024 out-of-sample; điểm ngoài vùng học → −1."),
    ("Giám sát (Ridge/RF).", "Cặp (chỉ số năm t → nhãn cụm năm t+1); bỏ 141 cặp nhãn nhiễu; CV expanding origin 2017–2022; Ridge α ∈ {0.1, 1, 10}; RF max_depth ∈ {4, 6, None}, min_samples_leaf ∈ {1, 2}; đánh giá một lần trên 2023→2024; đối chứng: lớp đa số và carry-forward."),
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
], widths=[1.6, 1.6, 1.2, 1.6, 6.0], caption="Bảng 2. STING theo từng năm (lưới thô 3×3, within-year z); 13 dòng theo mc=3, dòng 2017 đo riêng ở mc=5 (lưới 3×3)")
figure("sting_first_real.png", "Kết quả STING trên dữ liệu thật 2023 — hai mức phân giải lưới", 15.5)

h2("5.3. Pooled 2011–2023: STING vs k-means vs DBSCAN")
body("Tập gộp 2011–2023 (n=808, chỉ 8 chỉ tiêu sạch, z theo tập gộp): STING frozen cho k=3 (kích thước 629/16/5), nhiễu 20%; các chỉ số hình học tính trên điểm thuộc cụm. Hai cụm nhỏ chỉ chứa điểm 2011–2018 (không có điểm nào từ 2019) và 96.8% điểm non-noise (629/650) nằm trong cụm lớn nhất — cấu trúc “một lõi + hai vệ tinh li ti”; dịch chuyển giữa hai cụm cần đọc theo lưu ý ở 5.5.")
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
], widths=[1.8, 3.4, 0.9, 1.5, 1.5, 1.5, 1.7], caption="Bảng 3. STING vs baselines (noise tách khỏi metric hình học)")
body("Đọc bảng: k-means ép mọi điểm vào cụm và đạt silhouette 0.445 (cao nhất, k=2); STING và DBSCAN (eps nhỏ) đồng thuận tốt hơn (ARI 0.65); k-means phân vùng khác hẳn STING (ARI 0.07–0.17). Không metric nào “thắng tuyệt đối” — dữ liệu gần như một khối; mọi kết luận cần kèm noise và độ ổn định.")

h2("5.4. Robustness đa chỉ tiêu — ablation OFAT ở chiều cao")
body(f"PCA d1–d6 (trong-năm z, n={R_PCA['n']}): 2 thành phần đầu giữ {_pct(R_PCA['explained_var_total'])} phương sai; STING trên không gian PCA → k={R_PCA['k']}, nhiễu {_pct(R_PCA['noise_ratio'])}, ARI vs 2D = {R_PCA['ari_vs_2d']} — không nhận diện cấu trúc. Nhánh 8 chiều (2018–2024, n={N8}) đọc theo ablation OFAT — mỗi lần đổi đúng MỘT tham số so với cấu hình gốc (L=3 f=2 mc=10 lv=1): gốc → k={R_GOC['k']}, nhiễu {_pct(R_GOC['noise_ratio'])} (noise > 50% → không nhận diện); đổi f=3 → k={R_F3['k']}, nhiễu {_pct(R_F3['noise_ratio'])}; đổi lv=2 → k={R_LV2['k']}, nhiễu {_pct(R_LV2['noise_ratio'])}; đổi mc=2 → k={R_MC2['k']}, nhiễu {_pct(R_MC2['noise_ratio'])} — nhánh duy nhất đạt quy tắc chấp nhận cũ (k≥2 & noise ≤50%), CSV ghi verdict “có cấu trúc”, nhưng silhouette âm ({_f3(R_MC2['silhouette'])}) cho thấy hai cụm tách yếu, không phải cấu trúc mạnh. Ablation chỉ định thủ phạm thay vì chỉ kết luận âm tính chung: lv=2 làm sập hoàn toàn (toàn nhiễu), f=3 khi giữ mc=10 mất gần hết điểm; riêng mc=2 chứng tỏ nhánh 8 chiều không trống rỗng theo ngưỡng k/noise — dù không tách mạnh.")
_rob_rows = []
for _r in ROBUSTNESS:
    _branch = _r["branch"]
    _ev = (_r["explained_var_total"] or "").strip()
    if _ev:
        _branch += f" (EV {float(_ev) * 100:.1f}%)"
    _sil = (_r["silhouette"] or "").strip()
    _verdict = _r["verdict"]
    if _verdict == "có cấu trúc" and _sil and float(_sil) < 0:
        _verdict += " — silhouette âm, tách yếu"
    _rob_rows.append([_branch, _r["n"], _r["k"], _pct(_r["noise_ratio"]),
                      "n/a" if _sil == "" else _f3(_r["silhouette"]), _verdict])
table(["Nhánh", "n", "k", "noise", "Silh.", "Kết luận"], _rob_rows,
      widths=[6.2, 1.2, 0.9, 1.5, 1.5, 4.2],
      caption="Bảng 4. Robustness đa chỉ tiêu — PCA d1–d6 và ablation OFAT 8 chiều 2018–2024 (đổi một tham số mỗi lần so với gốc; nguồn: results/robustness.csv)")

h2("5.5. Pipeline dự đoán 2024 (out-of-sample)")
body("STING.predict (lưới toàn cục fit ≤2023) gán cụm 2024: 48/61 tỉnh đủ chỉ tiêu → cụm lớn; 13 → nhiễu. Không có “chuyển cụm thật” 2023→2024: 7 tỉnh chuyển sang nhiễu, 5 từ nhiễu ra (Bảng 6) — phát biểu này mang tính cấu trúc: cả 2023 lẫn 2024 không có điểm nào thuộc cụm 0/1 (hai cụm li ti chỉ có điểm 2011–2018), nên 0/59 là phát biểu rỗng, không chứng minh độ ổn định nhãn; 13/61 tỉnh vào nhiễu do ô lưới thưa (count < min_count), không phải do scaler — STING bất biến với biến đổi affine từng chiều. Lưu ý metadata: selection_metrics trong predict_config.json mô tả fit ≤ 2020 ([453,16,5]) trong khi model.pkl đóng gói là fit 2011–2023 ([629,16,5]). Hình 3 minh họa phủ cụm 2024 sau khi lưới học trên 2011–2023.")
body("Hồi quy dự báo 6.1 Y tế công lập năm sau (train 740 cặp 2011–2022, holdout 59 cặp 2023→2024). Ridge, mô hình được chọn qua CV, có MAE 0.0640 và R² 0.381, thấp hơn carry-forward (MAE 0.0683, R² 0.198) 6.3%. Random forest có MAE holdout 0.0616 (thấp hơn carry-forward 9.8%, R² 0.423) nhưng không được chọn vì R² CV thấp hơn (0.197 so với 0.265 của Ridge). Hình 4 đối chiếu dự báo hồi quy với độ quan trọng đặc trưng. CV hồi quy là expanding origin 2017–2022 theo thứ tự thời gian (không origin tương lai nào nằm trong fold huấn luyện), và holdout không được dùng để chọn mô hình. value_cv là best_score_ của GridSearchCV sau khi chọn trên chính 6 fold đó (không nested CV — hơi lạc quan, bias nhỏ vì lưới thô: spread alpha Ridge ≈ 0.001). sd_6_1 (target) nằm trong 8 đặc trưng (scripts/papi_pred_common.py:19-23) nên lợi thế 6.3% so với carry-forward chủ yếu đến từ lag-1 của chính target: bỏ sd_6_1 khỏi features, CV R² 0.265 → −0.264; corr dự báo vs carry-forward = 0.99.")
body("Phân loại dùng pseudo-label do STING sinh, trên một năm holdout 2023→2024. Logistic regression và random forest vượt baseline lớp đa số trên holdout này: accuracy 0.644 / 0.678 so với 0.186; macro-F1 0.541 / 0.600 so với 0.157. Một năm holdout không đủ để khẳng định năng lực dự báo tổng quát. Prevalence nhãn 1 trôi 0% (2011) → 92% (2021): trong mọi fold CV 2017–2022, lớp đa số train là 0 còn validation luôn đa số 1 (44–92%), nên macro-F1 CV 0.434 thực chất đo drift độ phủ; baseline mù thời gian “always dự đoán 1” đạt 0.400, chỉ thấp hơn LR 0.034.")
figure("predict_2024.png", "STING học 2011–2023 → dự đoán cụm 2024 (out-of-sample)", 13)
figure("supervised_regression.png", "Hồi quy: dự báo 6.1 Y tế công lập năm sau + độ quan trọng đặc trưng", 14.5)
table(["Model", "CV R²/F1", "Holdout MAE/acc", "Holdout F1/R²"], [
    ["Carry-forward (dự báo = giá trị năm nay)", _vn(CV_CARRY), "0.0683 MAE", "R² = 0.198"],
    ["Trung bình train", _vn(CV_MEAN), "0.0814 MAE", "R² = −0.105"],
    ["Ridge (được chọn qua CV)", "0.265", "0.0640 MAE", "R² = 0.381"],
    ["RandomForest", "0.197", "0.0616 MAE", "R² = 0.423"],
    ["Majority (lớp đa số) — phân loại", "0.228", "0.186 acc", "F1 = 0.157"],
    ["Logistic regression — phân loại", "0.434", "0.644 acc", "F1 = 0.541"],
    ["RandomForest — phân loại", "0.397", "0.678 acc", "F1 = 0.600"],
], widths=[5.6, 2.2, 3.4, 3.0], caption="Bảng 5. Hồi quy (chính) và phân loại pseudo-label STING (phụ) — CV expanding origin 2017–2022, holdout 2023→2024")
body(f"Baselines hồi quy có CV thật trên cùng 6 fold expanding origin 2017–2022, không tranh selection: (CV: carry {_vn(CV_CARRY)} vs ridge {_vn(CV_RIDGE)}); trung bình train {_vn(CV_MEAN)} — Ridge vẫn được chọn theo CV. Một holdout không chứng minh tổng quát.")
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
    ("Unit tests.", "python -m pytest tests -q → toàn bộ test xanh."),
    ("Dữ liệu.", "python scripts/check_data.py → PASS (882×41) + danh sách audit thang đo."),
    ("Tái lập.", "Mọi notebook execute sạch; mọi số liệu trong báo cáo truy được về results/*.csv; seeds cố định; PROVENANCE cho mọi nguồn."),
    ("Nguồn ngoài.", "python scripts/external_validation.py → results/external_validation.md + results/external_validation.csv + 4 hình external_* (từ data/processed/external_*.csv; provenance: data/processed/external_provenance.md, data/raw/*/PROVENANCE.md)."),
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
h2("6.4. Robustness — ablation OFAT chỉ định thủ phạm khi mở rộng chiều")
body(f"PCA d1–d6 không nhận diện cấu trúc ({_pct(R_PCA['explained_var_total'])} phương sai, k={R_PCA['k']}). Nhánh 8 chiều được đọc qua ablation OFAT: thủ phạm là tổ hợp tham số, không phải dữ liệu “quá sạch” — lv=2 sập hoàn toàn (k={R_LV2['k']}, {_pct(R_LV2['noise_ratio'])} nhiễu), f=3 khi giữ mc=10 mất gần hết điểm (k={R_F3['k']}, {_pct(R_F3['noise_ratio'])} nhiễu), gốc mc=10/lv=1 vượt ngưỡng nhiễu (k={R_GOC['k']}, {_pct(R_GOC['noise_ratio'])}); duy nhất mc=2 đạt ngưỡng k/noise (k={R_MC2['k']}, {_pct(R_MC2['noise_ratio'])}) nhưng silhouette âm ({_f3(R_MC2['silhouette'])}) — hai cụm tách yếu, không phải cấu trúc mạnh. Đây là kết quả cần báo cáo, không lược bỏ: nó bác bỏ khả năng “cấu trúc ẩn ở chiều cao”. Một cấu trúc 2D dựng lại bằng cách chọn cặp-post-hoc sẽ bị PCA phủ định — vì vậy nhóm cũng loại bỏ mọi “cấu trúc 2D post-hoc” khỏi tuyên bố khoa học.")
h2("6.5. Kiểm chứng ngoại lai (external validation)")
body("Robustness nội tại (mục 5.4) là âm tính; câu hỏi còn lại: cấu trúc học không giám sát có tương ứng với một thước đo ĐỘC LẬP — chưa từng dùng khi học — hay không? Nhóm đối chiếu nhãn cụm STING (model chốt, results/predict_all_years.csv) với các nguồn ngoài ở mục 3.1: không đưa vào feature, không nội suy ô trống; mọi thống kê tính lại trực tiếp từ CSV trong scripts/external_validation.py (số liệu đầy đủ: results/external_validation.md).")
body("Kiểm định chính — PCI [9] (khảo sát doanh nghiệp của VCCI – USAID, tách hoàn toàn khỏi PAPI là khảo sát hộ dân của CECODES/UNDP): 756 ô 2011–2022, join được 747 điểm có nhãn (9 ô có PCI nhưng panel thiếu chỉ tiêu nên không có nhãn). Phân nhóm theo nhãn STING (Bảng 7): nhiễu −1 (n=149, PCI trung bình 59.80), cụm 0 (n=5, 59.00), cụm 1 (n=16, 58.78), cụm 2 (n=577, 61.66). One-way ANOVA F(3,743) = 9.04, p = 6.9e-06; Kruskal–Wallis (phi tham số, có sửa tie) H = 31.78, p = 5.8e-07; eta² = 0.035. Đọc thận trọng: hai cụm nhỏ quá ít điểm để tự kết luận; cặp tương phản đáng tin là nhiễu vs cụm 2; Top-30 2023–2024 chỉ là kiểm tra phụ vì chọn mẫu (58/60 ô có nhãn; ANOVA p = 0.35 — không gộp với lưới đủ 63 tỉnh).")
table(["Nhãn nhóm", "n", "PCI trung bình", "Trung vị", "Độ lệch chuẩn"], [
    ["nhiễu (−1)", "149", "59.80", "59.16", "5.04"],
    ["cụm 0", "5", "59.00", "58.47", "1.06"],
    ["cụm 1", "16", "58.78", "58.19", "3.80"],
    ["cụm 2", "577", "61.66", "62.16", "4.29"],
], widths=[3.4, 1.6, 3.6, 2.6, 3.2], caption="Bảng 7. Kiểm chứng ngoại lai — PCI theo nhãn cụm STING (2011–2022, n=747); ANOVA F(3,743)=9.04, p=6.9e-06; Kruskal–Wallis H=31.78, p=5.8e-07")
figure("external_pci_by_cluster.png", "PCI theo nhãn cụm STING 2011–2022 — boxplot theo nhóm (nguồn: PCI VCCI–USAID; kết quả: results/external_validation.md)", 13.5)
body("Mật độ cơ sở y tế 2020 [11]: 423 điểm OD Mekong rơi vào 63 tỉnh (point-in-polygon), chuẩn hóa theo dân số GSO — theo quy mô nhóm: nhiễu 0.0026 cơ sở/1.000 dân (16 cơ sở/6,19 triệu người) so với cụm 2: 0.0045 (407 cơ sở/91,39 triệu); trung vị theo tỉnh 0.00075 so với 0.0022. 10 tỉnh count=0 là 0-thật (nguồn điểm không phủ tỉnh đó), không phải dữ liệu thiếu; snapshot một năm và đếm số điểm chứ không phải số giường → chỉ dùng làm external check, không đưa vào feature.")
figure("external_health_density_2020.png", "Mật độ cơ sở y tế/1.000 dân theo cụm STING — 2020 (nguồn: OD Mekong Health Facilities + GSO dân số)", 13.5)
body("GRDP/người [10] chỉ có cửa sổ 2018–2024 (441 ô; 2024 = Sơ bộ) — quyết định thiết kế: không nội suy 441 ô 2011–2017, dân số là normalizer chính xuyên panel. Join nhãn được 430/441 ô; 11 ô thiếu nhãn (panel PAPI thiếu chỉ tiêu) mask tường minh, không vẽ. Trong cửa sổ này gần như chỉ còn nhiễu vs cụm 2 (cụm 0 rỗng, cụm 1 còn 1 dòng) — hình chỉ nói điều dữ liệu cho phép.")
figure("external_grdp_by_cluster.png", "GRDP/người theo cụm STING — cửa sổ 2018–2024 (nguồn: GSO pxweb V03.12; 2024 = Sơ bộ)", 13.5)
body("Bối cảnh vĩ mô quốc gia [12] (WDI): GDP/người và % đô thị đủ 2010–2024 (15/15 năm); chi y tế thiếu 2024 (14/15); giường bệnh dừng 2017 (8/15) — chuỗi dừng phía nguồn, giữ ô trống, không nội suy. Cấp quốc gia nên chỉ dùng làm year effects/bối cảnh đọc xu hướng PAPI, không phải feature cấp tỉnh.")
figure("external_wdi_panel.png", "Bối cảnh vĩ mô quốc gia 2010–2024 (nguồn: World Bank WDI — chuỗi không đều phía nguồn, không nội suy)", 13.5)
h3("Nghèo cấp tỉnh (GSO V14.47)")
body(f"Kiểm chứng bổ trợ thứ hai dùng tỷ lệ hộ nghèo cấp tỉnh [10] — bảng GSO pxweb V14.47, số liệu thống kê chính thức tách khỏi PAPI là khảo sát hộ dân; KHÔNG đưa vào feature, KHÔNG nội suy ô thiếu. Cửa sổ giao hai nguồn 2012–2024 gồm {POV['n_win']} ô, trong đó {POV['n_val']} ô có giá trị ({POV['missing_txt']} thiếu phía nguồn — nguồn ghi “..”; 2017–2019 vốn không có trên pxweb được điền từ Niên giám Thống kê 2020/2021 — cùng chuẩn đa chiều, khớp pxweb ở cột giao 2020/2021 124/124); join nhãn cụm được {POV['n_join']} ô vào kiểm định (" + "; ".join(f"{r['group']} n={r['n']}" for r in POV_GROUPS) + f"); {POV['n_no_label']} ô tỉnh-năm có nghèo nhưng không có nhãn (panel PAPI thiếu chỉ tiêu sd_4_2/sd_6_1) được loại tường minh khỏi kiểm định. Chuẩn nghèo ĐỔI theo giai đoạn nên so mức tuyệt đối xuyên năm không like-for-like — hai kiểm định dưới đây báo cáo CÙNG nhau (số liệu đầy đủ: results/poverty_validation.md).")
table(["Nhãn nhóm", "n", "Thô — trung bình", "Thô — trung vị", "Trừ median năm — trung bình", "Trừ median năm — trung vị"], [
    [g["group"], g["n"], _vn(g["mean"]), _vn(g["median"]),
     _vn(dm["mean"]), _vn(dm["median"])]
    for g, dm in zip(POV_GROUPS, POV_GROUPS_DM)
], widths=[2.7, 1.2, 2.9, 2.4, 3.6, 3.3], caption=(
    f"Bảng 8. Nghèo GSO (%) theo nhãn cụm STING — cửa sổ giao 2012–2024 "
    f"(n={POV['n_join']}); gộp thô: Kruskal–Wallis H = {_note_val(POV_KW_RAW, 'H = ')}, "
    f"p = {_note_val(POV_KW_RAW, 'p = ')} — KHÔNG đáng kể; đã-trừ-median-năm: "
    f"H = {_note_val(POV_KW_DM, 'H = ')}, p = {_note_val(POV_KW_DM, 'p = ')} — đáng kể. "
    "Hai kết quả đọc CÙNG nhau"))
_pov_fig_no = figure("external_poverty_by_cluster.png",
                     "Tỷ lệ hộ nghèo GSO theo cụm STING — cửa sổ giao 2012–2024: "
                     "boxplot gộp (trên) và median theo năm từng cụm (dưới) (nguồn: GSO pxweb "
                     "V14.47 + NGTK 2020/2021 điền 2017–2019; kết quả: results/poverty_validation.md)", 13.5)
body(f"Đọc kết quả CÙNG nhau: gộp thô KHÔNG đáng kể (Kruskal–Wallis H = {_note_val(POV_KW_RAW, 'H = ')}, p = {_note_val(POV_KW_RAW, 'p = ')}; {POV_ANOVA_RAW['group']} = {_note_val(POV_ANOVA_RAW['note'], 'F = ')}, p = {_note_val(POV_ANOVA_RAW['note'], 'p = ')}; eta² = {_note_eta(_pov_note('poverty_pooled_raw', 'eta squared'))}) vì test gộp nhiễm hiệu ứng năm — median nghèo toàn panel giảm sâu xuyên giai đoạn và tỷ trọng cụm trôi theo năm (hàng dưới của Hình {_pov_fig_no}); đã-trừ-median-trong-năm đáng kể ở mức yếu (H = {_note_val(POV_KW_DM, 'H = ')}, p = {_note_val(POV_KW_DM, 'p = ')}; {POV_ANOVA_DM['group']} = {_note_val(POV_ANOVA_DM['note'], 'F = ')}, p = {_note_val(POV_ANOVA_DM['note'], 'p = ')}; eta² = {_note_eta(_pov_note('poverty_pooled_demeaned', 'eta squared'))}). Cặp tương phản đáng tin duy nhất nhiễu vs cụm 2 (cụm 0 n={_pov_group_n('cụm 0')}, cụm 1 n={_pov_group_n('cụm 1')} quá nhỏ để tự kết luận) không khác biệt ở mức gộp (Mann–Whitney U = {_note_val(POV_MW_RAW['note'], 'U = ')}, p = {_note_val(POV_MW_RAW['note'], 'p = ')}) và vẫn không khác biệt sau khi tách năm (U = {_note_val(POV_MW_DM['note'], 'U = ')}, p = {_note_val(POV_MW_DM['note'], 'p = ')}). Kết luận trung thực: ở mức gộp KHÔNG thấy khác biệt nghèo có ý nghĩa giữa các nhóm; tín hiệu chỉ xuất hiện sau khi tách hiệu ứng năm và yếu hơn nhiều so với kiểm định chính PCI (eta² {_note_eta(_pov_note('poverty_pooled_demeaned', 'eta squared'))} so với 0.035) — nghèo GSO đọc như kiểm chứng bổ trợ, không thay thế kiểm định chính và không chứng minh nhân quả. Tái lập: python scripts/poverty_validation.py.")
body("Tổng hợp: cấu trúc cụm STING tương ứng với một thước đo độc lập (PCI) ở mức ý nghĩa thống kê cao — luận cứ ngoài dữ liệu PAPI cho một mô hình học không giám sát. Kết quả này KHÔNG chứng minh quan hệ nhân quả và không phủ định kết luận “dữ liệu gần như một khối” (eta² nhỏ; khác biệt chủ yếu giữa nhiễu và cụm lớn). Tái lập: python scripts/external_validation.py.")
h2("6.6. Các hạn chế còn lại")
bullets([
    ("Một holdout duy nhất (2024).", "mọi kết luận dự đoán cần thêm nhiều năm; độ bất định lớn; backtest cuốn chiếu chỉ khả thi khi có thêm dữ liệu lịch sử — cấu trúc cụm thay vào đó đã được kiểm chứng bằng nguồn ngoài độc lập (mục 6.5)."),
    ("Cỡ mẫu per-year nhỏ.", "61–63 điểm/năm — nhiễu cao ở lưới mịn; cấu hình per-year bị giới hạn ở lưới thô."),
    ("Thang đo 1–10 che giấu phương sai thực.", "theo thời gian, d6 tăng 7.0→7.6 (2021) khả năng là thay đổi phương pháp khảo sát, không chỉ cải thiện; cần thận trọng khi diễn giải xu hướng."),
    ("Bản đồ chỉ có centroid.", "chưa dùng ranh giới GeoJSON (chỉ có scatter); Choropleth đầy đủ để dành báo cáo cuối (cải thiện P6)."),
    ("Nhãn DBSCAN n/a khi 1 cụm.", "một số cấu hình DBSCAN cho metric n/a — ghi rõ trong bảng, không giấu."),
    ("Nguồn ngoài không đồng đều.", "PCI 2023–2024 chỉ Top-30 (chọn mẫu — tách khỏi lưới đủ 63 tỉnh); GRDP chỉ 2018–2024 (2024 = Sơ bộ); rác thải GSO trống hoàn toàn 2018 (305/882 ô); WDI chuỗi không đều (giường bệnh dừng 2017, chi y tế thiếu 2024) — mọi thống kê external khai báo số ô chạy/tổng ô và không nội suy."),
    ("Mật độ y tế snapshot 2020.", "một năm duy nhất, đếm số điểm không phải số giường; 10 tỉnh count=0 là 0-thật (nguồn không phủ tỉnh đó)."),
    ("External validation không chứng minh nhân quả.", "eta² = 0.035 nhỏ; khác biệt PCI có ý nghĩa thống kê nhưng không cho phép suy luận quan hệ nhân quả; cụm 0 (n=5) và cụm 1 (n=16) quá ít điểm để tự kết luận."),
])
h2("6.7. Hướng phát triển")
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
    ("STING tự viết hoạt động đúng.", "ARI 0.950 trên dữ liệu giả lập; src/sting.py có 28 unit test xanh (55 test toàn suite); truy vấn vùng O(n); predict/save/load local."),
    ("Dữ liệu PAPI rất đồng nhất.", f"phân cụm theo năm đa số k=1; cấu trúc tách biệt chỉ ở ngoại vi nhỏ; robustness 8 chiều đọc theo ablation OFAT — lv=2 toàn nhiễu, f=3 {_pct(R_F3['noise_ratio'])} nhiễu, gốc {_pct(R_GOC['noise_ratio'])} nhiễu → không nhận diện; riêng mc=2 đạt ngưỡng k/noise nhưng silhouette âm — không có cấu trúc tách mạnh (báo cáo)."),
    ("Pipeline dự đoán hợp lệ phương pháp.", "chọn cấu hình train-only; 2024 out-of-sample một lần; STING.predict phủ 79%; Ridge (được chọn) thấp hơn carry-forward 6.3% MAE, RF 9.8% nhưng không được chọn vì CV R² thấp hơn; phân loại pseudo-label STING: LR và RF vượt majority trên một holdout 2023→2024 (accuracy 0.644/0.678 vs 0.186; macro-F1 0.541/0.600 vs 0.157); disclosure: value_cv là best_score_ sau chọn (không nested CV), sd_6_1 nằm trong features nên lợi thế so với carry-forward chủ yếu từ lag-1, prevalence pseudo-label trôi 0→92% nên CV phân loại đo drift độ phủ — một năm không đủ cho kết luận tổng quát."),
    ("Chất lượng dữ liệu là bài học cốt lõi.", "audit gãy thang đo (23/37 cột) tách biệt “cấu trúc thật” và artifact đổi thang — áp dụng được cho bất kỳ dữ liệu chuỗi thời gian đa phiên bản nào."),
])
h2("7.2. Hướng phát triển")
body("Xem 6.7 — trọng tâm: (1) rank-normalization xuyên năm; (2) quỹ đạo tỉnh; (3) backtest cuốn chiếu; (4) phân cụm có ràng buộc không gian; (5) nghiên cứu định tính bổ trợ. Ngoài ra, bản đồ choropleth đầy đủ (plotly + GeoJSON) và dashboard tương tác là bước trực quan tiếp theo.")
h2("7.3. Lời cuối")
body("Đồ án không “tạo ra” một cấu trúc cụm đẹp nếu dữ liệu không có nó; đồ án cung cấp: (i) một cài đặt STING hoàn chỉnh, kiểm thử kỹ; (ii) một quy trình dữ liệu nghiêm ngặt (audit thang đo, train-only selection) mà mọi phân tích PAPI xuyên năm nên áp dụng; (iii) báo cáo trung thực cả robustness mở rộng chiều (PCA âm tính; nhánh 8 chiều OFAT — mc=2 vượt ngưỡng k/noise với silhouette âm, các nhánh còn lại không nhận diện) lẫn kết quả dương tính. Nhóm tin rằng đây là cách học máy được ứng dụng có trách nhiệm vào nghiên cứu chính sách công.")
h2("7.4. Khai báo sử dụng công cụ hỗ trợ")
body("Nhóm sử dụng trợ lý AI lập trình trong một số phần của đồ án: khung code ban đầu cho một số script dữ liệu/trực quan, gỡ lỗi, và dry-run đo thời gian chuẩn bị demo (nhật ký rehearsal_log.md mục A ghi rõ phần dry-run do AI/từng cá nhân tự chạy). Mọi quyết định phương pháp, quy trình chọn cấu hình, đánh giá và kết luận do hai thành viên quyết định và kiểm chứng lại; cả hai thành viên chịu trách nhiệm giải thích mọi phần của đồ án. Môn học chưa quy định rubric khai báo cụ thể — nhóm chủ động khai báo theo thông lệ liêm chính học thuật.")

# ================= PHỤ LỤC A =================
h1("PHỤ LỤC A — LỆNH TÁI LẬP & KIỂM TRA")
body("Mọi bước dưới đây chạy từ thư mục gốc repo và cho kết quả như cột kỳ vọng; môi trường đã kiểm chứng: Python 3.14.2, Windows 11, dependencies trong requirements.txt.")
table(["Lệnh", "Kỳ vọng"], [
    ["python scripts/build_panel.py", "data/processed/papi_panel_63_2011_2024.csv (882×41); log 2 định dạng nguồn"],
    ["python scripts/check_data.py", "PASS — ≥500 hàng, ≥10 cột số; in danh sách audit gãy thang đo (23/37)"],
    ["python scripts/crosscheck_mendeley.py", "max |diff| = 0.0; ghi reports/crosscheck_mendeley.md"],
    ["python -m pytest tests -q", "toàn bộ test xanh"],
    ["python scripts/predict_sweep.py", "chọn cấu hình train-only; ghi models/predict_config.json + results/predict_config_search.csv"],
    ["python scripts/predict_demo.py", "dự đoán 2024; results/predict_summary.md (phủ 79%)"],
    ["python scripts/predict_supervised.py", "Ridge (được chọn) MAE thấp hơn carry-forward 6.3%; RF 9.8% nhưng không được chọn vì CV R² thấp hơn; metrics CSV"],
    ["python scripts/run_analysis.py", "metrics.csv, per_year.csv, robustness.csv, evolution/map hình, analysis_summary.md"],
    ["python scripts/build_external_master.py", "data/processed/external_master_63_2011_2024.csv (882×59, mask tường minh) + results/external_master_summary.md"],
    ["python scripts/external_validation.py", "results/external_validation.md + results/external_validation.csv + 4 hình external_* (ANOVA/Kruskal PCI, y tế 2020, GRDP, WDI)"],
    ["python scripts/poverty_validation.py", "results/poverty_validation.md + results/poverty_validation.csv + results/figs/external_poverty_by_cluster.png (KW gộp thô & đã-trừ-median-năm; Mann–Whitney nhiễu vs cụm 2)"],
    ["python -m nbconvert --to notebook --execute --inplace notebooks/midterm_demo.ipynb", "execute sạch ~18s, 18 cells, 0 lỗi"],
    ["python -m nbconvert --to notebook --execute --inplace notebooks/final_analysis.ipynb", f"execute sạch, {NB_CELLS} cells, {NB_IMGS} hình nhúng (đếm từ notebook đã execute)"],
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
    "VCCI – USAID. Chỉ số Năng lực cạnh tranh cấp tỉnh (PCI). pcivietnam.vn — dữ liệu công khai, tái sử dụng ghi nguồn VCCI–USAID.",
    "Tổng cục Thống kê (GSO/NSO). PX-Web pxweb.nso.gov.vn (dân số, GRDP cấp tỉnh) và Niên giám Thống kê, nso.gov.vn — dữ liệu thống kê chính thức công khai (trang bảng ghi “Bản quyền: Không”).",
    "Open Development Vietnam (OD Mekong). Health Facilities in Mekong Countries 2020. Giấy phép ODbL.",
    "World Bank. World Development Indicators (WDI) — Việt Nam (VNM), 2010–2024. CC BY 4.0.",
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
