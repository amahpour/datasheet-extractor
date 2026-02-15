from __future__ import annotations

"""Rule-based tagging and figure classification helpers."""

from src.schema import Classification

RULES: list[tuple[str, str, float, str]] = [
    ("timing", "timing_diagram", 0.92, "caption mentions timing"),
    ("state", "state_machine", 0.88, "caption mentions state"),
    ("block diagram", "block_diagram", 0.9, "caption mentions block diagram"),
    ("schematic", "block_diagram", 0.72, "schematic-like wording"),
    ("plot", "plot", 0.85, "caption mentions plot"),
    ("graph", "plot", 0.8, "caption mentions graph"),
    ("waveform", "timing_diagram", 0.82, "caption mentions waveform"),
    ("table", "table_image", 0.75, "caption suggests table in image"),
]


def classify_figure(caption: str, context_text: str = "") -> Classification:
    """Classify a figure using simple keyword rules over caption and context."""
    haystack = f"{caption} {context_text}".lower()
    for needle, cls, confidence, rationale in RULES:
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
