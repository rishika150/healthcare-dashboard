-- 01_schema.sql
-- Staging layer: raw CSV columns land as text, exactly as published.
-- Re-running the pipeline drops and rebuilds everything.

DROP VIEW IF EXISTS v_kpi_overall;
DROP VIEW IF EXISTS v_readmit_by_age;
DROP VIEW IF EXISTS v_readmit_by_diag;
DROP VIEW IF EXISTS v_readmit_by_los;
DROP VIEW IF EXISTS v_readmit_by_prior_inpatient;
DROP VIEW IF EXISTS v_readmit_by_age_diag;
DROP VIEW IF EXISTS v_readmit_by_admission_type;
DROP VIEW IF EXISTS v_readmit_by_a1c;
DROP TABLE IF EXISTS fact_medication;
DROP TABLE IF EXISTS fact_encounter;
DROP TABLE IF EXISTS raw_encounters;
DROP TABLE IF EXISTS lkp_admission_type;
DROP TABLE IF EXISTS lkp_discharge_disposition;
DROP TABLE IF EXISTS lkp_admission_source;

CREATE TABLE raw_encounters (
    encounter_id VARCHAR(20), patient_nbr VARCHAR(20), race VARCHAR(40), gender VARCHAR(40),
    age VARCHAR(20), weight VARCHAR(20), admission_type_id VARCHAR(10),
    discharge_disposition_id VARCHAR(10), admission_source_id VARCHAR(10),
    time_in_hospital VARCHAR(10), payer_code VARCHAR(10), medical_specialty VARCHAR(80),
    num_lab_procedures VARCHAR(10), num_procedures VARCHAR(10), num_medications VARCHAR(10),
    number_outpatient VARCHAR(10), number_emergency VARCHAR(10), number_inpatient VARCHAR(10),
    diag_1 VARCHAR(10), diag_2 VARCHAR(10), diag_3 VARCHAR(10), number_diagnoses VARCHAR(10),
    max_glu_serum VARCHAR(10), A1Cresult VARCHAR(10),
    metformin VARCHAR(10), repaglinide VARCHAR(10), nateglinide VARCHAR(10),
    chlorpropamide VARCHAR(10), glimepiride VARCHAR(10), acetohexamide VARCHAR(10),
    glipizide VARCHAR(10), glyburide VARCHAR(10), tolbutamide VARCHAR(10),
    pioglitazone VARCHAR(10), rosiglitazone VARCHAR(10), acarbose VARCHAR(10),
    miglitol VARCHAR(10), troglitazone VARCHAR(10), tolazamide VARCHAR(10),
    examide VARCHAR(10), citoglipton VARCHAR(10), insulin VARCHAR(10),
    glyburide_metformin VARCHAR(10), glipizide_metformin VARCHAR(10),
    glimepiride_pioglitazone VARCHAR(10), metformin_rosiglitazone VARCHAR(10),
    metformin_pioglitazone VARCHAR(10), `change` VARCHAR(10), diabetesMed VARCHAR(10),
    readmitted VARCHAR(10)
);

CREATE TABLE lkp_admission_type (id INT PRIMARY KEY, description VARCHAR(120));
CREATE TABLE lkp_discharge_disposition (id INT PRIMARY KEY, description VARCHAR(160));
CREATE TABLE lkp_admission_source (id INT PRIMARY KEY, description VARCHAR(120));
