"""Build the CASE 01 Power BI .pbix from verified Python aggregates."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from data_preparation import load_and_prepare_retail_data  # noqa: E402
from kpi_segmentation import run_kpi_segmentation  # noqa: E402
from statistical_analysis import complete_months, monthly_sales_summary  # noqa: E402


POWERBI_DIR = CASE_DIR / "powerbi"
DATA_DIR = POWERBI_DIR / "data"
PBIX_PATH = POWERBI_DIR / "CASE01_Retention_Priority.pbix"


def _records(frame: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for raw in frame.to_dict(orient="records"):
        row: dict = {}
        for key, value in raw.items():
            if pd.isna(value):
                continue
            if isinstance(value, pd.Timestamp):
                row[key] = value.to_pydatetime()
            elif isinstance(value, datetime):
                row[key] = value
            elif hasattr(value, "item"):
                row[key] = value.item()
            else:
                row[key] = value
        rows.append(row)
    return rows


def _write_csv(frame: pd.DataFrame, name: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / name
    export = frame.copy()
    for column in export.columns:
        if pd.api.types.is_datetime64_any_dtype(export[column]):
            export[column] = pd.to_datetime(export[column]).dt.strftime("%Y-%m-%d")
    export.to_csv(path, index=False)
    print(f"Wrote {path}")


def main() -> int:
    from pbix_mcp.builder import PBIXBuilder

    raw_path = CASE_DIR / "data" / "raw" / "online_retail_II.xlsx"
    prepared = load_and_prepare_retail_data(raw_path)
    kpis = run_kpi_segmentation(prepared)
    monthly = monthly_sales_summary(prepared.sales_analysis_df)
    value_lookup = kpis.values.set_index("kpi")["value"]

    monthly_table = monthly.rename(
        columns={
            "Month": "Month",
            "revenue": "revenue",
            "orders": "orders",
            "average_order_value": "average_order_value",
        }
    )[
        [
            "Month",
            "year",
            "calendar_month",
            "is_partial_month",
            "revenue",
            "orders",
            "average_order_value",
        ]
    ]
    monthly_table["period_type"] = monthly_table["is_partial_month"].map(
        {True: "partial", False: "complete"}
    )
    monthly_table = monthly_table.drop(columns=["is_partial_month"])

    segments = kpis.segment_summary.copy()
    actions = (
        segments.groupby("action", as_index=False)
        .agg(customers=("customers", "sum"), revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
    )
    cohort = kpis.cohort_retention.loc[
        ~kpis.cohort_retention["is_partial_cohort"]
        & kpis.cohort_retention["period_number"].between(0, 6),
        ["cohort_month", "period_number", "cohort_size", "active_customers", "retention"],
    ].copy()

    kpi_row = pd.DataFrame(
        [
            {
                "kpi_set": "CASE01",
                "gross_sales": float(value_lookup["Gross sales"]),
                "aov": float(value_lookup["AOV"]),
                "repeat_customer_rate": float(value_lookup["Repeat-customer rate"]),
                "uk_share": float(value_lookup["UK revenue share"]),
                "identified_share": float(
                    value_lookup["Identified-customer revenue share"]
                ),
                "negative_to_gross": float(
                    value_lookup["Negative-value-to-gross ratio"]
                ),
                "snapshot_date": kpis.snapshot_date.to_pydatetime(),
            }
        ]
    )
    notes = pd.DataFrame(
        {
            "line": [1, 2, 3, 4, 5],
            "note": [
                "2009-12-01 ~ 2011-12-09 관측 기간 내부 패턴이다.",
                "YoY 완전 월 매출 차이는 유의하지 않다 (p=0.52).",
                "Champions+Loyal이 식별 매출의 약 79%다.",
                "취소 금액은 원거래와 짝을 맞춘 환불률이 아니다.",
                "현재 소매시장으로 일반화하지 않는다.",
            ],
        }
    )

    _write_csv(monthly_table, "monthly_sales.csv")
    _write_csv(segments, "rfm_segments.csv")
    _write_csv(actions, "actions.csv")
    _write_csv(cohort, "cohort_retention.csv")
    _write_csv(kpi_row, "kpi.csv")
    _write_csv(notes, "notes.csv")

    builder = PBIXBuilder("CASE 01 Retention Priority")
    builder.add_table(
        "MonthlySales",
        [
            {"name": "Month", "data_type": "DateTime"},
            {"name": "year", "data_type": "Int64"},
            {"name": "calendar_month", "data_type": "Int64"},
            {"name": "period_type", "data_type": "String"},
            {"name": "revenue", "data_type": "Double"},
            {"name": "orders", "data_type": "Int64"},
            {"name": "average_order_value", "data_type": "Double"},
        ],
        rows=_records(monthly_table),
        source_csv=str((DATA_DIR / "monthly_sales.csv").resolve()),
    )
    builder.add_table(
        "Segments",
        [
            {"name": "segment", "data_type": "String"},
            {"name": "action", "data_type": "String"},
            {"name": "customers", "data_type": "Int64"},
            {"name": "orders", "data_type": "Int64"},
            {"name": "revenue", "data_type": "Double"},
            {"name": "median_recency", "data_type": "Double"},
            {"name": "median_frequency", "data_type": "Double"},
            {"name": "median_monetary", "data_type": "Double"},
            {"name": "customer_share", "data_type": "Double"},
            {"name": "revenue_share", "data_type": "Double"},
        ],
        rows=_records(segments),
        source_csv=str((DATA_DIR / "rfm_segments.csv").resolve()),
    )
    builder.add_table(
        "Actions",
        [
            {"name": "action", "data_type": "String"},
            {"name": "customers", "data_type": "Int64"},
            {"name": "revenue", "data_type": "Double"},
        ],
        rows=_records(actions),
        source_csv=str((DATA_DIR / "actions.csv").resolve()),
    )
    builder.add_table(
        "Cohort",
        [
            {"name": "cohort_month", "data_type": "DateTime"},
            {"name": "period_number", "data_type": "Int64"},
            {"name": "cohort_size", "data_type": "Int64"},
            {"name": "active_customers", "data_type": "Int64"},
            {"name": "retention", "data_type": "Double"},
        ],
        rows=_records(cohort),
        source_csv=str((DATA_DIR / "cohort_retention.csv").resolve()),
    )
    builder.add_table(
        "KPI",
        [
            {"name": "kpi_set", "data_type": "String"},
            {"name": "gross_sales", "data_type": "Double"},
            {"name": "aov", "data_type": "Double"},
            {"name": "repeat_customer_rate", "data_type": "Double"},
            {"name": "uk_share", "data_type": "Double"},
            {"name": "identified_share", "data_type": "Double"},
            {"name": "negative_to_gross", "data_type": "Double"},
            {"name": "snapshot_date", "data_type": "DateTime"},
        ],
        rows=_records(kpi_row),
        source_csv=str((DATA_DIR / "kpi.csv").resolve()),
    )
    builder.add_table(
        "Notes",
        [
            {"name": "line", "data_type": "Int64"},
            {"name": "note", "data_type": "String"},
        ],
        rows=_records(notes),
        source_csv=str((DATA_DIR / "notes.csv").resolve()),
    )
    builder.add_relationship("Segments", "action", "Actions", "action")

    builder.add_measure(
        "MonthlySales",
        "Gross Sales",
        "SUM(MonthlySales[revenue])",
        format_string="#,0",
    )
    builder.add_measure(
        "MonthlySales",
        "Completed Orders",
        "SUM(MonthlySales[orders])",
        format_string="#,0",
    )
    builder.add_measure(
        "MonthlySales",
        "Average Order Value",
        "DIVIDE([Gross Sales], [Completed Orders])",
        format_string="#,0",
    )
    builder.add_measure(
        "KPI",
        "Repeat Customer Rate",
        "MAX(KPI[repeat_customer_rate])",
        format_string="0.0%",
    )
    builder.add_measure(
        "KPI",
        "UK Revenue Share",
        "MAX(KPI[uk_share])",
        format_string="0.0%",
    )
    builder.add_measure(
        "KPI",
        "Identified Revenue Share",
        "MAX(KPI[identified_share])",
        format_string="0.0%",
    )
    builder.add_measure(
        "KPI",
        "RFM Snapshot",
        "MAX(KPI[snapshot_date])",
        data_type="DateTime",
        format_string="yyyy-mm-dd",
    )
    builder.add_measure(
        "Segments",
        "Segment Revenue",
        "SUM(Segments[revenue])",
        format_string="#,0",
    )
    builder.add_measure(
        "Segments",
        "Segment Customers",
        "SUM(Segments[customers])",
        format_string="#,0",
    )
    builder.add_measure(
        "Actions",
        "Action Revenue",
        "SUM(Actions[revenue])",
        format_string="#,0",
    )
    builder.add_measure(
        "Cohort",
        "Cohort Retention",
        "AVERAGE(Cohort[retention])",
        format_string="0.0%",
    )

    builder.add_page(
        "Retention Priority",
        [
            {
                "name": "gross_card",
                "type": "card",
                "x": 16,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Gross Sales"},
            },
            {
                "name": "aov_card",
                "type": "card",
                "x": 224,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Average Order Value"},
            },
            {
                "name": "repeat_card",
                "type": "card",
                "x": 432,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Repeat Customer Rate"},
            },
            {
                "name": "uk_card",
                "type": "card",
                "x": 640,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "UK Revenue Share"},
            },
            {
                "name": "identified_card",
                "type": "card",
                "x": 848,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Identified Revenue Share"},
            },
            {
                "name": "snapshot_card",
                "type": "card",
                "x": 1056,
                "y": 8,
                "width": 208,
                "height": 88,
                "config": {"measure": "RFM Snapshot"},
            },
            {
                "name": "month_slicer",
                "type": "slicer",
                "x": 16,
                "y": 104,
                "width": 200,
                "height": 36,
                "config": {"column": {"table": "MonthlySales", "column": "Month"}},
            },
            {
                "name": "monthly_line",
                "type": "lineChart",
                "x": 16,
                "y": 148,
                "width": 416,
                "height": 268,
                "config": {
                    "category": {"table": "MonthlySales", "column": "Month"},
                    "measure": "Gross Sales",
                    "sort": {"by": "Month", "direction": "asc"},
                },
            },
            {
                "name": "segment_bar",
                "type": "clusteredBarChart",
                "x": 440,
                "y": 148,
                "width": 416,
                "height": 268,
                "config": {
                    "category": {"table": "Segments", "column": "segment"},
                    "measure": "Segment Revenue",
                },
            },
            {
                "name": "segment_table",
                "type": "tableEx",
                "x": 864,
                "y": 104,
                "width": 400,
                "height": 312,
                "config": {
                    "columns": [
                        {"table": "Segments", "column": "segment"},
                        {"table": "Segments", "column": "action"},
                        {"measure": "Segment Customers"},
                        {"measure": "Segment Revenue"},
                        {"table": "Segments", "column": "median_recency"},
                        {"table": "Segments", "column": "revenue_share"},
                    ]
                },
            },
            {
                "name": "action_col",
                "type": "clusteredColumnChart",
                "x": 16,
                "y": 428,
                "width": 400,
                "height": 276,
                "config": {
                    "category": {"table": "Actions", "column": "action"},
                    "measure": "Action Revenue",
                },
            },
            {
                "name": "cohort_matrix",
                "type": "matrix",
                "x": 424,
                "y": 428,
                "width": 432,
                "height": 276,
                "config": {
                    "columns": [
                        {"table": "Cohort", "column": "cohort_month"},
                        {"table": "Cohort", "column": "period_number"},
                        {"measure": "Cohort Retention"},
                    ]
                },
            },
            {
                "name": "notes_table",
                "type": "tableEx",
                "x": 864,
                "y": 428,
                "width": 400,
                "height": 276,
                "config": {
                    "columns": [
                        {"table": "Notes", "column": "line"},
                        {"table": "Notes", "column": "note"},
                    ]
                },
            },
        ],
    )

    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    builder.save(str(PBIX_PATH))
    print(f"Wrote {PBIX_PATH} ({PBIX_PATH.stat().st_size:,} bytes)")
    print(f"Peak complete month revenue GBP {complete_months(monthly)['revenue'].max():,.0f}")
    print(f"Gross sales GBP {value_lookup['Gross sales']:,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
