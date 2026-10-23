"""Step 2: create the database and land the raw CSVs, untouched, in staging tables.

Everything lands as text so that no value is silently coerced on the way in;
typing and cleaning happen in SQL (sql/02_clean.sql).
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from common import IDS_CSV, RAW_CSV, db_name, get_engine, run_sql_file


def parse_ids_mapping() -> dict[str, pd.DataFrame]:
    """IDS_mapping.csv holds three lookup tables stacked with blank-line separators."""
    tables: dict[str, list[tuple[str, str]]] = {}
    current = None
    for raw_line in IDS_CSV.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line == ",":
            current = None
            continue
        key, _, desc = line.partition(",")
        if current is None:
            current = key.strip()
            tables[current] = []
            continue
        tables[current].append((key.strip(), desc.strip().strip('"').strip()))
    return {
        name: pd.DataFrame(rows, columns=["id", "description"]).astype({"id": int})
        for name, rows in tables.items()
    }


def main() -> None:
    with get_engine(with_db=False).begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name()}` CHARACTER SET utf8mb4"))
    engine = get_engine()
    run_sql_file(engine, "01_schema.sql")

    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    raw.columns = [c.replace("-", "_") for c in raw.columns]
    raw.to_sql("raw_encounters", engine, if_exists="append", index=False,
               chunksize=5000, method="multi")
    print(f"  loaded raw_encounters: {len(raw):,} rows x {raw.shape[1]} columns")

    target = {
        "admission_type_id": "lkp_admission_type",
        "discharge_disposition_id": "lkp_discharge_disposition",
        "admission_source_id": "lkp_admission_source",
    }
    for section, frame in parse_ids_mapping().items():
        frame.to_sql(target[section], engine, if_exists="append", index=False)
        print(f"  loaded {target[section]}: {len(frame)} rows")


if __name__ == "__main__":
    main()
