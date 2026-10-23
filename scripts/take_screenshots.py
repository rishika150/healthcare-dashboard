"""Capture README screenshots of the web dashboard with headless Edge or Chrome (no extra installs).

    python scripts/take_screenshots.py
"""
from __future__ import annotations

import functools
import http.server
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
PORT = 8799
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "msedge",
]


def find_browser() -> str:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    raise SystemExit("No Chrome or Edge found for headless screenshots.")


def serve() -> http.server.ThreadingHTTPServer:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

    handler = functools.partial(Quiet, directory=str(ROOT / "docs"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def shoot(browser: str, name: str, query: str, width: int, height: int) -> Path:
    path = OUT / f"{name}.png"
    subprocess.run([
        browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
        f"--window-size={width},{height}", "--virtual-time-budget=6000",
        f"--user-data-dir={tempfile.mkdtemp(prefix='shot-')}", "--no-first-run",
        f"--screenshot={path}", f"http://127.0.0.1:{PORT}/?{query}",
    ], capture_output=True, text=True, timeout=120)
    if not path.exists():
        raise SystemExit(f"Screenshot {path.name} was not written.")
    return path


def trim_bottom(path: Path) -> None:
    """Cut the empty page background below the footer."""
    img = Image.open(path).convert("RGB")
    bg = img.getpixel((img.width - 2, img.height - 2))
    px = img.load()
    bottom = img.height - 1
    while bottom > 0 and all(px[x, bottom] == bg for x in range(0, img.width, 7)):
        bottom -= 1
    img.crop((0, 0, img.width, min(img.height, bottom + 40))).save(path)


def crop(src: Path, name: str, top: int, height: int) -> None:
    img = Image.open(src)
    img.crop((0, top, img.width, min(img.height, top + height))).save(OUT / f"{name}.png")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    browser = find_browser()
    server = serve()
    try:
        full = shoot(browser, "dashboard-full", "theme=light", 1280, 7000)
        trim_bottom(full)
        crop(full, "hero", 0, 900)
        dark = shoot(browser, "dashboard-dark", "theme=dark", 1280, 7000)
        trim_bottom(dark)
        crop(dark, "hero-dark", 0, 900)
        dark.unlink()
        mobile = shoot(browser, "mobile", "theme=light", 390, 3000)
        crop(mobile, "mobile", 0, 1400)
    finally:
        server.shutdown()
    print(f"  screenshots written to {OUT}")


if __name__ == "__main__":
    main()
