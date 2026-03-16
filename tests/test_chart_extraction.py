"""Tests for Docling chart extraction integration in the pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from src.pipeline import process_pdf
from src.schema import Classification


def _make_minimal_pdf(path: Path) -> None:
    path.write_bytes(
        b"""%PDF-1.1
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 0 >>
stream
endstream
endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000061 00000 n
0000000120 00000 n
0000000204 00000 n
trailer
<< /Root 1 0 R /Size 5 >>
startxref
253
%%EOF
"""
    )


def _fake_extract(figures_dir: Path, chart_data: list[list[str]] | None, docling_cls: str):
    """Return a fake extract_document function for the given figure config."""

    def fake_extract_document(_pdf_path, out_dir=None, max_tokens=256, vlm_model=None):
        fdir = out_dir / "figures"
        fdir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (60, 60), color="white").save(fdir / "fig_0001.png")
        return {
            "page_count": 1,
            "blocks": [],
            "tables": [],
            "figures": [
                {
                    "id": "fig_0001",
                    "page": 1,
                    "bbox": [0.0, 0.0, 0.0, 0.0],
                    "caption": "",
                    "image_path": str(fdir / "fig_0001.png"),
                    "docling_classification": docling_cls,
                    "chart_data": chart_data or [],
                    "vlm_description": "",
                }
            ],
        }

    return fake_extract_document


def _noop_process_all_figures(figures_dir, processing_dir, ollama_model=None, force=False, figure_ids=None, pre_descriptions=None):
    """Stand-in that does nothing — real status files are pre-populated by the pipeline."""
    return []


def test_chart_figure_resolved_without_llm(monkeypatch, tmp_path: Path) -> None:
    """A figure with Docling chart data must be marked resolved_local before the LLM pass."""
    pdf_path = tmp_path / "sample.pdf"
    _make_minimal_pdf(pdf_path)
    out_root = tmp_path / "out"

    chart_data = [["x", "y"], ["0", "0.5"], ["1024", "1.0"], ["4095", "3.3"]]

    monkeypatch.setattr(
        "src.pipeline.extract_document",
        _fake_extract(tmp_path, chart_data, "bar_chart"),
    )
    monkeypatch.setattr("src.pipeline.process_all_figures", _noop_process_all_figures)

    process_pdf(pdf_path=pdf_path, out_root=out_root, force=True, no_tables=True)

    processing_file = out_root / "sample" / "processing" / "fig_0001.json"
    assert processing_file.exists(), "processing status file should be written"

    status = json.loads(processing_file.read_text())
    assert status["status"] == "resolved_local"
    assert status["stage"] == "docling_chart_extraction"
    assert status["needs_external"] is False
    assert status["confidence"] == 0.95
    # Description should embed the extracted data
    assert "bar_chart" in status["local_llm_description"]
    assert "4 rows" in status["local_llm_description"]


def test_chart_figure_classification_overrides_rules(monkeypatch, tmp_path: Path) -> None:
    """Docling's picture classification should take precedence over keyword rules."""
    pdf_path = tmp_path / "sample.pdf"
    _make_minimal_pdf(pdf_path)
    out_root = tmp_path / "out"

    monkeypatch.setattr(
        "src.pipeline.extract_document",
        _fake_extract(tmp_path, [["x", "y"], ["1", "2"]], "line_chart"),
    )
    monkeypatch.setattr("src.pipeline.process_all_figures", _noop_process_all_figures)
    # Rule-based classifier would return "other" for an empty caption
    monkeypatch.setattr(
        "src.pipeline.classify_figure",
        lambda _cap, _ctx: Classification(type="other", confidence=0.4, rationale="no rule matched"),
    )

    process_pdf(pdf_path=pdf_path, out_root=out_root, force=True, no_tables=True)

    doc = json.loads((out_root / "sample" / "document.json").read_text())
    fig = doc["figures"][0]
    assert fig["classification"]["type"] == "plot"
    assert fig["docling_classification"] == "line_chart"
    assert fig["chart_data"] == [["x", "y"], ["1", "2"]]


def test_non_chart_figure_unaffected(monkeypatch, tmp_path: Path) -> None:
    """A figure without chart_data must not get a pre-populated status file."""
    pdf_path = tmp_path / "sample.pdf"
    _make_minimal_pdf(pdf_path)
    out_root = tmp_path / "out"

    monkeypatch.setattr(
        "src.pipeline.extract_document",
        _fake_extract(tmp_path, [], "photograph"),
    )

    llm_called = []

    def tracking_process_all(figures_dir, processing_dir, ollama_model=None, force=False, figure_ids=None, pre_descriptions=None):
        llm_called.append(True)
        return []

    monkeypatch.setattr("src.pipeline.process_all_figures", tracking_process_all)

    process_pdf(pdf_path=pdf_path, out_root=out_root, force=True, no_tables=True)

    # The local LLM pass should still be invoked for non-chart figures
    assert llm_called, "process_all_figures should run for figures without chart data"

    # No pre-populated status file should exist (LLM pass would write it)
    processing_file = out_root / "sample" / "processing" / "fig_0001.json"
    assert not processing_file.exists()
