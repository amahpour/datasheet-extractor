# Datasheet Extractor

Local-first Python CLI for extracting datasheet PDFs into structured JSON, table exports, figure artifacts, and processing rollup reports.

## Install

```bash
pip install .
```

Optional extras:

```bash
pip install .[ocr]      # pytesseract for OCR
pip install .[vision]   # opencv
```

### Ollama (local vision LLM)

The pipeline uses [Ollama](https://ollama.com) to classify and describe extracted figures locally. Install it, then pull a vision model:

```bash
brew install ollama
ollama serve            # or open the Ollama macOS app
ollama pull moondream   # fast, ~1.7GB
```

## CLI usage

```bash
# Full pipeline: extract + local figure processing
datasheet-extract --input ./examples --out ./out --glob "*.pdf"

# Specify Ollama model explicitly
datasheet-extract --input ./examples --out ./out --ollama-model moondream

# Skip images or tables
datasheet-extract --input ./examples --out ./out --no-images
datasheet-extract --input ./examples --out ./out --no-tables
```

Python module invocation:

```bash
python -m cli.ds_extract --input ./examples --out ./out
python -m cli.smoke_test
```

### Options

- `--input` (default `./examples`)
- `--out` (default `./out`)
- `--glob` (default `*.pdf`)
- `--pages "1-3,7"`
- `--force` — reprocess even if status files exist
- `--no-images`
- `--no-tables`
- `--ocr {off,on,auto}` (default `off`)
- `--max-figures N`
- `--ollama-model NAME` — Ollama vision model (auto-detected if omitted)

## Two-stage workflow

### Stage 1: Extract + local processing (automatic)

The pipeline runs two phases in one command:

1. **Docling extraction** — text (markdown), tables (CSV/MD/JSON), and all figure images (PNG)
2. **Local figure processing** — each figure gets OCR + local vision LLM (Ollama). Results are written to per-figure status files.

Figures are classified and routed:

- **Resolved locally** — logos, icons, simple photos, text-heavy images
- **Needs external LLM** — plots, pinouts, schematics, block diagrams, timing diagrams

### Stage 2: External LLM (manual)

Open `processing_rollup.md` to see what still needs processing. For each figure flagged as `needs_external`, use the prompt template in `prompts/figure_analysis.md` with a vision-capable LLM (GPT-4o, Claude, etc.).

After processing, update the figure's status file in `processing/` to `"status": "resolved_external"` and fill in `external_llm_result`.

## Output layout

Per PDF (`out/<pdf_stem>/`):

- `document.json` — full extraction: text blocks, tables, figures
- `index.json` — paths to all artifacts
- `figures/fig_0001.png` — extracted figure images
- `tables/table_0001.{json,csv,md}` — extracted tables
- `processing/fig_0001.json` — per-figure processing status
- `processing_rollup.{json,md}` — summary of what's resolved vs pending
- `derived/figures/fig_0001/meta.json`
- `derived/figures/fig_0001/description.md`
- `manual_processing_report.{md,json}`

Global (`out/`):

- `index.json`
- `processing_rollup.json` — global rollup across all PDFs
- `manual_processing_report.{md,json}`

## Per-figure status file

Each `processing/fig_XXXX.json` tracks:

```json
{
  "figure_id": "fig_0017",
  "image_path": "out/dac5578/figures/fig_0017.png",
  "status": "needs_external",
  "stage": "local_llm",
  "ocr_text": "",
  "local_llm_description": "Graph showing linearity error vs digital input code...",
  "local_llm_classification": "plot",
  "external_llm_result": null,
  "needs_external": true,
  "confidence": 0.3,
  "processed_at": "2026-02-12T00:33:06Z"
}
```

Status values: `resolved_local`, `needs_external`, `resolved_external`

Stage 2 skips any figure where status is `resolved_local` or `resolved_external`.

## Caveats

- Docling extraction behavior varies by PDF type.
- OCR is optional and best-effort (requires pytesseract).
- Local vision models (moondream, llava) hallucinate on complex figures — they're used for classification/triage only, not precision extraction.
- Complex figures (plots, pinouts, schematics) are intentionally deferred to external LLM via the rollup report.
