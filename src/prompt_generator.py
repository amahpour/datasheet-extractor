"""Generate a one-shot markdown prompt for external LLM figure analysis.

After Moondream processes all figures, this module collects the ones that
fell below the confidence threshold and produces a self-contained markdown
file.  The prompt includes absolute image paths so it can be handed directly
to Claude, Codex, or any vision-capable agent.

Images are grouped into batches of ``BATCH_SIZE`` with explicit instructions
to report progress between batches and to maximise parallel subagent usage.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BATCH_SIZE = 20


def _load_needs_external(processing_dir: Path) -> list[dict]:
    """Return status dicts for every figure that still needs external analysis."""
    results = []
    for p in sorted(processing_dir.glob("fig_*.json")):
        status = json.loads(p.read_text(encoding="utf-8"))
        if status.get("status") == "needs_external":
            results.append(status)
    return results


def _figure_block(status: dict, analysis_dir: Path) -> str:
    """Render a single figure entry inside the prompt."""
    fig_id = status["figure_id"]
    abs_path = str(Path(status["image_path"]).resolve())
    local_cls = status.get("local_llm_classification", "unknown")
    local_desc = status.get("local_llm_description", "").strip()
    confidence = status.get("confidence", 0.0)
    output_path = analysis_dir / "derived" / "figures" / fig_id / "llm_analysis.json"

    lines = [
        f"### {fig_id}",
        "",
        f"- **Image:** `{abs_path}`",
        f"- **Moondream classification:** `{local_cls}` (confidence {confidence:.2f})",
    ]
    if local_desc:
        lines.append(f"- **Moondream description:** {local_desc[:120]}")
    lines.append(f"- **Save analysis to:** `{output_path}`")
    lines.append("")
    return "\n".join(lines)


def generate_prompt(
    processing_dir: Path,
    analysis_dir: Path,
    prompt_template_path: Path | None = None,
) -> str | None:
    """Build the full markdown prompt text.

    Returns ``None`` if there are no figures needing external analysis.
    """
    figures = _load_needs_external(processing_dir)
    if not figures:
        logger.info("No figures need external analysis — skipping prompt generation.")
        return None

    total = len(figures)
    batches: list[list[dict]] = []
    for i in range(0, total, BATCH_SIZE):
        batches.append(figures[i : i + BATCH_SIZE])

    # Read the analysis prompt template if available.
    template_section = ""
    if prompt_template_path and prompt_template_path.exists():
        template_section = prompt_template_path.read_text(encoding="utf-8")

    lines: list[str] = []

    # --- Header ---
    lines.extend([
        "# External Figure Analysis Prompt",
        "",
        f"**Total figures requiring analysis:** {total}",
        f"**Batch size:** {BATCH_SIZE}",
        f"**Number of batches:** {len(batches)}",
        "",
        "---",
        "",
        "## Instructions",
        "",
        "You are analysing figures extracted from an electronics datasheet.",
        "Each figure below includes an absolute path to its image file.",
        "",
        "### Workflow",
        "",
        "1. **Process figures in batches of 20.** Each batch is clearly marked below.",
        "2. **Maximise parallelism.** Use subagents / parallel tool calls to process",
        "   as many images concurrently as possible within each batch.  Do NOT",
        "   process images sequentially when they can be handled in parallel.",
        "3. **After completing each batch**, print a short status update:",
        "   ```",
        "   === Batch N/M complete — X figures analysed, Y remaining ===",
        "   ```",
        "4. For every figure, read the image at the absolute path provided and",
        "   produce a JSON analysis object following the schema below.",
        "5. Save each analysis to the output path listed under the figure.",
        "",
        "---",
        "",
    ])

    # --- Analysis schema (inline from template or embedded) ---
    if template_section:
        lines.extend([
            "## Analysis Schema",
            "",
            template_section,
            "",
            "---",
            "",
        ])

    # --- Batches ---
    for batch_idx, batch in enumerate(batches, start=1):
        lines.extend([
            f"## Batch {batch_idx} of {len(batches)}  ({len(batch)} figures)",
            "",
        ])
        for status in batch:
            lines.append(_figure_block(status, analysis_dir))

        lines.extend([
            f"**After completing batch {batch_idx}:** print status update before continuing.",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def write_prompt(
    processing_dir: Path,
    analysis_dir: Path,
    output_path: Path,
    prompt_template_path: Path | None = None,
) -> Path | None:
    """Generate the prompt and write it to ``output_path``.

    Returns the path written, or ``None`` if no figures need processing.
    """
    text = generate_prompt(
        processing_dir,
        analysis_dir,
        prompt_template_path=prompt_template_path,
    )
    if text is None:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    logger.info("Wrote external analysis prompt to %s", output_path)
    return output_path
