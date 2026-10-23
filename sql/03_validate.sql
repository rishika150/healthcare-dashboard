-- 03_validate.sql
-- Each statement returns one row: check_name, severity, failed_rows, detail.
--   severity 'error' -> the pipeline stops if failed_rows > 0
--   severity 'info'  -> a data-quality fact that is reported, not enforced

SELECT 'Every raw encounter reaches the clean table' AS check_name, 'error' AS severity,
       (SELECT COUNT(DISTINCT encounter_id) FROM raw_encounters)
     - (SELECT COUNT(*) FROM fact_encounter) AS failed_rows,
       'distinct raw encounter_id minus clean rows' AS detail;

SELECT 'Encounter IDs are unique in the raw file', 'error',
       COUNT(*) - COUNT(DISTINCT encounter_id), 'duplicate encounter_id rows'
FROM raw_encounters;

SELECT 'Readmission label is one of NO, <30, >30', 'error',
       SUM(readmitted_raw NOT IN ('NO', '<30', '>30')), 'unexpected readmitted values'
FROM fact_encounter;

SELECT 'Readmission flags are mutually exclusive', 'error',
       SUM(readmit_lt30 + readmit_gt30 > 1 OR readmit_any <> readmit_lt30 + readmit_gt30), 'conflicting flags'
FROM fact_encounter;

SELECT 'Length of stay is between 1 and 14 days', 'error',
       SUM(los_days NOT BETWEEN 1 AND 14), 'out-of-range time_in_hospital'
FROM fact_encounter;

SELECT 'Age band is one of the ten published bands', 'error',
       SUM(age_order NOT BETWEEN 0 AND 9), 'unparseable age'
FROM fact_encounter;

SELECT 'Utilisation counts are non-negative', 'error',
       SUM(num_lab_procedures < 0 OR num_procedures < 0 OR num_medications < 0
           OR number_outpatient < 0 OR number_emergency < 0 OR number_inpatient < 0),
       'negative counts'
FROM fact_encounter;

SELECT 'Admission type IDs map to the lookup', 'error',
       SUM(admission_type IS NULL), 'admission_type_id missing from IDS_mapping'
FROM fact_encounter;

SELECT 'Discharge IDs map to the lookup', 'error',
       SUM(discharge_disposition IS NULL), 'discharge_disposition_id missing from IDS_mapping'
FROM fact_encounter;

SELECT 'Every medication row belongs to an encounter', 'error',
       COUNT(*), 'orphan fact_medication rows'
FROM fact_medication m LEFT JOIN fact_encounter e USING (encounter_id)
WHERE e.encounter_id IS NULL;

SELECT 'Weight is missing', 'info', SUM(r.weight = '?'), 'weight is dropped from analysis'
FROM raw_encounters r;

SELECT 'Payer code is missing', 'info', SUM(payer_code IS NULL), 'kept as NULL'
FROM fact_encounter;

SELECT 'Medical specialty is missing', 'info', SUM(medical_specialty IS NULL), 'kept as NULL'
FROM fact_encounter;

SELECT 'Race is missing', 'info', SUM(race IS NULL), 'kept as NULL'
FROM fact_encounter;

SELECT 'Gender is Unknown/Invalid', 'info', SUM(gender IS NULL), 'set to NULL'
FROM fact_encounter;

SELECT 'Primary diagnosis is missing', 'info', SUM(primary_diag_group = 'Missing'), 'grouped as Missing'
FROM fact_encounter;

SELECT 'Discharged to hospice or expired', 'info', SUM(is_eligible = 0),
       'excluded from readmission rates'
FROM fact_encounter;

SELECT 'Repeat encounters for the same patient', 'info', SUM(is_first_encounter = 0),
       'kept; flag is_first_encounter allows a one-row-per-patient view'
FROM fact_encounter;
