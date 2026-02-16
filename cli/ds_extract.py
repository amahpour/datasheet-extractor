from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.extract_docling import DEFAULT_MAX_TOKENS
from src.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Datasheet PDF extractor")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="Path to a single PDF file")
    source.add_argument("--dir", type=Path, help="Directory containing PDF files")

    parser.add_argument("--out", type=Path, default=Path("./out"))
    parser.add_argument("--glob", dest="glob_pattern", default="*.pdf")
    parser.add_argument("--pages", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-images", action="store_true")
    parser.add_argument("--no-tables", action="store_true")
    parser.add_argument(
        "--max-figures",
        type=int,
        default=None,
        help="Maximum number of figures to process (default: no limit)",
    )
    parser.add_argument("--ollama-model", default=None,
                        help="Ollama vision model for local figure processing (auto-detected if omitted)")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"Max tokens per text block chunk (default: {DEFAULT_MAX_TOKENS})")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.file:
        pdf = args.file.resolve()
        if not pdf.is_file():
            print(f"Error: file not found: {pdf}", file=sys.stderr)
            return 1
        input_dir = pdf.parent
        glob_pattern = pdf.name
    else:
        input_dir = args.dir.resolve()
        glob_pattern = args.glob_pattern
        if not input_dir.is_dir():
            print(f"Error: directory not found: {input_dir}", file=sys.stderr)
            return 1

    run_pipeline(
        input_dir=input_dir,
        out_dir=args.out,
        pattern=glob_pattern,
        pages=args.pages,
        force=args.force,
        no_images=args.no_images,
        no_tables=args.no_tables,
        max_figures=args.max_figures,
        ollama_model=args.ollama_model,
        max_tokens=args.max_tokens,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
