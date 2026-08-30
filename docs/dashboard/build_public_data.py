"""Write the public dashboard snapshot from verified case JSON."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE01 = ROOT / "cases" / "01_retail_customer_analytics" / "evidence" / "later_stages_summary.json"
CASE02 = ROOT / "cases" / "02_youth_migration_dynamics" / "evidence" / "analysis_summary.json"
OUT = Path(__file__).resolve().parent / "data.js"


def kpi_map(rows: list[dict]) -> dict[str, object]:
    return {row["kpi"]: row for row in rows}


def main() -> None:
    case01 = json.loads(CASE01.read_text(encoding="utf-8"))
    case02 = json.loads(CASE02.read_text(encoding="utf-8"))
    kpis = kpi_map(case02["kpis"])
    seoul = next(row for row in case02["youth_profile"] if row["sido"] == "서울")
    cannot_lose = next(row for row in case01["segments"] if row["segment"] == "Cannot Lose")

    snapshot = {
        "source": "Verified Python aggregates. Not raw Excel or PostgreSQL.",
        "case02": {
            "title": "청년 이동 우선 지역",
            "year": case02["snapshot_year"],
            "sha256": case02["sha256"],
            "quality": f"{case02['quality_passed']}/{case02['quality_checks']}",
            "cards": [
                {
                    "label": "2025 총이동자",
                    "value": kpis["Total movers 2025"]["value"],
                    "format": "count",
                    "note": "전년 대비 −2.6%",
                },
                {
                    "label": "청년 이동자 20–39",
                    "value": kpis["Youth movers 20-39, 2025"]["value"],
                    "format": "count",
                    "note": "이동자의 45.1%",
                },
                {
                    "label": "수도권 순이동",
                    "value": kpis["Capital net vs non-capital 2025"]["value"],
                    "format": "signed",
                    "note": "비수도권 대비",
                },
                {
                    "label": "서울 청년 순이동",
                    "value": kpis["Seoul youth 20-39 net 2025"]["value"],
                    "format": "signed",
                    "note": f"20대 {int(seoul['net_20s']):+,} / 30대 {int(seoul['net_30s']):+,}",
                },
            ],
            "youth_profile": [
                {
                    "sido": row["sido"],
                    "net_youth": row["net_youth_20_39"],
                    "net_20s": row["net_20s"],
                    "net_30s": row["net_30s"],
                    "net_total": row["net_total"],
                    "typology": row["typology"],
                    "typology_ko": row["typology_ko"],
                }
                for row in case02["youth_profile"]
            ],
            "typology": case02["typology"],
            "top_od": case02["top_od"][:6],
        },
        "case01": {
            "title": "유지·재활성화 우선순위",
            "period": "2009-12-01 ~ 2011-12-09",
            "snapshot_date": case01["snapshot_date"][:10],
            "cards": [
                {
                    "label": "정상 매출",
                    "value": case01["kpis"]["Gross sales"],
                    "format": "gbp",
                    "note": "수량·가격 양수, 취소 제외",
                },
                {
                    "label": "재구매율",
                    "value": case01["kpis"]["Repeat-customer rate"],
                    "format": "pct",
                    "note": "식별 고객 기준",
                },
                {
                    "label": "고객 매출 Gini",
                    "value": case01["customer_gini"],
                    "format": "number",
                    "note": f"상위 10%가 {case01['top_10pct_customer_share']:.1%}",
                },
                {
                    "label": "Cannot Lose",
                    "value": cannot_lose["customers"],
                    "format": "count",
                    "note": "재활성화 1순위",
                },
            ],
            "segments": [
                {
                    "segment": row["segment"],
                    "action": row["action"],
                    "customers": row["customers"],
                    "revenue": row["revenue"],
                    "revenue_share": row["revenue_share"],
                    "median_recency": row["median_recency"],
                }
                for row in case01["segments"]
            ],
        },
    }
    OUT.write_text(
        "window.GDL_PUBLIC = " + json.dumps(snapshot, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
