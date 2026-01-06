"""Einstiegspunkt zum Ausführen des Steam Store Ingestors.

Beispielaufrufe (aus dem Projekt-Root):

    python run_steam_store_ingest.py              # Standard: 200 Apps, US-Store, englisch
    python run_steam_store_ingest.py --limit 500  # mehr Apps
    python run_steam_store_ingest.py --cc de --language german

Voraussetzungen:
- `data/bronze/steam_web/app_list.parquet` existiert (Steam Web Ingestor wurde ausgeführt).
- Abhängigkeiten installiert (am besten via `pip install -e .` oder `make setup`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.ingestion.steam_store import SteamStoreIngestor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Steam Store app details für eine Teilmenge der Apps aus "
            "data/bronze/steam_web/app_list.parquet."
        ),
    )

    parser.add_argument(
        "--app-list-parquet",
        type=Path,
        default=Path("data/bronze/steam_web/app_list.parquet"),
        help="Pfad zur App-Liste (Parquet) aus dem Steam Web Ingestor.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help=(
            "Wie viele Apps maximal abfragen? Default: 200. "
            "Zu groß kann lange dauern (ein Request pro App)."
        ),
    )

    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.3,
        help=(
            "Sekunden Pause zwischen Requests, um das Rate-Limit zu respektieren. "
            "0 = keine Pause (nicht empfohlen)."
        ),
    )

    parser.add_argument(
        "--cc",
        default="us",
        help="Ländercode, z.B. 'us', 'de'. Beeinflusst Preise / Verfügbarkeit.",
    )

    parser.add_argument(
        "--language",
        default="english",
        help="Sprache der Store-Daten, z.B. 'english', 'german'.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print("[steam-ml] Starte SteamStoreIngestor…")
    print(
        f"[steam-ml] app_list_parquet = {args.app_list_parquet}, "
        f"limit = {args.limit}, cc = {args.cc}, language = {args.language}"
    )

    ingestor = SteamStoreIngestor(request_delay=args.request_delay)

    try:
        ingestor.ingest_from_app_list(
            app_list_parquet=args.app_list_parquet,
            limit=args.limit,
            cc=args.cc,
            language=args.language,
        )
    except Exception as exc:  # noqa: BLE001 - hier wollen wir alles abfangen und schön ausgeben
        print("[steam-ml] FEHLER beim Ingest der Store-Daten:")
        print(f"  {type(exc).__name__}: {exc}")
        return 1

    print("[steam-ml] Store-Ingest erfolgreich abgeschlossen.")
    print("[steam-ml] Rohdaten:  data/raw/steam_store/app_details.json")
    print("[steam-ml] Parquet:   data/bronze/steam_store/app_details.parquet")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI Einstiegspunkt
    raise SystemExit(main(sys.argv[1:]))
