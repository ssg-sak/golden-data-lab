"""Statistical checks for CASE 01 EDA findings.

Tests are pre-specified from the EDA handoff. Large samples make p-values
easy to reject, so every test reports an effect size and an interpretation
boundary. Results describe 2009-12-01 to 2011-12-09 only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, kruskal, mannwhitneyu, rankdata, wilcoxon

from data_preparation import (
    PreparedRetailData,
    add_invoice_key,
    apply_purpose_splits,
    drop_exact_duplicate_extras,
    flag_mismatch_mask,
)


PARTIAL_MONTHS = (
    pd.Timestamp("2009-12-01"),
    pd.Timestamp("2011-12-01"),
)
ALPHA = 0.05
UK_LABEL = "United Kingdom"
CLIFF_THRESHOLDS = (
    (0.147, "negligible"),
    (0.33, "small"),
    (0.474, "medium"),
)
MATERIAL_RELATIVE_CHANGE = 0.05
MATERIAL_SHARE_POINTS = 0.01
RNG_SEED = 42


@dataclass
class StatisticalResults:
    monthly: pd.DataFrame
    complete_monthly: pd.DataFrame
    yoy_pairs: pd.DataFrame
    yoy_test: dict[str, Any]
    month_kruskal: dict[str, Any]
    uk_invoice_test: dict[str, Any]
    customer_concentration: dict[str, Any]
    customer_concentration_without_top_1pct: dict[str, Any]
    product_concentration: dict[str, Any]
    product_concentration_without_top_1pct: dict[str, Any]
    returns: dict[str, Any]
    sensitivity: pd.DataFrame
    hypothesis_summary: pd.DataFrame


def gini_coefficient(values: np.ndarray | pd.Series) -> float:
    """Gini of non-negative values. 0 is equality; 1 is complete concentration."""

    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return float("nan")
    if np.any(array < -1e-12):
        raise ValueError("Gini is defined here only for non-negative values.")
    array = np.sort(np.clip(array, 0, None))
    total = array.sum()
    if total == 0:
        return 0.0
    n = array.size
    index = np.arange(1, n + 1, dtype=float)
    return float((2.0 * np.sum(index * array) / (n * total)) - (n + 1) / n)


def share_top_fraction(values: np.ndarray | pd.Series, fraction: float) -> float:
    array = np.sort(np.asarray(values, dtype=float))
    total = array.sum()
    if array.size == 0 or total == 0:
        return float("nan")
    n_top = max(1, int(np.ceil(array.size * fraction)))
    return float(array[-n_top:].sum() / total)


def share_top_n(values: np.ndarray | pd.Series, n: int) -> float:
    array = np.sort(np.asarray(values, dtype=float))
    total = array.sum()
    if array.size == 0 or total == 0:
        return float("nan")
    n_top = min(n, array.size)
    return float(array[-n_top:].sum() / total)


def herfindahl_index(values: np.ndarray | pd.Series) -> float:
    array = np.asarray(values, dtype=float)
    total = array.sum()
    if array.size == 0 or total == 0:
        return float("nan")
    shares = array / total
    return float(np.sum(shares * shares))


def interpret_cliff_delta(delta: float) -> str:
    magnitude = abs(delta)
    label = "large"
    for threshold, name in CLIFF_THRESHOLDS:
        if magnitude < threshold:
            label = name
            break
    return label


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Positive values mean y tends to be larger than x."""

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    result = mannwhitneyu(y, x, alternative="two-sided")
    return float((2.0 * result.statistic) / (x.size * y.size) - 1.0)


def bootstrap_stat(
    values: np.ndarray,
    stat_func,
    *,
    n_boot: int = 1000,
    seed: int = RNG_SEED,
    alpha: float = ALPHA,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    array = np.asarray(values, dtype=float)
    point = float(stat_func(array))
    samples = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        draw = rng.choice(array, size=array.size, replace=True)
        samples[i] = stat_func(draw)
    lower = float(np.quantile(samples, alpha / 2))
    upper = float(np.quantile(samples, 1 - alpha / 2))
    return {"estimate": point, "ci_low": lower, "ci_high": upper, "n_boot": n_boot}


def paired_wilcoxon(before: np.ndarray, after: np.ndarray) -> dict[str, Any]:
    before = np.asarray(before, dtype=float)
    after = np.asarray(after, dtype=float)
    if before.size != after.size:
        raise ValueError("Paired samples must have the same length.")
    diff = after - before
    nonzero = diff != 0
    used = diff[nonzero]
    n = int(used.size)
    if n == 0:
        return {
            "n_pairs": int(before.size),
            "n_nonzero": 0,
            "w_statistic": float("nan"),
            "p_value": 1.0,
            "rank_biserial": 0.0,
            "median_diff": 0.0,
            "significant": False,
        }
    ranks = rankdata(np.abs(used))
    r_plus = float(ranks[used > 0].sum())
    r_minus = float(ranks[used < 0].sum())
    test = wilcoxon(used, alternative="two-sided", zero_method="wilcox")
    rank_biserial = (r_plus - r_minus) / (r_plus + r_minus)
    return {
        "n_pairs": int(before.size),
        "n_nonzero": n,
        "w_statistic": float(test.statistic),
        "p_value": float(test.pvalue),
        "rank_biserial": float(rank_biserial),
        "median_diff": float(np.median(diff)),
        "significant": bool(test.pvalue < ALPHA),
    }


def kruskal_epsilon_squared(groups: list[np.ndarray]) -> dict[str, Any]:
    cleaned = [np.asarray(group, dtype=float) for group in groups if len(group) > 0]
    if len(cleaned) < 2:
        raise ValueError("Kruskal-Wallis needs at least two groups.")
    test = kruskal(*cleaned)
    n = int(sum(group.size for group in cleaned))
    k = len(cleaned)
    epsilon = (float(test.statistic) - k + 1) / (n - k)
    return {
        "h_statistic": float(test.statistic),
        "p_value": float(test.pvalue),
        "n": n,
        "k": k,
        "epsilon_squared": float(epsilon),
        "significant": bool(test.pvalue < ALPHA),
    }


def mannwhitney_with_effect(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    test = mannwhitneyu(y, x, alternative="two-sided")
    delta = cliffs_delta(x, y)
    return {
        "u_statistic": float(test.statistic),
        "p_value": float(test.pvalue),
        "n_x": int(x.size),
        "n_y": int(y.size),
        "median_x": float(np.median(x)),
        "median_y": float(np.median(y)),
        "cliffs_delta": float(delta),
        "cliffs_delta_label": interpret_cliff_delta(delta),
        "significant": bool(test.pvalue < ALPHA),
    }


def cramers_v(table: np.ndarray) -> float:
    chi2, _, _, _ = chi2_contingency(table)
    n = table.sum()
    r, c = table.shape
    return float(np.sqrt(chi2 / (n * min(r - 1, c - 1))))


def monthly_sales_summary(sales_df: pd.DataFrame) -> pd.DataFrame:
    frame = add_invoice_key(sales_df)
    monthly = (
        frame.assign(Month=frame["InvoiceDate"].dt.to_period("M").dt.to_timestamp())
        .groupby("Month")
        .agg(
            revenue=("Total_Revenue", "sum"),
            orders=("Invoice_Key", "nunique"),
            units=("Quantity", "sum"),
        )
        .reset_index()
    )
    monthly["is_partial_month"] = monthly["Month"].isin(PARTIAL_MONTHS)
    monthly["average_order_value"] = monthly["revenue"] / monthly["orders"]
    monthly["calendar_month"] = monthly["Month"].dt.month
    monthly["year"] = monthly["Month"].dt.year
    return monthly


def complete_months(monthly: pd.DataFrame) -> pd.DataFrame:
    return monthly.loc[~monthly["is_partial_month"]].copy()


def invoice_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    frame = add_invoice_key(sales_df)
    invoices = (
        frame.groupby("Invoice_Key", as_index=False)
        .agg(
            revenue=("Total_Revenue", "sum"),
            invoice_date=("InvoiceDate", "min"),
            country=("Country", "first"),
        )
    )
    invoices["Month"] = invoices["invoice_date"].dt.to_period("M").dt.to_timestamp()
    invoices["calendar_month"] = invoices["invoice_date"].dt.month
    invoices["is_uk"] = invoices["country"].eq(UK_LABEL)
    invoices["is_partial_month"] = invoices["Month"].isin(PARTIAL_MONTHS)
    return invoices


def customer_revenue(customer_df: pd.DataFrame) -> pd.Series:
    return customer_df.groupby("Customer ID")["Total_Revenue"].sum()


def product_revenue(sales_df: pd.DataFrame) -> pd.Series:
    return sales_df.groupby("StockCode")["Total_Revenue"].sum()


def concentration_bundle(values: pd.Series, *, top_n: int = 10) -> dict[str, Any]:
    array = values.to_numpy(dtype=float)
    gini_ci = bootstrap_stat(array, gini_coefficient)
    top_frac_ci = bootstrap_stat(array, lambda data: share_top_fraction(data, 0.10))
    return {
        "n": int(values.size),
        "total": float(values.sum()),
        "gini": gini_ci,
        "top_10pct_share": top_frac_ci,
        "top_n_share": float(share_top_n(array, top_n)),
        "top_n": top_n,
        "hhi": float(herfindahl_index(array)),
    }


def drop_top_fraction(values: pd.Series, fraction: float = 0.01) -> pd.Series:
    if values.empty:
        return values
    n_drop = max(1, int(np.floor(values.size * fraction)))
    cutoff = values.nlargest(n_drop).min()
    kept = values.loc[values < cutoff]
    # If many ties sit on the cutoff, drop exactly n_drop largest.
    if values.size - len(kept) != n_drop:
        return values.sort_values(ascending=False).iloc[n_drop:]
    return kept


def year_over_year_pairs(complete_monthly: pd.DataFrame) -> pd.DataFrame:
    frame = complete_monthly.copy()
    y2010 = (
        frame.loc[frame["year"].eq(2010), ["calendar_month", "revenue"]]
        .set_index("calendar_month")
        .rename(columns={"revenue": "revenue_2010"})
    )
    y2011 = (
        frame.loc[frame["year"].eq(2011), ["calendar_month", "revenue"]]
        .set_index("calendar_month")
        .rename(columns={"revenue": "revenue_2011"})
    )
    paired = y2010.join(y2011, how="inner")
    paired["diff_2011_minus_2010"] = paired["revenue_2011"] - paired["revenue_2010"]
    paired["ratio_2011_over_2010"] = paired["revenue_2011"] / paired["revenue_2010"]
    return paired.reset_index()


def peak_complete_month_by_year(complete_monthly: pd.DataFrame) -> pd.DataFrame:
    idx = complete_monthly.groupby("year")["revenue"].idxmax()
    return complete_monthly.loc[idx, ["year", "Month", "calendar_month", "revenue"]].reset_index(
        drop=True
    )


def returns_analysis(
    prepared: PreparedRetailData,
) -> dict[str, Any]:
    retail = add_invoice_key(prepared.retail_df)
    identified = retail.loc[retail["Customer ID"].notna()].copy()
    identified["return_value"] = np.where(
        identified["Total_Revenue"].lt(0),
        -identified["Total_Revenue"],
        0.0,
    )
    identified["sales_value"] = np.where(
        identified["Total_Revenue"].gt(0)
        & ~identified["Is_Cancelled_or_Returned"],
        identified["Total_Revenue"],
        0.0,
    )
    customer = identified.groupby("Customer ID").agg(
        return_value=("return_value", "sum"),
        sales_value=("sales_value", "sum"),
        return_rows=("return_value", lambda s: int((s > 0).sum())),
    )
    returning = customer.loc[customer["return_value"].gt(0), "return_value"]
    stock = identified.groupby("StockCode")["return_value"].sum()
    returning_stock = stock.loc[stock.gt(0)]

    invoices = (
        retail.groupby("Invoice_Key", as_index=False)
        .agg(
            is_cancelled=("Is_Cancelled_Invoice", "max"),
            country=("Country", "first"),
        )
    )
    invoices["is_uk"] = invoices["country"].eq(UK_LABEL)
    table = pd.crosstab(invoices["is_uk"], invoices["is_cancelled"])
    chi2, p_value, _, _ = chi2_contingency(table.to_numpy())

    return {
        "identified_customers": int(len(customer)),
        "customers_with_return_value": int(len(returning)),
        "customer_return_gini_all": float(gini_coefficient(customer["return_value"])),
        "customer_return_gini_returning": float(gini_coefficient(returning)),
        "top_10pct_returning_customers_share": float(
            share_top_fraction(returning, 0.10)
        ),
        "stockcode_return_gini_positive": float(gini_coefficient(returning_stock)),
        "top_10_stockcode_return_share": float(share_top_n(returning_stock, 10)),
        "invoice_cancel_crosstab": table,
        "invoice_cancel_chi2": float(chi2),
        "invoice_cancel_p_value": float(p_value),
        "invoice_cancel_cramers_v": float(cramers_v(table.to_numpy())),
        "uk_cancel_rate": float(
            invoices.loc[invoices["is_uk"], "is_cancelled"].mean()
        ),
        "non_uk_cancel_rate": float(
            invoices.loc[~invoices["is_uk"], "is_cancelled"].mean()
        ),
        "flag_mismatch_rows": int(flag_mismatch_mask(prepared.retail_df).sum()),
        "total_return_value": float(customer["return_value"].sum()),
    }


def scenario_metrics(prepared: PreparedRetailData) -> dict[str, float]:
    sales = add_invoice_key(prepared.sales_analysis_df)
    customers = add_invoice_key(prepared.customer_analysis_df)
    gross = float(sales["Total_Revenue"].sum())
    uk = float(sales.loc[sales["Country"].eq(UK_LABEL), "Total_Revenue"].sum())
    customer_rev = customers.groupby("Customer ID")["Total_Revenue"].sum()
    orders = customers.groupby("Customer ID")["Invoice_Key"].nunique()
    product_rev = sales.groupby("StockCode")["Total_Revenue"].sum()
    negative_value = float(
        -prepared.retail_df.loc[
            prepared.retail_df["Total_Revenue"].lt(0), "Total_Revenue"
        ].sum()
    )
    return {
        "rows_raw": float(len(prepared.retail_df)),
        "rows_sales": float(len(prepared.sales_analysis_df)),
        "gross_sales": gross,
        "uk_share": uk / gross if gross else float("nan"),
        "customer_gini": float(gini_coefficient(customer_rev)),
        "top_10pct_customer_share": float(share_top_fraction(customer_rev, 0.10)),
        "top_10_stockcode_share": float(share_top_n(product_rev, 10)),
        "repeat_customer_rate": float(orders.ge(2).mean()),
        "negative_to_gross": negative_value / gross if gross else float("nan"),
    }


def sensitivity_table(prepared: PreparedRetailData) -> pd.DataFrame:
    baseline = scenario_metrics(prepared)
    dropped_dupes = apply_purpose_splits(
        drop_exact_duplicate_extras(prepared.retail_df)
    )
    without_mismatch = apply_purpose_splits(
        prepared.retail_df.loc[~flag_mismatch_mask(prepared.retail_df)].copy()
    )
    rows = []
    for name, metrics in (
        ("baseline", baseline),
        ("drop_duplicate_extras", scenario_metrics(dropped_dupes)),
        ("exclude_flag_mismatch", scenario_metrics(without_mismatch)),
    ):
        row = {"scenario": name, **metrics}
        rows.append(row)
    table = pd.DataFrame(rows).set_index("scenario")
    share_metrics = {
        "uk_share",
        "customer_gini",
        "top_10pct_customer_share",
        "top_10_stockcode_share",
        "repeat_customer_rate",
        "negative_to_gross",
    }
    material_flags = []
    for scenario in table.index:
        if scenario == "baseline":
            material_flags.append(False)
            continue
        changed = False
        for metric in table.columns:
            base = table.loc["baseline", metric]
            value = table.loc[scenario, metric]
            if not np.isfinite(base) or base == 0:
                continue
            relative = abs(value - base) / abs(base)
            share_delta = abs(value - base) if metric in share_metrics else 0.0
            if relative > MATERIAL_RELATIVE_CHANGE or share_delta > MATERIAL_SHARE_POINTS:
                changed = True
        material_flags.append(changed)
    table["material_change_vs_baseline"] = material_flags
    return table.reset_index()


def run_statistical_analysis(prepared: PreparedRetailData) -> StatisticalResults:
    monthly = monthly_sales_summary(prepared.sales_analysis_df)
    complete = complete_months(monthly)
    pairs = year_over_year_pairs(complete)
    yoy_test = paired_wilcoxon(
        pairs["revenue_2010"].to_numpy(),
        pairs["revenue_2011"].to_numpy(),
    )
    yoy_test["median_ratio"] = float(pairs["ratio_2011_over_2010"].median())
    yoy_test["peak_by_year"] = peak_complete_month_by_year(complete)

    invoices = invoice_sales(prepared.sales_analysis_df)
    complete_invoices = invoices.loc[~invoices["is_partial_month"]]
    month_groups = [
        complete_invoices.loc[
            complete_invoices["calendar_month"].eq(month), "revenue"
        ].to_numpy()
        for month in range(1, 13)
        if complete_invoices["calendar_month"].eq(month).any()
    ]
    month_kruskal = kruskal_epsilon_squared(month_groups)
    month_kruskal["note"] = (
        "Invoice-level Kruskal-Wallis on complete months. "
        "Interpret epsilon-squared; large n inflates significance."
    )

    uk_test = mannwhitney_with_effect(
        complete_invoices.loc[~complete_invoices["is_uk"], "revenue"].to_numpy(),
        complete_invoices.loc[complete_invoices["is_uk"], "revenue"].to_numpy(),
    )
    uk_test["group_x"] = "non-UK invoices"
    uk_test["group_y"] = "UK invoices"

    customer_rev = customer_revenue(prepared.customer_analysis_df)
    product_rev = product_revenue(prepared.sales_analysis_df)
    customer_conc = concentration_bundle(customer_rev)
    product_conc = concentration_bundle(product_rev, top_n=10)
    customer_conc_trimmed = concentration_bundle(drop_top_fraction(customer_rev, 0.01))
    product_conc_trimmed = concentration_bundle(
        drop_top_fraction(product_rev, 0.01), top_n=10
    )
    returns = returns_analysis(prepared)
    sensitivity = sensitivity_table(prepared)

    hypothesis_summary = pd.DataFrame(
        [
            {
                "hypothesis": "H1. Complete-month 2011 revenue differs from 2010",
                "unit": "paired calendar months Jan-Nov",
                "test": "Wilcoxon signed-rank",
                "p_value": yoy_test["p_value"],
                "effect": yoy_test["rank_biserial"],
                "effect_name": "rank-biserial (2011 vs 2010)",
                "significant_at_0.05": yoy_test["significant"],
            },
            {
                "hypothesis": "H2. Invoice revenue differs by calendar month",
                "unit": "completed invoices in complete months",
                "test": "Kruskal-Wallis",
                "p_value": month_kruskal["p_value"],
                "effect": month_kruskal["epsilon_squared"],
                "effect_name": "epsilon-squared",
                "significant_at_0.05": month_kruskal["significant"],
            },
            {
                "hypothesis": "H3. UK and non-UK invoice revenue distributions differ",
                "unit": "completed invoices in complete months",
                "test": "Mann-Whitney U",
                "p_value": uk_test["p_value"],
                "effect": uk_test["cliffs_delta"],
                "effect_name": f"Cliff's delta ({uk_test['cliffs_delta_label']})",
                "significant_at_0.05": uk_test["significant"],
            },
            {
                "hypothesis": "H4. Invoice cancellation is associated with UK vs non-UK",
                "unit": "invoices",
                "test": "Chi-square",
                "p_value": returns["invoice_cancel_p_value"],
                "effect": returns["invoice_cancel_cramers_v"],
                "effect_name": "Cramer's V",
                "significant_at_0.05": returns["invoice_cancel_p_value"] < ALPHA,
            },
        ]
    )
    return StatisticalResults(
        monthly=monthly,
        complete_monthly=complete,
        yoy_pairs=pairs,
        yoy_test=yoy_test,
        month_kruskal=month_kruskal,
        uk_invoice_test=uk_test,
        customer_concentration=customer_conc,
        customer_concentration_without_top_1pct=customer_conc_trimmed,
        product_concentration=product_conc,
        product_concentration_without_top_1pct=product_conc_trimmed,
        returns=returns,
        sensitivity=sensitivity,
        hypothesis_summary=hypothesis_summary,
    )
