from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.io import write_json
from src.utils.logging import get_logger


class BaseIngestor(ABC):
    """
    Base class for all data ingestors.

    Responsibilities:
    - HTTP client handling
    - retries & backoff
    - config loading
    - raw data persistence
    """

    def __init__(
        self,
        source_name: str,
        base_url: str,
        raw_root: Path = Path("data/raw"),
        timeout: float = 20.0,
    ) -> None:
        self.source_name = source_name
        self.base_url = base_url
        self.raw_root = raw_root / source_name
        self.timeout = timeout

        self.logger = get_logger(f"ingestor.{source_name}")
        self.client = httpx.Client(timeout=self.timeout)

        self.logger.info("Initialized ingestor")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        self.logger.info(f"GET {url}")

        response = self.client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def save_raw(self, identifier: str, payload: dict[str, Any]) -> None:
        path = self.raw_root / f"{identifier}.json"
        write_json(path, payload)
        self.logger.info(f"Saved raw data → {path}")

    def save_parquet(self, identifier: str, df: pd.DataFrame) -> None:
        path = Path("data/bronze") / self.source_name / f"{identifier}.parquet"
        from src.utils.io import write_parquet

        write_parquet(path, df)
        self.logger.info(f"Saved parquet → {path}")

    @abstractmethod
    def ingest(self, identifier: str) -> None:
        """
        Fetch data for a single entity and persist raw output.
        Must be implemented by concrete ingestors.
        """
        raise NotImplementedError
