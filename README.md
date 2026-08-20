# Golden Data Lab

Golden Data Lab은 여러 도메인의 원천 데이터를 동일한 분석 방법론으로 반복 분석하는 데이터 분석 포트폴리오입니다. SQL 추출부터 데이터 품질, Python 분석, 통계, KPI, Power BI, 실행 제안과 재현성까지 하나의 흐름으로 연결합니다.

## Project Goal

- 비즈니스 질문을 측정 가능한 분석 질문으로 바꾸기
- SQL과 Python을 역할에 맞게 사용하기
- 결측치, 중복, 이상치와 지표 정의를 명시적으로 관리하기
- 분석 결과를 의사결정과 실행 항목으로 연결하기
- 다른 사람이 같은 결과를 다시 만들 수 있도록 기록하기

## Standard Methodology

모든 사례는 [9단계 표준 분석 방법론](./docs/methodology.md)을 따릅니다.

| 단계 | 이름 | 핵심 작업 |
| --- | --- | --- |
| 1 | Business Question | 해결할 비즈니스·정책 질문과 의사결정 정의 |
| 2 | SQL Extraction | PostgreSQL 원천 적재, SQL 추출 및 기본 집계 |
| 3 | Data Quality Check | 결측치, 중복, 이상치와 정제 기준 확립 |
| 4 | Python EDA | 분포, 추세, 관계와 세그먼트 탐색 |
| 5 | Statistical Analysis | 가설 검정, 효과 크기와 불확실성 확인 |
| 6 | KPI & Segmentation | 핵심 지표와 고객·지역 분류 기준 정의 |
| 7 | Visualization | Power BI 의사결정 대시보드 제작 |
| 8 | Insight & Action | 검증된 사실을 실행 가능한 제안으로 변환 |
| 9 | Reproduction | 환경, 데이터 출처와 실행 순서 문서화 |

## Cases

### CASE 01: Retail Customer & Revenue Analytics

UCI Online Retail II의 약 106만 건 거래 라인을 이용해 고객과 매출 구조를 분석합니다.

- 기간: 2009-12-01 ~ 2011-12-09
- 핵심 주제: 데이터 품질, 취소·반품, 매출 지표, RFM, 코호트, 재구매
- 현재 상태: Business Question과 SQL Extraction 계약 확정, Data Quality 노트북 초안 작성
- [CASE 01 문서](./cases/01_retail_customer_analytics/README.md)
- [분석 용어 학습 가이드](./cases/01_retail_customer_analytics/STUDY_GUIDE.md)

이 데이터는 역사적 데이터이므로 현재 소매시장을 설명하는 근거로 사용하지 않습니다. CASE 01은 대규모 거래 데이터의 처리와 분석 방법론을 증명하는 사례입니다.

### CASE 02: Youth Migration & Regional Dynamics

행정안전부와 KOSIS 데이터를 이용해 청년층의 지역 간 이동과 정착·유출 패턴을 분석할 예정입니다.

- 현재 상태: 기획 단계
- [CASE 02 문서](./cases/02_youth_migration_dynamics/README.md)

## Repository Structure

```text
golden-data-lab/
├── cases/
│   ├── 01_retail_customer_analytics/
│   │   ├── data/
│   │   │   ├── raw/
│   │   │   └── processed/
│   │   ├── notebooks/
│   │   ├── src/
│   │   ├── README.md
│   │   └── STUDY_GUIDE.md
│   └── 02_youth_migration_dynamics/
├── common/
├── docs/
│   ├── methodology.md
│   └── case_template.md
├── .gitignore
└── requirements.txt
```

원본 및 정제 데이터 파일은 용량과 출처 관리 문제로 Git에 커밋하지 않습니다. 각 사례의 `data/raw`와 `data/processed`에는 디렉터리 구조만 보존합니다.

## Tech Stack

- Database: PostgreSQL, DBeaver
- Analysis: Python, pandas, GeoPandas, JupyterLab
- Statistics and Visualization: matplotlib, seaborn
- BI: Power BI
- Reproducibility: Git, GitHub, documented SQL and notebooks

## Quick Start

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python cases/01_retail_customer_analytics/src/download_data.py
jupyter lab
```

CASE 01 원본 데이터는 다운로드 스크립트가 `cases/01_retail_customer_analytics/data/raw/online_retail_II.xlsx`에 저장합니다.

## Working Principles

- 원본 데이터는 수정하지 않습니다.
- 지표마다 분모, 기간, 단위와 제외 조건을 기록합니다.
- 데이터에 없는 사실이나 인과관계를 추정해 단정하지 않습니다.
- 오래된 데이터의 결과를 현재 시장으로 일반화하지 않습니다.
- 결과뿐 아니라 실패한 가정, 분석 한계와 재현 절차도 남깁니다.
