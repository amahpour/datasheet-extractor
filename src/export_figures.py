from __future__ import annotations

"""Figure post-processing helpers for OCR and description derivation."""

import logging
from pathlib import Path

from PIL import Image

from src.schema import Description, Derived, Figure

logger = logging.getLogger(__name__)


def _ocr_text(image_path: Path) -> str | None:
    """Run OCR on an image and return extracted text when available."""
    try:
        import pytesseract  # type: ignore
    except Exception:
        return None
    try:
        return pytesseract.image_to_string(Image.open(image_path)).strip()
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", image_path, exc)
        return None


def ensure_png(image_path: Path) -> Path:
    """Ensure an image is stored as PNG and return the PNG path."""
    if image_path.suffix.lower() == ".png":
        return image_path
    png_path = image_path.with_suffix(".png")
    Image.open(image_path).save(png_path)
    return png_path


def derive_description(figure: Figure, ocr_mode: str) -> Figure:
    """Populate ``figure.derived.description`` from placeholders and optional OCR."""
    text = "Local-only placeholder description; no semantic reconstruction performed."
    confidence = 0.2
    notes = "LLM recommended"

    if ocr_mode != "off":
        ocr = _ocr_text(Path(figure.image_path))
        if ocr:
            text = f"Visible text (OCR): {ocr[:1000]}"
            confidence = 0.6
            notes = "OCR-derived text only"
    if (
        figure.classification.type
        in {"plot", "timing_diagram", "block_diagram", "state_machine"}
        and confidence < 0.7
    ):
        notes = "LLM recommended"
    else:
        notes = "none"

    figure.derived = Derived(
        description=Description(text=text, confidence=confidence, notes=notes)
    )
    return figure
