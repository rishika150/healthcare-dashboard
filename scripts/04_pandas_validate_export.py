"""Step 4: validate the SQL output with pandas, then export for Power BI and the web dashboard.

Validation is done two ways:
  1. schema/range checks on the clean table pulled from MySQL
  2. an independent re-computation of the headline numbers straight from the raw
     CSV in pandas, reconciled against the SQL views. If SQL and pandas disagree,
     one of them has a bug, and the pipeline stops.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from common import DOCS_DATA_DIR, PROCESSED_DIR, RAW_CSV, get_engine

INELIGIBLE_DISPOSITIONS = {11, 13, 14, 19, 20, 21}
TOLERANCE = 1e-4


def icd9_group(code: str | float) -> str:
    """Python twin of the CASE expression in sql/02_clean.sql."""
    if not isinstance(code, str) or code == "?":
        return "Missing"
    if code[0] in "VE":
        return "Other"
    if code.startswith("250"):
        return "Diabetes"
    v = float(code)
    whole = int(np.floor(v))
    if 390 <= v < 460 or whole == 785:
        return "Circulatory"
    if 460 <= v < 520 or whole == 786:
        return "Respiratory"
    if 520 <= v < 580 or whole == 787:
        return "Digestive"
    if 800 <= v < 1000:
        return "Injury"
    if 710 <= v < 740:
        return "Musculoskeletal"
    if 580 <= v < 630 or whole == 788:
        return "Genitourinary"
    if 140 <= v < 240:
        return "Neoplasms"
    return "Other"


def check(results: list, name: str, ok: bool, detail: str) -> None:
    results.append({"check": name, "severity": "error", "passed": bool(ok), "detail": detail})
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}: {detail}")


def lt30_rate(frame: pd.DataFrame) -> float:
    eligible = frame[frame["eligible"]]
    return float((eligible["readmitted"] == "<30").mean())


def main() -> None:
    engine = get_engine()
    fact = pd.read_sql("SELECT * FROM fact_encounter", engine)
    meds = pd.read_sql("SELECT * FROM fact_medication", engine)
    views = {name: pd.read_sql(f"SELECT * FROM {name}", engine) for name in (
        "v_kpi_overall", "v_readmit_by_age", "v_readmit_by_diag", "v_readmit_by_los",
        "v_readmit_by_prior_inpatient", "v_readmit_by_age_diag",
        "v_readmit_by_admission_type", "v_readmit_by_a1c")}
    raw = pd.read_csv(RAW_CSV, na_values=[], keep_default_na=False)

    results: list[dict] = []
    print("  schema and range checks on fact_encounter")
    check(results, "encounter_id is a unique key", fact["encounter_id"].is_unique,
          f"{fact['encounter_id'].nunique():,} unique of {len(fact):,}")
    required = ["encounter_id", "patient_nbr", "age_band", "los_days", "readmitted_raw",
                "primary_diag_group", "is_eligible"]
    nulls = int(fact[required].isna().sum().sum())
    check(results, "Required columns have no nulls", nulls == 0, f"{nulls} nulls in {len(required)} columns")
    check(results, "Rates are probabilities", fact[["readmit_lt30", "readmit_gt30"]].isin([0, 1]).all().all(),
          "flags are 0/1")
    check(results, "One first encounter per patient",
          int(fact["is_first_encounter"].sum()) == fact["patient_nbr"].nunique(),
          f"{int(fact['is_first_encounter'].sum()):,} first encounters, "
          f"{fact['patient_nbr'].nunique():,} patients")

    print("  reconciling SQL views against an independent pandas computation from the raw CSV")
    raw["eligible"] = ~raw["discharge_disposition_id"].isin(INELIGIBLE_DISPOSITIONS)
    raw["age_band"] = raw["age"].str.strip("[)")
    raw["diag_group"] = raw["diag_1"].map(icd9_group)

    kpi = views["v_kpi_overall"].iloc[0]
    check(results, "Row count matches raw CSV", int(kpi["encounters"]) == len(raw),
          f"SQL {int(kpi['encounters']):,} vs pandas {len(raw):,}")
    check(results, "30-day readmission rate matches",
          abs(float(kpi["readmit_lt30_rate"]) - lt30_rate(raw)) < TOLERANCE,
          f"SQL {float(kpi['readmit_lt30_rate']):.4f} vs pandas {lt30_rate(raw):.4f}")
    check(results, "Average length of stay matches",
          abs(float(kpi["avg_los_days"]) - raw["time_in_hospital"].mean()) < 0.01,
          f"SQL {float(kpi['avg_los_days']):.2f} vs pandas {raw['time_in_hospital'].mean():.2f}")

    by_age_pd = raw.groupby("age_band").apply(lt30_rate, include_groups=False)
    by_age_sql = views["v_readmit_by_age"].set_index("age_band")["readmit_lt30_rate"].astype(float)
    worst = float((by_age_sql - by_age_pd.reindex(by_age_sql.index)).abs().max())
    check(results, "Readmission by age matches", worst < TOLERANCE, f"max difference {worst:.6f}")

    by_diag_pd = raw.groupby("diag_group").size()
    by_diag_sql = views["v_readmit_by_diag"].set_index("primary_diag_group")["encounters"]
    same = by_diag_sql.sort_index().astype(int).equals(by_diag_pd.reindex(by_diag_sql.index).sort_index().astype(int))
    check(results, "ICD-9 grouping matches", same, f"{len(by_diag_sql)} groups compared")

    sql_checks = pd.read_csv(PROCESSED_DIR / "validation_sql.csv")
    if not all(r["passed"] for r in results):
        raise SystemExit("pandas validation failed")

    # Power BI model: one fact table, one medication bridge, plus small marts.
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fact.to_csv(PROCESSED_DIR / "fact_encounter.csv", index=False)
    meds.to_csv(PROCESSED_DIR / "fact_medication.csv", index=False)
    for name, frame in views.items():
        frame.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    pd.DataFrame(results).to_csv(PROCESSED_DIR / "validation_pandas.csv", index=False)
    print(f"  wrote Power BI tables to {PROCESSED_DIR}")

    eligible = fact[fact["is_eligible"] == 1]

    def rate_table(col: str) -> list[dict]:
        g = fact.groupby(col).agg(encounters=("encounter_id", "size"), avg_los=("los_days", "mean"))
        e = eligible.groupby(col).agg(eligible=("encounter_id", "size"),
                                      lt30=("readmit_lt30", "mean"), gt30=("readmit_gt30", "mean"))
        out = g.join(e).reset_index().rename(columns={col: "key"})
        return json.loads(out.round(4).to_json(orient="records"))

    discharge = rate_table("discharge_group")
    los_dist = rate_table("los_days")
    payload = {
        "meta": {
            "source": "UCI Machine Learning Repository: Diabetes 130-US Hospitals for Years 1999-2008",
            "source_url": "https://archive.ics.uci.edu/dataset/296",
            "hospitals": 130, "years": "1999-2008", "generated": date.today().isoformat(),
        },
        "kpi": {
            "encounters": int(kpi["encounters"]), "patients": int(kpi["patients"]),
            "eligible": int(kpi["eligible_encounters"]), "avg_los": float(kpi["avg_los_days"]),
            "median_los": float(fact["los_days"].median()),
            "lt30": float(kpi["readmit_lt30_rate"]), "gt30": float(kpi["readmit_gt30_rate"]),
            "any": float(kpi["readmit_any_rate"]),
        },
        "los": los_dist,
        "age": rate_table("age_band"),
        "diag": rate_table("primary_diag_group"),
        "prior": rate_table("prior_inpatient_band"),
        "admission": rate_table("admission_type_group"),
        "discharge": discharge,
        "a1c": rate_table("a1c_result"),
        "heat": json.loads(views["v_readmit_by_age_diag"].round(4).to_json(orient="records")),
        "validation": {
            "sql": json.loads(sql_checks.to_json(orient="records")),
            "pandas": results,
        },
    }
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA_DIR / "dashboard.json").write_text(json.dumps(payload, indent=1))
    print(f"  wrote {DOCS_DATA_DIR / 'dashboard.json'}")


if __name__ == "__main__":
    main()
