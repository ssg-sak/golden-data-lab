-- CASE 01 analysis views for Power BI or DBeaver
-- Run in golden_data_lab after the raw load has passed validation.
-- Filters match src/data_preparation.py purpose splits.

BEGIN;

CREATE OR REPLACE VIEW retail.v_sales_analysis AS
SELECT
    invoice,
    stock_code,
    description,
    quantity,
    invoice_date,
    price,
    customer_id,
    country,
    source_sheet,
    source_row_number,
    source_sheet || '|' || invoice AS invoice_key,
    quantity::numeric * price AS total_revenue,
    date_trunc('month', invoice_date)::date AS invoice_month,
    CASE
        WHEN date_trunc('month', invoice_date) IN (DATE '2009-12-01', DATE '2011-12-01')
            THEN true
        ELSE false
    END AS is_partial_month
FROM retail.online_retail_raw
WHERE invoice IS NOT NULL
  AND stock_code IS NOT NULL
  AND invoice_date IS NOT NULL
  AND quantity > 0
  AND price > 0
  AND upper(invoice) NOT LIKE 'C%';

COMMENT ON VIEW retail.v_sales_analysis IS
    'Python sales_analysis_df와 같은 정상 양수 매출. 고객 ID 결측 행을 포함합니다.';

CREATE OR REPLACE VIEW retail.v_customer_analysis AS
SELECT *
FROM retail.v_sales_analysis
WHERE customer_id IS NOT NULL;

COMMENT ON VIEW retail.v_customer_analysis IS
    'Python customer_analysis_df와 같은 식별 고객 정상 매출.';

CREATE OR REPLACE VIEW retail.v_monthly_sales AS
SELECT
    invoice_month,
    bool_or(is_partial_month) AS is_partial_month,
    sum(total_revenue) AS gross_sales,
    count(DISTINCT invoice_key) AS orders,
    sum(quantity) AS units
FROM retail.v_sales_analysis
GROUP BY invoice_month;

COMMIT;
