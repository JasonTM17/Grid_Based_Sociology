"""MỞ THẬT + render PDF/PNG để kiểm tra bố cục deliverable (cần Microsoft Office).

Yêu cầu: Word + PowerPoint (COM), pymupdf. Chạy:
    python scripts/render_check.py

Đầu ra (xem bằng mắt):
    C:\\Users\\Admin\\AppData\\Local\\Temp\\opencode\\demo_render\\
        slides\\slide_01.png ... slide_16.png   — mỗi slide
        report_p01.png ...                      — từng trang báo cáo (PDF render)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("TEMP", "/tmp")) / "opencode" / "demo_render"
REPORT = ROOT / "reports" / "final_report.docx"
SLIDES = ROOT / "slides" / "final.pptx"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def render_report(pdf_path: Path) -> None:
    import win32com.client as win32

    word = win32.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(REPORT), ReadOnly=True)
        doc.SaveAs2(str(pdf_path), FileFormat=17)  # wdFormatPDF
        doc.Close(False)
        print("Word: da export", pdf_path.name)
    finally:
        word.Quit()

    import pymupdf

    d = pymupdf.open(pdf_path)
    for i, page in enumerate(d):
        pix = page.get_pixmap(dpi=110)
        pix.save(str(OUT / f"report_p{i + 1:02d}.png"))
    print(f"PDF render: {len(d)} trang -> {OUT}")


def render_slides() -> None:
    import win32com.client as win32

    slide_dir = OUT / "slides"
    slide_dir.mkdir(parents=True, exist_ok=True)
    ppt = win32.Dispatch("PowerPoint.Application")
    try:
        pres = ppt.Presentations.Open(
            str(SLIDES), ReadOnly=True, Untitled=False, WithWindow=False
        )
        pres.SaveAs(str(slide_dir), 18)  # ppSaveAsPNG
        pres.Close()
        n = len(list(slide_dir.glob("*.PNG"))) + len(list(slide_dir.glob("*.png")))
        print(f"PowerPoint: da export {n} slide -> {slide_dir}")
    finally:
        ppt.Quit()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    render_report(OUT / "final_report.pdf")
    render_slides()
    print("XONG — mở thư mục:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
