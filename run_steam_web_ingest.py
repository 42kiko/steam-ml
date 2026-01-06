"""Einstiegspunkt zum Ausführen des Steam Web Ingestors.

Beispielaufrufe (aus dem Projekt-Root):

    python run_steam_web_ingest.py           # Standard: app_list, DLC inklusive
    python run_steam_web_ingest.py app_list  # explizit app_list
    python run_steam_web_ingest.py app_list --page-size 10000 --no-dlc

Voraussetzungen:
- Abhängigkeiten installiert (am besten via `pip install -e .`)
- Gültiger Steam Web API Key, entweder als
  - Umgebungsvariable `STEAM_API_KEY`, oder
  - in `config/sources/steam_web_api.local.yaml` unter `auth.api_key`.
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
        help="Was soll ingested werden? Aktuell nur 'app_list' unterstützt.",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=50_000,
        help="Anzahl Ergebnisse pro Page (Default: 50000). Kleinere Werte = mehr Requests, aber schneller sichtbares Feedback.",
    )

    parser.add_argument(
        "--no-dlc",
        action="store_true",
        help="DLCs aus der App-Liste ausschließen.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.identifier != "app_list":
        print(f"Unsupported identifier: {args.identifier!r}. Aktuell nur 'app_list' unterstützt.")
        return 1

    include_dlc = not args.no_dlc

    print("[steam-ml] Starte SteamWebIngestor…")
    print(
        f"[steam-ml] identifier = {args.identifier}, page_size = {args.page_size}, include_dlc = {include_dlc}"
    )

    ingestor = SteamWebIngestor()

    try:
        ingestor.ingest_app_list(include_dlc=include_dlc, page_size=args.page_size)
    except Exception as exc:  # noqa: BLE001 - hier wollen wir alles abfangen und schön ausgeben
        print("[steam-ml] FEHLER beim Ingest:")
        print(f"  {type(exc).__name__}: {exc}")
        print("[steam-ml] Prüfe bitte:")
        print("  - Ist dein STEAM_API_KEY korrekt gesetzt (Umgebungsvariable oder local.yaml)?")
        print("  - Hast du eine Internetverbindung?")
        return 1

    print("[steam-ml] Ingest erfolgreich abgeschlossen.")
    print("[steam-ml] Rohdaten: data/raw/steam_web/app_list.json")
    print("[steam-ml] Parquet:  data/bronze/steam_web/app_list.parquet")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI Einstiegspunkt
    raise SystemExit(main(sys.argv[1:]))
