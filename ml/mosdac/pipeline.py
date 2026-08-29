"""
MOSDAC Processing Pipeline

Orchestrates the full MOSDAC data processing workflow:
1. Timestamp matching across four products
2. HDF5 reading with metadata preservation
3. ROI subsetting and geospatial handling
4. Feature extraction
5. NPZ output

Supports:
- Single timestamp test
- Batch processing of all matched timestamps
"""

import argparse
import gc
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Local imports
from .hdf5_reader import read_l1c, read_ctp, read_hem, read_sst, read_product
from .timestamp_matcher import (
    scan_and_match, filter_complete, filter_incomplete, print_manifest_summary,
    generate_manifest, timestamp_key_to_iso
)
from .preprocess import (
    extract_features, save_features, print_feature_summary,
    DEFAULT_LAT_MIN, DEFAULT_LAT_MAX, DEFAULT_LON_MIN, DEFAULT_LON_MAX,
)
from .geospatial import (
    extract_l1c_grid, extract_latlon_grid, print_grid_comparison,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve data directory relative to this file's location (project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_DIR = _PROJECT_ROOT / "data_download"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "ml" / "data" / "mosdac_processed"
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"

# Default ROI (Bay of Bengal)
DEFAULT_ROI = {
    "lat_min": DEFAULT_LAT_MIN,
    "lat_max": DEFAULT_LAT_MAX,
    "lon_min": DEFAULT_LON_MIN,
    "lon_max": DEFAULT_LON_MAX,
}

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO"):
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce h5py noise
    logging.getLogger("h5py").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Single Timestamp Processing
# ---------------------------------------------------------------------------

def process_single_timestamp(
    timestamp_key: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    roi: dict = None,
    verbose: bool = True,
) -> dict | None:
    """
    Process a single timestamp through the full pipeline.

    Args:
        timestamp_key: e.g., "28AUG2026_0600"
        data_dir: root directory with product subdirectories
        output_dir: where to save NPZ feature files
        roi: dict with lat_min, lat_max, lon_min, lon_max
        verbose: print detailed output

    Returns:
        Feature dict if successful, None if failed
    """
    if roi is None:
        roi = DEFAULT_ROI

    logger = logging.getLogger(__name__)
    logger.info(f"Processing timestamp: {timestamp_key}")

    # Find files for this timestamp
    product_files = {}
    for product, dirname in {"l1c": "3SIMG_L1C_ASIA_MER", "ctp": "3SIMG_L2B_CTP",
                              "hem": "3SIMG_L2B_HEM", "sst": "3SIMG_L2B_SST"}.items():
        product_path = data_dir / dirname
        found = False
        for h5_file in product_path.rglob("*.h5"):
            if timestamp_key in h5_file.name:
                product_files[product] = h5_file
                found = True
                break
        if not found:
            product_files[product] = None
            logger.warning(f"  {product.upper()}: NOT FOUND for {timestamp_key}")

    # Check completeness
    missing = [p for p, f in product_files.items() if f is None]
    if missing:
        logger.warning(f"  Incomplete observation - missing: {missing}")

    # Read each available product
    matched_data = {
        "timestamp_key": timestamp_key,
        "timestamp": timestamp_key_to_iso(timestamp_key),
    }

    grids = {}

    # L1C
    if product_files["l1c"]:
        try:
            matched_data["l1c"] = read_l1c(product_files["l1c"])
            grids["l1c"] = extract_l1c_grid(matched_data["l1c"])
            if verbose:
                print(f"  L1C: {matched_data['l1c']['raw_counts']['IMG_TIR1'].shape} - {len(matched_data['l1c']['raw_counts'])} bands")
        except Exception as e:
            logger.error(f"  L1C read failed: {e}")
            matched_data["l1c"] = None

    # CTP
    if product_files["ctp"]:
        try:
            matched_data["ctp"] = read_ctp(product_files["ctp"])
            grids["ctp"] = extract_latlon_grid(matched_data["ctp"])
            if verbose:
                for ds in ["CTP", "CTT", "EFF_EMISS"]:
                    if ds in matched_data["ctp"].get("data", {}):
                        d = matched_data["ctp"]["data"][ds]["physical"]
                        print(f"  CTP.{ds}: {d.shape} dtype={d.dtype}")
        except Exception as e:
            logger.error(f"  CTP read failed: {e}")
            matched_data["ctp"] = None

    # HEM
    if product_files["hem"]:
        try:
            matched_data["hem"] = read_hem(product_files["hem"])
            grids["hem"] = extract_latlon_grid(matched_data["hem"])
            if verbose and "HEM" in matched_data["hem"].get("data", {}):
                d = matched_data["hem"]["data"]["HEM"]["physical"]
                print(f"  HEM: {d.shape} dtype={d.dtype}")
        except Exception as e:
            logger.error(f"  HEM read failed: {e}")
            matched_data["hem"] = None

    # SST
    if product_files["sst"]:
        try:
            matched_data["sst"] = read_sst(product_files["sst"])
            grids["sst"] = extract_latlon_grid(matched_data["sst"])
            if verbose:
                for ds in ["SST_FCT", "SST_REG", "SST_VAR"]:
                    if ds in matched_data["sst"].get("data", {}):
                        d = matched_data["sst"]["data"][ds]["physical"]
                        print(f"  SST.{ds}: {d.shape} dtype={d.dtype}")
        except Exception as e:
            logger.error(f"  SST read failed: {e}")
            matched_data["sst"] = None

    # Print grid comparison
    if grids and verbose:
        print_grid_comparison(grids)

    # Extract features
    if any(matched_data.get(p) for p in ["l1c", "ctp", "hem", "sst"]):
        features = extract_features(
            matched_data,
            lat_min=roi["lat_min"],
            lat_max=roi["lat_max"],
            lon_min=roi["lon_min"],
            lon_max=roi["lon_max"],
        )

        if verbose:
            print_feature_summary(features)

        # Save NPZ
        output_path = output_dir / f"features_{timestamp_key}.npz"
        save_features(features, output_path)

        # Also save grid info
        grid_info = {}
        for name, grid in grids.items():
            grid_info[name] = {
                "shape": grid.shape,
                "bounds": {
                    "lat_min": grid.bounds.lat_min,
                    "lat_max": grid.bounds.lat_max,
                    "lon_min": grid.bounds.lon_min,
                    "lon_max": grid.bounds.lon_max,
                } if grid.bounds else None,
            }

        grid_path = output_dir / f"grid_{timestamp_key}.json"
        with open(grid_path, "w") as f:
            json.dump(grid_info, f, indent=2, default=str)

        logger.info(f"Completed: {timestamp_key}")
        return features

    logger.error(f"No data available for {timestamp_key}")
    return None


def test_timestamp(
    timestamp_key: str = "28AUG2026_0600",
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    roi: dict = None,
) -> bool:
    """
    Test processing for a single timestamp with full verbose output.

    Returns True if successful.
    """
    print(f"\n{'='*70}")
    print(f"MOSDAC SINGLE TIMESTAMP TEST: {timestamp_key}")
    print(f"{'='*70}")

    setup_logging("DEBUG")

    try:
        result = process_single_timestamp(
            timestamp_key=timestamp_key,
            data_dir=data_dir,
            output_dir=output_dir,
            roi=roi,
            verbose=True,
        )
        success = result is not None

        if success:
            print(f"\n[OK] TEST PASSED: {timestamp_key}")
        else:
            print(f"\n[FAIL] TEST FAILED: {timestamp_key}")

        return success

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Test failed with exception: {e}")
        print(f"\n[ERROR] TEST ERROR: {e}")
        return False


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

def process_batch(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    manifest_path: Path = DEFAULT_MANIFEST,
    roi: dict = None,
    only_complete: bool = True,
) -> dict:
    """
    Process all matched timestamps in batch mode.

    Processes one timestamp at a time to control memory.

    Returns summary dict.
    """
    logger = logging.getLogger(__name__)

    if roi is None:
        roi = DEFAULT_ROI

    # Scan and match
    observations = scan_and_match(data_dir, manifest_path)
    print_manifest_summary(observations)

    # Filter
    if only_complete:
        to_process = filter_complete(observations)
        logger.info(f"Processing {len(to_process)} complete observations")
    else:
        to_process = observations
        logger.info(f"Processing all {len(to_process)} observations")

    # Process each timestamp
    results = {
        "total": len(observations),
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "complete_input": len(filter_complete(observations)),
        "incomplete_input": len(filter_incomplete(observations)),
        "output_dir": str(output_dir),
        "timestamps": [],
    }

    for i, obs in enumerate(to_process):
        ts_key = obs["timestamp_key"]
        logger.info(f"[{i+1}/{len(to_process)}] Processing {ts_key}")

        try:
            result = process_single_timestamp(
                timestamp_key=ts_key,
                data_dir=data_dir,
                output_dir=output_dir,
                roi=roi,
                verbose=False,
            )

            if result:
                results["processed"] += 1
                results["timestamps"].append({
                    "timestamp_key": ts_key,
                    "status": "success",
                })
            else:
                results["failed"] += 1
                results["timestamps"].append({
                    "timestamp_key": ts_key,
                    "status": "failed",
                })

        except Exception as e:
            logger.error(f"Failed to process {ts_key}: {e}")
            results["failed"] += 1
            results["timestamps"].append({
                "timestamp_key": ts_key,
                "status": "error",
                "error": str(e),
            })

        # Explicit memory cleanup
        gc.collect()

    # Save batch summary
    summary_path = output_dir / "batch_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"Batch complete: {results['processed']} succeeded, {results['failed']} failed")
    logger.info(f"Summary saved to: {summary_path}")

    return results


# ---------------------------------------------------------------------------
# CLI Entry Points
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MOSDAC INSAT-3DS Data Processing Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Test single timestamp
    test_parser = subparsers.add_parser("test", help="Test single timestamp")
    test_parser.add_argument("timestamp", nargs="?", default="28AUG2026_0600",
                             help="Timestamp key (e.g., 28AUG2026_0600)")
    test_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                             help="Root data directory")
    test_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                             help="Output directory for NPZ files")
    test_parser.add_argument("--lat-min", type=float, default=DEFAULT_LAT_MIN)
    test_parser.add_argument("--lat-max", type=float, default=DEFAULT_LAT_MAX)
    test_parser.add_argument("--lon-min", type=float, default=DEFAULT_LON_MIN)
    test_parser.add_argument("--lon-max", type=float, default=DEFAULT_LON_MAX)
    test_parser.add_argument("--log-level", default="INFO",
                             choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    # Batch process
    batch_parser = subparsers.add_parser("batch", help="Batch process all timestamps")
    batch_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    batch_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    batch_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    batch_parser.add_argument("--lat-min", type=float, default=DEFAULT_LAT_MIN)
    batch_parser.add_argument("--lat-max", type=float, default=DEFAULT_LAT_MAX)
    batch_parser.add_argument("--lon-min", type=float, default=DEFAULT_LON_MIN)
    batch_parser.add_argument("--lon-max", type=float, default=DEFAULT_LON_MAX)
    batch_parser.add_argument("--include-incomplete", action="store_true",
                              help="Also process incomplete observations")
    batch_parser.add_argument("--log-level", default="INFO",
                              choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    # Scan only
    scan_parser = subparsers.add_parser("scan", help="Scan and match timestamps only")
    scan_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    scan_parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    scan_parser.add_argument("--log-level", default="INFO",
                             choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Configure logging
    setup_logging(args.log_level)

    try:
        if args.command == "test":
            roi = {
                "lat_min": args.lat_min,
                "lat_max": args.lat_max,
                "lon_min": args.lon_min,
                "lon_max": args.lon_max,
            }
            success = test_timestamp(
                timestamp_key=args.timestamp,
                data_dir=args.data_dir,
                output_dir=args.output_dir,
                roi=roi,
            )
            return 0 if success else 1

        elif args.command == "batch":
            roi = {
                "lat_min": args.lat_min,
                "lat_max": args.lat_max,
                "lon_min": args.lon_min,
                "lon_max": args.lon_max,
            }
            results = process_batch(
                data_dir=args.data_dir,
                output_dir=args.output_dir,
                manifest_path=args.manifest,
                roi=roi,
                only_complete=not args.include_incomplete,
            )
            print(f"\n{'='*60}")
            print("BATCH PROCESSING COMPLETE")
            print(f"{'='*60}")
            print(f"Total timestamps found:     {results['total']}")
            print(f"Complete input observations: {results['complete_input']}")
            print(f"Incomplete input observations: {results['incomplete_input']}")
            print(f"Successfully processed:     {results['processed']}")
            print(f"Failed:                     {results['failed']}")
            print(f"Output directory:           {results['output_dir']}")
            print(f"{'='*60}")
            return 0 if results["failed"] == 0 else 1

        elif args.command == "scan":
            observations = scan_and_match(args.data_dir, args.manifest)
            print_manifest_summary(observations)
            return 0

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Pipeline error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())