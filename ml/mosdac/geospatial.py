"""
MOSDAC Geospatial Utilities

Handles coordinate systems, projections, spatial bounds, and ROI subsetting
for the four INSAT-3DS products with different grids/resolutions.

Products have different grids:
- L1C: 1616 x 1737, Mercator (4 km), X/Y in meters
- CTP: 313 x 312, lat/lon grids (separate arrays)
- HEM: 2816 x 2805, lat/lon grids
- SST: 2816 x 2805, lat/lon grids

DOES NOT perform full reprojection/resampling in this phase.
Provides coordinate extraction, bounds calculation, and ROI masking.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    from pyproj import CRS, Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default ROI (Bay of Bengal)
# ---------------------------------------------------------------------------

DEFAULT_LAT_MIN = 5.0
DEFAULT_LAT_MAX = 25.0
DEFAULT_LON_MIN = 78.0
DEFAULT_LON_MAX = 98.0


@dataclass
class SpatialBounds:
    """Spatial bounds in lat/lon."""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def contains(self, lat: float, lon: float) -> bool:
        return self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max

    def overlaps(self, other: "SpatialBounds") -> bool:
        return not (self.lat_max < other.lat_min or self.lat_min > other.lat_max or
                    self.lon_max < other.lon_min or self.lon_min > other.lon_max)


@dataclass
class GridInfo:
    """Information about a product's grid."""
    product: str
    shape: tuple
    lat: np.ndarray | None = None
    lon: np.ndarray | None = None
    x: np.ndarray | None = None  # for Mercator
    y: np.ndarray | None = None  # for Mercator
    projection: dict | None = None
    bounds: SpatialBounds | None = None

    def __post_init__(self):
        if self.lat is not None and self.lon is not None:
            valid_lat = self.lat[~np.isnan(self.lat)]
            valid_lon = self.lon[~np.isnan(self.lon)]
            if valid_lat.size > 0 and valid_lon.size > 0:
                self.bounds = SpatialBounds(
                    lat_min=float(valid_lat.min()),
                    lat_max=float(valid_lat.max()),
                    lon_min=float(valid_lon.min()),
                    lon_max=float(valid_lon.max()),
                )


# ---------------------------------------------------------------------------
# Coordinate Extraction
# ---------------------------------------------------------------------------

def extract_l1c_grid(l1c_data: dict) -> GridInfo:
    """Extract grid information from L1C data."""
    coords = l1c_data.get("coordinates", {})
    proj = l1c_data.get("projection", {})

    # L1C uses X/Y in meters (Mercator projection)
    x = coords.get("x")
    y = coords.get("y")

    # Try to get lat/lon from projection info if available
    lat = None
    lon = None

    if x is not None and y is not None and PYPROJ_AVAILABLE:
        try:
            # Create Mercator CRS from projection info
            central_meridian = proj.get("longitude_of_projection_origin", 77.25)
            standard_parallel = proj.get("standard_parallel", 17.75)
            false_easting = proj.get("false_easting", 0.0)
            false_northing = proj.get("false_northing", 0.0)
            semi_major = proj.get("semi_major_axis", 6378137.0)
            semi_minor = proj.get("semi_minor_axis", 6356752.3142)

            crs = CRS.from_dict({
                "proj": "merc",
                "lon_0": central_meridian,
                "lat_ts": standard_parallel,
                "x_0": false_easting,
                "y_0": false_northing,
                "a": semi_major,
                "b": semi_minor,
                "units": "m",
            })

            transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

            # Get full resolution grid shape from data
            ny, nx = l1c_data["raw_counts"]["IMG_TIR1"].shape[1:]

            # Create full meshgrid - this is memory intensive but needed for ROI masking
            # Use float32 to save memory
            yy, xx = np.meshgrid(y.astype(np.float32), x.astype(np.float32), indexing="ij")
            lons, lats = transformer.transform(xx.ravel(), yy.ravel())
            lat = lats.reshape(yy.shape).astype(np.float32)
            lon = lons.reshape(xx.shape).astype(np.float32)

        except Exception as e:
            logger.warning(f"Could not transform L1C grid to lat/lon: {e}")

    # Fallback: use projection bounds if available
    bounds = None
    if lat is not None and lon is not None:
        valid_lat = lat[~np.isnan(lat)]
        valid_lon = lon[~np.isnan(lon)]
        if valid_lat.size > 0:
            bounds = SpatialBounds(
                lat_min=float(valid_lat.min()),
                lat_max=float(valid_lat.max()),
                lon_min=float(valid_lon.min()),
                lon_max=float(valid_lon.max()),
            )
    elif "lower_left_lat_lon(degrees)" in proj and "upper_right_lat_lon(degrees)" in proj:
        ll = proj["lower_left_lat_lon(degrees)"]
        ur = proj["upper_right_lat_lon(degrees)"]
        bounds = SpatialBounds(
            lat_min=float(ll[0]),
            lat_max=float(ur[0]),
            lon_min=float(ll[1]),
            lon_max=float(ur[1]),
        )

    return GridInfo(
        product="L1C",
        shape=l1c_data["raw_counts"]["IMG_TIR1"].shape,
        lat=lat,
        lon=lon,
        x=x,
        y=y,
        projection=proj,
        bounds=bounds,
    )


def extract_latlon_grid(data: dict, lat_key: str = "lat", lon_key: str = "lon") -> GridInfo:
    """Extract grid information from CTP/HEM/SST data (have explicit lat/lon arrays)."""
    coords = data.get("coordinates", {})
    lat = coords.get(lat_key)
    lon = coords.get(lon_key)

    bounds = None
    if lat is not None and lon is not None:
        valid_lat = lat[~np.isnan(lat)]
        valid_lon = lon[~np.isnan(lon)]
        if valid_lat.size > 0:
            bounds = SpatialBounds(
                lat_min=float(valid_lat.min()),
                lat_max=float(valid_lat.max()),
                lon_min=float(valid_lon.min()),
                lon_max=float(valid_lon.max()),
            )

    return GridInfo(
        product=data.get("product", "UNKNOWN"),
        shape=(lat.shape if lat is not None else (0, 0)),
        lat=lat,
        lon=lon,
        bounds=bounds,
    )


# ---------------------------------------------------------------------------
# ROI Masking
# ---------------------------------------------------------------------------

def create_roi_mask(lat: np.ndarray, lon: np.ndarray,
                    lat_min: float = DEFAULT_LAT_MIN,
                    lat_max: float = DEFAULT_LAT_MAX,
                    lon_min: float = DEFAULT_LON_MIN,
                    lon_max: float = DEFAULT_LON_MAX) -> np.ndarray:
    """
    Create boolean mask for region of interest.

    Returns:
        Boolean array same shape as lat/lon, True = inside ROI
    """
    if lat is None or lon is None:
        raise ValueError("Latitude and longitude arrays required")

    mask = (
        (lat >= lat_min) & (lat <= lat_max) &
        (lon >= lon_min) & (lon <= lon_max)
    )
    return mask


def apply_roi_mask(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Apply ROI mask to data array.

    Handles cases where data shape matches mask or needs broadcasting.
    """
    if data.shape == mask.shape:
        return np.where(mask, data, np.nan)
    elif data.ndim == mask.ndim + 1 and data.shape[1:] == mask.shape:
        # Data has channel dimension: (C, H, W) vs mask (H, W)
        return np.where(mask, data, np.nan)
    elif data.ndim == mask.ndim + 1 and data.shape[0] == mask.shape[0] and data.shape[2] == mask.shape[1]:
        # (H, C, W) - unlikely but handle
        return np.where(mask[:, None, :], data, np.nan)
    else:
        logger.warning(f"Shape mismatch: data {data.shape} vs mask {mask.shape}, returning original")
        return data


def subset_to_roi(data: np.ndarray, lat: np.ndarray, lon: np.ndarray,
                  lat_min: float = DEFAULT_LAT_MIN,
                  lat_max: float = DEFAULT_LAT_MAX,
                  lon_min: float = DEFAULT_LON_MIN,
                  lon_max: float = DEFAULT_LON_MAX) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Subset data to ROI by finding bounding box of valid ROI pixels.

    Returns:
        (subset_data, subset_lat, subset_lon, roi_mask)

    This is more memory-efficient than masking full array when ROI is small.
    """
    mask = create_roi_mask(lat, lon, lat_min, lat_max, lon_min, lon_max)

    if not mask.any():
        logger.warning("No data within ROI")
        return data, lat, lon, mask

    # Find bounding box of ROI pixels
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]

    row_min, row_max = rows[0], rows[-1] + 1
    col_min, col_max = cols[0], cols[-1] + 1

    # Add small padding
    pad = 2
    row_min = max(0, row_min - pad)
    row_max = min(mask.shape[0], row_max + pad)
    col_min = max(0, col_min - pad)
    col_max = min(mask.shape[1], col_max + pad)

    sub_mask = mask[row_min:row_max, col_min:col_max]
    sub_lat = lat[row_min:row_max, col_min:col_max]
    sub_lon = lon[row_min:row_max, col_min:col_max]

    if data.ndim == 3 and data.shape[1:] == mask.shape:
        # (C, H, W)
        sub_data = data[:, row_min:row_max, col_min:col_max]
    elif data.ndim == 2 and data.shape == mask.shape:
        # (H, W)
        sub_data = data[row_min:row_max, col_min:col_max]
    elif data.ndim == 3 and data.shape[:2] == mask.shape:
        # (H, W, C)
        sub_data = data[row_min:row_max, col_min:col_max, :]
    else:
        logger.warning(f"Unexpected data shape {data.shape} for mask {mask.shape}, using full")
        return data, lat, lon, mask

    return sub_data, sub_lat, sub_lon, sub_mask


# ---------------------------------------------------------------------------
# Grid Comparison
# ---------------------------------------------------------------------------

def compare_grids(grids: dict[str, GridInfo]) -> dict:
    """
    Compare spatial properties of all product grids.

    Returns dict with comparison info.
    """
    result = {
        "products": {},
        "common_bounds": None,
        "resolution_estimates": {},
    }

    bounds_list = []
    for name, grid in grids.items():
        result["products"][name] = {
            "shape": grid.shape,
            "bounds": {
                "lat_min": grid.bounds.lat_min,
                "lat_max": grid.bounds.lat_max,
                "lon_min": grid.bounds.lon_min,
                "lon_max": grid.bounds.lon_max,
            } if grid.bounds else None,
            "has_latlon": grid.lat is not None and grid.lon is not None,
        }
        if grid.bounds:
            bounds_list.append(grid.bounds)

    if bounds_list:
        result["common_bounds"] = {
            "lat_min": max(b.lat_min for b in bounds_list),
            "lat_max": min(b.lat_max for b in bounds_list),
            "lon_min": max(b.lon_min for b in bounds_list),
            "lon_max": min(b.lon_max for b in bounds_list),
        }

    return result


def print_grid_comparison(grids: dict[str, GridInfo]) -> None:
    """Print human-readable grid comparison."""
    print(f"\n{'='*70}")
    print("GRID COMPARISON")
    print(f"{'='*70}")

    for name, grid in grids.items():
        print(f"\n{name}:")
        print(f"  Shape: {grid.shape}")
        if grid.bounds:
            print(f"  Bounds: lat [{grid.bounds.lat_min:.2f}, {grid.bounds.lat_max:.2f}], "
                  f"lon [{grid.bounds.lon_min:.2f}, {grid.bounds.lon_max:.2f}]")
        else:
            print(f"  Bounds: unknown")
        print(f"  Has lat/lon: {grid.lat is not None and grid.lon is not None}")
        if grid.projection:
            print(f"  Projection: {grid.projection.get('grid_mapping_name', 'unknown')}")

    comparison = compare_grids(grids)
    if comparison["common_bounds"]:
        cb = comparison["common_bounds"]
        print(f"\nCommon overlap region:")
        print(f"  lat [{cb['lat_min']:.2f}, {cb['lat_max']:.2f}], "
              f"lon [{cb['lon_min']:.2f}, {cb['lon_max']:.2f}]")

    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# L1C Mercator to Lat/Lon Conversion (when needed)
# ---------------------------------------------------------------------------

def l1c_xy_to_latlon(x: np.ndarray, y: np.ndarray, proj_info: dict) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert L1C Mercator X/Y coordinates to lat/lon.

    Uses pyproj if available. For full grid conversion, use sparingly due to memory.
    """
    if not PYPROJ_AVAILABLE:
        raise RuntimeError("pyproj required for coordinate transformation")

    central_meridian = proj_info.get("longitude_of_projection_origin", 77.25)
    standard_parallel = proj_info.get("standard_parallel", 17.75)
    false_easting = proj_info.get("false_easting", 0.0)
    false_northing = proj_info.get("false_northing", 0.0)
    semi_major = proj_info.get("semi_major_axis", 6378137.0)
    semi_minor = proj_info.get("semi_minor_axis", 6356752.3142)

    crs = CRS.from_dict({
        "proj": "merc",
        "lon_0": central_meridian,
        "lat_ts": standard_parallel,
        "x_0": false_easting,
        "y_0": false_northing,
        "a": semi_major,
        "b": semi_minor,
        "units": "m",
    })

    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)

    return lat, lon