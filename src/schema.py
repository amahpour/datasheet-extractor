from __future__ import annotations

from pydantic import BaseModel, Field


class SourceMeta(BaseModel):
    path: str
    sha256: str
    size: int
    mtime: float


class Classification(BaseModel):
    type: str
    confidence: float
    rationale: str


class Description(BaseModel):
    text: str
    confidence: float
    notes: str


class Derived(BaseModel):
    description: Description


class Block(BaseModel):
    id: str
    type: str
    page: int
    bbox: list[float] = Field(default_factory=list)
    text: str = ""
    heading_level: int | None = None


class Table(BaseModel):
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
    id: str
    page: int
    bbox: list[float] = Field(default_factory=list)
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    image_path: str = ""
    classification: Classification
    derived: Derived


class DocStats(BaseModel):
    page_count: int = 0
    block_count: int = 0
    table_count: int = 0
    figure_count: int = 0


class Document(BaseModel):
    source: SourceMeta
    doc_stats: DocStats
    blocks: list[Block] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
