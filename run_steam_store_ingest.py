"""Entry point for running the Steam Store ingestor.

Example invocations (from the project root):

    python run_steam_store_ingest.py              # Default: 200 apps, US store, English
    python run_steam_store_ingest.py --limit 500  # more apps
    python run_steam_store_ingest.py --cc de --language german

Requirements:
- `data/bronze/steam_web/app_list.parquet` exists (Steam Web ingestor has been run).
- Dependencies are installed (preferably via `pip install -e .` or `make setup`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.ingestion.steam_store import SteamStoreIngestor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Steam Store app details for a subset of apps from "
            "data/bronze/steam_web/app_list.parquet."
        ),
    )

    parser.add_argument(
        "--app-list-parquet",
        type=Path,
        default=Path("data/bronze/steam_web/app_list.parquet"),
        help="Path to the app list (Parquet) produced by the Steam Web ingestor.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help=(
            "Maximum number of apps to fetch in this run. Default: 200. "
            "Large values can take a long time (one request per app)."
        ),
    )

    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.3,
        help=(
            "Seconds to sleep between requests to respect the store rate limit. "
            "0 = no delay (not recommended)."
        ),
    )

    parser.add_argument(
        "--cc",
        default="us",
        help="Country code, e.g. 'us', 'de'. Affects prices / availability.",
    )

    parser.add_argument(
        "--language",
        default="english",
        help="Language of the store data, e.g. 'english', 'german'.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print("[steam-ml] Starting SteamStoreIngestor…")
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
    except Exception as exc:  # noqa: BLE001 - broad except is fine for CLI error reporting
        print("[steam-ml] ERROR during store ingest:")
        print(f"  {type(exc).__name__}: {exc}")
        return 1

    print("[steam-ml] Store ingest finished successfully.")
    print("[steam-ml] Raw data:  data/raw/steam_store/app_details.json")
    print("[steam-ml] Parquet:   data/bronze/steam_store/app_details.parquet")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI Einstiegspunkt
    raise SystemExit(main(sys.argv[1:]))
