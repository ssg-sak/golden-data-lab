"""Load parsed CASE 02 annex tables into PostgreSQL with an audit row."""

from __future__ import annotations

import argparse
import csv
import getpass
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR / "src"))

from constants import EXPECTED_SHA256, LOADER_VERSION, RAW_FILE_NAME  # noqa: E402
from parse_official_tables import load_official_tables, sha256_file  # noqa: E402


TABLES = (
    ("national_movers_yearly", "national_movers"),
    ("age_movers_yearly", "age_movers"),
    ("sido_flow_yearly", "sido_yearly"),
    ("sido_gender_2025", "sido_gender_2025"),
    ("sido_age_net_2025", "sido_age_net_2025"),
    ("od_movers_2025", "od_movers_2025"),
    ("od_net_2025", "od_net_2025"),
    ("capital_yearly", "capital_yearly"),
    ("monthly_movers", "monthly"),
    ("reason_2025", "reason_2025"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load CASE 02 official annex into PostgreSQL.")
    parser.add_argument(
        "--source",
        type=Path,
        default=CASE_DIR / "data" / "raw" / RAW_FILE_NAME,
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="golden_data_lab")
    parser.add_argument("--user", default="postgres")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate existing migration tables before loading again.",
    )
    parser.add_argument("--profile-only", action="store_true")
    return parser.parse_args()


def _csv_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if pd.isna(value):
            return ""
        if value.is_integer():
            return int(value)
        return value
    if pd.isna(value):
        return ""
    return value


def _copy_frame(cursor: Any, table: str, frame: pd.DataFrame) -> int:
    export = frame.copy()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    for row in export.itertuples(index=False, name=None):
        writer.writerow(_csv_cell(value) for value in row)
    buffer.seek(0)
    columns = ", ".join(export.columns)
    cursor.copy_expert(
        f"COPY migration.{table} ({columns}) FROM STDIN WITH (FORMAT CSV, NULL '')",
        buffer,
    )
    return len(export)


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    tables = load_official_tables(source)
    counts = {
        db_table: len(getattr(tables, attr))
        for db_table, attr in TABLES
    }
    digest = sha256_file(source)
    print("Source verification")
    print(f"  file: {source}")
    print(f"  SHA-256: {digest}")
    print(f"  expected: {EXPECTED_SHA256}")
    for name, count in counts.items():
        print(f"  {name}: {count:,} rows")
    if digest != EXPECTED_SHA256:
        raise ValueError("SHA-256 mismatch")
    if args.profile_only:
        return 0

    password = os.environ.get("PGPASSWORD") or getpass.getpass(
        f"PostgreSQL password for {args.user}: "
    )
    started_at = datetime.now(timezone.utc)
    sql_path = CASE_DIR / "sql" / "01_create_tables.sql"
    connection = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=password,
    )
    try:
        with connection:
            with connection.cursor() as cursor:
                ddl = (
                    sql_path.read_text(encoding="utf-8")
                    .replace("BEGIN;", "")
                    .replace("COMMIT;", "")
                )
                cursor.execute(ddl)
                if args.replace:
                    cursor.execute(
                        """
                        TRUNCATE TABLE
                            migration.national_movers_yearly,
                            migration.age_movers_yearly,
                            migration.sido_flow_yearly,
                            migration.sido_gender_2025,
                            migration.sido_age_net_2025,
                            migration.od_movers_2025,
                            migration.od_net_2025,
                            migration.capital_yearly,
                            migration.monthly_movers,
                            migration.reason_2025,
                            migration.load_audit
                        RESTART IDENTITY
                        """
                    )
                else:
                    cursor.execute("SELECT count(*) FROM migration.national_movers_yearly")
                    existing = cursor.fetchone()[0]
                    if existing:
                        raise RuntimeError(
                            f"Target already contains {existing:,} rows. Use --replace after review."
                        )
                loaded = {}
                for db_table, attr in TABLES:
                    loaded[db_table] = _copy_frame(cursor, db_table, getattr(tables, attr))
                if loaded != counts:
                    raise RuntimeError(f"Row reconciliation failed: {loaded} vs {counts}")
                cursor.execute((CASE_DIR / "sql" / "03_analysis_views.sql").read_text(encoding="utf-8"))
                finished_at = datetime.now(timezone.utc)
                cursor.execute(
                    """
                    INSERT INTO migration.load_audit (
                        source_file_name, source_sha256, source_size_bytes,
                        table_row_counts, started_at, finished_at,
                        database_user, loader_version, status
                    )
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, current_user, %s, 'success')
                    RETURNING load_id, database_user
                    """,
                    (
                        source.name,
                        digest,
                        source.stat().st_size,
                        json.dumps(loaded, ensure_ascii=False),
                        started_at,
                        finished_at,
                        LOADER_VERSION,
                    ),
                )
                load_id, database_user = cursor.fetchone()
        print("Load committed successfully")
        print(f"  load_id: {load_id}")
        print(f"  database user: {database_user}")
        print("Next: run sql/02_validate_load.sql and save its output.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"LOAD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
