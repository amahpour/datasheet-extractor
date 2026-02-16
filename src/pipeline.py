"""Top-level pipeline orchestration for datasheet extraction."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from src.export_figures import derive_description
from src.export_tables import export_table
from src.extract_docling import DEFAULT_MAX_TOKENS, extract_document, to_blocks
from src.local_processor import process_all_figures, read_status, write_rollup
from src.report import write_manual_report
from src.schema import (
    Derived,
    Description,
    DocStats,
    Document,
    Figure,
    SourceMeta,
    Table,
)
from src.tagger import classify_figure, tags_from_text
from src.utils import (
    deterministic_id,
    ensure_dir,
    parse_page_ranges,
    sha256_file,
    write_json,
)

logger = logging.getLogger(__name__)


def process_pdf(
    pdf_path: Path,
    out_root: Path,
    pages: str | None = None,
    force: bool = False,
    no_images: bool = False,
    no_tables: bool = False,
    max_figures: int = 25,
    ollama_model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Process a single PDF and persist all per-document artifacts."""
    pdf_out = ensure_dir(out_root / pdf_path.stem)

    # Clean stale artifacts from prior runs so downstream consumers never
    # see orphaned figures, processing statuses, or derived files.
    for subdir in ("figures", "tables", "processing", "derived"):
        stale = pdf_out / subdir
        if stale.is_dir():
            shutil.rmtree(stale)

    # Pass ``out_dir`` so Docling can write figure images directly to disk.
    raw = extract_document(
        pdf_path,
        out_dir=pdf_out if not no_images else None,
        max_tokens=max_tokens,
    )
    blocks = to_blocks(raw.get("blocks", []))
    page_filter = parse_page_ranges(pages)
    if page_filter:
        blocks = [b for b in blocks if b.page in page_filter]

    # Stage 1: normalize and export structured tables.
    tables: list[Table] = []
    if not no_tables:
        for i, t in enumerate(raw.get("tables", []), start=1):
            table_page = int(t.get("page", 1))
            if page_filter and table_page not in page_filter:
                continue
            table = Table(
                id=deterministic_id("table", i),
                page=table_page,
                bbox=[float(x) for x in t.get("bbox", [0, 0, 0, 0])],
                caption=str(t.get("caption", "")),
                tags=tags_from_text(str(t.get("caption", ""))),
                grid=t.get("grid", []),
            )
            export_table(table, pdf_out)
            tables.append(table)

    # Stage 2: normalize figures and attach lightweight local descriptions.
    figures: list[Figure] = []
    if not no_images:
        raw_figures = raw.get("figures", [])
        for i, fig_data in enumerate(raw_figures[:max_figures], start=1):
            fig_id = fig_data.get("id", deterministic_id("fig", i))
            caption = fig_data.get("caption", "")
            page = fig_data.get("page", 1)
            if page_filter and page not in page_filter:
                continue
            image_path = fig_data.get("image_path", "")

            # Use same-page text as weak context for rule-based classification.
            context = " ".join(b.text[:200] for b in blocks if b.page == page)
            classification = classify_figure(caption, context)

            figure = Figure(
                id=fig_id,
                page=page,
                bbox=[float(x) for x in fig_data.get("bbox", [0.0, 0.0, 0.0, 0.0])],
                caption=caption,
                tags=tags_from_text(caption),
                image_path=image_path,
                classification=classification,
                derived=Derived(
                    description=Description(text="", confidence=0.0, notes="")
                ),
            )
            figure = derive_description(figure)
            figures.append(figure)

        # Keep only finalized figure images so output artifacts match the
        # filtered figure list (e.g., page filters / max_figures limits).
        figures_dir = pdf_out / "figures"
        if figures_dir.is_dir():
            keep_names = {Path(f.image_path).name for f in figures if f.image_path}
            removed = 0
            for img_path in figures_dir.glob("*.png"):
                if img_path.name not in keep_names:
                    img_path.unlink()
                    removed += 1
            if removed:
                logger.info("Removed %d unreferenced figure image(s)", removed)

    stat = pdf_path.stat()
    doc = Document(
        source=SourceMeta(
            path=str(pdf_path),
            sha256=sha256_file(pdf_path),
            size=stat.st_size,
            mtime=stat.st_mtime,
        ),
        doc_stats=DocStats(
            page_count=int(raw.get("page_count", 0)),
            block_count=len(blocks),
            table_count=len(tables),
            figure_count=len(figures),
        ),
        blocks=blocks,
        tables=tables,
        figures=figures,
    )

    write_json(pdf_out / "document.json", doc.model_dump())
    write_json(
        pdf_out / "index.json",
        {
            "pdf": str(pdf_path),
            "document_json": str(pdf_out / "document.json"),
            "figures": [f.image_path for f in figures],
            "tables": [t.json_path for t in tables],
        },
    )

    for figure in figures:
        derived_dir = ensure_dir(pdf_out / "derived" / "figures" / figure.id)
        write_json(derived_dir / "meta.json", {"figure": figure.model_dump()})
        (derived_dir / "description.md").write_text(
            f"# {figure.id}\n\n{figure.derived.description.text}\n",
            encoding="utf-8",
        )

    # Stage 2.5: local vision LLM pass with per-figure status files.
    processing_statuses = []
    if not no_images and (pdf_out / "figures").is_dir():
        processing_dir = ensure_dir(pdf_out / "processing")
        logger.info("Running local figure processing for %s ...", pdf_path.stem)
        # Only process figures that survived the page filter.
        filtered_ids = {f.id for f in figures} if page_filter else None
        processing_statuses = process_all_figures(
            figures_dir=pdf_out / "figures",
            processing_dir=processing_dir,
            ollama_model=ollama_model,
            force=force,
            figure_ids=filtered_ids,
        )
        # Fold local LLM results back into the Figure objects so that
        # document.json, derived files, and the manual report all reflect
        # the actual LLM output rather than pre-LLM placeholders.
        for figure in figures:
            status = read_status(processing_dir, figure.id)
            if status is None:
                continue
            desc_text = status.get("local_llm_description", "")
            llm_cls = status.get("local_llm_classification", "")

            # Update the figure classification from LLM inference when
            # the rule-based classifier had no signal (empty caption).
            if llm_cls and figure.classification.type == "other":
                figure.classification.type = llm_cls
                figure.classification.confidence = status.get("confidence", 0.0)
                figure.classification.rationale = "local_llm classification"

            if desc_text:
                figure.derived.description.text = desc_text
                figure.derived.description.confidence = status.get("confidence", 0.0)
                figure.derived.description.notes = (
                    f"local_llm ({llm_cls})" if llm_cls else "local_llm"
                )
            elif status.get("stage") == "skip":
                figure.derived.description.text = status.get(
                    "local_llm_description", "Skipped"
                )
                figure.derived.description.notes = "skipped"
            else:
                figure.derived.description.text = "Pending external LLM processing."
                figure.derived.description.notes = "needs_external"

        # Rewrite document.json with updated descriptions and classifications.
        doc.figures = figures
        write_json(pdf_out / "document.json", doc.model_dump())

        # Rewrite per-figure derived description files.
        for figure in figures:
            derived_dir = ensure_dir(pdf_out / "derived" / "figures" / figure.id)
            write_json(derived_dir / "meta.json", {"figure": figure.model_dump()})
            (derived_dir / "description.md").write_text(
                f"# {figure.id}\n\n{figure.derived.description.text}\n",
                encoding="utf-8",
            )

        # Write per-PDF rollup
        rollup = write_rollup(processing_dir, pdf_out)
        logger.info(
            "  Rollup: %d resolved locally, %d need external LLM (%.0f%% complete)",
            rollup["resolved_local"],
            rollup["needs_external"],
            rollup["summary"]["percent_complete"],
        )

    # Write manual report AFTER LLM processing so classifications and
    # descriptions are up-to-date.  This ensures the report's routing
    # decisions are consistent with the processing rollup.
    per_pdf_report = write_manual_report(figures, pdf_out)

    return {
        "pdf": str(pdf_path),
        "out_dir": str(pdf_out),
        "document": doc.model_dump(),
        "manual_report": per_pdf_report,
        "processing_statuses": processing_statuses,
    }


def run_pipeline(
    input_dir: Path,
    out_dir: Path,
    pattern: str = "*.pdf",
    pages: str | None = None,
    force: bool = False,
    no_images: bool = False,
    no_tables: bool = False,
    max_figures: int = 25,
    ollama_model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict:
    """Run the extraction pipeline for all matching PDFs in ``input_dir``."""
    ensure_dir(out_dir)
    pdfs = sorted(input_dir.glob(pattern))
    if not pdfs and pattern == "*.pdf":
        pdfs = sorted(input_dir.glob("**/*.pdf"))
    logger.info("Found %s PDFs in %s matching %s", len(pdfs), input_dir, pattern)
    results = [
        process_pdf(
            pdf,
            out_dir,
            pages=pages,
            force=force,
            no_images=no_images,
            no_tables=no_tables,
            max_figures=max_figures,
            ollama_model=ollama_model,
            max_tokens=max_tokens,
        )
        for pdf in pdfs
    ]
    all_entries = []
    for result in results:
        all_entries.extend(result["manual_report"].get("figures", []))

    global_report = {"figures": all_entries}
    write_json(out_dir / "index.json", {"documents": [r["out_dir"] for r in results]})
    write_json(out_dir / "manual_processing_report.json", global_report)
    lines = ["# Global Manual Processing Report", ""]
    lines.extend(
        [
            f"- {entry['figure_id']}: {entry['recommended_manual_action']}"
            for entry in all_entries
        ]
    )
    if not all_entries:
        lines.append("- none")
    (out_dir / "manual_processing_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )

    # Global rollup across all PDFs
    all_statuses = []
    for result in results:
        all_statuses.extend(result.get("processing_statuses", []))
    if all_statuses:
        from src.local_processor import build_rollup

        global_rollup = build_rollup(all_statuses)
        write_json(out_dir / "processing_rollup.json", global_rollup)
        logger.info(
            "Global rollup: %d/%d figures complete (%.0f%%)",
            global_rollup["summary"]["fully_processed"],
            global_rollup["total_figures"],
            global_rollup["summary"]["percent_complete"],
        )

    return {"results": results, "global_report": global_report}
