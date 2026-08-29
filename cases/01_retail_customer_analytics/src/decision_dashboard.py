"""Decision-dashboard figures for CASE 01."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from kpi_segmentation import KPIResults
from statistical_analysis import StatisticalResults, gini_coefficient, share_top_fraction


def _apply_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def save_concentration_figure(
    customer_revenue: pd.Series,
    output_path: Path,
) -> Path:
    _apply_font()
    values = np.sort(customer_revenue.to_numpy(dtype=float))
    population = np.arange(1, values.size + 1) / values.size
    wealth = np.cumsum(values) / values.sum()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(population, wealth, color="#31688E", linewidth=2.2, label="식별 고객 매출")
    ax.plot([0, 1], [0, 1], color="#888888", linestyle="--", linewidth=1, label="완전 균등")
    ax.set_title("고객 매출  Lorenz 곡선", loc="left", fontsize=14, weight="bold")
    ax.set_xlabel("고객 누적 비중")
    ax.set_ylabel("매출 누적 비중")
    gini = gini_coefficient(values)
    top10 = share_top_fraction(values, 0.10)
    ax.text(
        0.05,
        0.82,
        f"Gini {gini:.2f}\n상위 10% 매출 비중 {top10:.1%}",
        transform=ax.transAxes,
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#C8C8C8"},
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_decision_dashboard(
    stats: StatisticalResults,
    kpis: KPIResults,
    output_path: Path,
) -> Path:
    _apply_font()
    fig = plt.figure(figsize=(16, 10))
    grid = fig.add_gridspec(2, 3, hspace=0.38, wspace=0.32)

    ax_month = fig.add_subplot(grid[0, 0])
    monthly = stats.monthly
    ax_month.plot(monthly["Month"], monthly["revenue"], color="#31688E", linewidth=2)
    complete = stats.complete_monthly
    peak = complete.loc[complete["revenue"].idxmax()]
    ax_month.scatter([peak["Month"]], [peak["revenue"]], color="#D89C22", zorder=3)
    ax_month.set_title("월별 정상 매출", loc="left", weight="bold")
    ax_month.set_ylabel("£")
    ax_month.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value/1_000_000:.1f}M")
    )
    ax_month.tick_params(axis="x", labelrotation=30)

    ax_seg = fig.add_subplot(grid[0, 1])
    segments = kpis.segment_summary.sort_values("revenue")
    ax_seg.barh(segments["segment"], segments["revenue"], color="#5A8FAD")
    ax_seg.set_title("RFM 세그먼트 매출", loc="left", weight="bold")
    ax_seg.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"£{value/1_000_000:.1f}M")
    )

    ax_kpi = fig.add_subplot(grid[0, 2])
    ax_kpi.axis("off")
    ax_kpi.set_title("확정 KPI", loc="left", weight="bold")
    value_lookup = kpis.values.set_index("kpi")["value"]
    lines = [
        f"정상 매출  £{value_lookup['Gross sales']:,.0f}",
        f"AOV  £{value_lookup['AOV']:,.0f}",
        f"재구매 고객  {value_lookup['Repeat-customer rate']:.1%}",
        f"영국 매출 비중  {value_lookup['UK revenue share']:.1%}",
        f"식별 고객 매출 비중  {value_lookup['Identified-customer revenue share']:.1%}",
        f"음수금액/정상매출  {value_lookup['Negative-value-to-gross ratio']:.1%}",
        f"RFM 기준일  {kpis.snapshot_date:%Y-%m-%d}",
    ]
    ax_kpi.text(0.0, 0.95, "\n\n".join(lines), va="top", fontsize=11, family="Malgun Gothic")

    ax_action = fig.add_subplot(grid[1, 0])
    action = (
        kpis.segment_summary.groupby("action", as_index=False)
        .agg(customers=("customers", "sum"), revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
    )
    ax_action.bar(action["action"], action["revenue"], color="#D7A438")
    ax_action.set_title("실행 유형별 매출", loc="left", weight="bold")
    ax_action.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"£{value/1_000_000:.1f}M")
    )

    ax_cohort = fig.add_subplot(grid[1, 1])
    retention = kpis.cohort_retention.copy()
    retention = retention.loc[
        ~retention["is_partial_cohort"] & retention["period_number"].between(0, 6)
    ]
    pivot = retention.pivot(
        index="cohort_month", columns="period_number", values="retention"
    )
    im = ax_cohort.imshow(pivot.to_numpy(), aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax_cohort.set_title("코호트 유지율 (0~6개월)", loc="left", weight="bold")
    ax_cohort.set_xticks(range(pivot.shape[1]), labels=list(pivot.columns))
    ax_cohort.set_yticks(
        range(pivot.shape[0]),
        labels=[stamp.strftime("%Y-%m") for stamp in pivot.index],
        fontsize=7,
    )
    ax_cohort.set_xlabel("코호트 월차")
    fig.colorbar(im, ax=ax_cohort, fraction=0.046, pad=0.04)

    ax_note = fig.add_subplot(grid[1, 2])
    ax_note.axis("off")
    ax_note.set_title("의사결정 메모", loc="left", weight="bold")
    yoy_p = stats.yoy_test["p_value"]
    gini = stats.customer_concentration["gini"]["estimate"]
    top10 = stats.customer_concentration["top_10pct_share"]["estimate"]
    material = stats.sensitivity.loc[
        stats.sensitivity["scenario"].ne("baseline"), "material_change_vs_baseline"
    ].any()
    note = (
        f"YoY Wilcoxon p={yoy_p:.3f}, "
        f"rank-biserial={stats.yoy_test['rank_biserial']:.2f}\n\n"
        f"고객 매출 Gini {gini:.2f}, 상위 10% {top10:.1%}\n\n"
        f"취소는 환불 매칭 없이 집중도만 해석\n\n"
        f"중복·플래그 민감도 결론 변경: {'있음' if material else '없음'}\n\n"
        "2009-2011 관측 기간 내부 패턴이며\n현재 시장으로 일반화하지 않음"
    )
    ax_note.text(0.0, 0.95, note, va="top", fontsize=11)

    fig.suptitle(
        "CASE 01 의사결정 요약: 유지·재활성화 우선 배분",
        fontsize=16,
        weight="bold",
        y=0.98,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path
