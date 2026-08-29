# CASE 02 Power BI

`.pbix`는 아직 없다. 의사결정 화면의 기준 이미지는 [`../evidence/dashboard/01_one_page_decision.png`](../evidence/dashboard/01_one_page_decision.png)다.

이 폴더의 CSV는 Python 집계 스냅샷이다. 원본 100만 행을 넣지 않으며 DB 비밀번호도 넣지 않는다.

## CSV

`powerbi/data/`에 `run_analysis.py`가 만든 분석 표를 복사한다.

| 파일 | 용도 |
| --- | --- |
| youth_profile_2025.csv | 시도별 청년 순이동과 유형 |
| typology_summary.csv | 유형별 시도 수 |
| top_od_2025.csv | 전 연령 시도 간 상위 경로 |
| youth_mobility_2005_2025.csv | 연령별 이동률 시계열 |
| capital_yearly.csv | 수도권 대 비수도권 순이동 |
| kpi.csv | 헤드라인 KPI |

새로고침은 이 PC 경로에 묶일 수 있다. 다른 기기에서는 폴더를 다시 지정한다.

## 해석

OD와 사유는 전 연령이다. 청년 순이동 막대와 같은 시각에 두더라도 제목에 연령을 명시한다.
