"""Build the CASE 02 Power BI .pbix from verified Python aggregates."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from data_preparation import load_and_prepare  # noqa: E402
from kpi_segmentation import run_kpi_segmentation  # noqa: E402
from parse_official_tables import verify_source_file  # noqa: E402
from constants import RAW_FILE_NAME  # noqa: E402


POWERBI_DIR = CASE_DIR / "powerbi"
DATA_DIR = POWERBI_DIR / "data"
PBIX_PATH = POWERBI_DIR / "CASE02_Youth_Priority.pbix"


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
    export.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Wrote {path}")


def main() -> int:
    from pbix_mcp.builder import PBIXBuilder

    raw_path = CASE_DIR / "data" / "raw" / RAW_FILE_NAME
    source = verify_source_file(raw_path)
    prepared = load_and_prepare(raw_path)
    kpis = run_kpi_segmentation(prepared.tables, prepared)
    value_lookup = kpis.values.set_index("kpi")["value"]

    youth_profile = kpis.youth_profile[
        [
            "sido",
            "net_total",
            "net_youth_20_39",
            "net_20s",
            "net_30s",
            "typology",
            "typology_ko",
            "is_capital",
        ]
    ].copy()
    youth_profile["region_group"] = youth_profile["is_capital"].map(
        {True: "수도권", False: "비수도권"}
    )
    youth_profile = youth_profile.drop(columns=["is_capital"])
    youth_profile["typology"] = youth_profile["typology"].astype(str)

    typology = kpis.typology_summary.copy()
    typology["typology"] = typology["typology"].astype(str)

    top_od = kpis.top_od.copy()
    top_od["route"] = top_od["origin"] + "→" + top_od["destination"]

    capital = prepared.tables.capital_yearly[["year", "net"]].copy()

    mobility = prepared.youth_mobility.melt(
        id_vars=["year"],
        value_vars=["20-24", "25-29", "30-34", "35-39", "40-44"],
        var_name="age_band",
        value_name="mobility_rate",
    )

    kpi_row = pd.DataFrame(
        [
            {
                "kpi_set": "CASE02",
                "total_movers": int(value_lookup["Total movers 2025"]),
                "yoy_pct": float(value_lookup["YoY change in total movers 2025"]),
                "youth_movers": int(value_lookup["Youth movers 20-39, 2025"]),
                "youth_share": float(value_lookup["Youth share of movers 2025"]),
                "inter_sido_movers": int(value_lookup["Inter-sido movers 2025"]),
                "capital_net": int(value_lookup["Capital net vs non-capital 2025"]),
                "seoul_youth_net": int(value_lookup["Seoul youth 20-39 net 2025"]),
                "top_inflow_sido": str(
                    kpis.values.set_index("kpi").loc[
                        "Youth 20-39 net, top inflow sido", "sido"
                    ]
                ),
                "top_inflow_net": int(value_lookup["Youth 20-39 net, top inflow sido"]),
                "source_sha256": source["sha256"],
            }
        ]
    )
    notes = pd.DataFrame(
        {
            "line": [1, 2, 3, 4, 5],
            "note": [
                "청년=20-39세(원표 5세 구간 합). e-지방지표 19-39와 직접 대사하지 않는다.",
                "시도 간 OD는 전 연령이다. 청년 전출지→전입지 경로는 이 부표에 없다.",
                "서울은 청년 전체 순유입이지만 20대 + / 30대 − 이다.",
                "등록 이동이며 주거 의향·주택·일자리 인과가 아니다.",
                "충남은 청년을 20-34로 바꾸면 순이동 부호가 바뀐다.",
            ],
        }
    )
    priority = kpis.priority.copy()
    priority["is_capital"] = priority["is_capital"].map({True: "수도권", False: "비수도권"})

    _write_csv(youth_profile, "youth_profile_2025.csv")
    _write_csv(typology, "typology_summary.csv")
    _write_csv(top_od, "top_od_2025.csv")
    _write_csv(capital, "capital_yearly.csv")
    _write_csv(mobility, "youth_mobility_long.csv")
    _write_csv(kpi_row, "kpi.csv")
    _write_csv(notes, "notes.csv")
    _write_csv(priority, "priority.csv")

    builder = PBIXBuilder("CASE 02 Youth Priority")
    builder.add_table(
        "YouthProfile",
        [
            {"name": "sido", "data_type": "String"},
            {"name": "net_total", "data_type": "Int64"},
            {"name": "net_youth_20_39", "data_type": "Int64"},
            {"name": "net_20s", "data_type": "Int64"},
            {"name": "net_30s", "data_type": "Int64"},
            {"name": "typology", "data_type": "String"},
            {"name": "typology_ko", "data_type": "String"},
            {"name": "region_group", "data_type": "String"},
        ],
        rows=_records(youth_profile),
        source_csv=str((DATA_DIR / "youth_profile_2025.csv").resolve()),
    )
    builder.add_table(
        "Typology",
        [
            {"name": "typology", "data_type": "String"},
            {"name": "typology_ko", "data_type": "String"},
            {"name": "sido_count", "data_type": "Int64"},
            {"name": "youth_net_sum", "data_type": "Int64"},
            {"name": "total_net_sum", "data_type": "Int64"},
            {"name": "sidos", "data_type": "String"},
        ],
        rows=_records(typology),
        source_csv=str((DATA_DIR / "typology_summary.csv").resolve()),
    )
    builder.add_table(
        "TopOD",
        [
            {"name": "origin", "data_type": "String"},
            {"name": "destination", "data_type": "String"},
            {"name": "movers", "data_type": "Int64"},
            {"name": "flow_block", "data_type": "String"},
            {"name": "route", "data_type": "String"},
        ],
        rows=_records(top_od),
        source_csv=str((DATA_DIR / "top_od_2025.csv").resolve()),
    )
    builder.add_table(
        "CapitalYearly",
        [
            {"name": "year", "data_type": "Int64"},
            {"name": "net", "data_type": "Int64"},
        ],
        rows=_records(capital),
        source_csv=str((DATA_DIR / "capital_yearly.csv").resolve()),
    )
    builder.add_table(
        "MobilityRates",
        [
            {"name": "year", "data_type": "Int64"},
            {"name": "age_band", "data_type": "String"},
            {"name": "mobility_rate", "data_type": "Double"},
        ],
        rows=_records(mobility),
        source_csv=str((DATA_DIR / "youth_mobility_long.csv").resolve()),
    )
    builder.add_table(
        "KPI",
        [
            {"name": "kpi_set", "data_type": "String"},
            {"name": "total_movers", "data_type": "Int64"},
            {"name": "yoy_pct", "data_type": "Double"},
            {"name": "youth_movers", "data_type": "Int64"},
            {"name": "youth_share", "data_type": "Double"},
            {"name": "inter_sido_movers", "data_type": "Int64"},
            {"name": "capital_net", "data_type": "Int64"},
            {"name": "seoul_youth_net", "data_type": "Int64"},
            {"name": "top_inflow_sido", "data_type": "String"},
            {"name": "top_inflow_net", "data_type": "Int64"},
            {"name": "source_sha256", "data_type": "String"},
        ],
        rows=_records(kpi_row),
        source_csv=str((DATA_DIR / "kpi.csv").resolve()),
    )
    builder.add_table(
        "Priority",
        [
            {"name": "priority_group", "data_type": "String"},
            {"name": "sido", "data_type": "String"},
            {"name": "typology_ko", "data_type": "String"},
            {"name": "net_youth_20_39", "data_type": "Int64"},
            {"name": "net_20s", "data_type": "Int64"},
            {"name": "net_30s", "data_type": "Int64"},
            {"name": "net_total", "data_type": "Int64"},
            {"name": "is_capital", "data_type": "String"},
        ],
        rows=_records(priority),
        source_csv=str((DATA_DIR / "priority.csv").resolve()),
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
    builder.add_relationship("YouthProfile", "typology", "Typology", "typology")

    builder.add_measure(
        "KPI",
        "Total Movers",
        "MAX(KPI[total_movers])",
        format_string="#,0",
    )
    builder.add_measure(
        "KPI",
        "Youth Movers",
        "MAX(KPI[youth_movers])",
        format_string="#,0",
    )
    builder.add_measure(
        "KPI",
        "Youth Share",
        "MAX(KPI[youth_share])",
        format_string="0.0%",
    )
    builder.add_measure(
        "KPI",
        "Capital Net",
        "MAX(KPI[capital_net])",
        format_string="#,0",
    )
    builder.add_measure(
        "KPI",
        "Seoul Youth Net",
        "MAX(KPI[seoul_youth_net])",
        format_string="#,0",
    )
    builder.add_measure(
        "YouthProfile",
        "Youth Net 20-39",
        "SUM(YouthProfile[net_youth_20_39])",
        format_string="#,0",
    )
    builder.add_measure(
        "Typology",
        "Sido Count",
        "SUM(Typology[sido_count])",
        format_string="#,0",
    )
    builder.add_measure(
        "TopOD",
        "OD Movers",
        "SUM(TopOD[movers])",
        format_string="#,0",
    )
    builder.add_measure(
        "CapitalYearly",
        "Capital Year Net",
        "SUM(CapitalYearly[net])",
        format_string="#,0",
    )
    builder.add_measure(
        "MobilityRates",
        "Mobility Rate",
        "AVERAGE(MobilityRates[mobility_rate])",
        format_string="0.0",
    )

    builder.add_page(
        "Youth Priority",
        [
            {
                "name": "movers_card",
                "type": "card",
                "x": 16,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Total Movers"},
            },
            {
                "name": "youth_card",
                "type": "card",
                "x": 224,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Youth Movers"},
            },
            {
                "name": "share_card",
                "type": "card",
                "x": 432,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Youth Share"},
            },
            {
                "name": "capital_card",
                "type": "card",
                "x": 640,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Capital Net"},
            },
            {
                "name": "seoul_card",
                "type": "card",
                "x": 848,
                "y": 8,
                "width": 200,
                "height": 88,
                "config": {"measure": "Seoul Youth Net"},
            },
            {
                "name": "region_slicer",
                "type": "slicer",
                "x": 1056,
                "y": 8,
                "width": 208,
                "height": 88,
                "config": {"column": {"table": "YouthProfile", "column": "region_group"}},
            },
            {
                "name": "youth_net_bar",
                "type": "clusteredBarChart",
                "x": 16,
                "y": 108,
                "width": 520,
                "height": 320,
                "config": {
                    "category": {"table": "YouthProfile", "column": "sido"},
                    "measure": "Youth Net 20-39",
                },
            },
            {
                "name": "typology_bar",
                "type": "clusteredBarChart",
                "x": 544,
                "y": 108,
                "width": 320,
                "height": 320,
                "config": {
                    "category": {"table": "Typology", "column": "typology_ko"},
                    "measure": "Sido Count",
                },
            },
            {
                "name": "priority_table",
                "type": "tableEx",
                "x": 872,
                "y": 108,
                "width": 392,
                "height": 320,
                "config": {
                    "columns": [
                        {"table": "Priority", "column": "priority_group"},
                        {"table": "Priority", "column": "sido"},
                        {"table": "Priority", "column": "net_youth_20_39"},
                        {"table": "Priority", "column": "net_20s"},
                        {"table": "Priority", "column": "net_30s"},
                    ]
                },
            },
            {
                "name": "capital_line",
                "type": "lineChart",
                "x": 16,
                "y": 440,
                "width": 400,
                "height": 264,
                "config": {
                    "category": {"table": "CapitalYearly", "column": "year"},
                    "measure": "Capital Year Net",
                    "sort": {"by": "year", "direction": "asc"},
                },
            },
            {
                "name": "od_bar",
                "type": "clusteredBarChart",
                "x": 424,
                "y": 440,
                "width": 432,
                "height": 264,
                "config": {
                    "category": {"table": "TopOD", "column": "route"},
                    "measure": "OD Movers",
                },
            },
            {
                "name": "notes_table",
                "type": "tableEx",
                "x": 864,
                "y": 440,
                "width": 400,
                "height": 264,
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
    keep = {
        "youth_profile_2025.csv",
        "typology_summary.csv",
        "top_od_2025.csv",
        "capital_yearly.csv",
        "youth_mobility_long.csv",
        "kpi.csv",
        "notes.csv",
        "priority.csv",
    }
    for leftover in DATA_DIR.glob("*.csv"):
        if leftover.name not in keep:
            leftover.unlink()
            print(f"Removed leftover {leftover.name}")
    print(f"Wrote {PBIX_PATH} ({PBIX_PATH.stat().st_size:,} bytes)")
    print(f"Total movers 2025 {int(value_lookup['Total movers 2025']):,}")
    print(f"Youth movers 20-39 {int(value_lookup['Youth movers 20-39, 2025']):,}")
    print(f"SHA-256 {source['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
