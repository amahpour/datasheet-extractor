from __future__ import annotations

import logging
import re
from pathlib import Path

from src.export_figures import derive_description
from src.export_tables import export_table
from src.extract_docling import extract_document, synthesize_placeholder_figure, to_blocks
from src.report import write_manual_report
from src.schema import Classification, Derived, Description, DocStats, Document, Figure, SourceMeta, Table
from src.tagger import classify_figure, tags_from_text
from src.utils import deterministic_id, ensure_dir, parse_page_ranges, sha256_file, write_json

logger = logging.getLogger(__name__)

FIGURE_RE = re.compile(r"\b(fig(?:ure)?\.?\s*\d+[a-zA-Z0-9\-]*)\b", flags=re.IGNORECASE)


def _detect_figures_from_blocks(blocks: list, max_figures: int) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for blk in blocks:
        if len(found) >= max_figures:
            break
        text = blk.text or ""
        for match in FIGURE_RE.finditer(text):
            snippet = text[max(0, match.start() - 30) : min(len(text), match.end() + 80)].replace("\n", " ").strip()
            found.append((blk.page, snippet))
            if len(found) >= max_figures:
                break
    return found


def process_pdf(
    pdf_path: Path,
    out_root: Path,
    pages: str | None = None,
    force: bool = False,
    no_images: bool = False,
    no_tables: bool = False,
    ocr: str = "off",
    max_figures: int = 25,
) -> dict:
    pdf_out = ensure_dir(out_root / pdf_path.stem)
    if force and pdf_out.exists():
        # keep directory but overwrite files deterministically
        pass

    raw = extract_document(pdf_path)
    blocks = to_blocks(raw.get("blocks", []))
    page_filter = parse_page_ranges(pages)
    if page_filter:
        blocks = [b for b in blocks if b.page in page_filter]

    tables: list[Table] = []
    if not no_tables:
        for i, t in enumerate(raw.get("tables", []), start=1):
            table = Table(
                id=deterministic_id("table", i),
                page=int(t.get("page", 1)),
                bbox=[float(x) for x in t.get("bbox", [0, 0, 0, 0])],
                caption=str(t.get("caption", "")),
                tags=tags_from_text(str(t.get("caption", ""))),
                grid=t.get("grid", []),
            )
            export_table(table, pdf_out)
            tables.append(table)

    figures: list[Figure] = []
    if not no_images:
        figures_dir = ensure_dir(pdf_out / "figures")
        for i, (page, caption) in enumerate(_detect_figures_from_blocks(blocks, max_figures=max_figures), start=1):
            fig_id = deterministic_id("fig", i)
            image_path = figures_dir / f"{fig_id}.png"
            synthesize_placeholder_figure(image_path, caption)
            classification = classify_figure(caption, " ".join(b.text[:200] for b in blocks if b.page == page))
            figure = Figure(
                id=fig_id,
                page=page,
                bbox=[0.0, 0.0, 0.0, 0.0],
                caption=caption,
                tags=tags_from_text(caption),
                image_path=str(image_path),
                classification=classification,
                derived=Derived(description=Description(text="", confidence=0.0, notes="")),
            )
            figure = derive_description(figure, ocr_mode=ocr)
            figures.append(figure)

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

    per_pdf_report = write_manual_report(figures, pdf_out)
    return {
        "pdf": str(pdf_path),
        "out_dir": str(pdf_out),
        "document": doc.model_dump(),
        "manual_report": per_pdf_report,
    }


def run_pipeline(
    input_dir: Path,
    out_dir: Path,
    pattern: str = "*.pdf",
    pages: str | None = None,
    force: bool = False,
    no_images: bool = False,
    no_tables: bool = False,
    ocr: str = "off",
    max_figures: int = 25,
) -> dict:
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
            ocr=ocr,
            max_figures=max_figures,
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
    lines.extend([f"- {entry['figure_id']}: {entry['recommended_manual_action']}" for entry in all_entries])
    if not all_entries:
        lines.append("- none")
    (out_dir / "manual_processing_report.md").write_text("\n".join(lines), encoding="utf-8")
    return {"results": results, "global_report": global_report}
