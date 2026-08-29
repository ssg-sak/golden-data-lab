-- CASE 01 raw load validation
-- Read-only checks. Run after loading all 1,067,371 source rows.

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
       expected_row_count,
       loaded_row_count,
       sheet_row_counts,
       started_at,
       finished_at,
       database_user,
       loader_version,
       status
FROM retail.load_audit
ORDER BY load_id DESC
LIMIT 1;

-- 1. 시트별·전체 행 수 대사
SELECT '01_row_count_by_sheet' AS check_name,
       source_sheet,
       count(*) AS actual_rows,
       CASE source_sheet
           WHEN 'Year 2009-2010' THEN 525461
           WHEN 'Year 2010-2011' THEN 541910
       END AS expected_rows,
       count(*) = CASE source_sheet
           WHEN 'Year 2009-2010' THEN 525461
           WHEN 'Year 2010-2011' THEN 541910
       END AS passed
FROM retail.online_retail_raw
GROUP BY source_sheet
ORDER BY source_sheet;

SELECT '01_total_row_count' AS check_name,
       count(*) AS actual_rows,
       1067371::bigint AS expected_rows,
       count(*) = 1067371 AS passed
FROM retail.online_retail_raw;

-- 2. 컬럼별 결측 건수와 비율
WITH null_counts AS (
    SELECT count(*) AS total_rows,
           count(*) FILTER (WHERE invoice IS NULL) AS invoice,
           count(*) FILTER (WHERE stock_code IS NULL) AS stock_code,
           count(*) FILTER (WHERE description IS NULL) AS description,
           count(*) FILTER (WHERE quantity IS NULL) AS quantity,
           count(*) FILTER (WHERE invoice_date IS NULL) AS invoice_date,
           count(*) FILTER (WHERE price IS NULL) AS price,
           count(*) FILTER (WHERE customer_id IS NULL) AS customer_id,
           count(*) FILTER (WHERE country IS NULL) AS country
    FROM retail.online_retail_raw
)
SELECT '02_null_profile' AS check_name,
       metric.column_name,
       metric.null_rows,
       round(100.0 * metric.null_rows / null_counts.total_rows, 4) AS null_pct
FROM null_counts
CROSS JOIN LATERAL (VALUES
    ('invoice', invoice),
    ('stock_code', stock_code),
    ('description', description),
    ('quantity', quantity),
    ('invoice_date', invoice_date),
    ('price', price),
    ('customer_id', customer_id),
    ('country', country)
) AS metric(column_name, null_rows)
ORDER BY metric.column_name;

-- 3. 거래 일시 범위와 월별 행 수
SELECT '03_invoice_date_range' AS check_name,
       min(invoice_date) AS min_invoice_date,
       max(invoice_date) AS max_invoice_date
FROM retail.online_retail_raw;

SELECT '03_monthly_row_count' AS check_name,
       date_trunc('month', invoice_date)::date AS invoice_month,
       count(*) AS row_count
FROM retail.online_retail_raw
GROUP BY 2
ORDER BY 2;

-- 4. Customer ID 보유·결측 거래 수
SELECT '04_customer_id_presence' AS check_name,
       CASE WHEN customer_id IS NULL THEN 'missing' ELSE 'present' END AS status,
       count(*) AS row_count,
       round(100.0 * count(*) / sum(count(*)) OVER (), 4) AS row_pct
FROM retail.online_retail_raw
GROUP BY 2
ORDER BY 2;

-- 5. Quantity 음수·0·양수 분포
SELECT '05_quantity_sign' AS check_name,
       CASE
           WHEN quantity < 0 THEN 'negative'
           WHEN quantity = 0 THEN 'zero'
           WHEN quantity > 0 THEN 'positive'
           ELSE 'null'
       END AS sign,
       count(*) AS row_count,
       round(100.0 * count(*) / sum(count(*)) OVER (), 4) AS row_pct
FROM retail.online_retail_raw
GROUP BY 2
ORDER BY 2;

-- 6. Price 음수·0·양수 분포
SELECT '06_price_sign' AS check_name,
       CASE
           WHEN price < 0 THEN 'negative'
           WHEN price = 0 THEN 'zero'
           WHEN price > 0 THEN 'positive'
           ELSE 'null'
       END AS sign,
       count(*) AS row_count,
       round(100.0 * count(*) / sum(count(*)) OVER (), 4) AS row_pct
FROM retail.online_retail_raw
GROUP BY 2
ORDER BY 2;

-- 7. C 시작 송장과 음수 수량의 교차 집계
SELECT '07_cancel_invoice_x_negative_quantity' AS check_name,
       invoice LIKE 'C%' AS invoice_starts_with_c,
       quantity < 0 AS has_negative_quantity,
       count(*) AS row_count
FROM retail.online_retail_raw
GROUP BY 2, 3
ORDER BY 2, 3;

-- 8. 국가·송장·고객 distinct count
SELECT '08_distinct_counts' AS check_name,
       count(DISTINCT country) AS countries,
       count(DISTINCT invoice) AS invoices,
       count(DISTINCT customer_id) AS customers
FROM retail.online_retail_raw;

-- 9. 완전 동일 행과 보수적인 중복 후보
WITH exact_groups AS (
    SELECT count(*) AS occurrences
    FROM retail.online_retail_raw
    GROUP BY invoice, stock_code, description, quantity,
             invoice_date, price, customer_id, country
    HAVING count(*) > 1
)
SELECT '09_exact_duplicates' AS check_name,
       count(*) AS duplicate_groups,
       coalesce(sum(occurrences), 0) AS affected_rows,
       coalesce(sum(occurrences - 1), 0) AS extra_rows
FROM exact_groups;

WITH candidate_groups AS (
    SELECT count(*) AS occurrences
    FROM retail.online_retail_raw
    GROUP BY invoice, stock_code, quantity, invoice_date, price, customer_id
    HAVING count(*) > 1
)
SELECT '09_duplicate_candidates' AS check_name,
       count(*) AS duplicate_groups,
       coalesce(sum(occurrences), 0) AS affected_rows,
       coalesce(sum(occurrences - 1), 0) AS extra_rows
FROM candidate_groups;

-- 10. Quantity * Price 기반 잠정 거래 금액 대사
SELECT '10_provisional_amount' AS check_name,
       sum(quantity::numeric * price) AS signed_amount,
       sum(quantity::numeric * price) FILTER (WHERE quantity > 0) AS positive_quantity_amount,
       sum(quantity::numeric * price) FILTER (WHERE quantity < 0) AS negative_quantity_amount
FROM retail.online_retail_raw;

-- 적재 완료 게이트: 불일치 시 오류를 발생시킨다.
DO $validation$
DECLARE
    actual_total bigint;
    first_sheet_total bigint;
    second_sheet_total bigint;
    latest_audit record;
BEGIN
    SELECT count(*) INTO actual_total
    FROM retail.online_retail_raw;

    SELECT count(*) INTO first_sheet_total
    FROM retail.online_retail_raw
    WHERE source_sheet = 'Year 2009-2010';

    SELECT count(*) INTO second_sheet_total
    FROM retail.online_retail_raw
    WHERE source_sheet = 'Year 2010-2011';

    SELECT * INTO latest_audit
    FROM retail.load_audit
    ORDER BY load_id DESC
    LIMIT 1;

    IF actual_total <> 1067371
       OR first_sheet_total <> 525461
       OR second_sheet_total <> 541910 THEN
        RAISE EXCEPTION
            'Row reconciliation failed: total %, first sheet %, second sheet %',
            actual_total, first_sheet_total, second_sheet_total;
    END IF;

    IF latest_audit IS NULL
       OR latest_audit.loaded_row_count <> actual_total
       OR latest_audit.expected_row_count <> actual_total
       OR latest_audit.source_sha256 <> 'BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980' THEN
        RAISE EXCEPTION 'Load audit reconciliation failed';
    END IF;

    RAISE NOTICE 'PASS: source, audit, and PostgreSQL row counts reconcile (% rows)', actual_total;
END
$validation$;
