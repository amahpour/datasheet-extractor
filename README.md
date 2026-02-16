# Datasheet Extractor

Local-first Python CLI for extracting datasheet PDFs into structured JSON, table exports, figure artifacts, and processing rollup reports.

## Install

```bash
pip install .
```

### Ollama (local vision LLM)

The pipeline uses [Ollama](https://ollama.com) to classify and describe extracted figures locally. Install it, then pull a vision model:

```bash
brew install ollama
ollama serve            # or open the Ollama macOS app
ollama pull moondream   # fast, ~1.7GB
```

## CLI usage

Use `--file` to process a single PDF, or `--dir` to process every PDF in a directory.

```bash
# Single file
datasheet-extract --file ./examples/dac7578/dac5578.pdf --out ./out

# Single file, first 3 pages only
datasheet-extract --file ./examples/dac7578/dac5578.pdf --out ./out --pages "1-3"

# All PDFs in a directory
datasheet-extract --dir ./examples --out ./out

# Specify Ollama model explicitly
datasheet-extract --dir ./examples --out ./out --ollama-model moondream

# Skip images or tables
datasheet-extract --dir ./examples --out ./out --no-images
datasheet-extract --dir ./examples --out ./out --no-tables
```

Python module invocation:

```bash
python -m cli.ds_extract --file ./examples/dac7578/dac5578.pdf --out ./out
python -m cli.ds_extract --dir ./examples --out ./out
python -m cli.smoke_test
```

### Options

- `--file` — path to a single PDF file (mutually exclusive with `--dir`)
- `--dir` — directory containing PDF files (mutually exclusive with `--file`)
- `--out` (default `./out`)
- `--glob` (default `*.pdf`) — filename pattern when using `--dir`
- `--pages "1-3,7"`
- `--force` — reprocess even if status files exist
- `--no-images`
- `--no-tables`
- `--max-figures N`
- `--ollama-model NAME` — Ollama vision model (auto-detected if omitted)

## Two-stage workflow

### Stage 1: Extract + local processing (automatic)

The pipeline runs two phases in one command:

1. **Docling extraction** — text (markdown), tables (CSV/MD/JSON), and all figure images (PNG)
2. **Local figure processing** — each figure is classified and described by Ollama. Results are written to per-figure status files.

Figures are classified and routed:

- **Resolved locally** — logos, icons, simple photos
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

- **Docling is required.** There is no fallback PDF extractor — if Docling fails, the error propagates.
- Figures that Docling cannot extract an image for are skipped (logged as warnings), not replaced with placeholders.
- Local vision models (moondream, llava) hallucinate on complex figures — they're used for classification/triage only, not precision extraction.
- Complex figures (plots, pinouts, schematics) are intentionally deferred to external LLM via the rollup report.
