"""Kiem tra san sang DEMO — chay truoc khi trinh bay (~10 giay).

Chay: python scripts/deliverables/demo_smoke.py
In bang kiem tra tung muc + ket luan tong. Exit 0 neu tat ca deu dat.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.common.notebook_checks import notebook_issues  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))


def file_nonempty(rel: str, min_bytes: int = 200) -> None:
    p = ROOT / rel
    ok = p.is_file() and p.stat().st_size >= min_bytes
    check(rel, ok, f"{p.stat().st_size if p.is_file() else 0:,} bytes" if p.is_file() else "MISSING")


check(
    "panel 882x41, >=500x10",
    (ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv").is_file(),
)
import pandas as pd  # noqa: E402

try:
    df = pd.read_csv(ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv")
    check("panel shape 882x41", df.shape == (882, 41), f"{df.shape[0]}x{df.shape[1]}")
    check("63 tinh x 14 nam", df.province_code.nunique() == 63 and df.year.nunique() == 14)
    n_num = df.select_dtypes("number").shape[1]
    check(">= 10 cot so", n_num >= 10, f"{n_num} cot so")
except Exception as e:
    check("panel readable", False, str(e))

for f in [
    "models/sting_predict_model.pkl",
    "models/sting_predict_scaler.json",
    "models/predict_config.json",
    "models/sup_ridge.joblib",
    "models/sup_rf.joblib",
    "models/sup_classifier.joblib",
]:
    file_nonempty(f)

for f in [
    "results/figs/predict_2024.png",
    "results/figs/00_synthetic_sting.png",
    "results/figs/sting_first_real.png",
    "results/figs/evolution.png",
    "results/figs/map_2024.png",
    "results/figs/stakeholder_quadrants_2024.png",
    "results/figs/supervised_regression.png",
    "results/figs/supervised_confusion.png",
    "results/predict_all_years.csv",
    "results/predict_summary.md",
    "results/stakeholder_province_summary_2024.csv",
    "results/stakeholder_summary.md",
    "results/KetQua_STING_PAPI.xlsx",
    "results/metrics.csv",
    "results/robustness.csv",
    "results/supervised_metrics.csv",
    "results/supervised_summary.md",
    "results/analysis_summary.md",
    "results/preprocessing_audit.csv",
    "results/preprocessing_sensitivity.csv",
    "data/processed/papi_panel_scale_metadata.csv",
]:
    file_nonempty(f, min_bytes=100)

for f in [
    "notebooks/Nhom15_STING_PAPI.ipynb",
    "notebooks/Nhom15_TienXuLy_PAPI.ipynb",
    "slides/Nhom15_STING_PAPI.pptx",
    "reports/Nhom15_BaoCao_STING_PAPI.docx",
    "reports/on-tap/qa_final.md",
    "submissions/Nhom15_STING_PAPI.zip",
]:
    file_nonempty(f, min_bytes=500)

try:
    import docx

    d = docx.Document(ROOT / "reports" / "Nhom15_BaoCao_STING_PAPI.docx")
    check("Nhom15_BaoCao_STING_PAPI.docx mo duoc", len(d.paragraphs) > 100, f"{len(d.paragraphs)} doan, {len(d.tables)} bang")
except Exception as e:
    check("Nhom15_BaoCao_STING_PAPI.docx mo duoc", False, str(e))

try:
    from pptx import Presentation

    p = Presentation(ROOT / "slides" / "Nhom15_STING_PAPI.pptx")
    n = len(p.slides._sldIdLst)
    check("Nhom15_STING_PAPI.pptx mo duoc 11 trang", n == 11, f"{n} trang")
except Exception as e:
    check("Nhom15_STING_PAPI.pptx mo duoc", False, str(e))

import nbformat  # noqa: E402

for nb in [
    "notebooks/Nhom15_STING_PAPI.ipynb",
    "notebooks/Nhom15_TienXuLy_PAPI.ipynb",
]:
    try:
        n = nbformat.read(ROOT / nb, as_version=4)
        n_cells = len(n.cells)
        issues = notebook_issues(n)
        check(
            f"{nb} da execute, 0 loi",
            not issues,
            f"{n_cells} cells; " + ("; ".join(issues) if issues else "Run All, 0 error/stderr"),
        )
    except Exception as e:
        check(f"{nb} doc duoc", False, str(e))

print("=" * 64)
print("KIỂM TRA SẴN SÀNG DEMO THỐNG NHẤT — STING × PAPI")
print("=" * 64)
for name, ok, detail in RESULTS:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
print("=" * 64)
if n_fail == 0:
    print(f"KET LUAN: SAN SANG DEMO ({len(RESULTS)}/{len(RESULTS)} muc dat). Chuc ban bao cao thanh cong!")
    print("Goi nop thong nhat: submissions/Nhom15_STING_PAPI/ va submissions/Nhom15_STING_PAPI.zip")
    raise SystemExit(0)
print(f"KET LUAN: CHUA SAN SANG — {n_fail} muc FAIL o tren. Sua xong chay lai script nay.")
raise SystemExit(1)
