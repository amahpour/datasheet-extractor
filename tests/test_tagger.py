from src.tagger import classify_figure, tags_from_text


def test_tagger_plot() -> None:
    cls = classify_figure("Figure 3. Output voltage plot")
    assert cls.type == "plot"
    assert cls.confidence > 0.5


def test_tagger_block_diagram() -> None:
    cls = classify_figure("Functional block diagram")
    assert cls.type == "block_diagram"


def test_tags() -> None:
    tags = tags_from_text("I2C DAC timing")
    assert "i2c" in tags
    assert "dac" in tags
    assert "timing" in tags
