# CASE 01 적재 증빙

이 폴더에는 PostgreSQL 적재를 직접 수행하고 검증한 기록을 보관한다.

전체 실행 내역과 데이터 품질 결과는 [`../WORK_LOG.md`](../WORK_LOG.md)에 기록한다.

## 고정된 원본 기준

- 파일: `online_retail_II.xlsx`
- SHA-256: `BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980`
- `Year 2009-2010`: 525,461행
- `Year 2010-2011`: 541,910행
- 전체: 1,067,371행

## 남길 증거

1. DBeaver에서 `00_create_database.sql`과 `01_create_raw_table.sql`을 실행한 화면
2. 본인이 터미널에서 `load_to_postgres.py`를 실행하는 화면
3. `retail.load_audit`에 기록된 원본 해시, 행 수, DB 사용자, 적재 시각
4. `02_validate_raw_load.sql`의 전체 출력 로그
5. 검증 마지막의 `PASS` 메시지

비밀번호, 개인 PC 계정명, 접속 문자열은 캡처나 Git 커밋에 포함하지 않는다.

## 검증 로그 생성 명령

프로젝트 루트에서 다음 명령을 직접 실행한다. 날짜는 실제 실행일로 바꾼다.

```powershell
& "D:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -X -h localhost -p 5432 -U postgres -d golden_data_lab `
  -v ON_ERROR_STOP=1 `
  -f "cases/01_retail_customer_analytics/sql/02_validate_raw_load.sql" `
  -L "cases/01_retail_customer_analytics/evidence/validation_YYYYMMDD.log"
```

로그를 공개하기 전 DB 사용자명 등 개인 식별 정보가 포함되지 않았는지 검토한다.

## Python EDA 증빙

- 실행 노트북: [`../notebooks/02_python_eda.ipynb`](../notebooks/02_python_eda.ipynb)
- 공통 데이터 준비 모듈: [`../src/data_preparation.py`](../src/data_preparation.py)
- 차트 PNG: [`eda_figures/`](./eda_figures/)
- 실행 결과: 코드 셀 13개 전부 실행, 오류 출력 0개, `NBFORMAT_VALID=True`
- 원본 보존: 실행 후 SHA-256이 고정된 원본 기준과 동일

## 통계·KPI·대시보드 증빙

- 요약 JSON: [`later_stages_summary.json`](./later_stages_summary.json)
- Lorenz: [`stats_figures/01_customer_lorenz.png`](./stats_figures/01_customer_lorenz.png)
- RFM·코호트: [`kpi_figures/`](./kpi_figures/)
- 한 페이지 의사결정 화면: [`dashboard/01_one_page_decision.png`](./dashboard/01_one_page_decision.png)
- 노트북: `03_statistical_analysis.ipynb`, `04_kpi_segmentation.ipynb`, `05_decision_dashboard.ipynb`
- 해석: [`../INSIGHTS.md`](../INSIGHTS.md)
