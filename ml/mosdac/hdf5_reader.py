"""
MOSDAC HDF5 Reader

Safe readers for all four INSAT-3DS product types:
- 3SIMG_L1C_ASIA_MER: Level-1C Imager (6 channels, raw counts + calibration LUTs)
- 3SIMG_L2B_CTP: Cloud Top Properties
- 3SIMG_L2B_HEM: Hydro-Estimator Precipitation
- 3SIMG_L2B_SST: Sea Surface Temperature

Preserves raw data, metadata, calibration info, and geospatial coordinates.
Does NOT blindly apply calibration - provides explicit calibration functions.
"""

import logging
from pathlib import Path
from typing import Any

import h5py
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

L1C_BANDS = [
    "IMG_TIR1",
    "IMG_TIR2",
    "IMG_WV",
    "IMG_VIS",
    "IMG_SWIR",
    "IMG_MIR",
]

L1C_CALIBRATION_DATASETS = {
    "IMG_TIR1": ("IMG_TIR1_RADIANCE", "IMG_TIR1_TEMP"),
    "IMG_TIR2": ("IMG_TIR2_RADIANCE", "IMG_TIR2_TEMP"),
    "IMG_WV": ("IMG_WV_RADIANCE", "IMG_WV_TEMP"),
    "IMG_VIS": ("IMG_VIS_RADIANCE", "IMG_VIS_ALBEDO"),
    "IMG_SWIR": ("IMG_SWIR_RADIANCE", "IMG_SWIR_ALBEDO"),
    "IMG_MIR": ("IMG_MIR_RADIANCE", "IMG_MIR_TEMP"),
}

CTP_KEY_DATASETS = ["CTP", "CTT", "EFF_EMISS"]
HEM_KEY_DATASETS = ["HEM"]
SST_KEY_DATASETS = ["SST_FCT", "SST_REG", "SST_VAR"]

# ROI for Bay of Bengal (configurable)
DEFAULT_LAT_MIN = 5.0
DEFAULT_LAT_MAX = 25.0
DEFAULT_LON_MIN = 78.0
DEFAULT_LON_MAX = 98.0

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _get_attr(obj: h5py.Dataset, key: str, default=None):
    """Safely get HDF5 attribute, handling numpy scalar types."""
    if key in obj.attrs:
        val = obj.attrs[key]
        if isinstance(val, (np.generic, np.ndarray)):
            return val.item() if np.isscalar(val) else val.tolist()
        return val
    return default


def _apply_scale_offset(data: np.ndarray, scale_factor: float, add_offset: float,
                         fill_value: float) -> np.ndarray:
    """Apply scale_factor and add_offset, handling fill values."""
    out = data.astype(np.float32)
    mask = (data == fill_value) if not np.isnan(fill_value) else np.zeros_like(data, dtype=bool)
    out = out * scale_factor + add_offset
    out[mask] = np.nan
    return out


def _mask_fill_value(data: np.ndarray, fill_value) -> np.ndarray:
    """Mask fill values as NaN."""
    out = data.astype(np.float32)
    if np.isnan(fill_value):
        return out
    out[data == fill_value] = np.nan
    return out


def _extract_time_from_dataset(time_ds: h5py.Dataset) -> str:
    """Extract timestamp from time dataset (minutes since 2000-01-01)."""
    try:
        minutes = time_ds[0]
        # Convert to datetime
        import datetime
        base = datetime.datetime(2000, 1, 1, 0, 0, 0)
        dt = base + datetime.timedelta(minutes=float(minutes))
        return dt.isoformat() + "Z"
    except Exception as e:
        logger.warning(f"Could not parse time dataset: {e}")
        return "unknown"


# ---------------------------------------------------------------------------
# L1C Reader
# ---------------------------------------------------------------------------

def read_l1c(filepath: Path) -> dict[str, Any]:
    """
    Read L1C ASIA MER HDF5 file.

    Returns dict with:
    - raw_counts: dict of band_name -> uint16 array (1, H, W)
    - calibration: dict of band_name -> {radiance_lut, temp_lut, scale_factor, add_offset, fill_value, metadata}
    - projection: dict of projection parameters
    - coordinates: {x: array, y: array}
    - time: acquisition time string
    - metadata: global attributes
    """
    result = {
        "product": "L1C_ASIA_MER",
        "filepath": str(filepath),
        "raw_counts": {},
        "calibration": {},
        "projection": {},
        "coordinates": {},
        "time": "unknown",
        "metadata": {},
    }

    with h5py.File(filepath, "r") as f:
        # Global attributes
        for k, v in f.attrs.items():
            result["metadata"][k] = v.item() if isinstance(v, np.generic) else v

        # Read raw count bands
        for band in L1C_BANDS:
            if band in f:
                ds = f[band]
                result["raw_counts"][band] = ds[()]
                result["calibration"][band] = {
                    "shape": ds.shape,
                    "dtype": str(ds.dtype),
                    "fill_value": _get_attr(ds, "_FillValue"),
                    "scale_factor": _get_attr(ds, "online_radiance_scale_factor"),
                    "scale_factor_gsics": _get_attr(ds, "online_radiance_scale_factor_gsics"),
                    "add_offset": _get_attr(ds, "online_radiance_add_offset"),
                    "add_offset_gsics": _get_attr(ds, "online_radiance_add_offset_gsics"),
                    "central_wavelength": _get_attr(ds, "central_wavelength"),
                    "bandwidth": _get_attr(ds, "bandwidth"),
                    "resolution": _get_attr(ds, "resolution"),
                    "resolution_unit": _get_attr(ds, "resolution_unit"),
                    "invert": _get_attr(ds, "invert"),
                    "long_name": _get_attr(ds, "long_name"),
                    "radiance_units": _get_attr(ds, "radiance_units"),
                    "wavelength_unit": _get_attr(ds, "wavelength_unit"),
                }

                # Read calibration LUTs if present
                rad_name, temp_name = L1C_CALIBRATION_DATASETS.get(band, (None, None))
                if rad_name and rad_name in f:
                    result["calibration"][band]["radiance_lut"] = f[rad_name][()]
                    result["calibration"][band]["radiance_lut_attrs"] = dict(f[rad_name].attrs)
                if temp_name and temp_name in f:
                    result["calibration"][band]["temp_lut"] = f[temp_name][()]
                    result["calibration"][band]["temp_lut_attrs"] = dict(f[temp_name].attrs)

        # Projection information
        if "Projection_Information" in f:
            proj = f["Projection_Information"]
            result["projection"] = {k: _get_attr(proj, k) for k in proj.attrs.keys()}

        # Coordinates
        if "X" in f:
            result["coordinates"]["x"] = f["X"][()]
        if "Y" in f:
            result["coordinates"]["y"] = f["Y"][()]

        # Time
        if "time" in f:
            result["time"] = _extract_time_from_dataset(f["time"])

        # Satellite geometry (optional)
        for geom in ["Sat_Azimuth", "Sat_Elevation", "Sun_Azimuth", "Sun_Elevation"]:
            if geom in f:
                ds = f[geom]
                result["metadata"][geom] = {
                    "shape": ds.shape,
                    "dtype": str(ds.dtype),
                    "fill_value": _get_attr(ds, "_FillValue"),
                    "scale_factor": _get_attr(ds, "scale_factor"),
                    "add_offset": _get_attr(ds, "add_offset"),
                    "units": _get_attr(ds, "units"),
                }

    logger.info(f"Read L1C: {filepath.name} - {len(result['raw_counts'])} bands")
    return result


def calibrate_l1c_band(raw_counts: np.ndarray, calib_info: dict,
                       use_gsics: bool = False) -> np.ndarray:
    """
    Convert raw counts to physical radiance/brightness temperature.

    Args:
        raw_counts: uint16 array from raw_counts[band]
        calib_info: calibration dict for that band
        use_gsics: if True, use GSICS-corrected scale/offset

    Returns:
        Float32 array with physical values (radiance or temperature), NaN for fill
    """
    scale = calib_info.get("scale_factor_gsics" if use_gsics else "scale_factor")
    offset = calib_info.get("add_offset_gsics" if use_gsics else "add_offset")
    fill = calib_info.get("fill_value", 1023)

    if scale is None or offset is None:
        raise ValueError("Calibration parameters not available")

    return _apply_scale_offset(raw_counts, scale, offset, fill)


def calibrate_l1c_to_temp(raw_counts: np.ndarray, calib_info: dict) -> np.ndarray:
    """
    Convert raw counts to brightness temperature using the TEMP LUT.

    This is the most accurate method for TIR bands.
    """
    temp_lut = calib_info.get("temp_lut")
    if temp_lut is None:
        raise ValueError("Temperature LUT not available")

    # LUT is typically 1024 entries mapping count -> temperature
    # Clamp indices to valid range
    indices = np.clip(raw_counts, 0, len(temp_lut) - 1).astype(int)
    result = temp_lut[indices].astype(np.float32)

    # Mask fill values
    fill = calib_info.get("fill_value", 1023)
    result[raw_counts == fill] = np.nan

    return result


# ---------------------------------------------------------------------------
# CTP Reader
# ---------------------------------------------------------------------------

def read_ctp(filepath: Path) -> dict[str, Any]:
    """
    Read CTP (Cloud Top Properties) HDF5 file.

    Key datasets: CTP (hPa), CTT (K), EFF_EMISS (unitless)
    All have lat/lon grids and scale_factor/add_offset.
    """
    result = {
        "product": "L2B_CTP",
        "filepath": str(filepath),
        "data": {},
        "coordinates": {},
        "time": "unknown",
        "metadata": {},
    }

    with h5py.File(filepath, "r") as f:
        for k, v in f.attrs.items():
            result["metadata"][k] = v.item() if isinstance(v, np.generic) else v

        # Key scientific datasets
        for ds_name in CTP_KEY_DATASETS:
            if ds_name in f:
                ds = f[ds_name]
                raw = ds[()]
                fill = _get_attr(ds, "_FillValue", -999.0)
                scale = _get_attr(ds, "scale_factor", 1.0)
                offset = _get_attr(ds, "add_offset", 0.0)

                result["data"][ds_name] = {
                    "raw": raw,
                    "physical": _apply_scale_offset(raw, scale, offset, fill),
                    "fill_value": fill,
                    "scale_factor": scale,
                    "add_offset": offset,
                    "units": _get_attr(ds, "units"),
                    "long_name": _get_attr(ds, "long_name"),
                }

        # Lat/Lon grids
        if "Latitude" in f:
            lat_ds = f["Latitude"]
            result["coordinates"]["lat"] = _apply_scale_offset(
                lat_ds[()],
                _get_attr(lat_ds, "scale_factor", 0.01),
                _get_attr(lat_ds, "add_offset", 0.0),
                _get_attr(lat_ds, "_FillValue", 31172),
            )
        if "Longitude" in f:
            lon_ds = f["Longitude"]
            result["coordinates"]["lon"] = _apply_scale_offset(
                lon_ds[()],
                _get_attr(lon_ds, "scale_factor", 0.01),
                _get_attr(lon_ds, "add_offset", 0.0),
                _get_attr(lon_ds, "_FillValue", 31172),
            )

        # CSBT lat/lon (clear-sky BT grid)
        if "CSBT_Latitude" in f:
            result["coordinates"]["csbt_lat"] = _apply_scale_offset(
                f["CSBT_Latitude"][()],
                _get_attr(f["CSBT_Latitude"], "scale_factor", 0.01),
                _get_attr(f["CSBT_Latitude"], "add_offset", 0.0),
                _get_attr(f["CSBT_Latitude"], "_FillValue", 31172),
            )
        if "CSBT_Longitude" in f:
            result["coordinates"]["csbt_lon"] = _apply_scale_offset(
                f["CSBT_Longitude"][()],
                _get_attr(f["CSBT_Longitude"], "scale_factor", 0.01),
                _get_attr(f["CSBT_Longitude"], "add_offset", 0.0),
                _get_attr(f["CSBT_Longitude"], "_FillValue", 31172),
            )

        if "time" in f:
            result["time"] = _extract_time_from_dataset(f["time"])

    logger.info(f"Read CTP: {filepath.name} - datasets: {list(result['data'].keys())}")
    return result


# ---------------------------------------------------------------------------
# HEM Reader
# ---------------------------------------------------------------------------

def read_hem(filepath: Path) -> dict[str, Any]:
    """
    Read HEM (Hydro-Estimator) HDF5 file.

    Key dataset: HEM (mm/hr precipitation rate)
    Has lat/lon grids.
    """
    result = {
        "product": "L2B_HEM",
        "filepath": str(filepath),
        "data": {},
        "coordinates": {},
        "time": "unknown",
        "metadata": {},
    }

    with h5py.File(filepath, "r") as f:
        for k, v in f.attrs.items():
            result["metadata"][k] = v.item() if isinstance(v, np.generic) else v

        for ds_name in HEM_KEY_DATASETS:
            if ds_name in f:
                ds = f[ds_name]
                raw = ds[()]
                fill = _get_attr(ds, "_FillValue", -999.0)
                scale = _get_attr(ds, "scale_factor", 1.0)
                offset = _get_attr(ds, "add_offset", 0.0)

                result["data"][ds_name] = {
                    "raw": raw,
                    "physical": _apply_scale_offset(raw, scale, offset, fill),
                    "fill_value": fill,
                    "scale_factor": scale,
                    "add_offset": offset,
                    "units": _get_attr(ds, "units"),
                    "long_name": _get_attr(ds, "long_name"),
                }

        if "Latitude" in f:
            lat_ds = f["Latitude"]
            result["coordinates"]["lat"] = _apply_scale_offset(
                lat_ds[()],
                _get_attr(lat_ds, "scale_factor", 0.01),
                _get_attr(lat_ds, "add_offset", 0.0),
                _get_attr(lat_ds, "_FillValue", 32767),
            )
        if "Longitude" in f:
            lon_ds = f["Longitude"]
            result["coordinates"]["lon"] = _apply_scale_offset(
                lon_ds[()],
                _get_attr(lon_ds, "scale_factor", 0.01),
                _get_attr(lon_ds, "add_offset", 0.0),
                _get_attr(lon_ds, "_FillValue", 32767),
            )

        if "time" in f:
            result["time"] = _extract_time_from_dataset(f["time"])

    logger.info(f"Read HEM: {filepath.name} - datasets: {list(result['data'].keys())}")
    return result


# ---------------------------------------------------------------------------
# SST Reader
# ---------------------------------------------------------------------------

def read_sst(filepath: Path) -> dict[str, Any]:
    """
    Read SST (Sea Surface Temperature) HDF5 file.

    Key datasets: SST_FCT, SST_REG, SST_VAR (all in Kelvin)
    Has lat/lon grids.
    """
    result = {
        "product": "L2B_SST",
        "filepath": str(filepath),
        "data": {},
        "coordinates": {},
        "time": "unknown",
        "metadata": {},
    }

    with h5py.File(filepath, "r") as f:
        for k, v in f.attrs.items():
            result["metadata"][k] = v.item() if isinstance(v, np.generic) else v

        for ds_name in SST_KEY_DATASETS:
            if ds_name in f:
                ds = f[ds_name]
                raw = ds[()]
                fill = _get_attr(ds, "_FillValue", -999.0)
                scale = _get_attr(ds, "scale_factor", 1.0)
                offset = _get_attr(ds, "add_offset", 0.0)

                result["data"][ds_name] = {
                    "raw": raw,
                    "physical": _apply_scale_offset(raw, scale, offset, fill),
                    "fill_value": fill,
                    "scale_factor": scale,
                    "add_offset": offset,
                    "units": _get_attr(ds, "units"),
                    "long_name": _get_attr(ds, "long_name"),
                }

        if "Latitude" in f:
            lat_ds = f["Latitude"]
            result["coordinates"]["lat"] = _apply_scale_offset(
                lat_ds[()],
                _get_attr(lat_ds, "scale_factor", 0.01),
                _get_attr(lat_ds, "add_offset", 0.0),
                _get_attr(lat_ds, "_FillValue", 32767),
            )
        if "Longitude" in f:
            lon_ds = f["Longitude"]
            result["coordinates"]["lon"] = _apply_scale_offset(
                lon_ds[()],
                _get_attr(lon_ds, "scale_factor", 0.01),
                _get_attr(lon_ds, "add_offset", 0.0),
                _get_attr(lon_ds, "_FillValue", 32767),
            )

        if "time" in f:
            result["time"] = _extract_time_from_dataset(f["time"])

    logger.info(f"Read SST: {filepath.name} - datasets: {list(result['data'].keys())}")
    return result


# ---------------------------------------------------------------------------
# Product Router
# ---------------------------------------------------------------------------

def read_product(filepath: Path, product_type: str = None) -> dict[str, Any]:
    """
    Auto-detect product type from filename and read accordingly.

    product_type: optional override ('l1c', 'ctp', 'hem', 'sst')
    """
    name = filepath.name.upper()

    if product_type is None:
        if "L1C_ASIA_MER" in name:
            product_type = "l1c"
        elif "L2B_CTP" in name:
            product_type = "ctp"
        elif "L2B_HEM" in name:
            product_type = "hem"
        elif "L2B_SST" in name:
            product_type = "sst"
        else:
            raise ValueError(f"Cannot detect product type from filename: {filepath.name}")

    readers = {
        "l1c": read_l1c,
        "ctp": read_ctp,
        "hem": read_hem,
        "sst": read_sst,
    }

    if product_type not in readers:
        raise ValueError(f"Unknown product type: {product_type}")

    return readers[product_type](filepath)


# ---------------------------------------------------------------------------
# Statistics Helper
# ---------------------------------------------------------------------------

def compute_basic_stats(arr: np.ndarray, name: str = "") -> dict:
    """Compute basic statistics for an array, handling NaN."""
    if arr is None or arr.size == 0:
        return {"name": name, "error": "empty array"}

    flat = arr.ravel()
    total = flat.size
    nan_count = np.isnan(flat).sum()
    valid = flat[~np.isnan(flat)]

    if valid.size == 0:
        return {
            "name": name,
            "total": int(total),
            "nan_count": int(nan_count),
            "nan_pct": 100.0,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
        }

    return {
        "name": name,
        "total": int(total),
        "nan_count": int(nan_count),
        "nan_pct": float(nan_count / total * 100),
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
        "std": float(valid.std()),
    }