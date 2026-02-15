from __future__ import annotations

"""Shared utility helpers used across the extraction pipeline."""

import hashlib
import json
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def deterministic_id(prefix: str, index: int) -> str:
    """Build a stable, sortable ID like ``fig_0001``."""
    return f"{prefix}_{index:04d}"


def ensure_dir(path: Path) -> Path:
    """Create a directory (including parents) and return the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict | list) -> None:
    """Serialize a dict/list to UTF-8 JSON with indentation."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_page_ranges(spec: str | None) -> set[int] | None:
    """Parse a page-range string like ``1,3-5`` into a set of page numbers."""
    if not spec:
        return None
    pages: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start, end = token.split("-", 1)
            for page in range(int(start), int(end) + 1):
                pages.add(page)
        else:
            pages.add(int(token))
    return pages


def relpath(path: Path, base: Path) -> str:
    """Return ``path`` relative to ``base`` using resolved absolute paths."""
    return str(path.resolve().relative_to(base.resolve()))


def csv_escape(value: str) -> str:
    """Escape a CSV field following standard quote-doubling behavior."""
    if any(ch in value for ch in [",", "\n", '"']):
        return '"' + value.replace('"', '""') + '"'
    return value


def flatten_grid_rows(grid: Iterable[Iterable[str]]) -> str:
    """Convert a table grid into CSV text."""
    lines = []
    for row in grid:
        lines.append(",".join(csv_escape(str(cell)) for cell in row))
    return "\n".join(lines) + ("\n" if lines else "")
