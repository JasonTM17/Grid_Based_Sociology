"""Export PowerPoint slides to PNG for layout QA (Microsoft PowerPoint COM).

Usage:
    python scripts/render_pptx.py
    python scripts/render_pptx.py slides/submission.pptx path/to/output_dir
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PPTX = ROOT / "slides" / "submission.pptx"
DEFAULT_OUT = Path(os.environ.get("TEMP", "/tmp")) / "opencode" / "slides10_render"


def export_png(pptx: Path, out_dir: Path, width: int = 1280, height: int = 720) -> int:
    import win32com.client as win32

    out_dir.mkdir(parents=True, exist_ok=True)
    ppt = win32.Dispatch("PowerPoint.Application")
    try:
        pres = ppt.Presentations.Open(
            str(pptx.resolve()), ReadOnly=True, Untitled=False, WithWindow=False
        )
        n = pres.Slides.Count
        for i in range(1, n + 1):
            target = out_dir / f"slide_{i:02d}.png"
            pres.Slides(i).Export(str(target), "PNG", width, height)
        pres.Close()
        print(f"exported {n} slides -> {out_dir}")
        return n
    finally:
        ppt.Quit()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx", nargs="?", default=str(DEFAULT_PPTX))
    ap.add_argument("out_dir", nargs="?", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    export_png(Path(args.pptx), Path(args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
