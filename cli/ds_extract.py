from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Datasheet PDF extractor")
    parser.add_argument("--input", type=Path, default=Path("./examples"))
    parser.add_argument("--out", type=Path, default=Path("./out"))
    parser.add_argument("--glob", dest="glob_pattern", default="*.pdf")
    parser.add_argument("--pages", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-images", action="store_true")
    parser.add_argument("--no-tables", action="store_true")
    parser.add_argument("--ocr", choices=["off", "on", "auto"], default="off")
    parser.add_argument("--max-figures", type=int, default=25)
    parser.add_argument("--ollama-model", default=None,
                        help="Ollama vision model for local figure processing (auto-detected if omitted)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    run_pipeline(
        input_dir=args.input,
        out_dir=args.out,
        pattern=args.glob_pattern,
        pages=args.pages,
        force=args.force,
        no_images=args.no_images,
        no_tables=args.no_tables,
        ocr=args.ocr,
        max_figures=args.max_figures,
        ollama_model=args.ollama_model,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
