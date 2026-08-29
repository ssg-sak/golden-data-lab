-- CASE 01 전용 데이터베이스를 최초 한 번만 생성한다.
-- DBeaver에서 기존 postgres 데이터베이스에 연결한 뒤 이 문장만 실행한다.
-- 이미 golden_data_lab 데이터베이스가 있다면 다시 실행하지 않는다.

CREATE DATABASE golden_data_lab
    WITH
    ENCODING = 'UTF8'
    TEMPLATE = template0;
