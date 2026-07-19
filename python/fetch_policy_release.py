"""고정된 정책 릴리스를 내려받아 원시 파일 해시를 검증한다."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


SOURCE_COMMIT = "fc24068bff34ca475d4761563ab15b172d66ece3"
SOURCE_URL = (
    "https://raw.githubusercontent.com/ssg-sak/golden-project/"
    f"{SOURCE_COMMIT}/frontend/public/data/policy_release.json"
)
EXPECTED_SHA256 = "d7b0658c62ec2e89465bc8ebf266bb5fd198461c5d9e8d5da2c44d5b3b33cfbc"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "datasets" / "policy_release.json"


def validate_contract(payload: dict[str, object]) -> None:
    """독립 분석에서 요구하는 최소 정책 데이터 계약을 확인한다."""
    metadata = payload["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("metadata가 JSON 객체가 아닙니다.")

    expected = {
        "district_count": 150,
        "resource_count": 25,
        "candidate_count": 9,
        "route_count": 5_100,
        "successful_route_count": 5_100,
        "missing_route_count": 0,
    }
    mismatches = {
        key: (metadata.get(key), value)
        for key, value in expected.items()
        if metadata.get(key) != value
    }
    if mismatches:
        raise ValueError(f"정책 데이터 계약이 일치하지 않습니다: {mismatches}")


def main() -> None:
    with urlopen(SOURCE_URL, timeout=30) as response:  # noqa: S310 - 고정 HTTPS 원천
        raw = response.read()

    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != EXPECTED_SHA256:
        raise ValueError(
            "정책 릴리스 SHA-256이 일치하지 않습니다: "
            f"expected={EXPECTED_SHA256}, actual={actual_sha256}"
        )

    payload = json.loads(raw.decode("utf-8"))
    validate_contract(payload)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(raw)
    print(f"검증 완료: {OUTPUT_PATH}")
    print(f"SHA-256: {actual_sha256}")


if __name__ == "__main__":
    main()

