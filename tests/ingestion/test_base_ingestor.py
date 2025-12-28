from pathlib import Path

import pandas as pd

from src.ingestion.base import BaseIngestor


class DummyIngestor(BaseIngestor):
    def ingest(self, identifier: str) -> None:
        payload = {"id": identifier}
        df = pd.DataFrame([payload])

        self.save_raw(identifier, payload)
        self.save_parquet(identifier, df)


def test_base_ingestor_saves_files(tmp_path: Path) -> None:
    ingestor = DummyIngestor(
        source_name="dummy",
        base_url="https://example.com",
        raw_root=tmp_path / "raw",
    )

    ingestor.ingest("test")

    raw_file = tmp_path / "raw" / "dummy" / "test.json"
    parquet_file = Path("data/bronze/dummy/test.parquet")

    assert raw_file.exists()
    assert parquet_file.exists()
