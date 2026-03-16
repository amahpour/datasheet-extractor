"""Tier 3 enrichment: send needs_external figures to a flagship model.

This is a standalone CLI that reads existing extraction output and lists
(or in the future, processes) figures that local models could not resolve.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich datasheet figures that need external LLM processing",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("./out"),
        help="Output directory from a prior datasheet-extract run (default: ./out)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    out_dir: Path = args.out
    if not out_dir.is_dir():
        print(f"Error: output directory not found: {out_dir}", file=sys.stderr)
        return 1

    # Collect all rollup files (per-PDF and global)
    rollup_paths = sorted(out_dir.glob("*/processing_rollup.json"))
    global_rollup = out_dir / "processing_rollup.json"
    if global_rollup.exists():
        rollup_paths.append(global_rollup)

    if not rollup_paths:
        print(f"Error: no processing_rollup.json found under {out_dir}", file=sys.stderr)
        return 1

    total_needs = 0
    for rollup_path in rollup_paths:
        rollup = json.loads(rollup_path.read_text(encoding="utf-8"))
        needs = rollup.get("figures", {}).get("needs_external", [])
        if not needs:
            continue

        label = rollup_path.parent.name
        logger.info("%s: %d figure(s) need external processing:", label, len(needs))
        for fig in needs:
            logger.info(
                "  %s → %s [%s]",
                fig["id"],
                fig.get("image_path", ""),
                fig.get("classification", ""),
            )
        total_needs += len(needs)

    if total_needs == 0:
        logger.info("All figures are already resolved — nothing to enrich.")
    else:
        logger.info(
            "Total: %d figure(s) across %d PDF(s) need external processing.",
            total_needs,
            len([p for p in rollup_paths
                 if json.loads(p.read_text(encoding="utf-8"))
                 .get("figures", {}).get("needs_external")]),
        )
        logger.info("Hint: use prompts/figure_analysis.md as the prompt template.")
        logger.info("Future: this command will call Claude API / OpenAI API to resolve them.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
