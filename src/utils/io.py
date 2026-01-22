import json
from pathlib import Path
from typing import Any

import pandas as pd

# Soft file size limit for GitHub in bytes (100 MiB)
MAX_GITHUB_FILE_SIZE_BYTES = 100 * 1024 * 1024


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    """Write a single parquet file.

    This is a thin wrapper used where we know the payload is small.
    For large dataframes that may exceed GitHub's 100 MiB file limit,
    prefer :func:`write_parquet_sharded`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _estimate_bytes_per_row(df: pd.DataFrame) -> float:
    """Roughly estimate the number of bytes per row in the dataframe.

    We use the in-memory size as an upper bound for parquet size on disk.
    The estimate does not need to be perfect; it is only used to decide
    how many rows to place in each shard.
    """

    if df.empty:
        return 0.0

    total_bytes = df.memory_usage(index=False, deep=True).sum()
    return float(total_bytes) / float(len(df))


def write_parquet_sharded(
    path: Path,
    df: pd.DataFrame,
    *,
    max_file_size_bytes: int = MAX_GITHUB_FILE_SIZE_BYTES,
) -> list[Path]:
    """Write a dataframe to one or more parquet files capped at ``max_file_size_bytes``.

    The base ``path`` is used as a logical identifier. If the dataframe is
    small enough, a single file is written to ``path``. For larger
    dataframes, multiple shard files are written next to it using the
    following naming scheme::

        {path.stem}_part000{path.suffix}
        {path.stem}_part001{path.suffix}
        ...

    The function returns the list of file paths that were written.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if df.empty:
        # Nothing to shard, but we still create a single (empty) file so the
        # dataset can be discovered and loaded later.
        df.to_parquet(path, index=False)
        return [path]

    est_bytes_per_row = _estimate_bytes_per_row(df)

    # If our estimate says the whole dataframe is below the limit, write it
    # as a single file for simplicity.
    if est_bytes_per_row * len(df) <= max_file_size_bytes:
        df.to_parquet(path, index=False)
        return [path]

    # Otherwise compute how many rows fit into a single shard. We guard
    # against degenerate cases where the estimate is zero or very small.
    rows_per_shard = max(1, int(max_file_size_bytes // max(1.0, est_bytes_per_row)))

    written_paths: list[Path] = []
    start = 0
    shard_idx = 0

    while start < len(df):
        end = min(start + rows_per_shard, len(df))
        shard = df.iloc[start:end]
        shard_path = path.with_name(f"{path.stem}_part{shard_idx:03d}{path.suffix}")
        shard.to_parquet(shard_path, index=False)
        written_paths.append(shard_path)

        shard_idx += 1
        start = end

    return written_paths


def read_parquet_merged(path: Path) -> pd.DataFrame:
    """Load a dataframe from a (potentially sharded) parquet dataset.

    This helper looks for shard files written by
    :func:`write_parquet_sharded`. If any shard files are present they are
    read and concatenated. If no shards are found, it falls back to reading
    ``path`` as a single parquet file.
    """

    path = Path(path)

    # Discover shards following the ``*_partNNN`` naming scheme.
    pattern = f"{path.stem}_part*{path.suffix}"
    shard_paths = sorted(path.parent.glob(pattern))

    if shard_paths:
        frames = [pd.read_parquet(p) for p in shard_paths]
        if not frames:
            # Should not happen, but defensively handle it.
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    # Fallback: attempt to read a single parquet file at ``path``.
    return pd.read_parquet(path)
