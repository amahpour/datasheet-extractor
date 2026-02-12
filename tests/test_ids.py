from pathlib import Path

from src.utils import deterministic_id, sha256_file


def test_sha256_stable(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("abc", encoding="utf-8")
    first = sha256_file(target)
    second = sha256_file(target)
    assert first == second


def test_deterministic_id() -> None:
    assert deterministic_id("fig", 1) == "fig_0001"
    assert deterministic_id("table", 12) == "table_0012"
