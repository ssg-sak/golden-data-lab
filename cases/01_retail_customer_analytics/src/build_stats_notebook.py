"""Build the reader-facing CASE 01 statistical analysis notebook."""

from pathlib import Path

import nbformat as nbf


CASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = CASE_DIR / "notebooks" / "03_statistical_analysis.ipynb"


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
# CASE 01 Statistical Analysis

## tl;dr

이 노트북은 EDA에서 관찰한 시기 차이, 매출 집중, 취소·반품 집중이 우연이나 소수 극단값만으로 설명되는지 점검합니다. 검정은 미리 정한 네 가지이며, 표본이 크면 p값이 작아지기 쉬우므로 효과 크기와 민감도를 함께 봅니다. 인과효과나 현재 시장 일반화는 하지 않습니다.
"""
    ),
    code(
        """
from pathlib import Path
import hashlib
import json
import sys

import pandas as pd
from IPython.display import Markdown, display

pd.set_option("display.max_columns", None)
pd.set_option("display.float_format", lambda value: f"{value:,.4f}")

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
from decision_dashboard import save_concentration_figure
from statistical_analysis import ALPHA, customer_revenue, run_statistical_analysis

raw_path = case_dir / "data" / "raw" / "online_retail_II.xlsx"
figure_dir = case_dir / "evidence" / "stats_figures"
figure_dir.mkdir(parents=True, exist_ok=True)
prepared = load_and_prepare_retail_data(raw_path)
stats = run_statistical_analysis(prepared)
source_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest().upper()

yoy = stats.yoy_test
display(Markdown(f'''
**실행 요약**

- 유의수준 α = **{ALPHA:.2f}**, 분석 단위와 효과 크기를 가설마다 명시합니다.
- 2010년 대비 2011년 완전 월 매출 Wilcoxon p = **{yoy["p_value"]:.4f}**, rank-biserial = **{yoy["rank_biserial"]:.2f}**.
- 고객 매출 Gini = **{stats.customer_concentration["gini"]["estimate"]:.2f}** (95% CI {stats.customer_concentration["gini"]["ci_low"]:.2f}–{stats.customer_concentration["gini"]["ci_high"]:.2f}).
- 상위 10% 고객 매출 비중 = **{stats.customer_concentration["top_10pct_share"]["estimate"]:.1%}**.
- 중복 제거·플래그 불일치 제외가 결론을 바꾸는지: 민감도 표에서 확인합니다.
'''))
"""
    ),
    md(
        """
## Context & Methods

### 사전 지정 가설

| ID | 질문 | 분석 단위 | 검정 | 효과 크기 |
| --- | --- | --- | --- | --- |
| H1 | 부분 월을 제외하면 2011년 월 매출이 2010년과 다른가? | 1–11월 쌍 | Wilcoxon signed-rank | rank-biserial |
| H2 | 달력 월에 따라 주문 금액 분포가 다른가? | 완전 월의 송장 | Kruskal-Wallis | epsilon-squared |
| H3 | 영국과 그 외 송장 금액 분포가 다른가? | 완전 월의 송장 | Mann-Whitney U | Cliff's delta |
| H4 | 송장 취소 여부가 영국/비영국과 연관되는가? | 송장 | 카이제곱 | Cramer's V |

### Key Assumptions

- 부분 월은 2009-12와 2011-12입니다.
- 고객·상품 집중도는 식별 고객 매출과 StockCode 매출입니다.
- 취소·반품 금액은 원거래와 매칭하지 않으므로 환불률이 아닙니다.
- 중복 후보 34,335행은 기본 분석에서 제거하지 않고 민감도에서만 제거합니다.
- 행 수가 많으면 통계적 유의성만으로 사업 임팩트를 주장하지 않습니다.
"""
    ),
    md("## Data\n\n### 1. Reconciliation"),
    code(
        """
assert source_sha256 == "BCBE73B35F5B7BABF197FB0CB983A11F5D9FF929078D4AA53D171B1F2DF2E980"
assert len(prepared.retail_df) == 1_067_371
assert len(prepared.sales_analysis_df) == 1_041_670
assert len(prepared.customer_analysis_df) == 805_549
print("PASS: source fingerprint and analysis populations reconcile.")
print(f"완전 월 수: {len(stats.complete_monthly):,}")
print(f"YoY 쌍 수: {len(stats.yoy_pairs):,}")
"""
    ),
    md("## Results\n\n### 2. Period differences"),
    code(
        """
peak_by_year = yoy["peak_by_year"]
display(stats.yoy_pairs.style.format({
    "revenue_2010": "£{:,.0f}",
    "revenue_2011": "£{:,.0f}",
    "diff_2011_minus_2010": "£{:,.0f}",
    "ratio_2011_over_2010": "{:.2f}",
}))
display(peak_by_year.style.format({"revenue": "£{:,.0f}"}))
print(
    f"Wilcoxon p={yoy['p_value']:.4f}, rank-biserial={yoy['rank_biserial']:.3f}, "
    f"median 2011/2010 ratio={yoy['median_ratio']:.2f}"
)
print(
    f"Kruskal-Wallis p={stats.month_kruskal['p_value']:.2e}, "
    f"epsilon-squared={stats.month_kruskal['epsilon_squared']:.3f}, n={stats.month_kruskal['n']:,}"
)
print(stats.month_kruskal["note"])
"""
    ),
    md("### 3. Concentration"),
    code(
        """
def concentration_row(label, bundle):
    return {
        "group": label,
        "n": bundle["n"],
        "gini": bundle["gini"]["estimate"],
        "gini_ci": f"{bundle['gini']['ci_low']:.2f}–{bundle['gini']['ci_high']:.2f}",
        "top_10pct_share": bundle["top_10pct_share"]["estimate"],
        "top_n_share": bundle["top_n_share"],
        "hhi": bundle["hhi"],
    }

concentration_table = pd.DataFrame([
    concentration_row("customers", stats.customer_concentration),
    concentration_row("customers without top 1%", stats.customer_concentration_without_top_1pct),
    concentration_row("stock codes", stats.product_concentration),
    concentration_row("stock codes without top 1%", stats.product_concentration_without_top_1pct),
])
display(concentration_table.style.format({
    "gini": "{:.3f}",
    "top_10pct_share": "{:.1%}",
    "top_n_share": "{:.1%}",
    "hhi": "{:.4f}",
}))
save_concentration_figure(
    customer_revenue(prepared.customer_analysis_df),
    figure_dir / "01_customer_lorenz.png",
)
print("Lorenz 곡선을 evidence/stats_figures/01_customer_lorenz.png에 저장했습니다.")
"""
    ),
    md("### 4. Cancellations and returns"),
    code(
        """
returns = stats.returns
return_table = pd.Series({
    "identified_customers": returns["identified_customers"],
    "customers_with_return_value": returns["customers_with_return_value"],
    "customer_return_gini_all": returns["customer_return_gini_all"],
    "customer_return_gini_returning": returns["customer_return_gini_returning"],
    "top_10pct_returning_customers_share": returns["top_10pct_returning_customers_share"],
    "top_10_stockcode_return_share": returns["top_10_stockcode_return_share"],
    "uk_cancel_rate": returns["uk_cancel_rate"],
    "non_uk_cancel_rate": returns["non_uk_cancel_rate"],
    "chi2_p_value": returns["invoice_cancel_p_value"],
    "cramers_v": returns["invoice_cancel_cramers_v"],
    "flag_mismatch_rows": returns["flag_mismatch_rows"],
})
display(return_table)
display(returns["invoice_cancel_crosstab"])
print("음수 거래금액은 원거래와 짝을 맞추지 않았으므로 환불률로 읽지 않습니다.")
"""
    ),
    md("### 5. Sensitivity"),
    code(
        """
sensitivity = stats.sensitivity.copy()
display(sensitivity.style.format({
    "rows_raw": "{:,.0f}",
    "rows_sales": "{:,.0f}",
    "gross_sales": "£{:,.0f}",
    "uk_share": "{:.1%}",
    "customer_gini": "{:.3f}",
    "top_10pct_customer_share": "{:.1%}",
    "top_10_stockcode_share": "{:.1%}",
    "repeat_customer_rate": "{:.1%}",
    "negative_to_gross": "{:.1%}",
}))
print(
    "material_change_vs_baseline: 상대 변화 5% 또는 비중 지표 1%p 초과. "
    "이 기준은 결론이 뒤집히는지를 보기 위한 실무 임계값입니다."
)
"""
    ),
    md("## Takeaways"),
    code(
        """
display(stats.hypothesis_summary.style.format({"p_value": "{:.4g}", "effect": "{:.3f}"}))
evidence_path = case_dir / "evidence" / "statistical_analysis_summary.json"
payload = {
    "alpha": ALPHA,
    "yoy_p_value": yoy["p_value"],
    "yoy_rank_biserial": yoy["rank_biserial"],
    "yoy_median_ratio": yoy["median_ratio"],
    "kruskal_p_value": stats.month_kruskal["p_value"],
    "kruskal_epsilon_squared": stats.month_kruskal["epsilon_squared"],
    "customer_gini": stats.customer_concentration["gini"]["estimate"],
    "top_10pct_customer_share": stats.customer_concentration["top_10pct_share"]["estimate"],
    "top_10_stockcode_share": stats.product_concentration["top_n_share"],
    "returning_customer_top_10pct_share": returns["top_10pct_returning_customers_share"],
    "cancel_cramers_v": returns["invoice_cancel_cramers_v"],
    "sensitivity_material_change": bool(
        stats.sensitivity.loc[
            stats.sensitivity["scenario"].ne("baseline"), "material_change_vs_baseline"
        ].any()
    ),
}
evidence_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Wrote {evidence_path}")
print("다음 단계: 이 효과 크기와 민감도 결과를 전제로 KPI와 RFM 세그먼트를 확정합니다.")
"""
    ),
    md(
        """
### Interpretation boundary

- p < 0.05는 관측 기간 안에서 차이가 우연만으로 보기 어렵다는 뜻이지, 개입 효과를 의미하지 않습니다.
- 고객·상품 집중도는 과거 매출 분포이며 미래 가치나 이익이 아닙니다.
- 결과는 2009-12-01~2011-12-09의 해외 온라인 소매 거래에만 해당합니다.
"""
    ),
]

nbf.validate(notebook)
NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, NOTEBOOK_PATH)
print(f"Wrote {NOTEBOOK_PATH}")
