import json
from pathlib import Path

import pandas as pd

from src.utils.io import (
    read_parquet_merged,
    write_json,
    write_parquet,
    write_parquet_sharded,
)


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


def test_write_parquet_sharded_and_read_merged(tmp_path: Path) -> None:
    path = tmp_path / "out.parquet"
    # Create a reasonably sized dataframe and force sharding by setting a
    # very small max_file_size_bytes.
    df = pd.DataFrame({"a": range(10_000), "b": ["x"] * 10_000})

    written_paths = write_parquet_sharded(path, df, max_file_size_bytes=10_000)

    # Expect multiple shards and no file written exactly at ``path`` when
    # sharding is enabled.
    assert len(written_paths) > 1
    assert all(p.exists() for p in written_paths)

    merged = read_parquet_merged(path)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), merged)
