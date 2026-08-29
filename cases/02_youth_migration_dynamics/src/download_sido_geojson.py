"""Download KOSTAT 2018 sido boundaries and write a 17-sido join file."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

import geopandas as gpd

from constants import (
    EXPECTED_GEOJSON_SHA256,
    EXPECTED_GEOJSON_SIZE_BYTES,
    GEOJSON_DOWNLOAD_URL,
    KOSTAT_CODE_TO_SIDO,
    PREPARED_GEOJSON_FILE_NAME,
    RAW_GEOJSON_FILE_NAME,
    SIDOS,
)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GoldenDataLab/1.0"}
SIMPLIFY_DEGREES = 0.008


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def prepare_sido_boundaries(raw_path: Path, output_path: Path) -> Path:
    frame = gpd.read_file(raw_path)
    if frame.crs is None:
        frame = frame.set_crs(4326)
    else:
        frame = frame.to_crs(4326)
    frame["geometry"] = frame.geometry.make_valid()
    frame["code"] = frame["code"].astype(str).str.zfill(2)
    missing = set(KOSTAT_CODE_TO_SIDO) - set(frame["code"])
    extra = set(frame["code"]) - set(KOSTAT_CODE_TO_SIDO)
    if missing or extra:
        raise ValueError(f"GeoJSON sido codes mismatch: missing={missing} extra={extra}")
    frame["sido"] = frame["code"].map(KOSTAT_CODE_TO_SIDO)
    if set(frame["sido"]) != set(SIDOS):
        raise ValueError(f"Prepared sido names {sorted(frame['sido'])} != SIDOS")
    frame["geometry"] = frame.geometry.make_valid().simplify(SIMPLIFY_DEGREES, preserve_topology=True)
    prepared = frame.loc[:, ["sido", "code", "name_eng", "geometry"]].copy()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_file(output_path, driver="GeoJSON")
    return output_path


def download_sido_geojson(output_path: Path | None = None) -> Path:
    case_dir = Path(__file__).resolve().parents[1]
    dest = output_path or case_dir / "data" / "raw" / RAW_GEOJSON_FILE_NAME
    print(f"Downloading from {GEOJSON_DOWNLOAD_URL}")
    _download(GEOJSON_DOWNLOAD_URL, dest)
    digest = sha256_file(dest)
    size = dest.stat().st_size
    print(f"Saved {dest} ({size:,} bytes)")
    print(f"SHA-256 {digest}")
    if size != EXPECTED_GEOJSON_SIZE_BYTES or digest != EXPECTED_GEOJSON_SHA256:
        raise ValueError(f"Checksum mismatch: size={size} sha256={digest}")
    prepared = case_dir / "data" / "geo" / PREPARED_GEOJSON_FILE_NAME
    prepare_sido_boundaries(dest, prepared)
    print(f"Wrote {prepared} ({prepared.stat().st_size:,} bytes)")
    return prepared


if __name__ == "__main__":
    try:
        download_sido_geojson()
    except Exception as exc:
        print(f"GEOJSON DOWNLOAD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
