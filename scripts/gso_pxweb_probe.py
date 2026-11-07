"""Tiện ích thăm dò PX-Web API của Tổng cục Thống kê (pxweb.nso.gov.vn).

Dùng nội bộ trong phiên tải dữ liệu GSO: liệt kê cây danh mục bảng, lấy
metadata bảng, và POST query lấy dữ liệu. KHÔNG ghi file dữ liệu — chỉ in ra
stdout để người vận hành đọc, hoặc tải về data/raw/gso/ khi dùng chế độ dump.

Chạy từ thư mục gốc repo:  python -E scripts/gso_pxweb_probe.py <lệnh> ...
Lệnh:
  tree <dbid...>            — liệt kê bảng trong 1..n database
  root                      — liệt kê database gốc
  meta <dbid> <tableid>     — metadata (các biến, giá trị) của bảng
  data <dbid> <tableid> <json_query_file> [out.xlsx]  — POST query
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

BASE = "https://pxweb.nso.gov.vn/api/v1/vi"


def enc(path: str) -> str:
    return urllib.parse.quote(path, safe="")


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research-download"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def post_json(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"User-Agent": "Mozilla/5.0 research-download", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    cmd = sys.argv[1]
    if cmd == "root":
        d = json.loads(get(f"{BASE}/"))
        for x in d:
            print(x.get("dbid"), "|", x.get("text"), "|", x.get("type"))
        return 0
    if cmd == "tree":
        dbid = " ".join(sys.argv[2:])
        d = json.loads(get(f"{BASE}/{enc(dbid)}/"))
        for x in d:
            print(x.get("id"), "|", x.get("text"), "|", x.get("type"))
        return 0
    if cmd == "meta":
        dbid, tid = sys.argv[2], sys.argv[3]
        d = json.loads(get(f"{BASE}/{enc(dbid)}/{enc(tid)}.px"))
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0
    if cmd == "data":
        dbid, tid, qfile = sys.argv[2], sys.argv[3], sys.argv[4]
        q = json.loads(open(qfile, encoding="utf-8").read())
        url = f"{BASE}/{enc(dbid)}/{enc(tid)}.px"
        out = sys.argv[5] if len(sys.argv) > 5 else None
        blob = post_json(url, q)
        if out:
            with open(out, "wb") as f:
                f.write(blob)
            print(f"Đã ghi {len(blob)} bytes -> {out}")
        else:
            sys.stdout.buffer.write(blob[:2000])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
