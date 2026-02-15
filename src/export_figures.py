"""Figure post-processing helpers for OCR and description derivation."""

from __future__ import annotations

import logging
from pathlib import Path

from src.schema import Description, Derived, Figure
from src.utils import run_ocr

# Maximum characters to keep from OCR output in descriptions.
OCR_TEXT_MAX = 1000

logger = logging.getLogger(__name__)


def derive_description(figure: Figure, ocr_mode: str) -> Figure:
    """Populate ``figure.derived.description`` from placeholders and optional OCR."""
    text = "Local-only placeholder description; no semantic reconstruction performed."
    confidence = 0.2
    notes = "LLM recommended"

    if ocr_mode != "off":
        ocr = run_ocr(Path(figure.image_path))
        if ocr:
            text = f"Visible text (OCR): {ocr[:OCR_TEXT_MAX]}"
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
