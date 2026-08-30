# CASE 02: Youth Migration & Regional Dynamics

이 사례는 Golden Data Lab의 [9단계 표준 분석 방법론](../../docs/methodology.md)을 따른다. 1단계부터 9단계까지 산출물이 있다. 시도 지도는 통계청 2018 경계에 2025 청년 순이동을 붙인 것이다.

분석 용어는 [CASE 02 분석 용어 학습 가이드](./STUDY_GUIDE.md)를 참고한다. PostgreSQL 적재는 [LOAD_GUIDE.md](./LOAD_GUIDE.md)를 따른다. 실행 내역은 [WORK_LOG.md](./WORK_LOG.md)에 있다.

## Methodology Status

| 단계 | 상태 | 핵심 산출물 |
| --- | --- | --- |
| 1. Business Question | 확정 | 의사결정, 청년 정의, 수도권 정의, 범위 |
| 2. SQL Extraction | 완료 | `migration` 스키마, 적재 감사, 검증 SQL `PASS` |
| 3. Data Quality Check | 완료 | 교차 대사 14건 `PASS`, 실행된 `01_data_quality_check.ipynb` |
| 4. Python EDA | 완료 | 실행된 `02_python_eda.ipynb`, 청년 순이동·OD·이동률 |
| 5. Statistical Analysis | 완료 | 가설 4개, 정의 민감도, 실행된 `03_statistical_analysis.ipynb` |
| 6. KPI & Segmentation | 완료 | KPI 사전, 4유형 분류, 실행된 `04_kpi_segmentation.ipynb` |
| 7. Visualization | 완료 | 시도 단계색지도, matplotlib 한 페이지 PNG, `05_decision_dashboard.ipynb` |
| 8. Insight & Action | 완료 | [`INSIGHTS.md`](./INSIGHTS.md) |
| 9. Reproduction | 완료 | [`REPRODUCTION.md`](./REPRODUCTION.md) |

## 1. Business Question

### Decision Context

- **가상 의사결정자:** 광역·기초 청년정책·인구정책 담당자
- **의사결정:** 청년 순유출이 큰 지역, 20대만 들어오고 30대가 나가는 지역, 20·30대가 함께 들어오는 지역 중 어디에 실태 점검과 정책 설계 여력을 먼저 둘 것인가?
- **분석 목적:** 등록 국내이동 통계에서 청년(20-39세) 순이동의 공간 패턴과 전 연령 시도 간 흐름을 구분해 우선 지역을 식별한다.

### Primary Question

> 2025년 등록 국내이동 기준으로 청년(20-39세)은 어느 시도에서 순유입·순유출되며, 20대와 30대의 부호가 갈리는 지역은 어디이고, 시도 간 전체 연령 흐름은 어디로 몰리는가?

### Supporting Questions

1. 전국 이동 규모와 청년 연령의 이동률은 2005-2025에 어떻게 달라졌는가?
2. 2025년 시도별 청년 순이동은 전체 순이동과 같은 방향인가?
3. 수도권은 비수도권 대비 순유입을 유지하는가, 내부 재배분은 어느 경로인가?
4. 전입 사유(직업·주택·교육 등)는 시도별로 어떻게 다른가? (전 연령)
5. 위 패턴을 유형으로 나누면 점검을 어디에 먼저 둘 수 있는가?

### Scope

- **포함:** 등록 국내이동, 시도 단위, 5세 연령, 성별, 시도 간 OD(전 연령), 수도권 대 비수도권, 전입 사유(전 연령)
- **제외:** 시군구 내부 원인, 해외 이동, 주거·일자리·대학의 인과효과, 미래 인구 예측, 미등록 이동
- **이유:** 원본은 행정 등록 이동 집계이며 이동 동기 조사표가 아니다. 청년 OD(전출지×전입지×연령)는 이 부표에 없다.

### Locked definitions

| 항목 | 확정 |
| --- | --- |
| 청년 | 20-24 + 25-29 + 30-34 + 35-39세 |
| 비교 정의 | 민감도용 20-34세. 충남만 부호가 바뀐다 |
| e-지방지표 | 청년 19-39. 이 분석과 직접 대사하지 않음 |
| 수도권 | 서울, 인천, 경기 |
| 순이동 | 전입 − 전출. 전국 합은 0 |
| OD 방향 | 행 = 전입지, 열 = 전출지 (서울 행 대사로 확정) |
| 이동의 의미 | 전입신고가 된 국내이동. “떠나고 싶어서”가 아님 |

### Success Criteria

- 핵심 지표마다 계산식, 단위, 기간, 연령 정의를 적는다.
- 표 사이 교차 대사가 모두 통과한다.
- 청년 순이동과 전 연령 OD를 같은 문장에서 섞지 않는다.
- 제3자가 원본 해시부터 같은 숫자를 다시 만들 수 있다.

## 2. SQL Extraction

### Source and Grain

- **Source:** 국가데이터처 「2025년 국내인구이동통계 결과」 부표 xlsx
- **File:** `data/raw/2025_domestic_migration_statistics.xlsx`
- **SHA-256:** `FE066C40AAE0AE5C34C67947B404DC8943405C9BF0A7952DA09B0CF26D901E9D`
- **Size:** 204,601 bytes
- **Primary URL:** `https://mods.go.kr/boardDownload.es?bid=205&list_no=443278&seq=4`
- **Fallback:** KDI 자료실 `callDownload.do?num=276443&filenum=2`
- **Period:** 추세 표는 1970/2005-2025, 시도×연령 순이동과 OD는 **2025년 스냅샷**
- **Raw grain:** 공식 통계표 셀. 개인 이동 기록이 아니다.

### PostgreSQL Contract

| 구분 | 확정 내용 |
| --- | --- |
| Schema | `migration` |
| Source of truth | 원본 xlsx. DB는 파서 출력의 감사 가능한 복사본 |
| Load policy | 셀 값을 바꾸지 않고 tidy 열로만 재배열. `source_sheet`, `source_row_number` 보존 |
| Query tool | DBeaver에서 PostgreSQL SQL 실행 |
| Python handoff | 같은 파서가 pandas와 COPY에 사용된다 |
| 검증 로그 | `evidence/validation_20260829.log`, `evidence/validation_20260829_full.log` |

잔여 시트 `8.월별`(2009-2011 월별)은 적재하지 않는다. 표 1 각주(`* 1970년...`)는 연도 행으로 읽지 않는다.

### Required SQL Outputs

1. 시트(테이블)별·전체 행 수 대사
2. 2025 총이동자 6,117,784
3. 연도 범위 1970-2025 (전국 이동 시계열 56행)
4. 핵심 값 결측 0건
5. 전국 순이동 0
6. 청년(20-39) 이동자 2,761,243
7. 서울 20-24 순이동 +25,664, 30-34 −10,861
8. OD 행=전입지 대사 (서울 시도간 전입 438,327)
9. 수도권 순이동 +38,465
10. 시도별 청년 순이동 뷰, 시도 간 상위 경로 뷰

### Handoff and Completion Gate

2단계 완료 조건은 다음과 같다.

- 원본 SHA-256이 `load_audit`와 일치한다.
- tidy 행 수가 검증 SQL 기대값과 일치한다.
- `sql/02_validate_load.sql`이 오류 없이 끝나고 `PASS`가 기록된다.
- 결측 삭제, 유형 분류는 이 단계에서 하지 않는다.

## Data Recency and Interpretation

2025년 등록 국내이동과 그 이전 공식 시계열이다. 주택시장, 대학 정원, 일자리 정책의 효과를 이 표만으로 단정하지 않는다. 시군구 청년정책의 성과 지표로 바로 쓰지 않는다.

## Next Step

실행 근거는 [`WORK_LOG.md`](./WORK_LOG.md), 제안은 [`INSIGHTS.md`](./INSIGHTS.md), 재현은 [`REPRODUCTION.md`](./REPRODUCTION.md)다. 한 페이지 화면은 [`evidence/dashboard/01_one_page_decision.png`](./evidence/dashboard/01_one_page_decision.png), 시도 지도는 [`evidence/figures/01_youth_net_2025.png`](./evidence/figures/01_youth_net_2025.png)다. 공개 웹 화면은 [GitHub Pages 대시보드](https://ssg-sak.github.io/golden-data-lab/dashboard/)다. 시군구 순이동과 연령별 시도 간 OD는 KOSIS 별도 표이며, 이 부표·이 지도의 단위는 시도이다.
