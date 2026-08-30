# 표준 분석 방법론 (Methodology)

Golden Data Lab의 모든 분석 사례는 아래의 9단계 표준 흐름을 따릅니다.

1. **Business Question:** 해결하고자 하는 비즈니스/정책 질문 정의
2. **SQL Extraction:** 원천 데이터 추출 및 DBeaver(PostgreSQL)를 통한 기본 집계
3. **Data Quality Check:** 결측치, 이상치, 중복값 확인 및 정제 기준 확립
4. **Python EDA:** 데이터 분포, 추세, 세그먼트 파악 (Pandas, GeoPandas)
5. **Statistical Analysis:** 가설 검정 및 통계적 유의성 확인
6. **KPI & Segmentation:** 분석 목적에 맞는 핵심 성과 지표(KPI) 및 고객/지역 세분화
7. **Visualization:** matplotlib로 의사결정용 1페이지 PNG 대시보드를 만든다. 숫자는 앞 단계 KPI·통계와 같아야 한다.
8. **Insight & Action:** 분석 결과 해석 및 실무 적용 방안(Action Item) 도출
9. **Reproduction:** 제3자가 동일한 결과를 도출할 수 있도록 환경과 실행 스크립트 문서화

7단계의 산출물은 Jupyter 노트북과 `evidence/dashboard/`의 PNG다. 외부 BI 도구 파일은 쓰지 않는다. 공개 웹 화면은 `docs/dashboard/`이며 같은 집계를 읽기 전용으로 보여 준다.
