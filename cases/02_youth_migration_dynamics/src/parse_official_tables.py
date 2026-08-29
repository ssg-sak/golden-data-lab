"""Parse the official 2025 domestic-migration statistical annex into tidy frames.

The Excel file is a formatted press workbook, not a database extract. Values are
read as published. The raw workbook is never rewritten.

OD orientation (locked by reconciliation, not by the ambiguous header):
row = destination (전입지), column = origin (전출지).
Diagonal cells are intra-sido moves. The 전국 column is the destination total.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from constants import (
    AGE_LABEL_MAP,
    CAPITAL_SIDOS,
    EXPECTED_SHA256,
    EXPECTED_SIZE_BYTES,
    GENDER_MAP,
    REQUIRED_SHEETS,
    SIDOS,
    SNAPSHOT_YEAR,
    STALE_SHEET,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_source_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != EXPECTED_SIZE_BYTES:
        raise ValueError(f"Unexpected size {size}; expected {EXPECTED_SIZE_BYTES}")
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Unexpected SHA-256 {digest}")
    return {"path": str(path), "sha256": digest, "size_bytes": size}


def _is_blank(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    text = str(value).strip()
    return text == "" or text == "-" or text == "－"


def parse_number(value: Any) -> float | None:
    if _is_blank(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if pd.isna(value):
            return None
        return float(value)
    text = str(value).strip().replace(",", "").replace(" ", "").replace("\u00a0", "")
    if text in {"-", "－", "*"}:
        return None
    return float(text)


def parse_int(value: Any) -> int | None:
    number = parse_number(value)
    if number is None:
        return None
    if abs(number - round(number)) > 1e-6:
        raise ValueError(f"Expected integer-like value, got {value!r}")
    return int(round(number))


def parse_year(value: Any) -> int | None:
    if _is_blank(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    return int(match.group(0))


def normalize_age(value: Any) -> str | None:
    if _is_blank(value):
        return None
    text = str(value).strip()
    text = text.replace("․", "-").replace("·", "-").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", "", text)
    text = text.replace("세이상", "+").replace("세", "")
    if text == "계":
        return "total"
    if text not in AGE_LABEL_MAP:
        raise ValueError(f"Unrecognized age label: {value!r} -> {text!r}")
    return AGE_LABEL_MAP[text]


def normalize_gender(value: Any) -> str | None:
    if _is_blank(value):
        return None
    text = str(value).strip()
    if text not in GENDER_MAP:
        raise ValueError(f"Unrecognized gender label: {value!r}")
    return GENDER_MAP[text]


def forward_fill_labels(series: pd.Series) -> pd.Series:
    cleaned = series.map(lambda value: None if _is_blank(value) else str(value).strip())
    return cleaned.ffill()


def read_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")


def inspect_workbook(path: Path) -> dict[str, Any]:
    verify_source_file(path)
    xl = pd.ExcelFile(path, engine="openpyxl")
    missing = [name for name in REQUIRED_SHEETS if name not in xl.sheet_names]
    if missing:
        raise ValueError(f"Missing required sheets: {missing}")
    extra = [name for name in xl.sheet_names if name not in REQUIRED_SHEETS]
    return {
        "sheet_names": list(xl.sheet_names),
        "extra_sheets": extra,
        "has_stale_monthly_sheet": STALE_SHEET in xl.sheet_names,
    }


def parse_national_movers(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "1. 성별 이동자수 및 이동률 추이")
    rows = []
    for idx in range(6, len(frame)):
        left = frame.iat[idx, 0]
        if _is_blank(left):
            continue
        text = str(left).strip()
        if text.startswith("*"):
            continue
        year = parse_year(left)
        if year is None:
            continue
        movers_total = parse_int(frame.iat[idx, 1])
        if movers_total is None:
            continue
        rows.append(
            {
                "year": year,
                "movers_total": parse_int(frame.iat[idx, 1]),
                "yoy_change": parse_int(frame.iat[idx, 2]),
                "yoy_pct": parse_number(frame.iat[idx, 3]),
                "movers_male": parse_int(frame.iat[idx, 4]),
                "movers_female": parse_int(frame.iat[idx, 5]),
                "sex_ratio_movers": parse_number(frame.iat[idx, 6]),
                "mobility_rate_total": parse_number(frame.iat[idx, 7]),
                "mobility_rate_yoy": parse_number(frame.iat[idx, 8]),
                "mobility_rate_male": parse_number(frame.iat[idx, 9]),
                "mobility_rate_female": parse_number(frame.iat[idx, 10]),
                "sex_ratio_rate": parse_number(frame.iat[idx, 11]),
                "intra_sido_movers": parse_int(frame.iat[idx, 12]),
                "intra_sido_rate": parse_number(frame.iat[idx, 13]),
                "inter_sido_movers": parse_int(frame.iat[idx, 14]),
                "inter_sido_rate": parse_number(frame.iat[idx, 15]),
                "source_sheet": "1. 성별 이동자수 및 이동률 추이",
                "source_row_number": idx + 1,
            }
        )
    return pd.DataFrame(rows)


def parse_age_movers(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "2. 성 및 연령별 이동자수 및 이동률추이")
    years: list[tuple[int, int]] = []
    for col in range(2, frame.shape[1]):
        year = parse_year(frame.iat[2, col])
        if year is not None:
            years.append((year, col))
    gender_filled = forward_fill_labels(frame.iloc[:, 0])
    rows = []
    for idx in range(5, len(frame)):
        gender = normalize_gender(gender_filled.iat[idx])
        age = normalize_age(frame.iat[idx, 1])
        if gender is None or age is None:
            continue
        for year, col in years:
            rows.append(
                {
                    "year": year,
                    "gender": gender,
                    "age_group": age,
                    "movers": parse_int(frame.iat[idx, col]),
                    "mobility_rate": parse_number(frame.iat[idx, col + 1]),
                    "source_sheet": "2. 성 및 연령별 이동자수 및 이동률추이",
                    "source_row_number": idx + 1,
                }
            )
    return pd.DataFrame(rows)


def _sido_header(frame: pd.DataFrame, header_row: int, start_col: int) -> list[tuple[int, str]]:
    pairs = []
    for col in range(start_col, frame.shape[1]):
        label = frame.iat[header_row, col]
        if _is_blank(label):
            continue
        name = str(label).strip()
        if name in {"전국", "시도 / 연령", "시도 /       연령"}:
            continue
        if name not in SIDOS and name != "전국":
            continue
        pairs.append((col, name))
    return pairs


def parse_sido_yearly(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "3. 시도별이동자추이")
    sido_cols = [(col, str(frame.iat[2, col]).strip()) for col in range(2, 20)]
    sido_cols = [(col, name) for col, name in sido_cols if name in SIDOS or name == "전국"]
    measure = None
    rows = []
    for idx in range(4, len(frame)):
        left = frame.iat[idx, 0]
        if not _is_blank(left):
            text = str(left).strip()
            if text in {"전입", "전출", "순이동"}:
                measure = {"전입": "in", "전출": "out", "순이동": "net"}[text]
        year = parse_year(frame.iat[idx, 1])
        if measure is None or year is None:
            continue
        for col, sido in sido_cols:
            rows.append(
                {
                    "year": year,
                    "sido": sido,
                    "measure": measure,
                    "value": parse_int(frame.iat[idx, col]),
                    "source_sheet": "3. 시도별이동자추이",
                    "source_row_number": idx + 1,
                }
            )
    return pd.DataFrame(rows)


def parse_sido_gender_2025(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "4. 시도및성별")
    gender_filled = forward_fill_labels(frame.iloc[:, 0])
    rows = []
    for idx in range(6, len(frame)):
        gender = normalize_gender(gender_filled.iat[idx])
        sido = None if _is_blank(frame.iat[idx, 1]) else str(frame.iat[idx, 1]).strip()
        if gender is None or sido not in {"전국", *SIDOS}:
            continue
        rows.append(
            {
                "year": SNAPSHOT_YEAR,
                "gender": gender,
                "sido": sido,
                "in_total": parse_int(frame.iat[idx, 2]),
                "out_total": parse_int(frame.iat[idx, 3]),
                "intra_sigungu": parse_int(frame.iat[idx, 4]),
                "inter_sigungu_in": parse_int(frame.iat[idx, 5]),
                "inter_sigungu_out": parse_int(frame.iat[idx, 6]),
                "inter_sido_in": parse_int(frame.iat[idx, 7]),
                "inter_sido_out": parse_int(frame.iat[idx, 8]),
                "net": parse_int(frame.iat[idx, 9]),
                "in_rate": parse_number(frame.iat[idx, 10]),
                "out_rate": parse_number(frame.iat[idx, 11]),
                "intra_sigungu_rate": parse_number(frame.iat[idx, 12]),
                "inter_sigungu_in_rate": parse_number(frame.iat[idx, 13]),
                "inter_sigungu_out_rate": parse_number(frame.iat[idx, 14]),
                "inter_sido_in_rate": parse_number(frame.iat[idx, 15]),
                "inter_sido_out_rate": parse_number(frame.iat[idx, 16]),
                "net_rate": parse_number(frame.iat[idx, 17]),
                "source_sheet": "4. 시도및성별",
                "source_row_number": idx + 1,
            }
        )
    return pd.DataFrame(rows)


def parse_sido_age_net_2025(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "5. 시도 및 연령별 순이동")
    sido_cols = [(col, str(frame.iat[2, col]).strip()) for col in range(2, 19)]
    sido_cols = [(col, name) for col, name in sido_cols if name in SIDOS]
    gender_filled = forward_fill_labels(frame.iloc[:, 0])
    rows = []
    for idx in range(4, len(frame)):
        gender = normalize_gender(gender_filled.iat[idx])
        age = normalize_age(frame.iat[idx, 1])
        if gender is None or age is None:
            continue
        for col, sido in sido_cols:
            rows.append(
                {
                    "year": SNAPSHOT_YEAR,
                    "gender": gender,
                    "sido": sido,
                    "age_group": age,
                    "net": parse_int(frame.iat[idx, col]),
                    "is_capital": sido in CAPITAL_SIDOS,
                    "source_sheet": "5. 시도 및 연령별 순이동",
                    "source_row_number": idx + 1,
                }
            )
    return pd.DataFrame(rows)


def _parse_od_matrix(path: Path, sheet_name: str, value_name: str) -> pd.DataFrame:
    frame = read_sheet(path, sheet_name)
    origin_cols = [(col, str(frame.iat[2, col]).strip()) for col in range(2, 21)]
    origin_cols = [(col, name) for col, name in origin_cols if name in {"전국", *SIDOS}]
    gender_filled = forward_fill_labels(frame.iloc[:, 0])
    rows = []
    for idx in range(4, len(frame)):
        gender = normalize_gender(gender_filled.iat[idx])
        dest = None if _is_blank(frame.iat[idx, 1]) else str(frame.iat[idx, 1]).strip()
        if gender is None or dest not in {"전국", *SIDOS}:
            continue
        for col, origin in origin_cols:
            rows.append(
                {
                    "year": SNAPSHOT_YEAR,
                    "gender": gender,
                    "destination": dest,
                    "origin": origin,
                    value_name: parse_int(frame.iat[idx, col]),
                    "is_intra": dest == origin and dest != "전국",
                    "source_sheet": sheet_name,
                    "source_row_number": idx + 1,
                }
            )
    return pd.DataFrame(rows)


def parse_od_movers_2025(path: Path) -> pd.DataFrame:
    return _parse_od_matrix(path, "6.전입출지별(이동자)", "movers")


def parse_od_net_2025(path: Path) -> pd.DataFrame:
    return _parse_od_matrix(path, "7.전입출지별(순이동)", "net")


def parse_capital_yearly(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "8.수도권 인구이동 추이")
    rows = []
    for idx in range(5, len(frame)):
        year = parse_year(frame.iat[idx, 0])
        net = parse_int(frame.iat[idx, 1])
        if year is None or net is None:
            continue
        rows.append(
            {
                "year": year,
                "net": net,
                "in_from_noncapital": parse_int(frame.iat[idx, 2]),
                "in_seoul": parse_int(frame.iat[idx, 3]),
                "in_incheon": parse_int(frame.iat[idx, 4]),
                "in_gyeonggi": parse_int(frame.iat[idx, 5]),
                "out_to_noncapital": parse_int(frame.iat[idx, 6]),
                "out_seoul": parse_int(frame.iat[idx, 7]),
                "out_incheon": parse_int(frame.iat[idx, 8]),
                "out_gyeonggi": parse_int(frame.iat[idx, 9]),
                "source_sheet": "8.수도권 인구이동 추이",
                "source_row_number": idx + 1,
            }
        )
    return pd.DataFrame(rows)


def parse_monthly(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "9.월별")
    current_year = None
    rows = []
    for idx in range(6, len(frame)):
        label = frame.iat[idx, 0]
        if _is_blank(label):
            continue
        text = str(label).strip()
        if text.startswith("*"):
            continue
        year = parse_year(text)
        month = None
        if "년" in text and "월" not in text:
            current_year = year
            period_type = "annual"
        else:
            month_match = re.search(r"(\d{1,2})월", text)
            if month_match is None:
                continue
            if year is not None and "." in text:
                current_year = year
            month = int(month_match.group(1))
            period_type = "monthly"
            year = current_year
        if year is None:
            continue
        rows.append(
            {
                "year": year,
                "month": month,
                "period_type": period_type,
                "movers_total": parse_int(frame.iat[idx, 1]),
                "yoy_same_month_pct": parse_number(frame.iat[idx, 2]),
                "yoy_cumulative_pct": parse_number(frame.iat[idx, 3]),
                "intra_sido_movers": parse_int(frame.iat[idx, 4]),
                "inter_sido_movers": parse_int(frame.iat[idx, 5]),
                "mobility_rate": parse_number(frame.iat[idx, 6]),
                "mobility_rate_yoy": parse_number(frame.iat[idx, 7]),
                "intra_sido_rate": parse_number(frame.iat[idx, 8]),
                "inter_sido_rate": parse_number(frame.iat[idx, 9]),
                "source_sheet": "9.월별",
                "source_row_number": idx + 1,
            }
        )
    return pd.DataFrame(rows)


REASON_MAP = {
    "계": "total",
    "직업": "job",
    "가족": "family",
    "주택": "housing",
    "교육": "education",
    "주거환경": "residential_environment",
    "자연환경": "natural_environment",
    "기타": "other",
}


def parse_reason_2025(path: Path) -> pd.DataFrame:
    frame = read_sheet(path, "10. 시도 및 전입사유별")
    sido_cols = [(col, str(frame.iat[2, col]).strip()) for col in range(2, 21)]
    sido_cols = [(col, name) for col, name in sido_cols if name in {"전국", *SIDOS}]
    block = None
    rows = []
    for idx in range(3, len(frame)):
        left = frame.iat[idx, 0]
        if not _is_blank(left):
            text = re.sub(r"\s+", "", str(left))
            mapping = {
                "전입자(시도내+시도간)": "in_all",
                "전출자(시도내+시도간)": "out_all",
                "전입자(시도간)": "in_inter_sido",
                "전출자(시도간)": "out_inter_sido",
                "순이동": "net",
            }
            if text in mapping:
                block = mapping[text]
        reason_label = None if _is_blank(frame.iat[idx, 1]) else str(frame.iat[idx, 1]).strip()
        if block is None or reason_label not in REASON_MAP:
            continue
        for col, sido in sido_cols:
            rows.append(
                {
                    "year": SNAPSHOT_YEAR,
                    "sido": sido,
                    "flow": block,
                    "reason": REASON_MAP[reason_label],
                    "reason_label_ko": reason_label,
                    "value": parse_int(frame.iat[idx, col]),
                    "source_sheet": "10. 시도 및 전입사유별",
                    "source_row_number": idx + 1,
                }
            )
    return pd.DataFrame(rows)


@dataclass
class OfficialTables:
    workbook: dict[str, Any]
    national_movers: pd.DataFrame
    age_movers: pd.DataFrame
    sido_yearly: pd.DataFrame
    sido_gender_2025: pd.DataFrame
    sido_age_net_2025: pd.DataFrame
    od_movers_2025: pd.DataFrame
    od_net_2025: pd.DataFrame
    capital_yearly: pd.DataFrame
    monthly: pd.DataFrame
    reason_2025: pd.DataFrame


def load_official_tables(path: Path) -> OfficialTables:
    inspect = inspect_workbook(path)
    return OfficialTables(
        workbook=inspect,
        national_movers=parse_national_movers(path),
        age_movers=parse_age_movers(path),
        sido_yearly=parse_sido_yearly(path),
        sido_gender_2025=parse_sido_gender_2025(path),
        sido_age_net_2025=parse_sido_age_net_2025(path),
        od_movers_2025=parse_od_movers_2025(path),
        od_net_2025=parse_od_net_2025(path),
        capital_yearly=parse_capital_yearly(path),
        monthly=parse_monthly(path),
        reason_2025=parse_reason_2025(path),
    )
