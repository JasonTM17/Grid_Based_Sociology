"""Đối chiếu chéo panel tự xây với panel của gói Mendeley (2011–2022).

Chạy: python scripts/crosscheck_mendeley.py
Ghi ra: reports/crosscheck_mendeley.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "data" / "processed" / "papi_panel_63_2011_2024.csv"
REF = ROOT / "data" / "raw" / "mendeley" / "Replication_package" / "data" / "papi_panel_63_2011_2022.csv"
OUT = ROOT / "reports" / "crosscheck_mendeley.md"

DIM_NAMES = {
    1: "papi_d1_participation",
    2: "papi_d2_transparency",
    3: "papi_d3_accountability",
    4: "papi_d4_corruption_control",
    5: "papi_d5_admin_procedures",
    6: "papi_d6_public_service_delivery",
    7: "papi_d7_environmental_governance",
    8: "papi_d8_e_governance",
}


def main() -> int:
    ours = pd.read_csv(PANEL)
    ref = pd.read_csv(REF)
    m = ours.merge(ref, on=["province_code", "year"], suffixes=("", "_ref"), how="inner")

    lines = ["# Đối chiếu chéo panel tự xây vs Mendeley (2011–2022)", ""]
    lines.append(f"- Panel của ta: {ours.shape[0]} hàng × {ours.shape[1]} cột")
    lines.append(f"- Panel Mendeley: {ref.shape[0]} hàng × {ref.shape[1]} cột")
    lines.append(f"- Số hàng giao nhau (khớp province_code + year): {len(m)}")
    lines.append("")

    any_fail = False
    lines.append("| Chiều | Overlap hợp lệ | Max |diff| | Ghi chú |")
    lines.append("|---|---|---|---|")
    for i, refcol in DIM_NAMES.items():
        if f"d{i}" not in m.columns or refcol not in m.columns:
            lines.append(f"| d{i} | - | - | THIẾU CỘT |")
            any_fail = True
            continue
        both = m[[f"d{i}", refcol]].dropna()
        if both.empty:
            lines.append(f"| d{i} | 0 | - | không có overlap hợp lệ |")
            any_fail = True
            continue
        diff = (both[f"d{i}"] - both[refcol]).abs()
        maxd = float(diff.max())
        note = "OK" if maxd <= 1e-6 else "**LỆCH**"
        if maxd > 1e-6:
            any_fail = True
        lines.append(f"| d{i} | {len(both)} | {maxd:.2e} | {note} |")

    lines.append("")
    verdict = "FAIL — có chiều lệch > 1e-6" if any_fail else "PASS — mọi chiều khớp trong 1e-6"
    lines.append(f"**Kết luận: {verdict}**")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print()
    print("saved:", OUT)
    return 0 if not any_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
