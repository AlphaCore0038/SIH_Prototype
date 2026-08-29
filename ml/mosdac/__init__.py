"""
MOSDAC INSAT-3DS Data Processing Module

A modular pipeline for processing MOSDAC HDF5 satellite data:
- L1C: INSAT-3DS Imager Level-1C (6 channels)
- CTP: Cloud Top Properties
- HEM: Hydro-Estimator Precipitation
- SST: Sea Surface Temperature

Pipeline stages:
1. Timestamp matching across products
2. HDF5 reading with metadata/calibration preservation
3. Geospatial handling (coordinates, projections, ROI)
4. Feature extraction
5. NPZ output for ML integration
"""

from .hdf5_reader import (
    read_l1c,
    read_ctp,
    read_hem,
    read_sst,
    read_product,
    calibrate_l1c_band,
    calibrate_l1c_to_temp,
    compute_basic_stats,
)

from .timestamp_matcher import (
    scan_product_directory,
    scan_all_products,
    match_timestamps,
    filter_complete,
    filter_incomplete,
    generate_manifest,
    parse_timestamp_from_filename,
    timestamp_key_to_iso,
    scan_and_match,
    print_manifest_summary,
)

from .geospatial import (
    DEFAULT_LAT_MIN,
    DEFAULT_LAT_MAX,
    DEFAULT_LON_MIN,
    DEFAULT_LON_MAX,
    SpatialBounds,
    GridInfo,
    extract_l1c_grid,
    extract_latlon_grid,
    create_roi_mask,
    apply_roi_mask,
    subset_to_roi,
    compare_grids,
    print_grid_comparison,
    l1c_xy_to_latlon,
)

from .preprocess import (
    extract_features,
    extract_l1c_features,
    extract_ctp_features,
    extract_hem_features,
    extract_sst_features,
    features_to_flat_array,
    save_features,
    load_features,
    print_feature_summary,
)

from .pipeline import (
    test_timestamp,
    process_batch,
    process_single_timestamp,
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_MANIFEST,
    DEFAULT_ROI,
)

__all__ = [
    # hdf5_reader
    "read_l1c",
    "read_ctp",
    "read_hem",
    "read_sst",
    "read_product",
    "calibrate_l1c_band",
    "calibrate_l1c_to_temp",
    "compute_basic_stats",
    # timestamp_matcher
    "scan_product_directory",
    "scan_all_products",
    "match_timestamps",
    "filter_complete",
    "filter_incomplete",
    "generate_manifest",
    "parse_timestamp_from_filename",
    "timestamp_key_to_iso",
    "scan_and_match",
    "print_manifest_summary",
    # geospatial
    "DEFAULT_LAT_MIN",
    "DEFAULT_LAT_MAX",
    "DEFAULT_LON_MIN",
    "DEFAULT_LON_MAX",
    "SpatialBounds",
    "GridInfo",
    "extract_l1c_grid",
    "extract_latlon_grid",
    "create_roi_mask",
    "apply_roi_mask",
    "subset_to_roi",
    "compare_grids",
    "print_grid_comparison",
    "l1c_xy_to_latlon",
    # preprocess
    "extract_features",
    "extract_l1c_features",
    "extract_ctp_features",
    "extract_hem_features",
    "extract_sst_features",
    "features_to_flat_array",
    "save_features",
    "load_features",
    "print_feature_summary",
    # pipeline
    "test_timestamp",
    "process_batch",
    "process_single_timestamp",
    "DEFAULT_DATA_DIR",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_MANIFEST",
    "DEFAULT_ROI",
]

__version__ = "0.1.0"