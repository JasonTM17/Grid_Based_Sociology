"""MỞ THẬT + render PDF/PNG để kiểm tra bố cục deliverable (cần Microsoft Office).

Yêu cầu: Word + PowerPoint (COM), pymupdf. Chạy:
    python scripts/deliverables/render_check.py
    python scripts/deliverables/render_check.py --slides-only --pptx slides/submission.pptx

Đầu ra mặc định (xem bằng mắt):
    %TEMP%\\sting_papi_render\\
        slides\\*.png      — từng slide
        final_report.pdf + report_p01.png ... — từng trang báo cáo
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path(tempfile.gettempdir()) / "sting_papi_render"
REPORT = ROOT / "reports" / "final_report.docx"
DEFAULT_SLIDES = ROOT / "slides" / "final.pptx"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def render_report(report_path: Path, out_dir: Path) -> Path:
    import win32com.client as win32

    pdf_path = out_dir / f"{report_path.stem}.pdf"
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(report_path.resolve()), ReadOnly=True)
        doc.SaveAs2(str(pdf_path), FileFormat=17)
        doc.Close(False)
        print("Word: da export", pdf_path.name)
    finally:
        word.Quit()

    import pymupdf

    d = pymupdf.open(pdf_path)
    for i, page in enumerate(d):
        pix = page.get_pixmap(dpi=110)
        pix.save(str(out_dir / f"report_p{i + 1:02d}.png"))
    print(f"PDF render: {len(d)} trang -> {out_dir}")
    return pdf_path


def render_slides(pptx_path: Path, out_dir: Path) -> int:
    import win32com.client as win32

    slide_dir = out_dir / "slides"
    slide_dir.mkdir(parents=True, exist_ok=True)
    ppt = win32.Dispatch("PowerPoint.Application")
    try:
        pres = ppt.Presentations.Open(
            str(pptx_path.resolve()), ReadOnly=True, Untitled=False, WithWindow=False
        )
        pres.SaveAs(str(slide_dir), 18)
        pres.Close()
        n = len({p.name.casefold() for p in slide_dir.iterdir() if p.suffix.lower() == ".png"})
        print(f"PowerPoint: da export {n} slide -> {slide_dir}")
        return n
    finally:
        ppt.Quit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", type=Path, default=DEFAULT_SLIDES, help="PowerPoint deck to export")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Output folder for rendered PNG/PDF")
    parser.add_argument("--slides-only", action="store_true", help="Only export PowerPoint slides")
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.slides_only:
        render_report(REPORT, out_dir)
    render_slides(args.pptx, out_dir)
    print("XONG — mở thư mục:", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
