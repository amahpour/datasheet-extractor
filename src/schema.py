from __future__ import annotations

"""Typed schema objects shared by all pipeline stages."""

from pydantic import BaseModel, Field


class SourceMeta(BaseModel):
    """Source file metadata persisted in each document payload."""

    path: str
    sha256: str
    size: int
    mtime: float


class Classification(BaseModel):
    """Lightweight label assigned to a figure."""

    type: str
    confidence: float
    rationale: str


class Description(BaseModel):
    """Derived textual description for a figure."""

    text: str
    confidence: float
    notes: str


class Derived(BaseModel):
    """Container for enrichment outputs generated after extraction."""

    description: Description


class Block(BaseModel):
    """Textual block extracted from a page."""

    id: str
    type: str
    page: int
    bbox: list[float] = Field(default_factory=list)
    text: str = ""
    heading_level: int | None = None


class Table(BaseModel):
    """Extracted table plus paths to exported artifacts."""

    id: str
    page: int
    bbox: list[float] = Field(default_factory=list)
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    grid: list[list[str]] = Field(default_factory=list)
    markdown_path: str = ""
    csv_path: str = ""
    json_path: str = ""


class Figure(BaseModel):
    """Extracted figure metadata and derived analysis fields."""

    id: str
    page: int
    bbox: list[float] = Field(default_factory=list)
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    image_path: str = ""
    classification: Classification
    derived: Derived


class DocStats(BaseModel):
    """High-level counts for extracted content."""

    page_count: int = 0
    block_count: int = 0
    table_count: int = 0
    figure_count: int = 0


class Document(BaseModel):
    """Top-level normalized document structure written to ``document.json``."""

    source: SourceMeta
    doc_stats: DocStats
    blocks: list[Block] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
