from pathlib import Path


def test_plugin_is_documented_as_not_portable() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "SOURCE.md").read_text(encoding="utf-8")
    assert "phronesis-io/eigenflux" in text
    assert "NOASSERTION" in text
    assert "不移植" in text


def test_notice_says_reference_only() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "NOTICE").read_text(encoding="utf-8")
    assert "不包含其任何代码" in text
    assert "NOASSERTION" in text


def test_no_upstream_code_is_shipped() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "plugin.toml").exists()
    assert not (root / "_shared").exists()
    assert not (root / "__init__.py").exists()
