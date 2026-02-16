"""Tests for subtitle generation."""

from src.subtitle import SubtitleGenerator
from src.config import Config


def test_generate_produces_ass_content(default_config, sample_messages):
    gen = SubtitleGenerator(default_config)
    content = gen.generate(sample_messages)

    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert "Dialogue:" in content


def test_generate_includes_all_messages(default_config, sample_messages):
    gen = SubtitleGenerator(default_config)
    content = gen.generate(sample_messages)

    dialogue_lines = [line for line in content.split("\n") if line.startswith("Dialogue:")]
    assert len(dialogue_lines) == len(sample_messages)


def test_generate_empty_messages(default_config):
    gen = SubtitleGenerator(default_config)
    content = gen.generate([])

    assert "[Script Info]" in content
    dialogue_lines = [line for line in content.split("\n") if line.startswith("Dialogue:")]
    assert len(dialogue_lines) == 0


def test_write_creates_file(tmp_path, default_config, sample_messages):
    gen = SubtitleGenerator(default_config)
    output = tmp_path / "test.ass"
    gen.write(sample_messages, str(output))

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "[Script Info]" in content


def test_gift_uses_gift_style(default_config, sample_messages):
    gen = SubtitleGenerator(default_config)
    content = gen.generate(sample_messages)

    # The gift message (bob) should use GiftBox style in a Dialogue line
    lines = content.split("\n")
    gift_dialogues = [l for l in lines if l.startswith("Dialogue:") and "GiftBox" in l]
    assert len(gift_dialogues) == 1
