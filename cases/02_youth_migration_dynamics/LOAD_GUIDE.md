# CASE 02 PostgreSQL 직접 적재 가이드

이 가이드는 적재를 직접 실행하고, 원본과 PostgreSQL 결과가 일치한다는 증거를 남기기 위한 절차다.

## 확인된 실행 환경과 원본

- PostgreSQL 18 서비스: `localhost:5432`에서 실행 중
- Database: `golden_data_lab` (CASE 01에서 생성)
- Schema: `migration`
- psql: `D:\Program Files\PostgreSQL\18\bin\psql.exe`
- 원본 SHA-256: `FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D`
- 원본 크기: 204,601 bytes

## 1. 데이터베이스

CASE 01에서 `golden_data_lab`을 만들었으면 생략한다. 없다면 [`sql/00_create_database.sql`](./sql/00_create_database.sql)을 `postgres` 데이터베이스에서 한 번만 실행한다.

## 2. 스키마와 테이블

적재 스크립트가 [`sql/01_create_tables.sql`](./sql/01_create_tables.sql)을 실행한다. 수동이면 DBeaver 연결이 `golden_data_lab`인지 확인한 뒤 같은 파일을 실행한다.

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'migration'
ORDER BY table_name;
```

## 3. 적재

```powershell
python cases/02_youth_migration_dynamics/src/load_to_postgres.py `
  --host localhost `
  --port 5432 `
  --database golden_data_lab `
  --user postgres
```

비밀번호는 화면에 남지 않는다. 첫 적재에는 `--replace`를 사용하지 않는다. 이미 행이 있으면 중단되며, 재적재만 `--replace`를 쓴다.

성공 시 `Load committed successfully`와 `load_id`가 출력되어야 한다. 2026-08-29 실행 기준 `national_movers_yearly`는 **56행**(1970-2025, 각주 행 제외)이다.

## 4. 검증 로그 저장

```powershell
python cases/02_youth_migration_dynamics/src/run_sql_validation.py
```

또는 psql:

```powershell
& "D:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -X -h localhost -p 5432 -U postgres -d golden_data_lab `
  -v ON_ERROR_STOP=1 `
  -f "cases/02_youth_migration_dynamics/sql/02_validate_load.sql" `
  -L "cases/02_youth_migration_dynamics/evidence/validation_YYYYMMDD.log"
```

마지막에 아래 메시지가 나오면 적재 완료 게이트를 통과한 것이다.

```text
PASS: source, audit, and PostgreSQL migration tables reconcile (2025 movers 6117784)
```

분석용 뷰는 [`sql/03_analysis_views.sql`](./sql/03_analysis_views.sql)이다.

## 5. 직접 수행 증빙 체크리스트

- [x] `migration.load_audit` 조회, `status = success`
- [x] `validation_20260829.log`와 마지막 `PASS` 메시지
- [x] `validation_20260829_full.log`
- [ ] 공개 저장소 전 로그에서 비밀번호를 가린다
