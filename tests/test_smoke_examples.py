from __future__ import annotations

import json
from pathlib import Path

from src.pipeline import run_pipeline


def test_examples_integration(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    examples = repo_root / "examples"
    out_dir = tmp_path / "out"

    run_pipeline(input_dir=examples, out_dir=out_dir, pattern="**/*.pdf", force=True)

    pdfs = sorted(examples.glob("**/*.pdf"))
    assert pdfs
    for pdf in pdfs:
        doc_dir = out_dir / pdf.stem
        assert (doc_dir / "document.json").exists()
        assert (doc_dir / "index.json").exists()

        payload = json.loads((doc_dir / "document.json").read_text(encoding="utf-8"))
        stats = payload["doc_stats"]
        assert stats["block_count"] > 0 or stats["table_count"] > 0 or stats["figure_count"] > 0
        if stats["figure_count"] > 0:
            assert list((doc_dir / "figures").glob("fig_*.png"))
        if stats["table_count"] > 0:
            assert list((doc_dir / "tables").glob("table_*.md"))
