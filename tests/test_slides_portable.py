"""Keep the reviewed presentation reproducible without silently stale evidence."""
from __future__ import annotations

import json

import pytest

from scripts.deliverables.build_slides import build_evidence
from scripts.deliverables import slides_portable


def test_portable_deck_matches_recomputed_evidence_and_reviewed_pptx(tmp_path):
    output = tmp_path / "slides.pptx"
    slides_portable.export_slides(build_evidence(), output)
    canonical = slides_portable.ROOT / "slides/Nhom15_STING_PAPI.pptx"
    assert output.read_bytes() == canonical.read_bytes()


def test_portable_deck_rejects_changed_evidence_without_overwriting_output(tmp_path):
    evidence = json.loads(slides_portable.SNAPSHOT.read_text(encoding="utf-8"))["evidence"]
    evidence["reference_n"] += 1
    output = tmp_path / "slides.pptx"
    output.write_bytes(b"previous reviewed version")
    with pytest.raises(ValueError, match="Dữ liệu slide đã thay đổi"):
        slides_portable.export_slides(evidence, output)
    assert output.read_bytes() == b"previous reviewed version"


def test_portable_deck_rejects_changed_authoring_source(tmp_path, monkeypatch):
    evidence = json.loads(slides_portable.SNAPSHOT.read_text(encoding="utf-8"))["evidence"]
    changed_source = tmp_path / "build_slides.mjs"
    changed_source.write_text("// changed layout", encoding="utf-8")
    monkeypatch.setattr(slides_portable, "AUTHORING_SOURCE", changed_source)
    with pytest.raises(ValueError, match="Nguồn bố cục đã thay đổi"):
        slides_portable.export_slides(evidence, tmp_path / "slides.pptx")
