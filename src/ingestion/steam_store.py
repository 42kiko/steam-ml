from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.base import BaseIngestor


class SteamStoreIngestor(BaseIngestor):
    """Ingestor für Steam Store API App-Details.

    Nutzt den in `data/bronze/steam_web/app_list.parquet` gespeicherten App-Index,
    ruft für ausgewählte App-IDs die Store-Details ab und speichert:

    - rohe JSON-Daten unter:   data/raw/steam_store/app_details.json
    - flache Parquet-Tabelle unter: data/bronze/steam_store/app_details.parquet
    """

    def __init__(
        self,
        raw_root: Path = Path("data/raw"),
        request_delay: float = 0.3,
    ) -> None:
        super().__init__(
            source_name="steam_store",
            base_url="https://store.steampowered.com/api",
            raw_root=raw_root,
        )
        # Kleine Pause zwischen Requests, um das Rate-Limit des Stores zu schonen.
        self.request_delay = request_delay

    def _fetch_single_app(
        self,
        appid: int,
        cc: str = "us",
        language: str = "english",
    ) -> dict[str, Any] | None:
        """Hole die Store-Details für eine einzelne App-ID.

        Siehe z.B. inoffizielle Steam-Store-API:
        https://store.steampowered.com/api/appdetails?appids=<appid>&cc=<cc>&l=<language>
        """

        self.logger.info("Fetching store details for appid=%s", appid)

        payload = self._get(
            "/appdetails",
            params={
                "appids": appid,
                "cc": cc,
                "l": language,
            },
        )

        data = payload.get(str(appid))
        if not data or not data.get("success"):
            self.logger.warning("No store data for appid=%s", appid)
            return None

        app_data = data.get("data") or {}
        # Sicherheitshalber die App-ID noch einmal explizit an den Datensatz hängen.
        app_data.setdefault("appid", appid)
        return app_data

    def ingest_from_app_list(
        self,
        app_list_parquet: Path = Path("data/bronze/steam_web/app_list.parquet"),
        limit: int | None = 200,
        cc: str = "us",
        language: str = "english",
    ) -> None:
        """Enrich die App-Liste um Store-Details für eine begrenzte Anzahl Apps.

        Parameters
        ----------
        app_list_parquet:
            Pfad zur Parquet-Datei mit der App-Liste aus dem Steam Web Ingestor.
        limit:
            Wie viele Apps sollen maximal abgefragt werden? ``None`` bedeutet: alle.
            Achtung: Zu groß => viele HTTP-Requests.
        cc:
            Ländercode (z.B. "us", "de"). Beeinflusst Preise / Verfügbarkeit.
        language:
            Sprache der Store-Daten (z.B. "english", "german").
        """

        if not app_list_parquet.exists():
            raise FileNotFoundError(
                f"App list parquet not found: {app_list_parquet}. "
                "Bitte zuerst den Steam Web Ingestor laufen lassen."
            )

        self.logger.info("Loading app list from %s", app_list_parquet)
        app_df = pd.read_parquet(app_list_parquet)

        if "appid" not in app_df.columns:
            raise ValueError("App list parquet does not contain an 'appid' column")

        # Vollständige, sortierte App-ID-Liste.
        appids_all = app_df["appid"].dropna().astype("int64").sort_values().tolist()

        # Bereits vorhandene Store-Details laden (für inkrementelles Fortsetzen).
        existing_parquet = Path("data/bronze") / "steam_store" / "app_details.parquet"
        ingested_appids: set[int] = set()
        if existing_parquet.exists():
            self.logger.info("Loading existing store details from %s", existing_parquet)
            existing_df = pd.read_parquet(existing_parquet)
            if "appid" not in existing_df.columns:
                raise ValueError("Existing app_details.parquet does not contain an 'appid' column")
            ingested_appids = set(existing_df["appid"].dropna().astype("int64").tolist())

        # Nur App-IDs, die wir noch nicht haben.
        remaining_appids = [a for a in appids_all if a not in ingested_appids]

        if not remaining_appids:
            self.logger.info(
                "All apps from app_list_parquet already have store details in %s",
                existing_parquet,
            )
            return

        if limit is not None:
            target_appids = remaining_appids[:limit]
        else:
            target_appids = remaining_appids

        self.logger.info(
            "Fetching store details for %s apps (remaining total: %s)",
            len(target_appids),
            len(remaining_appids),
        )

        results: list[dict[str, Any]] = []
        for idx, appid in enumerate(target_appids, start=1):
            self.logger.info("[%s/%s] appid=%s", idx, len(target_appids), appid)
            app_data = self._fetch_single_app(appid=appid, cc=cc, language=language)
            if app_data:
                results.append(app_data)
            # Kleine Pause zwischen Requests, um das Rate-Limit zu respektieren.
            if self.request_delay > 0:
                time.sleep(self.request_delay)

        payload: dict[str, Any] = {
            "apps": results,
            "meta": {
                "source": str(app_list_parquet),
                "count": len(results),
                "cc": cc,
                "language": language,
            },
        }

        # Roh-JSON speichern
        self.save_raw("app_details", payload)

        # Etwas flachere Parquet-Tabelle mittels json_normalize.
        if results:
            details_df = pd.json_normalize(results)

            # Steam liefert in vielen Feldern gemischte Typen (int, str, Listen, dicts).
            # PyArrow ist da empfindlich → wir casten alle "object"-Spalten auf String,
            # damit das Schema stabil wird.
            obj_cols = details_df.select_dtypes(include="object").columns
            if len(obj_cols) > 0:
                details_df[obj_cols] = details_df[obj_cols].astype("string")
        else:
            details_df = pd.DataFrame()

        # Neue Ergebnisse mit bestehenden Parquet-Daten zusammenführen (inkrementelles Update).
        existing_parquet = Path("data/bronze") / "steam_store" / "app_details.parquet"
        if existing_parquet.exists():
            existing_df = pd.read_parquet(existing_parquet)
            if not existing_df.empty:
                combined = pd.concat([existing_df, details_df], ignore_index=True)
                if "appid" in combined.columns:
                    combined = combined.drop_duplicates(subset=["appid"], keep="last")
            else:
                combined = details_df
        else:
            combined = details_df

        self.save_parquet("app_details", combined)

    def ingest(self, identifier: str) -> None:
        """Generic ingest dispatcher für den Steam Store Ingestor."""

        if identifier == "app_details_from_app_list":
            self.ingest_from_app_list()
        else:
            raise ValueError(f"Unknown identifier: {identifier}")
