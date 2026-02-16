"""Figure post-processing helpers for description derivation."""

from __future__ import annotations

from src.schema import Description, Derived, Figure


def derive_description(figure: Figure) -> Figure:
    """Populate ``figure.derived.description`` with initial metadata.

    The real description comes from Ollama (local_processor) or an external
    LLM (stage 2).  This sets a baseline so the field is never empty.
    """
    if (
        figure.classification.type
        in {"plot", "timing_diagram", "block_diagram", "state_machine"}
    ):
        notes = "LLM recommended"
    else:
        notes = "none"

    figure.derived = Derived(
        description=Description(
            text="Pending local LLM processing.",
            confidence=0.0,
            notes=notes,
        )
    )
    return figure
