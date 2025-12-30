import os
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.base import BaseIngestor


class SteamWebIngestor(BaseIngestor):
    """Ingestor for Steam Web API app metadata.

    Currently supports:
    - Full app list (appid + name) via the `IStoreService/GetAppList/v1` endpoint.

    Notes
    -----
    - This endpoint requires a Steam Web API key.
    - The key is expected in the `STEAM_API_KEY` environment variable.
    - The endpoint is paginated via `last_appid`; this ingestor will fetch all pages.
    """

    def __init__(
        self,
        raw_root: Path = Path("data/raw"),
    ) -> None:
        super().__init__(
            source_name="steam_web",
            base_url="https://api.steampowered.com",
            raw_root=raw_root,
        )

    def _get_api_key(self) -> str:
        """Return the Steam Web API key or raise a helpful error.

        The key must be provided via the `STEAM_API_KEY` environment variable.
        """

        api_key = os.getenv("STEAM_API_KEY")
        if not api_key:
            raise RuntimeError(
                "STEAM_API_KEY environment variable is not set. "
                "Create a Steam Web API key and export it as STEAM_API_KEY before running ingestion."
            )
        return api_key

    def ingest_app_list(self, include_dlc: bool = True, page_size: int = 50_000) -> None:
        """Ingest the complete Steam app list.

        This method:
        - Paginates through `IStoreService/GetAppList/v1` using `last_appid`.
        - Accumulates all apps into a single list/DataFrame.
        - Persists raw JSON and a Parquet snapshot via the BaseIngestor helpers.
        """

        api_key = self._get_api_key()

        all_apps: list[dict[str, Any]] = []
        last_appid = 0

        while True:
            response = self._get(
                "/IStoreService/GetAppList/v1/",
                params={
                    "key": api_key,
                    "max_results": page_size,
                    "last_appid": last_appid,
                    "include_dlc": "true" if include_dlc else "false",
                },
            )

            # Expected shape: {"response": {"apps": [{"appid": ..., "name": ...}, ...]}}
            page_apps = response.get("response", {}).get("apps", [])
            if not page_apps:
                break

            all_apps.extend(page_apps)
            last_appid = page_apps[-1]["appid"]

            # If we got fewer than a full page, we've reached the end.
            if len(page_apps) < page_size:
                break

        payload = {"apps": all_apps}
        df = pd.DataFrame(all_apps)

        self.save_raw("app_list", payload)
        self.save_parquet("app_list", df)

    def ingest(self, identifier: str) -> None:
        """Generic ingest dispatcher for Steam Web sources."""

        if identifier == "app_list":
            self.ingest_app_list()
        else:
            raise ValueError(f"Unknown identifier: {identifier}")
