"""Run CASE 02 validation SQL and write an evidence log.

Uses PGPASSWORD or an interactive prompt. The password is not written to the log.
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
PSQL = Path(r"D:\Program Files\PostgreSQL\18\bin\psql.exe")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate CASE 02 PostgreSQL load.")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="golden_data_lab")
    parser.add_argument("--user", default="postgres")
    parser.add_argument(
        "--log",
        type=Path,
        default=CASE_DIR / "evidence" / f"validation_{datetime.now().strftime('%Y%m%d')}.log",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = os.environ.get("PGPASSWORD") or getpass.getpass(
        f"PostgreSQL password for {args.user}: "
    )
    os.environ["PGPASSWORD"] = password
    if not PSQL.is_file():
        raise FileNotFoundError(PSQL)

    args.log.parent.mkdir(parents=True, exist_ok=True)
    sql_path = CASE_DIR / "sql" / "02_validate_load.sql"
    env = os.environ.copy()
    env["PGCLIENTENCODING"] = "UTF8"
    completed = subprocess.run(
        [
            str(PSQL),
            "-X",
            "-h", args.host,
            "-p", str(args.port),
            "-U", args.user,
            "-d", args.database,
            "-v", "ON_ERROR_STOP=1",
            "-f", str(sql_path),
            "-L", str(args.log),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    combined = (completed.stdout or "") + (completed.stderr or "")
    full_log = args.log.with_name(args.log.stem + "_full.log")
    full_log.write_text(combined, encoding="utf-8")
    print(f"wrote {args.log}")
    print(f"wrote {full_log}")
    if completed.returncode != 0:
        print(combined[-2000:], file=sys.stderr)
        print("VALIDATION FAILED", file=sys.stderr)
        return completed.returncode
    if "PASS: source, audit, and PostgreSQL migration tables reconcile" not in combined:
        # NOTICE may be on stderr; also check the -L log
        log_text = args.log.read_text(encoding="utf-8", errors="replace")
        if "PASS:" not in combined and "PASS:" not in log_text:
            print(combined[-2000:], file=sys.stderr)
            print("VALIDATION FAILED: PASS notice missing", file=sys.stderr)
            return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
