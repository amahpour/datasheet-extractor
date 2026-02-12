from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from src.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end smoke test")
    parser.add_argument("--input", type=Path, default=Path("./examples"))
    parser.add_argument("--out", type=Path, default=Path("./out"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    run_pipeline(input_dir=args.input, out_dir=args.out, force=True)

    pdfs = sorted(args.input.glob("*.pdf"))
    if not pdfs:
        nested = sorted(args.input.glob("**/*.pdf"))
        pdfs = nested
    failures: list[str] = []
    for pdf in pdfs:
        doc_dir = args.out / pdf.stem
        document_json = doc_dir / "document.json"
        index_json = doc_dir / "index.json"
        if not document_json.exists():
            failures.append(f"missing {document_json}")
            continue
        if not index_json.exists():
            failures.append(f"missing {index_json}")
            continue
        payload = json.loads(document_json.read_text(encoding="utf-8"))
        stats = payload.get("doc_stats", {})
        if stats.get("block_count", 0) + stats.get("table_count", 0) + stats.get("figure_count", 0) <= 0:
            failures.append(f"empty extraction for {pdf}")
        if stats.get("figure_count", 0) > 0 and not list((doc_dir / "figures").glob("fig_*.png")):
            failures.append(f"figures missing png for {pdf}")
        if stats.get("table_count", 0) > 0 and not list((doc_dir / "tables").glob("table_*.md")):
            failures.append(f"tables missing md for {pdf}")

    if failures:
        for failure in failures:
            logging.error(failure)
        return 1
    logging.info("Smoke test passed for %s PDFs", len(pdfs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
