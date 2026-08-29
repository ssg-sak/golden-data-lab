# CASE 01 작업 기록

이 문서는 CASE 01에서 직접 수행한 PostgreSQL 적재, 검증, 데이터 품질 점검의 실행 결과와 의사결정을 시간순으로 기록한다. 비밀번호와 개인 식별 정보는 기록하지 않는다.

## 2026-08-22: PostgreSQL 원본 적재 및 검증

### 실행 환경

| 항목 | 확인 결과 |
| --- | --- |
| Database | `golden_data_lab` |
| Schema | `retail` |
| Raw table | `retail.online_retail_raw` |
| Audit table | `retail.load_audit` |
| PostgreSQL | 18.4, Windows 64-bit |
| Loader | `src/load_to_postgres.py` 1.0.0 |

### 원본 기준

| 항목 | 값 |
| --- | ---: |
| 파일 | `online_retail_II.xlsx` |
| 파일 크기 | 45,622,278 bytes |
| SHA-256 | `BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980` |
| `Year 2009-2010` | 525,461행 |
| `Year 2010-2011` | 541,910행 |
| 전체 | 1,067,371행 |

### 적재 결과

- `retail.load_audit.load_id`: 1
- 시작: 2026-08-22 08:59:29 KST
- 종료: 2026-08-22 09:01:06 KST
- 예상 행 수: 1,067,371행
- 적재 행 수: 1,067,371행
- 상태: `success`

### 검증 결과

다음 세 기준이 모두 1,067,371행으로 일치했다.

```text
Excel 원본 행 수 = 적재 감사 행 수 = PostgreSQL 실제 행 수
```

최종 완료 메시지:

```text
PASS: source, audit, and PostgreSQL row counts reconcile (1067371 rows)
```

증빙 파일:

- `evidence/validation_20260822.log`: `psql -L` 기본 로그
- `evidence/validation_20260822_full.log`: PowerShell 표준 출력과 표준 오류를 함께 저장한 전체 로그

PostgreSQL의 `NOTICE`는 PowerShell에서 `NativeCommandError` 형식으로 표시될 수 있다. 이번 실행은 `PASS`가 기록됐고 대사 불일치 예외가 없으므로 검증 성공이다. 깨진 `?뚮┝` 문자열은 한글 `알림`의 콘솔 인코딩 문제이며 결과에는 영향을 주지 않는다.

## 2026-08-22: Data Quality Check

### 실행 파일

- 노트북: `notebooks/01_data_quality_check.ipynb`
- 입력: `data/raw/online_retail_II.xlsx`
- 실행 환경: 프로젝트 `.venv`
- 실행 결과: 코드 셀 11개 전부 실행, 오류 출력 0개
- 환경 검사: `pip check` 통과

### 노트북 정리 내용

1. 고객 ID가 없는 정상 매출을 버리지 않도록 매출용 데이터와 고객용 데이터를 분리했다.
2. `sales_analysis_df`는 고객 ID 결측 여부와 관계없이 정상 양수 매출을 보존한다.
3. `customer_analysis_df`는 고객/RFM 분석을 위해 고객 ID가 있는 행만 포함한다.
4. 취소·반품, 결측, 중복, 가격 이상치를 raw에서 삭제하지 않고 플래그와 집계로 관리한다.
5. SQL과 같은 거래 컬럼 기준으로 중복을 계산하도록 정의를 통일했다.
6. 대용량 `cleaned_retail_data.csv` 자동 저장을 제거했다.

### 주요 품질 결과

| 점검 항목 | 결과 | 해석 및 처리 |
| --- | ---: | --- |
| 원본 행 수 | 1,067,371 | PostgreSQL 적재 행 수와 일치 |
| `Customer ID` 결측 | 243,007행, 22.77% | 매출 분석에는 보존하고 고객/RFM에서는 제외 |
| 식별 고객 | 5,942명 | 고객 분석 모집단 |
| 취소 송장 행 | 19,494 | `Invoice`가 `C`로 시작 |
| 음수 수량 행 | 22,950 | 반품·조정 후보 |
| 취소 또는 반품 행 | 22,951 | 두 플래그의 합집합 |
| 취소·음수 플래그 불일치 | 3,458 | 후속 분석에서 별도 점검 |
| 완전 동일 중복 추가 행 | 34,335 | raw에서는 삭제하지 않음; SQL 결과와 일치 |
| 분석 기간 | 2009-12-01~2011-12-09 | 현재 시장으로 일반화하지 않음 |

### 분석 데이터 범위

| 데이터셋 | 행 수 | 원본 대비 보존율 | 사용 목적 |
| --- | ---: | ---: | --- |
| `retail_df` | 1,067,371 | 100.00% | 원본 품질, 취소율, 반품률, 순매출 |
| `sales_analysis_df` | 1,041,670 | 97.59% | 상품·국가·기간별 정상 양수 매출 |
| `customer_analysis_df` | 805,549 | 75.47% | 고객·RFM·코호트 분석 |

### 원본 보존 확인

- 별도 CSV 생성 없음
- 원본 Excel 수정 없음
- 실행 후 SHA-256이 적재 기준 해시와 동일함

## 2026-08-27: Python EDA

### 산출물과 실행 검증

- 공통 데이터 준비 모듈: `src/data_preparation.py`
- 단위 테스트: `tests/test_data_preparation.py` 3개 통과
- 실행 노트북: `notebooks/02_python_eda.ipynb`
- 실행 상태: 코드 셀 13개 전부 실행, 오류 출력 0개, `NBFORMAT_VALID=True`
- 차트: `evidence/eda_figures/`의 PNG 4개를 원본 크기로 시각 검토
- 원본 SHA-256: 적재 기준 `BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980`과 일치

### 주요 EDA 결과

| 지표 | 결과 | 해석 경계 |
| --- | ---: | --- |
| 정상 양수 매출 | £20,972,594.57 | 취소·반품이 아니며 수량·가격이 양수인 거래 라인 기준 |
| 관측 순거래액 | £19,287,250.57 | raw의 `Quantity × Price` 합계이며 회계 매출·이익이 아님 |
| 정상 매출 중 고객 ID 식별 비중 | 84.6% | 고객 분석이 포함하는 매출 범위 |
| 정상 매출 고객 | 5,878명 | raw 식별 고객 5,942명 중 정상 양수 매출 조건을 통과한 모집단 |
| 2회 이상 주문 고객 비중 | 72.8% | `Source_Sheet + Invoice` 기준, 관측 기간 안에서만 측정 |
| 영국 정상 매출 비중 | 85.2% | 국가 필드는 거래 기록상의 국가이며 국적이 아님 |
| 완전 월 최고 정상 매출 | 2011-11, £1,509,496 | 2009-12와 2011-12는 부분 월이라 최고 월 비교에서 제외 |
| 상위 10개 StockCode 매출 비중 | 10.3% | `Manual`, 우편료 등 비상품 코드가 포함될 수 있음 |
| 음수 거래금액 / 정상 양수 매출 | 8.0% | 원거래와 직접 매칭하지 않아 환불률로 해석하지 않음 |

### 분석 결정과 제한

1. 고유 거래 라인 ID가 없으므로 중복 후보 34,335행을 EDA에서도 임의 제거하지 않았다.
2. 송장 번호의 시트 간 충돌을 막기 위해 주문 키를 `Source_Sheet + Invoice`로 정의했다.
3. 정상 매출·고객 분석·취소 및 순거래액 분석에 각각 `sales_analysis_df`, `customer_analysis_df`, `retail_df`를 사용했다.
4. 월별 차트에서는 경계의 두 부분 월을 표시하고 최고 완전 월 계산에서 제외했다.
5. 차트에서 확인된 차이는 기술통계이며 통계적 유의성이나 인과관계를 의미하지 않는다.

## 현재 완료 상태

- [x] PostgreSQL 데이터베이스 및 raw 테이블 생성
- [x] Excel 1,067,371행 적재
- [x] 적재 감사 기록 생성
- [x] SQL 원천 검증 10개 실행
- [x] 최종 `PASS` 확인 및 전체 로그 저장
- [x] Data Quality Check 노트북 실행 및 SQL 대사
- [x] Python EDA
- [x] 통계 분석
- [x] KPI 및 고객 세분화
- [x] 시각화와 인사이트

## 2026-08-28: 통계, KPI, 대시보드, 인사이트

### 실행 파일

- 모듈: `src/statistical_analysis.py`, `src/kpi_segmentation.py`, `src/decision_dashboard.py`
- 단위 테스트: `tests/` 17개 통과
- 노트북: `03_statistical_analysis.ipynb`, `04_kpi_segmentation.ipynb`, `05_decision_dashboard.ipynb`
- 일괄 실행: `src/run_later_stages.py`
- 해석: `INSIGHTS.md`
- 재현: `REPRODUCTION.md`
- 한 페이지 화면: `evidence/dashboard/01_one_page_decision.png`
- 분석 뷰: `sql/03_analysis_views.sql`

### 사전 지정 가설 결과

| 가설 | 검정 | p | 효과 크기 | 해석 |
| --- | --- | --- | --- | --- |
| H1 2010 vs 2011 완전 월 매출 | Wilcoxon | 0.52 | rank-biserial 0.24 | 연도 차이 없음 |
| H2 달력월 송장 금액 | Kruskal-Wallis | < 0.001 | epsilon-squared 0.003 | 유의하나 효과 무시 가능 |
| H3 영국 vs 비영국 송장 금액 | Mann-Whitney | < 0.001 | Cliff's delta −0.28 (small) | 영국 송장이 약간 작음 |
| H4 영국 여부와 송장 취소 | 카이제곱 | < 0.001 | Cramer's V 0.05 | 연관은 있으나 실무 크기 작음 |

두 해 모두 완전 월 최고 매출은 11월이다. 고객 매출 Gini 0.74, 상위 10% 고객이 식별 매출의 63.9%를 차지한다. 반품 금액이 있는 고객의 상위 10%가 반품 금액의 85.7%를 차지한다. 중복 제거와 플래그 불일치 제외는 핵심 비중 지표를 바꾸지 않았다.

### 확정 KPI와 세그먼트

- 정상 매출 £20,972,595, AOV £513, 재구매율 72.8%, 영국 매출 비중 85.2%
- RFM 기준일 2011-12-10
- Champions 1,290명이 식별 매출의 68.1%
- 재활성화 1순위 Cannot Lose 229명

## 2026-08-29: Power BI 제거

시각화 7단계는 matplotlib 한 페이지 PNG와 `05_decision_dashboard.ipynb`만 남긴다. `powerbi/` 폴더, `.pbix`, `src/build_powerbi_pbix.py`를 삭제했다.

## 다음 작업

CASE 01은 9단계를 마쳤다. 의사결정 화면은 `evidence/dashboard/01_one_page_decision.png`다. 다음 사례는 CASE 02다.
