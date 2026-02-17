# Datasheet Extractor

Local-first Python CLI for extracting datasheet PDFs into structured JSON, table exports, figure artifacts, and processing rollup reports.

## Install

### Using Poetry (recommended)

```bash
poetry install
poetry shell  # activate the virtual environment
```

### Using pip

```bash
# Install from local directory
pip install .

# Install directly from GitHub
pip install git+https://github.com/amahpour/datasheet-extractor.git
```

### Ollama (local vision LLM)

The pipeline uses [Ollama](https://ollama.com) to classify and describe extracted figures locally. Install it, then pull a vision model:

```bash
brew install ollama
ollama serve            # or open the Ollama macOS app
ollama pull moondream   # fast, ~1.7GB
```

## Interactive notebook demo

Use the walkthrough notebook to demo the "before vs after" pipeline:

```bash
poetry run pip install jupyter ipykernel
poetry run jupyter notebook notebooks/pipeline_walkthrough.ipynb
```

The notebook shows:

- raw Docling extraction output
- schema-normalized objects and enrichment
- end-to-end `process_pdf()` run with rollups and reports

## CLI usage

Use `--file` to process a single PDF, or `--dir` to process every PDF in a directory.

**Note:** If using Poetry, prefix commands with `poetry run` (e.g., `poetry run datasheet-extract`).

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

With Poetry:

```bash
poetry run datasheet-extract --file ./examples/dac7578/dac5578.pdf --out ./out
poetry run datasheet-extract --dir ./examples --out ./out
poetry run datasheet-smoke-test
```

With pip or as a module:

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
- `--max-tokens N` (default `256`) — max tokens per text block chunk (aligned to embedding model tokenizer)

## Two-stage workflow

### Stage 1: Extract + local processing (automatic)

The pipeline runs two phases in one command:

1. **Docling extraction** — text is chunked using Docling's `HybridChunker`, which provides structure-aware, token-aligned chunks with section heading context. Each chunk carries its parent heading hierarchy and an `enriched_text` field ready for embedding. The chunker uses the `sentence-transformers/all-MiniLM-L6-v2` tokenizer (configurable via `--max-tokens`, default 256). Tables are exported as CSV/MD/JSON, and figure images as PNG.
2. **Local figure processing** — each figure is classified and described by Ollama. Results are written to per-figure status files.

Figures are classified and routed:

- **Resolved locally** — logos, icons, simple photos
- **Needs external LLM** — plots, pinouts, schematics, block diagrams, timing diagrams

### Stage 2: External LLM (manual)

Open `processing_rollup.md` to see what still needs processing. For each figure flagged as `needs_external`, use the prompt template in `prompts/figure_analysis.md` with a vision-capable LLM (GPT-4o, Claude, etc.).

After processing, update the figure's status file in `processing/` to `"status": "resolved_external"` and fill in `external_llm_result`.
Also record which external model produced that result by setting
`external_llm_provider` and `external_llm_model`.

## Output layout

Per PDF (`out/<pdf_stem>/`):

- `document.json` — full extraction: structure-aware chunked text blocks (with headings and enriched text), tables, figures
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
  "local_llm_provider": "ollama",
  "local_llm_model": "moondream",
  "local_llm_description": "Graph showing linearity error vs digital input code...",
  "local_llm_classification": "plot",
  "external_llm_provider": "",
  "external_llm_model": "",
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
- Local vision models (moondream, llava) hallucinate on complex figures — they're used for classification/triage only, not precision extraction. Garbled or non-text output (control characters, `<unk>` tokens) is automatically detected and treated as a failed description.
- Complex figures (plots, pinouts, schematics) are intentionally deferred to external LLM via the rollup report.
- **Docling does not extract figure captions or bounding boxes** for many PDF layouts. Figures will have empty `caption` fields and zeroed `bbox` values. This limits rule-based classification (which falls back to page context or LLM inference).
- **Table header OCR artifacts** (e.g., `THERMAL.THERMAL`, `PACKAGE- LEAD`) are passed through as-is from Docling's table extraction. These are upstream OCR/layout issues, not pipeline bugs.
