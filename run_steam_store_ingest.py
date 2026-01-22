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
import time
from pathlib import Path

import pandas as pd

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
        default=100000,
        help=(
            "Maximum number of apps to fetch in this run. Default: 200. "
            "Large values can take a long time (one request per app)."
        ),
    )

    parser.add_argument(
        "--request-delay",
        type=float,
        default=1.4,
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

    parser.add_argument(
        "--until-complete",
        action="store_true",
        help=(
            "If set, keep running ingest passes in batches until no new apps are "
            "added to app_details.parquet. This lets you start the script once "
            "and have it work through the full app list over time."
        ),
    )

    parser.add_argument(
        "--loop-sleep",
        type=float,
        default=300.0,
        help=(
            "Seconds to sleep between ingest passes when --until-complete is "
            "enabled. Default: 300 seconds (5 minutes)."
        ),
    )

    return parser.parse_args(argv)


def _count_ingested_appids() -> int:
    """Return the number of unique appids currently stored in app_details.parquet."""

    parquet_path = Path("data/bronze") / "steam_store" / "app_details.parquet"
    if not parquet_path.exists():
        return 0

    df = pd.read_parquet(parquet_path)
    if df.empty or "appid" not in df.columns:
        return 0

    return int(df["appid"].dropna().astype("int64").nunique())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print("[steam-ml] Starting SteamStoreIngestor…")
    print(
        f"[steam-ml] app_list_parquet = {args.app_list_parquet}, "
        f"limit = {args.limit}, cc = {args.cc}, language = {args.language}"
    )
    if args.until_complete:
        print(f"[steam-ml] until_complete mode enabled: loop-sleep = {args.loop_sleep} seconds")

    ingestor = SteamStoreIngestor(request_delay=args.request_delay)

    if not args.until_complete:
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
    else:
        # Long-running mode: keep running ingest passes until no new appids are added.
        try:
            prev_count = _count_ingested_appids()
            print(f"[steam-ml] Apps with store details before loop: {prev_count}")

            while True:
                print("[steam-ml] Starting ingest pass…")
                ingestor.ingest_from_app_list(
                    app_list_parquet=args.app_list_parquet,
                    limit=args.limit,
                    cc=args.cc,
                    language=args.language,
                )

                current_count = _count_ingested_appids()
                print(f"[steam-ml] Apps with store details after pass: {current_count}")

                if current_count <= prev_count:
                    print(
                        "[steam-ml] No new apps ingested in last pass. "
                        "Assuming all available apps have been processed."
                    )
                    break

                prev_count = current_count

                print(f"[steam-ml] Sleeping {args.loop_sleep} seconds before next pass…")
                time.sleep(args.loop_sleep)

        except Exception as exc:  # noqa: BLE001 - broad except is fine for CLI error reporting
            print("[steam-ml] ERROR during store ingest loop:")
            print(f"  {type(exc).__name__}: {exc}")
            return 1

    print("[steam-ml] Store ingest finished successfully.")
    print("[steam-ml] Raw data:  data/raw/steam_store/app_details.json")
    print("[steam-ml] Parquet:   data/bronze/steam_store/app_details.parquet")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI Einstiegspunkt
    raise SystemExit(main(sys.argv[1:]))
