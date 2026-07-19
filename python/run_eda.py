"""검증 정책 스냅샷의 데이터 품질과 핵심 분포를 재현한다."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager


matplotlib.use("Agg")

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT_DIR / "datasets" / "policy_release.json"
OUTPUT_DIR = ROOT_DIR / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"

REQUIRED_COLUMNS = (
    "district_name",
    "children_population",
    "senior_population",
    "vulnerable_population",
    "road_eta_minutes",
    "vdi",
    "latitude",
    "longitude",
)


def payload_sha256(value: Any) -> str:
    """JSON 줄바꿈과 키 순서에 영향을 받지 않는 해시를 계산한다."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_release(path: Path) -> dict[str, Any]:
    """정책 릴리스를 읽고 내부 콘텐츠 해시를 확인한다."""
    with path.open(encoding="utf-8") as file:
        release: dict[str, Any] = json.load(file)

    metadata = release["metadata"]
    expected_routes = metadata["district_count"] * (
        metadata["resource_count"] + metadata["candidate_count"]
    )
    contract = {
        "district_count": 150,
        "resource_count": 25,
        "candidate_count": 9,
        "route_count": expected_routes,
        "successful_route_count": expected_routes,
        "missing_route_count": 0,
    }
    mismatches = {
        key: {"actual": metadata.get(key), "expected": expected}
        for key, expected in contract.items()
        if metadata.get(key) != expected
    }
    if mismatches:
        raise ValueError(f"정책 데이터 계약 불일치: {mismatches}")

    for name in (
        "hospitals",
        "vulnerability",
        "candidates",
        "candidate_trace",
        "optimization",
    ):
        actual_hash = payload_sha256(release[name])
        expected_hash = metadata["content_sha256"][name]
        if actual_hash != expected_hash:
            raise ValueError(
                f"{name} 콘텐츠 해시 불일치: "
                f"expected={expected_hash}, actual={actual_hash}"
            )
    return release


def build_district_frame(release: dict[str, Any]) -> pd.DataFrame:
    """GeoJSON 속성을 분석용 행정동 테이블로 정규화한다."""
    rows = []
    for feature in release["vulnerability"]["features"]:
        properties = feature["properties"]
        rows.append(
            {
                "district_name": properties.get("adm_nm"),
                "children_population": properties.get("0~9세_인구"),
                "senior_population": properties.get("65세이상_인구"),
                "vulnerable_population": properties.get("취약인구"),
                "road_eta_minutes": properties.get("travel_time_minutes"),
                "road_distance_km": properties.get("road_distance_km"),
                "vdi": properties.get("vulnerability_index"),
                "nearest_hospital_name": properties.get("nearest_hospital_name"),
                "nearest_hospital_tier": properties.get("nearest_hospital_tier"),
                "latitude": properties.get("center_lat"),
                "longitude": properties.get("center_lng"),
            }
        )
    return pd.DataFrame(rows)


def build_quality_summary(
    district_frame: pd.DataFrame,
    risk_threshold: float,
) -> dict[str, Any]:
    """결측·중복·음수·산식 관계와 고위험 동 수를 점검한다."""
    missing_counts = {
        column: int(district_frame[column].isna().sum())
        for column in REQUIRED_COLUMNS
    }
    numeric_columns = (
        "children_population",
        "senior_population",
        "vulnerable_population",
        "road_eta_minutes",
        "road_distance_km",
        "vdi",
    )
    negative_counts = {
        column: int((district_frame[column] < 0).sum())
        for column in numeric_columns
    }
    expected_vulnerable_population = (
        district_frame["children_population"]
        + district_frame["senior_population"]
    )
    population_mismatch_count = int(
        (
            district_frame["vulnerable_population"]
            != expected_vulnerable_population
        ).sum()
    )
    return {
        "row_count": int(len(district_frame)),
        "duplicate_district_count": int(
            district_frame["district_name"].duplicated().sum()
        ),
        "missing_counts": missing_counts,
        "negative_counts": negative_counts,
        "vulnerable_population_mismatch_count": population_mismatch_count,
        "risk_threshold": risk_threshold,
        "high_risk_district_count": int(
            (district_frame["vdi"] >= risk_threshold).sum()
        ),
    }


def configure_plot_font() -> str:
    """환경에 설치된 한글 글꼴을 우선 선택한다."""
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    candidates = (
        "Malgun Gothic",
        "AppleGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
    )
    selected_font = next(
        (font for font in candidates if font in available_fonts),
        "DejaVu Sans",
    )
    plt.rc("font", family=selected_font)
    plt.rcParams["axes.unicode_minus"] = False
    return selected_font


def save_figures(district_frame: pd.DataFrame, risk_threshold: float) -> None:
    """VDI 분포와 ETA·VDI 관계를 PNG로 저장한다."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(10, 6))
    sns.histplot(district_frame["vdi"], bins=20, color="#2563eb")
    plt.axvline(
        risk_threshold,
        color="#dc2626",
        linestyle="--",
        label=f"High-risk threshold: {risk_threshold:,.2f}",
    )
    plt.title("VDI distribution across 150 administrative districts")
    plt.xlabel("VDI (vulnerable population × log(1 + road ETA))")
    plt.ylabel("Number of districts")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "vdi_distribution.png", dpi=160)
    plt.close()

    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(
        district_frame["road_eta_minutes"],
        district_frame["vdi"],
        c=district_frame["vulnerable_population"],
        cmap="viridis",
        alpha=0.8,
    )
    plt.axhline(
        risk_threshold,
        color="#dc2626",
        linestyle="--",
        label="High-risk threshold",
    )
    color_bar = plt.colorbar(scatter)
    color_bar.set_label("Vulnerable population (people)")
    plt.title("Road ETA and VDI by administrative district")
    plt.xlabel("Road ETA to nearest resource (minutes)")
    plt.ylabel("VDI")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "road_eta_vs_vdi.png", dpi=160)
    plt.close()


def write_outputs(
    release: dict[str, Any],
    district_frame: pd.DataFrame,
    quality_summary: dict[str, Any],
) -> None:
    """재현 가능한 분석 테이블과 요약 JSON을 생성한다."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    district_frame.to_csv(
        OUTPUT_DIR / "district_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    district_frame.nlargest(10, "vdi").to_csv(
        OUTPUT_DIR / "top10_risk_districts.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "analysis_version": release["metadata"]["version"],
        "population_base_month": release["metadata"]["population_base_month"],
        "quality": quality_summary,
        "descriptive_statistics": district_frame[
            [
                "children_population",
                "senior_population",
                "vulnerable_population",
                "road_eta_minutes",
                "road_distance_km",
                "vdi",
            ]
        ].describe().round(4).to_dict(),
        "top10_districts_by_vdi": district_frame.nlargest(10, "vdi")[
            ["district_name", "vulnerable_population", "road_eta_minutes", "vdi"]
        ].to_dict(orient="records"),
    }
    with (OUTPUT_DIR / "eda_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def main() -> None:
    release = load_release(INPUT_PATH)
    district_frame = build_district_frame(release)
    risk_threshold = float(release["metadata"]["risk_threshold"])
    quality_summary = build_quality_summary(district_frame, risk_threshold)

    selected_font = configure_plot_font()
    write_outputs(release, district_frame, quality_summary)
    save_figures(district_frame, risk_threshold)

    print(f"분석 버전: {release['metadata']['version']}")
    print(f"행정동: {len(district_frame)}개")
    print(f"고위험 행정동: {quality_summary['high_risk_district_count']}개")
    print(f"중복 행정동: {quality_summary['duplicate_district_count']}개")
    print(
        "필수값 결측: "
        f"{sum(quality_summary['missing_counts'].values())}개"
    )
    print(f"그래프 글꼴: {selected_font}")
    print(f"산출물: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
