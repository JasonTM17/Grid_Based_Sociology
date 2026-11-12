"""Cập nhật field Word trong báo cáo (TOC, danh mục hình/bảng, số trang).

Chạy ngay sau khi dựng file:
    python scripts/build_report.py
    python scripts/update_report_fields.py

Cần Microsoft Word và pywin32 trên Windows; ghi đè ``reports/final_report.docx`` tại chỗ.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "reports" / "final_report.docx"


def main() -> int:
    if not DOCX.is_file():
        print(f"Không tìm thấy {DOCX.relative_to(ROOT)} — chạy scripts/build_report.py trước.")
        return 1

    try:
        import win32com.client as win32
    except ImportError:
        print(
            "Không import được win32com (cài pywin32). "
            "Script này cần Microsoft Word trên Windows."
        )
        return 2

    word = None
    try:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(DOCX), ReadOnly=False)
        for i in range(1, doc.TablesOfContents.Count + 1):
            doc.TablesOfContents(i).Update()
        for i in range(1, doc.TablesOfFigures.Count + 1):
            doc.TablesOfFigures(i).Update()
        doc.Fields.Update()
        doc.Save()
        doc.Close(False)
        print("Da cap nhat field:", DOCX.relative_to(ROOT))
        return 0
    except Exception as exc:
        print(f"Word COM that bai: {exc}")
        return 2
    finally:
        if word is not None:
            word.Quit()


if __name__ == "__main__":
    raise SystemExit(main())
