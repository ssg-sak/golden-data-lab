-- CASE 02 SQL Extraction 검증
-- 원본 엑셀 값을 바꾸지 않은 tidy 적재가 PostgreSQL과 일치하는지 확인한다.
-- psql 또는 DBeaver에서 golden_data_lab 연결 후 실행한다.

\pset pager off
\timing on

SELECT '00_execution_identity' AS check_name,
       current_database() AS database_name,
       current_user AS database_user,
       version() AS postgres_version,
       statement_timestamp() AS validation_started_at;

SELECT '00_load_audit' AS check_name,
       load_id,
       source_file_name,
       source_sha256,
       source_size_bytes,
       table_row_counts,
       started_at,
       finished_at,
       database_user,
       loader_version,
       status
FROM migration.load_audit
ORDER BY load_id DESC
LIMIT 1;

-- 1. 2025 총이동자 수 대사
SELECT '01_national_2025_movers' AS check_name,
       movers_total AS actual_value,
       6117784::bigint AS expected_value,
       movers_total = 6117784 AS passed
FROM migration.national_movers_yearly
WHERE year = 2025;

-- 2. tidy 테이블 행 수 대사
SELECT '02_table_row_counts' AS check_name,
       table_name,
       actual_rows,
       expected_rows,
       actual_rows = expected_rows AS passed
FROM (
    SELECT 'national_movers_yearly' AS table_name, count(*) AS actual_rows, 56::bigint AS expected_rows
    FROM migration.national_movers_yearly
    UNION ALL
    SELECT 'age_movers_yearly', count(*), 1134 FROM migration.age_movers_yearly
    UNION ALL
    SELECT 'sido_flow_yearly', count(*), 1134 FROM migration.sido_flow_yearly
    UNION ALL
    SELECT 'sido_gender_2025', count(*), 54 FROM migration.sido_gender_2025
    UNION ALL
    SELECT 'sido_age_net_2025', count(*), 918 FROM migration.sido_age_net_2025
    UNION ALL
    SELECT 'od_movers_2025', count(*), 972 FROM migration.od_movers_2025
    UNION ALL
    SELECT 'od_net_2025', count(*), 972 FROM migration.od_net_2025
    UNION ALL
    SELECT 'capital_yearly', count(*), 37 FROM migration.capital_yearly
    UNION ALL
    SELECT 'monthly_movers', count(*), 39 FROM migration.monthly_movers
    UNION ALL
    SELECT 'reason_2025', count(*), 720 FROM migration.reason_2025
) AS counts
ORDER BY table_name;

-- 3. 연도 범위
SELECT '03_year_range_national' AS check_name,
       min(year) AS min_year,
       max(year) AS max_year,
       min(year) = 1970 AND max(year) = 2025 AS passed
FROM migration.national_movers_yearly;

-- 4. 결측 프로파일 (핵심 값)
SELECT '04_null_profile' AS check_name,
       'national_movers_total' AS column_name,
       count(*) FILTER (WHERE movers_total IS NULL) AS null_rows,
       count(*) FILTER (WHERE movers_total IS NULL) = 0 AS passed
FROM migration.national_movers_yearly
UNION ALL
SELECT '04_null_profile', 'sido_age_net',
       count(*) FILTER (WHERE net IS NULL),
       count(*) FILTER (WHERE net IS NULL) = 0
FROM migration.sido_age_net_2025
UNION ALL
SELECT '04_null_profile', 'od_movers',
       count(*) FILTER (WHERE movers IS NULL),
       count(*) FILTER (WHERE movers IS NULL) = 0
FROM migration.od_movers_2025;

-- 5. 전국 순이동 0
SELECT '05_national_net_zero' AS check_name,
       value AS actual_net,
       0::bigint AS expected_net,
       value = 0 AS passed
FROM migration.sido_flow_yearly
WHERE year = 2025 AND measure = 'net' AND sido = '전국';

-- 6. 청년 이동자 수 2025
SELECT '06_youth_movers_2025' AS check_name,
       sum(movers) AS actual_value,
       2761243::bigint AS expected_value,
       sum(movers) = 2761243 AS passed
FROM migration.age_movers_yearly
WHERE year = 2025
  AND gender = 'all'
  AND age_group IN ('20-24', '25-29', '30-34', '35-39');

-- 7. 서울 20-24 / 30-34 순이동
SELECT '07_seoul_age_net' AS check_name,
       age_group,
       net AS actual_net,
       CASE age_group WHEN '20-24' THEN 25664 WHEN '30-34' THEN -10861 END AS expected_net,
       net = CASE age_group WHEN '20-24' THEN 25664 WHEN '30-34' THEN -10861 END AS passed
FROM migration.sido_age_net_2025
WHERE year = 2025 AND gender = 'all' AND sido = '서울'
  AND age_group IN ('20-24', '30-34')
ORDER BY age_group;

-- 8. OD 행=전입지 대사
SELECT '08_od_row_is_destination' AS check_name,
       dest.movers - intra.movers AS implied_inter_sido_in,
       gender.inter_sido_in AS sheet4_inter_sido_in,
       dest.movers - intra.movers = gender.inter_sido_in AS passed
FROM migration.od_movers_2025 AS dest
JOIN migration.od_movers_2025 AS intra
  ON intra.gender = dest.gender
 AND intra.destination = dest.destination
 AND intra.origin = dest.destination
JOIN migration.sido_gender_2025 AS gender
  ON gender.gender = dest.gender
 AND gender.sido = dest.destination
WHERE dest.gender = 'all'
  AND dest.destination = '서울'
  AND dest.origin = '전국';

-- 9. 수도권 순이동 2025
SELECT '09_capital_net_2025' AS check_name,
       net AS actual_net,
       in_from_noncapital - out_to_noncapital AS implied_net,
       net = 38465 AND net = in_from_noncapital - out_to_noncapital AS passed
FROM migration.capital_yearly
WHERE year = 2025;

-- 10. 시도별 청년 순이동 (분석 핸드오프)
SELECT '10_youth_net_by_sido' AS check_name,
       sido,
       is_capital,
       net_20s,
       net_30s,
       net_youth_20_39,
       net_total
FROM migration.v_youth_net_2025
ORDER BY net_youth_20_39 DESC;

-- 11. 시도 간 상위 경로 (전 연령)
SELECT '11_top_inter_sido_od' AS check_name,
       origin,
       destination,
       movers,
       origin_capital,
       destination_capital
FROM migration.v_inter_sido_od_2025
ORDER BY movers DESC
LIMIT 10;

-- 완료 게이트: 불일치 시 예외
DO $validation$
DECLARE
    national_2025 bigint;
    youth_2025 bigint;
    seoul_20_24 bigint;
    seoul_30_34 bigint;
    capital_net bigint;
    latest_audit record;
    table_mismatch int;
BEGIN
    SELECT movers_total INTO national_2025
    FROM migration.national_movers_yearly
    WHERE year = 2025;

    SELECT sum(movers) INTO youth_2025
    FROM migration.age_movers_yearly
    WHERE year = 2025
      AND gender = 'all'
      AND age_group IN ('20-24', '25-29', '30-34', '35-39');

    SELECT net INTO seoul_20_24
    FROM migration.sido_age_net_2025
    WHERE gender = 'all' AND sido = '서울' AND age_group = '20-24';

    SELECT net INTO seoul_30_34
    FROM migration.sido_age_net_2025
    WHERE gender = 'all' AND sido = '서울' AND age_group = '30-34';

    SELECT net INTO capital_net
    FROM migration.capital_yearly
    WHERE year = 2025;

    SELECT * INTO latest_audit
    FROM migration.load_audit
    ORDER BY load_id DESC
    LIMIT 1;

    SELECT count(*) INTO table_mismatch
    FROM (
        SELECT count(*) AS actual_rows, 56::bigint AS expected_rows FROM migration.national_movers_yearly
        UNION ALL SELECT count(*), 1134 FROM migration.age_movers_yearly
        UNION ALL SELECT count(*), 1134 FROM migration.sido_flow_yearly
        UNION ALL SELECT count(*), 54 FROM migration.sido_gender_2025
        UNION ALL SELECT count(*), 918 FROM migration.sido_age_net_2025
        UNION ALL SELECT count(*), 972 FROM migration.od_movers_2025
        UNION ALL SELECT count(*), 972 FROM migration.od_net_2025
        UNION ALL SELECT count(*), 37 FROM migration.capital_yearly
        UNION ALL SELECT count(*), 39 FROM migration.monthly_movers
        UNION ALL SELECT count(*), 720 FROM migration.reason_2025
    ) AS counts
    WHERE actual_rows <> expected_rows;

    IF national_2025 <> 6117784
       OR youth_2025 <> 2761243
       OR seoul_20_24 <> 25664
       OR seoul_30_34 <> -10861
       OR capital_net <> 38465
       OR table_mismatch <> 0 THEN
        RAISE EXCEPTION
            'Row reconciliation failed: movers %, youth %, seoul 20-24 %, seoul 30-34 %, capital %, table mismatches %',
            national_2025, youth_2025, seoul_20_24, seoul_30_34, capital_net, table_mismatch;
    END IF;

    IF latest_audit IS NULL
       OR latest_audit.status <> 'success'
       OR latest_audit.source_sha256 <> 'FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D' THEN
        RAISE EXCEPTION 'Load audit reconciliation failed';
    END IF;

    RAISE NOTICE 'PASS: source, audit, and PostgreSQL migration tables reconcile (2025 movers %)', national_2025;
END
$validation$;
