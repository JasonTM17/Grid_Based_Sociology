"""Kiểm tra mọi tham chiếu `path:line` trong các file Q&A của repo.

Hai kiểu tham chiếu được hiểu:
- khối ``(nguồn: path:line; path:line)`` — qa_final.md, qa_midterm.md;
- dòng ``- **Repo:** `path:line`; `path:line` `` — qa_course_concepts.md.

Chạy từ thư mục gốc repo: python scripts/check_qa_sources.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QA_FILES = [
    ROOT / "reports" / "qa_final.md",
    ROOT / "reports" / "qa_midterm.md",
    ROOT / "reports" / "qa_course_concepts.md",
]

REF_RE = re.compile(r"\(nguồn:\s*([^)]+)\)", re.IGNORECASE)
REPO_LINE_RE = re.compile(r"\*\*Repo:\*\*\s*(.+)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
SPLIT_RE = re.compile(r"\s*;\s*")


def line_count(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def resolve_glob(pattern: str) -> list[Path]:
    if "*" not in pattern:
        return [ROOT / pattern.replace("\\", "/")]
    return sorted(ROOT.glob(pattern.replace("\\", "/")))


def _check_file_line(path_part: str, loc: str) -> tuple[bool, str]:
    path_part = path_part.replace("\\", "/")
    path = ROOT / path_part
    if not path.is_file():
        return False, f"không tồn tại: {path_part}"
    n = line_count(path)
    loc = loc.strip()
    if "-" in loc and loc.replace("-", "").isdigit() is False:
        # dạng start-end số
        if loc.count("-") == 1 and all(p.isdigit() for p in loc.split("-", 1)):
            start_s, end_s = loc.split("-", 1)
            start, end = int(start_s), int(end_s)
            if end > n:
                return False, f"{path_part} chỉ có {n} dòng, cần tới {end}"
            if start < 1:
                return False, f"dòng bắt đầu {start} < 1"
            return True, f"OK dòng {start}-{end} / {n}"
    if "-" in loc:
        parts = loc.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            if end > n:
                return False, f"{path_part} chỉ có {n} dòng, cần tới {end}"
            return True, f"OK dòng {start}-{end} / {n}"
    if loc.isdigit():
        line_no = int(loc)
        if line_no > n:
            return False, f"{path_part} chỉ có {n} dòng, cần {line_no}"
        return True, f"OK dòng {line_no} / {n}"
    return False, f"dòng không hợp lệ: {loc}"


def check_ref(ref: str) -> tuple[bool, str]:
    ref = ref.strip().strip("`")
    if not ref:
        return False, "tham chiếu rỗng"

    if "*" in ref and ":" not in ref.split("/")[-1]:
        paths = resolve_glob(ref)
        if not paths:
            return False, f"glob không khớp: {ref}"
        return True, f"OK ({len(paths)} file)"

    if ":" in ref:
        path_part, loc = ref.rsplit(":", 1)
        # cùng file, nhiều vị trí: app.py:91-104, 376-378, 604
        if "," in loc:
            bits = [b.strip() for b in loc.split(",")]
            msgs = []
            for bit in bits:
                ok, msg = _check_file_line(path_part, bit)
                if not ok:
                    return False, msg
                msgs.append(bit)
            return True, f"OK {path_part}: " + ", ".join(msgs)
        return _check_file_line(path_part, loc)

    path_part = ref.replace("\\", "/")
    path = ROOT / path_part
    if path.is_file():
        return True, f"OK file ({line_count(path)} dòng)"
    return False, f"không tồn tại: {path_part}"


def source_refs(text: str) -> tuple[list[str], list[str]]:
    """Tham chiếu nguồn trong một file Q&A, theo cả hai kiểu ghi.

    Trả về ``(refs, dòng_hỏng)``: dòng "Repo" không có tham chiếu trong dấu
    backtick bị coi là hỏng thay vì bị bỏ qua im lặng.
    """
    refs = []
    broken = []
    for block in REF_RE.findall(text):
        refs.extend(SPLIT_RE.split(block))
    for line in REPO_LINE_RE.findall(text):
        found = BACKTICK_RE.findall(line)
        if not found:
            broken.append(line.strip())
        refs.extend(found)
    return [ref.strip() for ref in refs if ref.strip()], broken


def main() -> int:
    errors: list[str] = []
    checked = 0
    for qa in QA_FILES:
        text = qa.read_text(encoding="utf-8")
        refs, broken_lines = source_refs(text)
        for line in broken_lines:
            errors.append(f"{qa.name}: dòng Repo thiếu `path:line` — {line}")
        n_file = 0
        for ref in refs:
            checked += 1
            n_file += 1
            ok, msg = check_ref(ref)
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {qa.name} :: {ref} -> {msg}")
            if not ok:
                errors.append(f"{qa.name}: {ref} — {msg}")
        print(f"[file] {qa.name}: {n_file} tham chiếu")
        if n_file == 0:
            errors.append(f"{qa.name}: không tìm thấy tham chiếu nguồn nào")

    print(f"\nTổng tham chiếu: {checked}, lỗi: {len(errors)}")
    if errors:
        for e in errors:
            print("  !", e)
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
