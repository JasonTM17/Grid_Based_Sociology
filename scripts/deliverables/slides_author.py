"""Author the upgraded 15-slide editable STING–PAPI defense deck (`slides/Nhom15_STING_PAPI.pptx`).

Preserves the two existing native Excel-backed editable charts (Slide 4 bar chart
and Slide 6 scatter chart) and Slides 1, 3, 4, 5, 6, 7, 13 (updating page footers
to `NN / 15`), while upgrading Slides 2, 8, 10, 11, 15 and authoring dedicated
visual slides 09 (Hồi quy 17 cấu hình & Conformal 90%), 12 (Suy luận bảng CR1/TWFE,
FDR 383 không gian con & Moran's I), and 14 (Hệ thống tích hợp & Phiếu 63 tỉnh).

Usage:
    python scripts/deliverables/slides_author.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image as PilImage
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TEMPLATE = ROOT / "assets" / "sting_papi_slides_template.pptx"
OUT = ROOT / "slides" / "Nhom15_STING_PAPI.pptx"
REPO_URL = "https://github.com/JasonTM17/Grid_Based_Sociology/blob/main/"
FONT = "Arial"

COLORS = {
    "navy": RGBColor(0x0F, 0x2B, 0x46),
    "teal": RGBColor(0x14, 0x6F, 0x78),
    "blue": RGBColor(0x12, 0x7E, 0xA1),
    "orange": RGBColor(0xB9, 0x56, 0x2A),
    "gold": RGBColor(0xB1, 0x7E, 0x20),
    "gray": RGBColor(0x56, 0x65, 0x74),
    "light": RGBColor(0xF3, 0xF6, 0xF8),
    "line": "D7E0E7",
    "ink": RGBColor(0x1B, 0x28, 0x34),
    "white": RGBColor(0xFF, 0xFF, 0xFF),
    "paleBlue": RGBColor(0xE9, 0xF2, 0xF8),
    "paleTeal": RGBColor(0xE8, 0xF4, 0xF2),
}


def _px(v: float):
    return Inches(v / 96.0)


def _pt(px_size: float):
    return Pt(px_size * 0.75)


def _dec(val: float, digits: int = 3) -> str:
    return f"{val:.{digits}f}".replace(".", ",").replace("-", "−")


def _pct(val: float, digits: int = 1) -> str:
    return f"{val * 100:.{digits}f}%".replace(".", ",")


def _p_str(val: float) -> str:
    if val < 1e-4:
        return f"{val:.2e}".replace(".", ",")
    return f"{val:.4f}".replace(".", ",")


def _clear_slide_shapes(slide) -> None:
    sp_tree = slide.shapes._spTree
    for child in list(sp_tree)[2:]:
        sp_tree.remove(child)


def _set_page_footer(slide, page_num: int, total: int = 15) -> None:
    label = f"{page_num:02d} / {total:02d}"
    for sh in slide.shapes:
        if sh.name == "page" and sh.has_text_frame:
            para = sh.text_frame.paragraphs[0]
            if para.runs:
                para.runs[0].text = label
            else:
                para.text = label
            return


def _set_notes(slide, prose: str, files: list[str] | None = None, links: list[str] | None = None) -> None:
    refs = [REPO_URL + f for f in (files or [])] + (links or [])
    body = prose if not refs else f"{prose}\n\nNguồn kiểm chứng:\n" + "\n".join(refs)
    tf = slide.notes_slide.notes_text_frame
    tf.text = body


def _add_text(
    slide,
    name: str,
    value: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size_px: float = 24,
    color: RGBColor = COLORS["ink"],
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
):
    box = slide.shapes.add_textbox(_px(x), _px(y), _px(w), _px(h))
    box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP

    lines = str(value).split("\n")
    for idx, line in enumerate(lines):
        para = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        para.alignment = align
        run = para.add_run()
        run.text = line
        run.font.name = FONT
        run.font.size = _pt(size_px)
        run.font.bold = bold
        run.font.color.rgb = color
    return box


def _add_chrome(slide, title_txt: str, source_txt: str, page_num: int, total: int = 15) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLORS["white"]
    _add_text(slide, "title", title_txt, 60, 44, 1160, 88, size_px=42, color=COLORS["navy"], bold=True)
    _add_text(slide, "source", source_txt, 60, 674, 1090, 27, size_px=16.8, color=COLORS["gray"], bold=False)
    _add_text(
        slide,
        "page",
        f"{page_num:02d} / {total:02d}",
        1150,
        674,
        70,
        26,
        size_px=17,
        color=COLORS["gray"],
        bold=False,
        align=PP_ALIGN.RIGHT,
    )


def _add_card_rect(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill_color: RGBColor,
):
    shape = slide.shapes.add_shape(1, _px(x), _px(y), _px(w), _px(h))
    shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = RGBColor(0xD7, 0xE0, 0xE7)
    shape.line.width = Pt(0.75)
    return shape


def _set_cell_borders(cell, line_hex: str = COLORS["line"]) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        old = tc_pr.find(qn(tag))
        if old is not None:
            tc_pr.remove(old)
        ln = parse_xml(
            f'<{tag} {nsdecls("a")} w="9525">'
            f'<a:solidFill><a:srgbClr val="{line_hex}"/></a:solidFill>'
            f'<a:prstDash val="solid"/>'
            f"</{tag}>"
        )
        tc_pr.append(ln)


def _add_table(
    slide,
    name: str,
    rows_data: list[list[str]],
    x: float,
    y: float,
    widths: list[float],
    heights: list[float],
    font_px: float = 20,
):
    n_rows = len(rows_data)
    n_cols = len(widths)
    tbl_shape = slide.shapes.add_table(
        n_rows,
        n_cols,
        _px(x),
        _px(y),
        _px(sum(widths)),
        _px(sum(heights)),
    )
    tbl_shape.name = name
    tbl = tbl_shape.table
    tbl.first_row = False
    tbl.horz_banding = False
    tbl.vert_banding = False
    tbl.first_col = False
    tbl.last_col = False

    for c_idx, col_w in enumerate(widths):
        tbl.columns[c_idx].width = _px(col_w)
    for r_idx, row_h in enumerate(heights):
        tbl.rows[r_idx].height = _px(row_h)

    for r_idx, row_vals in enumerate(rows_data):
        for c_idx, val in enumerate(row_vals):
            cell = tbl.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = (
                COLORS["teal"] if r_idx == 0 else (COLORS["light"] if r_idx % 2 == 0 else COLORS["white"])
            )
            cell.margin_left = 91440
            cell.margin_right = 91440
            cell.margin_top = 36000
            cell.margin_bottom = 36000
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            _set_cell_borders(cell)

            tf = cell.text_frame
            tf.word_wrap = True
            lines = str(val).split("\n")
            for l_idx, line in enumerate(lines):
                p = tf.paragraphs[0] if l_idx == 0 else tf.add_paragraph()
                p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER
                run = p.add_run()
                run.text = line
                run.font.name = FONT
                run.font.size = _pt(font_px)
                run.font.bold = (r_idx == 0)
                run.font.color.rgb = COLORS["white"] if r_idx == 0 else COLORS["ink"]
    return tbl_shape


def _fit_picture(slide, img_path: Path, x: float, y: float, max_w: float, max_h: float):
    with PilImage.open(img_path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w_px = iw * scale
    h_px = ih * scale
    left = x + (max_w - w_px) / 2.0
    top = y + (max_h - h_px) / 2.0
    return slide.shapes.add_picture(str(img_path), _px(left), _px(top), width=_px(w_px), height=_px(h_px))


def _reorder_slides(prs: Presentation, order_indices: list[int]) -> None:
    sld_id_lst = prs.slides._sldIdLst
    items = list(sld_id_lst)
    reordered = [items[idx] for idx in order_indices]
    for el in items:
        sld_id_lst.remove(el)
    for el in reordered:
        sld_id_lst.append(el)


def build_detailed_deck(
    evidence: dict,
    out_path: Path = OUT,
    template_path: Path = TEMPLATE,
) -> Path:
    """Author the 15-slide deck from `template_path` + `evidence`."""
    prs = Presentation(str(template_path))
    blank_layout = prs.slide_layouts[5]

    # Resolve original semantic slides cleanly even if called idempotently
    def _find_idx_by_title(substr: str, fallback: int) -> int:
        for i, sl in enumerate(prs.slides):
            for sh in sl.shapes:
                if sh.name == "title" and sh.has_text_frame and substr in sh.text:
                    return i
        return fallback

    if len(prs.slides) == 12:
        # Insert 3 blank slides (for Slide 09 Deep Regression, Slide 12 Panel Inference, Slide 14 Dashboard/Products)
        idx_s9_reg = len(prs.slides)
        prs.slides.add_slide(blank_layout)
        idx_s12_inf = len(prs.slides)
        prs.slides.add_slide(blank_layout)
        idx_s14_sys = len(prs.slides)
        prs.slides.add_slide(blank_layout)
        # Reorder 12 original slides + 3 new slides into clean 15-slide sequence:
        # 0:S1, 1:S2, 2:S3, 3:S4(chart), 4:S5, 5:S6(chart), 6:S7(LangSon), 7:S8,
        # 12:S9(RegDeep), 9:S10(HighDim), 8:S11(External), 13:S12(PanelInfCR1),
        # 10:S13(Stats2024), 14:S14(System/Delivery), 11:S15(Conclusion)
        _reorder_slides(prs, [0, 1, 2, 3, 4, 5, 6, 7, idx_s9_reg, 9, 8, idx_s12_inf, 10, idx_s14_sys, 11])
    elif len(prs.slides) != 15:
        raise ValueError(f"Expected 12 or 15 slides in template, found {len(prs.slides)}")

    # Double-check indices match expected roles cleanly
    assert _find_idx_by_title("lưới STING", 2) in (0, 2)

    # 1. Update page footers on untouched visual slides (1, 3, 4, 5, 6, 7, 13)
    for pos in (1, 3, 4, 5, 6, 7, 13):
        _set_page_footer(prs.slides[pos - 1], pos, 15)

    # ------------------------------------------------------------------
    # SLIDE 02 / 15: Data, 6-step Preprocessing Audit & Sensitivity
    # ------------------------------------------------------------------
    s2 = prs.slides[1]
    _clear_slide_shapes(s2)
    _add_chrome(
        s2,
        "Dữ liệu PAPI, tiền xử lý 6 bước & kiểm chứng độ nhạy",
        "Nguồn: panel 882×41 khóa; preprocessing_audit.csv; preprocessing_sensitivity.csv",
        2,
        15,
    )
    _add_text(
        s2,
        "sample",
        f"{evidence['panel_rows']} dòng × {evidence['panel_columns']} cột · 63 tỉnh × 14 năm. "
        f"Đủ hai chỉ tiêu: {evidence['all_complete_n']} dòng; thiếu: 13 dòng (22 ô).",
        60,
        138,
        1160,
        40,
        size_px=25,
        color=COLORS["teal"],
        bold=True,
    )
    _add_text(s2, "feature-heading", "Hai chỉ tiêu & Tiền xử lý Test → Decide", 60, 194, 540, 38, size_px=27, color=COLORS["teal"], bold=True)
    _add_table(
        s2,
        "features",
        [
            ["Mã", "Ý nghĩa chỉ tiêu (PAPI 2011–2024)"],
            ["4.2", "Kiểm soát tham nhũng trong cung ứng dịch vụ công"],
            ["6.1", "Y tế công lập"],
        ],
        60,
        240,
        [80, 460],
        [48, 76, 54],
        font_px=21,
    )
    pr = evidence["preprocessing"]
    _add_table(
        s2,
        "preproc-audit",
        [
            ["Bước kiểm định", "Quyết định bảo toàn dữ liệu"],
            ["Dedup & mã 0", f"0/882 trùng · {pr['zero_to_nan']} ô 0→NaN · Giữ {pr['total_missing']} ô thiếu"],
            ["Scale & |z|>3", f"{pr['scale_flagged']}/37 cờ nhảy · Giữ {pr['outliers_train2d']}/808 |z|>3 (xóa → nhiễu {pr['drop_outlier_noise']})"],
            ["Độ nhạy B/C vs A", f"|Δ CV| ≤ {pr['max_abs_delta']} < cv_std(A) ở Ridge, LR, NB"],
        ],
        60,
        434,
        [185, 355],
        [46, 56, 58, 56],
        font_px=17.5,
    )
    _add_text(s2, "protocol-heading", "Phân tách chặt theo thời gian", 640, 194, 580, 38, size_px=27, color=COLORS["teal"], bold=True)
    _add_table(
        s2,
        "protocol",
        [
            ["Giai đoạn", "Vai trò trong pipeline"],
            ["Đến 2020", "Sàng lọc đặc trưng, fit cấu hình ứng viên"],
            ["2021–2022", "Chọn cấu hình STING & CV hồi quy/phân loại"],
            ["2011–2023", "Fit lại lưới 808 dòng (và nhánh 8D ≤ 2023)"],
            ["2024", "Giữ scaler & lưới; gán 61 dòng / đánh giá 59 tỉnh"],
        ],
        640,
        240,
        [172, 408],
        [54, 72, 68, 66, 76],
        font_px=22,
    )
    _add_text(
        s2,
        "train-only",
        "StandardScaler chỉ fit trên tập huấn luyện ở từng bước; hoàn toàn không nội suy ô thiếu.",
        640,
        594,
        580,
        62,
        size_px=21,
        color=COLORS["navy"],
        bold=True,
    )
    _set_notes(
        s2,
        "Slide 2 hợp nhất dữ liệu PAPI (882×41) với quy trình 6 bước PREPROCESSING_PIPELINE và bằng chứng kiểm định trong preprocessing_audit.csv & preprocessing_sensitivity.csv: "
        "0/882 dòng trùng khóa; 109 ô điểm 0 quy về NaN (giữ nguyên 4.649/32.634 ô thiếu); đối chiếu Mendeley 756 khóa / 5.118 giá trị có max |diff| = 0.0; "
        "xóa 7 điểm |z|>3 trên train 2011–2023 làm co biên min/max của lưới đều STING khiến tỷ lệ nhiễu vọt từ 19,6% lên 24,6%, nên quyết định giữ nguyên. "
        "Thử nghiệm thay dropna bằng SimpleImputer(median) (biến thể B) hay TrainFoldWinsorizer (C) chỉ tạo |Δ CV| ≤ 0,015 (< cv_std của A là 0,056–0,130).",
        [
            "data/processed/papi_panel_v1_LOCKED.csv",
            "reports/crosscheck_mendeley.md",
            "src/preprocessing.py",
            "results/preprocessing_audit.csv",
            "results/preprocessing_sensitivity.csv",
            "notebooks/Nhom15_TienXuLy_PAPI.ipynb",
        ],
        ["https://papi.org.vn/", "https://doi.org/10.17632/wbk42j9wc8.1"],
    )

    # ------------------------------------------------------------------
    # SLIDE 08 / 15: Forecast + Edge Misses + Balanced Classifiers
    # ------------------------------------------------------------------
    s8 = prs.slides[7]
    _clear_slide_shapes(s8)
    _add_chrome(
        s8,
        "Dự báo điểm cải thiện MAE nhưng bỏ sót vùng rìa",
        "Nguồn: papi_forecast_2024.json; supervised_metrics.csv; course_supervised_baselines.csv (n = 59)",
        8,
        15,
    )
    f_scores = evidence["forecast"]["scores"]
    def _sc(tgt: str, mth: str):
        return next(r for r in f_scores if r["target"] == tgt and r["method"] == mth)
    _add_table(
        s8,
        "forecast-scores",
        [
            ["Chỉ tiêu", "MAE Ridge", "MAE giữ 2023", "RMSE Ridge", "RMSE giữ 2023"],
            ["4.2", _dec(_sc("sd_4_2", "forecast")["mae"], 4), _dec(_sc("sd_4_2", "carry")["mae"], 4), _dec(_sc("sd_4_2", "forecast")["rmse"], 4), _dec(_sc("sd_4_2", "carry")["rmse"], 4)],
            ["6.1", _dec(_sc("sd_6_1", "forecast")["mae"], 4), _dec(_sc("sd_6_1", "carry")["mae"], 4), _dec(_sc("sd_6_1", "forecast")["rmse"], 4), _dec(_sc("sd_6_1", "carry")["rmse"], 4)],
        ],
        60,
        148,
        [160, 250, 250, 250, 250],
        [56, 62, 62],
        font_px=24,
    )
    _add_text(s8, "recall-value", f"0 / {evidence['forecast']['actual_outside']}", 60, 344, 500, 68, size_px=54, color=COLORS["orange"], bold=True)
    _add_text(
        s8,
        "recall-label",
        "tỉnh ngoài vùng dày được dự báo điểm phát hiện (cả 59 dự báo rơi vào Cụm 2). Balanced accuracy = 0,500.",
        60,
        418,
        520,
        88,
        size_px=23,
    )
    _add_text(s8, "auc-value", f"AUC {_dec(evidence['forecast']['scenario_auc'])}", 680, 344, 530, 68, size_px=52, color=COLORS["teal"], bold=True)
    _add_text(
        s8,
        "auc-label",
        f"{evidence['forecast']['scenario_count']} cặp phần dư tạo kịch bản xếp hạng.\nHồi cứu thăm dò; chưa phải xác suất hiệu chỉnh tiền cứu.",
        680,
        418,
        530,
        88,
        size_px=23,
    )
    nb = next(r for r in evidence["course_baselines"] if r["model"] == "gaussian naive bayes")
    sup = evidence["supervised_summary"]
    _add_card_rect(s8, "clf-panel", 60, 520, 1160, 134, COLORS["paleTeal"])
    _add_text(
        s8,
        "classification-scope",
        f"Phân loại vùng lưới STING (CV expanding 2017–2022, giữ holdout 59 tỉnh không dùng chọn tham số):\n"
        f"• Baseline học phần (6 model, gồm KNN/SVM/DT): Naive Bayes CV macro-F1 {_dec(nb['value_cv'])} (holdout {_dec(nb['holdout_macro_f1'])}).\n"
        f"• Cập nhật cân bằng lớp (thắng 6/6 fold CV): C3 Random Forest (balanced) CV macro-F1 {_dec(sup['rf_bal_cv'])} (Acc {_pct(sup['rf_bal_acc'])} / F1 {_dec(sup['rf_bal_f1'])}); "
        f"C1 Logistic (balanced) đạt {_pct(sup['lr_bal_acc'])} / F1 {_dec(sup['lr_bal_f1'])}.",
        80,
        532,
        1120,
        114,
        size_px=20,
        color=COLORS["navy"],
        bold=False,
    )
    _set_notes(
        s8,
        "Nhánh dự báo hai đầu ra cho thấy dự báo điểm kỳ vọng có điều kiện co về vùng trung tâm Cụm 2 nên bỏ sót 11/11 ca ngoài vùng dù MAE giảm. "
        "Phần phân loại nhãn trong/ngoài vùng dày (pseudo-label STING) ban đầu dùng Naive Bayes (0,514), sau khi áp dụng ứng viên C3 Random Forest balanced đã nâng CV macro-F1 lên 0,524 (thắng 6/6 fold trước LR gốc 0,434) và lưu làm models/sup_classifier.joblib, cùng C1 Logistic balanced đạt holdout Acc 74,6% / Macro-F1 0,595.",
        [
            "results/papi_forecast_2024.json",
            "results/supervised_metrics.csv",
            "results/course_supervised_baselines.csv",
            "scripts/supervised/predict_supervised.py",
        ],
    )

    # ------------------------------------------------------------------
    # SLIDE 09 / 15 (NEW): Deep Regression (17 Configs), Conformal 90% & E3
    # ------------------------------------------------------------------
    s9 = prs.slides[8]
    _clear_slide_shapes(s9)
    _add_chrome(
        s9,
        "Hồi quy 17 cấu hình 6.1, Conformal 90% & Backtest E3",
        "Nguồn: regression_deep_analysis.{csv,md}; regression_conformal_2024.csv; future_work_backtest.csv",
        9,
        15,
    )
    reg = evidence["regression_deep"]
    _add_text(s9, "reg-head", "Đối chiếu 17 cấu hình hồi quy 6.1 (train 740)", 55, 136, 580, 34, size_px=21.5, color=COLORS["teal"], bold=True)
    _add_table(
        s9,
        "reg-table",
        [
            ["Cấu hình / Cơ chế", "CV R²", "Holdout MAE (R²)"],
            ["Giữ nguyên năm trước (baseline)", _dec(reg["carry_cv_r2"], 3), f"{_dec(reg['carry_ho_mae'], 4)} ({_dec(reg['carry_ho_r2'], 3)})"],
            ["AR(1) OLS (chỉ dùng 6.1 năm t)", _dec(reg["ar1_cv_r2"], 4), f"{_dec(reg['ar1_ho_mae'], 4)} ({_dec(reg['ar1_ho_r2'], 3)})"],
            ["Ridge 8 đặc trưng (chính thức)", _dec(reg["ridge_cv_r2"], 4), f"{_dec(reg['ridge_ho_mae'], 4)} ({_dec(reg['ridge_ho_r2'], 3)})"],
            ["Sai phân Δ6.1 = y(t+1)−y(t) Ridge α=50", _dec(reg["delta_cv_r2"], 4), f"{_dec(reg['delta_ho_mae'], 4)} ({_dec(reg['delta_ho_r2'], 3)})"],
            ["Panel FE (63 tỉnh) / Ablation bỏ 6.1", f"{_dec(reg['panel_fe_cv_r2'], 3)} / {_dec(reg['ablation_cv_r2'], 3)}", f"{_dec(reg['panel_fe_ho_mae'], 4)} ({_dec(reg['panel_fe_ho_r2'], 3)})"],
        ],
        55,
        180,
        [295, 135, 150],
        [46, 44, 44, 44, 44, 48],
        font_px=17.5,
    )
    _add_card_rect(s9, "reg-box", 55, 464, 580, 192, COLORS["paleTeal"])
    _add_text(
        s9,
        "reg-findings",
        f"Phát hiện cơ chế, bất định & không gian:\n"
        f"• VIF tham nhũng 4.1–4.3 = 3,76–5,00 (κ = 5,09); Ridge vượt carry trên OOF CV (n=366, Wilcoxon p = {_dec(reg['wilcoxon_oof_p'], 5)}), holdout p = {_dec(reg['wilcoxon_ho_p'], 3)}.\n"
        f"• Conformal 90% (±{_dec(reg['conf90_rad'], 4)}): phủ {_pct(reg['conf90_cov'])}; cận dưới < 1,7848 báo 28 tỉnh (bắt 4/4 thấp, precision 4/28; phủ ≠ chính xác cảnh báo).\n"
        f"• Backtest E3 (2019–24): Ridge thắng MAE 4/6 năm; phần dư 2024 chưa phát hiện tự tương quan 5% (I = {_dec(evidence['spatial']['resid_i'], 4)}, p = {_dec(evidence['spatial']['resid_p'], 4)}).",
        72,
        472,
        546,
        178,
        size_px=16.8,
        color=COLORS["ink"],
    )
    _fit_picture(s9, ROOT / "results/figs/regression_diagnostics_deep.png", 648, 138, 578, 520)
    _set_notes(
        s9,
        "Slide 9 trình bày kết quả đối chiếu 17 mô hình hồi quy đơn chỉ tiêu 6.1: tín hiệu dự báo cốt lõi đến từ quán tính AR(1) (bỏ 6.1 R² sụp về −0,2637), mô hình sai phân Δ6.1 Ridge α=50 đạt CV R² cao nhất 0,2732 (phi tuyến RF/KNN/HistGB chỉ đạt 0,168–0,197), Conformal 90% hiệu chỉnh trên OOF ≤2022 đạt độ phủ 94,9% (cảnh báo cận dưới báo 28 tỉnh, bắt 4/4 thấp nhưng FP=24 nên độ phủ ≠ precision), và chẩn đoán không gian chưa phát hiện tự tương quan phần dư ở 5% (Moran's I = −0,0431, p = 0,7930).",
        [
            "scripts/supervised/regression_deep_analysis.py",
            "results/regression_deep_analysis.csv",
            "results/regression_conformal_2024.csv",
            "results/figs/regression_diagnostics_deep.png",
            "results/future_work_backtest.csv",
        ],
    )

    # ------------------------------------------------------------------
    # SLIDE 10 / 15 (UPGRADED): High-Dim Robustness -> QuantileSTING & CLIQUE
    # ------------------------------------------------------------------
    s10 = prs.slides[9]
    _clear_slide_shapes(s10)
    _add_chrome(
        s10,
        "Độ bền số chiều: Từ loãng lưới đến STING đa chiều",
        "Nguồn: robustness.csv; src/high_dim.py; high_dim_sting.csv/subspaces.csv (train ≤ 2023, holdout 2024)",
        10,
        15,
    )
    hd = evidence["high_dim"]
    _add_text(s10, "hd-head", "Điểm nghẽn lưới đều & Giải pháp Quantile / CLIQUE", 55, 138, 575, 36, size_px=22, color=COLORS["teal"], bold=True)
    _add_table(
        s10,
        "robustness",
        [
            ["Cấu hình đối chiếu", "k", "Nhiễu", "Silh. / Phủ 2024"],
            ["PCA(2) d1–d6 / 8D đều (gốc)", "1 / 3", "6,2 / 60,5%", "n/a / 0,297"],
            ["8D d1–d8 đều mc=2 (OFAT)", "2", "10,9%", "−0,089 (tách yếu)"],
            ["8D d1–d8 Quantile mc=4 (wy-z)", str(hd["d8q4_k"]), _pct(hd["d8q4_noise"]), f"+{_dec(hd['d8q4_sil'], 3)} (mc=5: {_pct(hd['d8q5_ho'])})"],
            ["8D sàng lọc Quantile mc=7 (≤23)", str(hd["q7_k"]), _pct(hd["q7_noise"]), f"24: {_pct(hd['q7_ho'])} (wy-z k=3)"],
            ["CLIQUE 5D đều / 4D Quantile", f"{hd['cu5_k']} / {hd['cq4_k']}", f"{_pct(hd['cu5_noise'], 0)} / {_pct(hd['cq4_noise'], 0)}", f"{_dec(hd['cu5_sil'], 3)} / {_dec(hd['cq4_sil'], 3)}"],
        ],
        55,
        180,
        [255, 76, 108, 141],
        [46, 46, 46, 46, 46, 46],
        font_px=17.5,
    )
    _add_card_rect(s10, "hd-box", 55, 468, 580, 188, COLORS["paleBlue"])
    _add_text(
        s10,
        "hd-takeaway",
        f"Vì sao lưới đều 8D thất bại & vẫn giữ STING 2D (3/4/5/2):\n"
        f"• Thang thưa 16^d (f=4 lv=2 mc=5): nhiễu nhảy {_pct(hd['d2_f4_noise'])} (d=2) → {_pct(hd['d3_f4_noise'])} (d=3) → 100% (d=4, 65.536 ô); 0/28 cặp có cụm ≤ 90%.\n"
        f"• Không thay bản chính 2D: Quantile trên lưới mịn 2D 16×16 cắt nát vùng lõi lên {_pct(hd['q2d_noise'])} nhiễu (Silh. {_dec(hd['q2d_sil'], 3)}), "
        f"nên STING 2D 3/4/5/2 vẫn tối ưu cho 4.2 × 6.1.",
        72,
        478,
        546,
        170,
        size_px=18,
        color=COLORS["navy"],
        bold=False,
    )
    _fit_picture(s10, ROOT / "results/figs/high_dim_sting_analysis.png", 648, 138, 578, 520)
    _set_notes(
        s10,
        "Slide 10 đặt cạnh nhau bảng robustness gốc (PCA k=1, 8D 60,5% nhiễu, mc=2 sil −0,089) với toàn bộ nghiên cứu STING đa chiều không rò rỉ 2024 (src/high_dim.py): "
        "(1) Thang thưa 16^d lý giải curse of dimensionality; (2) Rà vét cạn 28 cặp/56 bộ ba khẳng định PAPI mang 1 lõi chi phối; (3) Subspace CLIQUE Apriori khai phá đến 5D đều / 4D Quantile; (4) QuantileSTING hiệu chuẩn n/res^d hạ nhiễu d1–d8 xuống 44,7% (Silh +0,161) và tách 8D sàng lọc mc=7 thành k=4 phủ 60,7% năm 2024. Nhưng trên 2D 16×16 thì Quantile phá vỡ lõi (49,0% nhiễu), khẳng định giữ STING 2D lưới đều 3/4/5/2 làm chuẩn.",
        ["results/robustness.csv", "src/high_dim.py", "scripts/analysis/high_dim_sting.py", "results/high_dim_sting.csv", "results/high_dim_sting.md"],
    )

    # ------------------------------------------------------------------
    # SLIDE 11 / 15 (UPGRADED SLIDE 9): External Validation + Naive vs CR1 Flag
    # ------------------------------------------------------------------
    s11 = prs.slides[10]
    _clear_slide_shapes(s11)
    _add_chrome(
        s11,
        "Đối chiếu nguồn ngoài PAPI & Giới hạn gộp",
        "Nguồn: external_validation.{csv,md}; poverty_validation.csv; panel_inference.csv (PCI 2011–2022)",
        11,
        15,
    )
    ext = evidence["external_checks"]
    pi = evidence["panel_inf"]
    _add_table(
        s11,
        "external",
        [
            ["Nguồn / giai đoạn", "n", "p gộp (Kruskal)", "p Year-FE CR1 (63 tỉnh)", "Diễn giải mô tả"],
            ["PCI 2011–2022", str(ext["pci_n"]), f"{_p_str(ext['pci_p'])} (raw)", f"{_p_str(pi['2d_pci_cr1'])} (Wald {_dec(pi['2d_pci_waldf'], 2)})", "Trung vị Cụm 2: 62,16 vs −1: 59,16\nBiến mất hoàn toàn khi thêm Year-FE"],
            ["GRDP/người 2018–2024", str(ext["grdp_n"]), _p_str(ext["grdp_p"]), f"{_p_str(pi['2d_grdp_cr1'])} (TWFE {_p_str(pi['2d_grdp_tw'])})", "Khác biệt mô tả giữa nhóm,\nchưa đạt ngưỡng 5% dưới CR1"],
            ["Điểm y tế ODM 2020", str(ext["odm_n"]), _p_str(ext["odm_p"]), "Snapshot 1 năm", f"Chưa có bằng chứng khác biệt;\n{ext['odm_zero_count']} tỉnh không ghi nhận điểm nguồn"],
            ["Nghèo GSO 2012–2024", str(ext["poverty_n"]), f"{_dec(ext['poverty_raw_p'], 3)} (thô)", f"{_p_str(pi['2d_pov_cr1'])} (C2 vs −1)", f"Trừ median năm KW p={_dec(ext['poverty_demeaned_p'], 6)}\nHiệu ứng ANOVA {ext['poverty_eta_note'].split(' (')[0].replace('.', ',')}"],
        ],
        55,
        148,
        [265, 76, 178, 226, 425],
        [62, 86, 86, 88, 90],
        font_px=20.5,
    )
    _add_text(
        s11,
        "external-limit",
        "Quan sát lặp theo tỉnh & xu hướng năm làm p-value gộp gây nhiễu dương giả trên 2D — chi tiết hiệu chỉnh CR1/TWFE & FDR 383 không gian con ở Slide 12.",
        55,
        584,
        1170,
        74,
        size_px=22,
        color=COLORS["navy"],
        bold=True,
    )
    _set_notes(
        s11,
        "So với bảng gộp thô trước đây, cột p Year-FE CR1 chứng minh trực diện vì sao kiểm định gộp gây hiểu lầm: PCI 2011–2022 trên STING 2D cho p gộp 5,84e-7 (raw C2 vs -1 = 8,14e-7) nhưng khi thêm Fixed Effects theo năm + CR1 63 tỉnh chỉ còn β = -0,174 (p = 0,7007, WCR = 0,7075; Wald 4 nhóm p = 0,9237) — hoàn toàn là nhiễu trộn theo năm (2011–2013 điểm PCI cả nước thấp hơn và tỷ lệ C2 thấp hơn). "
        "GRDP cũng trượt ngưỡng 5% (p CR1 = 0,0662) và Nghèo C2 vs -1 cho p CR1 = 0,8888.",
        ["results/external_validation.csv", "results/poverty_validation.csv", "results/panel_inference.csv", "results/panel_inference.md"],
    )

    # ------------------------------------------------------------------
    # SLIDE 12 / 15 (NEW): Panel Inference (CR1/TWFE), Holm/BH/BY FDR & Spatial Moran's I
    # ------------------------------------------------------------------
    s12 = prs.slides[11]
    _clear_slide_shapes(s12)
    _add_chrome(
        s12,
        "Suy luận bảng (CR1 / TWFE), Kiểm soát FDR & Moran's I",
        "Nguồn: panel_inference.{csv,md}; FWL + Liang–Zeger CR1 (63 tỉnh); B = 1.999 WCR / hoán vị quanh E[I]",
        12,
        15,
    )
    _add_text(s12, "inf-head", "Year-FE CR1 vs Two-Way FE & Kiểm soát đa kiểm định", 55, 138, 575, 36, size_px=21.5, color=COLORS["teal"], bold=True)
    _add_table(
        s12,
        "panel-inf-table",
        [
            ["Nhánh · Biến ngoài", "Naive thô", "Year-FE CR1 (β, p)", "TWFE · Holm (3 / 6)"],
            ["STING 2D · PCI (n=726)", _p_str(pi["2d_pci_raw"]), f"{_dec(pi['2d_pci_b'], 3)} ({_p_str(pi['2d_pci_cr1'])})", f"TW {_p_str(pi['2d_pci_tw'])} · Loại"],
            ["8D Quant. mc=7 · PCI (411)", _p_str(pi["hd_pci_raw"]), f"{_dec(pi['hd_pci_b'], 3)} ({_p_str(pi['hd_pci_cr1'])})", f"{_dec(pi['hd_pci_tw'], 3)} · {_dec(pi['hd_pci_holm'], 3)} / {_dec(pi['hd_pci_holm_g'], 3)}"],
            ["8D wy-z mc=7 · PCI (415)", _p_str(pi["wy_pci_raw"]), f"{_dec(pi['wy_pci_b'], 3)} ({_p_str(pi['wy_pci_cr1'])})", f"TW {_p_str(pi['wy_pci_tw'])} (độ nhạy)"],
            ["8D Quant. · GRDP / Nghèo", f"{_dec(pi['hd_grdp_raw'], 3)} / {_p_str(pi['hd_pov_raw'])}", f"{_p_str(pi['hd_grdp_cr1'])} / {_p_str(pi['hd_pov_cr1'])}", "Holm 0,149 (Loại)"],
            ["Thăm dò 383 KGC PCI (KW)", f"{pi['sub_naive']} (<0,05)", f"{pi['sub_bh']} BH-FDR 5%", f"{pi['sub_by']} BY / {pi['sub_holm']} Holm"],
        ],
        55,
        178,
        [222, 108, 128, 122],
        [46, 46, 46, 46, 46, 46],
        font_px=16,
    )
    sp = evidence["spatial"]
    _add_card_rect(s12, "inf-box", 55, 464, 580, 192, COLORS["paleTeal"])
    _add_text(
        s12,
        "inf-notes",
        f"Kết luận suy luận & Chẩn đoán không gian 2024:\n"
        f"• Kiểm soát 6 phép & TWFE: 8D mc=7 đạt CR1 (p = {_p_str(pi['hd_pci_cr1'])}, WCR = {_dec(pi['hd_pci_wcr'], 4)}) và Holm nội họ 8D ({_dec(pi['hd_pci_holm'], 4)}), chưa đạt Holm 6 phép ({_dec(pi['hd_pci_holm_g'], 4)}); TWFE p = {_dec(pi['hd_pci_tw'], 4)} chưa bác bỏ 0.\n"
        f"• Không gian (Queen 63 tỉnh): sd_6_1 I = +{_dec(sp['obs61_i'], 4)} (p={_p_str(sp['obs61_p'])}); pred_ridge I = +{_dec(sp['pred_i'], 4)} (p={_p_str(sp['pred_p'])}); phần dư Ridge chưa phát hiện tự tương quan 5% (I = {_dec(sp['resid_i'], 4)}, p = {_p_str(sp['resid_p'])}).",
        72,
        472,
        546,
        178,
        size_px=16.8,
        color=COLORS["ink"],
    )
    _fit_picture(s12, ROOT / "results/figs/panel_inference_diagnostics.png", 648, 138, 578, 520)
    _set_notes(
        s12,
        "Slide 12 là trụ cột suy luận thống kê của đồ án: phép chiếu Frisch–Waugh–Lovell (FWL) + Liang–Zeger CR1 trên 63 tỉnh và WCR Bootstrap (B=1.999, chiếu lại Year-FE) loại bỏ hoàn toàn nhiễu trộn theo năm ở 2D PCI (p=0,7007) và dương giả trên GRDP/Nghèo ở 8D Quantile; với 8D Quantile mc=7 trên PCI, β=+1,561 (p=0,0156, WCR=0,0185) đạt Holm nội họ 8D (0,0468) nhưng chưa đạt Holm 6 phép chính (0,0937) và TWFE p=0,3420 chưa bác bỏ 0 (không tự chứng minh phân tầng cấu trúc hay nhân quả). Sàng lọc thăm dò 383 KGC giữ 117 BH-FDR 5%; Moran's I phần dư Ridge (I=-0,0431, p=0,7930) chưa phát hiện tự tương quan 5% nhưng không đồng nghĩa chứng minh nhiễu trắng.",
        ["scripts/analysis/panel_inference.py", "results/panel_inference.csv", "results/panel_inference.md", "results/figs/panel_inference_diagnostics.png", "tests/test_panel_inference.py"],
    )

    # ------------------------------------------------------------------
    # SLIDE 14 / 15 (NEW): Dashboard 6 Tab, Excel 28 Sheet, Báo cáo DOCX & Phiếu 63 tỉnh
    # ------------------------------------------------------------------
    s14 = prs.slides[13]
    _clear_slide_shapes(s14)
    _add_chrome(
        s14,
        "Hệ thống tích hợp: Dashboard, Báo cáo & Phiếu 63 tỉnh",
        "Nguồn: app.py; KetQua_STING_PAPI.xlsx; stakeholder_quadrants_2024.png; client_product.py",
        14,
        15,
    )
    _add_text(s14, "sys-p1-t", "Dashboard Streamlit 6 Tab (chỉ-đọc, fail-closed)", 55, 138, 575, 34, size_px=23, color=COLORS["teal"], bold=True)
    _add_text(
        s14,
        "sys-p1-b",
        "• Tổng quan & Lưới STING 63 tỉnh (14 năm) + Phân tích Đa chiều Quantile / CLIQUE.\n"
        "• Dự báo 6.1 (17 cấu hình, Conformal 90%) + Kiểm chứng ngoài (Year-FE CR1, FDR, Moran's I).\n"
        "• Kiểm toán thang đo 23/37 cột + Bảng bàn giao 63 tỉnh & In phiếu A4 từng địa phương.",
        55,
        178,
        575,
        136,
        size_px=18.5,
    )
    _add_text(s14, "sys-p2-t", "Bộ Hồ sơ Thống nhất & Khung Thẩm định Độc lập", 55, 316, 575, 34, size_px=23, color=COLORS["teal"], bold=True)
    _add_text(
        s14,
        "sys-p2-b",
        "• Báo cáo DOCX 7 chương (13 hình, 18 bảng, 86 mục điều hướng Word) & Excel 28 sheet.\n"
        "• Bộ đôi Notebook thực thi sạch (22 & 9 code cell) + Bộ Slide bảo vệ 15 trang.\n"
        "• Khung thẩm định mù đôi 16 hồ sơ rà soát (cases.csv + external_dossier.csv phi-PAPI).",
        55,
        356,
        575,
        128,
        size_px=18,
    )
    _add_card_rect(s14, "sys-ci-box", 55, 496, 575, 154, COLORS["paleBlue"])
    _add_text(
        s14,
        "sys-ci-text",
        "Kiểm chứng tự động & Đóng gói liên nền tảng (Ubuntu · Windows · macOS):\n"
        "• 293 kiểm thử pytest (94% bao phủ src/) · 264 tham chiếu Q&A hợp lệ.\n"
        "• Gói ZIP 173 tệp tự chứa, khớp SHA-256 & replay notebook trên cả 3 HĐH.",
        72,
        508,
        542,
        132,
        size_px=17,
        color=COLORS["navy"],
        bold=True,
    )
    _fit_picture(s14, ROOT / "results/figs/stakeholder_quadrants_2024.png", 648, 138, 578, 520)
    _set_notes(
        s14,
        "Slide 14 minh họa sản phẩm tích hợp sẵn sàng bàn giao và trình diễn thực tế: dashboard Streamlit 6 tab hoạt động hoàn toàn trên artifact đã kiểm chứng (fail-closed nếu lệch CSV), bảng Excel 28 sheet đồng bộ chỉ mục động, phiếu A4 in được từng tỉnh, bộ hồ sơ thẩm định thực địa mù đôi 16 ca phi-PAPI cùng toàn bộ quy trình kiểm chứng 3 hệ điều hành trên GitHub Actions.",
        ["app.py", "scripts/analysis/client_product.py", "results/KetQua_STING_PAPI.xlsx", "results/stakeholder_province_summary_2024.csv", "scripts/deliverables/build_report.py"],
    )

    # ------------------------------------------------------------------
    # SLIDE 15 / 15 (UPGRADED CONCLUSION): Complete 15-slide Synthesis
    # ------------------------------------------------------------------
    s15 = prs.slides[14]
    _clear_slide_shapes(s15)
    _add_chrome(
        s15,
        "Kết luận, giới hạn và hướng phát triển",
        "Tài liệu chính: Wang, Yang & Muntz (VLDB 1997); PAPI; Mendeley; PCI, GSO, ODM; CR1/FDR",
        15,
        15,
    )
    _add_text(s15, "contribution-title", "1. Kết luận cốt lõi từ toàn bộ nghiên cứu", 60, 142, 1160, 38, size_px=26, color=COLORS["teal"], bold=True)
    _add_text(
        s15,
        "contribution-body",
        "• STING 2D (3/4/5/2) minh bạch, truy vết được từng ô (ARI = 0,950 giả lập; bất biến 869/869 z-score; 48 Cụm 2 / 13 ô thưa / 2 thiếu 2024).\n"
        "• Hồi quy 17 cấu hình làm rõ động lực AR(1)/Δ6.1 (CV R² 0,2732), Conformal 90% phủ 94,9% (precision 4/28), C3/C1 nâng F1 CV 0,524 và phần dư Ridge chưa phát hiện tự tương quan 5% (p = 0,7930).\n"
        "• Mở rộng đa chiều (QuantileSTING / CLIQUE) giảm nhiễu 8D còn 44,7% (Silh. +0,161); Year-FE CR1 giữ PCI ở 8D (p = 0,0156, Holm nhánh 0,0468; Holm 6 phép 0,0937; sàng lọc thăm dò 117/383 BH-FDR).",
        60,
        184,
        1160,
        156,
        size_px=19.8,
    )
    _add_text(s15, "limits-title", "2. Giới hạn phương pháp luận", 60, 354, 1160, 38, size_px=26, color=COLORS["teal"], bold=True)
    _add_text(
        s15,
        "limits-body",
        "• STING 2D có Cụm 2 chiếm 96,8% điểm vào cụm; chia quantile chỉ hợp lý ở 3D–8D (gây vỡ lõi 2D lên 49,0% nhiễu) nên giữ chuẩn 2D lưới đều.\n"
        "• Nhãn phân loại là pseudo-label; chưa bác bỏ TWFE (p = 0,342) hay đạt Holm 6 phép chính (0,0937) và mới hồi kiểm trên một mốc holdout 2024.",
        60,
        396,
        1160,
        96,
        size_px=20,
    )
    _add_text(s15, "future-title", "3. Bước tiếp theo", 60, 502, 1160, 38, size_px=26, color=COLORS["teal"], bold=True)
    _add_text(
        s15,
        "future-body",
        "• Tổ chức 2 chuyên viên chấm mù đôi độc lập 16 phiếu địa phương (cases.csv + external_dossier.csv) trước khi dùng nhãn tham chiếu.\n"
        "• Kiểm định tiền cứu ngoài mẫu trên dữ liệu PAPI 2025 khi được công bố và hiệu chỉnh xác suất cảnh báo vận hành.",
        60,
        544,
        1160,
        74,
        size_px=20.5,
    )
    _add_text(
        s15,
        "thanks",
        "Cảm ơn thầy và các bạn. Nhóm xin nhận câu hỏi.",
        60,
        626,
        1160,
        36,
        size_px=26,
        color=COLORS["teal"],
        bold=True,
    )
    _set_notes(
        s15,
        "Slide 15 kết luận cô đọng toàn bộ 4 trụ cột của đồ án: (1) STING 2D truy vết chuẩn hóa & bàn giao 63 tỉnh; (2) Phân tích hồi quy 17 cấu hình + Conformal 90% + cân bằng lớp C3/C1; (3) Mở rộng STING đa chiều QuantileSTING & Subspace CLIQUE kèm bằng chứng giữ chuẩn 2D lưới đều; (4) Lớp suy luận bảng FWL Year-FE CR1 / TWFE, Holm-BH-BY FDR trên 383 không gian con và Moran's I phần dư. Mọi mở rộng đóng vai trò thăm dò học thuật bổ trợ, không tự ý thay cấu hình chốt trước khi có kiểm chứng tiền cứu PAPI 2025.",
        [
            "results/future_work.md",
            "results/high_dim_sting.md",
            "results/panel_inference.md",
            "results/regression_deep_analysis.md",
            "reports/Nhom15_BaoCao_STING_PAPI.docx",
        ],
        [
            "https://www.vldb.org/conf/1997/P186.PDF",
            "https://papi.org.vn/",
            "https://doi.org/10.17632/wbk42j9wc8.1",
            "https://otexts.com/fpp3/",
        ],
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return out_path


def main() -> None:
    import argparse
    from scripts.deliverables.build_slides import build_evidence

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT, help="Destination PPTX path")
    args = parser.parse_args()
    ev = build_evidence()
    out = build_detailed_deck(ev, args.output, TEMPLATE)
    print(f"Authored 15 detailed slides to {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
