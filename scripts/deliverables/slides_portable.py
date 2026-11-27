"""Reproduce a reviewed PPTX snapshot without an optional slide-authoring runtime.

The source presentation remains fully editable in PowerPoint. This exporter
checks the recomputed evidence and authoring source against the reviewed snapshot
before copying it. It deliberately refuses to reuse a deck after its evidence or
layout source changes. Use the Artifact authoring engine and visually review the
new deck before freezing another snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import zipfile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "assets/sting_papi_slides_template.pptx"
SNAPSHOT = ROOT / "assets/sting_papi_slides_evidence.json"
AUTHORING_SOURCE = ROOT / "scripts/deliverables/build_slides.mjs"


def _normalized(value):
    """Ignore sub-display floating point roundoff across supported platforms."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Slide evidence contains a non-finite number")
        return round(value, 10)
    if isinstance(value, dict):
        return {key: _normalized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    return value


def evidence_digest(evidence: dict) -> str:
    content = json.dumps(
        _normalized(evidence), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slide_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        xml = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
    ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
    return len(xml.findall("p:sldIdLst/p:sldId", ns))


def freeze_template(source: Path, evidence: dict) -> None:
    """Record a snapshot after the caller has completed visual review."""
    if _slide_count(source) != evidence["slide_count"]:
        raise ValueError("Số trang PPTX không khớp dữ liệu đã kiểm tra")
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != TEMPLATE.resolve():
        shutil.copyfile(source, TEMPLATE)
    snapshot = {
        "schema_version": 1,
        "slide_count": evidence["slide_count"],
        "evidence_sha256": evidence_digest(evidence),
        "template_sha256": _file_digest(TEMPLATE),
        "authoring_source_sha256": _file_digest(AUTHORING_SOURCE),
        "evidence": _normalized(evidence),
    }
    SNAPSHOT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def export_slides(evidence: dict, output_path: Path) -> Path:
    """Export only when the frozen presentation still matches its evidence."""
    if not TEMPLATE.is_file() or not SNAPSHOT.is_file():
        raise ValueError("Thiếu mẫu slide đã duyệt; dựng bằng --engine artifact trước")
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1:
        raise ValueError("Phiên bản mẫu slide không được hỗ trợ")
    if evidence_digest(evidence) != snapshot["evidence_sha256"]:
        raise ValueError(
            "Dữ liệu slide đã thay đổi. Dựng lại bằng --engine artifact, kiểm tra "
            "bố cục rồi cập nhật mẫu; không xuất bản số liệu cũ."
        )
    if _file_digest(AUTHORING_SOURCE) != snapshot["authoring_source_sha256"]:
        raise ValueError(
            "Nguồn bố cục đã thay đổi. Dùng --engine artifact và duyệt lại trước khi xuất."
        )
    if _file_digest(TEMPLATE) != snapshot["template_sha256"]:
        raise ValueError("Mẫu PPTX không khớp checksum đã lưu")
    if _slide_count(TEMPLATE) != evidence["slide_count"]:
        raise ValueError("Số trang của mẫu không khớp dữ liệu")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.resolve() != TEMPLATE.resolve():
        shutil.copyfile(TEMPLATE, output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--freeze", type=Path, required=True,
        help="PPTX vừa được dựng và đã kiểm tra trực quan để lưu làm mẫu",
    )
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    from scripts.deliverables.build_slides import build_evidence

    freeze_template(args.freeze, build_evidence())
    print(f"Đã lưu mẫu slide và dữ liệu kiểm chứng: {TEMPLATE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
