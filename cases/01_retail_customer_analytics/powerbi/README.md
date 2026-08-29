# CASE 01 Power BI 대시보드 명세

이 문서는 방법론 7단계 Visualization의 Power BI 제작 계약이다. Python 한 페이지 화면은 [`../evidence/dashboard/01_one_page_decision.png`](../evidence/dashboard/01_one_page_decision.png)와 [`../notebooks/05_decision_dashboard.ipynb`](../notebooks/05_decision_dashboard.ipynb)가 재현한다.

바이너리 보고서는 [`CASE01_Retention_Priority.pbix`](./CASE01_Retention_Priority.pbix)다. 집계 테이블만 넣었고 비밀번호는 없다. Power BI Desktop에서 바로 연다.

재생성:

```powershell
pip install pbix-mcp
python cases/01_retail_customer_analytics/src/build_powerbi_pbix.py
```

## Decision question

관측 기간의 실현 매출을 기준으로, 유지와 재활성화 노력을 어느 고객 세그먼트에 먼저 둘 것인가?

## Data source

`.pbix`는 Python 검증 파이프라인의 **대시보드 입자 집계**를 Import 스냅샷으로 담는다. 원본 106만 행과 PostgreSQL 접속 정보는 넣지 않는다.

| 테이블 | 내용 | 대사 |
| --- | --- | --- |
| `MonthlySales` | 월별 정상 매출 | Gross Sales = £20,972,595 |
| `Segments` | RFM 세그먼트 | 식별 매출 합계 |
| `Actions` | 유지·재활성화 등 실행 유형 | Segments 집계 |
| `Cohort` | 부분 월 제외, 0~6개월 유지율 | |
| `KPI` | 창 전체 비중 지표와 RFM 기준일 | |
| `Notes` | 해석 한계 | |

CSV 사본은 [`data/`](./data/)에 있다. Desktop에서 Refresh하면 빌드 PC의 CSV 절대 경로를 찾는다. 다른 PC에서는 데이터 원본을 이 폴더로 바꾸거나, 스냅샷만 사용한다.

PostgreSQL 뷰(`../sql/03_analysis_views.sql`)는 같은 정의를 Desktop에서 직접 연결할 때의 source of truth다. `.pbix` 카드 숫자는 Python KPI와 같아야 한다.

원본 Excel을 Power BI에 직접 연결하지 않는다.

## Relationships

| From | To | Cardinality |
| --- | --- | --- |
| `v_customer_analysis[invoice_key]` | 주문 차원으로 사용 | many invoices per customer |
| `v_monthly_sales[invoice_month]` | 월 슬라이서 | 1:many to sales month |

고객 세그먼트 테이블을 만들 경우 `customer_id`로 `v_customer_analysis`와 many-to-one로 연결한다.

## DAX measures

날짜는 데이터 최대일 + 1일을 RFM 기준일로 쓴다. 값을 최신 연도로 바꾸지 않는다.

```dax
Gross Sales =
SUM ( 'v_sales_analysis'[total_revenue] )

Completed Orders =
DISTINCTCOUNT ( 'v_sales_analysis'[invoice_key] )

AOV =
DIVIDE ( [Gross Sales], [Completed Orders] )

Identified Revenue =
CALCULATE (
    [Gross Sales],
    NOT ISBLANK ( 'v_sales_analysis'[customer_id] )
)

Identified Revenue Share =
DIVIDE ( [Identified Revenue], [Gross Sales] )

UK Revenue Share =
DIVIDE (
    CALCULATE ( [Gross Sales], 'v_sales_analysis'[country] = "United Kingdom" ),
    [Gross Sales]
)

Is Partial Month =
'v_monthly_sales'[invoice_month] IN { DATE ( 2009, 12, 1 ), DATE ( 2011, 12, 1 ) }
```

취소·반품 금액은 원거래 매칭 없이 raw의 음수 `quantity * price` 절댓값으로만 참고 카드에 둔다. 이름을 `Refund Rate`로 쓰지 않는다.

## Page layout (1 page)

페이지 이름: `Retention Priority`

| 위치 | 시각화 | 필드 | 주의 |
| --- | --- | --- | --- |
| 상단 카드 6개 | Card | Gross Sales, AOV, Repeat-customer rate, UK share, Identified share, RFM snapshot | 회계 매출/이익 카드 금지 |
| 좌상 | Line | 월별 Gross Sales | 부분 월은 점선 또는 주석 |
| 중상 | Bar | RFM 세그먼트별 Gross Sales, 범례=action | Champions/Loyal vs Cannot Lose/At Risk |
| 우상 | Table | 세그먼트, 고객 수, 매출 비중, 중앙 Recency | KPI 노트북과 동일 정렬 |
| 좌하 | Bar | 실행 유형(유지·재활성화 등)별 매출 | |
| 중하 | Matrix | 코호트 월 × 월차 유지율 | 부분 월 코호트 제외 |
| 우하 | Text box | 해석 한계: 2009-2011, 인과 없음, 현재 시장 일반화 금지 | |

슬라이서는 `invoice_month`만 허용한다. 국가 슬라이서를 넣을 경우 국가=국적이 아님을 제목에 적는다.

## Completion gate

- [`CASE01_Retention_Priority.pbix`](./CASE01_Retention_Priority.pbix)가 열리고 Gross Sales 카드가 Python KPI £20,972,595와 같다.
- 부분 월을 최고 월 비교에 쓰지 않는다. 월 차트에는 표시하고 `period_type`으로 구분한다.
- 비밀번호와 서버 주소는 `.pbix`에 저장하지 않는다.
