from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.extract_docling import DEFAULT_MAX_TOKENS
from src.local_processor import detect_ollama_model_for_tier
from src.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# Default Ollama models per tier
_TIER_DEFAULTS: dict[int, str] = {
    1: "moondream:latest",
    2: "qwen2.5vl:7b",
}


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
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help=(
            "Extraction tier: "
            "1=fast local (moondream, no chart extraction), "
            "2=enriched local (qwen + Docling chart extraction + VLM descriptions), "
            "3=enrich existing output with external model (default: 1)"
        ),
    )
    parser.add_argument(
        "--ollama-model",
        default=None,
        help=(
            "Override the Ollama vision model for figure processing. "
            "Default depends on tier: moondream:latest (tier 1), qwen2.5vl:7b (tier 2)."
        ),
    )
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"Max tokens per text block chunk (default: {DEFAULT_MAX_TOKENS})")
    return parser


def _run_enrich(out_dir: Path) -> int:
    """Tier 3: read existing rollup and list figures that need external processing."""
    rollup_paths = sorted(out_dir.glob("*/processing_rollup.json"))
    if not rollup_paths:
        global_rollup = out_dir / "processing_rollup.json"
        if global_rollup.exists():
            rollup_paths = [global_rollup]

    if not rollup_paths:
        print(f"Error: no processing_rollup.json found under {out_dir}", file=sys.stderr)
        return 1

    total_needs = 0
    for rollup_path in rollup_paths:
        rollup = json.loads(rollup_path.read_text(encoding="utf-8"))
        needs = rollup.get("figures", {}).get("needs_external", [])
        if needs:
            logger.info("%s: %d figure(s) need external processing", rollup_path.parent.name, len(needs))
            for fig in needs:
                logger.info("  %s → %s [%s]", fig["id"], fig.get("image_path", ""), fig.get("classification", ""))
            total_needs += len(needs)

    if total_needs == 0:
        logger.info("All figures are already resolved — nothing to enrich.")
    else:
        logger.info(
            "Total: %d figure(s) across %d PDF(s) need external processing.",
            total_needs,
            len(rollup_paths),
        )
        logger.info("Hint: use prompts/figure_analysis.md as the prompt template.")

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # Tier 3: enrichment pass on existing output
    if args.tier == 3:
        return _run_enrich(args.out)

    # Resolve ollama model: explicit override > auto-detect for tier > tier default
    ollama_model = args.ollama_model
    if ollama_model is None:
        detected = detect_ollama_model_for_tier(args.tier)
        if detected:
            ollama_model = detected
            logger.info("Auto-detected Ollama model for tier %d: %s", args.tier, ollama_model)
        else:
            ollama_model = _TIER_DEFAULTS.get(args.tier)
            logger.info("Using default Ollama model for tier %d: %s", args.tier, ollama_model)

    do_chart_extraction = args.tier >= 2

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
        ollama_model=ollama_model,
        max_tokens=args.max_tokens,
        do_chart_extraction=do_chart_extraction,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
