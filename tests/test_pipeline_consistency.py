from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from src.pipeline import process_pdf
from src.schema import Classification


def _make_minimal_pdf(path: Path) -> None:
    # Minimal valid PDF bytes for a single blank page.
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


def test_local_llm_classification_is_canonical(monkeypatch, tmp_path: Path) -> None:
    """Ensure local LLM classification always overrides pre-LLM rule labels."""
    pdf_path = tmp_path / "sample.pdf"
    _make_minimal_pdf(pdf_path)
    out_root = tmp_path / "out"

    # Pretend extraction produced one figure with a non-"other" rule label.
    def fake_extract_document(_pdf_path, out_dir=None, max_tokens=256):
        assert out_dir is not None
        figures_dir = out_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (60, 60), color="white").save(figures_dir / "fig_0001.png")
        return {
            "page_count": 1,
            "blocks": [
                {
                    "page": 1,
                    "text": "state machine description",
                    "enriched_text": "state machine description",
                    "headings": [],
                    "bbox": [0.0, 0.0, 0.0, 0.0],
                    "type": "text",
                }
            ],
            "tables": [],
            "figures": [
                {
                    "id": "fig_0001",
                    "page": 1,
                    "bbox": [0.0, 0.0, 0.0, 0.0],
                    "caption": "",
                    "image_path": str(figures_dir / "fig_0001.png"),
                }
            ],
        }

    def fake_classify_figure(_caption, _context):
        return Classification(
            type="state_machine",
            confidence=0.88,
            rationale="caption mentions state",
        )

    def fake_process_all_figures(
        figures_dir,
        processing_dir,
        ollama_model=None,
        force=False,
        figure_ids=None,
    ):
        statuses = [
            {
                "figure_id": "fig_0001",
                "image_path": str(figures_dir / "fig_0001.png"),
                "status": "resolved_local",
                "stage": "local_llm",
                "local_llm_description": "A simple TI logo image.",
                "local_llm_classification": "logo",
                "external_llm_result": None,
                "needs_external": False,
                "confidence": 0.7,
                "processed_at": "2026-02-16T00:00:00Z",
            }
        ]
        processing_dir.mkdir(parents=True, exist_ok=True)
        (processing_dir / "fig_0001.json").write_text(
            json.dumps(statuses[0], indent=2), encoding="utf-8"
        )
        return statuses

    monkeypatch.setattr("src.pipeline.extract_document", fake_extract_document)
    monkeypatch.setattr("src.pipeline.classify_figure", fake_classify_figure)
    monkeypatch.setattr("src.pipeline.process_all_figures", fake_process_all_figures)

    process_pdf(
        pdf_path=pdf_path,
        out_root=out_root,
        force=True,
        no_images=False,
        no_tables=True,
    )

    doc = json.loads((out_root / "sample" / "document.json").read_text(encoding="utf-8"))
    manual = json.loads(
        (out_root / "sample" / "manual_processing_report.json").read_text(
            encoding="utf-8"
        )
    )
    rollup = json.loads(
        (out_root / "sample" / "processing_rollup.json").read_text(encoding="utf-8")
    )

    assert doc["figures"][0]["classification"]["type"] == "logo"
    assert doc["figures"][0]["classification"]["rationale"] == "local_llm classification"

    assert manual["figures"][0]["classification"]["type"] == "logo"
    assert manual["figures"][0]["classification"]["rationale"] == "local_llm classification"

    # Same figure must agree across manual report and rollup.
    rollup_cls = rollup["figures"]["resolved_local"][0]["classification"]
    assert manual["figures"][0]["classification"]["type"] == rollup_cls
