"""Document extraction via Docling."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.schema import Block
from src.utils import deterministic_id

logger = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0


def _page_from_provenance(element: object) -> int:
    """Extract the page number from a Docling element's provenance metadata.

    PictureItem and TableItem objects store their location in a ``prov``
    list rather than a top-level ``page_no`` attribute.  This helper
    mirrors the provenance walk used by the HybridChunker block loop.
    """
    for p in getattr(element, "prov", []):
        page_no = getattr(p, "page_no", None)
        if page_no is not None:
            return int(page_no)
    return 1

# Default chunking parameter (token limit aligned to embedding model).
DEFAULT_MAX_TOKENS = 256
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _extract_with_docling(
    pdf_path: Path,
    out_dir: Path | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict[str, Any]:
    """Extract text, tables, and figures from a PDF using Docling.

    When *out_dir* is provided, extracted figure images are saved there and
    their paths are included in the returned dict.

    Text is chunked using Docling's ``HybridChunker`` with a HuggingFace
    tokenizer aligned to the target embedding model.  Each chunk carries
    section headings and an ``enriched_text`` field ready for embedding.
    """
    from docling.chunking import HybridChunker
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.transforms.chunker.tokenizer.huggingface import (
        HuggingFaceTokenizer,
    )
    from docling_core.types.doc import PictureItem, TableItem
    from transformers import AutoTokenizer

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

    # --- text blocks via HybridChunker ---
    tok = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    hf_tok = HuggingFaceTokenizer(tokenizer=tok, max_tokens=max_tokens)
    chunker = HybridChunker(tokenizer=hf_tok)

    blocks: list[dict[str, Any]] = []
    for ch in chunker.chunk(doc):
        pages: set[int] = set()
        for item in ch.meta.doc_items:
            for p in getattr(item, "prov", []):
                pages.add(p.page_no)
        page = min(pages) if pages else 1

        blocks.append(
            {
                "page": page,
                "text": ch.text,
                "enriched_text": chunker.contextualize(ch),
                "headings": ch.meta.headings or [],
                "bbox": [0.0, 0.0, 0.0, 0.0],
                "type": "text",
            }
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
                        logger.warning(
                            "Picture %s: no image data returned by Docling, skipping",
                            picture_counter,
                        )
                        continue
                except Exception as exc:
                    logger.warning(
                        "Could not save picture %s: %s, skipping", picture_counter, exc
                    )
                    continue

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
                        "page": _page_from_provenance(element),
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


def extract_document(
    pdf_path: Path,
    out_dir: Path | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict[str, Any]:
    """Extract document content using Docling."""
    return _extract_with_docling(pdf_path, out_dir=out_dir, max_tokens=max_tokens)


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
                enriched_text=str(raw.get("enriched_text", "")),
                headings=raw.get("headings", []),
            )
        )
    return blocks
