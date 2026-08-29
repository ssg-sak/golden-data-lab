"""One-page decision dashboard for CASE 02."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from data_preparation import PreparedMigrationData
from kpi_segmentation import KPIResults
from parse_official_tables import OfficialTables
from sido_map import plot_youth_net_map
from statistical_analysis import StatisticalResults


TYPOLOGY_COLORS = {
    "Early Career Magnet": "#C73E1D",
    "Dual Magnet": "#2E6F9E",
    "Family Settle": "#3B8C6E",
    "Youth Outflow": "#8A8A8A",
}


def _apply_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def _thousands(value: float, _pos: object) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{abs(value)/1000:.0f}천"


def save_decision_dashboard(
    tables: OfficialTables,
    prepared: PreparedMigrationData,
    stats: StatisticalResults,
    kpis: KPIResults,
    output_path: Path,
) -> Path:
    _apply_font()
    fig = plt.figure(figsize=(16, 10.5))
    grid = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.32)

    ax_map = fig.add_subplot(grid[0, :2])
    plot_youth_net_map(ax_map, kpis.youth_profile)

    ax_type = fig.add_subplot(grid[0, 2])
    summary = kpis.typology_summary
    ax_type.barh(
        summary["typology_ko"],
        summary["sido_count"],
        color=[TYPOLOGY_COLORS[label] for label in summary["typology"]],
    )
    ax_type.set_title("유형별 시도 수", loc="left", weight="bold")
    ax_type.set_xlabel("시도 수")

    ax_age = fig.add_subplot(grid[1, 0])
    mobility = prepared.youth_mobility
    ax_age.plot(mobility["year"], mobility["20-24"], label="20-24", color="#C73E1D", linewidth=2)
    ax_age.plot(mobility["year"], mobility["25-29"], label="25-29", color="#E09F3E", linewidth=2)
    ax_age.plot(mobility["year"], mobility["30-34"], label="30-34", color="#2E6F9E", linewidth=2)
    ax_age.plot(mobility["year"], mobility["35-39"], label="35-39", color="#3B8C6E", linewidth=2)
    ax_age.plot(
        mobility["year"], mobility["40-44"], label="40-44", color="#888888", linewidth=1.4, linestyle="--"
    )
    ax_age.set_title("전국 연령별 이동률 2005-2025", loc="left", weight="bold")
    ax_age.set_ylabel("%")
    ax_age.legend(frameon=False, fontsize=8)

    ax_cap = fig.add_subplot(grid[1, 1])
    capital = tables.capital_yearly
    ax_cap.plot(capital["year"], capital["net"] / 1000, color="#2E6F9E", linewidth=2)
    ax_cap.axhline(0, color="#333333", linewidth=0.8)
    ax_cap.set_title("수도권 순이동 (비수도권 대비)", loc="left", weight="bold")
    ax_cap.set_ylabel("천 명")

    ax_od = fig.add_subplot(grid[1, 2])
    top = kpis.top_od.head(8).iloc[::-1]
    labels = [f"{row.origin}→{row.destination}" for row in top.itertuples(index=False)]
    ax_od.barh(labels, top["movers"], color="#5A8FAD")
    ax_od.set_title("2025 시도 간 이동 상위 경로 (전 연령)", loc="left", weight="bold")
    ax_od.set_xlabel("이동자 수")
    ax_od.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1000:.0f}천"))

    seoul = kpis.youth_profile.set_index("sido").loc["서울"]
    fig.suptitle(
        "CASE 02  청년 이동 우선 지역  —  2025 등록 국내이동  "
        f"(서울 20대 순이동 {int(seoul['net_20s']):+,} / 30대 {int(seoul['net_30s']):+,})",
        fontsize=14,
        weight="bold",
        y=0.98,
    )
    fig.text(
        0.01,
        0.01,
        "청년=20-39세(5세 구간 합). 시도 간 OD는 전 연령. 유형은 2025 순이동 부호이며 인과가 아니다. "
        "지도 경계는 통계청 2018 시도(표시를 위해 울릉·독도는 잘랐다). "
        f"H1 20-24 vs 40-44 이동률 Wilcoxon p={stats.h1['p_value']:.1e}.",
        fontsize=8,
        color="#444444",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_youth_net_figure(youth_profile: pd.DataFrame, output_path: Path) -> Path:
    _apply_font()
    fig, ax = plt.subplots(figsize=(8.2, 10.5))
    plot_youth_net_map(ax, youth_profile)
    fig.text(
        0.02,
        0.01,
        "경계: 통계청 2018 시도. 값은 2025 등록 청년(20-39) 순이동. 울릉·독도는 표시 범위 밖.",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path
