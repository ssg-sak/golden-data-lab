-- CASE 02 parsed annex layer
-- 공식 통계표 엑셀을 값 변경 없이 tidy 테이블로 적재한다.
-- 이 파일은 golden_data_lab 데이터베이스에서 실행한다.

BEGIN;

CREATE SCHEMA IF NOT EXISTS migration;

CREATE TABLE IF NOT EXISTS migration.load_audit (
    load_id            bigserial PRIMARY KEY,
    source_file_name   text NOT NULL,
    source_sha256      char(64) NOT NULL,
    source_size_bytes  bigint NOT NULL,
    table_row_counts   jsonb NOT NULL,
    started_at         timestamptz NOT NULL,
    finished_at        timestamptz NOT NULL,
    database_user      text NOT NULL,
    loader_version     text NOT NULL,
    status             text NOT NULL CHECK (status IN ('success'))
);

CREATE TABLE IF NOT EXISTS migration.national_movers_yearly (
    year                   integer NOT NULL,
    movers_total           bigint,
    yoy_change             bigint,
    yoy_pct                numeric,
    movers_male            bigint,
    movers_female          bigint,
    sex_ratio_movers       numeric,
    mobility_rate_total    numeric,
    mobility_rate_yoy      numeric,
    mobility_rate_male     numeric,
    mobility_rate_female   numeric,
    sex_ratio_rate         numeric,
    intra_sido_movers      bigint,
    intra_sido_rate        numeric,
    inter_sido_movers      bigint,
    inter_sido_rate        numeric,
    source_sheet           text NOT NULL,
    source_row_number      integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.age_movers_yearly (
    year              integer NOT NULL,
    gender            text NOT NULL,
    age_group         text NOT NULL,
    movers            bigint,
    mobility_rate     numeric,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.sido_flow_yearly (
    year              integer NOT NULL,
    sido              text NOT NULL,
    measure           text NOT NULL,
    value             bigint,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.sido_gender_2025 (
    year                   integer NOT NULL,
    gender                 text NOT NULL,
    sido                   text NOT NULL,
    in_total               bigint,
    out_total              bigint,
    intra_sigungu          bigint,
    inter_sigungu_in       bigint,
    inter_sigungu_out      bigint,
    inter_sido_in          bigint,
    inter_sido_out         bigint,
    net                    bigint,
    in_rate                numeric,
    out_rate               numeric,
    intra_sigungu_rate     numeric,
    inter_sigungu_in_rate  numeric,
    inter_sigungu_out_rate numeric,
    inter_sido_in_rate     numeric,
    inter_sido_out_rate    numeric,
    net_rate               numeric,
    source_sheet           text NOT NULL,
    source_row_number      integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.sido_age_net_2025 (
    year              integer NOT NULL,
    gender            text NOT NULL,
    sido              text NOT NULL,
    age_group         text NOT NULL,
    net               bigint,
    is_capital        boolean NOT NULL,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.od_movers_2025 (
    year              integer NOT NULL,
    gender            text NOT NULL,
    destination       text NOT NULL,
    origin            text NOT NULL,
    movers            bigint,
    is_intra          boolean NOT NULL,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.od_net_2025 (
    year              integer NOT NULL,
    gender            text NOT NULL,
    destination       text NOT NULL,
    origin            text NOT NULL,
    net               bigint,
    is_intra          boolean NOT NULL,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.capital_yearly (
    year                 integer NOT NULL,
    net                  bigint,
    in_from_noncapital   bigint,
    in_seoul             bigint,
    in_incheon           bigint,
    in_gyeonggi          bigint,
    out_to_noncapital    bigint,
    out_seoul            bigint,
    out_incheon          bigint,
    out_gyeonggi         bigint,
    source_sheet         text NOT NULL,
    source_row_number    integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.monthly_movers (
    year                 integer NOT NULL,
    month                integer,
    period_type          text NOT NULL,
    movers_total         bigint,
    yoy_same_month_pct   numeric,
    yoy_cumulative_pct   numeric,
    intra_sido_movers    bigint,
    inter_sido_movers    bigint,
    mobility_rate        numeric,
    mobility_rate_yoy    numeric,
    intra_sido_rate      numeric,
    inter_sido_rate      numeric,
    source_sheet         text NOT NULL,
    source_row_number    integer NOT NULL
);

CREATE TABLE IF NOT EXISTS migration.reason_2025 (
    year              integer NOT NULL,
    sido              text NOT NULL,
    flow              text NOT NULL,
    reason            text NOT NULL,
    reason_label_ko   text NOT NULL,
    value             bigint,
    source_sheet      text NOT NULL,
    source_row_number integer NOT NULL
);

COMMENT ON SCHEMA migration IS '국가데이터처 2025 국내인구이동통계 결과 부표의 tidy 적재';
COMMENT ON COLUMN migration.od_movers_2025.destination IS '전입지. 행=전입지, 열=전출지로 해석한다';
COMMENT ON COLUMN migration.od_movers_2025.origin IS '전출지';
COMMENT ON COLUMN migration.sido_age_net_2025.age_group IS '5세 구간. 청년 분석은 20-24,25-29,30-34,35-39 합';

COMMIT;
