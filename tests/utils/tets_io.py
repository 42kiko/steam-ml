import json
from pathlib import Path

import pandas as pd

from src.utils.io import write_json, write_parquet


def test_write_json(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    payload = {"a": 1, "b": "x"}

    write_json(path, payload)

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_write_parquet(tmp_path: Path) -> None:
    path = tmp_path / "out.parquet"
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    write_parquet(path, df)

    assert path.exists()
    loaded = pd.read_parquet(path)
    pd.testing.assert_frame_equal(df, loaded)
