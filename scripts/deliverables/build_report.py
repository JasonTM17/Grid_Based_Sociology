"""Build reports/final_report.docx — báo cáo cuối kỳ (tiếng Việt, 7 chương).

Định dạng theo mẫu Báo cáo cuối kì: bìa có logo và khung, trang riêng
cho nhóm thực hiện, mục lục và các danh mục. Chương 1 bắt đầu từ trang 1.
Thông số và nguồn mẫu được ghi trong reports/report_format_notes.md.

Cách dùng: python scripts/deliverables/build_report.py
Trước khi đóng gói, chạy scripts/deliverables/update_report_fields.py bằng Word.
"""

import ast
import csv
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.deliverables.report_style import apply_reference_style  # noqa: E402

FIGS = ROOT / "results" / "figs"
OUT = ROOT / "reports" / "final_report.docx"




def _read_results_csv(name):
    with open(ROOT / "results" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


SUP_ROWS = _read_results_csv("supervised_metrics.csv")
CLUSTER_METRICS = _read_results_csv("metrics.csv")
ROBUSTNESS = _read_results_csv("robustness.csv")
PREPROC_AUDIT = _read_results_csv("preprocessing_audit.csv")
COURSE_SUP_ROWS = _read_results_csv("course_supervised_baselines.csv")


def _preprocessing_audit_table():
    return [[r["test"], r["result"], r["decision"]] for r in PREPROC_AUDIT]


def _course_baselines_table():
    rows = []
    for r in COURSE_SUP_ROWS:
        rows.append([
            r["model"],
            r["metric_cv"],
            _vn(r["value_cv"]),
            _vn(r["holdout_acc"]),
            _vn(r["holdout_macro_f1"]),
        ])
    return rows


def _vn(v):
    """Hiển thị số âm với dấu trừ kiểu typography (U+2212) khớp phần còn lại của báo cáo."""
    return str(v).replace("-", "−")


def _pct(v):
    s = f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
    return s + "%"


def _f3(v):
    v = (v or "").strip()
    return "n/a" if v == "" else _vn(f"{float(v):.3f}")


PREPROCESSING_AUDIT_TABLE = _preprocessing_audit_table()
COURSE_BASELINES_TABLE = _course_baselines_table()


FORECAST = json.loads((ROOT / "results" / "papi_forecast_2024.json").read_text(encoding="utf-8"))
FORECAST_SCORES = {(row["target"], row["method"]): row for row in FORECAST["scores"]}
FORECAST_ZONES = {row["method"]: row for row in FORECAST["grid"]}


def _dec(value, digits=4):
    return _vn(f"{value:.{digits}f}".replace(".", ","))


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
N8 = R_GOC["n"]


PREDICT_SWEEP_CONFIGS = [
    (3, 3, 4, 2), (3, 3, 5, 2), (3, 3, 8, 2), (3, 3, 12, 2),
    (3, 4, 5, 2), (3, 4, 8, 2), (2, 3, 12, 1), (2, 4, 8, 1),
]
SWEEP_CONFIG_TXT = "; ".join(
    f"L={L} f={f} mc={mc} lv={lv}" for L, f, mc, lv in PREDICT_SWEEP_CONFIGS
)

SUITE_OK = "toàn bộ test suite pass"


def _vn_thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _mendeley_overlap_total() -> int:
    text = (ROOT / "reports" / "crosscheck_mendeley.md").read_text(encoding="utf-8")
    total = 0
    for line in text.splitlines():
        m = re.match(r"\| d\d+ \| (\d+) \|", line)
        if m:
            total += int(m.group(1))
    if total == 0:
        raise ValueError("reports/crosscheck_mendeley.md: không đọc được overlap")
    return total


MENDELEY_OVERLAP = _mendeley_overlap_total()
MENDELEY_OVERLAP_TXT = _vn_thousands(MENDELEY_OVERLAP)


def _per_year_table_rows():
    rows = []
    for r in _read_results_csv("per_year.csv"):
        sizes = ast.literal_eval(r["cluster_sizes"].strip())
        sizes_txt = ", ".join(str(x) for x in sizes)
        rows.append([
            str(r["year"]), str(r["n"]), str(r["k"]),
            _pct(r["noise_ratio"]), sizes_txt,
        ])
    return rows


PER_YEAR_TABLE = _per_year_table_rows()


def _classification_supervised_bullet() -> str:
    for p in (ROOT, ROOT / "src"):
        ps = str(p)
        if ps not in sys.path:
            sys.path.insert(0, ps)
    from scripts.common.papi_pred_common import load_config, load_panel
    from scripts.supervised.predict_supervised import build_classification_pairs

    cfg = load_config()
    pairs = build_classification_pairs(load_panel(), cfg["features"], cfg["sting"])
    total = len(pairs)
    noise = int((pairs["y"] == 0).sum())
    n_train = int(((pairs["y"] == 0) & (pairs["year_t"] <= 2022)).sum())
    n_hold = int(((pairs["y"] == 0) & (pairs["year_t"] == 2023)).sum())
    return (
        f"Cặp (chỉ số năm t → nhãn cụm năm t+1); {total} cặp nhãn, trong đó "
        f"{noise} điểm nhiễu được gán nhãn 0 ({n_train} train / {n_hold} holdout); "
        "CV expanding origin 2017–2022; Ridge α ∈ {0.1, 1, 10}; "
        "RF max_depth ∈ {4, 6, None}, min_samples_leaf ∈ {1, 2}; "
        "đánh giá một lần trên 2023→2024; đối chứng: lớp đa số và carry-forward."
    )


CLASSIFICATION_SUP_BULLET = _classification_supervised_bullet()

POV_ROWS = _read_results_csv("poverty_validation.csv")


def _pov_note(section, group):
    """Note kiểm định do scripts/analysis/poverty_validation.py tự tính (không hardcode)."""
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


_nb = json.loads((ROOT / "notebooks" / "Nhom15_CuoiKy_STING_PAPI.ipynb").read_text(
    encoding="utf-8"))
NB_CELLS = len(_nb["cells"])
NB_IMGS = sum(1 for c in _nb["cells"] for out in c.get("outputs", [])
              if isinstance(out.get("data"), dict) and "image/png" in out["data"])

NAVY = RGBColor(0x0F, 0x2B, 0x46)
TEAL = RGBColor(0x1B, 0x6E, 0x77)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x5A, 0x5A, 0x5A)

doc = Document()
doc.core_properties.title = "Phân cụm dựa trên lưới STING trên dữ liệu PAPI 2011–2024"
doc.core_properties.subject = "Báo cáo cuối kỳ môn Học máy, Nhóm 15"
doc.core_properties.author = "Nguyễn Tiến Sơn · Trần Thị Ngọc Quyên"


def set_run(run, size=12, bold=False, color=INK, italic=False, name="Times New Roman"):
    f = run.font
    f.name = name
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color

    rpr = run._element.rPr
    if rpr is not None:
        rFonts = rpr.rFonts
        if rFonts is not None:
            rFonts.set(qn("w:hAnsi"), name)
            rFonts.set(qn("w:cs"), name)


def _append_field_to_run(run, instruction: str, cached: str | None = None):
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    el = run._element
    el.append(fld_begin)
    el.append(instr)
    el.append(fld_sep)
    if cached is not None:
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = cached
        el.append(t)
    el.append(fld_end)


def _paragraph_field(paragraph, instruction: str, placeholder: str, *, size=10.5,
                    bold=False, color=INK, italic=False):
    """Word field với kết quả tạm (cập nhật bằng scripts/deliverables/update_report_fields.py)."""
    run = paragraph.add_run()
    set_run(run, size, bold, color, italic)
    _append_field_to_run(run, instruction, placeholder)


def h1(text):
    para = doc.add_heading("", level=1)
    if text.startswith("CHƯƠNG ") and not text.startswith("CHƯƠNG 1."):
        para.paragraph_format.page_break_before = True
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
    para = doc.add_paragraph(style="Body Text")
    r = para.add_run(text)
    set_run(r, 13, False, INK, italic)
    return para


def front_title(text):
    para = doc.add_paragraph(text, style="Title")
    para.paragraph_format.page_break_before = True
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
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    t.style = doc.styles["Table Grid"]
    t.autofit = widths is None
    for column, width in zip(t.columns, widths or []):
        column.width = Cm(width)
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
    if caption:
        for cell in t.rows[-1].cells:
            cell.paragraphs[-1].paragraph_format.keep_with_next = True
        cp = doc.add_paragraph(style="Caption")
        cp.add_run("Bảng ")
        _paragraph_field(cp, "SEQ Bảng \\* ARABIC", str(TABLE_NO[0]), size=12, bold=True, italic=True)
        cp.add_run(f". {caption}")
    return t


def _shade_cell(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    wshd = OxmlElement("w:shd")
    wshd.set(qn("w:val"), "clear")
    wshd.set(qn("w:color"), "auto")
    wshd.set(qn("w:fill"), hex_fill)
    tcPr.append(wshd)


FIG_NO = [0]
TABLE_NO = [0]


def tbl_caption(title):
    TABLE_NO[0] += 1
    return title


def figure(fname, caption, width_cm=12.5):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(2)
    para.paragraph_format.keep_with_next = True
    para.add_run().add_picture(str(FIGS / fname), width=Cm(width_cm))
    FIG_NO[0] += 1
    n = FIG_NO[0]
    cp = doc.add_paragraph(style="Caption")
    cp.add_run("Hình ")
    _paragraph_field(cp, "SEQ Hình \\* ARABIC", str(n), size=12, bold=True, italic=True)
    cp.add_run(f". {caption}")
    return n


def _catalog_field(caption_label: str):
    p1 = doc.add_paragraph()
    r = p1.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f'TOC \\h \\z \\c "{caption_label}"'
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    r._element.append(fld1)
    r._element.append(it)
    r._element.append(fld2)


def toc_field():
    p1 = doc.add_paragraph()
    r = p1.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = 'TOC \\o "1-3" \\h \\z \\u'
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    r._element.append(fld1)
    r._element.append(it)
    r._element.append(fld2)



doc.add_section(WD_SECTION_START.NEW_PAGE)
team = h1("NHÓM THỰC HIỆN")
team.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph("Học phần: Học máy (MALE431984) · Nhóm 15")
doc.add_paragraph("Giảng viên hướng dẫn: ThS. Lê Minh Tân")
table(["STT", "Họ và tên", "Mã số sinh viên"], [
    ["1", "Nguyễn Tiến Sơn", "24110054"],
    ["2", "Trần Thị Ngọc Quyên", "24110051"],
], widths=[2.0, 8.3, 6.2])
topic_line = doc.add_paragraph("Chủ đề 6: Phân cụm dựa trên lưới (Grid-based clustering).")
topic_line.paragraph_format.space_before = Pt(8)
doc.add_paragraph("Mã nguồn dự án: https://github.com/JasonTM17/Grid_Based_Sociology")


front_title("TÓM TẮT")
body("Đồ án nghiên cứu phân cụm dựa trên lưới, chọn một biến thể STING rút gọn theo ngưỡng số điểm và áp dụng lên dữ liệu PAPI cấp tỉnh [1,2]. Từ 14 workbook giai đoạn 2011–2024, nhóm xây dựng bảng 882 quan sát tỉnh–năm và 41 cột, đáp ứng quy mô dữ liệu của học phần [8]. Các bước tiền xử lý gồm kiểm tra trùng khóa, giữ giá trị thiếu có cấu trúc, đối chiếu thang đo và chuẩn hóa bằng dữ liệu huấn luyện. Phân tích chính sử dụng hai chỉ tiêu: kiểm soát tham nhũng trong cung ứng dịch vụ công và y tế công lập.")
body("Trên 240 điểm giả lập có hai nhóm tham chiếu, cài đặt cho ARI 0,950 và 2,5% nhiễu. Với hai chỉ tiêu PAPI giai đoạn 2011–2023, cấu hình chính tạo một cụm 629 điểm, hai cụm nhỏ 16 và 5 điểm, cùng 19,6% nhiễu. Lưới 2011–2023 gán 48/61 tỉnh có hai điểm PAPI 2024 quan sát vào cụm lớn. Thử nghiệm hồi cứu tiếp theo dùng hồi quy để dự báo cả hai điểm 2024 từ tám chỉ tiêu 2023. Trên 59 tỉnh đối chiếu được, Ridge có MAE thấp hơn cách giữ điểm năm trước ở cả hai chỉ tiêu, trong khi RMSE của 4.2 tăng nhẹ. Khi đưa các dự báo điểm vào lưới, cả 59 tỉnh vào cụm lớn và bỏ sót 11 tỉnh có quan sát ngoài vùng dày. Phân tích giới hạn ở hai chỉ tiêu và một năm đối chiếu.")
body("Từ khóa: STING, phân cụm dựa trên lưới, PAPI, dữ liệu tỉnh–năm.", italic=True)


front_title("LỜI MỞ ĐẦU")
body("Đề tài thuộc Topic 6 — Grid-based clustering. Theo bài giảng, cuối kỳ cần dữ liệu thật có hơn 500 dòng và 10 cột, báo cáo Word và notebook. Nhóm chọn tự cài đặt biến thể STING bằng NumPy để giải thích cơ chế lưới; đây là lựa chọn triển khai của nhóm. Scikit-learn hỗ trợ chuẩn hóa, chỉ số đánh giá và các mô hình đối chứng. PAPI được chọn vì dữ liệu công khai, có 14 năm và nhiều chỉ tiêu về quản trị, dịch vụ công.")
body(f"Đồ án gồm: cài đặt STING từ đầu (src/sting.py); pipeline dữ liệu từ 14 workbook gốc; đối chiếu chéo với gói replication nghiên cứu công bố (Mendeley, CC BY 4.0 — lệch 0.0 trên {MENDELEY_OVERLAP_TXT} cặp giá trị có dữ liệu trên 8 chiều, tính từ reports/crosscheck_mendeley.md) [3]; phân cụm các năm; so sánh với k-means/DBSCAN; robustness đa chỉ tiêu; bản đồ 63 tỉnh; và dự báo hai điểm PAPI rồi dùng lưới STING để đối chiếu vùng năm 2024.")
body("Mã nguồn lưu các bước dựng panel, kiểm tra dữ liệu, chọn cấu hình và phân tích kết quả. Notebook cuối kỳ tái lập ví dụ giả lập, nhãn STING và sai số dự báo từ panel đã lưu, đồng thời đọc các bảng và hình thực nghiệm. Notebook tiền xử lý PAPI dựng lại bảng từ các tệp Excel gốc; lệnh tái lập được tổng hợp ở Phụ lục A.")
body("Nhóm xin chân thành cảm ơn ThS. Lê Minh Tân và Bộ môn Trí tuệ nhân tạo đã hướng dẫn và góp ý trong quá trình thực hiện đồ án. Nhóm trân trọng ghi nhận các tổ chức cung cấp dữ liệu công khai được dẫn trong báo cáo.")


front_title("MỤC LỤC")
toc_field()


front_title("DANH MỤC CHỮ VIẾT TẮT")
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

front_title("DANH MỤC HÌNH ẢNH")
_catalog_field("Hình")

front_title("DANH MỤC BẢNG")
_catalog_field("Bảng")
doc.add_section(WD_SECTION_START.NEW_PAGE)


h1("CHƯƠNG 1. TỔNG QUAN ĐỀ TÀI")
h2("1.1. Bối cảnh và vấn đề đặt ra")
body("Chỉ số PAPI (Vietnam Provincial Governance and Public Administration Performance Index) được CECODES, VFF-CRT, RTA & UNDP công bố hàng năm từ 2011, đo lường chất lượng quản trị và cung ứng dịch vụ công ở cấp tỉnh trên 8 yếu tố (từ 2018): Tham gia ở cấp cơ sở (d1), Minh bạch (d2), Trách nhiệm giải trình (d3), Kiểm soát tham nhũng (d4), Thủ tục hành chính công (d5), Cung ứng dịch vụ công (d6), Quản trị môi trường (d7), Quản trị điện tử (d8). Đề bài môn Học máy (Topic 6 — Grid-based clustering) yêu cầu một thuật toán phân cụm dựa trên lưới, dataset thật ≥ 500 dòng × ≥ 10 cột, và nhóm chọn PAPI vì hai lý do: (i) dữ liệu công khai, có chuỗi thời gian dài (14 năm × 63 tỉnh); (ii) cơ sở dữ liệu đủ chiều để thử thách grid-based clustering ở chiều thấp.")
body("Bài toán thực tiễn: muốn phân loại các tỉnh theo nhóm cung ứng dịch vụ công/kiểm soát tham nhũng để hỗ trợ hoạch định chính sách. Câu hỏi nghiên cứu: (1) dữ liệu PAPI có cấu trúc cụm tách biệt không; (2) cấu trúc đó ổn định qua thời gian không; (3) mô hình hồi quy từ dữ liệu đến 2023 dự báo hai điểm PAPI 2024 với sai số ra sao và nhận diện vùng trên lưới STING đến mức nào.")
h2("1.2. Mục tiêu và phạm vi")
bullets([
    ("Mục tiêu 1.", "Hiện thực từ đầu các ý tưởng cốt lõi của STING (Wang–Yang–Muntz, VLDB 1997) và nêu rõ phần đơn giản hóa ở Chương 2: lưới phân cấp, thống kê ô, gom cụm, nhãn nhiễu −1."),
    ("Mục tiêu 2.", "Xây pipeline dữ liệu PAPI 2011–2024 → panel 882×41; kiểm chứng với gói replication công bố (Mendeley, CC BY 4.0): max |diff| = 0.0."),
    ("Mục tiêu 3.", "Phân cụm theo năm + tập gộp; so sánh STING vs k-means vs DBSCAN (metric hình học tách nhãn nhiễu)."),
    ("Mục tiêu 4.", "Robustness: PCA d1–d6 toàn panel; nhánh 8 chiều 2018–2024 — ablation OFAT, đổi đúng một tham số mỗi lần so với cấu hình gốc."),
    ("Mục tiêu 5.", "Dự báo 4.2 và 6.1 bằng mô hình chọn theo thời gian. Dùng cùng lưới STING để đối chiếu dự báo và quan sát với mốc giữ điểm năm trước."),
])
body("Phạm vi: 63 tỉnh/thành Việt Nam, 2011–2024, cấp tỉnh/năm. Không phân tích cấp huyện, không dự đoán sau 2024; các nguồn khảo sát ngoài (PCI, GSO, OD Mekong, WDI — mục 3.1) chỉ dùng để kiểm chứng bên ngoài, không đưa vào huấn luyện (mục 6.5).")
h2("1.3. Đóng góp của đồ án")
bullets([
    ("Kỹ thuật.", f"STING tự cài (src/sting.py); bộ test STING (`tests/test_sting.py`) xanh ({SUITE_OK}); quy trình gán cụm và dự báo bổ trợ; quy trình chọn cấu hình chống selection-on-test."),
    ("Dữ liệu.", "Panel 882×41; audit thang đo xuyên năm (23/37 cột bị cờ heuristic bước nhảy > 0.25) — lần đầu được hệ thống hóa cho PAPI trong phạm vi đồ án; PROVENANCE + hash cho mọi nguồn."),
    ("Thực nghiệm.", "Trên hai chỉ tiêu và cấu hình chính, một cụm lớn chiếm ưu thế so với hai cụm nhỏ. Các thử nghiệm PCA và 8 chiều cho thấy kết quả nhạy với đặc trưng, mức lưới và ngưỡng số điểm; chưa đủ cơ sở để suy ra cấu trúc chung của toàn bộ dữ liệu PAPI."),
])


h1("CHƯƠNG 2. CƠ SỞ LÝ THUYẾT")
h2("2.1. Grid-based clustering")
body("Grid-based clustering chia không gian đặc trưng thành các ô lưới và dùng thông tin tóm tắt của ô để tìm vùng điểm dày. Lưới được đặt trên các chỉ tiêu phân tích, không phải lưới chia bản đồ địa lý. Khi số chiều và cấu hình được giữ cố định, chi phí thống kê có thể tăng gần tuyến tính theo số điểm. Phương pháp nhạy với độ phân giải, ngưỡng số điểm và hướng trục; khi số chiều tăng, dữ liệu dễ phân tán vào nhiều ô thưa.")
h2("2.2. STING (STatistical INformation Grid)")
body("STING gốc của Wang, Yang và Muntz (VLDB 1997) lưu số điểm, trung bình, độ lệch chuẩn, cực trị và loại phân phối của từng thuộc tính. Truy vấn đánh giá độ liên quan ở lớp thô rồi duyệt tiếp các ô con liên quan. Thống kê của ô cha có thể được gộp từ thống kê các ô con [1].")
body("Trong đồ án, fit tính thống kê từ các điểm ở từng mức. Pipeline PAPI chọn một mức, lấy ô có số điểm đạt min_count rồi gom các ô dày kề nhau thành cụm. Điểm trong ô thưa nhận nhãn −1. Tùy chọn significance_z so trung bình ô con với ô cha và được tắt trong cấu hình chính. Notebook minh họa riêng truy vấn phân cấp query_top_down. Phép truy vấn ước lượng xác suất theo phân phối chuẩn của từng chiều và giả định các chiều độc lập.")
h2("2.3. Cài đặt trong đồ án (src/sting.py)")
bullets([
    ("fit(X).", "Dựng L mức trên n điểm d chiều; với khóa ô nguyên và stable radix sort của NumPy đang dùng, chi phí theo dữ liệu khoảng O(L·n·d). Không coi số mức và số chiều luôn bằng hằng số khi phân tích tổng quát. Refit hủy nhãn cũ, cần cluster lại trước predict."),
    ("cluster(level).", "Chọn ô dày → gom thành phần liên thông trên đồ thị kề ô (BFS/DFS) → gán nhãn điểm; nhãn −1 cho điểm không nằm trong ô dày."),
    ("predict(X).", "Điểm MỚI: tìm ô chứa nó ở mức đã dùng → cụm của ô đó; nếu ô không dày hoặc điểm ngoài vùng huấn luyện → −1."),
    ("query_rect(rect).", "Quét M ô có dữ liệu ở một mức và gộp các ô nằm trọn trong vùng. Phương sai gộp tính cả độ phân tán trong từng ô và chênh lệch giữa trung bình các ô, với trọng số là số điểm. Chi phí truy vấn là O(M·d). Khi phân cụm, mỗi ô có tối đa 2d láng giềng nếu nối qua mặt và 3^d−1 nếu tính cả góc. Chi phí chung còn gồm bước sắp xếp các ô dày."),
    ("query_top_down(rect).", "Duyệt từ gốc đến mức đích. Với ô cha giao một phần vùng truy vấn, chương trình có thể dừng nhánh nếu xác suất ước lượng có ít nhất một điểm trong vùng thấp hơn 1 − confidence. Kết quả gộp thống kê của các ô nằm trọn trong vùng tại mức đích."),
    ("save/load.", "Lưu và nạp lại lưới đã xác định cụm. Khi gán điểm quan sát mới, quy trình dùng cùng bộ chuẩn hóa đã lưu riêng."),
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
body("WCSS là tổng khoảng cách bình phương từ điểm tới centroid của cụm. K-Means tối ưu WCSS với k cố định; tăng k thường làm WCSS giảm nên cần đọc elbow cùng chỉ số khác. STING sinh k từ lưới và có noise: không so WCSS hay silhouette giữa các tập điểm khác nhau như một bảng xếp hạng tuyệt đối; luôn báo cả cỡ cụm và tỷ lệ noise. Dendrogram của Hierarchical Clustering ghi thứ tự ghép cụm theo khoảng cách, còn hierarchy của STING là chia không gian hình học; hai loại cây không đồng nghĩa.")
body("Mỗi yếu tố PAPI chuẩn hóa về 1–10 điểm theo năm; chỉ tiêu thành phần có thang riêng và có thể đổi thang giữa các phiên bản (vd 5.4 đổi 0.25–2.5 → 0.33–3.33 tại 2021 khi cấu trúc chỉ tiêu thay đổi). Vì vậy sử dụng xuyên năm buộc phải kiểm tra thang từng chỉ tiêu — làm bằng audit bước nhảy trung bình năm trong scripts/data/check_data.py (ngưỡng 0.25 điểm).")


h1("CHƯƠNG 3. DỮ LIỆU VÀ TIỀN XỬ LÝ")
h2("3.1. Nguồn dữ liệu và PROVENANCE")
bullets([
    ("PAPI 2011–2024.", "14 workbook chính thức từ papi.org.vn; manifest tên file + bytes + SHA-256: data/raw/papi/PROVENANCE.md. 3 file (2020/2021/2023) khớp tuyệt đối SHA-256 với gói replication Mendeley."),
    ("Mendeley replication.", "Le et al., Mendeley Data, DOI 10.17632/wbk42j9wc8.1, CC BY 4.0. 4 file nhỏ dùng trực tiếp (crosswalk, centroids, panel đối chiếu, ledger hash) đã commit kèm PROVENANCE.md; phần còn lại tải theo DOI."),
    ("GeoJSON tỉnh.", "Open Development Vietnam (OD Mekong), CC-BY-SA 4.0 [4]. Lưu ý: `code` hằng 'AD01' — join bản đồ qua centroids theo province_code; 6 tên tỉnh lệch có bảng alias."),
    ("PCI 2011–2024.", "Chỉ số Năng lực cạnh tranh cấp tỉnh — VCCI – USAID: workbook + trang xếp hạng từ pcivietnam.vn (dữ liệu công khai, ghi nguồn VCCI–USAID) [9]. Đủ 63 tỉnh × 12 năm 2011–2022 = 756 ô; 2023–2024 chỉ công bố Top-30 (chỉ dùng kiểm tra phụ, cảnh báo chọn mẫu). raw: data/raw/pci/PROVENANCE.md; chuẩn hóa: data/processed/external_provenance.md."),
    ("GSO/NSO — dân số & GRDP.", "PX-Web chính thức pxweb.nso.gov.vn (“Bản quyền: Không”) + Niên giám Thống kê [10]: dân số theo tỉnh đủ 882 tỉnh-năm (2 vintage — 378 dòng pxweb + 504 dòng Niên giám — giữ nguyên từng vintage, không trộn bình quân); GRDP/người 441 ô 2018–2024 (2024 = Sơ bộ). raw: data/raw/gso/PROVENANCE.md."),
    ("OD Mekong — Health Facilities 2020.", "2.169 điểm cơ sở y tế các nước Mekong (ODbL) [11]; 423 điểm rơi vào Việt Nam qua point-in-polygon với GeoJSON 63 tỉnh; 10 tỉnh không có điểm cơ sở y tế trong nguồn; số 0 chỉ là số điểm quan sát được, không khẳng định địa phương thực tế không có cơ sở y tế."),
    ("World Bank WDI.", "4 chỉ số vĩ mô quốc gia VNM 2010–2024, CC BY 4.0 [12] — dùng làm bối cảnh, không phải feature cấp tỉnh."),
    ("Bảng master nối nguồn.", "scripts/data/build_external_master.py nối panel PAPI + các nguồn trên theo khóa (papi_province_code, year) — validate one-to-one giữ đúng 882 dòng, cột mask thiếu tường minh từng nguồn (PCI 816/882; dân số 882/882; GRDP 441/882; y tế 63/882; rác thải 305/882, trống hoàn toàn 2018), không nội suy: data/processed/external_master_63_2011_2024.csv (882×59)."),
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
    ["Đối chiếu chéo Mendeley", f"max |diff| = 0.0 ({MENDELEY_OVERLAP_TXT} so sánh trên 8 chiều)"],
    ["Tên tỉnh 63/63 mỗi năm", "Đạt (assert trong parser)"],
], widths=[8.0, 8.0], caption=tbl_caption("Kiểm chứng chất lượng dữ liệu"))
h2("3.4. Audit thang đo xuyên năm (điểm mới)")
body("Nhóm đánh dấu 23/37 chỉ tiêu có chênh lệch trung bình giữa hai năm liền kề vượt 0,25 điểm. Đối chiếu workbook cho thấy sd_5_1, sd_5_3 và sd_5_4 đổi từ thang 0,25–2,5 sang 0,33–3,33 vào năm 2021. Với sd_2_1, mức tăng 1,355 điểm vào năm 2018 là dấu hiệu cần kiểm tra thêm. Các workbook đối chiếu quanh năm 2021 ghi cùng khoảng điểm cho sd_3_2 (0,33–3,33) và sd_6_4 (0,25–2,5). Cùng khoảng điểm vẫn cần đối chiếu nội dung chỉ tiêu và cách khảo sát khi so sánh qua các năm.")
body("Nhóm dùng tám chỉ tiêu đã đối chiếu khoảng điểm để tạo các cặp ứng viên STING và làm đầu vào cho mô hình hồi quy bổ trợ. Phân tích STING chính chọn hai chỉ tiêu sd_4_2 và sd_6_1. Bảng metadata ở data/processed/papi_panel_scale_metadata.csv ghi các khoảng điểm và nguồn đối chiếu.")
h2("3.5. Kiểm tra quy trình tiền xử lý")
body("Quy trình gồm làm sạch dữ liệu, tích hợp theo khóa và chuẩn hóa chỉ tiêu. Bước làm sạch kiểm tra trùng khóa, giá trị thiếu, tính nhất quán và ngoại lai. Bước tích hợp kiểm tra khóa nối và số dòng sau khi ghép. Bảng kiểm tra đọc từ results/preprocessing_audit.csv, sinh bởi scripts/data/preprocessing_audit.py. Giá trị thiếu được giữ là NaN; chỉ các dòng đủ đặc trưng mới được đưa vào từng phép phân tích. Các ô có |z|>3 được đánh dấu để khảo sát và vẫn giữ trong panel. Cờ ngoại lai z-score và nhãn nhiễu STING là hai quy tắc khác nhau: điểm chỉ nhận nhãn −1 khi không thuộc ô dày hoặc nằm ngoài vùng lưới đã học.")
table(
    ["Test", "Kết quả", "Quyết định"],
    PREPROCESSING_AUDIT_TABLE,
    widths=[4.8, 4.8, 6.4],
    caption=tbl_caption(
        "Kiểm tra quy trình tiền xử lý — nguồn: results/preprocessing_audit.csv"
    ),
)
h2("3.6. Quyết định tiền xử lý và giới hạn")
body(
    "Tóm tắt các quyết định xử lý dựa trên kết quả kiểm tra và giới hạn thiết kế liên quan baseline "
    "học phần — số đo trong cột giữa trích từ results/preprocessing_audit.md và "
    "results/course_supervised_baselines.md; chi tiết đầy đủ ở Bảng trên, không lặp từng test."
)
table(
    ["Quyết định", "Số đo", "Lý do"],
    [
        [
            "Không nội suy ô thiếu",
            "4284/4649 ô thiếu nằm ngoài cửa sổ thu thập của cột",
            "Thiếu là cấu trúc (chỉ tiêu chưa thu thập trong năm); điền giả định làm sai ý nghĩa "
            "điểm PAPI — chỉ loại dòng bằng dropna khi ghép cặp feature.",
        ],
        [
            "Giữ ngoại lai, không xóa",
            "122 ô |z|>3 (0,4%)",
            "Giữ điểm khảo sát và chỉ đánh dấu. Cờ z-score không quyết định nhãn STING; "
            "nhãn nhiễu phụ thuộc ô chứa điểm và lưới đã học.",
        ],
        [
            "Scaler + STING chỉ fit ≤2023",
            "Δmean=0, Δscale=0 (khớp JSON ≤2023)",
            "Chống rò rỉ: năm 2024 chỉ transform/predict; fit thêm 2024 đổi mean (Δmean=0,011456) "
            "và không khớp tham số đóng băng.",
        ],
        [
            "Pseudo-label ≠ bán giám sát",
            "Nhãn vùng dày (1) / ngoại vi (0) do STING",
            "Nhãn là nhãn cụm do mô hình sinh, không phải nhãn khảo sát và không phải bài toán "
            "bán giám sát (học từ tập nhãn + tập không nhãn song song); mục 5.6 chỉ đối chứng độ "
            "khớp với nhãn lưới.",
        ],
        [
            "Chọn classifier theo macro-F1 CV",
            "Holdout 2023→2024: lớp 0 = 11, lớp 1 = 48 tỉnh",
            "Mất cân lớp mạnh trên một năm giữ — accuracy dễ theo đa số; macro-F1 cân hai lớp khi "
            "so sánh classifier học phần (không dùng holdout để chọn model).",
        ],
    ],
    widths=[3.6, 4.4, 7.0],
    caption=tbl_caption(
        "Quyết định tiền xử lý, chống rò rỉ và giới hạn pseudo-label / đánh giá"
    ),
)


h1("CHƯƠNG 4. PHƯƠNG PHÁP")
h2("4.1. Cấu hình STING và quy trình chọn train-only")
body(f"Ứng viên cặp chỉ tiêu được giới hạn ở các cột qua audit thang đo: 28 cặp từ 8 sub-dim sạch × 8 cấu hình lưới được chọn ({SWEEP_CONFIG_TXT}) = 224 tổ hợp (không phải tích Descartes đầy đủ của mọi (n_levels, factor, min_count); d1–d6 bị loại khỏi sweep — thang 1–10 chưa chứng minh tương đương xuyên năm). Tiêu chí chọn đặt TRƯỚC khi nhìn năm 2024 và PHÂN RÃ THEO BÀI TOÁN: hồi quy chọn model bằng CV expanding origin 2017–2022 thuần train; cặp chỉ tiêu + tham số STING (cho cả STING.predict và nhãn phân loại) do sweep chọn bằng cách fit ≤ 2020 và chấm coverage trên “tương lai giả” 2021–2022 (kèm k, nhiễu, độ vững mc±1) — 2 năm này trùng 2 fold CV cuối của phân loại, nên CV score phân loại hơi lạc quan. Allowlist của sweep dùng cả kiến thức ngoại sinh về PAPI 2021: sd_5_1/5_3/5_4 bị loại vì bước nhảy 2021 nằm ngoài giai đoạn train, heuristic train-only không tự bắt được. Hàm điểm = coverage − 0.5·noise − 0.15·largest − 0.02·|k−3| + 0.03·stable là heuristic chỉnh tay, không có dẫn xuất; bảo đảm chính nằm ở bộ lọc cứng (k ∈ [2,6], noise ≤ 25%, cụm lớn nhất ≤ 85%, coverage ≥ 75%) — cấu hình thoái hóa k=1 đạt điểm 0.84 cao hơn winner 0.6213 và chỉ bị chặn bởi bộ lọc này; margin top-1/top-2 = 0.018, nhỏ hơn một thành phần điểm đơn lẻ; stable_mc_pm1 = false của cấu hình thắng nhận 0 điểm thưởng độ ổn định nhưng không có ứng viên stable nào qua lọc, nên không dùng làm gate. Kết quả đóng băng vào models/predict_config.json: cặp sd_4_2 (4.2 Kiểm soát tham nhũng trong cung ứng dịch vụ công) × sd_6_1 (6.1 Y tế công lập); STING(L=3, factor=4, min_count=5, cluster level=2, connectivity=1); coverage 2021–2022 = 0.851. Cấu hình lưới dùng dữ liệu đến 2023. Khi đặt điểm PAPI đã quan sát năm 2024 lên lưới, tỷ lệ nằm trong ô dày là 79%, phân bố {{ngoài vùng dày: 13, cụm 2: 48}}.")
h2("4.2. Kiểm thử")
body(f"Bộ test STING trong tests/test_sting.py (pytest; {SUITE_OK}; coverage được đo bằng pytest --cov tại checkpoint kiểm tra): thống kê ô khớp numpy; phục hồi 2 Gaussian blobs với gate ARI ≥ 0.9; biên, 1 điểm, ô rỗng; predict trước cluster và sau refit chưa cluster → RuntimeError; out-of-support → −1; save/load khôi phục chính xác nhãn. Notebook cuối kỳ trực tiếp kiểm chứng synthetic, tái lập nhãn từ lưới cố định và tính lại dự báo, sai số từng chỉ tiêu cùng độ đúng theo vùng.")
h2("4.3. Baselines")
bullets([
    ("k-means.", "k ∈ {2, 3, 4, 5}; n_init=10; seed=42. Ép mọi điểm vào cụm (không có nhiễu)."),
    ("DBSCAN.", "eps ∈ {0.2, 0.4, 0.6, 0.8, 1.0}; min_samples=5; metric n/a khi <2 cụm."),
    ("Metrics.", "Silhouette/DB/CH trên điểm thuộc cụm; STING tách noise; báo cáo noise_ratio riêng; khi k<2 → n/a."),
    ("ARI.", "Adjusted Rand Index với frozen STING (nhãn gộp)."),
])
h2("4.4. Robustness đa chỉ tiêu (điều kiện đặt trước)")
bullets([
    ("Nhánh A — PCA.", "Chuẩn hóa d1–d6 trong từng năm rồi gộp để lấy hai thành phần chính. Trên hai thành phần này, STING dùng 3 mức, hệ số chia 3, ngưỡng 5 điểm và phân cụm ở mức 2 theo các ô chung cạnh. Mốc đánh giá là ít nhất 2 cụm và tỷ lệ nhiễu tối đa 50%. Hai thành phần giữ 63,2% phương sai và cấu hình này cho một cụm."),
    ("Nhánh B — 8 chiều (OFAT).", f"2018–2024 (n={N8}), trong-năm z; cấu hình gốc STING(L=3, f=2, mc=10, lv=1) + 3 nhánh OFAT đổi đúng MỘT tham số mỗi lần (f=3; mc=2; lv=2). Quy tắc chấp nhận giữ nguyên cho mọi nhánh: k≥2 & noise ≤ 50% → “đạt ngưỡng k/nhiễu”, nếu không → “không đạt ngưỡng”; silhouette/db/ch tính tại từng nhánh (k<2 → n/a). Kết quả ở mục 5.4."),
])
h2("4.5. Dự báo điểm PAPI và đối chiếu trên lưới STING")
bullets([
    ("Ghép cặp.", "Tám chỉ tiêu ở năm t là đầu vào. Hai đích là 4.2 và 6.1 ở t+1. Ghép các năm liền nhau theo mã tỉnh, dùng cặp đủ cả hai đích."),
    ("Chọn mô hình.", "Thử giữ điểm năm trước, Ridge alpha 1, Random Forest 96 cây (sâu tối đa 6, ít nhất 5 mẫu mỗi lá) và trung bình 50/50 của hai mô hình. Chọn riêng từng chỉ tiêu theo MAE trung bình của sáu lượt kiểm định mở rộng. Tại mỗi mốc 2017–2022, năm đích huấn luyện cuối bằng hoặc sớm hơn mốc xuất phát [13]."),
    ("Đối chiếu.", "Từ thông tin đến 2023, tạo điểm dự báo cho 2024. Sau đó ghép với điểm đã quan sát để tính sai số. Cả dự báo và quan sát được đưa qua bộ chuẩn hóa và lưới STING dựng đến cuối 2023."),
    ("Độ nhạy theo sai số.", "Giữ các cặp sai số 4.2 và 6.1 ngoài lượt kiểm định 2018–2023. Cộng từng cặp vào hai dự báo của một tỉnh rồi đếm tỷ lệ kịch bản ngoài vùng dày."),
    ("Thí nghiệm phân loại học phần.", "Mục 5.6 dùng nhãn do lưới STING tạo để đối chiếu một số mô hình phân loại. Đó là thí nghiệm riêng với đích là nhãn lưới."),
])


h1("CHƯƠNG 5. KẾT QUẢ")
h2("5.1. Kiểm chứng thuật toán trên dữ liệu giả lập")
body("Trên ví dụ 240 điểm từ hai nhóm Gauss, cài đặt thu được 2 cụm, ARI 0,950 và 2,5% nhiễu (Hình 1). Kết quả kiểm chứng hành vi trên ví dụ này; các kiểm tra thống kê ô, biên lưới và lưu/nạp mô hình được đánh giá riêng bằng bộ kiểm thử.")
figure("00_synthetic_sting.png", "Demo STING trên dữ liệu giả lập — blobs 2 cụm (ARI = 0.950)", 11)

h2("5.2. STING theo từng năm (fit riêng từng năm)")
body("Với cấu hình L=2, factor=3, min_count=3 và phân cụm ở mức 1, các năm trong Bảng 4 đều cho một cụm. Đây là kết quả của hai chỉ tiêu dưới cấu hình đang xét, không chứng minh toàn bộ PAPI đồng nhất. Hình 2 minh họa rằng thay đổi cấu hình trên cùng dữ liệu năm 2023 có thể cho số cụm khác.")
table(["Năm", "n", "k", "noise", "Kích thước cụm (giảm dần)"], PER_YEAR_TABLE,
      widths=[1.6, 1.6, 1.2, 1.6, 6.0],
      caption=tbl_caption(
          "STING theo từng năm (lưới L=2 f=3 mc=3, within-year z) — sinh từ results/per_year.csv"
      ))
figure("sting_first_real.png", "Hai cấu hình lưới và ngưỡng số điểm trên PAPI năm 2023", 15.5)

h2("5.3. Đối chứng STING, K-means và DBSCAN trên dữ liệu 2011–2023")
body("Phân tích chính dùng 808 quan sát đủ hai chỉ tiêu sd_4_2 và sd_6_1 giai đoạn 2011–2023, chuẩn hóa bằng thống kê của chính giai đoạn này. STING cho 3 cụm với kích thước 629, 16 và 5 điểm, cùng 19,6% nhiễu. Cụm lớn chứa 629/650 điểm đã vào cụm, tương đương 96,8%. Hai cụm nhỏ chỉ có điểm thuộc giai đoạn 2011–2018. Mục 5.5 trình bày kết quả chuyển trạng thái theo thời gian.")
comparison_rows = []
for metric in CLUSTER_METRICS:
    if metric["scope"] == "pooled 2011-2023":
        method = metric["method"].replace("STING (frozen)", "STING").replace("k-means", "K-means")
        comparison_rows.append([
            method, metric["k"], _pct(metric["noise_ratio"]).replace(".", ","),
            _f3(metric["silhouette"]).replace(".", ","),
            _f3(metric["davies_bouldin"]).replace(".", ","),
            _f3(metric["ari_vs_sting"]).replace(".", ",") if metric["ari_vs_sting"] else "—",
        ])
table(["Phương pháp", "Số cụm", "Nhiễu", "Silhouette", "Davies–Bouldin", "ARI với STING"],
      comparison_rows, widths=[4.1, 1.7, 1.8, 2.4, 3.1, 3.0],
      caption=tbl_caption("So sánh phân hoạch trên dữ liệu PAPI 2011–2023"))
body("K-means với k = 2 có silhouette 0,445 trên 808 điểm. STING được chấm trên 650 điểm thuộc cụm và DBSCAN (eps = 0,2) trên 693 điểm. Để đối chiếu cùng mẫu số, notebook giữ nguyên các nhãn đã học và tính lại silhouette trên 631 điểm thuộc cụm của cả STING lẫn DBSCAN. Các giá trị lần lượt là 0,366 cho STING, 0,457 cho K-means và 0,258 cho DBSCAN. Tập giao chỉ đại diện cho phần dữ liệu được cả hai phương pháp gán cụm.")
body("ARI STING–DBSCAN là 0,647 trên toàn bộ 808 quan sát, tính cả nhãn nhiễu, và 0,431 trên tập giao 631 quan sát. Hai số đo mức đồng thuận của phân hoạch trong từng phạm vi mẫu.")

h2("5.4. Robustness đa chỉ tiêu — ablation OFAT ở chiều cao")
body(f"PCA d1–d6 (trong-năm z, n={R_PCA['n']}): 2 thành phần đầu giữ {_pct(R_PCA['explained_var_total'])} phương sai; STING trên không gian PCA → k={R_PCA['k']}, nhiễu {_pct(R_PCA['noise_ratio'])}, ARI vs 2D = {R_PCA['ari_vs_2d']} — không nhận diện cấu trúc. Nhánh 8 chiều (2018–2024, n={N8}) đọc theo ablation OFAT — mỗi lần đổi đúng MỘT tham số so với cấu hình gốc (L=3 f=2 mc=10 lv=1): gốc → k={R_GOC['k']}, nhiễu {_pct(R_GOC['noise_ratio'])} (noise > 50% → không nhận diện); đổi f=3 → k={R_F3['k']}, nhiễu {_pct(R_F3['noise_ratio'])}; đổi lv=2 → k={R_LV2['k']}, nhiễu {_pct(R_LV2['noise_ratio'])}; đổi mc=2 → k={R_MC2['k']}, nhiễu {_pct(R_MC2['noise_ratio'])} — nhánh duy nhất đạt quy tắc chấp nhận cũ (k≥2 & noise ≤50%), CSV ghi verdict “có cấu trúc”, nhưng silhouette âm ({_f3(R_MC2['silhouette'])}) cho thấy hai cụm tách yếu, không phải cấu trúc mạnh. So sánh OFAT cho thấy sự nhạy với tham số trong các nhánh đã thử: lv=2 làm sập hoàn toàn (toàn nhiễu), f=3 khi giữ mc=10 mất gần hết điểm; riêng mc=2 chứng tỏ nhánh 8 chiều không trống rỗng theo ngưỡng k/noise — dù không tách mạnh.")
_rob_rows = []
for _r in ROBUSTNESS:
    _branch = _r["branch"]
    _ev = (_r["explained_var_total"] or "").strip()
    if _ev:
        _branch += f" (EV {float(_ev) * 100:.1f}%)"
    _sil = (_r["silhouette"] or "").strip()
    _verdict = _r["verdict"]
    if _verdict == "có cấu trúc" and _sil and float(_sil) < 0:
        _verdict = "đạt ngưỡng k/nhiễu; silhouette âm, tách yếu"
    _rob_rows.append([_branch, _r["n"], _r["k"], _pct(_r["noise_ratio"]),
                      "n/a" if _sil == "" else _f3(_r["silhouette"]), _verdict])
table(["Nhánh", "n", "k", "noise", "Silh.", "Kết luận"], _rob_rows,
      widths=[6.2, 1.2, 0.9, 1.5, 1.5, 4.2],
      caption=tbl_caption(
          "Robustness đa chỉ tiêu — PCA d1–d6 và ablation OFAT 8 chiều 2018–2024 "
          "(đổi một tham số mỗi lần so với gốc; nguồn: results/robustness.csv)"
      ))

h2("5.5. Dự báo hai chỉ tiêu năm 2024 và đối chiếu vùng")
body(f"Huấn luyện cuối dùng {FORECAST['train_pairs']} cặp lịch sử hoàn chỉnh có năm đích đến 2023. "
     f"Trong {FORECAST['forecast_count']} tỉnh có đủ tám đầu vào năm 2023, "
     f"{FORECAST['comparable_count']} tỉnh có cả hai điểm PAPI 2024 để đối chiếu. "
     "Hai chỉ tiêu đều chọn Ridge bằng MAE trung bình trong sáu lượt kiểm định lịch sử. "
     "Bảng so sánh dùng đúng cùng tập tỉnh cho Ridge và cách giữ nguyên điểm năm 2023. "
     "Đánh giá 2024 là hồi cứu trên một năm đã có số liệu.")
figure("papi_forecast_values.png", "Dự báo và quan sát hai chỉ tiêu PAPI năm 2024", 15.0)
score_rows = []
for code, name in (("sd_4_2", "4.2 Kiểm soát tham nhũng"), ("sd_6_1", "6.1 Y tế công lập")):
    for method, model_name, cv_key in (
        ("forecast", FORECAST["selected"][code], FORECAST["selected_method"][code]),
        ("carry", "Giữ điểm 2023", "carry"),
    ):
        score = FORECAST_SCORES[code, method]
        score_rows.append([name, model_name, _dec(FORECAST["cv_mae"][code][cv_key]), _dec(score["mae"]),
                           _dec(score["rmse"]), _dec(score["bias"])])
forecast_table = table(["Chỉ tiêu", "Cách dự báo", "MAE kiểm định", "MAE 2024", "RMSE 2024", "Độ lệch TB"],
                       score_rows, widths=[3.9, 2.65, 2.45, 2.1, 2.25, 2.5],
                       caption=tbl_caption("Sai số dự báo trên cùng các tỉnh đủ hai điểm năm 2024"))
for row in forecast_table.rows:
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.keep_with_next = True
body("MAE là độ lệch tuyệt đối trung bình. RMSE đặt trọng số lớn hơn lên sai số lớn. "
     "Ridge có MAE thấp hơn cách giữ điểm 2023 ở hai chỉ tiêu. Với 4.2, "
     "RMSE tăng từ 0,0953 lên 0,0972 và độ lệch trung bình từ −0,0245 xuống −0,0581. "
     "Vì vậy, sai số tuyệt đối trung bình giảm đi cùng mức dự báo thấp hơn quan sát rõ hơn ở chỉ tiêu này.")
figure("papi_forecast_grid.png", "Điểm dự báo và điểm quan sát năm 2024 trên cùng lưới STING", 15.2)
body(f"Trong {FORECAST['comparable_count']} tỉnh của phép so sánh dự báo, "
     f"{FORECAST['actual_outside']} tỉnh có điểm quan sát ngoài vùng dày. "
     "Dự báo điểm đưa tất cả tỉnh trong mẫu này vào cụm lớn. "
     f"Tỷ lệ trùng nhãn là {_pct(FORECAST_ZONES['forecast']['exact_label_agreement'])}, "
     "bằng mốc luôn gán cụm lớn, với độ đúng cân bằng 0,50. Dự báo điểm nhận ra 0/11 tỉnh ngoài vùng dày, "
     "còn giữ nguyên điểm 2023 nhận ra 4/11 và gán ngoài nhầm 5 tỉnh. "
     "Tỷ lệ trùng nhãn cao chủ yếu do cụm lớn chiếm đa số.")
body(f"Với mỗi tỉnh, nhóm thử {FORECAST['scenario_count']} cặp sai số lịch sử. "
     f"Tỷ lệ kịch bản ngoài vùng dày cho AUC xếp hạng {_dec(FORECAST['scenario_auc'], 3)} "
     "khi đối chiếu 59 tỉnh năm 2024. Đây là khảo sát độ nhạy với sai số gộp từ các năm trước. "
     "Để diễn giải như xác suất dự báo cần kiểm tra hiệu chỉnh trên các mốc độc lập.")
body("Đối chiếu các điểm đã quan sát cho thấy 48/61 tỉnh vào cụm lớn. Hai tỉnh thiếu chỉ tiêu "
     "được loại khỏi phép gán, còn 13 tỉnh đủ điểm nằm trong ô có dưới 5 quan sát tham chiếu. "
     "Quảng Ninh và Bình Dương nằm trong 13 tỉnh này và thiếu dữ liệu năm 2023. "
     "Bảng chuyển trạng thái còn 59 tỉnh, gồm 48 trong vùng dày và 11 ngoài vùng. "
     "Tập mã tỉnh này trùng với mẫu đối chiếu dự báo của năm 2024. "
     "Lạng Sơn từ ngoài vùng dày năm 2023 vào cụm lớn năm 2024 trên cùng lưới.")
table(["Năm 2023 / năm 2024", "Nhiễu (−1)", "Cụm lớn (2)", "Tổng"], [
    ["Nhiễu (−1)", "4", "5", "9"],
    ["Cụm lớn (2)", "7", "43", "50"],
    ["Tổng", "11", "48", "59"],
], widths=[6.4, 2.4, 2.4, 2.4],
      caption=tbl_caption("Chuyển trạng thái của 59 tỉnh đủ dữ liệu trong cả hai năm 2023 và 2024"))

h2("5.6. So sánh các bộ phân loại học trong môn")
body(
    "Bổ sung các baseline theo nội dung học phần (Naive Bayes, k-NN, SVM tuyến tính/RBF, "
    "Decision Tree, Random Forest) trên cùng pseudo-label STING và cùng giao thức expanding "
    "origin 2017–2022; chọn siêu tham số theo macro-F1 CV; holdout duy nhất 2023→2024 không "
    "tham gia chọn model (nguồn: results/course_supervised_baselines.csv). Nhãn do STING sinh "
    "không phải ground truth khảo sát; một năm giữ lại không chứng minh mô hình nào vượt trội "
    "tổng quát — bảng chỉ mô tả độ khớp với nhãn lưới trên holdout này."
)
table(
    ["Model", "Metric CV", "value_cv", "Holdout acc", "Holdout macro-F1"],
    COURSE_BASELINES_TABLE,
    widths=[3.6, 4.2, 1.6, 2.0, 2.6],
    caption=tbl_caption(
        "So sánh classifier học phần — nguồn: results/course_supervised_baselines.csv"
    ),
)
_course_cm_no = figure(
    "course_confusion_matrix.png",
    "Ma trận nhầm lẫn holdout 2023→2024 — các classifier học phần (hàng = nhãn STING thật, "
    "cột = dự báo; nguồn: results/figs/course_confusion_matrix.png)",
    14.0,
)
body(
    f"Hình {_course_cm_no} tổng hợp ma trận nhầm lẫn trên cùng holdout; đọc cùng Bảng {TABLE_NO[0]} — "
    "không suy luận vượt trội giữa các thuật toán ngoài phạm vi một năm và nhãn pseudo."
)

h2("5.7. Dịch chuyển cụm qua thời gian và bản đồ")
body("Hình 6 vẽ nhãn lưới toàn cục cho mọi tỉnh-năm (xám = nhiễu, trắng = thiếu chỉ tiêu); Hình 7 — bản đồ centroid 2024, các tỉnh nhận nhãn nhiễu nằm ở nhiều vùng, không gom một vùng địa lý.")
figure("evolution.png", "Dịch chuyển cụm STING 2011–2024 (lưới toàn cục; xám = nhiễu; trắng = thiếu dữ liệu)", 10.5)
figure("map_2024.png", "Bản đồ centroid tô màu theo cụm — 2024 (nhãn chú thích các tỉnh nhiễu)", 10.0)

h2("5.8. Kiểm thử & tái lập")
bullets([
    ("Unit tests.", "python -m pytest tests -q → toàn bộ test xanh."),
    ("Dữ liệu.", "python scripts/data/check_data.py → PASS (882×41) + danh sách audit thang đo."),
    ("Tái lập.", "Mọi notebook execute sạch; mọi số liệu trong báo cáo truy được về results/*.csv; seeds cố định; PROVENANCE cho mọi nguồn."),
    ("Nguồn ngoài.", "python scripts/analysis/external_validation.py → results/external_validation.md + results/external_validation.csv + 4 hình external_* (từ data/processed/external_*.csv; provenance: data/processed/external_provenance.md, data/raw/*/PROVENANCE.md)."),
])


h1("CHƯƠNG 6. THẢO LUẬN VÀ HẠN CHẾ")
h2("6.1. Giới hạn khi diễn giải cụm chiếm ưu thế")
body("Kết quả chính có một cụm chiếm ưu thế và hai cụm nhỏ trên hai chỉ tiêu. Điều này phụ thuộc tập đặc trưng, phạm vi năm, độ phân giải và ngưỡng số điểm. Kết quả một cụm của cấu hình theo năm chỉ mô tả hành vi của cấu hình đó; Hình 2 cho thấy một lựa chọn lưới khác tạo ba cụm trên dữ liệu 2023. Nhãn lưới không đủ để kết luận các tỉnh tương đồng trên toàn bộ 37 chỉ tiêu, hoặc để chia địa phương thành nhóm phát triển cao và thấp.")
h2("6.2. Bài học từ gãy thang đo")
body("Trong thử nghiệm ban đầu, nhóm đã xem xét cặp sd_5_4 và sd_6_2. Workbook cho thấy sd_5_4 đổi thang từ 0,25–2,5 sang 0,33–3,33 tại năm 2021. Bước nhảy trung bình quan sát là +0,576, trong khi nhân trung bình năm 2020 với hệ số 1,333 sẽ tăng khoảng +0,632. Hai giá trị cùng hướng nhưng không tách được ảnh hưởng của đổi thang và biến động khảo sát. Vì vậy, nhóm không dùng cặp này để kết luận về khác biệt quản trị. Khi gộp nhiều phiên bản dữ liệu cần kiểm tra cả tính tương thích của thang đo và khả năng cụm phản ánh giai đoạn thu thập.")
h2("6.3. Cách đọc chỉ số và giới hạn của lưới song song trục")
bullets([
    ("Chỉ số hình học.", "Đọc silhouette cùng số quan sát được chấm và tỷ lệ nhiễu. K-means gán mọi điểm vào một trong k cụm đã định trước."),
    ("Đồng thuận phân hoạch.", "ARI STING–DBSCAN thay đổi khi loại các điểm nhiễu khỏi mẫu. Kết quả phụ thuộc thiết lập eps và mẫu dùng để đối chiếu."),
    ("Cụm chiếm ưu thế.", "Một cụm giữ 96,8% số điểm đã vào cụm. Hai cụm còn lại nhỏ và chỉ xuất hiện ở phần đầu chuỗi thời gian."),
    ("Lưới song song trục.", "Biên các ô thay đổi theo tập đặc trưng và độ phân giải. Silhouette dùng khoảng cách Euclid, còn STING gom theo liên thông của ô lưới."),
])
h2("6.4. Ảnh hưởng của cấu hình khi mở rộng số chiều")
body("Hai thành phần PCA giữ 63,2% phương sai và cấu hình STING đang xét cho một cụm. Trong nhánh 8 chiều, thay riêng mức lưới hoặc ngưỡng số điểm tạo các tỷ lệ nhiễu rất khác nhau; cấu hình min_count=2 đạt ngưỡng số cụm và tỷ lệ nhiễu đã đặt nhưng silhouette âm. Các kết quả cho thấy sự phụ thuộc vào cấu hình trong phạm vi thử nghiệm. Chúng không bác bỏ mọi khả năng có cấu trúc ở chiều cao, vì chỉ khảo sát một số cấu hình và PCA có thể bỏ thông tin ngoài hai thành phần đầu.")
h2("6.5. Kiểm chứng bên ngoài độc lập")
body("Robustness nội tại (mục 5.4) là âm tính; câu hỏi còn lại: cấu trúc học không giám sát có tương ứng với một thước đo chưa từng dùng khi học — kiểm chứng bên ngoài độc lập (liên hệ giữa nhóm, không phải nhân quả) — hay không? Nhóm đối chiếu nhãn cụm STING (model chốt, results/predict_all_years.csv) với các nguồn ngoài ở mục 3.1: không đưa vào feature, không nội suy ô trống; mọi thống kê tính lại trực tiếp từ CSV trong scripts/analysis/external_validation.py (số liệu đầy đủ: results/external_validation.md).")
body("PCI [9] là nguồn khảo sát doanh nghiệp dùng để đối chiếu mô tả với nhãn PAPI. Có 756 quan sát tỉnh–năm 2011–2022, trong đó 747 quan sát có nhãn STING. Bảng 10 gồm 149 điểm nhiễu, 5 điểm cụm 0, 16 điểm cụm 1 và 577 điểm cụm 2. ANOVA cho F(3,743)=9,04, p≈6,9×10⁻⁶; Kruskal–Wallis cho H=31,78, p≈5,8×10⁻⁷; eta²=0,035. Các phép thử gộp chưa hiệu chỉnh sự phụ thuộc giữa các lần quan sát cùng tỉnh và giữa các năm, nên p-value chỉ mang tính tham khảo. Hai cụm nhỏ có ít điểm; kết quả không chứng minh quan hệ nhân quả hoặc xác nhận nhãn cụm là nhóm xã hội thực. Dữ liệu PCI Top-30 năm 2023–2024 được đọc riêng vì có chọn mẫu.")
table(["Nhãn nhóm", "n", "PCI trung bình", "Trung vị", "Độ lệch chuẩn"], [
    ["nhiễu (−1)", "149", "59.80", "59.16", "5.04"],
    ["cụm 0", "5", "59.00", "58.47", "1.06"],
    ["cụm 1", "16", "58.78", "58.19", "3.80"],
    ["cụm 2", "577", "61.66", "62.16", "4.29"],
], widths=[3.4, 1.6, 3.6, 2.6, 3.2],
      caption=tbl_caption(
          "Kiểm chứng bên ngoài — PCI theo nhãn cụm STING (2011–2022, n=747); "
          "ANOVA F(3,743)=9.04, p=6.9e-06; Kruskal–Wallis H=31.78, p=5.8e-07"
      ))
figure("external_pci_by_cluster.png", "PCI theo nhãn cụm STING 2011–2022 — boxplot theo nhóm (nguồn: PCI VCCI–USAID; kết quả: results/external_validation.md)", 13.5)
body("Mật độ cơ sở y tế 2020 [11]: 423 điểm OD Mekong rơi vào 63 tỉnh (point-in-polygon), chuẩn hóa theo dân số GSO — theo quy mô nhóm: nhiễu 0.0026 cơ sở/1.000 dân (16 cơ sở/6,19 triệu người) so với cụm 2: 0.0045 (407 cơ sở/91,39 triệu); trung vị theo tỉnh 0.00075 so với 0.0022. 10 tỉnh không có điểm trong nguồn; số 0 không chứng minh thực tế không có cơ sở y tế; snapshot một năm và đếm số điểm chứ không phải số giường → chỉ dùng làm external check, không đưa vào feature.")
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
    tbl_caption(
        "Nghèo GSO (%) theo nhãn cụm STING — cửa sổ giao 2012–2024 "
    f"(n={POV['n_join']}); gộp thô: Kruskal–Wallis H = {_note_val(POV_KW_RAW, 'H = ')}, "
    f"p = {_note_val(POV_KW_RAW, 'p = ')} — KHÔNG đáng kể; đã-trừ-median-năm: "
    f"H = {_note_val(POV_KW_DM, 'H = ')}, p = {_note_val(POV_KW_DM, 'p = ')} — đáng kể. "
    "Hai kết quả đọc CÙNG nhau"
    )))
_pov_fig_no = figure("external_poverty_by_cluster.png",
                     "Tỷ lệ hộ nghèo GSO theo cụm STING — cửa sổ giao 2012–2024: "
                     "boxplot gộp (trên) và median theo năm từng cụm (dưới) (nguồn: GSO pxweb "
                     "V14.47 + NGTK 2020/2021 điền 2017–2019; kết quả: results/poverty_validation.md)", 13.5)
body(f"Đọc kết quả CÙNG nhau: gộp thô KHÔNG đáng kể (Kruskal–Wallis H = {_note_val(POV_KW_RAW, 'H = ')}, p = {_note_val(POV_KW_RAW, 'p = ')}; {POV_ANOVA_RAW['group']} = {_note_val(POV_ANOVA_RAW['note'], 'F = ')}, p = {_note_val(POV_ANOVA_RAW['note'], 'p = ')}; eta² = {_note_eta(_pov_note('poverty_pooled_raw', 'eta squared'))}) vì test gộp nhiễm hiệu ứng năm — median nghèo toàn panel giảm sâu xuyên giai đoạn và tỷ trọng cụm trôi theo năm (hàng dưới của Hình {_pov_fig_no}); đã-trừ-median-trong-năm đáng kể ở mức yếu (H = {_note_val(POV_KW_DM, 'H = ')}, p = {_note_val(POV_KW_DM, 'p = ')}; {POV_ANOVA_DM['group']} = {_note_val(POV_ANOVA_DM['note'], 'F = ')}, p = {_note_val(POV_ANOVA_DM['note'], 'p = ')}; eta² = {_note_eta(_pov_note('poverty_pooled_demeaned', 'eta squared'))}). Cặp đối chiếu có nhiều quan sát hơn là nhiễu với cụm 2 (cụm 0 n={_pov_group_n('cụm 0')}, cụm 1 n={_pov_group_n('cụm 1')} quá nhỏ để tự kết luận) không khác biệt ở mức gộp (Mann–Whitney U = {_note_val(POV_MW_RAW['note'], 'U = ')}, p = {_note_val(POV_MW_RAW['note'], 'p = ')}) và vẫn không khác biệt sau khi tách năm (U = {_note_val(POV_MW_DM['note'], 'U = ')}, p = {_note_val(POV_MW_DM['note'], 'p = ')}). Kết luận trung thực: ở mức gộp KHÔNG thấy khác biệt nghèo có ý nghĩa giữa các nhóm; tín hiệu chỉ xuất hiện sau khi tách hiệu ứng năm và yếu hơn nhiều so với kiểm định chính PCI (eta² {_note_eta(_pov_note('poverty_pooled_demeaned', 'eta squared'))} so với 0.035) — nghèo GSO đọc như kiểm chứng bổ trợ, không thay thế kiểm định chính và không chứng minh nhân quả. Tái lập: python scripts/analysis/poverty_validation.py.")
body("Tổng hợp, các nguồn ngoài cung cấp đối chiếu mô tả bổ sung cho nhãn STING. Cỡ nhóm chênh lệch, hiệu ứng năm và sự phụ thuộc giữa các quan sát giới hạn việc suy luận. Những kết quả này không xác nhận toàn bộ PAPI đồng nhất, không biến nhãn mô hình thành ground truth và không chứng minh quan hệ nhân quả.")
body("Các kiểm định gộp với nguồn ngoài chưa hiệu chỉnh đầy đủ quan sát lặp theo tỉnh và năm. Các p-value được trình bày để đối chiếu mô tả trong mẫu hiện có, không phải bằng chứng xác nhận nhãn cụm hay quan hệ nhân quả.")
h2("6.6. Các hạn chế còn lại")
bullets([
    ("Một mốc hồi cứu cuối (2024).", "Dự báo điểm nghiêng về vùng dày. Kết quả xếp hạng từ kịch bản sai số dùng cùng mẫu 2024, cần đối chiếu trên thêm các mốc độc lập."),
    ("Cỡ mẫu per-year nhỏ.", "61–63 điểm/năm — nhiễu cao ở lưới mịn; cấu hình per-year bị giới hạn ở lưới thô."),
    ("Thang đo 1–10 che giấu phương sai thực.", "theo thời gian, d6 tăng 7.0→7.6 (2021) khả năng là thay đổi phương pháp khảo sát, không chỉ cải thiện; cần thận trọng khi diễn giải xu hướng."),
    ("Bản đồ chỉ có centroid.", "chưa dùng ranh giới GeoJSON (chỉ có scatter); bản đồ choropleth đầy đủ không nằm trong phạm vi báo cáo này."),
    ("Nhãn DBSCAN n/a khi 1 cụm.", "một số cấu hình DBSCAN cho metric n/a — ghi rõ trong bảng, không giấu."),
    ("Nguồn ngoài không đồng đều.", "PCI 2023–2024 chỉ Top-30 (chọn mẫu — tách khỏi lưới đủ 63 tỉnh); GRDP chỉ 2018–2024 (2024 = Sơ bộ); rác thải GSO trống hoàn toàn 2018 (305/882 ô); WDI chuỗi không đều (giường bệnh dừng 2017, chi y tế thiếu 2024) — mọi thống kê external khai báo số ô chạy/tổng ô và không nội suy."),
    ("Mật độ y tế snapshot 2020.", "một năm duy nhất, đếm số điểm không phải số giường; 10 tỉnh không có điểm trong nguồn; độ phủ nguồn hạn chế nên không coi đó là không có cơ sở y tế trên thực tế."),
    ("Giới hạn kiểm định gộp.", "Các nguồn ngoài chỉ hỗ trợ đối chiếu mô tả. Quan sát lặp theo tỉnh và năm chưa được hiệu chỉnh trong các phép thử gộp; cỡ hai cụm nhỏ hạn chế và eta²=0,035, nên không diễn giải p-value thành bằng chứng nhân quả hay xác nhận cấu trúc xã hội."),
])
h2("6.7. Hướng phát triển")
bullets([
    ("Chuẩn hóa theo hạng.", "Khảo sát việc đưa chỉ tiêu về thứ hạng trong từng năm để giảm nhạy với thang tuyệt đối; vẫn phải kiểm tra nội dung chỉ tiêu và thiết kế khảo sát có tương thích giữa các năm hay không."),
    ("Feature trajectory.", "mỗi tỉnh = vector quỹ đạo 2011–2024 (đặc trưng theo thời gian) — phân cụm quỹ đạo, không phân cụm từng mốc."),
    ("Nhiều holdout.", "backtest cuốn chiếu 2015→2024 — độ tin cậy dự báo cao hơn."),
    ("Spatial.", "thêm tự tương quan không gian (láng giềng) — GeoJSON CC-BY-SA 4.0 đã có."),
    ("Định tính.", "phỏng vấn sâu 3–5 tỉnh ngoại vi để kiểm tra giả thuyết “hai tốc độ” quản trị."),
])


h1("CHƯƠNG 7. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN")
h2("7.1. Kết luận")
bullets([
    ("Kiểm tra cài đặt STING.", f"ARI 0.950 trên bộ dữ liệu giả lập. Các kiểm thử trong `tests/test_sting.py` đạt ({SUITE_OK}). Truy vấn vùng có chi phí O(M·d) với M ô có dữ liệu và d chiều."),
    ("Kết quả phụ thuộc phạm vi phân tích.", "Trên hai chỉ tiêu và cấu hình chính, một cụm lớn chiếm ưu thế. Các thử nghiệm mở rộng cho kết quả nhạy với cấu hình và chưa có bằng chứng phân tách mạnh trong phạm vi đã thử; không suy ra toàn bộ PAPI hay các địa phương đồng nhất."),
    ("Dự báo hai chỉ tiêu và đối chiếu vùng.", "Ridge có MAE thấp hơn giữ nguyên điểm 2023 ở cả hai chỉ tiêu trên mẫu 59 tỉnh. Dự báo điểm đưa cả 59 vào cụm lớn và bỏ sót 11 tỉnh có quan sát ngoài vùng dày. So sánh điểm liên tục và so sánh vùng cho hai loại kết quả cần diễn giải riêng."),
    ("Rà soát thang đo.", "Bước sàng lọc đánh dấu 23/37 chỉ tiêu để đối chiếu với workbook. Việc đối chiếu giúp chọn đầu vào và giới hạn cách diễn giải các thay đổi theo thời gian."),
])
h2("7.2. Hướng phát triển")
body("Xem 6.7 — trọng tâm: (1) rank-normalization xuyên năm; (2) quỹ đạo tỉnh; (3) backtest cuốn chiếu; (4) phân cụm có ràng buộc không gian; (5) nghiên cứu định tính bổ trợ. Ngoài ra, bản đồ choropleth đầy đủ (plotly + GeoJSON) và dashboard tương tác là bước trực quan tiếp theo.")
h2("7.3. Lời cuối")
body("Đồ án không “tạo ra” một cấu trúc cụm đẹp nếu dữ liệu không có nó; đồ án cung cấp: (i) một biến thể grid-based dựa trên STING, đã kiểm thử trong phạm vi cài đặt công bố; (ii) quy trình dữ liệu có audit thang đo và lựa chọn không dùng holdout 2024; (iii) báo cáo trung thực cả robustness mở rộng chiều (PCA âm tính; nhánh 8 chiều OFAT — mc=2 vượt ngưỡng k/noise với silhouette âm, các nhánh còn lại không nhận diện) lẫn kết quả dương tính. Kết quả không chứng minh cấu trúc xã hội hay quan hệ nhân quả.")
h2("7.4. Khai báo sử dụng công cụ hỗ trợ")
body("Nhóm sử dụng trợ lý AI lập trình để hỗ trợ xây dựng một số script dữ liệu và trực quan, gỡ lỗi, kiểm tra kết quả và chạy thử kỹ thuật. Nhật ký rehearsal_log.md mục A ghi rõ lượt chạy thử kỹ thuật cá nhân do AI thực hiện. Hai thành viên chịu trách nhiệm rà soát nguồn, chạy lại kết quả và giải thích phương pháp, lựa chọn cấu hình cùng giới hạn của bài nộp. Việc chạy thử kỹ thuật không thay cho buổi luyện thuyết trình và hỏi đáp của nhóm.")


h1("PHỤ LỤC A — LỆNH TÁI LẬP & KIỂM TRA")
body("Mọi bước dưới đây chạy từ thư mục gốc repo và cho kết quả như cột kỳ vọng; môi trường đã kiểm chứng: Python 3.14.2, Windows 11, dependencies trong requirements.txt.")
table(["Lệnh", "Kỳ vọng"], [
    ["python scripts/data/build_panel.py", "data/processed/papi_panel_63_2011_2024.csv (882×41); log 2 định dạng nguồn"],
    ["python scripts/data/check_data.py", "PASS — ≥500 hàng, ≥10 cột số; in danh sách cờ audit thang đo (23/37 heuristic)"],
    ["python scripts/data/crosscheck_mendeley.py", "max |diff| = 0.0; ghi reports/crosscheck_mendeley.md"],
    ["python -m pytest tests -q", "toàn bộ test xanh"],
    ["python scripts/analysis/predict_sweep.py", "chọn cấu hình train-only; ghi models/predict_config.json + results/predict_config_search.csv"],
    ["python scripts/analysis/predict_demo.py", "Gán điểm PAPI đã quan sát vào lưới lịch sử. results/predict_summary.md"],
    ["python scripts/figures/forecast_papi_grid.py", "Dự báo hai chỉ tiêu và tạo bảng sai số, kết quả từng tỉnh và hình đối chiếu."],
    ["python scripts/supervised/predict_supervised.py", "Thí nghiệm học phần đơn chỉ tiêu 6.1 và phân loại theo nhãn lưới."],
    ["python scripts/analysis/run_analysis.py", "metrics.csv, per_year.csv, robustness.csv, evolution/map hình, analysis_summary.md"],
    ["python scripts/data/build_external_master.py", "data/processed/external_master_63_2011_2024.csv (882×59, mask tường minh) + results/external_master_summary.md"],
    ["python scripts/analysis/external_validation.py", "results/external_validation.md + results/external_validation.csv + 4 hình external_* (ANOVA/Kruskal PCI, y tế 2020, GRDP, WDI)"],
    ["python scripts/analysis/poverty_validation.py", "results/poverty_validation.md + results/poverty_validation.csv + results/figs/external_poverty_by_cluster.png (KW gộp thô & đã-trừ-median-năm; Mann–Whitney nhiễu vs cụm 2)"],
    ["python -m nbconvert --to notebook --execute --inplace notebooks/STING_PAPI_Demo_MoRong.ipynb", "execute sạch ~18s, 18 cells, 0 lỗi"],
    ["python -m nbconvert --to notebook --execute --inplace notebooks/Nhom15_CuoiKy_STING_PAPI.ipynb", f"execute sạch, {NB_CELLS} cells, {NB_IMGS} hình nhúng (đếm từ notebook đã execute)"],
    ["python scripts/deliverables/build_report.py", "reports/final_report.docx"],
], widths=[9.8, 6.0], caption=tbl_caption("Danh sách lệnh tái lập và kết quả kỳ vọng"))
body("Môi trường: jupyter/pytest/nbconvert không cài trên PATH — luôn dùng python -m pytest / python -m nbconvert. Dữ liệu gốc data/raw/ bất biến; panel tái tạo từ raw bằng build_panel.py; Mendeley đầy đủ tải theo DOI 10.17632/wbk42j9wc8.1 (chỉ commit 4 file nhỏ dùng trực tiếp).")










def _md_read(name):
    return (ROOT / "results" / name).read_text(encoding="utf-8")


def _md_rx(pattern, text):
    m = re.search(pattern, text, re.MULTILINE)
    if m is None:
        raise ValueError(f"Phụ lục B: không khớp pattern {pattern!r}")
    return m


def _md_between(text, start, end=None):
    i = text.index(start)
    j = text.index(end, i) if end is not None else len(text)
    return text[i:j]


def _md_rows(block):
    for ln in block.splitlines():
        ln = ln.strip()
        if ln.startswith("|") and ln.endswith("|") and "---" not in ln:
            yield [c.strip() for c in ln.strip("|").split("|")]


def _md_kw(sec):
    return _md_rx(r"\*\*Kruskal–Wallis\*\*: H = ([\d.]+), df = (\d+), "
                  r"p = ([\d.eE+-]+) \(n = (\d+);", sec)


def _md_medians(sec):
    return [{"cl": c[0], "n": c[2], "median": c[3]} for c in _md_rows(sec)
            if len(c) == 8 and c[0].lstrip("-").isdigit()]


def _grpm(med_list, cl):
    m = next(x for x in med_list if x["cl"] == cl)
    return f"{m['median']} (n = {m['n']})"



_A = _md_read("protocol_sensitivity.md")
_A3 = _md_between(_A, "## 3.", "## 4.")
_A4 = _md_between(_A, "## 4.", "## 5.")
_A5 = _md_between(_A, "## 5.", "## 6.")
_A6 = _md_between(_A, "## 6.", "## 7.")
_A7 = _md_between(_A, "## 7.", "## 8.")
_A8 = _md_between(_A, "## 8.", "## 9.")
_A_M = _md_rx(r"Khớp giá trị từng trường trên (\d+)/(\d+) dòng", _A3)
_A_MATCH = f"{_A_M.group(1)}/{_A_M.group(2)}"
_A_ORDER = _md_rx(r"Khớp cả THỨ TỰ (\d+) dòng sau sort như gốc: (True|False)", _A3)
_A_PASS = [{"feat": c[0], "cfg": c[1], "sizes": c[3], "score": c[8]}
           for c in _md_rows(_A3)
           if len(c) == 9 and c[0].startswith("sd_") and "+" in c[0]]
assert len(_A_PASS) == 4, "Phụ lục B: bảng 4 dòng pass bộ lọc cũ lệch định dạng"
_A_WINNER = next(r for r in _A_PASS if r["feat"] == "sd_4_2+sd_6_1")
_A_ZERO = _md_rx(r"pass bộ lọc sửa \((\d+)/(\d+)\)", _A4)
_A_MCS_MOD = _md_rx(r"## 4\. Bộ lọc SỬA — kết quả chính \(mcs = ([\d.]+)\)",
                    _A4).group(1)
_A_CONT = _md_rx(r"Tổ hợp gần đạt nhất \(trong nhóm đạt k/noise/coverage, "
                 r"(\d+)/(\d+) tổ hợp\): `([\w+]+)` \(([\d/]+)\) — min_share = "
                 r"([\d.]+) \(còn thiếu ([\d.]+) để đạt ([\d.]+)\), "
                 r"largest_sửa = (\d+\.\d+)", _A4)
_A_CONT_OLD = next(r["score"] for r in _A_PASS
                   if r["feat"] == _A_CONT.group(3) and r["cfg"] == _A_CONT.group(4))
_A_CONT_DELTA = _vn(f"{float(_A_CONT_OLD) - float(_A_WINNER['score']):.4f}")
_A_MCS = {c[0]: c[1] for c in _md_rows(_A7)
          if len(c) == 5 and re.fullmatch(r"0\.\d+", c[0])}
assert len(_A_MCS) == 3, "Phụ lục B: bảng độ nhạy mcs phải đủ 3 dòng"
_A_ONLY5 = _md_rx(r"chỉ (\d+)/(\d+) tổ hợp có largest_sửa ≤ ([\d.]+), và cả nhóm "
                  r"này có noise_train ([\d.]+[–-][\d.]+), coverage "
                  r"([\d.]+[–-][\d.]+)", _A7)
_A_TOP5R1 = next(c for c in _md_rows(_A5)
                 if len(c) == 13 and c[0] == "1" and c[1].startswith("sd_"))
_A_TOP1 = _md_rx(r"top-1 toàn bảng là \*\*([\w+]+)\*\* \(([\d/]+)\) với score_sửa "
                 r"([\d.]+)", _A6)
_A_FZ_LG = _md_rx(r"\| largest_sửa \(non-noise\) \| ([\d.]+) — vượt ngưỡng ([\d.]+) "
                  r"thêm ([\d.]+) \|", _A6)
_A_FZ_MS = _md_rx(r"\| min_share \(non-noise\) \| ([\d.]+) — thiếu ([\d.]+) so với "
                  r"mcs=([\d.]+) \|", _A6)
_A_FZ_SM = _md_rx(r"\| score_sửa của cấu hình đóng băng \| ([\d.]+) \|", _A6).group(1)
_A_SCORE_PUB = _md_rx(r"\| score công bố \(bộ lọc cũ\) \| ([\d.]+) \|",
                      _A6).group(1)
assert float(_A_SCORE_PUB) == float(_A_WINNER["score"]), \
    "Phụ lục B: score công bố ở mục 6 lệch dòng winner mục 3"
_A_GAP_MOD = _md_rx(r"score_sửa: top-1 toàn bảng \(không pass bộ lọc sửa\) − đóng băng "
                    r"\| ([\d.]+) \|", _A6).group(1)
_A_GAP_OLD = _md_rx(r"khoảng cách score \(công thức cũ\): top-1 − [\d.]+ \| ([\d.]+) \|",
                    _A6).group(1)
_A_ST_TOP = _md_rx(r"top-1 toàn bảng `([\w+]+)` \(([\d/]+)\) có stable_mc_pm1 = "
                   r"\*\*(True|False)\*\*", _A8)
_A_ST_CONT = _md_rx(r"`([\w+]+)` \(([\d/]+)\): stable_mc_pm1 = \*\*(True|False)\*\*",
                    _A8)


_B = _md_read("cluster_profile.md")
_B_PCI = _md_between(_B, "### 2.1)", "### 2.2)")
_B_POV = _md_between(_B, "### 2.2)", "### 2.3)")
_B_HEA = _md_between(_B, "### 2.3)", "### 2.4)")
_B_GRD = _md_between(_B, "### 2.4)", "### 2.5)")
_B_URB = _md_between(_B, "### 2.5)", "## 3)")
_B_BOOT = _md_between(_B, "## 3)", "## 4)")
_B_KW = {"pci": _md_kw(_B_PCI), "pov": _md_kw(_B_POV), "hea": _md_kw(_B_HEA),
         "grd": _md_kw(_B_GRD), "urb": _md_kw(_B_URB)}
_B_MED_PCI = _md_medians(_B_PCI)
_B_MED_POV = _md_medians(_B_POV)
_B_MED_GRD = _md_medians(_B_GRD)
assert len(_B_MED_PCI) == len(_B_MED_POV) == 4, \
    "Phụ lục B: bảng median PCI/nghèo phải đủ 4 nhóm"
assert len(_B_MED_GRD) == 3, "Phụ lục B: bảng median GRDP phải đủ 3 nhóm"
_B_SEED = _md_rx(r"seed \*\*(\d+)\*\* = `numpy\.random\.default_rng\(\d+\)`",
                 _B).group(1)
_B_NBOOT = _md_rx(r"\*\*Bootstrap\*\*: (\d+) lần resample CÓ hoàn lại "
                  r"\*\*theo TỈNH\*\*", _B).group(1)
_B_KEEP_ALL, _B_SIL = None, None
for c in _md_rows(_B_BOOT):
    if len(c) == 6 and c[4].startswith("["):
        if "Silhouette" in c[0]:
            _B_SIL = c
        else:
            _B_KEEP_ALL = c
assert _B_KEEP_ALL is not None and _B_SIL is not None, \
    "Phụ lục B: bảng bootstrap mean/CI lệch định dạng"
_B_SIL_REF = _md_rx(r"silhouette của model gốc trên train \(không nhiễu\) = "
                    r"\*\*([\d.]+)\*\*", _B_BOOT).group(1)
_B_KEEP = [c for c in _md_rows(_B_BOOT)
           if len(c) == 6 and c[1].endswith("%") and c[5].endswith("/200")]
assert len(_B_KEEP) == 4, "Phụ lục B: bảng giữ nhãn theo nhãn gốc phải đủ 4 nhóm"
_B_JAC = {c[0]: (c[1], c[2]) for c in _md_rows(_B_BOOT)
          if len(c) == 3 and c[0] in ("0", "1", "2") and "/200" in c[2]}
assert len(_B_JAC) == 3, "Phụ lục B: bảng Jaccard phải đủ 3 cụm gốc"
_B_ZERO_N = len([p for p in next(ln for ln in _B_HEA.splitlines()
                                 if "0-thật" in ln).split("):", 1)[1].split(",")
                 if p.strip()])


_C = _md_read("supervised_depth.md")
_C_RIDGE = _md_between(_C, "### Ridge hồi quy — R²", "### LogisticRegression")
_C_LR = _md_between(_C, "### LogisticRegression", "- Hình:")
_C_IMPT = _md_between(_C, "### Trên train 2011–2022 (in-sample)", "### Trên holdout")
_C_IMPH = _md_between(_C, "### Trên holdout 2023→2024", "- Hình:")
_C_RES3 = _md_between(_C, "## 3) Residual diagnostics", "### 3a)")
_C_LARGE = _md_between(_C, "### 3b)", "### 3c)")
_C_TOP = _md_between(_C, "### 3c)", "## Phạm vi")


def _md_lc(sec):
    return [(c[0], c[1], c[4]) for c in _md_rows(sec)
            if len(c) == 5 and re.fullmatch(r"\d{4}", c[0])]


def _md_imp(sec):
    out = [(c[1].replace("`", ""), c[2]) for c in _md_rows(sec)
           if len(c) == 5 and c[0].isdigit() and c[1].startswith("`sd_")]
    return out[:3]


_C_RIDGE_LC = _md_lc(_C_RIDGE)
_C_LR_LC = _md_lc(_C_LR)
assert len(_C_RIDGE_LC) == len(_C_LR_LC) == 7, \
    "Phụ lục B: learning curve phải đủ 7 origin 2016–2022"
_C_RIDGE_MIN = min(_C_RIDGE_LC, key=lambda t: float(t[2]))
_C_RIDGE_MAX = max(_C_RIDGE_LC, key=lambda t: float(t[2]))
_C_IMP_TR = _md_imp(_C_IMPT)
_C_IMP_HO = _md_imp(_C_IMPH)
assert len(_C_IMP_TR) == len(_C_IMP_HO) == 3, \
    "Phụ lục B: permutation importance phải đủ top-3 cả 2 bảng"
_C_RES_M = _md_rx(r"Holdout (\d+) cặp \(origin 2023 → đích 2024\): residual mean "
                  r"(-?[\d.]+), median (-?[\d.]+), sd (-?[\d.]+), min (-?[\d.]+), "
                  r"max (-?[\d.]+), MAE ([\d.]+)", _C_RES3)
assert float(_C_RES_M.group(2)) > 0, \
    "Phụ lục B: residual mean holdout phải dương (dự báo thấp hơn thực tế)"
_C_SUP_MAE = next(r["holdout_mae"] for r in SUP_ROWS
                  if r["task"] == "regression" and r["model"] == "ridge")
assert float(_C_SUP_MAE) == float(_C_RES_M.group(7)), \
    "Phụ lục B: MAE holdout parse từ supervised_depth.md lệch supervised_metrics.csv"
_C_POP = _md_rx(r"Median dân số 2023 \(của chính (\d+) tỉnh holdout\) = "
                r"([\d.]+) nghìn", _C_LARGE)
_C_LGSM = {c[0]: c for c in _md_rows(_C_LARGE)
           if len(c) == 7 and c[0] in ("lớn", "nhỏ")}
assert set(_C_LGSM) == {"lớn", "nhỏ"}, "Phụ lục B: bảng residual lớn/nhỏ lệch định dạng"
_C_TOP5 = [(c[1], c[6]) for c in _md_rows(_C_TOP) if len(c) == 7 and c[0].isdigit()]
assert len(_C_TOP5) == 5, "Phụ lục B: top-5 tỉnh lệch nhất phải đủ 5 dòng"
_C_TOP5_POS = all(float(r) > 0 for _, r in _C_TOP5)
_C_SEED = _md_rx(r"permutation importance dùng seed (\d+), n_repeats=(\d+)", _C)
assert _C_SEED.group(1) == _B_SEED, "Phụ lục B: seed các lane không thống nhất"
_C_HYPER = _md_rx(r"Ridge alpha=([\d.]+), LogisticRegression C=([\d.]+), "
                  r"RF max_depth=(\d+), min_samples_leaf=(\d+)", _C)
_C_CHECK = _md_rx(r"ridge CV R²=([\d.]+) / holdout MAE=([\d.]+) và RF CV R²=([\d.]+)",
                  _C)
_MDD = (ROOT / "reports" / "model_deep_dive.md").read_text(encoding="utf-8")
_MDD_VER = _md_rx(r"\*\*Phiên bản (\d+)\*\*", _MDD).group(1)
_MDD_DATE = _md_rx(r"\*\*Ngày:\*\* (\d{4}-\d{2}-\d{2})", _MDD).group(1)

h1("PHỤ LỤC B — PHÂN TÍCH CHUYÊN SÂU MODEL").paragraph_format.page_break_before = True
body("Phụ lục tổng hợp các kiểm tra bổ sung về độ nhạy của quy trình chọn cấu hình, hồ sơ và độ ổn định của cụm, cùng chẩn đoán mô hình giám sát. Các phép thử giữ nguyên cấu hình chính đã công bố. Số liệu chi tiết và mã tái lập được lưu trong reports/model_deep_dive.md và các kết quả được dẫn ở từng mục dưới đây.")

h2("B.1. Độ nhạy quy trình chọn cấu hình")
bullets([
    ("Tái lập bộ lọc CŨ — bắt buộc trước khi tin bộ lọc sửa.",
     f"{_A_MATCH} dòng khớp từng trường (k, sizes_top5, noise, largest, coverage, "
     f"stable, score, pass), khớp cả THỨ TỰ {_A_ORDER.group(1)} dòng sau sort; 4 "
     f"dòng pass trùng hệt công bố ({' / '.join(r['score'] for r in _A_PASS)}) — "
     f"winner {_A_WINNER['feat']} ({_A_WINNER['cfg']}, sizes {_A_WINNER['sizes']}, "
     f"score {_A_WINNER['score']})."),
    ("Bộ lọc SỬA (largest trên non-noise + ràng buộc cụm nhỏ nhất ≥ mcs): KHÔNG có "
     "ứng viên nào pass — phát hiện quan trọng của B5, ghi đúng theo yêu cầu.",
     f"{_A_ZERO.group(1)}/{_A_ZERO.group(2)} tổ hợp pass tại mcs = {_A_MCS_MOD}; "
     f"chính cấu hình đóng băng {_A_WINNER['feat']} ({_A_WINNER['cfg']}) tự fail: "
     f"largest_sửa = {_A_FZ_LG.group(1)} > {_A_FZ_LG.group(2)} (vượt "
     f"{_A_FZ_LG.group(3)}), min_share = {_A_FZ_MS.group(1)} < {_A_FZ_MS.group(3)} "
     f"(thiếu {_A_FZ_MS.group(2)}), score_sửa = {_A_FZ_SM} vs score công bố "
     f"{_A_SCORE_PUB}."),
    ("Độ nhạy MIN_CLUSTER_SHARE: kết quả không đổi ở cả 3 ngưỡng.",
     f"số tổ hợp pass = {_A_MCS['0.02']} (mcs 0.02) / {_A_MCS['0.05']} (0.05) / "
     f"{_A_MCS['0.1']} (0.1); vì chỉ {_A_ONLY5.group(1)}/{_A_ONLY5.group(2)} tổ "
     f"hợp có largest_sửa ≤ {_A_ONLY5.group(3)} và cả nhóm có noise_train "
     f"{_A_ONLY5.group(4)}, coverage {_A_ONLY5.group(5)} — cụm cân bằng trên "
     "non-noise chỉ xuất hiện kèm nhiễu cao và mất phủ."),
    ("Điểm cao nhất toàn bảng là giải suy biến.",
     f"top-1 {_A_TOP1.group(1)} ({_A_TOP1.group(2)}) score_sửa = "
     f"{_A_TOP1.group(3)} nhưng k = {_A_TOP5R1[3]} — fail {_A_TOP5R1[12]}; "
     f"contender gần đạt nhất (đạt k/noise/coverage, {_A_CONT.group(1)}/"
     f"{_A_CONT.group(2)} tổ hợp): {_A_CONT.group(3)} ({_A_CONT.group(4)}) — "
     f"min_share = {_A_CONT.group(5)}, còn thiếu {_A_CONT.group(6)} để đạt "
     f"{_A_CONT.group(7)}, largest_sửa = {_A_CONT.group(8)}; stable_mc_pm1: "
     f"top-1 = {_A_ST_TOP.group(3)}, contender = {_A_ST_CONT.group(3)} — trùng "
     "stable = False của cả 4 dòng pass cũ."),
    ("Khoảng cách điểm với cấu hình đóng băng.",
     f"score_sửa: top-1 − đóng băng = {_A_GAP_MOD}; công thức cũ: top-1 − "
     f"{_A_SCORE_PUB} = {_A_GAP_OLD}; contender gần nhất (score cũ {_A_CONT_OLD}) "
     f"= {_A_CONT_DELTA} so với {_A_SCORE_PUB} — không có ứng viên thay thế trong "
     "phạm vi giả định B5; nới giao thức là quyền của GV."),
])
body("Số liệu đầy đủ: results/protocol_sensitivity.md (kèm protocol_sensitivity.csv, "
     "results/figs/protocol_sensitivity_grid.png). Tái lập: "
     "python -E scripts/analysis/protocol_sensitivity.py.", italic=True)

h2("B.2. Hồ sơ và độ ổn định của cụm")
bullets([
    ("PCI tái hiện đúng số đã công bố — kiểm chứng chéo độc lập trên cùng join.",
     f"Kruskal–Wallis H = {_B_KW['pci'].group(1)}, df = {_B_KW['pci'].group(2)}, "
     f"p = {_B_KW['pci'].group(3)} (n = {_B_KW['pci'].group(4)} ô, 2011–2022); "
     f"trung vị nhóm: nhiễu {_grpm(_B_MED_PCI, '-1')}, cụm 0 "
     f"{_grpm(_B_MED_PCI, '0')}, cụm 1 {_grpm(_B_MED_PCI, '1')}, cụm 2 "
     f"{_grpm(_B_MED_PCI, '2')}."),
    ("Các chỉ số ngoài còn lại không phân hóa theo cụm (cụm 0/1 quá nhỏ — chỉ mô tả).",
     f"nghèo 13 năm giao 2012–2024: H = {_B_KW['pov'].group(1)}, "
     f"p = {_B_KW['pov'].group(3)}, n = {_B_KW['pov'].group(4)} (trung vị: nhiễu "
     f"{_grpm(_B_MED_POV, '-1')}, cụm 0 {_grpm(_B_MED_POV, '0')}, cụm 1 "
     f"{_grpm(_B_MED_POV, '1')}, cụm 2 {_grpm(_B_MED_POV, '2')}); y tế 2020: "
     f"H = {_B_KW['hea'].group(1)}, p = {_B_KW['hea'].group(3)}, "
     f"n = {_B_KW['hea'].group(4)}, df = {_B_KW['hea'].group(2)} — {_B_ZERO_N} "
     f"tỉnh không có điểm cơ sở y tế trong nguồn; GRDP/người 2018–2024: H = {_B_KW['grd'].group(1)}, "
     f"p = {_B_KW['grd'].group(3)}, n = {_B_KW['grd'].group(4)} (trung vị nhiễu "
     f"{_grpm(_B_MED_GRD, '-1')} vs cụm 2 {_grpm(_B_MED_GRD, '2')}); % đô thị: "
     f"H = {_B_KW['urb'].group(1)}, p = {_B_KW['urb'].group(3)}, "
     f"n = {_B_KW['urb'].group(4)}."),
    (f"Bootstrap ổn định ({_B_NBOOT} lần, seed {_B_SEED}, resample CÓ hoàn lại "
     "theo TỈNH, refit cấu hình đóng băng).",
     f"tỉ lệ giữ nhãn mean = {_B_KEEP_ALL[1]}, median = {_B_KEEP_ALL[2]}, sd = "
     f"{_B_KEEP_ALL[3]}, CI95 {_B_KEEP_ALL[4]}; silhouette non-noise mean = "
     f"{_B_SIL[1]}, CI95 {_B_SIL[4]} (hợp lệ {_B_SIL[5]}/{_B_NBOOT} lần) vs "
     f"model gốc trên train = {_B_SIL_REF}."),
    ("Cụm li ti vỡ dưới bootstrap — chỉ cặp nhiễu vs cụm 2 đáng tin.",
     f"giữ nhãn gộp: nhiễu {_B_KEEP[0][1]}, cụm 0 {_B_KEEP[1][1]} (ghép được "
     f"Jaccard > 0 chỉ {_B_JAC['0'][1]} lần, Jaccard TB {_B_JAC['0'][0]}), cụm 1 "
     f"{_B_KEEP[2][1]} ({_B_JAC['1'][1]}, J {_B_JAC['1'][0]}), cụm 2 "
     f"{_B_KEEP[3][1]} ({_B_JAC['2'][1]}, J {_B_JAC['2'][0]})."),
])
body("Số liệu đầy đủ: results/cluster_profile.md (kèm cluster_profile.csv, "
     "results/figs/deep_cluster_profile.png). Tái lập: "
     "python -E scripts/analysis/cluster_profile.py.", italic=True)

h2("B.3. Chẩn đoán mô hình giám sát")
bullets([
    ("Kiểm đối tái dùng pipeline — khớp 100% số đã công bố.",
     f"tái tính in-memory cho ridge CV R² = {_C_CHECK.group(1)} / holdout MAE = "
     f"{_C_CHECK.group(2)} / RF CV R² = {_C_CHECK.group(3)} — KHỚP "
     "results/supervised_metrics.csv (MAE holdout bằng chính số Bảng 7); siêu "
     "tham số cố định (CV train-only 2017–2022 của pipeline): Ridge alpha = "
     f"{_C_HYPER.group(1)}, LR C = {_C_HYPER.group(2)}, RF max_depth = "
     f"{_C_HYPER.group(3)} / min_samples_leaf = {_C_HYPER.group(4)}."),
    (f"Permutation importance (RF hồi quy, seed {_C_SEED.group(1)}, n_repeats = "
     f"{_C_SEED.group(2)}): sd_6_1 chiếm áp đảo.",
     f"train 2011–2022 (in-sample, mean giảm R²): 1. {_C_IMP_TR[0][0]} = "
     f"{_C_IMP_TR[0][1]}; 2. {_C_IMP_TR[1][0]} = {_C_IMP_TR[1][1]}; "
     f"3. {_C_IMP_TR[2][0]} = {_C_IMP_TR[2][1]}; holdout 2023→2024 (chỉ mô tả): "
     f"1. {_C_IMP_HO[0][0]} = {_C_IMP_HO[0][1]}. sd_6_1 chính là biến đích năm "
     "trước của pipeline → phần supervised chủ yếu là tự tương quan thời gian."),
    ("Learning curve expanding origin 2016→2022 (không đụng holdout).",
     f"Ridge R² dao động {_C_RIDGE_MIN[2]} (origin {_C_RIDGE_MIN[0]}, "
     f"{_C_RIDGE_MIN[1]} năm train) → {_C_RIDGE_MAX[2]} (origin "
     f"{_C_RIDGE_MAX[0]}), không tăng đơn điệu; LogisticRegression macro-F1 "
     f"{_C_LR_LC[0][2]} (2016) → {_C_LR_LC[-1][2]} (2022)."),
    ("Residual Ridge holdout 2023→2024 — dự báo THẤP hơn thực tế.",
     f"{_C_RES_M.group(1)} cặp: mean = {_C_RES_M.group(2)}, median = "
     f"{_C_RES_M.group(3)}, sd = {_C_RES_M.group(4)}, MAE = {_C_RES_M.group(7)} "
     f"(trùng công bố); tỉnh nhỏ (< median dân số {_C_POP.group(2)} nghìn của "
     f"{_C_POP.group(1)} tỉnh holdout) resid mean = {_C_LGSM['nhỏ'][3]} vs tỉnh "
     f"lớn = {_C_LGSM['lớn'][3]}; top-5 |residual|: "
     + "; ".join(f"{t} +{r}" for t, r in _C_TOP5)
     + (" — cả 5 đều dự báo THẤP hơn thực tế" if _C_TOP5_POS else "") + "."),
])
body("Số liệu đầy đủ: results/supervised_depth.md (kèm supervised_depth.csv, "
     "results/figs/supervised_learning_curve.png, "
     "results/figs/supervised_importance.png). Tái lập: "
     "python -E scripts/supervised/supervised_depth.py.", italic=True)
body("Các kiểm tra bổ sung cần được đọc riêng cho từng nhóm: tỷ lệ giữ nhãn toàn bộ chịu ảnh hưởng lớn từ cụm chiếm ưu thế, còn hai cụm nhỏ và các đặc trưng ngoài giá trị y tế năm trước kém ổn định hơn. Những nhận xét này mô tả phạm vi thử nghiệm hiện có và không xác nhận một phân hoạch xã hội tổng quát.")


h1("TÀI LIỆU THAM KHẢO").paragraph_format.page_break_before = True
refs = [
    "Wang, W., Yang, J., Muntz, R. (1997). STING: A Statistical Information Grid Approach to Spatial Data Mining. Proc. 23rd International Conference on Very Large Data Bases (VLDB), Athens, Greece, 186–195.",
    "CECODES, VFF-CRT, RTA & UNDP. Chỉ số Hiệu quả Quản trị và Hành chính công cấp tỉnh ở Việt Nam (PAPI) 2011–2024. Hà Nội. Truy cập papi.org.vn/du-lieu-papi/.",
    "Le, K. C. và cộng sự (2026). Replication data and code for: Digital Governance Capacity and Municipal Waste-Collection Performance in Vietnamese Provinces. Mendeley Data, phiên bản 1. DOI 10.17632/wbk42j9wc8.1. Giấy phép CC BY 4.0.",
    "Open Development Vietnam (OD Mekong). Ranh giới hành chính cấp tỉnh Việt Nam — GeoJSON. data.opendevelopmentmekong.net. Giấy phép CC-BY-SA 4.0.",
    "scikit-learn developers. scikit-learn: Machine Learning in Python. https://scikit-learn.org — KMeans, DBSCAN, silhouette_score, Davies–Bouldin, Calinski–Harabasz.",
    "Jain, A. K. (2010). Data clustering: 50 years beyond K-means. Pattern Recognition Letters, 31(8), 651–666.",
    "Milligan, G. W., Cooper, M. C. (1985). An examination of procedures for determining the number of clusters in a data set. Psychometrika, 50(2), 159–179.",
    "Tài liệu môn học: Học Máy — Đề cương Topic 6: Grid-based clustering (cung cấp bởi giảng viên, kỳ học 2026).",
    "VCCI – USAID. Chỉ số Năng lực cạnh tranh cấp tỉnh (PCI). pcivietnam.vn — dữ liệu công khai, tái sử dụng ghi nguồn VCCI–USAID.",
    "Tổng cục Thống kê (GSO/NSO). PX-Web pxweb.nso.gov.vn (dân số, GRDP cấp tỉnh) và Niên giám Thống kê, nso.gov.vn — dữ liệu thống kê chính thức công khai (trang bảng ghi “Bản quyền: Không”).",
    "Open Development Vietnam (OD Mekong). Health Facilities in Mekong Countries 2020. Giấy phép ODbL.",
    "World Bank. World Development Indicators (WDI) — Việt Nam (VNM), 2010–2024. CC BY 4.0.",
    "Hyndman, R. J. & Athanasopoulos, G. (2021). Forecasting: Principles and Practice (3rd ed.). OTexts. Kiểm định theo thời gian. https://otexts.com/fpp3/tscv.html.",
]
for i, r in enumerate(refs, start=1):
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Cm(0.7)
    para.paragraph_format.space_after = Pt(4)
    rr = para.add_run(f"[{i}]  ")
    set_run(rr, 12, True, TEAL)
    r2 = para.add_run(r)
    set_run(r2, 12, False, INK)

apply_reference_style(doc)
doc.save(str(OUT))
print("saved:", OUT)
