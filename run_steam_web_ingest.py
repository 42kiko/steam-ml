"""Entry point for running the Steam Web ingestor.

Example invocations (from the project root):

    python run_steam_web_ingest.py           # Default: app_list, DLC included
    python run_steam_web_ingest.py app_list  # explicit app_list
    python run_steam_web_ingest.py app_list --page-size 10000 --no-dlc

Requirements:
- Dependencies installed (preferably via `pip install -e .`).
- Valid Steam Web API key provided either via:
  - environment variable `STEAM_API_KEY`, or
  - `config/sources/steam_web_api.local.yaml` under `auth.api_key`.
"""

from __future__ import annotations

import argparse
import sys

from src.ingestion.steam_web import SteamWebIngestor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Steam Web API ingestor (currently only the full app list).",
    )

    parser.add_argument(
        "identifier",
        nargs="?",
        default="app_list",
        help="What to ingest. Currently only 'app_list' is supported.",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=50_000,
        help=(
            "Number of results per page (default: 50000). "
            "Smaller values → more requests, but faster feedback."
        ),
    )

    parser.add_argument(
        "--no-dlc",
        action="store_true",
        help="Exclude DLCs from the app list.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.identifier != "app_list":
        print(
            f"Unsupported identifier: {args.identifier!r}. Currently only 'app_list' is supported."
        )
        return 1

    include_dlc = not args.no_dlc

    print("[steam-ml] Starting SteamWebIngestor…")
    print(
        f"[steam-ml] identifier = {args.identifier}, page_size = {args.page_size}, include_dlc = {include_dlc}"
    )

    ingestor = SteamWebIngestor()

    try:
        ingestor.ingest_app_list(include_dlc=include_dlc, page_size=args.page_size)
    except Exception as exc:  # noqa: BLE001 - broad except is fine for CLI error reporting
        print("[steam-ml] ERROR during ingest:")
        print(f"  {type(exc).__name__}: {exc}")
        print("[steam-ml] Please check:")
        print("  - Is your STEAM_API_KEY set correctly (environment variable or local.yaml)?")
        print("  - Do you have an active internet connection?")
        return 1

    print("[steam-ml] Ingest finished successfully.")
    print("[steam-ml] Raw data: data/raw/steam_web/app_list.json")
    print("[steam-ml] Parquet:  data/bronze/steam_web/app_list.parquet")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI Einstiegspunkt
    raise SystemExit(main(sys.argv[1:]))
