# Codex-CLI Datasheet Extractor – Evaluation Report

**Date:** 2025-02-10  
**Scope:** Run the datasheet extractor on examples and judge how well Codex-cli assembled this project.

---

## Summary: Does It Work?

**Yes, but with critical bugs that prevented it from running.** After fixes, the pipeline works and produces meaningful output (text, tables, JSON). Docling integration was incorrect for the current Docling 2.x API.

---

## What Works Well ✓

1. **Project structure** – Clear layout: `cli/` for entry points, `src/` for logic, `examples/`, `tests/`.
2. **CLI design** – Sensible flags (`--input`, `--out`, `--pages`, `--force`, `--max-figures`) and script/module invocation paths.
3. **Schema** – Pydantic models (`Document`, `Block`, `Table`, `Figure`) are well-defined.
4. **Output layout** – Per-PDF folders with `document.json`, `index.json`, tables in CSV/MD/JSON, manual processing report.
5. **Fallback behavior** – Docling failure falls back to pypdf for text extraction.
6. **Placeholder figures** – Figure detection via regex plus placeholder PNG generation.
7. **Manual processing report** – Rule-based recommendations for LLM follow-up.

---

## Bugs Fixed (Blocking Issues)

### 1. `TypeError` on `page_count` (critical)
- **Error:** `int() argument must be a string, a bytes-like object or a real number, not 'method'`
- **Cause:** Docling’s `doc.num_pages` is a callable; `getattr(doc, "num_pages", 0) or len(...)` returned the method instead of calling it.
- **Fix:** Treat `num_pages` as callable and call it when needed.

### 2. Empty text extraction (critical)
- **Effect:** `block_count: 1` with `text: ""`, so no usable content.
- **Cause:** Code assumed `doc.pages` with `page.text`; Docling 2.x uses a different model.
- **Fix:** Use `doc.export_to_markdown()` for text extraction.

### 3. No table extraction
- **Effect:** `table_count` was always 0.
- **Cause:** `tables` was hardcoded to `[]` and Docling’s `document.tables` was never used.
- **Fix:** Iterate `doc.tables`, use `table.export_to_dataframe(doc=doc)`, and map to the internal grid format.

### 4. Missing dependency
- **Effect:** `export_to_dataframe()` requires pandas.
- **Fix:** Add `pandas` to `pyproject.toml` dependencies.

---

## Output Quality (After Fixes)

For `adafruit-dac7578-8-x-channel-12-bit-i2c-dac.pdf` (pages 1–2):

| Metric        | Value          |
|---------------|----------------|
| block_count   | 1 (full markdown) |
| table_count   | 2              |
| figure_count  | 0              |
| Text quality  | Good (markdown with headings, lists, code, links) |
| Tables        | Table of Contents + another table exported to CSV/MD/JSON |

Figure count is 0 because the Adafruit guide uses `<!-- image -->` placeholders rather than “Figure 1” / “fig. 2” style labels; the regex only targets the latter.

---

## Performance

- Docling startup/model loading: ~10–15 seconds.
- Per PDF: ~20–25 seconds on an M1 Mac (MPS).
- Full run on 2 PDFs: ~50+ seconds.
- Resource warning: `resource_tracker: There appear to be 1 leaked semaphore objects` (Docling internals, not this repo).

---

## Verdict

| Criterion          | Grade | Notes |
|--------------------|-------|-------|
| Architecture       | B+    | Solid modular design and clear boundaries |
| Docling integration| D     | Wrong API assumptions, required fixes to work |
| Robustness         | C     | One blocking bug plus empty extraction path |
| Output usefulness  | B     | Good after fixes; markdown + tables + JSON |
| Documentation      | B     | README is clear; API usage wasn’t verified |

**Bottom line:** The project shows good structure and design, but the Docling integration was based on a different or older API and didn’t run without changes. After fixing `page_count`, text extraction, table extraction, and dependencies, it produces useful output for datasheet extraction.
