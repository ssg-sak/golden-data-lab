"""Execute CASE 02 notebooks and save cell outputs."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


CASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOKS = [
    CASE_DIR / "notebooks" / "01_data_quality_check.ipynb",
    CASE_DIR / "notebooks" / "02_python_eda.ipynb",
    CASE_DIR / "notebooks" / "03_statistical_analysis.ipynb",
    CASE_DIR / "notebooks" / "04_kpi_segmentation.ipynb",
    CASE_DIR / "notebooks" / "05_decision_dashboard.ipynb",
]


def main() -> int:
    for path in NOTEBOOKS:
        print(f"Executing {path.name}...", flush=True)
        notebook = nbformat.read(path, as_version=4)
        client = NotebookClient(
            notebook,
            timeout=1200,
            kernel_name="python3",
            cwd=str(CASE_DIR),
        )
        client.execute()
        nbformat.write(notebook, path)
        print(f"Wrote executed {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
