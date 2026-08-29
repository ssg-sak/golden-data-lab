"""Run CASE 02 parse through dashboard and write evidence artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from constants import EXPECTED_SHA256, RAW_FILE_NAME, SNAPSHOT_YEAR  # noqa: E402
from data_preparation import load_and_prepare  # noqa: E402
from data_quality import run_quality_checks  # noqa: E402
from decision_dashboard import save_decision_dashboard, save_youth_net_figure  # noqa: E402
from kpi_segmentation import run_kpi_segmentation  # noqa: E402
from parse_official_tables import sha256_file, verify_source_file  # noqa: E402
from statistical_analysis import run_statistical_analysis  # noqa: E402


def _json_ready(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def main() -> int:
    raw_path = CASE_DIR / "data" / "raw" / RAW_FILE_NAME
    source = verify_source_file(raw_path)
    prepared = load_and_prepare(raw_path)
    tables = prepared.tables
    quality = run_quality_checks(tables, prepared)
    stats = run_statistical_analysis(tables, prepared)
    kpis = run_kpi_segmentation(tables, prepared)

    processed = CASE_DIR / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    exports = {
        "youth_profile_2025.csv": kpis.youth_profile,
        "typology_summary.csv": kpis.typology_summary,
        "priority.csv": kpis.priority,
        "top_od_2025.csv": kpis.top_od,
        "youth_mobility_2005_2025.csv": prepared.youth_mobility,
        "capital_yearly.csv": tables.capital_yearly,
        "inter_sido_od_2025.csv": prepared.inter_sido,
        "quality_checks.csv": quality,
        "kpi.csv": kpis.values,
    }
    for name, frame in exports.items():
        frame.to_csv(processed / name, index=False, encoding="utf-8-sig")

    evidence = CASE_DIR / "evidence"
    figures = evidence / "figures"
    dashboard = evidence / "dashboard"
    save_youth_net_figure(kpis.youth_profile, figures / "01_youth_net_2025.png")
    save_decision_dashboard(tables, prepared, stats, kpis, dashboard / "01_one_page_decision.png")

    failed = quality.loc[~quality["passed"]]
    summary = {
        "source_file": RAW_FILE_NAME,
        "sha256": source["sha256"],
        "expected_sha256": EXPECTED_SHA256,
        "snapshot_year": SNAPSHOT_YEAR,
        "quality_checks": int(len(quality)),
        "quality_passed": int(quality["passed"].sum()),
        "quality_failed": json.loads(failed.to_json(orient="records", force_ascii=False)),
        "kpis": json.loads(kpis.values.to_json(orient="records", force_ascii=False)),
        "typology": json.loads(kpis.typology_summary.to_json(orient="records", force_ascii=False)),
        "youth_profile": json.loads(kpis.youth_profile.to_json(orient="records", force_ascii=False)),
        "priority": json.loads(kpis.priority.to_json(orient="records", force_ascii=False)),
        "top_od": json.loads(kpis.top_od.to_json(orient="records", force_ascii=False)),
        "concentration": stats.concentration,
        "sensitivity_sign_flips": int(stats.sensitivity["sign_flips"].sum()),
        "hypothesis_summary": json.loads(stats.hypothesis_summary.to_json(orient="records", force_ascii=False)),
        "h1": {key: _json_ready(value) for key, value in stats.h1.items()},
        "h2": {key: _json_ready(value) for key, value in stats.h2.items()},
        "h3": {key: _json_ready(value) for key, value in stats.h3.items()},
        "h4": {key: _json_ready(value) for key, value in stats.h4.items()},
        "capital_flows": json.loads(prepared.capital_flows.to_json(orient="records", force_ascii=False)),
    }
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"quality {summary['quality_passed']}/{summary['quality_checks']} passed")
    print(f"wrote {evidence / 'analysis_summary.json'}")
    if summary["quality_failed"]:
        print("FAILED CHECKS", summary["quality_failed"])
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ANALYSIS FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
