"""Generate the Power BI Project (.pbip) for the readmission report.

    python powerbi/build_pbip.py [path\\to\\data\\processed] [--param-path PATH]

Writes powerbi/pbip/: a TMDL semantic model (tables, measures, relationship, a
DataFolder parameter pointing at the pipeline's CSVs) and a four-page report.
Open powerbi/pbip/DiabetesReadmission.pbip in Power BI Desktop and click Refresh.
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "pbip"
NAME = "DiabetesReadmission"
FACT = "fact_encounter"
MEDS = "fact_medication"

INK, INK2, PAPER, STAY, RETURN = "#142826", "#485C59", "#EEF1EF", "#00779E", "#C8304A"

# ---------------------------------------------------------------- semantic model

INT_COLS = {
    "encounter_id", "patient_nbr", "age_order", "admission_type_id", "discharge_disposition_id",
    "admission_source_id", "los_days", "num_lab_procedures", "num_procedures", "num_medications",
    "number_outpatient", "number_emergency", "number_inpatient", "number_diagnoses", "med_changed",
    "on_diabetes_med", "readmit_lt30", "readmit_gt30", "readmit_any", "is_eligible", "is_first_encounter",
}
HIDDEN = {"readmitted_raw", "diag_1", "diag_2", "diag_3", "admission_type_id",
          "discharge_disposition_id", "admission_source_id", "age_order"}

MEASURES = [
    ("Encounters", "COUNTROWS ( fact_encounter )", "#,0"),
    ("Patients", "DISTINCTCOUNT ( fact_encounter[patient_nbr] )", "#,0"),
    ("Eligible Encounters", "CALCULATE ( COUNTROWS ( fact_encounter ), fact_encounter[is_eligible] = 1 )", "#,0"),
    ("Readmitted <30", "CALCULATE ( SUM ( fact_encounter[readmit_lt30] ), fact_encounter[is_eligible] = 1 )", "#,0"),
    ("30-Day Readmission Rate", "DIVIDE ( [Readmitted <30], [Eligible Encounters] )", "0.0%"),
    ("Readmission Rate >30", "DIVIDE ( CALCULATE ( SUM ( fact_encounter[readmit_gt30] ), fact_encounter[is_eligible] = 1 ), [Eligible Encounters] )", "0.0%"),
    ("Any Readmission Rate", "DIVIDE ( CALCULATE ( SUM ( fact_encounter[readmit_any] ), fact_encounter[is_eligible] = 1 ), [Eligible Encounters] )", "0.0%"),
    ("Avg Length of Stay", "AVERAGE ( fact_encounter[los_days] )", "0.0"),
    ("Median Length of Stay", "MEDIAN ( fact_encounter[los_days] )", "0.0"),
    ("30-Day Rate (All Patients)", "CALCULATE ( [30-Day Readmission Rate], REMOVEFILTERS ( fact_encounter ) )", "0.0%"),
    ("30-Day Rate vs Average", "[30-Day Readmission Rate] - [30-Day Rate (All Patients)]", "+0.0%;-0.0%;0.0%"),
    ("30-Day Rate (n>=200)", "IF ( [Eligible Encounters] >= 200, [30-Day Readmission Rate] )", "0.0%"),
    ("Prescriptions", "COUNTROWS ( fact_medication )", "#,0"),
    ("HbA1c Tested Share", "DIVIDE ( CALCULATE ( [Encounters], fact_encounter[a1c_result] <> \"Not measured\" ), [Encounters] )", "0.0%"),
]


def q(name: str) -> str:
    """Quote a TMDL object name when it isn't a plain identifier."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def csv_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        return f.readline().strip().split(",")


def table_tmdl(table: str, columns: list[str], measures: list[tuple] = ()) -> str:
    lines = [f"table {table}", f"\tlineageTag: {uuid.uuid4()}", ""]
    for name, expr, fmt in measures:
        lines += [f"\tmeasure {q(name)} = {expr}", f"\t\tformatString: {fmt}",
                  f"\t\tlineageTag: {uuid.uuid4()}", ""]
    types = []
    for col in columns:
        is_int = col in INT_COLS
        types.append(f'{{"{col}", {"Int64.Type" if is_int else "type text"}}}')
        lines += [f"\tcolumn {col}", f"\t\tdataType: {'int64' if is_int else 'string'}"]
        if is_int:
            lines.append("\t\tformatString: 0")
        lines += [f"\t\tlineageTag: {uuid.uuid4()}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {col}"]
        if col == "age_band":
            lines.append("\t\tsortByColumn: age_order")
        if col in HIDDEN:
            lines.append("\t\tisHidden")
        lines.append("")
    m = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{table}.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f"    Typed = Table.TransformColumnTypes(Headers, {{{', '.join(types)}}})",
        "in",
        "    Typed",
    ]
    lines += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource ="]
    lines += [f"\t\t\t\t{l}" for l in m]
    lines.append("")
    return "\n".join(lines) + "\n"


def write_model(data_folder: Path, param_value: str) -> None:
    sm = OUT / f"{NAME}.SemanticModel"
    d = sm / "definition"
    (d / "tables").mkdir(parents=True)
    (sm / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2))
    (sm / ".platform").write_text(platform("SemanticModel"))
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n\n")
    (d / "model.tmdl").write_text(
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"ref table {FACT}\nref table {MEDS}\n")
    folder = param_value.rstrip("\\/") + "\\"
    (d / "expressions.tmdl").write_text(
        f'expression DataFolder = "{folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {uuid.uuid4()}\n\n\tannotation PBI_ResultType = Text\n")
    (d / "relationships.tmdl").write_text(
        f"relationship {uuid.uuid4()}\n\tfromColumn: {MEDS}.encounter_id\n\ttoColumn: {FACT}.encounter_id\n")
    (d / "tables" / f"{FACT}.tmdl").write_text(table_tmdl(FACT, csv_header(data_folder / f"{FACT}.csv"), MEASURES))
    (d / "tables" / f"{MEDS}.tmdl").write_text(table_tmdl(MEDS, csv_header(data_folder / f"{MEDS}.csv")))


def platform(kind: str) -> str:
    return json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": kind, "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    }, indent=2)


# ---------------------------------------------------------------- report

def lit(v) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def s(text: str) -> dict:
    return lit("'" + text.replace("'", "''") + "'")


def color(hexv: str) -> dict:
    return {"solid": {"color": s(hexv)}}


ALIAS = {FACT: "e", MEDS: "m"}  # query aliases must be unique per table


def field(kind: str, name: str, table: str = FACT) -> dict:
    src = {"Expression": {"SourceRef": {"Source": ALIAS[table]}}, "Property": name}
    return {kind: src, "Name": f"{table}.{name}"}


class Page:
    def __init__(self, name: str, display: str, title: str, subtitle: str):
        self.name, self.display, self.visuals = name, display, []
        self.text(title, subtitle, 32, 20, 900, 74)

    def add(self, x, y, w, h, single: dict) -> None:
        vid = uuid.uuid4().hex[:20]
        z = len(self.visuals) * 1000
        cfg = {"name": vid, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z, "width": w, "height": h}}],
               "singleVisual": single}
        self.visuals.append({"x": x, "y": y, "z": z, "width": w, "height": h,
                             "config": json.dumps(cfg), "filters": "[]"})

    def text(self, title: str, sub: str, x, y, w, h) -> None:
        paras = [{"textRuns": [{"value": title, "textStyle": {"fontFamily": "Segoe UI Semibold", "fontSize": "22pt", "color": INK}}]}]
        if sub:
            paras.append({"textRuns": [{"value": sub, "textStyle": {"fontFamily": "Segoe UI", "fontSize": "11pt", "color": INK2}}]})
        self.add(x, y, w, h, {"visualType": "textbox", "drillFilterOtherVisuals": True,
                              "objects": {"general": [{"properties": {"paragraphs": paras}}]}})

    def chart(self, vtype, x, y, w, h, title, roles: dict, sort=None, objects=None, top_n=None):
        """roles maps a visual role to a list of (kind, name, table) fields."""
        tables = {}
        select, projections = [], {}
        for role, fields in roles.items():
            projections[role] = []
            for kind, name, table in fields:
                tables[ALIAS[table]] = table
                f = field(kind, name, table)
                if f["Name"] not in [x["Name"] for x in select]:
                    select.append(f)
                projections[role].append({"queryRef": f["Name"]})
        query = {"Version": 2, "From": [{"Name": k, "Entity": v, "Type": 0} for k, v in tables.items()], "Select": select}
        if sort:
            kind, name, table, direction = sort
            query["OrderBy"] = [{"Direction": direction, "Expression": {kind: field(kind, name, table)[kind]}}]
        vc = {"title": [{"properties": {"show": lit("true"), "text": s(title), "fontColor": color(INK),
                                        "fontSize": lit("12D"), "fontFamily": s("Segoe UI Semibold")}}],
              "background": [{"properties": {"show": lit("true"), "color": color("#F7F9F8"), "transparency": lit("0D")}}],
              "border": [{"properties": {"show": lit("false")}}],
              "dropShadow": [{"properties": {"show": lit("false")}}]}
        single = {"visualType": vtype, "projections": projections, "prototypeQuery": query,
                  "drillFilterOtherVisuals": True, "hasDefaultSort": sort is None,
                  "objects": objects or {}, "vcObjects": vc}
        self.add(x, y, w, h, single)

    def section(self, ordinal: int) -> dict:
        return {"name": self.name, "displayName": self.display,
                "displayOption": 1, "width": 1280, "height": 720, "ordinal": ordinal,
                "config": json.dumps({"objects": {"background": [{"properties": {"color": color(PAPER), "transparency": lit("0D")}}],
                                                  "outspace": [{"properties": {"color": color(PAPER)}}]}}),
                "filters": "[]", "visualContainers": self.visuals}


M = lambda n, t=FACT: ("Measure", n, t)  # noqa: E731
C = lambda n, t=FACT: ("Column", n, t)  # noqa: E731


def bar_colors(fill: str = STAY, labels: bool = True) -> dict:
    return {"dataPoint": [{"properties": {"fill": color(fill)}}],
           "labels": [{"properties": {"show": lit("true" if labels else "false"), "color": color(INK2)}}],
           "valueAxis": [{"properties": {"gridlineColor": color("#CDD7D4")}}]}


def heat_objects(measure: str) -> dict:
    ref = f"{FACT}.{measure}"
    gradient = {"linearGradient2": {
        "min": {"color": {"Literal": {"Value": f"'{PAPER}'"}}},
        "max": {"color": {"Literal": {"Value": f"'{RETURN}'"}}},
        "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}}}}
    inp = {"Measure": {"Expression": {"SourceRef": {"Entity": FACT}}, "Property": measure}}
    return {"values": [{"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {"Input": inp, "FillRule": gradient}}}}}},
                        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": ref}}],
            "grid": [{"properties": {"gridHorizontal": lit("false"), "gridVertical": lit("false")}}]}


def build_pages() -> list[Page]:
    pages = []

    p = Page("ReportSection1", "Overview", "Who comes back within 30 days",
             "101,766 diabetic patient encounters, 130 US hospitals, 1999-2008. Rates exclude deaths and hospice discharges.")
    cards = [("Encounters", INK), ("Patients", INK), ("Avg Length of Stay", INK),
             ("30-Day Readmission Rate", RETURN), ("Any Readmission Rate", INK)]
    for i, (mname, col) in enumerate(cards):
        p.chart("card", 32 + i * 246, 108, 230, 110, mname, {"Values": [M(mname)]},
                objects={"labels": [{"properties": {"color": color(col), "fontSize": lit("28D")}}],
                         "categoryLabels": [{"properties": {"show": lit("false")}}]})
    for v in p.visuals[-5:]:  # exact counts on the cards, not 102K
        cfg = json.loads(v["config"])
        cfg["singleVisual"]["objects"]["labels"][0]["properties"]["labelDisplayUnits"] = lit("1D")
        v["config"] = json.dumps(cfg)
    p.chart("clusteredColumnChart", 32, 236, 600, 452, "Encounters by length of stay, days",
            {"Category": [C("los_days")], "Y": [M("Encounters")]}, sort=("Column", "los_days", FACT, 1),
            objects={**bar_colors(), "labels": [{"properties": {"show": lit("false")}}],
                     "categoryAxis": [{"properties": {"axisType": s("Categorical")}}]})
    p.chart("clusteredBarChart", 648, 236, 600, 452, "30-day readmission rate by discharge destination",
            {"Category": [C("discharge_group")], "Y": [M("30-Day Readmission Rate")]},
            sort=("Measure", "30-Day Readmission Rate", FACT, 2), objects=bar_colors(RETURN))
    pages.append(p)

    p = Page("ReportSection2", "Age", "Older patients stay longer and return slightly more often",
             "Length of stay rises steadily with age; the 30-day rate climbs from 9.8% at 50-60 to 12.6% at 80-90.")
    p.chart("clusteredColumnChart", 32, 108, 600, 290, "30-day readmission rate by age",
            {"Category": [C("age_band")], "Y": [M("30-Day Readmission Rate")]}, sort=("Column", "age_band", FACT, 1),
            objects=bar_colors(RETURN))
    p.chart("clusteredColumnChart", 648, 108, 600, 290, "Average length of stay by age, days",
            {"Category": [C("age_band")], "Y": [M("Avg Length of Stay")]}, sort=("Column", "age_band", FACT, 1),
            objects=bar_colors())
    p.chart("lineChart", 32, 414, 1216, 274, "Readmission within and after 30 days, by age",
            {"Category": [C("age_band")], "Y": [M("30-Day Readmission Rate"), M("Readmission Rate >30")]},
            sort=("Column", "age_band", FACT, 1),
            objects={"dataPoint": [{"properties": {"fill": color(RETURN)}, "selector": {"metadata": f"{FACT}.30-Day Readmission Rate"}},
                                   {"properties": {"fill": color(STAY)}, "selector": {"metadata": f"{FACT}.Readmission Rate >30"}}],
                     "legend": [{"properties": {"show": lit("true"), "position": s("Top")}}]})
    pages.append(p)

    p = Page("ReportSection3", "Diagnosis", "Diabetes as the primary diagnosis carries the highest risk",
             "Primary ICD-9 diagnosis grouped as in Strack et al. (2014). Groups and matrix cells under 200 eligible encounters are left out.")
    p.chart("clusteredBarChart", 32, 108, 470, 580, "30-day readmission rate by primary diagnosis",
            {"Category": [C("primary_diag_group")], "Y": [M("30-Day Rate (n>=200)")]},
            sort=("Measure", "30-Day Rate (n>=200)", FACT, 2), objects=bar_colors(RETURN))
    p.chart("pivotTable", 518, 108, 730, 340, "30-day readmission rate, diagnosis by age",
            {"Rows": [C("primary_diag_group")], "Columns": [C("age_band")], "Values": [M("30-Day Rate (n>=200)")]},
            objects=heat_objects("30-Day Rate (n>=200)"))
    p.chart("scatterChart", 518, 464, 730, 224, "Length of stay vs 30-day rate (bubble size = encounters)",
            {"Category": [C("primary_diag_group")], "X": [M("Avg Length of Stay")], "Y": [M("30-Day Rate (n>=200)")],
             "Size": [M("Encounters")]},
            objects={"dataPoint": [{"properties": {"fill": color(STAY)}}],
                     "categoryLabels": [{"properties": {"show": lit("true")}}]})
    pages.append(p)

    p = Page("ReportSection4", "Risk drivers", "A patient's history predicts a return better than anything else",
             "Five or more inpatient stays in the prior year: 37.1% back within 30 days, 4.3x the rate with none.")
    p.chart("clusteredColumnChart", 32, 108, 600, 290, "30-day rate by inpatient stays in the prior year",
            {"Category": [C("prior_inpatient_band")], "Y": [M("30-Day Readmission Rate")]},
            sort=("Column", "prior_inpatient_band", FACT, 1), objects=bar_colors(RETURN))
    p.chart("clusteredColumnChart", 648, 108, 600, 290, "30-day rate by length of stay, days",
            {"Category": [C("los_days")], "Y": [M("30-Day Readmission Rate")]}, sort=("Column", "los_days", FACT, 1),
            objects={**bar_colors(labels=False), "categoryAxis": [{"properties": {"axisType": s("Categorical")}}]})
    p.chart("clusteredBarChart", 32, 414, 600, 274, "30-day rate by HbA1c result",
            {"Category": [C("a1c_result")], "Y": [M("30-Day Readmission Rate")]},
            sort=("Measure", "30-Day Readmission Rate", FACT, 2), objects=bar_colors())
    p.chart("clusteredBarChart", 648, 414, 600, 274, "Most prescribed diabetes medications",
            {"Category": [C("medication", MEDS)], "Y": [M("Prescriptions")]},
            sort=("Measure", "Prescriptions", FACT, 2), objects=bar_colors())
    pages.append(p)
    return pages


def write_report() -> None:
    rp = OUT / f"{NAME}.Report"
    rp.mkdir(parents=True)
    (rp / ".platform").write_text(platform("Report"))
    (rp / "definition.pbir").write_text(json.dumps(
        {"version": "1.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2))
    pages = build_pages()
    report = {
        "config": json.dumps({"version": "5.59", "themeCollection": {}, "activeSectionIndex": 0,
                              "linguisticSchemaSyncVersion": 0, "objects": {}}),
        "layoutOptimization": 0,
        "resourcePackages": [],
        "sections": [pg.section(i) for i, pg in enumerate(pages)],
    }
    (rp / "report.json").write_text(json.dumps(report, indent=2))


def main() -> None:
    args = sys.argv[1:]
    # --param-path sets the DataFolder value stored in the model without changing where
    # the CSV headers are read from; the committed project uses a placeholder this way.
    param_path = None
    if "--param-path" in args:
        i = args.index("--param-path")
        param_path = args[i + 1]
        del args[i:i + 2]
    data_folder = Path(args[0]) if args else ROOT / "data" / "processed"
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / f"{NAME}.pbip").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True}}, indent=2))
    (OUT / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    write_model(data_folder.resolve(), param_path or str(data_folder.resolve()))
    write_report()
    print(f"  wrote {OUT / (NAME + '.pbip')}")


if __name__ == "__main__":
    main()
