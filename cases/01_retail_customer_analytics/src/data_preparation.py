"""Reusable data preparation for CASE 01 retail analysis notebooks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = {
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
}

DUPLICATE_KEY_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]


@dataclass
class PreparedRetailData:
    """Purpose-specific dataframes built from the preserved raw workbook."""

    retail_df: pd.DataFrame
    sales_analysis_df: pd.DataFrame
    customer_analysis_df: pd.DataFrame
    returns_df: pd.DataFrame
    sheet_row_counts: dict[str, int]


def find_case_dir(start: Path | None = None) -> Path:
    """Find the CASE 01 directory from the repository root or a child folder."""

    start_path = (start or Path.cwd()).resolve()
    candidates = [
        start_path,
        start_path.parent,
        start_path / "cases" / "01_retail_customer_analytics",
    ]
    for candidate in candidates:
        if (candidate / "data" / "raw" / "online_retail_II.xlsx").exists():
            return candidate
    raise FileNotFoundError(
        "online_retail_II.xlsx를 찾지 못했습니다. 저장소 루트 또는 CASE 01 폴더에서 실행하세요."
    )


def count_exact_duplicate_extras(frame: pd.DataFrame) -> int:
    """Count duplicate extras using the SQL-aligned transaction columns."""

    return int(
        frame.duplicated(subset=DUPLICATE_KEY_COLUMNS, keep="first").sum()
    )


def add_invoice_key(frame: pd.DataFrame) -> pd.DataFrame:
    """Identify orders by source sheet plus invoice number."""

    result = frame.copy()
    result["Invoice_Key"] = (
        result["Source_Sheet"].astype("string") + "|" + result["Invoice"].astype("string")
    )
    return result


def flag_mismatch_mask(frame: pd.DataFrame) -> pd.Series:
    """Rows where cancelled-invoice and negative-quantity flags disagree."""

    return frame["Is_Cancelled_Invoice"] != frame["Is_Negative_Quantity"]


def drop_exact_duplicate_extras(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the first row of each SQL-aligned duplicate group."""

    return frame.loc[~frame.duplicated(subset=DUPLICATE_KEY_COLUMNS, keep="first")].copy()


def _normalize_retail_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()

    for column in ["Invoice", "StockCode", "Description", "Country", "Source_Sheet"]:
        normalized[column] = normalized[column].astype("string").str.strip()

    normalized["InvoiceDate"] = pd.to_datetime(
        normalized["InvoiceDate"], errors="coerce"
    )
    normalized["Quantity"] = pd.to_numeric(normalized["Quantity"], errors="coerce")
    normalized["Price"] = pd.to_numeric(normalized["Price"], errors="coerce")

    customer_id_numeric = pd.to_numeric(normalized["Customer ID"], errors="coerce")
    fractional_customer_id = (
        customer_id_numeric.notna() & customer_id_numeric.mod(1).ne(0)
    )
    if fractional_customer_id.any():
        raise ValueError("소수부가 있는 Customer ID가 발견되었습니다. 원본 값을 확인하세요.")
    normalized["Customer ID"] = customer_id_numeric.astype("Int64").astype("string")

    normalized["Is_Cancelled_Invoice"] = (
        normalized["Invoice"].str.upper().str.startswith("C", na=False)
    )
    normalized["Is_Negative_Quantity"] = normalized["Quantity"].lt(0)
    normalized["Is_Cancelled_or_Returned"] = (
        normalized["Is_Cancelled_Invoice"]
        | normalized["Is_Negative_Quantity"]
    )
    normalized["Total_Revenue"] = normalized["Quantity"] * normalized["Price"]
    return normalized


def prepare_retail_frames(
    sheet_frames: dict[str, pd.DataFrame],
    *,
    expected_raw_rows: int | None = None,
    expected_duplicate_extras: int | None = None,
) -> PreparedRetailData:
    """Validate, combine, normalize, and split workbook sheets by analysis purpose."""

    if not sheet_frames:
        raise ValueError("분석할 Excel 시트가 없습니다.")

    for sheet_name, frame in sheet_frames.items():
        missing_columns = EXPECTED_COLUMNS.difference(frame.columns)
        if missing_columns:
            raise ValueError(f"{sheet_name}: 필수 컬럼 누락 {sorted(missing_columns)}")

    sheet_row_counts = {name: len(frame) for name, frame in sheet_frames.items()}
    combined = pd.concat(
        [
            frame.assign(Source_Sheet=sheet_name)
            for sheet_name, frame in sheet_frames.items()
        ],
        ignore_index=True,
    )
    retail_df = _normalize_retail_frame(combined)
    return apply_purpose_splits(
        retail_df,
        sheet_row_counts=sheet_row_counts,
        expected_raw_rows=expected_raw_rows,
        expected_duplicate_extras=expected_duplicate_extras,
    )


def apply_purpose_splits(
    retail_df: pd.DataFrame,
    *,
    sheet_row_counts: dict[str, int] | None = None,
    expected_raw_rows: int | None = None,
    expected_duplicate_extras: int | None = None,
) -> PreparedRetailData:
    """Split a normalized retail frame into purpose-specific populations."""

    valid_sales_mask = (
        retail_df["Invoice"].notna()
        & retail_df["StockCode"].notna()
        & retail_df["InvoiceDate"].notna()
        & retail_df["Quantity"].gt(0)
        & retail_df["Price"].gt(0)
        & ~retail_df["Is_Cancelled_or_Returned"]
    )
    sales_analysis_df = (
        retail_df.loc[valid_sales_mask]
        .sort_values(["InvoiceDate", "Invoice", "StockCode"], kind="stable")
        .reset_index(drop=True)
    )
    customer_analysis_df = (
        sales_analysis_df.loc[sales_analysis_df["Customer ID"].notna()]
        .copy()
        .reset_index(drop=True)
    )
    returns_df = (
        retail_df.loc[retail_df["Is_Cancelled_or_Returned"]].copy().reset_index(drop=True)
    )

    if expected_raw_rows is not None and len(retail_df) != expected_raw_rows:
        raise AssertionError(
            f"원본 행 수 불일치: expected={expected_raw_rows:,}, actual={len(retail_df):,}"
        )
    duplicate_extras = count_exact_duplicate_extras(retail_df)
    if (
        expected_duplicate_extras is not None
        and duplicate_extras != expected_duplicate_extras
    ):
        raise AssertionError(
            "중복 추가 행 수 불일치: "
            f"expected={expected_duplicate_extras:,}, actual={duplicate_extras:,}"
        )

    assert sales_analysis_df["Quantity"].gt(0).all()
    assert sales_analysis_df["Price"].gt(0).all()
    assert sales_analysis_df["Total_Revenue"].gt(0).all()
    assert not sales_analysis_df["Is_Cancelled_or_Returned"].any()
    assert sales_analysis_df["InvoiceDate"].notna().all()
    assert customer_analysis_df["Customer ID"].notna().all()

    return PreparedRetailData(
        retail_df=retail_df,
        sales_analysis_df=sales_analysis_df,
        customer_analysis_df=customer_analysis_df,
        returns_df=returns_df,
        sheet_row_counts=sheet_row_counts or {},
    )


def load_and_prepare_retail_data(raw_path: Path) -> PreparedRetailData:
    """Load both source sheets and apply the verified CASE 01 data contract."""

    excel_file = pd.ExcelFile(raw_path, engine="openpyxl")
    sheet_frames = pd.read_excel(excel_file, sheet_name=None)
    return prepare_retail_frames(
        sheet_frames,
        expected_raw_rows=1_067_371,
        expected_duplicate_extras=34_335,
    )
