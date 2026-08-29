"""Download the official 2025 domestic migration statistical annex."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

from constants import (
    EXPECTED_SHA256,
    EXPECTED_SIZE_BYTES,
    FALLBACK_DOWNLOAD_URL,
    PRIMARY_DOWNLOAD_URL,
    RAW_FILE_NAME,
)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GoldenDataLab/1.0"}


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


def download_official_annex(output_path: Path | None = None) -> Path:
    case_dir = Path(__file__).resolve().parents[1]
    dest = output_path or case_dir / "data" / "raw" / RAW_FILE_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for url in (PRIMARY_DOWNLOAD_URL, FALLBACK_DOWNLOAD_URL):
        try:
            print(f"Downloading from {url}")
            _download(url, dest)
            digest = sha256_file(dest)
            size = dest.stat().st_size
            print(f"Saved {dest} ({size:,} bytes)")
            print(f"SHA-256 {digest}")
            if size != EXPECTED_SIZE_BYTES or digest != EXPECTED_SHA256:
                raise ValueError(
                    f"Checksum mismatch: size={size} sha256={digest}"
                )
            return dest
        except Exception as exc:  # noqa: BLE001 - try fallback source
            last_error = exc
            print(f"Download failed: {exc}")
    raise RuntimeError(f"Could not download a verified annex: {last_error}")


if __name__ == "__main__":
    try:
        download_official_annex()
    except Exception as exc:
        print(f"DOWNLOAD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
