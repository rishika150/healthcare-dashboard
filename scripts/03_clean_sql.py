"""Step 3: build the clean tables in SQL, run the SQL validation suite, create report views."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from common import PROCESSED_DIR, SQL_DIR, get_engine, run_sql_file, split_sql


def run_validation(engine) -> pd.DataFrame:
    rows = []
    with engine.connect() as conn:
        for stmt in split_sql((SQL_DIR / "03_validate.sql").read_text(encoding="utf-8")):
            name, severity, failed, detail = conn.execute(text(stmt)).one()
            rows.append({"check": name, "severity": severity,
                         "rows": int(failed or 0), "detail": detail})
    return pd.DataFrame(rows)


def main() -> None:
    engine = get_engine()
    run_sql_file(engine, "02_clean.sql")

    results = run_validation(engine)
    results["passed"] = (results["severity"] == "info") | (results["rows"] == 0)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(PROCESSED_DIR / "validation_sql.csv", index=False)
    for r in results.itertuples():
        mark = "ok  " if r.passed else "FAIL"
        print(f"  [{mark}] {r.check}: {r.rows:,} ({r.detail})")
    failed = results[~results["passed"]]
    if not failed.empty:
        raise SystemExit(f"{len(failed)} SQL validation check(s) failed")

    run_sql_file(engine, "04_marts.sql")


if __name__ == "__main__":
    main()
