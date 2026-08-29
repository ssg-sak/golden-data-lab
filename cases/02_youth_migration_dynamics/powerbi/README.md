# CASE 02 Power BI 대시보드 명세

이 문서는 방법론 7단계 Visualization의 Power BI 제작 계약이다. Python 한 페이지 화면은 [`../evidence/dashboard/01_one_page_decision.png`](../evidence/dashboard/01_one_page_decision.png)와 [`../notebooks/05_decision_dashboard.ipynb`](../notebooks/05_decision_dashboard.ipynb)가 재현한다.

바이너리 보고서는 [`CASE02_Youth_Priority.pbix`](./CASE02_Youth_Priority.pbix)다. 집계 테이블만 넣었고 비밀번호는 없다. Power BI Desktop에서 바로 연다.

재생성:

```powershell
pip install pbix-mcp
python cases/02_youth_migration_dynamics/src/build_powerbi_pbix.py
```

## Decision question

2025년 등록 국내이동 기준으로 청년(20-39세) 순이동과 전 연령 시도 간 흐름을 보고, 실태 점검을 어디에 먼저 둘 것인가?

## Data source

`.pbix`는 Python 검증 파이프라인의 **대시보드 입자 집계**를 Import 스냅샷으로 담는다. 원본 엑셀과 PostgreSQL 접속 정보는 넣지 않는다.

| 테이블 | 내용 | 주의 |
| --- | --- | --- |
| `KPI` | 2025 총이동·청년 이동·수도권 순이동 | 청년 정의 20-39 |
| `YouthProfile` | 시도별 청년 순이동과 유형 | 2025 스냅샷 |
| `Typology` | 유형별 시도 수 | 인과 군집이 아님 |
| `TopOD` | 전 연령 시도 간 상위 경로 | 청년 OD가 아님 |
| `CapitalYearly` | 수도권 대 비수도권 순이동 | |
| `MobilityRates` | 연령별 이동률 시계열 | 전국 |
| `Priority` | 점검 우선 시도 | `INSIGHTS.md`와 같은 순서 |
| `Notes` | 해석 한계 | |

CSV 사본은 [`data/`](./data/)에 있다. Desktop에서 Refresh하면 빌드 PC의 CSV 절대 경로를 찾는다. 다른 PC에서는 데이터 원본을 이 폴더로 바꾸거나, 스냅샷만 사용한다.

원본 Excel을 Power BI에 직접 연결하지 않는다.

## Page layout (1 page)

페이지 이름: `Youth Priority`

| 위치 | 시각화 | 필드 | 주의 |
| --- | --- | --- | --- |
| 상단 카드 | Card | Total Movers, Youth Movers, Youth Share, Capital Net, Seoul Youth Net | 인과·예측 카드 금지 |
| 좌상 | Bar | 시도별 청년(20-39) 순이동 | |
| 중상 | Bar | 유형별 시도 수 | |
| 우상 | Table | 우선 시도, 20대/30대 순이동 | |
| 좌하 | Line | 수도권 순이동 시계열 | |
| 중하 | Bar | 시도 간 상위 경로 | 제목에 전 연령 |
| 우하 | Table | 해석 한계 | |

슬라이서는 수도권/비수도권만 허용한다. 지도를 넣지 않는다(GeoJSON 없음).

## Completion gate

- [`CASE02_Youth_Priority.pbix`](./CASE02_Youth_Priority.pbix)가 열리고 Total Movers 카드가 6,117,784와 같다.
- OD 시각 제목이나 Notes에 전 연령임을 남긴다.
- 비밀번호와 서버 주소는 `.pbix`에 저장하지 않는다.
