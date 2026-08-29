# CASE 01 PostgreSQL 직접 적재 가이드

이 가이드는 적재를 직접 실행하고, 원본과 PostgreSQL 결과가 일치한다는 증거를 남기기 위한 절차다.

## 확인된 실행 환경과 원본

- PostgreSQL 18 서비스: `localhost:5432`에서 실행 중
- psql: `D:\Program Files\PostgreSQL\18\bin\psql.exe`
- 원본 SHA-256: `BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980`
- 원본 행 수: 1,067,371행

## 1. 데이터베이스 생성

1. DBeaver에서 `localhost:5432`의 기존 `postgres` 데이터베이스에 접속한다.
2. [`sql/00_create_database.sql`](./sql/00_create_database.sql)을 SQL Editor에서 직접 실행한다.
3. Database Navigator를 새로 고치고 `golden_data_lab` 데이터베이스 연결을 연다.

`golden_data_lab`이 이미 있다면 생성 문장은 다시 실행하지 않고 다음 단계로 이동한다.

## 2. raw 테이블 생성

1. DBeaver SQL Editor의 현재 연결이 `golden_data_lab`인지 확인한다.
2. [`sql/01_create_raw_table.sql`](./sql/01_create_raw_table.sql)을 실행한다.
3. 다음 확인 쿼리를 직접 실행한다.

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'retail'
ORDER BY table_name;
```

기대 결과는 `load_audit`, `online_retail_raw` 두 테이블이다.

## 3. Excel 원본 적재

PowerShell에서 이 저장소의 `golden-data-lab` 폴더로 이동한 뒤 실행한다.

```powershell
python cases/01_retail_customer_analytics/src/load_to_postgres.py `
  --host localhost `
  --port 5432 `
  --database golden_data_lab `
  --user postgres
```

비밀번호 입력 내용은 화면에 표시되지 않는다. 첫 적재에는 `--replace`를 사용하지 않는다.

성공 시 다음 값이 출력되어야 한다.

- `Year 2009-2010`: 525,461행
- `Year 2010-2011`: 541,910행
- 합계: 1,067,371행
- `Load committed successfully`

중간에 실패하면 전체 트랜잭션이 롤백된다. 원인을 확인한 뒤 같은 명령을 다시 실행한다.

## 4. 검증 로그 저장

프로젝트 루트에서 날짜를 실제 실행일로 바꾸어 실행한다.

```powershell
& "D:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -X -h localhost -p 5432 -U postgres -d golden_data_lab `
  -v ON_ERROR_STOP=1 `
  -f "cases/01_retail_customer_analytics/sql/02_validate_raw_load.sql" `
  -L "cases/01_retail_customer_analytics/evidence/validation_YYYYMMDD.log"
```

마지막에 아래 형식의 메시지가 나오면 적재 완료 게이트를 통과한 것이다.

```text
NOTICE: PASS: source, audit, and PostgreSQL row counts reconcile (1067371 rows)
```

## 5. 직접 수행 증빙 체크리스트

- [ ] DBeaver에서 데이터베이스 생성 SQL을 실행한 화면
- [ ] raw 테이블 두 개가 보이는 Database Navigator 화면
- [ ] 본인이 적재 명령을 입력하고 성공 메시지를 받은 터미널 화면
- [ ] `retail.load_audit` 조회 결과
- [ ] `validation_YYYYMMDD.log`와 마지막 `PASS` 메시지
- [ ] SQL과 Python 파일을 설명할 수 있는 간단한 작업 메모

공개 저장소에 올리기 전 캡처와 로그에서 비밀번호, 개인 PC 계정명, 개인 식별 가능한 DB 사용자명을 가린다.
