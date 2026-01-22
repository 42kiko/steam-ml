from pathlib import Path

from utils.io import read_parquet_merged

base_path = Path("data/bronze/steam_store/full_part/full.parquet")

df = read_parquet_merged(base_path)
print(df.head())
