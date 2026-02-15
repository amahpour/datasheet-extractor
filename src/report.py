"""Manual follow-up report generation for extracted figures."""

from __future__ import annotations

from pathlib import Path

from src.schema import Figure
from src.utils import write_json


def _recommend_action(figure: Figure) -> tuple[str, str, float]:
    """Suggest whether a figure needs external/manual interpretation."""
    fig_type = figure.classification.type
    if fig_type == "plot":
        return (
            "LLM: convert plot to CSV",
            "plot digitization requires semantic understanding",
            0.8,
        )
    if fig_type in {"block_diagram", "state_machine", "timing_diagram"}:
        return (
            "LLM: convert diagram to ASCII/Mermaid",
            "diagram interpretation is not reliable locally",
            0.8,
        )
    if figure.derived.description.notes == "LLM recommended":
        return "LLM: describe image", "insufficient local text extraction", 0.7
    return "none", "local extraction sufficient", 0.6


def build_figure_report_entry(figure: Figure) -> dict:
    """Convert a figure object into a report entry dict."""
    action, reason, confidence = _recommend_action(figure)
    return {
        "figure_id": figure.id,
        "page": figure.page,
        "caption": figure.caption,
        "tags": figure.tags,
        "image_path": figure.image_path,
        "classification": figure.classification.model_dump(),
        "recommended_manual_action": action,
        "reason": reason,
        "confidence": confidence,
    }


def write_manual_report(figures: list[Figure], out_dir: Path) -> dict:
    """Write manual-processing report in JSON and Markdown formats."""
    entries = [build_figure_report_entry(f) for f in figures]
    report = {"figures": entries}
    write_json(out_dir / "manual_processing_report.json", report)

    lines = ["# Manual Processing Report", ""]
    if not entries:
        lines.append("No figures requiring manual follow-up.")
    for entry in entries:
        lines.extend(
            [
                f"## {entry['figure_id']}",
                f"- page: {entry['page']}",
                f"- caption: {entry['caption']}",
                f"- image_path: {entry['image_path']}",
                f"- classification: {entry['classification']['type']} ({entry['classification']['confidence']})",
                f"- recommended_manual_action: {entry['recommended_manual_action']}",
                f"- reason: {entry['reason']}",
                "",
            ]
        )
    (out_dir / "manual_processing_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return report
