// Power Query (M) for the two model tables. In Power BI Desktop:
//   Home > Transform data > Manage Parameters > New: name it DataFolder (Text),
//   value = full path to this repo's data\processed folder, e.g. C:\code\diabetes-readmission-dashboard\data\processed\
//   Then Home > New Source > Blank Query > Advanced Editor, paste one query each.

// ---- Query: fact_encounter ----
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_encounter.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"encounter_id", Int64.Type}, {"patient_nbr", Int64.Type}, {"age_order", Int64.Type},
        {"los_days", Int64.Type}, {"num_lab_procedures", Int64.Type}, {"num_procedures", Int64.Type},
        {"num_medications", Int64.Type}, {"number_outpatient", Int64.Type}, {"number_emergency", Int64.Type},
        {"number_inpatient", Int64.Type}, {"number_diagnoses", Int64.Type},
        {"med_changed", Int64.Type}, {"on_diabetes_med", Int64.Type},
        {"readmit_lt30", Int64.Type}, {"readmit_gt30", Int64.Type}, {"readmit_any", Int64.Type},
        {"is_eligible", Int64.Type}, {"is_first_encounter", Int64.Type}
    })
in
    Typed

// ---- Query: fact_medication ----
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_medication.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {{"encounter_id", Int64.Type}})
in
    Typed
