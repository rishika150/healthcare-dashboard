"""Turn a Power BI 'Export to PDF' file into one PNG per report page.

    python powerbi/pdf_to_screenshots.py path\\to\\DiabetesReadmission.pdf

Writes screenshots/powerbi-<page>.png. Needs: pip install pymupdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["overview", "age", "diagnosis", "risk-drivers"]


def main() -> None:
    pdf = Path(sys.argv[1])
    out = ROOT / "screenshots"
    out.mkdir(exist_ok=True)
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc):
            name = PAGES[i] if i < len(PAGES) else f"page-{i + 1}"
            # Scale so a 1280-wide report page renders at about 1600 px
            zoom = 1600 / page.rect.width
            page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(out / f"powerbi-{name}.png")
            print(f"  powerbi-{name}.png")


if __name__ == "__main__":
    main()
