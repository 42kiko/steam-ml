"""Entry point for running the SteamSpy ingestor.

Currently supports fetching the global `all` dataset from SteamSpy, which contains aggregate
stats (owners, playtime estimates, etc.) for a large number of apps.

Example usage (from the project root):

    python run_steam_spy_ingest.py          # default: identifier = "all"
    python run_steam_spy_ingest.py all

Output:
- Raw JSON:   data/raw/steam_spy/all.json
- Parquet:    data/bronze/steam_spy/all.parquet
"""

from __future__ import annotations

import argparse
import sys

from src.ingestion.steam_spy import SteamSpyIngestor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the SteamSpy ingestor. Currently only the global `all` dataset " "is supported."
        ),
    )

    parser.add_argument(
        "identifier",
        nargs="?",
        default="all",
        help="What to ingest from SteamSpy. Currently only 'all' is supported.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.identifier != "all":
        print(f"Unsupported identifier: {args.identifier!r}. Currently only 'all' is supported.")
        return 1

    print("[steam-ml] Starting SteamSpyIngestor…")
    print(f"[steam-ml] identifier = {args.identifier}")

    ingestor = SteamSpyIngestor()

    try:
        ingestor.ingest_all()
    except Exception as exc:  # noqa: BLE001 - broad except is fine for CLI error reporting
        print("[steam-ml] ERROR during SteamSpy ingest:")
        print(f"  {type(exc).__name__}: {exc}")
        return 1

    print("[steam-ml] SteamSpy ingest finished successfully.")
    print("[steam-ml] Raw data:  data/raw/steam_spy/all.json")
    print("[steam-ml] Parquet:   data/bronze/steam_spy/all.parquet")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main(sys.argv[1:]))
