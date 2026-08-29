"""Build the reader-facing CASE 01 KPI and RFM notebook."""

from pathlib import Path

import nbformat as nbf


CASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = CASE_DIR / "notebooks" / "04_kpi_segmentation.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


notebook = nbf.v4.new_notebook()
notebook["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3"},
}

notebook["cells"] = [
    md(
        """
# CASE 01 KPI & Segmentation

## tl;dr

이 노트북은 통계 단계에서 확인한 집중도와 시기 패턴을 전제로, 의사결정자가 반복해서 볼 KPI와 RFM 세그먼트를 확정합니다. 세그먼트는 유지·육성·재활성화·관찰·저우선 행동으로만 연결하며, 이익이나 캠페인 인과효과는 계산하지 않습니다.
"""
    ),
    code(
        """
from pathlib import Path
import hashlib
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from IPython.display import Markdown, display

pd.set_option("display.max_columns", None)
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")

CASE_NAME = "01_retail_customer_analytics"
case_dir_candidates = [
    Path.cwd(),
    Path.cwd().parent,
    Path.cwd() / "cases" / CASE_NAME,
]
case_dir = next(
    (path.resolve() for path in case_dir_candidates
     if (path / "data" / "raw" / "online_retail_II.xlsx").exists()),
    None,
)
if case_dir is None:
    raise FileNotFoundError(
        "online_retail_II.xlsx를 찾지 못했습니다. 저장소 루트 또는 notebooks 폴더에서 실행하세요."
    )

sys.path.insert(0, str(case_dir / "src"))
from data_preparation import load_and_prepare_retail_data
from kpi_segmentation import run_kpi_segmentation

raw_path = case_dir / "data" / "raw" / "online_retail_II.xlsx"
figure_dir = case_dir / "evidence" / "kpi_figures"
figure_dir.mkdir(parents=True, exist_ok=True)
prepared = load_and_prepare_retail_data(raw_path)
kpis = run_kpi_segmentation(prepared)
source_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest().upper()
value_lookup = kpis.values.set_index("kpi")["value"]

display(Markdown(f'''
**실행 요약**

- RFM 기준일: **{kpis.snapshot_date:%Y-%m-%d}** (마지막 거래일 + 1일)
- 정상 매출: **£{value_lookup["Gross sales"]:,.0f}**, AOV: **£{value_lookup["AOV"]:,.0f}**
- 식별 고객: **{int(value_lookup["Identified customers"]):,}명**, 재구매율: **{value_lookup["Repeat-customer rate"]:.1%}**
- 세그먼트는 최근성·빈도·금액 오분위 점수이며 고객 성격의 증명이 아닙니다.
'''))
"""
    ),
    md(
        """
## Context & Methods

### KPI 계약

각 지표는 분모, 분석 단위, 기간, 포함·제외 조건을 사전 정의합니다. 통계 단계의 민감도에서 중복 제거가 핵심 비중 지표를 뒤집지 않았다는 전제를 사용합니다.

### RFM 규칙

- Recency: 기준일 − 마지막 정상 구매일, 낮을수록 점수 5
- Frequency: `Invoice_Key` 고유 수, 높을수록 점수 5
- Monetary: 정상 매출 합계, 높을수록 점수 5
- 동점은 `rank(method='first')` 후 오분위로 끊어 빈 구간을 피합니다.
- 세그먼트 이름은 CRM 우선순위 라벨이며 군집분석 결과가 아닙니다.
"""
    ),
    md("## Data\n\n### 1. Reconciliation"),
    code(
        """
assert source_sha256 == "BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980"
assert len(kpis.rfm) == int(value_lookup["Identified customers"])
assert kpis.rfm["segment"].notna().all()
print("PASS: KPI inputs match the CASE 01 data contract.")
display(kpis.dictionary)
"""
    ),
    md("## Results\n\n### 2. Confirmed KPI values"),
    code(
        """
display(kpis.values)
"""
    ),
    md("### 3. RFM segments"),
    code(
        """
display(kpis.segment_summary.style.format({
    "customers": "{:,.0f}",
    "orders": "{:,.0f}",
    "revenue": "£{:,.0f}",
    "median_recency": "{:.0f}",
    "median_frequency": "{:.1f}",
    "median_monetary": "£{:,.0f}",
    "customer_share": "{:.1%}",
    "revenue_share": "{:.1%}",
}))
"""
    ),
    code(
        """
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid")
plot_frame = kpis.segment_summary.sort_values("revenue", ascending=False)
fig, ax = plt.subplots(figsize=(11, 5.5))
sns.barplot(data=plot_frame, x="segment", y="revenue", hue="action", dodge=False, ax=ax)
ax.set_title("RFM 세그먼트별 정상 매출", loc="left", fontsize=15, weight="bold")
ax.set_xlabel("")
ax.set_ylabel("매출 (£)")
ax.tick_params(axis="x", labelrotation=25)
ax.legend(title="실행 유형", frameon=False)
fig.tight_layout()
fig.savefig(figure_dir / "01_rfm_segment_revenue.png", dpi=160, bbox_inches="tight")
plt.show()
"""
    ),
    md("### 4. Cohort retention"),
    code(
        """
retention = kpis.cohort_retention
heatmap = (
    retention.loc[~retention["is_partial_cohort"] & retention["period_number"].between(0, 6)]
    .pivot(index="cohort_month", columns="period_number", values="retention")
)
display(heatmap.round(3).head(8))
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(heatmap, cmap="YlGnBu", vmin=0, vmax=1, ax=ax)
ax.set_title("코호트 유지율 (부분 월 코호트 제외, 0~6개월)", loc="left", weight="bold")
ax.set_xlabel("코호트 월차")
ax.set_ylabel("첫 구매 월")
fig.tight_layout()
fig.savefig(figure_dir / "02_cohort_retention.png", dpi=160, bbox_inches="tight")
plt.show()
"""
    ),
    md("### 5. CRM priority"),
    code(
        """
display(kpis.priority.style.format({
    "customers": "{:,.0f}",
    "revenue": "£{:,.0f}",
    "customer_share": "{:.1%}",
    "revenue_share": "{:.1%}",
    "median_recency": "{:.0f}",
}))
print("유지 세그먼트는 현재 기여, 재활성화 세그먼트는 최근성이 떨어진 과거 고가치 고객입니다.")
"""
    ),
    md(
        """
### Interpretation boundary

- RFM 점수는 관측 기간의 완료 매출만 사용합니다. 원가, 마진, 광고비가 없어 CLV가 아닙니다.
- 재구매와 유지는 창 안의 송장만 세므로 창 밖 활동은 알 수 없습니다.
- 세그먼트 크기가 달라도 같은 마케팅 처방을 가정하지 않습니다.
- 다음 단계는 이 표를 한 페이지 의사결정 화면으로 옮기는 것입니다.
"""
    ),
]

nbf.validate(notebook)
NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, NOTEBOOK_PATH)
print(f"Wrote {NOTEBOOK_PATH}")
