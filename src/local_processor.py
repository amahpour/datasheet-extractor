"""Local figure processing with per-figure status tracking.

Every figure gets:
  1. OCR (if pytesseract is available)
  2. Local vision LLM via Ollama (classify + describe)

The result is written to  out/<pdf>/processing/<fig_id>.json  so that
stage 2 (external LLM) can skip already-resolved figures.

Status values:
  - resolved_local   – local processing was sufficient
  - needs_external   – flagged for a more capable external LLM
  - resolved_external – external LLM has processed it (set by stage 2)
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from src.utils import run_ocr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Images below this are literal noise (a couple of stray pixels)
NOISE_PIXEL_THRESHOLD = 500

# If OCR extracts this many clean chars, the image is "text-heavy"
OCR_RICH_CHARS = 120

# Minimum description length to consider locally resolved
MIN_DESCRIPTION_LEN = 50

# Truncation limits for rollup summaries
ROLLUP_DESCRIPTION_MAX = 120
ROLLUP_DESCRIPTION_DISPLAY_MAX = 80
ROLLUP_OCR_PREVIEW_MAX = 80

# Classification keywords that mean "needs external for precision"
COMPLEX_TYPES = {
    "plot",
    "pinout",
    "schematic",
    "block_diagram",
    "timing_diagram",
    "register_map",
    "wiring_diagram",
    "state_machine",
    "table_image",
}

# Classification keywords that are simple enough to resolve locally
SIMPLE_TYPES = {"logo", "icon", "decorative", "photo", "screenshot", "other"}

# Local LLM prompt — keep it dead simple so small models don't choke
DESCRIBE_PROMPT = "Describe this image from an electronics datasheet."


# ---------------------------------------------------------------------------
# Per-figure status file
# ---------------------------------------------------------------------------


def _status_path(processing_dir: Path, figure_id: str) -> Path:
    """Return the status-file path for a figure within ``processing_dir``."""
    return processing_dir / f"{figure_id}.json"


def read_status(processing_dir: Path, figure_id: str) -> dict | None:
    """Read existing status file, or None if it doesn't exist."""
    p = _status_path(processing_dir, figure_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def write_status(processing_dir: Path, status: dict) -> None:
    """Write a per-figure status JSON file."""
    processing_dir.mkdir(parents=True, exist_ok=True)
    p = _status_path(processing_dir, status["figure_id"])
    p.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")


def _new_status(figure_id: str, image_path: str) -> dict:
    """Create a default status payload for a new figure-processing run."""
    return {
        "figure_id": figure_id,
        "image_path": image_path,
        "status": "needs_external",
        "stage": "",
        "ocr_text": "",
        "local_llm_description": "",
        "local_llm_classification": "",
        "external_llm_result": None,
        "needs_external": True,
        "confidence": 0.0,
        "processed_at": "",
    }


# ---------------------------------------------------------------------------
# Local LLM via Ollama Python library
# ---------------------------------------------------------------------------


def _ollama_generate(model: str, prompt: str, image_path: Path) -> str:
    """Call ollama.generate with an image. Returns response text or ''."""
    try:
        import ollama  # type: ignore
    except ImportError:
        logger.warning("ollama Python package not installed. Run: pip install ollama")
        return ""

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        resp = ollama.generate(model=model, prompt=prompt, images=[img_b64])
        return resp.get("response", "").strip()
    except Exception as exc:
        logger.warning("Ollama generate failed for %s: %s", image_path, exc)
        return ""


def _detect_ollama_model() -> str | None:
    """Find a suitable vision model from ollama."""
    try:
        import ollama  # type: ignore

        result = ollama.list()

        # ollama.list() may return a dict or an object with a .models attribute
        if hasattr(result, "models"):
            model_list = result.models
        elif isinstance(result, dict):
            model_list = result.get("models", [])
        else:
            model_list = []

        model_names = []
        for m in model_list:
            # Each model may be a dict or an object with .model attribute
            if hasattr(m, "model"):
                name = m.model
            elif isinstance(m, dict):
                name = m.get("name", "") or m.get("model", "")
            else:
                name = str(m)
            model_names.append(name.lower())

        # Prefer stronger general-purpose vision models before lightweight ones.
        for candidate in ["llava:7b", "llava", "bakllava", "minicpm-v", "moondream"]:
            for name in model_names:
                if candidate in name:
                    return name
        return None
    except ImportError:
        return None
    except Exception as exc:
        logger.debug("Could not list ollama models: %s", exc)
        return None


def _infer_classification(description: str) -> str:
    """Infer a classification from a free-text description using keywords."""
    text = description.lower()

    # Order matters: more specific matches first
    rules = [
        (["logo"], "logo"),
        (["icon", "symbol", "arrow"], "icon"),
        (["pin", "pinout", "pin diagram", "pin assignment"], "pinout"),
        (["schematic", "circuit diagram"], "schematic"),
        (["timing", "waveform", "clock", "signal timing"], "timing_diagram"),
        (["state machine", "state diagram", "flowchart"], "state_machine"),
        (["register", "bit field", "register map"], "register_map"),
        (["block diagram", "functional block"], "block_diagram"),
        (["wiring", "hookup", "connection diagram"], "wiring_diagram"),
        (
            ["plot", "graph", "chart", "x-axis", "y-axis", "linearity", "error", "vs"],
            "plot",
        ),
        (["table", "row", "column", "header"], "table_image"),
        (["circuit board", "inputs and outputs", "chip diagram"], "block_diagram"),
        (["photo", "photograph", "pcb", "board", "chip"], "photo"),
        (["screenshot", "ide", "terminal", "oscilloscope"], "screenshot"),
        (["package", "dimension", "footprint", "mechanical"], "mechanical"),
    ]
    for keywords, classification in rules:
        if any(kw in text for kw in keywords):
            return classification

    return "other"


# ---------------------------------------------------------------------------
# Decide if locally resolved
# ---------------------------------------------------------------------------


def _is_resolved_locally(classification: str, ocr_text: str, description: str) -> bool:
    """Decide if local processing is sufficient for this figure."""
    # Simple types are always resolved locally
    if classification in SIMPLE_TYPES:
        return True

    # If OCR got a ton of text and it's not a complex type, resolve it
    clean_ocr = "".join(ch for ch in ocr_text if ch.isalnum() or ch.isspace()).strip()
    if len(clean_ocr) >= OCR_RICH_CHARS and classification not in COMPLEX_TYPES:
        return True

    # Complex types always need external
    if classification in COMPLEX_TYPES:
        return False

    # Unknown classification — if we got a decent description, resolve it
    if len(description) > MIN_DESCRIPTION_LEN:
        return True

    return False


# ---------------------------------------------------------------------------
# Main: process a single figure
# ---------------------------------------------------------------------------


def process_figure(
    figure_id: str,
    image_path: Path,
    processing_dir: Path,
    ollama_model: str | None = None,
    force: bool = False,
) -> dict:
    """Process a single figure locally and write its status file.

    Skips processing if a status file already exists (unless force=True).
    Returns the status dict.
    """
    # Check for existing status
    if not force:
        existing = read_status(processing_dir, figure_id)
        if existing is not None:
            logger.debug(
                "  %s: already processed (status=%s), skipping",
                figure_id,
                existing["status"],
            )
            return existing

    status = _new_status(figure_id, str(image_path))
    now = datetime.now(timezone.utc).isoformat()

    if not image_path.exists():
        status["status"] = "resolved_local"
        status["stage"] = "skip"
        status["local_llm_description"] = "File not found"
        status["needs_external"] = False
        status["processed_at"] = now
        write_status(processing_dir, status)
        return status

    img = Image.open(image_path)
    w, h = img.size
    pixels = w * h

    # Literal noise — skip entirely
    if pixels < NOISE_PIXEL_THRESHOLD:
        status["status"] = "resolved_local"
        status["stage"] = "skip"
        status["local_llm_classification"] = "noise"
        status["local_llm_description"] = f"Image too small to be meaningful ({w}x{h})"
        status["needs_external"] = False
        status["confidence"] = 1.0
        status["processed_at"] = now
        write_status(processing_dir, status)
        return status

    # --- OCR ---
    ocr_text = run_ocr(image_path)
    status["ocr_text"] = ocr_text

    # --- Local LLM ---
    classification = "other"
    description = ""

    if ollama_model:
        response = _ollama_generate(ollama_model, DESCRIBE_PROMPT, image_path)
        if response:
            description = response.strip()
            classification = _infer_classification(description)
            status["stage"] = "local_llm"
            status["local_llm_classification"] = classification
            status["local_llm_description"] = description
    else:
        # No local LLM — use OCR-only heuristics
        status["stage"] = "ocr"
        text_lower = ocr_text.lower()
        if any(kw in text_lower for kw in ["vs", "error", "response", "frequency"]):
            classification = "plot"
        elif any(
            kw in text_lower for kw in ["pin", "vout", "vcc", "gnd", "sda", "scl"]
        ):
            classification = "pinout"
        status["local_llm_classification"] = classification
        status["local_llm_description"] = (
            f"OCR text: {ocr_text[:300]}" if ocr_text else ""
        )

    # --- Decide resolved vs needs_external ---
    resolved = _is_resolved_locally(classification, ocr_text, description)
    status["status"] = "resolved_local" if resolved else "needs_external"
    status["needs_external"] = not resolved
    status["confidence"] = 0.7 if resolved else 0.3
    status["processed_at"] = now

    write_status(processing_dir, status)
    return status


# ---------------------------------------------------------------------------
# Batch: process all figures in a directory
# ---------------------------------------------------------------------------


def process_all_figures(
    figures_dir: Path,
    processing_dir: Path,
    ollama_model: str | None = None,
    force: bool = False,
) -> list[dict]:
    """Process all fig_*.png files, write per-figure status, return all statuses."""
    # Auto-detect model if not specified
    if ollama_model is None:
        ollama_model = _detect_ollama_model()
        if ollama_model:
            logger.info("Detected Ollama vision model: %s", ollama_model)
        else:
            logger.warning("No Ollama vision model found. Running OCR-only mode.")

    results = []
    fig_paths = sorted(figures_dir.glob("fig_*.png"))
    total = len(fig_paths)

    for i, fig_path in enumerate(fig_paths, start=1):
        fig_id = fig_path.stem
        logger.info("  [%d/%d] Processing %s ...", i, total, fig_id)
        status = process_figure(
            fig_id,
            fig_path,
            processing_dir,
            ollama_model=ollama_model,
            force=force,
        )
        logger.info(
            "    → status=%s, classification=%s",
            status["status"],
            status["local_llm_classification"],
        )
        results.append(status)

    return results


# ---------------------------------------------------------------------------
# Rollup report (reads from per-figure status files)
# ---------------------------------------------------------------------------


def build_rollup_from_dir(processing_dir: Path) -> dict:
    """Build rollup by reading all status files in the processing dir."""
    statuses = []
    for p in sorted(processing_dir.glob("fig_*.json")):
        statuses.append(json.loads(p.read_text(encoding="utf-8")))
    return build_rollup(statuses)


def build_rollup(statuses: list[dict]) -> dict:
    """Build a rollup summary from a list of status dicts."""
    resolved_local = [s for s in statuses if s["status"] == "resolved_local"]
    needs_external = [s for s in statuses if s["status"] == "needs_external"]
    resolved_external = [s for s in statuses if s["status"] == "resolved_external"]

    total = len(statuses)
    locally_done = len(resolved_local)
    externally_done = len(resolved_external)
    pending = len(needs_external)

    return {
        "total_figures": total,
        "resolved_local": locally_done,
        "resolved_external": externally_done,
        "needs_external": pending,
        "summary": {
            "fully_processed": locally_done + externally_done,
            "pending_external": pending,
            "percent_complete": round(
                100 * (locally_done + externally_done) / max(total, 1), 1
            ),
        },
        "figures": {
            "resolved_local": [
                {
                    "id": s["figure_id"],
                    "classification": s.get("local_llm_classification", ""),
                    "description": s.get("local_llm_description", "")[
                        :ROLLUP_DESCRIPTION_MAX
                    ],
                }
                for s in resolved_local
            ],
            "needs_external": [
                {
                    "id": s["figure_id"],
                    "image_path": s["image_path"],
                    "classification": s.get("local_llm_classification", ""),
                    "description": s.get("local_llm_description", "")[
                        :ROLLUP_DESCRIPTION_MAX
                    ],
                    "ocr_preview": s.get("ocr_text", "")[:ROLLUP_OCR_PREVIEW_MAX],
                }
                for s in needs_external
            ],
            "resolved_external": [
                {
                    "id": s["figure_id"],
                    "classification": s.get("local_llm_classification", ""),
                }
                for s in resolved_external
            ],
        },
    }


def write_rollup(processing_dir: Path, out_dir: Path) -> dict:
    """Read all status files and write rollup JSON + markdown."""
    rollup = build_rollup_from_dir(processing_dir)

    # JSON
    (out_dir / "processing_rollup.json").write_text(
        json.dumps(rollup, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown
    s = rollup["summary"]
    lines = [
        "# Figure Processing Rollup",
        "",
        f"**Total figures:** {rollup['total_figures']}",
        f"**Resolved locally:** {rollup['resolved_local']}",
        f"**Resolved by external LLM:** {rollup['resolved_external']}",
        f"**Pending external LLM:** {s['pending_external']}",
        f"**Completion:** {s['percent_complete']}%",
        "",
        "---",
        "",
    ]

    if rollup["figures"]["resolved_local"]:
        lines.append(f"## Resolved locally ({rollup['resolved_local']})")
        lines.append("")
        for fig in rollup["figures"]["resolved_local"]:
            desc = fig["description"].replace("\n", " ")[:ROLLUP_DESCRIPTION_DISPLAY_MAX]
            lines.append(f"- `{fig['id']}` [{fig['classification']}] {desc}")
        lines.append("")

    if rollup["figures"]["needs_external"]:
        lines.append(f"## Needs external LLM ({s['pending_external']})")
        lines.append("")
        lines.append("Use the prompt template in `prompts/figure_analysis.md`.")
        lines.append("")
        for fig in rollup["figures"]["needs_external"]:
            desc = fig["description"].replace("\n", " ")[:ROLLUP_DESCRIPTION_DISPLAY_MAX]
            lines.append(
                f"- `{fig['id']}` [{fig['classification']}] → `{fig['image_path']}`"
            )
            if desc:
                lines.append(f"  {desc}")
        lines.append("")

    if rollup["figures"]["resolved_external"]:
        lines.append(f"## Resolved by external LLM ({rollup['resolved_external']})")
        lines.append("")
        for fig in rollup["figures"]["resolved_external"]:
            lines.append(f"- `{fig['id']}` [{fig['classification']}]")
        lines.append("")

    (out_dir / "processing_rollup.md").write_text("\n".join(lines), encoding="utf-8")

    return rollup
