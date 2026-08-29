"""Build the reader-facing CASE 01 decision dashboard notebook."""

from pathlib import Path

import nbformat as nbf


CASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = CASE_DIR / "notebooks" / "05_decision_dashboard.ipynb"


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
# CASE 01 Decision Dashboard

## tl;dr

이 노트북은 통계와 KPI 결과를 한 페이지로 압축합니다. Power BI Desktop용 데이터 모델·측정값 명세는 `powerbi/README.md`에 있습니다. 여기서 생성하는 PNG는 같은 의사결정 질문을 재현 가능한 정적 화면으로 남깁니다.
"""
    ),
    code(
        """
from pathlib import Path
import hashlib
import sys

import pandas as pd
from IPython.display import Image, Markdown, display

pd.set_option("display.max_columns", None)

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
from decision_dashboard import save_decision_dashboard
from kpi_segmentation import run_kpi_segmentation
from statistical_analysis import run_statistical_analysis

raw_path = case_dir / "data" / "raw" / "online_retail_II.xlsx"
figure_dir = case_dir / "evidence" / "dashboard"
figure_dir.mkdir(parents=True, exist_ok=True)
prepared = load_and_prepare_retail_data(raw_path)
stats = run_statistical_analysis(prepared)
kpis = run_kpi_segmentation(prepared)
source_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest().upper()
assert source_sha256 == "BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980"

dashboard_path = save_decision_dashboard(
    stats, kpis, figure_dir / "01_one_page_decision.png"
)
display(Markdown(f"**RFM 기준일:** {kpis.snapshot_date:%Y-%m-%d}"))
display(Image(filename=str(dashboard_path)))
"""
    ),
    md("## Decision table"),
    code(
        """
display(kpis.priority.style.format({
    "customers": "{:,.0f}",
    "revenue": "£{:,.0f}",
    "customer_share": "{:.1%}",
    "revenue_share": "{:.1%}",
    "median_recency": "{:.0f}",
}))
display(kpis.values)
print("Power BI 연결은 sql/03_analysis_views.sql와 powerbi/README.md를 사용합니다.")
"""
    ),
    md(
        """
### Interpretation boundary

- 이 화면은 관측 기간의 완료 매출과 RFM 라벨만 보여 줍니다.
- Power BI에서 최신 날짜로 바꾸거나 예측 시각을 추가하지 않습니다.
- 실행 제안의 문장 근거는 `INSIGHTS.md`로 이어집니다.
"""
    ),
]

nbf.validate(notebook)
NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, NOTEBOOK_PATH)
print(f"Wrote {NOTEBOOK_PATH}")
