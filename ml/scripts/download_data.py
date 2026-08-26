"""Download IBTrACS North Indian Basin CSV (v04r01)."""

import urllib.request
import sys
from pathlib import Path

URL = (
    "https://www.ncei.noaa.gov/data/"
    "international-best-track-archive-for-climate-stewardship-ibtracs/"
    "v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
DEST = RAW_DIR / "ibtracs_NI.csv"


def main() -> None:
    if DEST.exists():
        print(f"Already downloaded: {DEST}")
        return

    print(f"Downloading IBTrACS North Indian Basin CSV...")
    print(f"  Source: {URL}")
    print(f"  Dest:   {DEST}")
    try:
        urllib.request.urlretrieve(URL, DEST)
    except Exception as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        print(
            "\nManual download instructions:\n"
            f"  1. Open {URL}\n"
            "  2. Save as ibtracs_NI.list.v04r01.csv\n"
            f"  3. Place in: {RAW_DIR}/ibtracs_NI.csv",
            file=sys.stderr,
        )
        sys.exit(1)

    size_mb = DEST.stat().st_size / (1024 * 1024)
    print(f"Downloaded: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
