"""
MOSDAC Preprocessing - Feature Extraction

Extracts satellite-derived features from matched L1C, CTP, HEM, SST observations
within the region of interest (ROI).

Output: NPZ files with feature arrays, timestamps, and metadata.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

from .geospatial import (
    DEFAULT_LAT_MIN, DEFAULT_LAT_MAX, DEFAULT_LON_MIN, DEFAULT_LON_MAX,
    create_roi_mask, subset_to_roi, extract_l1c_grid, extract_latlon_grid,
)
from .hdf5_reader import compute_basic_stats

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature Extraction Functions
# ---------------------------------------------------------------------------

def extract_l1c_features(l1c_data: dict, lat: np.ndarray, lon: np.ndarray,
                         lat_min: float, lat_max: float,
                         lon_min: float, lon_max: float) -> dict[str, Any]:
    """
    Extract features from L1C data within ROI.

    Returns dict with statistics for each band.
    """
    features = {
        "bands": {},
        "roi_shape": None,
    }

    # Create ROI mask
    mask = create_roi_mask(lat, lon, lat_min, lat_max, lon_min, lon_max)
    features["roi_shape"] = list(mask.shape)
    features["roi_pixel_count"] = int(mask.sum())

    raw_counts = l1c_data.get("raw_counts", {})

    for band_name, band_data in raw_counts.items():
        # band_data shape: (1, H, W) -> squeeze to (H, W)
        if band_data.ndim == 3 and band_data.shape[0] == 1:
            band_2d = band_data[0]
        else:
            band_2d = band_data

        # Apply ROI subsetting
        sub_data, sub_lat, sub_lon, sub_mask = subset_to_roi(
            band_2d, lat, lon, lat_min, lat_max, lon_min, lon_max
        )

        # Compute statistics on raw counts
        stats = compute_basic_stats(sub_data, f"L1C_{band_name}_raw")
        stats["band"] = band_name
        stats["calibration_available"] = band_name in l1c_data.get("calibration", {})

        # Also compute on calibrated brightness temperature for TIR bands
        calib = l1c_data.get("calibration", {}).get(band_name, {})
        if "temp_lut" in calib:
            try:
                from .hdf5_reader import calibrate_l1c_to_temp
                temp_data = calibrate_l1c_to_temp(band_2d, calib)
                sub_temp, _, _, _ = subset_to_roi(
                    temp_data, lat, lon, lat_min, lat_max, lon_min, lon_max
                )
                temp_stats = compute_basic_stats(sub_temp, f"L1C_{band_name}_temp")
                stats["brightness_temp"] = temp_stats
            except Exception as e:
                logger.warning(f"Could not calibrate {band_name} to temp: {e}")

        features["bands"][band_name] = stats

    return features


def extract_ctp_features(ctp_data: dict,
                         lat_min: float, lat_max: float,
                         lon_min: float, lon_max: float) -> dict[str, Any]:
    """
    Extract features from CTP data within ROI.

    Key datasets: CTP (hPa), CTT (K), EFF_EMISS (unitless)
    """
    features = {
        "datasets": {},
        "roi_shape": None,
    }

    coords = ctp_data.get("coordinates", {})
    lat = coords.get("lat")
    lon = coords.get("lon")

    if lat is None or lon is None:
        logger.warning("CTP: No lat/lon coordinates available")
        return features

    mask = create_roi_mask(lat, lon, lat_min, lat_max, lon_min, lon_max)
    features["roi_shape"] = list(mask.shape)
    features["roi_pixel_count"] = int(mask.sum())

    for ds_name in ["CTP", "CTT", "EFF_EMISS"]:
        if ds_name in ctp_data.get("data", {}):
            ds_info = ctp_data["data"][ds_name]
            physical = ds_info["physical"]

            # Subset to ROI
            sub_data, _, _, _ = subset_to_roi(
                physical, lat, lon, lat_min, lat_max, lon_min, lon_max
            )

            stats = compute_basic_stats(sub_data, f"CTP_{ds_name}")
            stats["units"] = ds_info.get("units")
            stats["long_name"] = ds_info.get("long_name")
            features["datasets"][ds_name] = stats

    return features


def extract_hem_features(hem_data: dict,
                         lat_min: float, lat_max: float,
                         lon_min: float, lon_max: float) -> dict[str, Any]:
    """
    Extract features from HEM data within ROI.

    Key dataset: HEM (mm/hr precipitation rate)
    """
    features = {
        "datasets": {},
        "roi_shape": None,
    }

    coords = hem_data.get("coordinates", {})
    lat = coords.get("lat")
    lon = coords.get("lon")

    if lat is None or lon is None:
        logger.warning("HEM: No lat/lon coordinates available")
        return features

    mask = create_roi_mask(lat, lon, lat_min, lat_max, lon_min, lon_max)
    features["roi_shape"] = list(mask.shape)
    features["roi_pixel_count"] = int(mask.sum())

    if "HEM" in hem_data.get("data", {}):
        ds_info = hem_data["data"]["HEM"]
        physical = ds_info["physical"]

        sub_data, _, _, _ = subset_to_roi(
            physical, lat, lon, lat_min, lat_max, lon_min, lon_max
        )

        stats = compute_basic_stats(sub_data, "HEM_precipitation")
        stats["units"] = ds_info.get("units", "mm/hr")
        stats["long_name"] = ds_info.get("long_name")

        # Additional precipitation-specific metrics
        valid = sub_data[~np.isnan(sub_data)]
        if valid.size > 0:
            stats["high_rain_threshold_mmhr"] = 10.0
            stats["high_rain_pixels"] = int((valid > 10.0).sum())
            stats["high_rain_fraction"] = float((valid > 10.0).mean())
            stats["very_high_rain_pixels"] = int((valid > 50.0).sum())
            stats["very_high_rain_fraction"] = float((valid > 50.0).mean())

        features["datasets"]["HEM"] = stats

    return features


def extract_sst_features(sst_data: dict,
                         lat_min: float, lat_max: float,
                         lon_min: float, lon_max: float) -> dict[str, Any]:
    """
    Extract features from SST data within ROI.

    Key datasets: SST_FCT, SST_REG, SST_VAR (all in Kelvin)
    """
    features = {
        "datasets": {},
        "roi_shape": None,
    }

    coords = sst_data.get("coordinates", {})
    lat = coords.get("lat")
    lon = coords.get("lon")

    if lat is None or lon is None:
        logger.warning("SST: No lat/lon coordinates available")
        return features

    mask = create_roi_mask(lat, lon, lat_min, lat_max, lon_min, lon_max)
    features["roi_shape"] = list(mask.shape)
    features["roi_pixel_count"] = int(mask.sum())

    for ds_name in ["SST_FCT", "SST_REG", "SST_VAR"]:
        if ds_name in sst_data.get("data", {}):
            ds_info = sst_data["data"][ds_name]
            physical = ds_info["physical"]

            sub_data, _, _, _ = subset_to_roi(
                physical, lat, lon, lat_min, lat_max, lon_min, lon_max
            )

            stats = compute_basic_stats(sub_data, f"SST_{ds_name}")
            stats["units"] = ds_info.get("units", "K")
            stats["long_name"] = ds_info.get("long_name")
            features["datasets"][ds_name] = stats

    # Compute SST gradient (spatial variability) if SST_REG available
    if "SST_REG" in sst_data.get("data", {}):
        ds_info = sst_data["data"]["SST_REG"]
        physical = ds_info["physical"]
        sub_data, sub_lat, sub_lon, _ = subset_to_roi(
            physical, lat, lon, lat_min, lat_max, lon_min, lon_max
        )

        # Simple gradient magnitude
        if sub_data.ndim == 2:
            gy, gx = np.gradient(sub_data)
            grad_mag = np.sqrt(gx**2 + gy**2)
            grad_stats = compute_basic_stats(grad_mag, "SST_gradient_mag")
            grad_stats["units"] = "K/pixel"
            features["datasets"]["SST_GRADIENT"] = grad_stats

    return features


# ---------------------------------------------------------------------------
# Main Feature Extraction
# ---------------------------------------------------------------------------

def extract_features(matched_data: dict,
                     lat_min: float = DEFAULT_LAT_MIN,
                     lat_max: float = DEFAULT_LAT_MAX,
                     lon_min: float = DEFAULT_LON_MIN,
                     lon_max: float = DEFAULT_LON_MAX) -> dict[str, Any]:
    """
    Extract features from all four products for a matched observation.

    Args:
        matched_data: dict with keys 'l1c', 'ctp', 'hem', 'sst' containing
                      data from hdf5_reader functions
        lat_min, lat_max, lon_min, lon_max: ROI bounds

    Returns:
        Feature dict ready for NPZ saving
    """
    result = {
        "timestamp": matched_data.get("timestamp"),
        "timestamp_key": matched_data.get("timestamp_key"),
        "roi_bounds": {
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max,
        },
        "products": {},
    }

    # --- L1C ---
    if matched_data.get("l1c"):
        l1c = matched_data["l1c"]
        grid = extract_l1c_grid(l1c)
        if grid.lat is not None and grid.lon is not None:
            result["products"]["l1c"] = extract_l1c_features(
                l1c, grid.lat, grid.lon, lat_min, lat_max, lon_min, lon_max
            )
            result["products"]["l1c"]["grid_bounds"] = {
                "lat_min": grid.bounds.lat_min if grid.bounds else None,
                "lat_max": grid.bounds.lat_max if grid.bounds else None,
                "lon_min": grid.bounds.lon_min if grid.bounds else None,
                "lon_max": grid.bounds.lon_max if grid.bounds else None,
            } if grid.bounds else None
        else:
            logger.warning("L1C: Could not extract lat/lon grid, skipping feature extraction")
            result["products"]["l1c"] = {"error": "no lat/lon grid"}

    # --- CTP ---
    if matched_data.get("ctp"):
        result["products"]["ctp"] = extract_ctp_features(
            matched_data["ctp"], lat_min, lat_max, lon_min, lon_max
        )

    # --- HEM ---
    if matched_data.get("hem"):
        result["products"]["hem"] = extract_hem_features(
            matched_data["hem"], lat_min, lat_max, lon_min, lon_max
        )

    # --- SST ---
    if matched_data.get("sst"):
        result["products"]["sst"] = extract_sst_features(
            matched_data["sst"], lat_min, lat_max, lon_min, lon_max
        )

    return result


def features_to_flat_array(features: dict) -> tuple[np.ndarray, list[str]]:
    """
    Convert nested feature dict to flat feature array for ML.

    Returns:
        (feature_array, feature_names)
    """
    values = []
    names = []

    def flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                flatten(v, f"{prefix}{k}_")
        elif isinstance(obj, (int, float, np.number)) and not isinstance(obj, bool):
            names.append(prefix.rstrip("_"))
            values.append(float(obj))
        elif isinstance(obj, (list, tuple)) and len(obj) == 1:
            # Single-element list
            names.append(prefix.rstrip("_"))
            values.append(float(obj[0]))

    # Extract only the statistical values
    for product_name, product_data in features.get("products", {}).items():
        if "error" in product_data:
            continue

        # L1C bands
        if "bands" in product_data:
            for band_name, band_stats in product_data["bands"].items():
                for stat_name, stat_val in band_stats.items():
                    if isinstance(stat_val, (int, float, np.number)) and not isinstance(stat_val, bool):
                        names.append(f"{product_name}_{band_name}_{stat_name}")
                        values.append(float(stat_val))
                    elif isinstance(stat_val, dict) and "brightness_temp" in stat_val:
                        bt = stat_val["brightness_temp"]
                        for bt_stat, bt_val in bt.items():
                            if isinstance(bt_val, (int, float, np.number)) and not isinstance(bt_val, bool):
                                names.append(f"{product_name}_{band_name}_bt_{bt_stat}")
                                values.append(float(bt_val))

        # CTP/HEM/SST datasets
        if "datasets" in product_data:
            for ds_name, ds_stats in product_data["datasets"].items():
                for stat_name, stat_val in ds_stats.items():
                    if isinstance(stat_val, (int, float, np.number)) and not isinstance(stat_val, bool):
                        names.append(f"{product_name}_{ds_name}_{stat_name}")
                        values.append(float(stat_val))

    return np.array(values, dtype=np.float32), names


# ---------------------------------------------------------------------------
# Save/Load
# ---------------------------------------------------------------------------

def save_features(features: dict, output_path: Path) -> None:
    """
    Save features to NPZ file.

    Stores:
    - feature_array: flat array of all numeric features
    - feature_names: list of feature names
    - timestamp: ISO timestamp string
    - timestamp_key: original timestamp key
    - roi_bounds: dict
    - full_features: JSON-serializable full feature dict (as string)
    """
    import json

    feature_array, feature_names = features_to_flat_array(features)

    # Prepare metadata
    metadata = {
        "timestamp": features.get("timestamp"),
        "timestamp_key": features.get("timestamp_key"),
        "roi_bounds": features.get("roi_bounds"),
        "feature_count": len(feature_names),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        feature_array=feature_array,
        feature_names=np.array(feature_names, dtype=object),
        metadata=json.dumps(metadata),
        full_features=json.dumps(features, default=str),
    )

    logger.info(f"Saved features to {output_path}: {len(feature_names)} features")


def load_features(filepath: Path) -> dict:
    """Load features from NPZ file."""
    import json

    data = np.load(filepath, allow_pickle=True)
    return {
        "feature_array": data["feature_array"],
        "feature_names": data["feature_names"].tolist(),
        "metadata": json.loads(str(data["metadata"])),
        "full_features": json.loads(str(data["full_features"])),
    }


# ---------------------------------------------------------------------------
# Summary Printing
# ---------------------------------------------------------------------------

def print_feature_summary(features: dict) -> None:
    """Print human-readable feature summary."""
    print(f"\n{'='*60}")
    print("FEATURE EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Timestamp: {features.get('timestamp')}")
    print(f"ROI: {features.get('roi_bounds')}")

    for product_name, product_data in features.get("products", {}).items():
        print(f"\n  {product_name.upper()}:")
        if "error" in product_data:
            print(f"    ERROR: {product_data['error']}")
            continue

        if "bands" in product_data:
            for band_name, stats in product_data["bands"].items():
                if isinstance(stats, dict) and "mean" in stats:
                    print(f"    {band_name}: mean={stats.get('mean'):.2f}, "
                          f"range=[{stats.get('min'):.2f}, {stats.get('max'):.2f}], "
                          f"NaN%={stats.get('nan_pct', 0):.1f}%")

        if "datasets" in product_data:
            for ds_name, stats in product_data["datasets"].items():
                if isinstance(stats, dict) and "mean" in stats:
                    print(f"    {ds_name}: mean={stats.get('mean'):.2f}, "
                          f"range=[{stats.get('min'):.2f}, {stats.get('max'):.2f}], "
                          f"NaN%={stats.get('nan_pct', 0):.1f}%")

    flat, names = features_to_flat_array(features)
    print(f"\nTotal features for ML: {len(names)}")
    print(f"{'='*60}\n")