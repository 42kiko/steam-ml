from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.base import BaseIngestor


class SteamSpyIngestor(BaseIngestor):
    """Ingestor for SteamSpy API data.

    This initial version focuses on the `all` request, which returns a large dictionary of
    apps keyed by appid. It provides a single method that:

    - fetches the full `all` payload from SteamSpy,
    - saves the raw JSON under `data/raw/steam_spy/all.json`,
    - normalizes the records into a flattened Parquet table at
      `data/bronze/steam_spy/all.parquet`.
    """

    def __init__(
        self,
        raw_root: Path = Path("data/raw"),
    ) -> None:
        super().__init__(
            source_name="steam_spy",
            base_url="https://steamspy.com/api.php",
            raw_root=raw_root,
        )

    def ingest_all(self) -> None:
        """Fetch the full `all` dataset from SteamSpy and persist JSON + Parquet.

        See the SteamSpy API docs for details on the shape of this payload. Roughly, it looks
        like:

        { "appid": { ...app data... }, ... }
        """

        self.logger.info("Fetching SteamSpy `all` dataset…")

        payload: dict[str, Any] = self._get("", params={"request": "all"})

        # Save raw JSON as-is.
        self.save_raw("all", payload)

        # Flatten values (app records) into a DataFrame. Keys are appids as strings.
        records: list[dict[str, Any]] = []
        for appid_str, data in payload.items():
            if not isinstance(data, dict):
                continue
            row = {"appid": int(appid_str)}
            row.update(data)
            records.append(row)

        df = pd.json_normalize(records)
        # Cast any object columns to string to avoid Arrow schema issues.
        obj_cols = df.select_dtypes(include="object").columns
        if len(obj_cols) > 0:
            df[obj_cols] = df[obj_cols].astype("string")

        self.save_parquet("all", df)

    def ingest(self, identifier: str) -> None:
        """Generic ingest dispatcher for the SteamSpy ingestor."""

        if identifier == "all":
            self.ingest_all()
        else:
            raise ValueError(f"Unknown identifier: {identifier}")
