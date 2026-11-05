"""Kiểm tra tuân thủ dataset cuối kỳ: >= 500 hàng và >= 10 cột (theo yêu cầu môn).

Cách dùng (chạy từ thư mục gốc dự án):
    python scripts/check_data.py [duong_dan_csv_hoac_parquet]

Mặc định: data/processed/papi_panel_63_2011_2024.csv
Kết quả: in shape, số cột số, tỷ lệ thiếu, số tỉnh, khoảng năm → PASS/FAIL.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MIN_ROWS = 500
MIN_COLS = 10


def load(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def scale_audit(df: pd.DataFrame) -> list[tuple[str, float, int]]:
    """Cột có bước nhảy trung bình năm > 0.25 điểm cần được kiểm tra thêm.

    Đây là heuristic từ dữ liệu, không tự chứng minh gãy thang đo: thay đổi
    điểm trung bình có thể là biến động thực. Một ví dụ đã được đối chiếu với
    workbook gốc là sd_5_4 (0.25–2.5 đến 2020, 0.33–3.33 từ 2021).
    """
    num = [
        c for c in df.columns
        if (c.startswith("d") or c.startswith("sd_")) and df[c].dtype.kind in "fi"
    ]
    if "year" not in df.columns or not num:
        return []
    means = df.groupby("year")[num].mean()
    flags = []
    for c in num:
        m = means[c].dropna()
        if len(m) < 5:
            continue
        jumps = m.diff().abs()
        j = float(jumps.max())
        if j > 0.25:
            flags.append((c, round(j, 3), int(jumps.idxmax())))
    flags.sort(key=lambda t: -t[1])
    return flags


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    path = Path(argv[1]) if len(argv) > 1 else Path("data/processed/papi_panel_63_2011_2024.csv")
    if not path.exists():
        print(f"[SKIP] Chưa có file {path} — panel sẽ được tạo ở Phase 2.")
        return 2

    df = load(path)
    n_rows, n_cols = df.shape
    n_numeric = df.select_dtypes("number").shape[1]

    print(f"File: {path}")
    print(f"Shape: {n_rows} hàng x {n_cols} cột (cột số: {n_numeric})")

    key = "province" if "province" in df.columns else ("province_code" if "province_code" in df.columns else None)
    if key:
        print(f"Số tỉnh ({key}): {df[key].nunique()}")
    if "year" in df.columns:
        years = sorted(df["year"].dropna().unique())
        print(f"Năm: {years[0]}–{years[-1]} ({len(years)} năm)")

    missing = df.isna().mean().sort_values(ascending=False).head(8)
    print("Thiếu nhiều nhất (%):")
    print((missing * 100).round(2).to_string())

    flags = scale_audit(df)
    if flags:
        print("CẢNH BÁO biến động trung bình năm > 0.25 điểm (heuristic; không tự kết luận gãy thang đo):")
        for c, j, y in flags[:15]:
            print(f"  {c}: +{j} tại {y}")
        print(f"  Tổng {len(flags)}/{len([c for c in df.columns if c.startswith(('d','sd_'))])} cột chỉ tiêu bị đánh dấu.")
        print("  Đối chiếu workbook/codebook trước khi kết luận nguyên nhân hoặc chọn feature xuyên năm.")
    else:
        print("Không có mean-jump flag theo heuristic; kết quả này không tự chứng minh thang đo tương đương.")

    ok_rows = n_rows >= MIN_ROWS
    ok_cols = n_cols >= MIN_COLS
    ok_numeric = n_numeric >= MIN_COLS
    verdict = "PASS" if (ok_rows and ok_cols and ok_numeric) else "FAIL"
    print(f"Yêu cầu: >= {MIN_ROWS} hàng, >= {MIN_COLS} cột tổng, >= {MIN_COLS} cột số -> {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
