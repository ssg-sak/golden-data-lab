"""Derived analysis frames for CASE 02. Raw Excel values are not rewritten."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from constants import (
    CAPITAL_SIDOS,
    SIDOS,
    SNAPSHOT_YEAR,
    YOUTH_20_34,
    YOUTH_20S,
    YOUTH_30S,
    YOUTH_AGES,
)
from parse_official_tables import OfficialTables, load_official_tables


TYPOLOGY_ORDER = (
    "Early Career Magnet",
    "Dual Magnet",
    "Family Settle",
    "Youth Outflow",
)

TYPOLOGY_KO = {
    "Early Career Magnet": "초입 유입·후기 유출형",
    "Dual Magnet": "청년 유입형",
    "Family Settle": "후기 정착형",
    "Youth Outflow": "청년 유출형",
}


def assign_youth_typology(net_20s: int, net_30s: int) -> str:
    """Mutually exclusive labels. Sign of 20s is checked first, then 30s.

    Zero is grouped with the non-positive side so a region cannot sit in two
    buckets. This is a 2025 snapshot typology, not a causal cluster.
    """

    if net_20s > 0 and net_30s > 0:
        return "Dual Magnet"
    if net_20s > 0 and net_30s <= 0:
        return "Early Career Magnet"
    if net_20s <= 0 and net_30s > 0:
        return "Family Settle"
    return "Youth Outflow"


def _sum_ages(frame: pd.DataFrame, ages: tuple[str, ...], gender: str = "all") -> pd.DataFrame:
    subset = frame.loc[
        (frame["gender"] == gender) & (frame["age_group"].isin(ages)),
        ["sido", "net"],
    ]
    return (
        subset.groupby("sido", as_index=False)["net"]
        .sum()
        .set_index("sido")
        .reindex(SIDOS)
        .reset_index()
    )


def youth_profile_2025(sido_age_net: pd.DataFrame, gender: str = "all") -> pd.DataFrame:
    total = sido_age_net.loc[
        (sido_age_net["gender"] == gender) & (sido_age_net["age_group"] == "total"),
        ["sido", "net"],
    ].rename(columns={"net": "net_total"})
    youth = _sum_ages(sido_age_net, YOUTH_AGES, gender).rename(columns={"net": "net_youth_20_39"})
    youth_20_34 = _sum_ages(sido_age_net, YOUTH_20_34, gender).rename(
        columns={"net": "net_youth_20_34"}
    )
    net_20s = _sum_ages(sido_age_net, YOUTH_20S, gender).rename(columns={"net": "net_20s"})
    net_30s = _sum_ages(sido_age_net, YOUTH_30S, gender).rename(columns={"net": "net_30s"})
    bands = (
        sido_age_net.loc[
            (sido_age_net["gender"] == gender) & (sido_age_net["age_group"].isin(YOUTH_AGES)),
            ["sido", "age_group", "net"],
        ]
        .pivot(index="sido", columns="age_group", values="net")
        .reindex(columns=list(YOUTH_AGES))
        .reset_index()
        .rename(columns={age: f"net_{age.replace('-', '_')}" for age in YOUTH_AGES})
    )
    profile = (
        total.merge(youth, on="sido")
        .merge(youth_20_34, on="sido")
        .merge(net_20s, on="sido")
        .merge(net_30s, on="sido")
        .merge(bands, on="sido")
    )
    profile["year"] = SNAPSHOT_YEAR
    profile["gender"] = gender
    profile["is_capital"] = profile["sido"].isin(CAPITAL_SIDOS)
    profile["typology"] = [
        assign_youth_typology(int(row.net_20s), int(row.net_30s))
        for row in profile.itertuples(index=False)
    ]
    profile["typology_ko"] = profile["typology"].map(TYPOLOGY_KO)
    profile["youth_share_of_abs_net"] = profile["net_youth_20_39"].abs() / profile[
        "net_total"
    ].abs().replace(0, pd.NA)
    return profile.sort_values("net_youth_20_39", ascending=False).reset_index(drop=True)


def inter_sido_od(od_movers: pd.DataFrame, gender: str = "all") -> pd.DataFrame:
    frame = od_movers.loc[
        (od_movers["gender"] == gender)
        & (od_movers["origin"].isin(SIDOS))
        & (od_movers["destination"].isin(SIDOS))
        & (od_movers["origin"] != od_movers["destination"])
    ].copy()
    frame["origin_capital"] = frame["origin"].isin(CAPITAL_SIDOS)
    frame["destination_capital"] = frame["destination"].isin(CAPITAL_SIDOS)
    frame["flow_block"] = frame.apply(_flow_block, axis=1)
    return frame.reset_index(drop=True)


def _flow_block(row: pd.Series) -> str:
    if row.origin_capital and row.destination_capital:
        return "capital_to_capital"
    if row.origin_capital and not row.destination_capital:
        return "capital_to_noncapital"
    if (not row.origin_capital) and row.destination_capital:
        return "noncapital_to_capital"
    return "noncapital_to_noncapital"


def capital_od_summary(od_movers: pd.DataFrame, gender: str = "all") -> pd.DataFrame:
    inter = inter_sido_od(od_movers, gender)
    summary = (
        inter.groupby("flow_block", as_index=False)["movers"]
        .sum()
        .sort_values("movers", ascending=False)
        .reset_index(drop=True)
    )
    summary["share"] = summary["movers"] / summary["movers"].sum()
    return summary


def youth_mobility_series(age_movers: pd.DataFrame, gender: str = "all") -> pd.DataFrame:
    subset = age_movers.loc[age_movers["gender"] == gender].copy()
    youth = (
        subset.loc[subset["age_group"].isin(YOUTH_AGES)]
        .groupby("year", as_index=False)
        .agg(youth_movers=("movers", "sum"))
    )
    total = subset.loc[subset["age_group"] == "total", ["year", "movers", "mobility_rate"]].rename(
        columns={"movers": "total_movers", "mobility_rate": "total_mobility_rate"}
    )
    bands = (
        subset.loc[subset["age_group"].isin(YOUTH_AGES + ("15-19", "40-44"))]
        .pivot(index="year", columns="age_group", values="mobility_rate")
        .reset_index()
    )
    merged = youth.merge(total, on="year").merge(bands, on="year")
    merged["youth_share_of_movers"] = merged["youth_movers"] / merged["total_movers"]
    return merged.sort_values("year").reset_index(drop=True)


@dataclass
class PreparedMigrationData:
    tables: OfficialTables
    youth_profile: pd.DataFrame
    youth_profile_male: pd.DataFrame
    youth_profile_female: pd.DataFrame
    inter_sido: pd.DataFrame
    capital_flows: pd.DataFrame
    youth_mobility: pd.DataFrame


def prepare_migration_data(tables: OfficialTables) -> PreparedMigrationData:
    return PreparedMigrationData(
        tables=tables,
        youth_profile=youth_profile_2025(tables.sido_age_net_2025, "all"),
        youth_profile_male=youth_profile_2025(tables.sido_age_net_2025, "male"),
        youth_profile_female=youth_profile_2025(tables.sido_age_net_2025, "female"),
        inter_sido=inter_sido_od(tables.od_movers_2025, "all"),
        capital_flows=capital_od_summary(tables.od_movers_2025, "all"),
        youth_mobility=youth_mobility_series(tables.age_movers, "all"),
    )


def load_and_prepare(path) -> PreparedMigrationData:
    return prepare_migration_data(load_official_tables(path))
