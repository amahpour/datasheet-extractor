"""Document extraction adapters.

This module prefers Docling for rich extraction and falls back to pypdf for
text-only extraction when Docling is unavailable or fails.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.schema import Block
from src.utils import deterministic_id

logger = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0

# Dimensions for placeholder images when extraction fails.
PLACEHOLDER_WIDTH = 600
PLACEHOLDER_HEIGHT = 350
PLACEHOLDER_CAPTION_MAX = 120


def _extract_with_docling(
    pdf_path: Path, out_dir: Path | None = None
) -> dict[str, Any]:
    """Extract text, tables, and figures from a PDF using Docling.

    When *out_dir* is provided, extracted figure images are saved there and
    their paths are included in the returned dict.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import PictureItem, TableItem

    # Configure pipeline to generate images for pictures (and optionally pages)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    conv_res = converter.convert(str(pdf_path))
    doc = conv_res.document

    # --- page count ---
    pc = getattr(doc, "num_pages", None)
    if callable(pc):
        page_count = int(pc())
    elif isinstance(pc, int):
        page_count = pc
    else:
        page_count = len(getattr(doc, "pages", {})) or 1

    # --- text blocks (markdown) ---
    blocks: list[dict[str, Any]] = []
    if hasattr(doc, "export_to_markdown"):
        md = doc.export_to_markdown()
        if md and md.strip():
            blocks.append(
                {
                    "page": 1,
                    "text": md.strip(),
                    "bbox": [0.0, 0.0, 0.0, 0.0],
                    "type": "text",
                }
            )
            page_count = max(page_count, 1)

    if not blocks:
        for i, page in enumerate(getattr(doc, "pages", {}).values(), start=1):
            text = ""
            if hasattr(page, "text"):
                text = str(page.text) if page.text else ""
            blocks.append(
                {"page": i, "text": text, "bbox": [0.0, 0.0, 0.0, 0.0], "type": "text"}
            )

    # --- tables ---
    tables_out: list[dict[str, Any]] = []
    for i, table in enumerate(getattr(doc, "tables", []), start=1):
        try:
            df = table.export_to_dataframe(doc=doc)
            grid = [[str(v) for v in row] for row in df.values.tolist()]
            header = list(df.columns.astype(str))
            grid = [header] + grid if grid else ([header] if header else [])

            # Derive page number from the table element when available.
            table_page = getattr(table, "page_no", None)
            if table_page is None:
                prov = getattr(table, "prov", None) or []
                if prov:
                    first = prov[0] if isinstance(prov, list) else prov
                    table_page = getattr(first, "page_no", None) or getattr(
                        first, "page", None
                    )
            tables_out.append(
                {
                    "page": int(table_page) if table_page else 1,
                    "bbox": [0.0, 0.0, 0.0, 0.0],
                    "caption": "",
                    "grid": grid,
                }
            )
        except Exception as exc:
            logger.warning("Could not export table %s: %s", i, exc)

    # --- figures (actual images via iterate_items) ---
    figures_out: list[dict[str, Any]] = []
    if out_dir is not None:
        figures_dir = out_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        picture_counter = 0
        table_img_counter = 0
        for element, _level in doc.iterate_items():
            if isinstance(element, PictureItem):
                picture_counter += 1
                fig_id = deterministic_id("fig", picture_counter)
                image_path = figures_dir / f"{fig_id}.png"
                try:
                    pil_img = element.get_image(doc)
                    if pil_img is not None:
                        pil_img.save(image_path, format="PNG")
                    else:
                        _synthesize_placeholder(
                            image_path, f"Picture {picture_counter} (no image data)"
                        )
                except Exception as exc:
                    logger.warning(
                        "Could not save picture %s: %s", picture_counter, exc
                    )
                    _synthesize_placeholder(
                        image_path, f"Picture {picture_counter} (error)"
                    )

                # Extract caption/text from the element if available
                caption = ""
                if hasattr(element, "caption_text"):
                    caption = (
                        str(element.caption_text(doc))
                        if callable(getattr(element, "caption_text", None))
                        else str(getattr(element, "caption_text", ""))
                    )
                elif hasattr(element, "text"):
                    caption = str(element.text) if element.text else ""

                figures_out.append(
                    {
                        "id": fig_id,
                        "page": getattr(element, "page_no", 1) or 1,
                        "bbox": [0.0, 0.0, 0.0, 0.0],
                        "caption": caption,
                        "image_path": str(image_path),
                    }
                )

            elif isinstance(element, TableItem):
                # Also save table images for reference
                table_img_counter += 1
                tbl_img_id = deterministic_id("table_img", table_img_counter)
                image_path = figures_dir / f"{tbl_img_id}.png"
                try:
                    pil_img = element.get_image(doc)
                    if pil_img is not None:
                        pil_img.save(image_path, format="PNG")
                except Exception:
                    pass  # Table images are optional

    return {
        "page_count": page_count,
        "blocks": blocks,
        "tables": tables_out,
        "figures": figures_out,
    }


def _extract_with_pypdf(pdf_path: Path) -> dict[str, Any]:
    """Extract text blocks from a PDF using ``pypdf`` as a fallback."""
    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(str(pdf_path))
    blocks: list[dict[str, Any]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        blocks.append(
            {"page": i, "text": text, "bbox": [0.0, 0.0, 0.0, 0.0], "type": "text"}
        )
    return {
        "page_count": len(reader.pages),
        "blocks": blocks,
        "tables": [],
        "figures": [],
    }


def extract_document(pdf_path: Path, out_dir: Path | None = None) -> dict[str, Any]:
    """Extract document content, preferring Docling and falling back to pypdf."""
    try:
        return _extract_with_docling(pdf_path, out_dir=out_dir)
    except Exception as exc:
        logger.warning(
            "Docling extraction failed for %s; falling back to pypdf: %s", pdf_path, exc
        )
        return _extract_with_pypdf(pdf_path)


def _synthesize_placeholder(fig_path: Path, caption: str) -> None:
    """Create a placeholder figure when a real image cannot be extracted."""
    img = Image.new(
        "RGB", (PLACEHOLDER_WIDTH, PLACEHOLDER_HEIGHT), color=(248, 248, 248)
    )
    draw = ImageDraw.Draw(img)
    draw.text(
        (20, 20),
        f"Placeholder figure\n{caption[:PLACEHOLDER_CAPTION_MAX]}",
        fill=(0, 0, 0),
    )
    img.save(fig_path)


def to_blocks(raw_blocks: list[dict[str, Any]]) -> list[Block]:
    """Convert raw block dictionaries into typed ``Block`` models."""
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
