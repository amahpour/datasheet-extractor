"""Tests for the one-shot external analysis prompt generator."""

from __future__ import annotations

import json
from pathlib import Path

from src.prompt_generator import BATCH_SIZE, generate_prompt, write_prompt


def _make_status(fig_id: str, status: str = "needs_external", confidence: float = 0.3) -> dict:
    return {
        "figure_id": fig_id,
        "image_path": f"/abs/path/figures/{fig_id}.png",
        "status": status,
        "stage": "local_llm",
        "local_llm_classification": "other",
        "local_llm_description": "Some description text here.",
        "confidence": confidence,
        "needs_external": status == "needs_external",
        "processed_at": "2026-01-01T00:00:00Z",
    }


def _populate_processing_dir(processing_dir: Path, statuses: list[dict]) -> None:
    processing_dir.mkdir(parents=True, exist_ok=True)
    for s in statuses:
        (processing_dir / f"{s['figure_id']}.json").write_text(
            json.dumps(s, indent=2), encoding="utf-8"
        )


def test_generate_prompt_returns_none_when_no_figures(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    processing_dir.mkdir()
    result = generate_prompt(processing_dir, tmp_path / "analysis")
    assert result is None


def test_generate_prompt_includes_absolute_paths(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    statuses = [_make_status("fig_0001"), _make_status("fig_0002")]
    _populate_processing_dir(processing_dir, statuses)

    prompt = generate_prompt(processing_dir, tmp_path / "analysis")
    assert prompt is not None
    assert "/abs/path/figures/fig_0001.png" in prompt
    assert "/abs/path/figures/fig_0002.png" in prompt


def test_generate_prompt_batches_correctly(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    # Create 25 figures — should produce 2 batches (20 + 5).
    statuses = [_make_status(f"fig_{i:04d}") for i in range(1, 26)]
    _populate_processing_dir(processing_dir, statuses)

    prompt = generate_prompt(processing_dir, tmp_path / "analysis")
    assert prompt is not None
    assert "Batch 1 of 2" in prompt
    assert "Batch 2 of 2" in prompt
    assert "(20 figures)" in prompt
    assert "(5 figures)" in prompt


def test_generate_prompt_skips_resolved_local(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    statuses = [
        _make_status("fig_0001", status="resolved_local", confidence=0.7),
        _make_status("fig_0002", status="needs_external", confidence=0.3),
    ]
    _populate_processing_dir(processing_dir, statuses)

    prompt = generate_prompt(processing_dir, tmp_path / "analysis")
    assert prompt is not None
    assert "fig_0001" not in prompt
    assert "fig_0002" in prompt


def test_generate_prompt_contains_subagent_instructions(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    _populate_processing_dir(processing_dir, [_make_status("fig_0001")])

    prompt = generate_prompt(processing_dir, tmp_path / "analysis")
    assert prompt is not None
    assert "subagent" in prompt.lower() or "parallel" in prompt.lower()
    assert "status update" in prompt.lower()


def test_write_prompt_creates_file(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    _populate_processing_dir(processing_dir, [_make_status("fig_0001")])

    output = tmp_path / "output" / "prompt.md"
    result = write_prompt(processing_dir, tmp_path / "analysis", output)
    assert result == output
    assert output.exists()
    assert "fig_0001" in output.read_text(encoding="utf-8")


def test_write_prompt_returns_none_when_empty(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    processing_dir.mkdir()
    output = tmp_path / "output" / "prompt.md"
    result = write_prompt(processing_dir, tmp_path / "analysis", output)
    assert result is None
    assert not output.exists()


def test_generate_prompt_includes_template(tmp_path: Path) -> None:
    processing_dir = tmp_path / "processing"
    _populate_processing_dir(processing_dir, [_make_status("fig_0001")])

    template = tmp_path / "template.md"
    template.write_text("## Custom Schema\nUse this JSON format.", encoding="utf-8")

    prompt = generate_prompt(processing_dir, tmp_path / "analysis", template)
    assert prompt is not None
    assert "Custom Schema" in prompt
