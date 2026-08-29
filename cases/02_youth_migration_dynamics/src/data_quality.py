"""Data-quality checks against the official annex. Nothing is dropped here."""

from __future__ import annotations

from typing import Any

import pandas as pd

from constants import HEADLINE_TOTAL_MOVERS_2025, SIDOS, SNAPSHOT_YEAR, STALE_SHEET
from data_preparation import PreparedMigrationData
from parse_official_tables import OfficialTables


def _check(name: str, passed: bool, actual: Any, expected: Any | None = None, note: str = "") -> dict[str, Any]:
    return {
        "check_name": name,
        "passed": bool(passed),
        "actual": actual,
        "expected": expected,
        "note": note,
    }


def run_quality_checks(tables: OfficialTables, prepared: PreparedMigrationData) -> pd.DataFrame:
    checks: list[dict[str, Any]] = []
    national_2025 = tables.national_movers.loc[
        tables.national_movers["year"] == SNAPSHOT_YEAR
    ].iloc[0]
    checks.append(
        _check(
            "headline_total_movers_2025",
            int(national_2025["movers_total"]) == HEADLINE_TOTAL_MOVERS_2025,
            int(national_2025["movers_total"]),
            HEADLINE_TOTAL_MOVERS_2025,
            "보도 헤드라인과 표 1의 2025 총이동자 수",
        )
    )
    intra_plus_inter = int(national_2025["intra_sido_movers"]) + int(
        national_2025["inter_sido_movers"]
    )
    checks.append(
        _check(
            "intra_plus_inter_equals_total",
            intra_plus_inter == int(national_2025["movers_total"]),
            intra_plus_inter,
            int(national_2025["movers_total"]),
        )
    )
    male_female = int(national_2025["movers_male"]) + int(national_2025["movers_female"])
    checks.append(
        _check(
            "male_plus_female_equals_total",
            male_female == int(national_2025["movers_total"]),
            male_female,
            int(national_2025["movers_total"]),
        )
    )

    sido_in = tables.sido_yearly.query("year == @SNAPSHOT_YEAR and measure == 'in' and sido == '전국'")[
        "value"
    ].item()
    checks.append(
        _check(
            "sheet3_national_in_equals_sheet1",
            int(sido_in) == int(national_2025["movers_total"]),
            int(sido_in),
            int(national_2025["movers_total"]),
        )
    )

    net_national = tables.sido_yearly.query(
        "year == @SNAPSHOT_YEAR and measure == 'net' and sido == '전국'"
    )["value"].item()
    checks.append(_check("national_net_is_zero", int(net_national) == 0, int(net_national), 0))

    sheet5_total = (
        tables.sido_age_net_2025.query("gender == 'all' and age_group == 'total'")
        .set_index("sido")["net"]
        .reindex(SIDOS)
    )
    sheet3_net = (
        tables.sido_yearly.query("year == @SNAPSHOT_YEAR and measure == 'net' and sido != '전국'")
        .set_index("sido")["value"]
        .reindex(SIDOS)
    )
    checks.append(
        _check(
            "sheet5_total_matches_sheet3_net",
            sheet5_total.equals(sheet3_net.astype("int64")),
            int((sheet5_total - sheet3_net).abs().sum()),
            0,
        )
    )

    age_bands = tables.sido_age_net_2025.query("gender == 'all' and age_group != 'total'")
    band_sum = age_bands.groupby("sido")["net"].sum().reindex(SIDOS)
    checks.append(
        _check(
            "age_bands_sum_to_sido_total_net",
            band_sum.equals(sheet5_total.astype("int64")),
            int((band_sum - sheet5_total).abs().sum()),
            0,
            "0-4부터 80+까지 합이 계와 같은지",
        )
    )

    gender_sum = (
        tables.sido_age_net_2025.query("gender != 'all' and age_group == 'total'")
        .groupby("sido")["net"]
        .sum()
        .reindex(SIDOS)
    )
    checks.append(
        _check(
            "male_female_net_sum_to_all",
            gender_sum.equals(sheet5_total.astype("int64")),
            int((gender_sum - sheet5_total).abs().sum()),
            0,
        )
    )

    od = tables.od_movers_2025.query("gender == 'all'")
    dest_total = od.query("destination == '서울' and origin == '전국'")["movers"].item()
    intra = od.query("destination == '서울' and origin == '서울'")["movers"].item()
    inter_in = tables.sido_gender_2025.query("gender == 'all' and sido == '서울'")[
        "inter_sido_in"
    ].item()
    checks.append(
        _check(
            "od_row_is_destination",
            int(dest_total) - int(intra) == int(inter_in),
            int(dest_total) - int(intra),
            int(inter_in),
            "행=전입지, 열=전출지. 서울 행의 전국-대각 = 시도간 전입",
        )
    )

    od_net = tables.od_net_2025.query(
        "gender == 'all' and destination == '서울' and origin == '경기'"
    )["net"].item()
    movers_sg = tables.od_movers_2025.query(
        "gender == 'all' and destination == '서울' and origin == '경기'"
    )["movers"].item()
    movers_gs = tables.od_movers_2025.query(
        "gender == 'all' and destination == '경기' and origin == '서울'"
    )["movers"].item()
    checks.append(
        _check(
            "od_net_equals_mover_difference",
            int(od_net) == int(movers_sg) - int(movers_gs),
            int(od_net),
            int(movers_sg) - int(movers_gs),
        )
    )

    capital_row = tables.capital_yearly.set_index("year").loc[SNAPSHOT_YEAR]
    checks.append(
        _check(
            "capital_net_equals_in_minus_out",
            int(capital_row["net"])
            == int(capital_row["in_from_noncapital"]) - int(capital_row["out_to_noncapital"]),
            int(capital_row["net"]),
            int(capital_row["in_from_noncapital"]) - int(capital_row["out_to_noncapital"]),
        )
    )

    typology_n = prepared.youth_profile["typology"].nunique()
    checks.append(
        _check(
            "typology_covers_all_sidos",
            len(prepared.youth_profile) == 17 and typology_n >= 1,
            len(prepared.youth_profile),
            17,
        )
    )
    checks.append(
        _check(
            "stale_sheet_detected_and_unused",
            tables.workbook["has_stale_monthly_sheet"],
            STALE_SHEET,
            STALE_SHEET,
            "워크북에 2009-2011 월별 잔여 시트가 있으나 분석에서 사용하지 않음",
        )
    )

    seoul_youth = prepared.youth_profile.set_index("sido").loc["서울"]
    checks.append(
        _check(
            "seoul_20s_positive_30s_negative",
            seoul_youth["net_20s"] > 0 > seoul_youth["net_30s"],
            {"net_20s": int(seoul_youth["net_20s"]), "net_30s": int(seoul_youth["net_30s"])},
            "20s>0 and 30s<0",
        )
    )
    return pd.DataFrame(checks)
