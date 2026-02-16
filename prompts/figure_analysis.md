# Datasheet Figure Analysis Prompt

Use this prompt with a vision-capable LLM (GPT-4o, Claude, Gemini, etc.).
Attach the extracted figure image along with this prompt text.

---

## Prompt

You are an expert electronics engineer analyzing figures extracted from a component datasheet PDF.

**Your task:** Examine the attached image and produce a structured analysis. The image was extracted automatically — it could be a photograph, schematic, block diagram, timing diagram, pin diagram, plot/graph, wiring diagram, table rendered as an image, or something else entirely.

### Step 1: Classify the image

Identify which ONE type best describes this image:

| Type | Description |
|------|-------------|
| `photo` | Product photograph, PCB photo, physical component |
| `pinout` | Pin diagram or pin assignment drawing |
| `schematic` | Circuit schematic |
| `block_diagram` | Functional block diagram |
| `timing_diagram` | Timing/waveform diagram |
| `state_machine` | State diagram or flowchart |
| `plot` | Graph, chart, or data plot (e.g. voltage vs. time) |
| `wiring_diagram` | Hookup / wiring / connection diagram |
| `table_image` | A table rendered as an image rather than text |
| `register_map` | Register bit-field layout |
| `mechanical` | Mechanical drawing, package dimensions, footprint |
| `screenshot` | Software screenshot (IDE, terminal, oscilloscope UI) |
| `other` | Anything that doesn't fit the above |

### Step 2: Produce structured output

Return your analysis as a JSON object with this exact schema:

```json
{
  "classification": "<type from table above>",
  "title": "<short descriptive title for this figure>",
  "summary": "<1-3 sentence description of what the image shows>",
  "structured_data": {
    // Include ONE of the following based on classification:

    // For "plot":
    "x_axis": "<label and unit>",
    "y_axis": "<label and unit>",
    "series": [
      {"name": "<series name>", "data_points": [{"x": 0, "y": 0}, ...]}
    ],
    "csv": "<CSV string of the data>"

    // For "table_image":
    "headers": ["col1", "col2", ...],
    "rows": [["val1", "val2", ...], ...]

    // For "timing_diagram":
    "signals": [
      {"name": "<signal>", "transitions": "<description of timing>"}
    ],
    "wavedrom": "<WaveDrom JSON if possible>"

    // For "block_diagram" or "state_machine":
    "mermaid": "<Mermaid diagram code>",
    "nodes": ["<node1>", "<node2>", ...],
    "connections": [{"from": "<node>", "to": "<node>", "label": "<optional>"}]

    // For "schematic":
    "components": [{"ref": "<designator>", "type": "<type>", "value": "<value>"}],
    "nets": ["<net descriptions>"],
    "description": "<what the circuit does>"

    // For "pinout":
    "pins": [{"number": 1, "name": "<name>", "function": "<description>"}]

    // For "register_map":
    "register_name": "<name>",
    "address": "<hex address if visible>",
    "bits": [{"range": "7:0", "name": "<field>", "access": "R/W", "description": "..."}]

    // For "wiring_diagram":
    "connections": [{"from": "<component.pin>", "to": "<component.pin>", "wire_color": "<if visible>"}]

    // For "photo", "mechanical", "screenshot", "other":
    "description": "<detailed text description of what is visible>"
  },
  "component_references": ["<part numbers, IC names, or component refs mentioned>"],
  "key_values": {
    // Any important electrical values visible in the image:
    // e.g. "voltage_range": "3.3V - 5V", "i2c_address": "0x4C"
  },
  "confidence": 0.0  // 0.0 to 1.0, your confidence in the structured extraction
}
```

### Rules

1. **Be thorough.** Extract every piece of information visible in the image.
2. **Be precise.** Use exact values, units, and labels as shown.
3. **When uncertain**, include what you can and set `confidence` lower.
4. **For plots**, digitize as many data points as you can reasonably read from the axes.
5. **For diagrams**, prefer Mermaid syntax so the output is machine-reproducible.
6. **For tables**, transcribe every row and column exactly.
7. **Omit keys** from `structured_data` that don't apply to the classification.
8. **`component_references`** should list any IC part numbers, connector types, or named components visible (e.g. "DAC7578", "STEMMA QT", "RP2040").

---

## Batch usage

To process all figures from a datasheet extraction run, **check each figure's
processing status first** to avoid re-analysing figures that have already been
handled (either locally or in a previous external pass).

```
for each image in out/<pdf_stem>/figures/fig_*.png:
    fig_id   = stem of the image filename (e.g. "fig_0042")
    status   = load out/<pdf_stem>/processing/<fig_id>.json   # per-figure status

    # ── Skip rules ──────────────────────────────────────────
    # 1. Already resolved locally (local LLM was sufficient)
    if status.status == "resolved_local":
        skip

    # 2. Already processed by an external LLM in a prior run
    if file exists out/<pdf_stem>/derived/figures/<fig_id>/llm_analysis.json:
        skip

    # ── Process ─────────────────────────────────────────────
    # Only figures with status "needs_external" (or missing status) should be sent.
    send this prompt + the image to your vision LLM
    save the JSON response to out/<pdf_stem>/derived/figures/<fig_id>/llm_analysis.json

    # Optionally update the processing status:
    status.status = "resolved_external"
    write status back to out/<pdf_stem>/processing/<fig_id>.json
```

**Key:** the `processing/<fig_id>.json` files are written during Stage 1 (local
processing) and record the tier, classification, and whether the figure was
resolved. Only figures marked `needs_external` should be sent to the paid LLM.
