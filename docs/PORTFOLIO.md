# 커리어 포트폴리오 안내

이 저장소를 이력서·GitHub 프로필·면접에서 쓰는 순서와, 지금 말할 수 있는 범위를 고정한다. Golden Data Lab은 **아직 진행 중인 작업**이 있다. 완료되지 않은 산출물을 완료된 것처럼 쓰지 않는다.

## 30초 소개

Golden Data Lab은 도메인이 달라도 **같은 9단계**로 분석을 반복하는 포트폴리오입니다. SQL 적재·품질 검사·Python·통계·KPI·시각화·인사이트·재현 문서를 한 흐름으로 남깁니다. 원본은 고치지 않고, 분모를 적고, 데이터에 없는 인과는 단정하지 않습니다.

## 지금 상태

| 사례 | 역할 | 상태 | 면접에서 보여줄 것 |
| --- | --- | --- | --- |
| [CASE 01 소매](../cases/01_retail_customer_analytics/README.md) | 방법론이 끝까지 도는지 증명 | **9단계 완료** | `INSIGHTS.md`, 한 페이지 PNG, `.pbix`, SQL `PASS` 로그 |
| [CASE 02 청년 이동](../cases/02_youth_migration_dynamics/README.md) | 공식 통계표·정의 잠금·교차 대사 | **진행 중** | 질문·청년 정의, PostgreSQL `migration` 검증, `INSIGHTS.md` 초안. `.pbix`와 실행된 노트북은 아직 없음 |

## 이력서에 쓸 문장

한 줄:

> 거래 데이터와 공식 인구이동 통계를 PostgreSQL에 적재하고, 품질 검사·가설 검정·KPI·의사결정 화면까지 같은 절차로 재현 가능하게 문서화한 분석 포트폴리오.

불릿 (사실만):

- UCI Online Retail II 약 106만 행을 PostgreSQL에 적재·검증하고, RFM·코호트·취소 패턴으로 유지·재활성화 우선순위를 정리함. 기간은 2009-12 ~ 2011-12이며 현재 소매시장으로 일반화하지 않음.
- 국가데이터처 2025 국내인구이동통계 부표를 tidy 표로 파싱하고, 원본 해시·행 수·핵심 지표를 SQL로 교차 대사함. 청년은 원표 5세 구간 합 20-39세로 잠금.
- 분석 파이프라인·단위 테스트·검증 로그·한계(말할 수 없는 것)를 저장소에 남김.

넣지 말 것:

- “청년 OD로 지방→서울 경로를 밝혔다” — 부표에 연령별 OD가 없다.
- “주택·일자리가 이동을 일으켰다” — 인과 자료가 없다.
- “CASE 02 Power BI까지 완료” — CSV와 PNG만 있고 `.pbix`는 없다.
- CASE 01 숫자를 2026년 이커머스 성과처럼 쓰기.

## 면접에서 여는 순서

1. 루트 [README](../README.md)의 9단계 표와 이 문서의 상태 표.
2. CASE 01 [`INSIGHTS.md`](../cases/01_retail_customer_analytics/INSIGHTS.md) → 한 페이지 [`01_one_page_decision.png`](../cases/01_retail_customer_analytics/evidence/dashboard/01_one_page_decision.png) → 필요하면 `.pbix`.
3. CASE 01 [`sql/02_validate_raw_load.sql`](../cases/01_retail_customer_analytics/sql/02_validate_raw_load.sql)과 `evidence`의 `PASS` 로그. “적재만 하고 검증을 안 한 분석”이 아님을 보여 준다.
4. CASE 02는 **정의와 대사**를 보여 준다. [`README.md`](../cases/02_youth_migration_dynamics/README.md) 잠금 정의 → [`LOAD_GUIDE.md`](../cases/02_youth_migration_dynamics/LOAD_GUIDE.md) → [`INSIGHTS.md`](../cases/02_youth_migration_dynamics/INSIGHTS.md). 서울 청년 순유입과 20대/30대 부호가 갈린다는 점, 청년 OD가 없다는 한계를 먼저 말한다.
5. 물어보면 [`WORK_LOG.md`](../cases/02_youth_migration_dynamics/WORK_LOG.md)에서 각주 행을 연도로 오인한 뒤 파서를 고치고 재적재한 기록을 보여 준다.

## GitHub 프로필 README에 붙일 블록

[`ssg-sak`](https://github.com/ssg-sak) 프로필 저장소에 아래를 붙여도 된다. CASE 02가 끝나면 상태 한 줄만 고친다.

```markdown
### Data analysis
- [golden-data-lab](https://github.com/ssg-sak/golden-data-lab) — SQL·데이터 품질·Python·통계·KPI·Power BI를 9단계로 반복하는 분석 포트폴리오.
  - CASE 01 소매 고객·매출: 방법론 전 과정 완료 (2009–2011 거래, 현재 시장으로 일반화하지 않음)
  - CASE 02 청년 국내이동: 공식 통계 적재·교차 대사·인사이트 초안까지 진행 중
```

다른 공개 저장소(서비스·팀 프로젝트)와 역할을 나누려면, 이 레포는 **분석 절차와 재현**을 보여 주는 자리로 두고, 제품 화면은 해당 레포 README에 맡긴다.

## CASE 02가 끝나기 전에 남은 것

면접에서 “아직”이라고 말해도 되는 목록이다.

- Power BI `.pbix` (지금은 `powerbi/data/*.csv`와 PNG)
- Jupyter 노트북 셀 실행 결과 저장 (지금은 생성 스크립트로 만든 골격)
- 시도 경계 지도 (GeoJSON 없음, 막대 그래프만 사용)
- 시군구·연령별 OD 등 이 부표에 없는 확장 (원본이 없으면 만들지 않음)

## 작업이 늘면 이 문서에서 고칠 곳

- 위 상태 표
- 이력서 불릿의 CASE 02 범위
- 프로필 README 상태 한 줄
- 루트 README의 CASE 02 “현재 상태”
