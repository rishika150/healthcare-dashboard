"""Step 1: download the UCI 'Diabetes 130-US Hospitals 1999-2008' dataset (CC BY 4.0)."""
from __future__ import annotations

import io
import urllib.request
import zipfile

from common import IDS_CSV, RAW_CSV, RAW_DIR

URL = "https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip"


def main() -> None:
    if RAW_CSV.exists() and IDS_CSV.exists():
        print(f"  raw files already present in {RAW_DIR}")
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {URL}")
    with urllib.request.urlopen(URL, timeout=120) as resp:
        payload = resp.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for member in zf.namelist():
            name = member.rsplit("/", 1)[-1]
            if name in (RAW_CSV.name, IDS_CSV.name):
                (RAW_DIR / name).write_bytes(zf.read(member))
    print(f"  saved {RAW_CSV.name} and {IDS_CSV.name}")


if __name__ == "__main__":
    main()
