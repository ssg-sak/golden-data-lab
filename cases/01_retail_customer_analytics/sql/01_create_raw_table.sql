-- CASE 01 raw layer
-- 이 파일은 golden_data_lab 데이터베이스에서 실행한다.

BEGIN;

CREATE SCHEMA IF NOT EXISTS retail;

CREATE TABLE IF NOT EXISTS retail.online_retail_raw (
    invoice           text,
    stock_code        text,
    description       text,
    quantity          integer,
    invoice_date      timestamp without time zone,
    price             numeric(12, 4),
    customer_id       bigint,
    country           text,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL,
    loaded_at         timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE retail.online_retail_raw IS
    'UCI Online Retail II의 두 Excel 시트를 값 변경 없이 합친 원천 거래 라인';
COMMENT ON COLUMN retail.online_retail_raw.source_row_number IS
    '헤더를 포함한 Excel 시트의 실제 행 번호';

CREATE TABLE IF NOT EXISTS retail.load_audit (
    load_id            bigserial PRIMARY KEY,
    source_file_name   text NOT NULL,
    source_sha256      char(64) NOT NULL,
    source_size_bytes  bigint NOT NULL,
    expected_row_count bigint NOT NULL,
    loaded_row_count   bigint NOT NULL,
    sheet_row_counts   jsonb NOT NULL,
    started_at         timestamptz NOT NULL,
    finished_at        timestamptz NOT NULL,
    database_user      text NOT NULL,
    loader_version     text NOT NULL,
    status             text NOT NULL CHECK (status IN ('success'))
);

COMMIT;
