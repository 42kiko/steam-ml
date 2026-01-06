# steam-ml-platform 🚂🎮

A small end-to-end **data science & ML playground for Steam data**. The goal is to build a clean
pipeline that pulls raw data from Steam (and related APIs), normalizes it into Parquet, and turns
it into feature-ready datasets for **EDA, forecasting, and machine learning** (e.g. game success
prediction, recommendation, trend analysis).

## ✨ Features (current state)

- ✅ **Steam Web API ingestor**
  - Fetches the global app list (appid + name, last_modified, etc.).
  - Persists raw JSON and a Parquet snapshot.
- ✅ **Steam Store API ingestor**
  - Fetches detailed store metadata (type, name, price info, age rating, etc.).
  - Works **incrementally**: each run only fetches apps that are not yet in the store dataset.
- ✅ **Local data lake layout**
  - `data/raw/<source>` for raw JSON payloads.
  - `data/bronze/<source>` for normalized Parquet tables.
- ✅ **Basic test suite & tooling**
  - Pytest, Black, Ruff, pre-commit hooks.

---

## 🧱 Project structure

```text path=null start=null
steam-ml/
├─ config/
│  └─ sources/
│     ├─ steam_web_api.yaml           # Steam Web API config (placeholder key; ignored in git)
│     └─ steam_web_api.local.yaml     # Local override with your real key (git-ignored)
├─ data/
│  ├─ raw/
│  │  ├─ steam_web/                   # Raw JSON from Steam Web API
│  │  └─ steam_store/                 # Raw JSON from Steam Store API
│  └─ bronze/
│     ├─ steam_web/                   # Parquet tables for Steam Web data
│     └─ steam_store/                 # Parquet tables for Steam Store data
├─ src/
│  ├─ ingestion/
│  │  ├─ base.py                      # BaseIngestor with HTTP client, retries, persistence
│  │  ├─ steam_web.py                 # Steam Web API ingestor (app list)
│  │  ├─ steam_store.py               # Steam Store API ingestor (app details, incremental)
│  │  ├─ steam_spy.py                 # Placeholder for future SteamSpy ingestor
│  │  └─ __init__.py
│  └─ utils/
│     ├─ config.py                    # YAML config loader
│     ├─ io.py                        # JSON / Parquet IO helpers
│     └─ logging.py                   # Simple logger helper
├─ tests/
│  ├─ ingestion/                      # Tests for BaseIngestor behavior
│  └─ utils/                          # Tests for utils (config, IO, logging)
├─ run_steam_web_ingest.py            # CLI entrypoint for Steam Web app list
├─ run_steam_store_ingest.py          # CLI entrypoint for Steam Store app details
├─ pyproject.toml                     # Dependencies & tooling config
├─ README.md                          # You are here
└─ WARP.md                            # Notes for warp.dev agents
```

---

## 🔧 Requirements

- Python **3.11** (see `pyproject.toml`)
- A working `git` installation
- Windows, macOS, or Linux (examples below use Windows PowerShell, but commands are generic)

---

## 🚀 Getting started

### 1. Clone the repository

```bash path=null start=null
git clone <your-fork-or-repo-url>
cd steam-ml
```

### 2. Create and activate a virtual environment

Using the Python launcher on Windows:

```powershell path=null start=null
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Check the version:

```powershell path=null start=null
python --version  # should be 3.11.x
```

### 3. Install dependencies

You can either use the Makefile (recommended) or pip directly.

**With `make`**:

```powershell path=null start=null
make setup   # creates editable install + syncs dependencies
```

**Or with plain pip**:

```powershell path=null start=null
python -m pip install -e .
```

---

## 🔐 Configuring your Steam Web API key

The Steam Web ingestor requires a **Steam Web API key**. The resolution order is:

1. Environment variable `STEAM_API_KEY`.
2. Local override file: `config/sources/steam_web_api.local.yaml`.
3. Repo config: `config/sources/steam_web_api.yaml` (placeholder only; no real keys in git).

### Option A: Environment variable (quick & safe)

```powershell path=null start=null
$env:STEAM_API_KEY = 'YOUR_STEAM_WEB_API_KEY_HERE'
```

This applies only to the current shell session.

### Option B: Local YAML file (persistent, git-ignored)

Create `config/sources/steam_web_api.local.yaml`:

```yaml path=null start=null
auth:
  api_key: "YOUR_STEAM_WEB_API_KEY_HERE"
```

This file is **git-ignored** and should contain your real key. The repo-level
`steam_web_api.yaml` can keep a placeholder key only.

---

## 📥 Ingestion workflows

### 1. Steam Web API: app list

The Steam Web ingestor fetches the global app list via the
`IStoreService/GetAppList/v1` endpoint and stores the result locally.

Run it via the CLI entrypoint (from the project root, venv active):

```powershell path=null start=null
python run_steam_web_ingest.py
```

You can tweak pagination and DLC handling:

```powershell path=null start=null
# Explicit identifier (currently only "app_list" is supported)
python run_steam_web_ingest.py app_list

# Smaller page size for quicker feedback
python run_steam_web_ingest.py app_list --page-size 10000

# Exclude DLCs from the app list
python run_steam_web_ingest.py app_list --no-dlc
```

Output artifacts:

- Raw JSON: `data/raw/steam_web/app_list.json`
- Parquet: `data/bronze/steam_web/app_list.parquet`

### 2. Steam Store API: app details (incremental)

The Steam Store ingestor enriches the app list with detailed store metadata
from `https://store.steampowered.com/api/appdetails`.

It is **incremental**:

- It reads `data/bronze/steam_web/app_list.parquet` to get the full list of app IDs.
- It reads `data/bronze/steam_store/app_details.parquet` (if present) to see which
  apps already have store details.
- Each run only fetches a **subset of the remaining app IDs**.
- New results are merged into `app_details.parquet` without duplicating app IDs.

Run it via the CLI entrypoint:

```powershell path=null start=null
python run_steam_store_ingest.py --limit 200 --request-delay 0.3
```

Flags:

- `--app-list-parquet PATH`
  - Path to the app list Parquet (defaults to `data/bronze/steam_web/app_list.parquet`).
- `--limit N`
  - Maximum number of **new** apps to fetch in this run (default: `200`).
- `--request-delay SECONDS`
  - Sleep time between requests (default: `0.3` seconds) to avoid HTTP 429
    "Too Many Requests" responses.
- `--cc` / `--language`
  - Country code and language for the store data (defaults: `us`, `english`).

Example: run this command regularly to gradually fetch all store details over time:

```powershell path=null start=null
python run_steam_store_ingest.py --limit 200 --request-delay 0.5
```

Output artifacts:

- Raw JSON (latest batch): `data/raw/steam_store/app_details.json`
- Parquet (cumulative, incremental): `data/bronze/steam_store/app_details.parquet`

You can inspect the resulting tables with pandas, for example:

```python path=null start=null
import pandas as pd

apps = pd.read_parquet("data/bronze/steam_web/app_list.parquet")
store = pd.read_parquet("data/bronze/steam_store/app_details.parquet")

print("Total apps in app list:", len(apps))
print("Apps with store details:", store["appid"].nunique())
print(store[["appid", "name"]].head())
```

---

## 🧪 Tests & quality tools

Run the full test suite:

```powershell path=null start=null
make test
# or
python -m pytest tests
```

Format code with Black:

```powershell path=null start=null
make format
```

Lint with Ruff:

```powershell path=null start=null
make lint
```

Run all pre-commit hooks on the entire codebase:

```powershell path=null start=null
make check
```

---

## 🗺️ Architecture overview

### Ingestion layer (`src/ingestion`)

- **`BaseIngestor` (`base.py`)**
  - Manages a shared `httpx.Client` with timeout and a custom `User-Agent`.
  - Wraps HTTP GET calls with retries and exponential backoff (`tenacity`).
  - Provides helpers to persist raw JSON and Parquet to the `data/` tree.
- **`SteamWebIngestor` (`steam_web.py`)**
  - Handles Steam Web API app list ingestion using a Steam Web API key.
  - Uses `_get_api_key()` to resolve the key from env or YAML configs.
- **`SteamStoreIngestor` (`steam_store.py`)**
  - Fetches store details via the (unofficial) `appdetails` endpoint.
  - Works incrementally based on what is already stored in `app_details.parquet`.
  - Applies light schema normalization (e.g., casting mixed-type columns to strings).

### Utilities (`src/utils`)

- **`config.py`** – YAML loader.
- **`io.py`** – JSON and Parquet write helpers (ensuring parent dirs exist).
- **`logging.py`** – Namespaced loggers with a consistent format.

---

## 🔮 Next steps / ML roadmap

This repo is intended to grow into a full **Steam ML project**, not just ingestion. Some concrete
next steps:

- 📊 **EDA notebooks**
  - Explore distributions (owners, price, tags, genres, review scores).
  - Correlate features (e.g. tags + price + discount history vs. review sentiment or popularity).
- 🧩 **Feature engineering layer**
  - Build curated feature tables ("silver" / "gold" data) that join Web, Store, and future sources
    like SteamSpy.
  - Encode text fields (tags, short descriptions) and possibly leverage image metadata in later
    experiments.
- 🤖 **ML models**
  - Supervised tasks: game success prediction, pricing tiers, review-score forecasting.
  - Recommendation-style tasks: "similar games" based on metadata and (later) player behavior.
- 🔌 **More data sources**
  - Add a `SteamSpy` ingestor (ownership & playtime estimates).
  - Optionally add review scraping / summary endpoints.
- 🧵 **Pipelines & scheduling**
  - Add a higher-level pipeline entrypoint (e.g. `src/pipelines/ingest_all.py`).
  - Optionally integrate with a scheduler (cron, Airflow, Prefect, etc.).

Pull requests and experiments are welcome – this repo is intentionally small and
hackable so you can iterate quickly. 🚀
