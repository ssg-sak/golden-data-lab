# 표준 분석 방법론 (Methodology)

Golden Data Lab의 모든 분석 사례는 아래의 9단계 표준 흐름을 따릅니다.

1. **Business Question:** 해결하고자 하는 비즈니스/정책 질문 정의
2. **SQL Extraction:** 원천 데이터 추출 및 DBeaver(PostgreSQL)를 통한 기본 집계
3. **Data Quality Check:** 결측치, 이상치, 중복값 확인 및 정제 기준 확립
4. **Python EDA:** 데이터 분포, 추세, 세그먼트 파악 (Pandas, GeoPandas)
5. **Statistical Analysis:** 가설 검정 및 통계적 유의성 확인
6. **KPI & Segmentation:** 분석 목적에 맞는 핵심 성과 지표(KPI) 및 고객/지역 세분화
7. **Visualization (Power BI):** 의사결정자를 위한 1페이지 요약 대시보드 제작
8. **Insight & Action:** 분석 결과 해석 및 실무 적용 방안(Action Item) 도출
9. **Reproduction:** 제3자가 동일한 결과를 도출할 수 있도록 환경과 실행 스크립트 문서화
