"""
MOSDAC Timestamp Matcher

Scans the four product directories, extracts timestamps from filenames,
and matches observations across products.

Filename format: 3SIMG_{DDMMMYYYY}_{HHMM}_L1C_ASIA_MER_V01R00.h5
Example: 3SIMG_28AUG2026_0600_L1C_ASIA_MER_V01R00.h5

Timestamp key: 28AUG2026_0600
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCT_DIRS = {
    "l1c": "3SIMG_L1C_ASIA_MER",
    "ctp": "3SIMG_L2B_CTP",
    "hem": "3SIMG_L2B_HEM",
    "sst": "3SIMG_L2B_SST",
}

TIMESTAMP_PATTERN = re.compile(r"3SIMG_(\d{2}[A-Z]{3}\d{4})_(\d{4})_")

# Month abbreviation to number
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


# ---------------------------------------------------------------------------
# Timestamp Parsing
# ---------------------------------------------------------------------------

def parse_timestamp_from_filename(filename: str) -> tuple[str, datetime] | None:
    """
    Extract timestamp from MOSDAC filename.

    Returns:
        (timestamp_key, datetime_obj) or None if not matched

    timestamp_key format: "28AUG2026_0600"
    datetime_obj: timezone-aware UTC datetime
    """
    match = TIMESTAMP_PATTERN.search(filename)
    if not match:
        return None

    date_str = match.group(1)  # e.g., "28AUG2026"
    time_str = match.group(2)  # e.g., "0600"

    try:
        day = int(date_str[:2])
        month_str = date_str[2:5].upper()
        year = int(date_str[5:])
        month = MONTH_MAP.get(month_str)
        if month is None:
            return None

        hour = int(time_str[:2])
        minute = int(time_str[2:])

        dt = datetime(year, month, day, hour, minute)
        timestamp_key = f"{date_str}_{time_str}"

        return timestamp_key, dt
    except (ValueError, KeyError):
        return None


def timestamp_key_to_iso(timestamp_key: str) -> str:
    """Convert timestamp key to ISO format string."""
    dt = parse_timestamp_from_filename(f"3SIMG_{timestamp_key}_DUMMY.h5")
    if dt:
        return dt[1].isoformat() + "Z"
    return "unknown"


# ---------------------------------------------------------------------------
# Directory Scanning
# ---------------------------------------------------------------------------

def scan_product_directory(product_dir: Path) -> dict[str, Path]:
    """
    Scan a product directory for .h5 files and return timestamp -> filepath mapping.

    Handles nested structure: product_dir/YYYY/DDMMM/*.h5
    """
    result = {}

    if not product_dir.exists():
        logger.warning(f"Product directory does not exist: {product_dir}")
        return result

    for h5_file in product_dir.rglob("*.h5"):
        parsed = parse_timestamp_from_filename(h5_file.name)
        if parsed:
            timestamp_key, _ = parsed
            if timestamp_key in result:
                logger.warning(f"Duplicate timestamp {timestamp_key} in {product_dir.name}: {h5_file.name}")
            result[timestamp_key] = h5_file
        else:
            logger.debug(f"Could not parse timestamp from: {h5_file.name}")

    logger.info(f"Scanned {product_dir.name}: {len(result)} files")
    return result


def scan_all_products(base_dir: Path) -> dict[str, dict[str, Path]]:
    """
    Scan all four product directories.

    Returns:
        {product: {timestamp_key: filepath}}
    """
    result = {}
    for product, dirname in PRODUCT_DIRS.items():
        product_path = base_dir / dirname
        result[product] = scan_product_directory(product_path)
    return result


# ---------------------------------------------------------------------------
# Timestamp Matching
# ---------------------------------------------------------------------------

def match_timestamps(product_files: dict[str, dict[str, Path]]) -> list[dict[str, Any]]:
    """
    Match timestamps across all four products.

    Returns list of observation dicts:
    {
        "timestamp_key": "28AUG2026_0600",
        "timestamp_iso": "2026-08-28T06:00:00Z",
        "l1c": Path or None,
        "ctp": Path or None,
        "hem": Path or None,
        "sst": Path or None,
        "complete": bool,
        "missing": list[str]
    }
    """
    # Collect all unique timestamps
    all_timestamps = set()
    for product_files_dict in product_files.values():
        all_timestamps.update(product_files_dict.keys())

    observations = []
    for ts_key in sorted(all_timestamps):
        obs = {
            "timestamp_key": ts_key,
            "timestamp_iso": timestamp_key_to_iso(ts_key),
            "l1c": product_files["l1c"].get(ts_key),
            "ctp": product_files["ctp"].get(ts_key),
            "hem": product_files["hem"].get(ts_key),
            "sst": product_files["sst"].get(ts_key),
        }

        # Check completeness
        missing = [p for p in ["l1c", "ctp", "hem", "sst"] if obs[p] is None]
        obs["missing"] = missing
        obs["complete"] = len(missing) == 0

        observations.append(obs)

    complete_count = sum(1 for o in observations if o["complete"])
    logger.info(f"Matched {len(observations)} timestamps: {complete_count} complete, {len(observations) - complete_count} incomplete")

    return observations


def filter_complete(observations: list[dict]) -> list[dict]:
    """Return only complete observations (all four products present)."""
    return [o for o in observations if o["complete"]]


def filter_incomplete(observations: list[dict]) -> list[dict]:
    """Return only incomplete observations."""
    return [o for o in observations if not o["complete"]]


# ---------------------------------------------------------------------------
# Manifest Generation
# ---------------------------------------------------------------------------

def generate_manifest(observations: list[dict], output_path: Path = None) -> dict:
    """
    Generate a manifest JSON for the matched observations.

    If output_path provided, write to file.
    Returns the manifest dict.
    """
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_observations": len(observations),
        "complete_observations": sum(1 for o in observations if o["complete"]),
        "incomplete_observations": sum(1 for o in observations if not o["complete"]),
        "observations": [],
    }

    for obs in observations:
        manifest["observations"].append({
            "timestamp_key": obs["timestamp_key"],
            "timestamp_iso": obs["timestamp_iso"],
            "products": {
                "l1c": str(obs["l1c"]) if obs["l1c"] else None,
                "ctp": str(obs["ctp"]) if obs["ctp"] else None,
                "hem": str(obs["hem"]) if obs["hem"] else None,
                "sst": str(obs["sst"]) if obs["sst"] else None,
            },
            "complete": obs["complete"],
            "missing": obs["missing"],
        })

    if output_path:
        import json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Manifest written to: {output_path}")

    return manifest


# ---------------------------------------------------------------------------
# Main Matching Function
# ---------------------------------------------------------------------------

def scan_and_match(base_dir: Path, output_manifest: Path = None) -> list[dict]:
    """
    Full pipeline: scan all products, match timestamps, optionally save manifest.

    Returns list of observation dicts.
    """
    product_files = scan_all_products(base_dir)
    observations = match_timestamps(product_files)

    if output_manifest:
        generate_manifest(observations, output_manifest)

    return observations


# ---------------------------------------------------------------------------
# CLI Helper
# ---------------------------------------------------------------------------

def print_manifest_summary(observations: list[dict]) -> None:
    """Print a human-readable summary of matched observations."""
    complete = filter_complete(observations)
    incomplete = filter_incomplete(observations)

    print(f"\n{'='*60}")
    print("TIMESTAMP MATCHING SUMMARY")
    print(f"{'='*60}")
    print(f"Total timestamps found: {len(observations)}")
    print(f"Complete (all 4 products): {len(complete)}")
    print(f"Incomplete: {len(incomplete)}")

    if incomplete:
        print("\nIncomplete observations:")
        for obs in incomplete:
            missing = ", ".join(obs["missing"])
            print(f"  {obs['timestamp_key']}: missing {missing}")

    if complete:
        print("\nComplete observations (first 10):")
        for obs in complete[:10]:
            print(f"  {obs['timestamp_key']} ({obs['timestamp_iso']})")
        if len(complete) > 10:
            print(f"  ... and {len(complete) - 10} more")

    print(f"{'='*60}\n")