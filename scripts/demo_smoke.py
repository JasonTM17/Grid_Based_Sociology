"""Kiem tra san sang DEMO — chay truoc khi len san (~10 giay).

Chay: python scripts/demo_smoke.py
In bang kiem tra tung muc + ket luan tong. Exit 0 neu tat ca deu dat.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))


def file_nonempty(rel: str, min_bytes: int = 200) -> None:
    p = ROOT / rel
    ok = p.is_file() and p.stat().st_size >= min_bytes
    check(rel, ok, f"{p.stat().st_size if p.is_file() else 0:,} bytes" if p.is_file() else "MISSING")


# --- 1) Dataset va model --- #
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
except Exception as e:  # noqa: BLE001
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

# --- 2) Artifacts ket qua --- #
for f in [
    "results/figs/predict_2024.png",
    "results/figs/00_synthetic_sting.png",
    "results/figs/sting_first_real.png",
    "results/figs/evolution.png",
    "results/figs/map_2024.png",
    "results/figs/supervised_regression.png",
    "results/figs/supervised_confusion.png",
    "results/predict_all_years.csv",
    "results/predict_summary.md",
    "results/metrics.csv",
    "results/robustness.csv",
    "results/supervised_metrics.csv",
    "results/supervised_summary.md",
    "results/analysis_summary.md",
]:
    file_nonempty(f, min_bytes=100)

# --- 3) Deliverables nop bai --- #
for f in [
    "notebooks/midterm_demo.ipynb",
    "notebooks/final_analysis.ipynb",
    "notebooks/submission_demo.ipynb",
    "slides/final.pptx",
    "slides/submission.pptx",
    "reports/final_report.docx",
    "reports/qa_midterm.md",
    "reports/qa_final.md",
]:
    file_nonempty(f, min_bytes=500)

# --- 4) Docs mo duoc --- #
try:
    import docx  # noqa: E402

    d = docx.Document(ROOT / "reports" / "final_report.docx")
    check("final_report.docx mo duoc", len(d.paragraphs) > 100, f"{len(d.paragraphs)} doan, {len(d.tables)} bang")
except Exception as e:  # noqa: BLE001
    check("final_report.docx mo duoc", False, str(e))

try:
    from pptx import Presentation  # noqa: E402

    p = Presentation(ROOT / "slides" / "final.pptx")
    n = len(p.slides._sldIdLst)
    check("final.pptx mo duoc 16 trang", n == 16, f"{n} trang")
except Exception as e:  # noqa: BLE001
    check("final.pptx mo duoc", False, str(e))

# --- 5) Notebook execute san --- #
import nbformat  # noqa: E402

for nb in [
    "notebooks/midterm_demo.ipynb",
    "notebooks/final_analysis.ipynb",
    "notebooks/submission_demo.ipynb",
]:
    try:
        n = nbformat.read(ROOT / nb, as_version=4)
        n_cells = len(n.cells)
        n_err = sum(
            1 for c in n.cells for o in c.get("outputs", []) if o.get("output_type") == "error"
        )
        check(f"{nb} da execute, 0 loi", n_err == 0, f"{n_cells} cells, {n_err} loi")
    except Exception as e:  # noqa: BLE001
        check(f"{nb} doc duoc", False, str(e))

try:
    from pptx import Presentation  # noqa: E402

    p_sub = Presentation(ROOT / "slides" / "submission.pptx")
    n_sub = len(p_sub.slides._sldIdLst)
    check("submission.pptx mo duoc <=10 trang", 1 <= n_sub <= 10, f"{n_sub} trang")
except Exception as e:  # noqa: BLE001
    check("submission.pptx mo duoc", False, str(e))

# --- Bao cao --- #
print("=" * 64)
print("KIỂM TRA SẴN SÀNG DEMO — STING × PAPI")
print("=" * 64)
for name, ok, detail in RESULTS:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
print("=" * 64)
if n_fail == 0:
    print(f"KET LUAN: SAN SANG DEMO ({len(RESULTS)}/{len(RESULTS)} muc dat). Chuc ban buoi thi thanh cong!")
    print("Goi y: chay 'python -m nbconvert --to notebook --execute --inplace notebooks/midterm_demo.ipynb'")
    print("       truoc buoi thi neu bat dau tu may khac.")
    raise SystemExit(0)
print(f"KET LUAN: CHUA SAN SANG — {n_fail} muc FAIL o tren. Sua xong chay lai script nay.")
raise SystemExit(1)
