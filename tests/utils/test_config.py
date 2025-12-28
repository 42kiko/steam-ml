from pathlib import Path

from src.utils.config import load_yaml


def test_load_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("foo: bar\nnum: 1", encoding="utf-8")

    data = load_yaml(yaml_file)

    assert data["foo"] == "bar"
    assert data["num"] == 1
