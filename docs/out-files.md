# Output Files in `out/`

This document describes every output artifact generated under `out/` by the current `src/` pipeline, including interim files.

## Scope

- Based on writers in `src/` (`pipeline.py`, `extract_docling.py`, `export_tables.py`, `report.py`, `local_processor.py`).
- Includes both per-document outputs (`out/<pdf_stem>/...`) and global outputs (`out/...`).
- Path patterns use placeholders:
  - `<pdf_stem>`: source PDF filename stem (for example `dac5578`)
  - `<fig_id>`: `fig_0001` style ID
  - `<table_id>`: `table_0001` style ID

## Per-Document Artifacts (`out/<pdf_stem>/...`)

| Path pattern | Type | Stage | Produced by | Purpose |
|---|---|---|---|---|
| `out/<pdf_stem>/document.json` | Final | Structured export | `src/pipeline.py::process_pdf` | Canonical normalized document payload (`source`, stats, blocks, tables, figures). |
| `out/<pdf_stem>/index.json` | Final | Structured export | `src/pipeline.py::process_pdf` | Per-document index of key artifact paths (`document_json`, figure image paths, table JSON paths). |
| `out/<pdf_stem>/tables/<table_id>.json` | Final | Table export | `src/export_tables.py::export_table` | Table content as structured JSON (`id`, `grid`, `caption`). |
| `out/<pdf_stem>/tables/<table_id>.csv` | Final | Table export | `src/export_tables.py::export_table` | Flattened CSV table export. |
| `out/<pdf_stem>/tables/<table_id>.md` | Final | Table export | `src/export_tables.py::export_table` | Markdown table rendering. |
| `out/<pdf_stem>/figures/<fig_id>.png` | Final input to downstream | Docling extraction | `src/extract_docling.py::_extract_with_docling` | Figure images extracted from the PDF. |
| `out/<pdf_stem>/figures/table_img_XXXX.png` | Interim/optional | Docling extraction | `src/extract_docling.py::_extract_with_docling` | Optional table snapshots emitted by Docling `TableItem` image export. |
| `out/<pdf_stem>/derived/figures/<fig_id>/meta.json` | Interim | Figure enrichment | `src/pipeline.py::process_pdf` | Snapshot of enriched `Figure` model (classification + derived description baseline). |
| `out/<pdf_stem>/derived/figures/<fig_id>/description.md` | Interim | Figure enrichment | `src/pipeline.py::process_pdf` | Human-readable initial derived description for the figure. |
| `out/<pdf_stem>/manual_processing_report.json` | Final handoff | Manual/LLM routing | `src/report.py::write_manual_report` | Figure-by-figure recommended next action (`none` vs external LLM/manual). |
| `out/<pdf_stem>/manual_processing_report.md` | Final handoff | Manual/LLM routing | `src/report.py::write_manual_report` | Markdown view of the same manual follow-up recommendations. |
| `out/<pdf_stem>/processing/<fig_id>.json` | Interim (stateful) | Local LLM pass | `src/local_processor.py::write_status` via `process_figure` | Per-figure local processing status (`resolved_local` / `needs_external` / `resolved_external`). |
| `out/<pdf_stem>/processing_rollup.json` | Final for stage 2 orchestration | Local LLM pass | `src/local_processor.py::write_rollup` | Aggregate status summary for the document’s figures. |
| `out/<pdf_stem>/processing_rollup.md` | Final for operators | Local LLM pass | `src/local_processor.py::write_rollup` | Human-readable rollup with pending external-LLM list. |

## Global Artifacts (`out/...`)

| Path | Type | Stage | Produced by | Purpose |
|---|---|---|---|---|
| `out/index.json` | Final | Global aggregation | `src/pipeline.py::run_pipeline` | List of per-document output directories processed in this run. |
| `out/manual_processing_report.json` | Final handoff | Global aggregation | `src/pipeline.py::run_pipeline` | Merged manual/LLM follow-up entries across all PDFs. |
| `out/manual_processing_report.md` | Final handoff | Global aggregation | `src/pipeline.py::run_pipeline` | Markdown summary of merged manual actions. |
| `out/processing_rollup.json` | Final (optional) | Global aggregation | `src/pipeline.py::run_pipeline` + `src/local_processor.py::build_rollup` | Cross-document figure processing completion summary. |

## Conditional Generation Rules

- `--no-tables`: skips `tables/` outputs.
- `--no-images`: skips `figures/`, `derived/figures/`, `processing/`, and per-document `processing_rollup.*`.
- `max_figures` (default `25`): limits figures normalized into `document.json`, `derived/`, reports, and `processing/` files.
  - Note: `figures/*.png` can still contain more images because Docling extraction happens before this cap is applied.
- Global `out/processing_rollup.json` is only written when at least one per-figure processing status exists.

## Notes on Files Seen in `out/` Today

- The current `out/` tree matches the patterns above.
- In this workspace snapshot, `out/dac5578/figures/` contains more figure PNGs than `out/dac5578/processing/` and `out/dac5578/derived/figures/` because `max_figures=25` was applied after extraction.
