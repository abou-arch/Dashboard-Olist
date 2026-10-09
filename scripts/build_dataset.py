"""Construit les tables Parquet du dashboard à partir des CSV de data/raw/.

Usage : python scripts/build_dataset.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from olist_dashboard.config import PROCESSED_DIR  # noqa: E402
from olist_dashboard.data import build_tables, load_raw, write_processed  # noqa: E402


def main() -> None:
    tables = build_tables(load_raw())
    write_processed(tables)
    for name, df in tables.items():
        print(f"{name:>7} : {len(df):>7,} lignes -> {PROCESSED_DIR / (name + '.parquet')}")


if __name__ == "__main__":
    main()
