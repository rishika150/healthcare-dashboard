-- 04_marts.sql
-- Reporting views. Readmission rates use eligible encounters only
-- (patients who died or went to hospice cannot be readmitted).

CREATE VIEW v_kpi_overall AS
SELECT COUNT(*)                                   AS encounters,
       COUNT(DISTINCT patient_nbr)                AS patients,
       SUM(is_eligible)                           AS eligible_encounters,
       ROUND(AVG(los_days), 2)                    AS avg_los_days,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate,
       ROUND(SUM(readmit_gt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_gt30_rate,
       ROUND(SUM(readmit_any  * is_eligible) / SUM(is_eligible), 4) AS readmit_any_rate
FROM fact_encounter;

CREATE VIEW v_readmit_by_age AS
SELECT age_band, age_order,
       COUNT(*)                                   AS encounters,
       ROUND(AVG(los_days), 2)                    AS avg_los_days,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate,
       ROUND(SUM(readmit_gt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_gt30_rate
FROM fact_encounter
GROUP BY age_band, age_order;

CREATE VIEW v_readmit_by_diag AS
SELECT primary_diag_group,
       COUNT(*)                                   AS encounters,
       ROUND(AVG(los_days), 2)                    AS avg_los_days,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate,
       ROUND(SUM(readmit_gt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_gt30_rate
FROM fact_encounter
GROUP BY primary_diag_group;

CREATE VIEW v_readmit_by_los AS
SELECT los_days,
       COUNT(*)                                   AS encounters,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate
FROM fact_encounter
GROUP BY los_days;

CREATE VIEW v_readmit_by_prior_inpatient AS
SELECT prior_inpatient_band,
       COUNT(*)                                   AS encounters,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate
FROM fact_encounter
GROUP BY prior_inpatient_band;

CREATE VIEW v_readmit_by_age_diag AS
SELECT age_band, age_order, primary_diag_group,
       SUM(is_eligible)                           AS eligible_encounters,
       ROUND(SUM(readmit_lt30 * is_eligible) / NULLIF(SUM(is_eligible), 0), 4) AS readmit_lt30_rate,
       ROUND(AVG(los_days), 2)                    AS avg_los_days
FROM fact_encounter
GROUP BY age_band, age_order, primary_diag_group;

CREATE VIEW v_readmit_by_admission_type AS
SELECT admission_type_group,
       COUNT(*)                                   AS encounters,
       ROUND(AVG(los_days), 2)                    AS avg_los_days,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate
FROM fact_encounter
GROUP BY admission_type_group;

CREATE VIEW v_readmit_by_a1c AS
SELECT a1c_result,
       COUNT(*)                                   AS encounters,
       ROUND(SUM(readmit_lt30 * is_eligible) / SUM(is_eligible), 4) AS readmit_lt30_rate
FROM fact_encounter
GROUP BY a1c_result;
