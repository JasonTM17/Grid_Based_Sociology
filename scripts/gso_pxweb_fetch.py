"""Tải dữ liệu bảng PX-Web cổ điển của GSO (pxweb.nso.gov.vn) qua POST WebForms.

Giao diện PX-Web "cổ" của GSO không mở API v1 cho các database Tài khoản quốc
gia, nên script này giả lập trình duyệt: GET trang chọn biến -> POST form
(VIEWSTATE/EVENTVALIDATION + danh sách giá trị được chọn + nút "Tiếp tục") ->
phân tích bảng HTML hoặc đi tiếp sang trang lưu file.

Chạy từ thư mục gốc repo:
  python -E scripts/gso_pxweb_fetch.py <table_url> <out_html> [giữ_cột2.txt]

giữ_cột2.txt (tùy chọn): mỗi dòng một GIÁ TRỊ (text option) của listbox thứ 2
(thường là biến "Năm") — chỉ chọn các giá trị này thay vì chọn tất cả.

Chỉ đọc từ mạng và ghi file HTML thô vào data/raw/gso/; mọi chuẩn hóa ở script
khác. KHÔNG dùng cho đăng nhập/paywall — bảng GSO là dữ liệu công khai.
"""
from __future__ import annotations

import html as htmlmod
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-download"


def _unesc(s: str) -> str:
    return htmlmod.unescape(s)


def extract_fields(page: str) -> list[tuple[str, str]]:
    """Trích (name, value) cho input/select trong form ASP.NET."""
    fields: list[tuple[str, str]] = []
    for m in re.finditer(r"<input\b[^>]*>", page):
        tag = m.group(0)
        nm = re.search(r'name="([^"]*)"', tag)
        if not nm:
            continue
        name = _unesc(nm.group(1))
        ty = re.search(r'type="([^"]*)"', tag)
        typ = (ty.group(1).lower() if ty else "text")
        if typ in ("submit", "image", "button"):
            continue  # nút bấm: chỉ thêm khi chủ động kích
        val = re.search(r'value="([^"]*)"', tag)
        if typ == "checkbox" or typ == "radio":
            chk = re.search(r'checked="([^"]*)"', tag) or re.search(r"\bchecked\b", tag)
            if not chk:
                continue
        fields.append((name, _unesc(val.group(1)) if val else ""))
    for m in re.finditer(r'(?s)<select\b[^>]*name="([^"]*)"[^>]*>(.*?)</select>', page):
        name, body = _unesc(m.group(1)), m.group(2)
        opts = re.findall(r'(?s)<option\b([^>]*)>(.*?)</option>', body)
        if "cboSelectLanguages" in name:
            fields.append((name, "vi"))
            continue
        if "OutputFormatDropDownList" in name:
            continue  # để mặc định server-side
        sel = [_unesc(re.search(r'value="([^"]*)"', a).group(1)) if re.search(r'value="([^"]*)"', a) else _unesc(t.strip())
               for a, t in opts if "selected" in a]
        for v in sel:
            fields.append((name, v))
    return fields


def post(url: str, data: list[tuple[str, str]], opener) -> str:
    body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": url,
    }, method="POST")
    with opener.open(req, timeout=180) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    table_url, out_path = sys.argv[1], sys.argv[2]
    keep2: set[str] = set()
    if len(sys.argv) > 3:
        keep2 = {line.strip() for line in open(sys.argv[3], encoding="utf-8-sig") if line.strip()}
        print(f"[0] listbox #2 chỉ giữ {sorted(keep2)}")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    req = urllib.request.Request(table_url, headers={"User-Agent": UA})
    page1 = opener.open(req, timeout=120).read().decode("utf-8", errors="replace")
    fields = extract_fields(page1)
    print(f"[1] GET OK — {len(fields)} trường form gốc")

    # Đánh dấu chọn: mọi option của 2 listbox giá trị (mặc định chưa chọn gì)
    boxes = re.findall(
        r'(?s)<select[^>]*name="([^"]*ValuesListBox[^"]*)"[^>]*>(.*?)</select>', page1)
    select_data: list[tuple[str, str]] = []
    for bi, (name, body) in enumerate(boxes):
        for a, t in re.findall(r'(?s)<option\b([^>]*)>(.*?)</option>', body):
            vm = re.search(r'value="([^"]*)"', a)
            txt = _unesc(t.strip())
            v = _unesc(vm.group(1)) if vm else txt
            if bi == 1 and keep2 and txt not in keep2:
                continue
            select_data.append((_unesc(name), v))
    print(f"[2] chọn {len(select_data)} giá trị biến")

    trigger = "ctl00$ContentPlaceHolderMain$VariableSelector1$VariableSelector1$ButtonViewTable"
    payload = fields + select_data + [(trigger, "Tiếp tục")]
    page2 = post(table_url, payload, opener)
    print(f"[3] POST Tiếp tục — {len(page2)} bytes")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page2)
    print("Đã ghi:", out_path)
    # Gợi ý nhanh trang kế tiếp
    for pat in ("<table", "OutputFormat", "lưu", "Lưu", "Save"):
        print(f"    chứa {pat!r}: {pat in page2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
