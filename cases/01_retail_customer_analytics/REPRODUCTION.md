# CASE 01 Reproduction

제3자가 같은 원본, 같은 코드, 같은 순서로 같은 숫자를 다시 만들 수 있게 한다. 비밀번호와 개인 식별 정보는 기록하지 않는다.

## Environment

| 항목 | 값 |
| --- | --- |
| OS | Windows 10, PowerShell |
| Python | 프로젝트 `.venv` |
| 패키지 | 저장소 루트 `requirements.txt` (`pandas`, `scipy`, `matplotlib`, `seaborn`, `openpyxl`, `jupyterlab`, `nbclient`) |
| Database | PostgreSQL 18, `golden_data_lab.retail` (SQL 단계) |
| 원본 | `cases/01_retail_customer_analytics/data/raw/online_retail_II.xlsx` |
| SHA-256 | `BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980` |
| 원본 행 수 | 1,067,371 |

원본 Excel은 Git에 없다. 다운로드 스크립트 또는 검증된 로컬 사본을 사용한다.

## Execution order

저장소의 `golden-data-lab` 폴더에서 실행한다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python cases/01_retail_customer_analytics/src/download_data.py
```

### 1–2. Business question and SQL extraction

1. [`README.md`](./README.md)의 의사결정과 분석 질문을 읽는다.
2. [`LOAD_GUIDE.md`](./LOAD_GUIDE.md)대로 데이터베이스, raw 테이블, 적재를 수행한다.
3. `sql/02_validate_raw_load.sql` 마지막에 `PASS`가 나와야 한다.
4. Power BI 또는 DBeaver 분석용 뷰가 필요하면 `sql/03_analysis_views.sql`을 실행한다.

Python만으로 3단계 이후를 재현할 수 있다. PostgreSQL은 source of truth 계약과 BI 연결용이다.

### 3–4. Data quality and EDA

```powershell
jupyter lab
```

`notebooks/`에서 순서대로 실행한다.

1. `01_data_quality_check.ipynb`
2. `02_python_eda.ipynb`

공통 준비 모듈 테스트:

```powershell
python -m unittest discover -s cases/01_retail_customer_analytics/tests -v
```

### 5–7. Statistics, KPI, dashboard

노트북을 직접 실행하거나 한 번에 계산한다.

```powershell
python cases/01_retail_customer_analytics/src/build_stats_notebook.py
python cases/01_retail_customer_analytics/src/build_kpi_notebook.py
python cases/01_retail_customer_analytics/src/build_dashboard_notebook.py
python cases/01_retail_customer_analytics/src/run_later_stages.py
python cases/01_retail_customer_analytics/src/build_powerbi_pbix.py
```

그다음 Jupyter에서 다음을 실행한다.

3. `03_statistical_analysis.ipynb`
4. `04_kpi_segmentation.ipynb`
5. `05_decision_dashboard.ipynb`

기대 산출물:

- `evidence/later_stages_summary.json`
- `evidence/stats_figures/01_customer_lorenz.png`
- `evidence/kpi_figures/01_rfm_segment_revenue.png`
- `evidence/kpi_figures/02_cohort_retention.png`
- `evidence/dashboard/01_one_page_decision.png`

노트북 셀이 원본 SHA-256과 행 수 계약을 `assert`로 확인한다. 실패하면 이후 숫자를 사용하지 않는다.

### 8–9. Insight and this document

- 해석과 실행 항목: [`INSIGHTS.md`](./INSIGHTS.md)
- Power BI 페이지 명세: [`powerbi/README.md`](./powerbi/README.md)
- 실행 기록: [`WORK_LOG.md`](./WORK_LOG.md)

## Metric contracts that must not drift

- 주문 키: `Source_Sheet + Invoice`
- 정상 매출: 수량·가격 양수, 취소·반품 아님. 고객 ID 결측은 매출에 포함
- 고객 분석: 정상 매출 중 고객 ID가 있는 행만
- 부분 월: 2009-12, 2011-12. 최고 월 비교에서 제외
- RFM 기준일: 식별 고객 마지막 거래시각 + 1일
- 중복 추가 행 34,335: 기본 분석에서 삭제하지 않음
- 음수 거래금액 비율은 매칭된 환불률이 아님

## Out of scope for reproduction

- Power BI `.pbix`: [`powerbi/CASE01_Retention_Priority.pbix`](./powerbi/CASE01_Retention_Priority.pbix). 재생성은 `src/build_powerbi_pbix.py`.
- 원본 날짜를 최신 연도로 바꾸는 작업. 하면 이 사례의 결과가 아니다.
