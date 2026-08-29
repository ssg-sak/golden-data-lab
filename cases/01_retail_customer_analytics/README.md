# CASE 01: Retail Customer & Revenue Analytics

이 사례는 Golden Data Lab의 [9단계 표준 분석 방법론](../../docs/methodology.md)을 따른다. 1단계부터 9단계까지 CASE 01 산출물을 완료했다.

분석 용어가 익숙하지 않을 때는 [CASE 01 분석 용어 학습 가이드](./STUDY_GUIDE.md)를 함께 참고한다.

PostgreSQL 원천 적재는 [CASE 01 PostgreSQL 직접 적재 가이드](./LOAD_GUIDE.md)를 따른다.

실제 실행 내역과 검증 결과는 [CASE 01 작업 기록](./WORK_LOG.md)에 시간순으로 정리한다.

## Methodology Status

| 단계 | 상태 | 핵심 산출물 |
| --- | --- | --- |
| 1. Business Question | 확정 | 의사결정, 분석 질문, 범위, 성공 기준 |
| 2. SQL Extraction | 완료 | PostgreSQL 원천 테이블, 적재 감사, 검증 로그와 `PASS` |
| 3. Data Quality Check | 완료 | 실행 완료된 `01_data_quality_check.ipynb` |
| 4. Python EDA | 완료 | 실행 완료된 `02_python_eda.ipynb`, 검증된 표와 차트 4개 |
| 5. Statistical Analysis | 완료 | `03_statistical_analysis.ipynb`, 가설 4개와 민감도 표 |
| 6. KPI & Segmentation | 완료 | `04_kpi_segmentation.ipynb`, KPI 사전, RFM, 코호트 |
| 7. Visualization | 완료 | 한 페이지 PNG, `CASE01_Retention_Priority.pbix`, Power BI 명세 |
| 8. Insight & Action | 완료 | [`INSIGHTS.md`](./INSIGHTS.md) |
| 9. Reproduction | 완료 | [`REPRODUCTION.md`](./REPRODUCTION.md) |

## 1. Business Question

### Decision Context

- **가상 의사결정자:** 온라인 소매업체의 CRM·Revenue Manager
- **의사결정:** 어떤 고객군과 거래 구간에 유지, 재활성화, 취소·반품 개선 노력을 우선 배분할 것인가?
- **분석 목적:** 완료 매출의 구조와 고객 반복 구매 행동을 파악하고, 매출 기여도가 높거나 이탈 위험이 있는 고객군을 식별한다.

### Primary Question

> 관측 기간의 실현 매출은 어떤 고객 행동과 거래 특성에서 발생했으며, 고객 유지와 취소·반품 관리를 위해 어떤 세그먼트를 우선 관리해야 하는가?

### Supporting Questions

1. 매출과 주문은 시기, 국가, 상품 및 고객별로 어떻게 분포하는가?
2. 신규 고객은 이후에도 재구매하며, 코호트별 유지 패턴은 어떻게 다른가?
3. 최근성, 구매 빈도, 구매 금액을 기준으로 어떤 고객군을 구분할 수 있는가?
4. 취소·반품은 거래량과 매출에 어느 정도 영향을 주며 특정 고객·상품에 집중되는가?
5. 분석 결과에 따라 유지, 재활성화 또는 거래 품질 개선의 우선순위를 어떻게 정할 수 있는가?

### Scope

- **포함:** 거래 추세, 완료 매출, 순매출, 주문, 고객, 상품, 국가, 취소·반품, RFM, 코호트
- **제외:** 이익·마진, 광고 성과, 배송 성과, 고객 인구통계, 인과효과, 미래 매출 예측
- **이유:** 원본 데이터에 원가, 광고비, 배송 상태, 고객 속성 및 실험 정보가 없다.

### Success Criteria

- 모든 핵심 지표는 계산식, 분석 단위, 기간, 취소·반품 포함 여부를 명시한다.
- 비즈니스 질문마다 SQL 또는 Python 결과와 연결되는 검증 가능한 근거를 제시한다.
- 고객 ID 결측 거래가 고객 분석에 미치는 영향을 수치로 공개한다.
- 원본에서 최종 결과까지 제3자가 같은 순서로 재현할 수 있어야 한다.
- 결과는 관측 기간 내부의 행동 패턴으로만 해석하고 현재 시장으로 일반화하지 않는다.

## 2. SQL Extraction

### Source and Grain

- **Source:** UCI Online Retail II
- **File:** `data/raw/online_retail_II.xlsx`
- **Sheets:** `Year 2009-2010`, `Year 2010-2011`
- **Period:** 2009-12-01 ~ 2011-12-09
- **Raw grain:** 송장에 포함된 상품 한 줄, 즉 `invoice line item`
- **Important constraint:** 원본에는 고유 거래 라인 ID가 없으므로 동일 행을 즉시 중복 삭제하지 않는다.

### PostgreSQL Contract

| 구분 | 확정 내용 |
| --- | --- |
| Schema | `retail` |
| Raw table | `retail.online_retail_raw` |
| Source of truth | 두 Excel 시트를 행 방향으로 합친 원천 테이블 |
| Load policy | 원본 값은 변경하지 않고 `source_sheet`, `source_row_number`, `loaded_at`만 추가 |
| Query tool | DBeaver에서 PostgreSQL SQL 실행 |
| Python handoff | 검증된 SQL view 또는 명시적 `SELECT` 결과를 pandas로 로드 |

### Raw Table Fields

| 컬럼 | PostgreSQL 타입 | 의미 |
| --- | --- | --- |
| `invoice` | `text` | 송장 번호. `C` 시작 여부는 후속 품질 단계에서 검증 |
| `stock_code` | `text` | 상품 코드 |
| `description` | `text` | 상품 설명, 결측 허용 |
| `quantity` | `integer` | 거래 수량. 음수는 취소·반품 후보 |
| `invoice_date` | `timestamp` | 거래 일시. 원본에 시간대 정보 없음 |
| `price` | `numeric(12,4)` | 단가 |
| `customer_id` | `bigint` | 고객 식별자, 결측 허용 |
| `country` | `text` | 거래에 기록된 국가. 고객 거주지로 단정하지 않음 |
| `source_sheet` | `text` | 원본 시트명 |
| `source_row_number` | `integer` | 시트 내 원본 행 번호 |
| `loaded_at` | `timestamptz` | PostgreSQL 적재 시각 |

### Required SQL Outputs

SQL Extraction 단계에서는 데이터를 임의로 정제하지 않고 다음 원천 검증과 기본 집계까지만 수행한다.

1. 시트별·전체 행 수 대사
2. 컬럼별 결측 건수와 비율
3. 최소·최대 거래 일시 및 월별 행 수
4. `Customer ID` 보유·결측 거래 수
5. 음수·0·양수 `Quantity` 분포
6. 음수·0·양수 `Price` 분포
7. `C` 시작 송장과 음수 수량의 교차 집계
8. 국가·송장·고객의 distinct count
9. 완전 동일 행과 중복 후보의 건수
10. `Quantity * Price` 기반 잠정 거래 금액의 합계 대사

### Handoff and Completion Gate

2단계 완료 조건은 다음과 같다.

- 두 시트의 적재 행 수 합계가 PostgreSQL 원천 테이블 행 수와 일치한다.
- 원본 컬럼과 PostgreSQL 타입 매핑이 문서와 일치한다.
- 위 10개 검증 쿼리가 오류 없이 실행되고 결과가 저장된다.
- Python에서 사용할 쿼리 또는 view의 컬럼, 행 단위, 필터 조건이 명시된다.
- 결측치 제거, 취소·반품 제외, 이상치 처리, 중복 제거는 수행하지 않고 3단계로 넘긴다.

## Data Recency and Interpretation

이 데이터는 2009~2011년의 역사적 거래 데이터다. 현재 영국 소매시장이나 최신 소비 트렌드를 설명하는 근거로 사용하지 않는다. 이 사례의 목적은 대규모 거래 데이터에서 SQL 추출, 품질 관리, 고객·매출 분석 및 재현 가능한 의사결정 과정을 증명하는 것이다.

날짜를 최근 연도로 임의 변경하지 않으며, 현재 시장에 적용할 결론은 최신 데이터로 다시 검증해야 한다.

## Next Step

PostgreSQL 적재부터 재현 문서까지 CASE 01을 완료했다. 실행 근거는 [`WORK_LOG.md`](./WORK_LOG.md), 실행 제안은 [`INSIGHTS.md`](./INSIGHTS.md), 재현 순서는 [`REPRODUCTION.md`](./REPRODUCTION.md)다.

Power BI 보고서는 [`powerbi/CASE01_Retention_Priority.pbix`](./powerbi/CASE01_Retention_Priority.pbix)다. 명세와 재생성은 [`powerbi/README.md`](./powerbi/README.md)를 따른다. 다음 사례는 CASE 02 기획을 분석 질문과 데이터 계약으로 구체화하는 것이다.
