from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.schema import Block
from src.utils import deterministic_id

logger = logging.getLogger(__name__)


def _extract_with_docling(pdf_path: Path) -> dict[str, Any]:
    from docling.document_converter import DocumentConverter  # type: ignore

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    blocks: list[dict[str, Any]] = []
    page_count = getattr(doc, "num_pages", 0) or len(getattr(doc, "pages", []))
    for i, page in enumerate(getattr(doc, "pages", []), start=1):
        text = ""
        if hasattr(page, "text"):
            text = str(page.text)
        blocks.append({"page": i, "text": text, "bbox": [0.0, 0.0, 0.0, 0.0], "type": "text"})
    if not blocks and hasattr(doc, "export_to_markdown"):
        md = doc.export_to_markdown()
        blocks = [{"page": 1, "text": md, "bbox": [0.0, 0.0, 0.0, 0.0], "type": "text"}]
        page_count = max(page_count, 1)

    return {"page_count": page_count, "blocks": blocks, "tables": [], "figures": []}


def _extract_with_pypdf(pdf_path: Path) -> dict[str, Any]:
    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(str(pdf_path))
    blocks: list[dict[str, Any]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        blocks.append({"page": i, "text": text, "bbox": [0.0, 0.0, 0.0, 0.0], "type": "text"})
    return {"page_count": len(reader.pages), "blocks": blocks, "tables": [], "figures": []}


def extract_document(pdf_path: Path) -> dict[str, Any]:
    try:
        return _extract_with_docling(pdf_path)
    except Exception as exc:
        logger.warning("Docling extraction failed for %s; falling back to pypdf: %s", pdf_path, exc)
        return _extract_with_pypdf(pdf_path)


def synthesize_placeholder_figure(fig_path: Path, caption: str) -> None:
    img = Image.new("RGB", (600, 350), color=(248, 248, 248))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), f"Placeholder figure\n{caption[:120]}", fill=(0, 0, 0))
    img.save(fig_path)


def to_blocks(raw_blocks: list[dict[str, Any]]) -> list[Block]:
    blocks: list[Block] = []
    for i, raw in enumerate(raw_blocks, start=1):
        blocks.append(
            Block(
                id=deterministic_id("blk", i),
                type=raw.get("type", "text"),
                page=int(raw.get("page", 1)),
                bbox=[float(x) for x in raw.get("bbox", [0, 0, 0, 0])],
                text=str(raw.get("text", "")),
            )
        )
    return blocks
