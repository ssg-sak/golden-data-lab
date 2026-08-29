"""KPI definitions and RFM / cohort segmentation for CASE 01."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from data_preparation import PreparedRetailData, add_invoice_key
from statistical_analysis import (
    PARTIAL_MONTHS,
    UK_LABEL,
    complete_months,
    monthly_sales_summary,
)


SNAPSHOT_OFFSET_DAYS = 1


@dataclass
class KPIResults:
    dictionary: pd.DataFrame
    values: pd.DataFrame
    rfm: pd.DataFrame
    segment_summary: pd.DataFrame
    cohort_retention: pd.DataFrame
    priority: pd.DataFrame
    snapshot_date: pd.Timestamp


KPI_ROWS = [
    {
        "kpi": "Gross sales",
        "formula": "SUM(Quantity × Price)",
        "grain": "sales line (sales_analysis_df)",
        "period": "2009-12-01 to 2011-12-09",
        "include": "Quantity > 0, Price > 0, not cancelled/returned",
        "exclude": "C-invoices, negative quantity, zero/negative price",
    },
    {
        "kpi": "Observed net transaction value",
        "formula": "SUM(Quantity × Price) over raw rows",
        "grain": "raw line (retail_df)",
        "period": "2009-12-01 to 2011-12-09",
        "include": "All raw rows",
        "exclude": "None; not accounting revenue",
    },
    {
        "kpi": "AOV",
        "formula": "Gross sales / COUNT DISTINCT Invoice_Key",
        "grain": "completed order",
        "period": "same as gross sales",
        "include": "sales_analysis_df orders",
        "exclude": "Line-item averages",
    },
    {
        "kpi": "Identified-customer revenue share",
        "formula": "Customer-analysis revenue / Gross sales",
        "grain": "sales line",
        "period": "same as gross sales",
        "include": "Normal positive sales with Customer ID",
        "exclude": "Guest checkout lines from the numerator",
    },
    {
        "kpi": "Repeat-customer rate",
        "formula": "Customers with ≥2 Invoice_Key / identified customers",
        "grain": "identified customer",
        "period": "observation window only",
        "include": "customer_analysis_df",
        "exclude": "Pre/post-window purchases; missing Customer ID",
    },
    {
        "kpi": "UK revenue share",
        "formula": "UK gross sales / Gross sales",
        "grain": "sales line country field",
        "period": "same as gross sales",
        "include": "Country = United Kingdom",
        "exclude": "Country is not nationality",
    },
    {
        "kpi": "Negative-value-to-gross ratio",
        "formula": "ABS(SUM of negative Quantity × Price) / Gross sales",
        "grain": "raw line",
        "period": "same as gross sales",
        "include": "Negative transaction amounts",
        "exclude": "Not a matched refund rate",
    },
]


def assign_rfm_segment(r_score: int, f_score: int, m_score: int) -> str:
    """Map quintile RFM scores to a mutually exclusive CRM segment."""

    if r_score >= 4 and f_score >= 4 and m_score >= 4:
        return "Champions"
    if r_score <= 2 and f_score >= 4 and m_score >= 4:
        return "Cannot Lose"
    if r_score <= 2 and f_score <= 2 and m_score >= 4:
        return "Hibernating High Value"
    if r_score <= 2 and f_score >= 3:
        return "At Risk"
    if r_score >= 4 and f_score <= 2:
        return "New / Recent"
    if r_score >= 3 and f_score >= 4:
        return "Loyal"
    if r_score >= 3 and m_score >= 4:
        return "Potential"
    if r_score >= 3:
        return "Need Attention"
    if m_score >= 4:
        return "Hibernating High Value"
    return "Hibernating"


def action_for_segment(segment: str) -> str:
    return {
        "Champions": "유지",
        "Loyal": "유지",
        "Potential": "육성",
        "New / Recent": "육성",
        "Need Attention": "관찰",
        "Cannot Lose": "재활성화",
        "At Risk": "재활성화",
        "Hibernating High Value": "재활성화",
        "Hibernating": "저우선",
    }[segment]


def quintile_score(series: pd.Series, *, reverse: bool = False) -> pd.Series:
    n = len(series)
    if n == 0:
        return pd.Series(dtype=int)
    bins = min(5, n)
    if bins == 1:
        return pd.Series(3, index=series.index, dtype=int)
    labels = list(range(bins, 0, -1)) if reverse else list(range(1, bins + 1))
    return pd.qcut(series.rank(method="first"), bins, labels=labels).astype(int)


def build_rfm(customer_df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    frame = add_invoice_key(customer_df)
    rfm = frame.groupby("Customer ID").agg(
        last_purchase=("InvoiceDate", "max"),
        first_purchase=("InvoiceDate", "min"),
        frequency=("Invoice_Key", "nunique"),
        monetary=("Total_Revenue", "sum"),
        country=("Country", "first"),
    )
    rfm["recency_days"] = (snapshot_date - rfm["last_purchase"]).dt.days
    rfm["R_score"] = quintile_score(rfm["recency_days"], reverse=True)
    rfm["F_score"] = quintile_score(rfm["frequency"])
    rfm["M_score"] = quintile_score(rfm["monetary"])
    rfm["RFM_score"] = (
        rfm["R_score"].astype(str)
        + rfm["F_score"].astype(str)
        + rfm["M_score"].astype(str)
    )
    rfm["segment"] = [
        assign_rfm_segment(r, f, m)
        for r, f, m in zip(rfm["R_score"], rfm["F_score"], rfm["M_score"])
    ]
    rfm["action"] = rfm["segment"].map(action_for_segment)
    return rfm.sort_values("monetary", ascending=False)


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    summary = (
        rfm.groupby(["segment", "action"], dropna=False)
        .agg(
            customers=("frequency", "size"),
            orders=("frequency", "sum"),
            revenue=("monetary", "sum"),
            median_recency=("recency_days", "median"),
            median_frequency=("frequency", "median"),
            median_monetary=("monetary", "median"),
        )
        .reset_index()
    )
    summary["customer_share"] = summary["customers"] / summary["customers"].sum()
    summary["revenue_share"] = summary["revenue"] / summary["revenue"].sum()
    action_order = {"유지": 0, "육성": 1, "재활성화": 2, "관찰": 3, "저우선": 4}
    summary["action_rank"] = summary["action"].map(action_order)
    return summary.sort_values(["action_rank", "revenue"], ascending=[True, False]).drop(
        columns=["action_rank"]
    )


def cohort_retention(customer_df: pd.DataFrame) -> pd.DataFrame:
    frame = add_invoice_key(customer_df)
    first = (
        frame.groupby("Customer ID")["InvoiceDate"].min().dt.to_period("M").dt.to_timestamp()
    )
    activity = (
        frame.assign(
            activity_month=frame["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby(["Customer ID", "activity_month"])
        .size()
        .reset_index(name="lines")
    )
    activity["cohort_month"] = activity["Customer ID"].map(first)
    activity["period_number"] = (
        (activity["activity_month"].dt.year - activity["cohort_month"].dt.year) * 12
        + (activity["activity_month"].dt.month - activity["cohort_month"].dt.month)
    )
    cohort_sizes = (
        activity.groupby("cohort_month")["Customer ID"].nunique().rename("cohort_size")
    )
    retained = (
        activity.groupby(["cohort_month", "period_number"])["Customer ID"]
        .nunique()
        .reset_index(name="active_customers")
    )
    retained = retained.merge(cohort_sizes, on="cohort_month")
    retained["retention"] = retained["active_customers"] / retained["cohort_size"]
    # Partial first/last months remain visible but should not be ranked as complete.
    retained["is_partial_cohort"] = retained["cohort_month"].isin(PARTIAL_MONTHS)
    return retained.sort_values(["cohort_month", "period_number"])


def priority_table(summary: pd.DataFrame) -> pd.DataFrame:
    focused = summary.loc[
        summary["action"].isin(["유지", "재활성화"])
    ].copy()
    focused["priority_note"] = np.where(
        focused["action"].eq("유지"),
        "현재 매출 기여가 큰 활성 고객. 서비스 유지 우선.",
        "과거 가치가 있으나 최근성이 낮음. 재활성화 후보.",
    )
    return focused[
        [
            "segment",
            "action",
            "customers",
            "revenue",
            "customer_share",
            "revenue_share",
            "median_recency",
            "priority_note",
        ]
    ]


def compute_kpi_values(prepared: PreparedRetailData) -> pd.DataFrame:
    sales = add_invoice_key(prepared.sales_analysis_df)
    customers = add_invoice_key(prepared.customer_analysis_df)
    gross = float(sales["Total_Revenue"].sum())
    orders = int(sales["Invoice_Key"].nunique())
    identified_revenue = float(customers["Total_Revenue"].sum())
    customer_orders = customers.groupby("Customer ID")["Invoice_Key"].nunique()
    uk_revenue = float(sales.loc[sales["Country"].eq(UK_LABEL), "Total_Revenue"].sum())
    net_value = float(prepared.retail_df["Total_Revenue"].sum())
    negative_value = float(
        -prepared.retail_df.loc[
            prepared.retail_df["Total_Revenue"].lt(0), "Total_Revenue"
        ].sum()
    )
    monthly = monthly_sales_summary(prepared.sales_analysis_df)
    peak = complete_months(monthly).sort_values("revenue", ascending=False).iloc[0]
    values = pd.DataFrame(
        [
            {"kpi": "Gross sales", "value": gross, "unit": "GBP"},
            {"kpi": "Observed net transaction value", "value": net_value, "unit": "GBP"},
            {"kpi": "Completed orders", "value": orders, "unit": "orders"},
            {"kpi": "AOV", "value": gross / orders, "unit": "GBP / order"},
            {
                "kpi": "Identified customers",
                "value": int(customer_orders.size),
                "unit": "customers",
            },
            {
                "kpi": "Identified-customer revenue share",
                "value": identified_revenue / gross,
                "unit": "share",
            },
            {
                "kpi": "Repeat-customer rate",
                "value": float(customer_orders.ge(2).mean()),
                "unit": "share",
            },
            {"kpi": "UK revenue share", "value": uk_revenue / gross, "unit": "share"},
            {
                "kpi": "Negative-value-to-gross ratio",
                "value": negative_value / gross,
                "unit": "ratio",
            },
            {
                "kpi": "Peak complete-month gross sales",
                "value": float(peak["revenue"]),
                "unit": f"GBP ({peak['Month']:%Y-%m})",
            },
        ]
    )
    return values


def run_kpi_segmentation(prepared: PreparedRetailData) -> KPIResults:
    snapshot = prepared.customer_analysis_df["InvoiceDate"].max() + pd.Timedelta(
        days=SNAPSHOT_OFFSET_DAYS
    )
    rfm = build_rfm(prepared.customer_analysis_df, snapshot)
    summary = segment_summary(rfm)
    return KPIResults(
        dictionary=pd.DataFrame(KPI_ROWS),
        values=compute_kpi_values(prepared),
        rfm=rfm,
        segment_summary=summary,
        cohort_retention=cohort_retention(prepared.customer_analysis_df),
        priority=priority_table(summary),
        snapshot_date=snapshot,
    )
