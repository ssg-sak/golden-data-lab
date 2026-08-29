"""KPI dictionary and 2025 youth regional typology."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from constants import SNAPSHOT_YEAR, YOUTH_AGES
from data_preparation import PreparedMigrationData, TYPOLOGY_ORDER
from parse_official_tables import OfficialTables


KPI_ROWS = [
    {
        "kpi": "Total movers 2025",
        "formula": "Sheet 1 총이동 이동자수, 남녀전체",
        "grain": "registered mover, calendar year 2025",
        "period": "2025",
        "include": "시도내 + 시도간",
        "exclude": "해외 이동, 미등록 이동",
    },
    {
        "kpi": "Youth movers 20-39, 2025",
        "formula": "Sheet 2 20-24+25-29+30-34+35-39 이동자수",
        "grain": "registered mover by 5-year age",
        "period": "2025",
        "include": "남녀전체, 시도내+시도간",
        "exclude": "19세; e-지방지표 19-39와 직접 대사하지 않음",
    },
    {
        "kpi": "Youth share of movers 2025",
        "formula": "Youth movers 20-39 / Total movers",
        "grain": "national calendar year",
        "period": "2025",
        "include": "Sheet 2 남녀전체",
        "exclude": "순이동 지표가 아님",
    },
    {
        "kpi": "Inter-sido movers 2025",
        "formula": "Sheet 1 시도간 이동자수",
        "grain": "registered mover crossing a sido boundary",
        "period": "2025",
        "include": "시도간만",
        "exclude": "시군구 내부 이동",
    },
    {
        "kpi": "Capital net vs non-capital 2025",
        "formula": "전입(비수도권→수도권) - 전출(수도권→비수도권)",
        "grain": "capital region vs rest of country",
        "period": "2025",
        "include": "서울·인천·경기",
        "exclude": "수도권 내부 서울↔경기 흐름",
    },
    {
        "kpi": "Youth 20-39 net, top inflow sido",
        "formula": "Sheet 5 20-39 순이동 합, 최댓값 시도",
        "grain": "sido, 2025, 남녀전체",
        "period": "2025",
        "include": "네 개 5세 구간 순이동 합",
        "exclude": "전입지×전출지 청년 OD (원본에 없음)",
    },
]


@dataclass
class KPIResults:
    dictionary: pd.DataFrame
    values: pd.DataFrame
    youth_profile: pd.DataFrame
    typology_summary: pd.DataFrame
    priority: pd.DataFrame
    reason_net: pd.DataFrame
    top_od: pd.DataFrame


def typology_summary(youth_profile: pd.DataFrame) -> pd.DataFrame:
    summary = (
        youth_profile.groupby(["typology", "typology_ko"], as_index=False)
        .agg(
            sido_count=("sido", "size"),
            youth_net_sum=("net_youth_20_39", "sum"),
            total_net_sum=("net_total", "sum"),
            sidos=("sido", lambda values: ", ".join(values)),
        )
    )
    summary["typology"] = pd.Categorical(summary["typology"], TYPOLOGY_ORDER, ordered=True)
    return summary.sort_values("typology").reset_index(drop=True)


def priority_table(youth_profile: pd.DataFrame) -> pd.DataFrame:
    outflow = (
        youth_profile.loc[youth_profile["typology"] == "Youth Outflow"]
        .sort_values("net_youth_20_39")
        .head(5)
        .copy()
    )
    outflow["priority_group"] = "Youth net outflow"
    magnet = (
        youth_profile.loc[youth_profile["typology"] == "Early Career Magnet"]
        .sort_values("net_20s", ascending=False)
        .copy()
    )
    magnet["priority_group"] = "Early-career inflow, later outflow"
    dual = (
        youth_profile.loc[youth_profile["typology"] == "Dual Magnet"]
        .sort_values("net_youth_20_39", ascending=False)
        .head(3)
        .copy()
    )
    dual["priority_group"] = "Youth inflow (20s and 30s)"
    settle = youth_profile.loc[youth_profile["typology"] == "Family Settle"].copy()
    settle["priority_group"] = "20s outflow, 30s inflow"
    cols = [
        "priority_group",
        "sido",
        "typology_ko",
        "net_youth_20_39",
        "net_20s",
        "net_30s",
        "net_total",
        "is_capital",
    ]
    return pd.concat([magnet, dual, settle, outflow], ignore_index=True)[cols]


def kpi_values(tables: OfficialTables, prepared: PreparedMigrationData) -> pd.DataFrame:
    national = tables.national_movers.set_index("year").loc[SNAPSHOT_YEAR]
    youth_2025 = prepared.youth_mobility.set_index("year").loc[SNAPSHOT_YEAR]
    capital = tables.capital_yearly.set_index("year").loc[SNAPSHOT_YEAR]
    top_in = prepared.youth_profile.iloc[0]
    values = [
        {
            "kpi": "Total movers 2025",
            "value": int(national["movers_total"]),
            "unit": "persons",
        },
        {
            "kpi": "YoY change in total movers 2025",
            "value": float(national["yoy_pct"]),
            "unit": "percent",
        },
        {
            "kpi": "Youth movers 20-39, 2025",
            "value": int(youth_2025["youth_movers"]),
            "unit": "persons",
        },
        {
            "kpi": "Youth share of movers 2025",
            "value": float(youth_2025["youth_share_of_movers"]),
            "unit": "share",
        },
        {
            "kpi": "Inter-sido movers 2025",
            "value": int(national["inter_sido_movers"]),
            "unit": "persons",
        },
        {
            "kpi": "Capital net vs non-capital 2025",
            "value": int(capital["net"]),
            "unit": "persons",
        },
        {
            "kpi": "Youth 20-39 net, top inflow sido",
            "value": int(top_in["net_youth_20_39"]),
            "unit": "persons",
            "sido": top_in["sido"],
        },
        {
            "kpi": "Seoul youth 20-39 net 2025",
            "value": int(prepared.youth_profile.set_index("sido").loc["서울", "net_youth_20_39"]),
            "unit": "persons",
        },
        {
            "kpi": "Youth age bands used",
            "value": "+".join(YOUTH_AGES),
            "unit": "definition",
        },
    ]
    return pd.DataFrame(values)


def reason_net_table(tables: OfficialTables) -> pd.DataFrame:
    frame = tables.reason_2025.query("flow == 'net' and reason != 'total' and sido != '전국'")
    return frame.pivot(index="sido", columns="reason", values="value").reset_index()


def top_od_pairs(prepared: PreparedMigrationData, n: int = 10) -> pd.DataFrame:
    return (
        prepared.inter_sido.sort_values("movers", ascending=False)
        .head(n)
        .loc[:, ["origin", "destination", "movers", "flow_block"]]
        .reset_index(drop=True)
    )


def run_kpi_segmentation(
    tables: OfficialTables, prepared: PreparedMigrationData
) -> KPIResults:
    profile = prepared.youth_profile.copy()
    return KPIResults(
        dictionary=pd.DataFrame(KPI_ROWS),
        values=kpi_values(tables, prepared),
        youth_profile=profile,
        typology_summary=typology_summary(profile),
        priority=priority_table(profile),
        reason_net=reason_net_table(tables),
        top_od=top_od_pairs(prepared),
    )
