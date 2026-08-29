"""Build CASE 02 notebooks."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

CASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = CASE_DIR / "notebooks"


SETUP = """\
from pathlib import Path
import sys

CASE_NAME = "02_youth_migration_dynamics"
RAW_NAME = "2025_domestic_migration_statistics.xlsx"
candidates = [
    Path.cwd(),
    Path.cwd().parent,
    Path.cwd() / "cases" / CASE_NAME,
]
CASE_DIR = next(
    (path.resolve() for path in candidates if (path / "data" / "raw" / RAW_NAME).exists()),
    None,
)
if CASE_DIR is None:
    raise FileNotFoundError(
        f"{RAW_NAME}를 찾지 못했습니다. 저장소 루트 또는 notebooks 폴더에서 실행하세요."
    )
sys.path.insert(0, str(CASE_DIR / "src"))

from constants import RAW_FILE_NAME
from data_preparation import load_and_prepare
from data_quality import run_quality_checks
from kpi_segmentation import run_kpi_segmentation
from parse_official_tables import verify_source_file
from statistical_analysis import run_statistical_analysis

RAW = CASE_DIR / "data" / "raw" / RAW_FILE_NAME
source = verify_source_file(RAW)
prepared = load_and_prepare(RAW)
tables = prepared.tables
print(source["sha256"])
print("stale sheet present:", tables.workbook["has_stale_monthly_sheet"])
"""


def _write(name: str, cells: list) -> Path:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    nb = new_notebook(
        cells=cells,
        metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}},
    )
    path = NOTEBOOK_DIR / name
    path.write_text(nbformat.writes(nb), encoding="utf-8")
    return path


def build() -> list[Path]:
    quality = [
        new_markdown_cell(
            "# CASE 02 Data Quality Check\n\n원본 엑셀은 수정하지 않는다. 공식 부표의 교차 대사만 수행한다."
        ),
        new_code_cell(SETUP),
        new_code_cell("quality = run_quality_checks(tables, prepared)\nquality"),
        new_code_cell("assert quality['passed'].all(), quality.loc[~quality['passed']]"),
        new_markdown_cell(
            "## 잠긴 해석\n\n"
            "- 청년 = 20-24 + 25-29 + 30-34 + 35-39세. e-지방지표 19-39와 직접 대사하지 않는다.\n"
            "- OD 행렬은 행=전입지, 열=전출지다. 서울 행의 전국-대각 = 시도간 전입과 일치한다.\n"
            "- `8.월별` 시트는 2009-2011 잔여 표로 보이며 분석에서 제외한다."
        ),
    ]
    eda = [
        new_markdown_cell(
            "# CASE 02 Python EDA\n\n2025 청년 순이동과 전 연령 시도 간 경로를 탐색한다. 원인은 단정하지 않는다."
        ),
        new_code_cell(SETUP),
        new_code_cell(
            "prepared.youth_profile[['sido','net_total','net_youth_20_39','net_20s','net_30s','typology_ko']]"
        ),
        new_code_cell("prepared.youth_mobility.tail()"),
        new_code_cell("prepared.capital_flows"),
        new_code_cell(
            "inter = prepared.inter_sido.sort_values('movers', ascending=False).head(10)\n"
            "inter[['origin','destination','movers','flow_block']]"
        ),
        new_markdown_cell(
            "서울은 20대 순유입·30대 순유출이 동시에 나타난다. 경기·인천은 20대와 30대가 모두 순유입이다. "
            "시도 간 상위 경로는 수도권 내부이며, 이 OD는 전 연령이다."
        ),
    ]
    stats = [
        new_markdown_cell(
            "# CASE 02 Statistical Analysis\n\n가설은 EDA 핸드오프에서 미리 정한다. p값과 효과 크기를 함께 본다."
        ),
        new_code_cell(
            SETUP + "\nstats = run_statistical_analysis(tables, prepared)\nstats.hypothesis_summary"
        ),
        new_code_cell("stats.h1"),
        new_code_cell("stats.h3"),
        new_code_cell("stats.concentration"),
        new_code_cell("stats.sensitivity.loc[stats.sensitivity['sign_flips']]"),
    ]
    kpi = [
        new_markdown_cell(
            "# CASE 02 KPI & Segmentation\n\n유형은 2025년 20대·30대 순이동 부호로만 나눈다."
        ),
        new_code_cell(
            SETUP + "\nkpis = run_kpi_segmentation(tables, prepared)\nkpis.values"
        ),
        new_code_cell("kpis.typology_summary"),
        new_code_cell("kpis.priority"),
        new_code_cell("kpis.dictionary"),
    ]
    dash = [
        new_markdown_cell(
            "# CASE 02 Decision Dashboard\n\n"
            "한 페이지 PNG는 같은 의사결정 질문의 정적 재현이다. "
            "산출물은 `evidence/dashboard/01_one_page_decision.png`다. "
            "시도 단계색지도는 `evidence/figures/01_youth_net_2025.png`다."
        ),
        new_code_cell(
            SETUP
            + """
from IPython.display import Image, display
from decision_dashboard import save_decision_dashboard
from kpi_segmentation import run_kpi_segmentation
from statistical_analysis import run_statistical_analysis

stats = run_statistical_analysis(tables, prepared)
kpis = run_kpi_segmentation(tables, prepared)
path = CASE_DIR / "evidence" / "dashboard" / "01_one_page_decision.png"
save_decision_dashboard(tables, prepared, stats, kpis, path)
display(Image(filename=str(path)))
print(path)
"""
        ),
        new_code_cell("kpis.priority"),
        new_markdown_cell(
            "시도 간 상위 경로는 전 연령이다. 청년 순이동 막대와 같은 화면에 두더라도 연령을 섞어 읽지 않는다. "
            "해석은 `INSIGHTS.md`다."
        ),
    ]
    return [
        _write("01_data_quality_check.ipynb", quality),
        _write("02_python_eda.ipynb", eda),
        _write("03_statistical_analysis.ipynb", stats),
        _write("04_kpi_segmentation.ipynb", kpi),
        _write("05_decision_dashboard.ipynb", dash),
    ]


if __name__ == "__main__":
    for path in build():
        print(path)
