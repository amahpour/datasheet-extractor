"""Rule-based tagging and figure classification helpers."""

from __future__ import annotations

from src.schema import Classification

# Rules that are safe to match against both caption and surrounding page context.
CONTEXT_RULES: list[tuple[str, str, float, str]] = [
    ("timing", "timing_diagram", 0.92, "caption mentions timing"),
    ("state", "state_machine", 0.88, "caption mentions state"),
    ("block diagram", "block_diagram", 0.9, "caption mentions block diagram"),
    ("schematic", "block_diagram", 0.72, "schematic-like wording"),
    ("plot", "plot", 0.85, "caption mentions plot"),
    ("graph", "plot", 0.8, "caption mentions graph"),
    ("waveform", "timing_diagram", 0.82, "caption mentions waveform"),
]

# Rules that only make sense when the keyword appears in the figure's own caption.
# Matching these against page context is too noisy (e.g. "see Table 1" in body text
# would misclassify every figure on that page as a table_image).
CAPTION_ONLY_RULES: list[tuple[str, str, float, str]] = [
    ("table", "table_image", 0.75, "caption suggests table in image"),
]


def classify_figure(caption: str, context_text: str = "") -> Classification:
    """Classify a figure using simple keyword rules over caption and context.

    Keywords like "table" are only matched against the caption to avoid
    false positives from incidental use of the word in surrounding body text.
    """
    caption_lower = caption.lower()
    haystack = f"{caption} {context_text}".lower()

    # Caption-only rules first (higher signal).
    for needle, cls, confidence, rationale in CAPTION_ONLY_RULES:
        if needle in caption_lower:
            return Classification(type=cls, confidence=confidence, rationale=rationale)

    # Context-safe rules match against both caption and surrounding text.
    for needle, cls, confidence, rationale in CONTEXT_RULES:
        if needle in haystack:
            return Classification(type=cls, confidence=confidence, rationale=rationale)

    return Classification(type="other", confidence=0.4, rationale="no rule matched")


def tags_from_text(*chunks: str) -> list[str]:
    """Extract coarse tags from text using a fixed candidate list."""
    joined = " ".join(chunks).lower()
    tags: list[str] = []
    candidates = [
        "i2c",
        "dac",
        "adc",
        "voltage",
        "timing",
        "state",
        "register",
        "pin",
        "power",
    ]
    for candidate in candidates:
        if candidate in joined:
            tags.append(candidate)
    return sorted(set(tags))
