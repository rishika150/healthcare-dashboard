"""Run the whole pipeline: download -> MySQL load -> SQL clean/validate -> pandas validate/export."""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

STEPS = [
    ("01_download", "Download raw data"),
    ("02_load_mysql", "Load raw CSVs into MySQL"),
    ("03_clean_sql", "Clean and validate in SQL"),
    ("04_pandas_validate_export", "Validate in pandas and export"),
]


def main() -> None:
    for module, label in STEPS:
        print(f"\n== {label} ==")
        started = time.time()
        importlib.import_module(module).main()
        print(f"  done in {time.time() - started:.1f}s")
    print("\nPipeline finished.")


if __name__ == "__main__":
    main()
