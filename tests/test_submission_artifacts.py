"""Gate artifact nộp bài: slide, notebook demo, và provenance PDF PAPI.

Đối chiếu demo tổng hợp và kết quả phân cụm PAPI với artifact. Các hàm
``check_*`` dùng chung cho artifact thật và bản sao đột biến trong RAM.

Chạy: python -m pytest tests/test_submission_artifacts.py -q
"""

from __future__ import annotations

import copy
from base64 import b64decode
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
import pytest
from docx import Document
from docx.oxml.ns import qn
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]

SUBMISSION_PPTX = ROOT / "slides" / "submission.pptx"
SUBMISSION_NB = ROOT / "notebooks" / "Nhom15_GiuaKy_STING_PAPI.ipynb"
PROVENANCE = ROOT / "data" / "raw" / "papi" / "PROVENANCE.md"
PAPI_PDF = ROOT / "data" / "raw" / "papi" / "PAPI_2024_REPORT_VIE_final.pdf"
EXPECTED_ARI_STR = "0.950"
MIDTERM_SLIDE_COUNT = 11
THANK_YOU = "Cảm ơn thầy và các bạn đã lắng nghe"

_IGNORE_PATTERNS = (
    re.compile(r"""filterwarnings\s*\(\s*['"]ignore['"]""", re.IGNORECASE),
    re.compile(r"""simplefilter\s*\(\s*['"]ignore['"]""", re.IGNORECASE),
)
_PDF_HASH_RE = re.compile(
    r"PAPI_2024_REPORT_VIE_final\.pdf.*?SHA-256\s+`([a-f0-9]{64})`",
    re.IGNORECASE | re.DOTALL,
)
_HOST_ABS_PATH_PATTERNS = (
    re.compile(r"D:\\"),
    re.compile(r"C:\\Users"),
    re.compile(r"/Users/"),
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_report_embeds_current_canonical_figures():
    figures = (
        "00_synthetic_sting.png", "sting_first_real.png", "papi_forecast_values.png",
        "papi_forecast_grid.png", "course_confusion_matrix.png", "evolution.png",
        "map_2024.png", "external_pci_by_cluster.png", "external_health_density_2020.png",
        "external_grdp_by_cluster.png", "external_wdi_panel.png", "external_poverty_by_cluster.png",
    )
    report = Document(ROOT / "reports" / "final_report.docx")
    shapes = list(report.inline_shapes)
    assert len(shapes) == len(figures) + 1
    for shape, path in zip(shapes, (
        ROOT / "assets/report-cover-logo.png", *(ROOT / "results" / "figs" / name for name in figures)
    ), strict=True):
        relation = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
        embedded = report.part.related_parts[relation].blob
        assert hashlib.sha256(embedded).hexdigest() == _sha256_file(path), (
            f"Hình chưa cập nhật từ {path.name}; cần tạo lại báo cáo."
        )


def test_report_uses_the_user_final_template_geometry():
    report = Document(ROOT / "reports" / "final_report.docx")
    cover, front, body = report.sections
    assert (cover.left_margin.twips, cover.right_margin.twips) == (1417, 1134)
    assert (cover.page_width.twips, cover.page_height.twips) == (11906, 16838)
    border = cover._sectPr.find(qn("w:pgBorders"))
    assert border.get(qn("w:display")) == "firstPage"
    assert [edge.get(qn("w:val")) for edge in border] == ["double"] * 4
    assert front._sectPr.find(qn("w:pgBorders")) is None
    assert body._sectPr.find(qn("w:pgNumType")).get(qn("w:start")) == "1"
    assert report.styles["Body Text"].paragraph_format.line_spacing == 1.5


def check_pptx_submission(prs: Presentation) -> list[str]:
    """Kiểm tra 10 slide đầu, slide cảm ơn và ghi chú thuyết trình."""
    violations: list[str] = []
    count = len(prs.slides)
    if count != MIDTERM_SLIDE_COUNT:
        violations.append(f"submission.pptx có {count} slide, cần đúng {MIDTERM_SLIDE_COUNT}")
    else:
        closing_text = [
            shape.text.strip() for shape in prs.slides[-1].shapes if shape.has_text_frame and shape.text.strip()
        ]
        if closing_text != [THANK_YOU]:
            violations.append("slide cuối chỉ dành cho lời cảm ơn")
    for index, slide in enumerate(prs.slides, start=1):
        notes = ""
        if slide.has_notes_slide:
            frame = slide.notes_slide.notes_text_frame
            notes = (frame.text if frame is not None else "").strip()
        if not notes:
            violations.append(f"slide {index}: ghi chú trống")
    return violations


def _cell_source_text(cell: dict) -> str:
    raw = cell.get("source", "")
    if isinstance(raw, list):
        return "".join(raw)
    return str(raw)


def check_notebook_cells(nb: dict) -> list[str]:
    """Ô code phải có output; không error/stderr; không filterwarnings ignore."""
    violations: list[str] = []
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    if not code_cells:
        violations.append("notebook không có ô code")
        return violations

    for index, cell in enumerate(code_cells):
        source = _cell_source_text(cell)
        for pattern in _IGNORE_PATTERNS:
            if pattern.search(source):
                violations.append(
                    f"ô code #{index}: nguồn chứa lệnh bỏ qua cảnh báo ({pattern.pattern})"
                )

        outputs = cell.get("outputs")
        if not outputs:
            violations.append(f"ô code #{index}: không có output đã lưu")
            continue

        for output in outputs:
            if output.get("output_type") == "error":
                violations.append(f"ô code #{index}: output_type=error")
            if output.get("output_type") == "stream" and output.get("name") == "stderr":
                violations.append(f"ô code #{index}: có stderr stream")

    return violations


def notebook_markdown_text(nb: dict) -> str:
    chunks: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        chunks.append(_cell_source_text(cell))
    return "\n".join(chunks)


def notebook_executed_text(nb: dict) -> str:
    """Ghép mọi stdout / text/plain từ output đã lưu."""
    chunks: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for output in cell.get("outputs") or []:
            kind = output.get("output_type")
            if kind == "stream":
                text = output.get("text", "")
                chunks.append("".join(text) if isinstance(text, list) else str(text))
            elif kind in ("execute_result", "display_data"):
                data = output.get("data") or {}
                plain = data.get("text/plain")
                if plain is not None:
                    chunks.append("".join(plain) if isinstance(plain, list) else str(plain))
    return "\n".join(chunks)


def check_notebook_no_absolute_host_paths(nb: dict) -> list[str]:
    """Output đã lưu không được chứa đường dẫn tuyệt đối máy chủ."""
    blob = notebook_executed_text(nb)
    violations: list[str] = []
    for pattern in _HOST_ABS_PATH_PATTERNS:
        if pattern.search(blob):
            violations.append(
                f"output notebook chứa đường dẫn host khớp {pattern.pattern!r}"
            )
    return violations


def provenance_pdf_sha256(md_text: str) -> str | None:
    match = _PDF_HASH_RE.search(md_text)
    return match.group(1).lower() if match else None


def check_papi_pdf_provenance(
    provenance_path: Path = PROVENANCE,
    pdf_path: Path = PAPI_PDF,
) -> list[str]:
    violations: list[str] = []
    if not provenance_path.is_file():
        violations.append(f"thiếu {provenance_path.relative_to(ROOT)}")
        return violations
    if not pdf_path.is_file():
        violations.append(f"thiếu {pdf_path.relative_to(ROOT)}")
        return violations

    text = provenance_path.read_text(encoding="utf-8")
    if "PAPI_2024_REPORT_VIE_final.pdf" not in text:
        violations.append("PROVENANCE.md không liệt kê PAPI_2024_REPORT_VIE_final.pdf")

    listed = provenance_pdf_sha256(text)
    if listed is None:
        violations.append(
            "PROVENANCE.md không ghi SHA-256 của PAPI_2024_REPORT_VIE_final.pdf"
        )
        return violations

    actual = _sha256_file(pdf_path)
    if listed != actual:
        violations.append(
            f"SHA-256 trong PROVENANCE ({listed}) khác file thực ({actual})"
        )
    return violations


@pytest.fixture(scope="module")
def submission_notebook() -> dict:
    assert SUBMISSION_NB.is_file(), "thiếu notebooks/Nhom15_GiuaKy_STING_PAPI.ipynb"
    return json.loads(SUBMISSION_NB.read_text(encoding="utf-8"))


def test_submission_pptx_exists_and_notes():
    assert SUBMISSION_PPTX.is_file(), "thiếu slides/submission.pptx"
    presentation = Presentation(str(SUBMISSION_PPTX))
    violations = check_pptx_submission(presentation)
    assert not violations, "\n".join(violations)
    titles_and_text = "\n".join(shape.text for slide in presentation.slides
                                for shape in slide.shapes if shape.has_text_frame)
    assert "Đọc cụm từ bảng đếm 3 × 3" in titles_and_text
    assert "Tài liệu tham khảo" not in titles_and_text
    assert "nhóm báo cáo trung thực" not in titles_and_text.lower()
    assert "PHÂN CỤM DỰA TRÊN LƯỚI STING" in titles_and_text
    assert "APPLICATION OF STING GRID-BASED CLUSTERING" in titles_and_text
    assert all(call in titles_and_text for call in (
        "run_preprocessing_pipeline(...)", "fit(X)", "cluster(level, connectivity=1)", "predict(X_moi)",
    ))
    assert "Vì sao STING có 3 cụm, K-means dùng k = 2?" in titles_and_text
    assert "56 ô dày" in titles_and_text
    assert "Z-score thay đổi điều gì?" in titles_and_text
    assert "Silhouette trên cùng 680 điểm" in titles_and_text
    assert "print((idx_raw == idx_z).all(axis=1).sum())" in titles_and_text
    assert "869/869 điểm cùng ô" in titles_and_text and "68 điểm đổi cụm" in titles_and_text
    assert "8 điểm đổi trạng thái nhiễu" in titles_and_text
    assert "482 và 195 điểm" in titles_and_text
    assert "48/61 tỉnh nằm ở 21 ô dày thuộc 1 cụm trên lưới 2011–2023." in titles_and_text
    assert "7 tỉnh sang ô thưa, 5 tỉnh từ ô thưa vào cụm." in titles_and_text
    assert "dự báo" not in titles_and_text.lower()
    assert "869 quan sát tỉnh–năm" in titles_and_text
    assert "677" in titles_and_text and "19.7%" in titles_and_text
    assert "huấn luyện" not in titles_and_text
    table = next(shape.table for shape in presentation.slides[7].shapes if shape.has_table)
    assert [table.cell(i, 3).text for i in range(1, 5)] == ["0.3802", "0.4605", "0.3499", "0.2740"]
    trace = next(shape.table for shape in presentation.slides[9].shapes if shape.has_table)
    assert [trace.cell(i, 2).text for i in (1, 2)] == ["(13, 9)", "(12, 10)"]
    assert [trace.cell(i, 3).text for i in (1, 2)] == ["2", "12"]


def test_midterm_notebook_root_skips_incomplete_loose_folder(submission_notebook, tmp_path, monkeypatch):
    root = tmp_path / "Đồ án PAPI"
    loose = root / "submissions/01-giua-ky"
    for relative in (
        "src/sting.py", "src/preprocessing.py", "scripts/common/midterm_clustering.py",
        "data/processed/papi_panel_63_2011_2024.csv", "submissions/01-giua-ky/src/sting.py",
    ):
        marker = root / relative
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()

    monkeypatch.chdir(loose)
    for env_key in ("STING_REPO_ROOT", "SUBMISSION_DEMO_NB_PATH", "JPY_STARTUP_PATH"):
        monkeypatch.delenv(env_key, raising=False)
    setup = next(cell for cell in submission_notebook["cells"] if cell["cell_type"] == "code")
    finder = _cell_source_text(setup).split("ROOT = _find_project_root()", 1)[0]
    namespace = {}
    exec(finder, namespace)

    assert namespace["_find_project_root"]() == root


def test_submission_notebook_cells(submission_notebook: dict):
    violations = check_notebook_cells(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_no_absolute_host_paths(submission_notebook: dict):
    violations = check_notebook_no_absolute_host_paths(submission_notebook)
    assert not violations, "\n".join(violations)


def test_submission_notebook_course_rubric_sections(submission_notebook: dict):
    """Giữa kỳ cần tiền xử lý, demo Grid-based và đánh giá phân cụm."""
    md_text = notebook_markdown_text(submission_notebook)
    code_cells = [
        c for c in submission_notebook.get("cells", []) if c.get("cell_type") == "code"
    ]
    missing: list[str] = []
    for section in ("Lý thuyết STING", "Cài đặt từ đầu", "Phân cụm trên dữ liệu PAPI",
                    "Chuẩn bị mẫu phân tích", "Tính z-score từ số liệu thật"):
        if section not in md_text:
            missing.append(f"thiếu mục {section}")
    if not any("preprocessing_audit.csv" in _cell_source_text(c) for c in code_cells):
        missing.append("không có ô đọc preprocessing_audit.csv")
    for calculation in ("KMeans(", "DBSCAN(", "scores.std(ddof=0)", "Counter(grid_model.label_of_.values())"):
        if not any(calculation in _cell_source_text(c) for c in code_cells):
            missing.append(f"thiếu phép tính {calculation}")
    assert not missing, "\n".join(missing)
    assert all(phrase not in md_text for phrase in (
        "Thứ tự giảng dạy", "Test → Decide", "Cách chạy", "Cùng ví dụ với slide",
    ))


def test_submission_notebook_key_numbers(submission_notebook: dict):
    output = notebook_executed_text(submission_notebook)
    assert "2 cụm, mỗi cụm 7 điểm. 1 điểm nhiễu." in output
    assert f"ARI = {EXPECTED_ARI_STR}" in output
    for expected in (
        "869 quan sát đủ hai chỉ tiêu", "61/63 quan sát vào cùng mẫu",
        "Hai chỉ tiêu có 22 ô thiếu trên 13 dòng tỉnh–năm.",
        "56 ô dày tạo thành 3 vùng liên thông.",
        "1 ô dày, 5 quan sát.", "3 ô dày, 16 quan sát.", "52 ô dày, 677 quan sát.",
        "Nhiễu: 171/869 quan sát (19.7%)",
        "= 0.9005", "= 0.3737", "ô (12, 10) (đếm từ 0), ô có 17 quan sát",
        "K-means chọn k=2 trong các giá trị đã thử và gán đủ 869 điểm.",
    ):
        assert expected in output


def test_submission_runs_all_kmeans_and_sensitivity_trials(submission_notebook: dict):
    output = notebook_executed_text(submission_notebook)
    for k, score in ((2, "0.4472"), (3, "0.3354"), (4, "0.3649"), (5, "0.3311")):
        assert f"k={k}  |  Silhouette = {score}" in output
    for threshold, k, n_noise, pct in ((3, 3, 85, "9.8"), (5, 3, 171, "19.7"), (8, 1, 271, "31.2")):
        assert f"Ngưỡng {threshold}  |  {k} cụm  |  {n_noise}/869 nhiễu ({pct}%)" in output


def test_midterm_compares_shared_points_and_check_scaling_effect(submission_notebook: dict):
    output = notebook_executed_text(submission_notebook)
    assert "Silhouette trên cùng 680/869 điểm" in output
    assert "869 − (171 + 120 − 102) = 680" in output
    assert "162/171 điểm nhãn −1 có |z| ≤ 3 trên cả hai trục" in output
    assert "Nếu loại 9 điểm |z| > 3 rồi dựng lại lưới trên 860 điểm: 4 cụm, 173/860 điểm nhiễu (20.1%)." in output
    assert "Lưới 4 × 4 | 12 ô dày | 1 cụm | 6/869 điểm nhiễu" in output
    assert "Lưới 16 × 16 | 56 ô dày | 3 cụm | 171/869 điểm nhiễu" in output
    assert "Kề 8 hướng (connectivity=2) | 56 ô dày | 1 cụm | 171/869 điểm nhiễu" in output
    for method, score in (("STING", "0.3802"), ("K-means k=2", "0.4605"),
                          ("K-means k=3", "0.3499"), ("DBSCAN", "0.2740")):
        assert f"{method} | silhouette cùng tập = {score}" in output
    assert "K-means k=2 chia các điểm này thành 482 + 195" in output
    assert "K-means k=3 chia các điểm này thành 306 + 303 + 68" in output
    assert "STING: 869/869 điểm cùng chỉ số ô, 869/869 nhãn trùng" in output
    assert "K-means k=2: 68/869 điểm đổi nhóm sau ghép tên cụm" in output
    assert "ARI giữa hai lần chạy K-means: 0.7103" in output
    assert "DBSCAN: ε gốc = 0.0316, 5 cụm, 116 điểm nhiễu" in output
    assert "DBSCAN sau chuẩn hóa: 6 cụm, 120 điểm nhiễu, 8/869 điểm đổi trạng thái nhiễu" in output
    assert "DBSCAN: 6 điểm chuyển sang nhiễu, 2 điểm từ nhiễu vào cụm" in output
    assert "Thêm significance_z=2.0: 46 ô đạt, 4 cụm, 270/869 điểm nhiễu" in output
    assert "Lưới tham chiếu dùng 808 quan sát 2011–2023." in output
    assert "48/61 tỉnh đủ hai chỉ tiêu vào cụm (78.7%)." in output
    assert "48 điểm nằm ở 21 ô dày thuộc 1 cụm." in output
    assert "Cả 13/13 tỉnh ô thưa năm 2024 đều có |z| ≤ 3 trên lưới tham chiếu (|z| lớn nhất = 2.1299)." in output
    assert "Ghép được 59 tỉnh đủ chỉ tiêu ở cả hai năm." in output
    assert "39/43 tỉnh giữ nguyên cụm nhưng đổi ô." in output
    assert "papi_forecast" not in "\n".join(_cell_source_text(cell) for cell in submission_notebook["cells"])
    assert "Lạng Sơn 2023: ngoài vùng dày trên cùng lưới" in output
    assert "Lạng Sơn 2024: cụm 2 trên cùng lưới" in output
    assert "Ô (13, 9) có 2 điểm tham chiếu." in output
    assert "Ô (12, 10) có 12 điểm tham chiếu." in output
    assert "7 tỉnh sang ô thưa, 5 tỉnh từ ô thưa vào cụm." in output
    assert "Truy vấn từ trên xuống tổng hợp 322 điểm trong các ô nằm trọn vùng" in output
    assert "Đếm trực tiếp từng điểm trong vùng: 348 điểm." in output


def test_midterm_contains_the_comparison_and_observed_figures(submission_notebook):
    cells = submission_notebook["cells"]
    figures = (
        (next(cell for cell in cells if "papi-zscore-comparison" in cell.get("metadata", {}).get("tags", [])),
         "papi_zscore_comparison.png"),
        (next(cell for cell in cells if 'results/figs/predict_2024.png' in _cell_source_text(cell)),
         "predict_2024.png"),
    )
    for cell, filename in figures:
        png = next(output["data"]["image/png"] for output in cell["outputs"] if "image/png" in output.get("data", {}))
        assert b64decode("".join(png)) == (ROOT / "results/figs" / filename).read_bytes()


def test_midterm_slide_uses_current_panel_for_2024_coverage(tmp_path):
    panel_path = Path("data/processed/papi_panel_63_2011_2024.csv")
    slide_builder = Path("scripts/deliverables/build_slides_10.py")
    for relative in (
        panel_path, slide_builder, Path("src/sting.py"),
        Path("scripts/common/midterm_clustering.py"), Path("scripts/common/papi_pred_common.py"),
        Path("scripts/common/fig_style.py"), Path("results/preprocessing_audit.csv"),
        Path("results/papi_observed_grid_2024.csv"), Path("results/figs/00_synthetic_sting.png"),
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


    panel = pd.read_csv(tmp_path / panel_path)
    year = panel.year.eq(2024)
    features = ["sd_4_2", "sd_6_1"]
    panel.loc[year & panel.province_vi.eq("Quảng Ninh"), features] = (
        panel.loc[year & panel.province_vi.eq("Lạng Sơn"), features].to_numpy()
    )
    panel.to_csv(tmp_path / panel_path, index=False)
    completed = subprocess.run(
        [sys.executable, str(slide_builder)], cwd=tmp_path, capture_output=True, timeout=120,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    slide = Presentation(str(tmp_path / "slides/submission.pptx")).slides[9]
    text = "\n".join(shape.text for shape in slide.shapes if shape.has_text_frame)
    assert "49/61 tỉnh nằm ở 21 ô dày thuộc 1 cụm" in text


def test_papi_pdf_provenance_chain():
    violations = check_papi_pdf_provenance()
    assert not violations, "\n".join(violations)


def test_gate_detects_twelfth_slide_in_memory():
    """Đột biến RAM: thêm slide thứ 12 phải làm gate đỏ (không ghi file)."""
    presentation = Presentation(str(SUBMISSION_PPTX))
    layout_index = 6 if len(presentation.slide_layouts) > 6 else 0
    presentation.slides.add_slide(presentation.slide_layouts[layout_index])
    assert len(presentation.slides) == 12
    violations = check_pptx_submission(presentation)
    assert any("cần đúng 11" in message for message in violations)


def test_gate_rejects_content_on_thank_you_slide():
    presentation = Presentation(str(SUBMISSION_PPTX))
    text_box = next(shape for shape in presentation.slides[-1].shapes if shape.has_text_frame and shape.text)
    text_box.text += "\nChi tiết kết quả"
    assert "slide cuối chỉ dành cho lời cảm ơn" in check_pptx_submission(presentation)


def test_gate_detects_error_output_in_memory(submission_notebook: dict):
    """Đột biến RAM: chèn output error phải làm gate đỏ."""
    mutant = copy.deepcopy(submission_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        cell.setdefault("outputs", []).append(
            {
                "output_type": "error",
                "ename": "SyntheticError",
                "evalue": "cố ý",
                "traceback": ["SyntheticError: cố ý"],
            }
        )
        break
    else:
        pytest.fail("notebook không có ô code để đột biến")

    violations = check_notebook_cells(mutant)
    assert any("output_type=error" in message for message in violations)


def test_gate_detects_missing_output_in_memory(submission_notebook: dict):
    mutant = copy.deepcopy(submission_notebook)
    for cell in mutant.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            break
    violations = check_notebook_cells(mutant)
    assert any("không có output" in message for message in violations)


def test_optional_final_slides_match_grid_method_and_presentation_scope():
    """Keep the method caveat and teacher-facing results in the oral deck."""
    deck = Presentation(ROOT / "slides/final.pptx")
    text = "\n".join(
        shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame
    )
    assert len(deck.slides) == 16
    assert all(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip()
               for slide in deck.slides)
    assert "STING rút gọn" in text
    assert "Cài đặt dùng ngưỡng số đếm" in text
    assert "STING gốc còn dùng phân phối và kiểm định thống kê" in text
    assert "23/37 cột đổi thang" not in text
    assert "28 unit test" not in text
    assert "Kết quả chính và hướng phát triển" in text
    assert "Dự báo hai điểm PAPI rồi đối chiếu theo vùng" in text
    assert "0/11 tỉnh ngoài vùng dày được nhận ra" in text
    assert "0,0736" in text and "0,0641" in text
    assert "Cảm ơn thầy và các bạn đã lắng nghe" in text
    closing_text = "\n".join(
        shape.text for shape in deck.slides[-1].shapes if shape.has_text_frame
    ).strip()
    assert closing_text == "Cảm ơn thầy và các bạn đã lắng nghe"
    assert all(phrase not in text.lower() for phrase in (
        "báo cáo trung thực", "slide ghi điểm", "nói rõ trước khi được hỏi",
        "nghi thức phản biện", "bộ nộp cuối kỳ",
    ))
    notes = "\n".join(slide.notes_slide.notes_text_frame.text for slide in deck.slides)
    assert all(name in notes for name in ["Nhom15_CuoiKy_STING_PAPI.docx", "Nhom15_CuoiKy_STING_PAPI.ipynb"])
