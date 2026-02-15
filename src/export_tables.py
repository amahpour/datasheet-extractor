"""Table export helpers for JSON/CSV/Markdown artifacts."""

from __future__ import annotations

from pathlib import Path

from src.schema import Table
from src.utils import flatten_grid_rows, write_json


def grid_to_markdown(grid: list[list[str]]) -> str:
    """Render a rectangular-ish grid as GitHub-flavored Markdown table text."""
    if not grid:
        return ""
    header = grid[0]
    body = grid[1:] if len(grid) > 1 else []
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines) + "\n"


def export_table(table: Table, out_dir: Path) -> None:
    """Write all table artifact formats and annotate paths on the table object."""
    table_dir = out_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    json_path = table_dir / f"{table.id}.json"
    csv_path = table_dir / f"{table.id}.csv"
    md_path = table_dir / f"{table.id}.md"

    write_json(
        json_path, {"id": table.id, "grid": table.grid, "caption": table.caption}
    )
    csv_path.write_text(flatten_grid_rows(table.grid), encoding="utf-8")
    md_path.write_text(grid_to_markdown(table.grid), encoding="utf-8")

    table.json_path = str(json_path)
    table.csv_path = str(csv_path)
    table.markdown_path = str(md_path)
