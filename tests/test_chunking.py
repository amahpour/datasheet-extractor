"""Tests for HybridChunker-based block extraction and the to_blocks mapper."""

from __future__ import annotations

from src.extract_docling import to_blocks


# ---------------------------------------------------------------------------
# to_blocks -- deterministic IDs, page preservation, new fields
# ---------------------------------------------------------------------------


class TestToBlocks:
    def test_deterministic_ids(self) -> None:
        raw = [
            {"page": 1, "text": "chunk1", "type": "text"},
            {"page": 1, "text": "chunk2", "type": "text"},
            {"page": 2, "text": "chunk3", "type": "text"},
        ]
        blocks = to_blocks(raw)
        assert [b.id for b in blocks] == ["blk_0001", "blk_0002", "blk_0003"]

    def test_pages_preserved(self) -> None:
        raw = [
            {"page": 3, "text": "a"},
            {"page": 5, "text": "b"},
        ]
        blocks = to_blocks(raw)
        assert blocks[0].page == 3
        assert blocks[1].page == 5

    def test_no_single_huge_block(self) -> None:
        """Many small raw blocks produce many Block objects."""
        raw = [
            {"page": p, "text": f"Content for page {p}, chunk {c}", "type": "text"}
            for p in range(1, 6)
            for c in range(1, 4)
        ]
        blocks = to_blocks(raw)
        assert len(blocks) == 15
        assert all(b.page >= 1 for b in blocks)

    def test_all_blocks_have_valid_page(self) -> None:
        raw = [{"page": i, "text": f"p{i}"} for i in range(1, 11)]
        blocks = to_blocks(raw)
        for b in blocks:
            assert b.page >= 1

    def test_headings_mapped(self) -> None:
        raw = [
            {
                "page": 1,
                "text": "Some text",
                "headings": ["DESCRIPTION", "Overview"],
                "type": "text",
            }
        ]
        blocks = to_blocks(raw)
        assert blocks[0].headings == ["DESCRIPTION", "Overview"]

    def test_headings_default_empty(self) -> None:
        raw = [{"page": 1, "text": "No headings"}]
        blocks = to_blocks(raw)
        assert blocks[0].headings == []

    def test_enriched_text_mapped(self) -> None:
        raw = [
            {
                "page": 1,
                "text": "Raw text",
                "enriched_text": "DESCRIPTION\n\nRaw text",
                "type": "text",
            }
        ]
        blocks = to_blocks(raw)
        assert blocks[0].enriched_text == "DESCRIPTION\n\nRaw text"

    def test_enriched_text_default_empty(self) -> None:
        raw = [{"page": 1, "text": "No enriched"}]
        blocks = to_blocks(raw)
        assert blocks[0].enriched_text == ""


# ---------------------------------------------------------------------------
# Integration: simulated HybridChunker output -> to_blocks
# ---------------------------------------------------------------------------


class TestHybridChunkerIntegration:
    """Verify that realistic HybridChunker-shaped raw dicts convert correctly."""

    def _make_raw_blocks(self) -> list[dict]:
        """Simulate realistic HybridChunker output for a multi-page datasheet."""
        return [
            {
                "page": 1,
                "text": "The DAC5578 is a low-power, voltage-output DAC.",
                "enriched_text": "DESCRIPTION\n\nThe DAC5578 is a low-power, voltage-output DAC.",
                "headings": ["DESCRIPTION"],
                "type": "text",
                "bbox": [0.0, 0.0, 0.0, 0.0],
            },
            {
                "page": 1,
                "text": "Relative Accuracy: 0.25LSB INL",
                "enriched_text": "1 FEATURES\n\nRelative Accuracy: 0.25LSB INL",
                "headings": ["1 FEATURES"],
                "type": "text",
                "bbox": [0.0, 0.0, 0.0, 0.0],
            },
            {
                "page": 2,
                "text": "Supply voltage range: 2.7V to 5.5V",
                "enriched_text": "ELECTRICAL CHARACTERISTICS\n\nSupply voltage range: 2.7V to 5.5V",
                "headings": ["ELECTRICAL CHARACTERISTICS"],
                "type": "text",
                "bbox": [0.0, 0.0, 0.0, 0.0],
            },
            {
                "page": 3,
                "text": "Pin 1: AVDD",
                "enriched_text": "PIN CONFIGURATION\n\nPin 1: AVDD",
                "headings": ["PIN CONFIGURATION"],
                "type": "text",
                "bbox": [0.0, 0.0, 0.0, 0.0],
            },
            {
                "page": 4,
                "text": "Register map overview",
                "enriched_text": "APPLICATION INFORMATION\nRegister Map\n\nRegister map overview",
                "headings": ["APPLICATION INFORMATION", "Register Map"],
                "type": "text",
                "bbox": [0.0, 0.0, 0.0, 0.0],
            },
        ]

    def test_multiple_blocks_from_multiple_pages(self) -> None:
        blocks = to_blocks(self._make_raw_blocks())
        assert len(blocks) == 5
        pages_seen = {b.page for b in blocks}
        assert pages_seen == {1, 2, 3, 4}

    def test_blocks_have_headings(self) -> None:
        blocks = to_blocks(self._make_raw_blocks())
        for b in blocks:
            assert isinstance(b.headings, list)
        assert blocks[0].headings == ["DESCRIPTION"]
        assert blocks[4].headings == ["APPLICATION INFORMATION", "Register Map"]

    def test_enriched_text_contains_headings(self) -> None:
        blocks = to_blocks(self._make_raw_blocks())
        assert blocks[0].enriched_text.startswith("DESCRIPTION")
        assert "DAC5578" in blocks[0].enriched_text

    def test_deterministic_ids_stable(self) -> None:
        raw = self._make_raw_blocks()
        first_run = to_blocks(raw)
        second_run = to_blocks(raw)
        assert [b.id for b in first_run] == [b.id for b in second_run]

    def test_no_image_placeholder_in_blocks(self) -> None:
        blocks = to_blocks(self._make_raw_blocks())
        for b in blocks:
            assert "<!-- image -->" not in b.text
            assert "![" not in b.text
