-- 02_clean.sql
-- Typed, cleaned analytical layer built from raw_encounters.
--   * '?' / 'None' / 'Unknown/Invalid' become NULL or an explicit 'Not measured' label
--   * coded IDs are mapped to readable descriptions and grouped for reporting
--   * ICD-9 primary diagnoses are grouped as in Strack et al. (2014), the paper
--     that published this dataset
--   * encounters ending in death or hospice cannot be readmitted, so they are
--     flagged out of the readmission denominator (is_eligible = 0)

CREATE TABLE fact_encounter (
    encounter_id             BIGINT PRIMARY KEY,
    patient_nbr              BIGINT NOT NULL,
    race                     VARCHAR(40) NULL,
    gender                   VARCHAR(10) NULL,
    age_band                 VARCHAR(8)  NOT NULL,
    age_order                TINYINT     NOT NULL,
    admission_type_id        INT,
    admission_type           VARCHAR(120),
    admission_type_group     VARCHAR(20),
    discharge_disposition_id INT,
    discharge_disposition    VARCHAR(160),
    discharge_group          VARCHAR(30),
    admission_source_id      INT,
    admission_source         VARCHAR(120),
    admission_source_group   VARCHAR(20),
    los_days                 TINYINT NOT NULL,
    payer_code               VARCHAR(10) NULL,
    medical_specialty        VARCHAR(80) NULL,
    num_lab_procedures       SMALLINT,
    num_procedures           SMALLINT,
    num_medications          SMALLINT,
    number_outpatient        SMALLINT,
    number_emergency         SMALLINT,
    number_inpatient         SMALLINT,
    prior_inpatient_band     VARCHAR(4),
    diag_1                   VARCHAR(10) NULL,
    diag_2                   VARCHAR(10) NULL,
    diag_3                   VARCHAR(10) NULL,
    primary_diag_group       VARCHAR(20) NOT NULL,
    number_diagnoses         SMALLINT,
    max_glu_serum            VARCHAR(15),
    a1c_result               VARCHAR(15),
    insulin                  VARCHAR(10),
    med_changed              TINYINT,
    on_diabetes_med          TINYINT,
    readmitted_raw           VARCHAR(5) NOT NULL,
    readmit_lt30             TINYINT NOT NULL,
    readmit_gt30             TINYINT NOT NULL,
    readmit_any              TINYINT NOT NULL,
    is_eligible              TINYINT NOT NULL,
    is_first_encounter       TINYINT NOT NULL,
    INDEX ix_patient (patient_nbr),
    INDEX ix_age (age_band),
    INDEX ix_diag (primary_diag_group)
);

INSERT INTO fact_encounter
WITH dedup AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY r.encounter_id ORDER BY r.encounter_id) AS rn
    FROM raw_encounters r
),
base AS (
    SELECT d.*,
           NULLIF(TRIM(d.diag_1), '?')                    AS d1,
           REPLACE(REPLACE(d.age, '[', ''), ')', '')       AS age_clean,
           CAST(d.discharge_disposition_id AS UNSIGNED)   AS dispo,
           CAST(d.admission_source_id AS UNSIGNED)        AS src_id
    FROM dedup d
    WHERE d.rn = 1
)
SELECT
    CAST(b.encounter_id AS UNSIGNED),
    CAST(b.patient_nbr AS UNSIGNED),
    NULLIF(b.race, '?'),
    CASE WHEN b.gender IN ('Male', 'Female') THEN b.gender END,
    b.age_clean,
    CAST(SUBSTRING_INDEX(b.age_clean, '-', 1) AS UNSIGNED) DIV 10,
    CAST(b.admission_type_id AS UNSIGNED),
    at.description,
    CASE CAST(b.admission_type_id AS UNSIGNED)
        WHEN 1 THEN 'Emergency' WHEN 2 THEN 'Urgent' WHEN 3 THEN 'Elective'
        WHEN 7 THEN 'Trauma' ELSE 'Unknown' END,
    b.dispo,
    dd.description,
    CASE
        WHEN b.dispo = 1 THEN 'Home'
        WHEN b.dispo IN (6, 8) THEN 'Home with care'
        WHEN b.dispo IN (3, 4, 5, 15, 22, 23, 24) THEN 'Nursing or rehab'
        WHEN b.dispo IN (2, 9, 10, 16, 17, 27, 28, 29, 30) THEN 'Transferred'
        WHEN b.dispo IN (11, 19, 20, 21) THEN 'Expired'
        WHEN b.dispo IN (13, 14) THEN 'Hospice'
        WHEN b.dispo = 7 THEN 'Left against advice'
        ELSE 'Unknown' END,
    b.src_id,
    src.description,
    CASE
        WHEN b.src_id = 7 THEN 'Emergency room'
        WHEN b.src_id IN (1, 2, 3) THEN 'Referral'
        WHEN b.src_id IN (4, 5, 6, 10, 18, 22, 25, 26) THEN 'Transfer'
        ELSE 'Unknown' END,
    CAST(b.time_in_hospital AS UNSIGNED),
    NULLIF(b.payer_code, '?'),
    NULLIF(b.medical_specialty, '?'),
    CAST(b.num_lab_procedures AS UNSIGNED),
    CAST(b.num_procedures AS UNSIGNED),
    CAST(b.num_medications AS UNSIGNED),
    CAST(b.number_outpatient AS UNSIGNED),
    CAST(b.number_emergency AS UNSIGNED),
    CAST(b.number_inpatient AS UNSIGNED),
    CASE WHEN CAST(b.number_inpatient AS UNSIGNED) >= 5 THEN '5+'
         ELSE CAST(CAST(b.number_inpatient AS UNSIGNED) AS CHAR) END,
    b.d1,
    NULLIF(TRIM(b.diag_2), '?'),
    NULLIF(TRIM(b.diag_3), '?'),
    CASE
        WHEN b.d1 IS NULL THEN 'Missing'
        WHEN b.d1 LIKE 'V%' OR b.d1 LIKE 'E%' THEN 'Other'
        WHEN b.d1 LIKE '250%' THEN 'Diabetes'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 390 AND CAST(b.d1 AS DECIMAL(7,2)) < 460
          OR FLOOR(CAST(b.d1 AS DECIMAL(7,2))) = 785 THEN 'Circulatory'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 460 AND CAST(b.d1 AS DECIMAL(7,2)) < 520
          OR FLOOR(CAST(b.d1 AS DECIMAL(7,2))) = 786 THEN 'Respiratory'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 520 AND CAST(b.d1 AS DECIMAL(7,2)) < 580
          OR FLOOR(CAST(b.d1 AS DECIMAL(7,2))) = 787 THEN 'Digestive'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 800 AND CAST(b.d1 AS DECIMAL(7,2)) < 1000 THEN 'Injury'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 710 AND CAST(b.d1 AS DECIMAL(7,2)) < 740 THEN 'Musculoskeletal'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 580 AND CAST(b.d1 AS DECIMAL(7,2)) < 630
          OR FLOOR(CAST(b.d1 AS DECIMAL(7,2))) = 788 THEN 'Genitourinary'
        WHEN CAST(b.d1 AS DECIMAL(7,2)) >= 140 AND CAST(b.d1 AS DECIMAL(7,2)) < 240 THEN 'Neoplasms'
        ELSE 'Other' END,
    CAST(b.number_diagnoses AS UNSIGNED),
    CASE WHEN b.max_glu_serum IN ('None', '') THEN 'Not measured' ELSE b.max_glu_serum END,
    CASE WHEN b.A1Cresult IN ('None', '') THEN 'Not measured' ELSE b.A1Cresult END,
    b.insulin,
    CASE WHEN b.`change` = 'Ch' THEN 1 ELSE 0 END,
    CASE WHEN b.diabetesMed = 'Yes' THEN 1 ELSE 0 END,
    b.readmitted,
    CASE WHEN b.readmitted = '<30' THEN 1 ELSE 0 END,
    CASE WHEN b.readmitted = '>30' THEN 1 ELSE 0 END,
    CASE WHEN b.readmitted IN ('<30', '>30') THEN 1 ELSE 0 END,
    CASE WHEN b.dispo IN (11, 13, 14, 19, 20, 21) THEN 0 ELSE 1 END,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY b.patient_nbr
                                 ORDER BY CAST(b.encounter_id AS UNSIGNED)) = 1
         THEN 1 ELSE 0 END
FROM base b
LEFT JOIN lkp_admission_type at        ON at.id  = CAST(b.admission_type_id AS UNSIGNED)
LEFT JOIN lkp_discharge_disposition dd ON dd.id  = b.dispo
LEFT JOIN lkp_admission_source src     ON src.id = b.src_id;

-- Long-format medication table: one row per encounter per diabetes drug prescribed.
-- dosage_change is Up / Down / Steady.
CREATE TABLE fact_medication (
    encounter_id  BIGINT NOT NULL,
    medication    VARCHAR(40) NOT NULL,
    dosage_change VARCHAR(10) NOT NULL,
    PRIMARY KEY (encounter_id, medication)
);

INSERT INTO fact_medication
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'metformin', metformin FROM raw_encounters WHERE metformin <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'repaglinide', repaglinide FROM raw_encounters WHERE repaglinide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'nateglinide', nateglinide FROM raw_encounters WHERE nateglinide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'chlorpropamide', chlorpropamide FROM raw_encounters WHERE chlorpropamide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'glimepiride', glimepiride FROM raw_encounters WHERE glimepiride <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'acetohexamide', acetohexamide FROM raw_encounters WHERE acetohexamide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'glipizide', glipizide FROM raw_encounters WHERE glipizide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'glyburide', glyburide FROM raw_encounters WHERE glyburide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'tolbutamide', tolbutamide FROM raw_encounters WHERE tolbutamide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'pioglitazone', pioglitazone FROM raw_encounters WHERE pioglitazone <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'rosiglitazone', rosiglitazone FROM raw_encounters WHERE rosiglitazone <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'acarbose', acarbose FROM raw_encounters WHERE acarbose <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'miglitol', miglitol FROM raw_encounters WHERE miglitol <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'troglitazone', troglitazone FROM raw_encounters WHERE troglitazone <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'tolazamide', tolazamide FROM raw_encounters WHERE tolazamide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'examide', examide FROM raw_encounters WHERE examide <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'citoglipton', citoglipton FROM raw_encounters WHERE citoglipton <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'insulin', insulin FROM raw_encounters WHERE insulin <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'glyburide_metformin', glyburide_metformin FROM raw_encounters WHERE glyburide_metformin <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'glipizide_metformin', glipizide_metformin FROM raw_encounters WHERE glipizide_metformin <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'glimepiride_pioglitazone', glimepiride_pioglitazone FROM raw_encounters WHERE glimepiride_pioglitazone <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'metformin_rosiglitazone', metformin_rosiglitazone FROM raw_encounters WHERE metformin_rosiglitazone <> 'No'
UNION ALL
SELECT DISTINCT CAST(encounter_id AS UNSIGNED), 'metformin_pioglitazone', metformin_pioglitazone FROM raw_encounters WHERE metformin_pioglitazone <> 'No';
