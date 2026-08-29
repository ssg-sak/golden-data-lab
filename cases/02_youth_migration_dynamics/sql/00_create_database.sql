-- CASE 02 uses the existing golden_data_lab database.
-- DBeaver에서 기존 postgres 데이터베이스에 연결한 뒤, 데이터베이스가 없을 때만 실행한다.

CREATE DATABASE golden_data_lab
    WITH
    ENCODING = 'UTF8'
    TEMPLATE = template0;
