"""Run CASE 01 statistical, KPI, and dashboard stages from the raw workbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from data_preparation import load_and_prepare_retail_data  # noqa: E402
from decision_dashboard import save_concentration_figure, save_decision_dashboard  # noqa: E402
from kpi_segmentation import run_kpi_segmentation  # noqa: E402
from statistical_analysis import customer_revenue, run_statistical_analysis  # noqa: E402


def _json_ready(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def main() -> int:
    raw_path = CASE_DIR / "data" / "raw" / "online_retail_II.xlsx"
    prepared = load_and_prepare_retail_data(raw_path)
    stats = run_statistical_analysis(prepared)
    kpis = run_kpi_segmentation(prepared)

    stats_dir = CASE_DIR / "evidence" / "stats_figures"
    kpi_dir = CASE_DIR / "evidence" / "kpi_figures"
    dashboard_dir = CASE_DIR / "evidence" / "dashboard"
    save_concentration_figure(
        customer_revenue(prepared.customer_analysis_df),
        stats_dir / "01_customer_lorenz.png",
    )
    save_decision_dashboard(stats, kpis, dashboard_dir / "01_one_page_decision.png")

    summary = {
        "snapshot_date": kpis.snapshot_date.isoformat(),
        "yoy_p_value": stats.yoy_test["p_value"],
        "yoy_rank_biserial": stats.yoy_test["rank_biserial"],
        "yoy_median_ratio": stats.yoy_test["median_ratio"],
        "kruskal_p_value": stats.month_kruskal["p_value"],
        "kruskal_epsilon_squared": stats.month_kruskal["epsilon_squared"],
        "uk_cliffs_delta": stats.uk_invoice_test["cliffs_delta"],
        "uk_cliffs_delta_label": stats.uk_invoice_test["cliffs_delta_label"],
        "customer_gini": stats.customer_concentration["gini"]["estimate"],
        "customer_gini_ci": [
            stats.customer_concentration["gini"]["ci_low"],
            stats.customer_concentration["gini"]["ci_high"],
        ],
        "top_10pct_customer_share": stats.customer_concentration["top_10pct_share"]["estimate"],
        "top_10_stockcode_share": stats.product_concentration["top_n_share"],
        "customer_gini_without_top_1pct": stats.customer_concentration_without_top_1pct["gini"]["estimate"],
        "returning_customer_top_10pct_share": stats.returns["top_10pct_returning_customers_share"],
        "cancel_cramers_v": stats.returns["invoice_cancel_cramers_v"],
        "uk_cancel_rate": stats.returns["uk_cancel_rate"],
        "non_uk_cancel_rate": stats.returns["non_uk_cancel_rate"],
        "sensitivity_material_change": bool(
            stats.sensitivity.loc[
                stats.sensitivity["scenario"].ne("baseline"),
                "material_change_vs_baseline",
            ].any()
        ),
        "kpis": {
            row.kpi: _json_ready(row.value)
            for row in kpis.values.itertuples(index=False)
        },
        "segments": json.loads(
            kpis.segment_summary.to_json(orient="records", date_format="iso")
        ),
        "priority": json.loads(kpis.priority.to_json(orient="records")),
        "hypothesis_summary": json.loads(
            stats.hypothesis_summary.to_json(orient="records")
        ),
        "sensitivity": json.loads(stats.sensitivity.to_json(orient="records")),
        "yoy_pairs": json.loads(stats.yoy_pairs.to_json(orient="records")),
        "peak_by_year": json.loads(
            stats.yoy_test["peak_by_year"].to_json(orient="records", date_format="iso")
        ),
        "cohort_month1_median": float(
            kpis.cohort_retention.loc[
                (~kpis.cohort_retention["is_partial_cohort"])
                & kpis.cohort_retention["period_number"].eq(1),
                "retention",
            ].median()
        ),
    }
    summary_path = CASE_DIR / "evidence" / "later_stages_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=_json_ready), encoding="utf-8")
    kpi_dir.mkdir(parents=True, exist_ok=True)
    print(json.dumps({k: summary[k] for k in summary if k not in {"segments", "priority", "hypothesis_summary", "sensitivity", "yoy_pairs"}}, indent=2, default=_json_ready))
    print(f"Wrote {summary_path}")
    print(f"Wrote {dashboard_dir / '01_one_page_decision.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
