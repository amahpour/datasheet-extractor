# Datasheet Extractor

Local-first Python CLI for extracting datasheet PDFs into structured JSON, table exports, figure artifacts, and manual follow-up reports.

## Install

```bash
pip install .
```

Optional extras:

```bash
pip install .[ocr]
pip install .[vision]
```

## CLI usage

Console scripts (installed by `pip install .`):

```bash
datasheet-extract --input ./examples --out ./out --glob "*.pdf"
datasheet-smoke-test
```

Python module invocation:

```bash
python -m cli.ds_extract --input ./examples --out ./out
python -m cli.smoke_test
```

### Options

`datasheet-extract` supports:

- `--input` (default `./examples`)
- `--out` (default `./out`)
- `--glob` (default `*.pdf`)
- `--pages "1-3,7"`
- `--force`
- `--no-images`
- `--no-tables`
- `--ocr {off,on,auto}` (default `off`)
- `--max-figures N`

## Output layout

Per PDF (`out/<pdf_stem>/`):

- `document.json`
- `index.json`
- `figures/fig_0001.png`
- `tables/table_0001.{json,csv,md}`
- `derived/figures/fig_0001/meta.json`
- `derived/figures/fig_0001/description.md`
- `manual_processing_report.{md,json}`

Global (`out/`):

- `index.json`
- `manual_processing_report.{md,json}`

## Manual processing report

Every figure gets a rule-based recommendation:

- `LLM: describe image`
- `LLM: convert plot to CSV`
- `LLM: convert diagram to ASCII/Mermaid`
- `none`

No external LLM/API calls are made. The pipeline is local-only.

## Caveats

- Docling extraction behavior varies by PDF type.
- OCR is optional and best-effort.
- Diagram/plot understanding is intentionally conservative and deferred to manual/LLM follow-up via reports.
