# MOSDAC Phase 2 - Feature Validation Report

*Generated: 2026-08-28T19:29:59.360147+00:00*

## 1. Dataset Summary

### Verification

```json
{
  "npz_count": 37,
  "all_loadable": true,
  "keys_present": [
    "feature_array",
    "feature_names",
    "metadata",
    "full_features"
  ],
  "names_consistent": true,
  "n_samples": 37,
  "n_features": 96,
  "manifest_exists": true,
  "batch_summary_exists": true,
  "sample_timestamps": [
    "2026-08-27T16:30:00Z",
    "2026-08-27T17:00:00Z",
    "2026-08-27T19:30:00Z",
    "...",
    "2026-08-28T12:00:00Z",
    "2026-08-28T12:30:00Z",
    "2026-08-28T13:00:00Z"
  ]
}
```

- NPZ count: 37
- All loadable: True
- Names consistent: True

## 2. Feature Quality

- n_features: 96

- Issues summary: {
  "excessive_missing": 0,
  "constant": 31,
  "near_constant": 0,
  "statistically_unusual": 4
}


**Constant features (12):**

| feature | unique | std | note |
|---|---|---|---|

| l1c_IMG_TIR1_total | 1 | 0.0 | total/pixel-count constant - no variance |

| l1c_IMG_TIR1_nan_count | 1 | 0.0 | total/pixel-count constant - no variance |

| l1c_IMG_TIR1_nan_pct | 1 | 0.0 | total/pixel-count constant - no variance |

| l1c_IMG_TIR2_total | 1 | 0.0 | total/pixel-count constant - no variance |

| l1c_IMG_TIR2_nan_count | 1 | 0.0 | total/pixel-count constant - no variance |


**Near-constant:**


**Range flags (sample):**

| feature | mean | min | max | flag |
|---|---|---|---|---|

| l1c_IMG_TIR1_total | 295302.0 | 295302.0 | 295302.0 | potentially_valid |

| l1c_IMG_TIR1_nan_count | 0.0 | 0.0 | 0.0 | potentially_valid |

| l1c_IMG_TIR1_nan_pct | 0.0 | 0.0 | 0.0 | potentially_valid |

| l1c_IMG_TIR1_min | 456.7567567567568 | 353.0 | 536.0 | potentially_valid |

| l1c_IMG_TIR1_max | 950.1081081081081 | 944.0 | 956.0 | potentially_valid |

| l1c_IMG_TIR1_mean | 670.8244002058699 | 650.705810546875 | 701.97607421875 | potentially_valid |

| l1c_IMG_TIR1_std | 118.41058514569256 | 103.19410705566406 | 135.138916015625 | potentially_valid |

| l1c_IMG_TIR2_total | 295302.0 | 295302.0 | 295302.0 | potentially_valid |

| l1c_IMG_TIR2_nan_count | 0.0 | 0.0 | 0.0 | potentially_valid |

| l1c_IMG_TIR2_nan_pct | 0.0 | 0.0 | 0.0 | potentially_valid |

| l1c_IMG_TIR2_min | 572.1351351351351 | 508.0 | 630.0 | potentially_valid |

| l1c_IMG_TIR2_max | 949.5675675675676 | 942.0 | 955.0 | potentially_valid |

| l1c_IMG_TIR2_mean | 728.3206770613386 | 710.8573608398438 | 757.0050048828125 | potentially_valid |

| l1c_IMG_TIR2_std | 90.62629514127164 | 77.29195404052734 | 104.47998046875 | potentially_valid |

| l1c_IMG_WV_total | 295302.0 | 295302.0 | 295302.0 | potentially_valid |

| l1c_IMG_WV_nan_count | 0.0 | 0.0 | 0.0 | potentially_valid |

| l1c_IMG_WV_nan_pct | 0.0 | 0.0 | 0.0 | potentially_valid |

| l1c_IMG_WV_min | 865.8648648648649 | 857.0 | 872.0 | potentially_valid |

| l1c_IMG_WV_max | 986.1081081081081 | 982.0 | 990.0 | potentially_valid |

| l1c_IMG_WV_mean | 914.62631143106 | 911.1998291015625 | 921.3828125 | potentially_valid |


## 3. Missing-Value Analysis

### Pixel missing

```json
{
  "CTP (hPa) pixel NaN %": {
    "mean_pct": 16.14537914379223,
    "std": 1.7623724816410233,
    "min": 12.827620506286621,
    "max": 19.380041122436523
  },
  "CTT (K) pixel NaN %": {
    "mean_pct": 16.14537914379223,
    "std": 1.7623724816410233,
    "min": 12.827620506286621,
    "max": 19.380041122436523
  },
  "EFF_EMISS pixel NaN %": {
    "mean_pct": 16.14537914379223,
    "std": 1.7623724816410233,
    "min": 12.827620506286621,
    "max": 19.380041122436523
  },
  "HEM pixel NaN %": {
    "mean_pct": 0.0,
    "std": 0.0,
    "min": 0.0,
    "max": 0.0
  },
  "SST_FCT pixel NaN %": {
    "mean_pct": 91.26256973679001,
    "std": 1.6359242940810188,
    "min": 89.16287994384766,
    "max": 94.2232666015625
  },
  "SST_REG pixel NaN %": {
    "mean_pct": 93.39098523114178,
    "std": 2.1138328728741005,
    "min": 90.3946304321289,
    "max": 98.632080078125
  },
  "SST_VAR pixel NaN %": {
    "mean_pct": 91.26256973679001,
    "std": 1.6359242940810188,
    "min": 89.16287994384766,
    "max": 94.2232666015625
  }
}
```

**Likely causes:**

- **CTP/CTT/EFF_EMISS ~12-19%:** Expected product coverage: CTP algorithm masks clear-sky / invalid retrievals as -999 -> ~16% NaN is normal for Bay ROI. Not ingestion bug; ctp_EFF_EMISS min/max constant 0.01/1.0 suggests valid cloud mask.

- **HEM 0% NaN:** Expected: Hydro-Estimator outputs 0 mm/hr for no rain, not NaN. No masking issue.

- **SST 89-98% NaN:** Expected geographic/product coverage: SST is ocean-only, ROI 5-25N 78-98E includes ~60% land (Indian subcontinent) + cloud-masked pixels. L2B SST masks land + cloudy as fill -999; ~91% mean NaN for FCT/VAR and 93% for REG (REG stricter QA) matches ocean fraction. Not ingestion/calibration error; verified scale 0.01 fill 32767 correctly applied.


**ML-safe recommendations:**

- **general:** Do NOT replace NaN with zero (would bias means: SST 0K impossible, CTP 0 hPa impossible).

- **CTP:** Keep NaN mask; for ML use valid-pixel stats (mean valid) + auxiliary valid_fraction = 1 - nan_pct/100 as separate feature (already present as mean of nan_pct). Optionally impute with median of valid per feature only during model input scaling, and add missing_indicator column.

- **HEM:** No imputation needed (0% pixel NaN). Keep high_rain stats; consider log1p for HEM_mean due to skew.

- **SST:** Do not use SST mean alone when valid pixels <10%. Recommend: use SST_FCT where valid_fraction >0.05, otherwise mark sample SST-unavailable; for ML, use masked mean + missing_indicator + valid_pixel_count; consider SST gradient feature instead of raw mean when NaN>90%. Future: ocean-only ROI refinement or SST_valid_fraction threshold.

- **L1C:** 0% NaN by design (fill 1023 handled, but rare). No issue.


## 4. Correlation ( |r| >= 0.95 )

### Correlation

```json
{
  "threshold": 0.95,
  "n_variable_features": 65,
  "n_pairs_ge_thresh": 74,
  "pairs": [
    {
      "f1": "ctp_CTP_nan_count",
      "f2": "ctp_CTT_nan_count",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "ctp_CTP_nan_count",
      "f2": "ctp_EFF_EMISS_nan_count",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "ctp_CTP_nan_pct",
      "f2": "ctp_CTT_nan_pct",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "ctp_CTP_nan_pct",
      "f2": "ctp_EFF_EMISS_nan_pct",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "ctp_CTT_nan_count",
      "f2": "ctp_EFF_EMISS_nan_count",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "ctp_CTT_nan_pct",
      "f2": "ctp_EFF_EMISS_nan_pct",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "sst_SST_FCT_nan_count",
      "f2": "sst_SST_VAR_nan_count",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "sst_SST_FCT_nan_pct",
      "f2": "sst_SST_VAR_nan_pct",
      "r": 1.0,
      "abs_r": 1.0
    },
    {
      "f1": "hem_HEM_very_high_rain_pixels",
      "f2": "hem_HEM_very_high_rain_fraction",
      "r": 0.9999999999999996,
      "abs_r": 0.9999999999999996
    },
    {
      "f1": "hem_HEM_high_rain_pixels",
      "f2": "hem_HEM_high_rain_fraction",
      "r": 0.9999999999999966,
      "abs_r": 0.9999999999999966
    },
    {
      "f1": "ctp_CTP_nan_pct",
      "f2": "ctp_CTT_nan_count",
      "r": 0.9999999999999818,
      "abs_r": 0.9999999999999818
    },
    {
      "f1": "ctp_CTP_nan_pct",
      "f2": "ctp_EFF_EMISS_nan_count",
      "r": 0.9999999999999818,
      "abs_r": 0.9999999999999818
    },
    {
      "f1": "ctp_CTT_nan_pct",
      "f2": "ctp_EFF_EMISS_nan_count",
      "r": 0.9999999999999818,
      "abs_r": 0.9999999999999818
    },
    {
      "f1": "ctp_CTP_nan_count",
      "f2": "ctp_CTP_nan_pct",
      "r": 0.9999999999999817,
      "abs_r": 0.9999999999999817
    },
    {
      "f1": "ctp_CTP_nan_count",
      "f2": "ctp_CTT_nan_pct",
      "r": 0.9999999999999817,
      "abs_r": 0.9999999999999817
    },
    {
      "f1": "ctp_CTP_nan_count",
      "f2": "ctp_EFF_EMISS_nan_pct",
      "r": 0.9999999999999817,
      "abs_r": 0.9999999999999817
    },
    {
      "f1": "ctp_CTT_nan_count",
      "f2": "ctp_CTT_nan_pct",
      "r": 0.9999999999999817,
      "abs_r": 0.9999999999999817
    },
    {
      "f1": "ctp_CTT_nan_count",
      "f2": "ctp_EFF_EMISS_nan_pct",
      "r": 0.9999999999999817,
      "abs_r": 0.9999999999999817
    },
    {
      "f1": "ctp_EFF_EMISS_nan_count",
      "f2": "ctp_EFF_EMISS_nan_pct",
      "r": 0.9999999999999817,
      "abs_r": 0.9999999999999817
    },
    {
      "f1": "sst_SST_REG_nan_count",
      "f2": "sst_SST_REG_nan_pct",
      "r": 0.9999999999993909,
      "abs_r": 0.9999999999993909
    },
    {
      "f1": "sst_SST_FCT_nan_count",
      "f2": "sst_SST_FCT_nan_pct",
      "r": 0.99999999999935,
      "abs_r": 0.99999999999935
    },
    {
      "f1": "sst_SST_FCT_nan_count",
      "f2": "sst_SST_VAR_nan_pct",
      "r": 0.99999999999935,
      "abs_r": 0.99999999999935
    },
    {
      "f1": "sst_SST_FCT_nan_pct",
      "f2": "sst_SST_VAR_nan_count",
      "r": 0.99999999999935,
      "abs_r": 0.99999999999935
    },
    {
      "f1": "sst_SST_VAR_nan_count",
      "f2": "sst_SST_VAR_nan_pct",
      "r": 0.99999999999935,
      "abs_r": 0.99999999999935
    },
    {
      "f1": "l1c_IMG_VIS_std",
      "f2": "l1c_IMG_SWIR_std",
      "r": 0.999205204210114,
      "abs_r": 0.999205204210114
    },
    {
      "f1": "l1c_IMG_VIS_mean",
      "f2": "l1c_IMG_SWIR_mean",
      "r": 0.9990101491922968,
      "abs_r": 0.9990101491922968
    },
    {
      "f1": "l1c_IMG_VIS_std",
      "f2": "l1c_IMG_SWIR_mean",
      "r": 0.9987447788699774,
      "abs_r": 0.9987447788699774
    },
    {
      "f1": "l1c_IMG_TIR1_std",
      "f2": "l1c_IMG_TIR2_std",
      "r": 0.9985869327598257,
      "abs_r": 0.9985869327598257
    },
    {
      "f1": "l1c_IMG_VIS_mean",
      "f2": "l1c_IMG_VIS_std",
      "r": 0.9975085191888533,
      "abs_r": 0.9975085191888533
    },
    {
      "f1": "l1c_IMG_SWIR_mean",
      "f2": "l1c_IMG_SWIR_std",
      "r": 0.997348944048761,
      "abs_r": 0.997348944048761
    }
  ],
  "groups": [
    [
      "ctp_CTP_std",
      "ctp_CTT_std",
      "ctp_EFF_EMISS_mean",
      "ctp_EFF_EMISS_std",
      "l1c_IMG_MIR_std",
      "l1c_IMG_TIR1_min",
      "l1c_IMG_TIR1_std",
      "l1c_IMG_TIR2_min",
      "l1c_IMG_TIR2_std",
      "l1c_IMG_WV_std"
    ],
    [
      "l1c_IMG_MIR_max",
      "l1c_IMG_MIR_mean",
      "l1c_IMG_SWIR_max",
      "l1c_IMG_SWIR_mean",
      "l1c_IMG_SWIR_min",
      "l1c_IMG_SWIR_std",
      "l1c_IMG_VIS_max",
      "l1c_IMG_VIS_mean",
      "l1c_IMG_VIS_min",
      "l1c_IMG_VIS_std"
    ],
    [
      "ctp_CTP_nan_count",
      "ctp_CTP_nan_pct",
      "ctp_CTT_nan_count",
      "ctp_CTT_nan_pct",
      "ctp_EFF_EMISS_nan_count",
      "ctp_EFF_EMISS_nan_pct"
    ],
    [
      "sst_SST_FCT_nan_count",
      "sst_SST_FCT_nan_pct",
      "sst_SST_VAR_nan_count",
      "sst_SST_VAR_nan_pct"
    ],
    [
      "l1c_IMG_TIR1_mean",
      "l1c_IMG_TIR2_mean",
      "l1c_IMG_WV_mean"
    ],
    [
      "hem_HEM_high_rain_fraction",
      "hem_HEM_high_rain_pixels"
    ],
    [
      "hem_HEM_very_high_rain_fraction",
      "hem_HEM_very_high_rain_pixels"
    ],
    [
      "sst_SST_REG_nan_count",
      "sst_SST_REG_nan_pct"
    ]
  ],
  "note": "Highly correlated feature pairs/groups for review; no automatic removal."
}
```


## 5. Temporal Consistency

### Temporal

```json
{
  "sorted": true,
  "n_samples": 37,
  "time_range": [
    "2026-08-27T16:30:00Z",
    "2026-08-28T13:00:00Z"
  ],
  "expected_interval_min": 30,
  "gaps_min": [
    30.0,
    150.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    30.0,
    60.0,
    30.0,
    30.0,
    30.0
  ],
  "gap_issues": [
    {
      "from": "2026-08-27T17:00:00Z",
      "to": "2026-08-27T19:30:00Z",
      "gap_min": 150.0,
      "expected": 30
    },
    {
      "from": "2026-08-28T10:30:00Z",
      "to": "2026-08-28T11:30:00Z",
      "gap_min": 60.0,
      "expected": 30
    }
  ],
  "temporal_flags": [
    {
      "feature": "l1c_IMG_TIR1_total",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_TIR1_nan_count",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_TIR1_nan_pct",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_TIR1_mean",
      "issue": "jump",
      "at": "2026-08-27T17:00:00Z->2026-08-27T19:30:00Z",
      "diff": 14.1485595703125,
      "z": 3.755731928968197
    },
    {
      "feature": "l1c_IMG_TIR1_std",
      "issue": "jump",
      "at": "2026-08-27T17:00:00Z->2026-08-27T19:30:00Z",
      "diff": -5.0837860107421875,
      "z": 3.0094054278575864
    },
    {
      "feature": "l1c_IMG_TIR2_total",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_TIR2_nan_count",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_TIR2_nan_pct",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_TIR2_min",
      "issue": "jump",
      "at": "2026-08-28T10:30:00Z->2026-08-28T11:30:00Z",
      "diff": 27.0,
      "z": 3.0897439936401514
    },
    {
      "feature": "l1c_IMG_TIR2_mean",
      "issue": "jump",
      "at": "2026-08-27T17:00:00Z->2026-08-27T19:30:00Z",
      "diff": 10.8648681640625,
      "z": 3.2417601070982034
    },
    {
      "feature": "l1c_IMG_TIR2_std",
      "issue": "jump",
      "at": "2026-08-27T17:00:00Z->2026-08-27T19:30:00Z",
      "diff": -5.3863677978515625,
      "z": 3.602549227623558
    },
    {
      "feature": "l1c_IMG_WV_total",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_WV_nan_count",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_WV_nan_pct",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_WV_min",
      "issue": "jump",
      "at": "2026-08-27T17:00:00Z->2026-08-27T19:30:00Z",
      "diff": 9.0,
      "z": 3.501747145204016
    },
    {
      "feature": "l1c_IMG_WV_mean",
      "issue": "jump",
      "at": "2026-08-27T16:30:00Z->2026-08-27T17:00:00Z",
      "diff": 4.02093505859375,
      "z": 3.8961140131722294
    },
    {
      "feature": "l1c_IMG_WV_std",
      "issue": "jump",
      "at": "2026-08-27T17:00:00Z->2026-08-27T19:30:00Z",
      "diff": -2.6644973754882812,
      "z": 4.938783809947005
    },
    {
      "feature": "l1c_IMG_VIS_total",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_VIS_nan_count",
      "issue": "constant_over_time",
      "unique": 1
    },
    {
      "feature": "l1c_IMG_VIS_nan_pct",
      "issue": "constant_over_time",
      "unique": 1
    }
  ],
  "n_flags": 57
}
```

**Gap issues:** nominal 30 min violated at incomplete periods (17:00->19:30, 10:30->11:30) - matches manifest incomplete.

**Flags:** 57 features with jumps/constancy - see JSON.


## 6. Spatial Information Assessment

### Spatial

```json
{
  "current_features_per_product": {
    "l1c_bands": [
      "IMG_TIR1",
      "IMG_TIR2",
      "IMG_WV",
      "IMG_VIS",
      "IMG_SWIR",
      "IMG_MIR"
    ],
    "ctp": [
      "CTP",
      "CTT",
      "EFF_EMISS"
    ],
    "hem": [
      "HEM"
    ],
    "sst": [
      "SST_FCT",
      "SST_REG",
      "SST_VAR"
    ]
  },
  "roi_bounds": {
    "lat_min": 5.0,
    "lat_max": 25.0,
    "lon_min": 78.0,
    "lon_max": 98.0
  },
  "grid_summary": {
    "l1c": {
      "shape": [
        1,
        1616,
        1737
      ],
      "bounds": {
        "lat_min": -9.999999046325684,
        "lat_max": 45.5,
        "lon_min": 44.5,
        "lon_max": 110.0
      }
    },
    "ctp": {
      "shape": [
        313,
        312
      ],
      "bounds": {
        "lat_min": -79.2899982277304,
        "lat_max": 78.73999824002385,
        "lon_min": 1.7199999615550041,
        "lon_max": 162.3599963709712
      }
    },
    "hem": {
      "shape": [
        2816,
        2805
      ],
      "bounds": {
        "lat_min": -81.03999818861485,
        "lat_max": 81.03999818861485,
        "lon_min": 0.8399999812245369,
        "lon_max": 163.14999635331333
      }
    },
    "sst": {
      "shape": [
        2816,
        2805
      ],
      "bounds": {
        "lat_min": -81.03999818861485,
        "lat_max": 81.03999818861485,
        "lon_min": 0.8399999812245369,
        "lon_max": 163.14999635331333
      }
    }
  },
  "lost_information": [
    "Large grids (L1C 1616x1737 \u22482.8M pix, HEM/SST 2816x2805 \u22487.9M) collapsed to per-ROI mean/std/min/max -> texture, organization, anisotropy lost.",
    "No cold-cloud fraction (<235K), anvil shape, or convective organization metric.",
    "No temperature-gradient stats beyond SST mean (CTP/CT T gradients not computed).",
    "No rainfall concentration / spatial variance beyond high_rain_fraction (no Moran\u2019s I, no contiguity).",
    "No location/centroid of extremum (e.g., coldest cloud lat/lon, heaviest rain lat/lon).",
    "Fixed ROI 5-25N 78-98E includes land; ocean-only signal diluted. No radial/sector stats around cyclone center.",
    "No multi-scale (e.g., GLCM, wavelet) or histogram features."
  ],
  "phase3_recommendations": [
    "Keep 96 stats as baseline; add 8-12 spatial descriptors: cold_cloud_fraction_TIR1<235K, TIR1\u2013WV BTD variance, CTP/CTT gradient mag mean+std, rainfall concentration (p90/p50, Gini), SST gradient (already hem high_rain but add SST_GRAD), centroid of coldest 5% pixels, QC valid_fraction per dataset.",
    "Future: cyclone-relative ROI (center radius 500km, 8 radial sectors) once center labels available; requires target alignment.",
    "Add ocean-mask-aware SST stats (ocean-only mean) vs current ROI that mixes land NaN.",
    "Provide histogram counts (e.g., 5-bin temp histogram) not just mean/std to preserve distribution.",
    "No grid resize/reproject for Phase 2; if common grid needed, use pyproj+rasterio in Phase 3."
  ],
  "implementation_note": "No new spatial features implemented in Phase 2 - recommendation only."
}
```


## 7. Label / Target Alignment

### Label

```json
{
  "existing_target": {
    "type": "future_positions lat/lon at 5 horizons",
    "horizons_h": [
      6,
      12,
      24,
      48,
      72
    ],
    "seq_length": 4,
    "n_features_in": 8,
    "feature_cols": [
      "lat",
      "lon",
      "dlat",
      "dlon",
      "speed_kmh",
      "direction_deg",
      "hour_sin",
      "hour_cos"
    ]
  },
  "mosdac_resolution": "30 min (half-hourly L1C), matched 30-min CTP/HEM/SST",
  "existing_model_resolution": "3h natural IBTrACS, horizons 6h steps",
  "ibtracs_raw_exists": true,
  "ibtracs_note": "IBTrACS v04r01 ends ~2024; 2026 MOSDAC has no historical labels",
  "can_align_directly": false,
  "blocker": "Major ML integration blocker: 37 MOSDAC timestamps (2026-08-27/28) have no cyclone ID/center/wind/pressure labels aligned to the existing supervised trajectory targets (future lat/lon). IBTrACS training data ends 2024. Without cyclone-center association, sequence construction (4x3h history -> 5 horizons) impossible. Additional data required: (a) operational cyclone track for 2026-08-27/28 (IMD best track, if cyclone existed) or (b) reprocess historical period where both IBTrACS and INSAT-3DS overlap (e.g., 2023-2024 cyclones in BB) to co-locate satellite windows with label storm IDs. Alternatively use MOSDAC for unsupervised pretraining / image-only forecasting.",
  "required_labels": [
    "cyclone_id (SID) per MOSDAC timestamp or 'no-cyclone' flag",
    "cyclone center lat/lon (or bounding box) at satellite time",
    "cyclone intensity (wind, pressure) if jointly predicting",
    "future target positions at +6/12/24/48/72h aligned to same SID",
    "temporal sync: satellite 30-min vs label 3h - resample or nearest-neighbor mapping"
  ]
}
```


## 8. Dataset-Size Limitations

### Size

```json
{
  "n_timestamps": 37,
  "temporal_coverage": "2026-08-27T16:30Z to 2026-08-28T13:00Z (~20.5h)",
  "sampling_interval": "30 min nominal, 2 gaps (17:00->19:30 150m, 10:30->11:30 60m)",
  "n_complete": 37,
  "n_incomplete": 13,
  "n_features": 96,
  "p_n_ratio": 2.59,
  "p": 96,
  "n": 37,
  "existing_model_input_features": 8,
  "comparison": "MOSDAC p=96 >> existing p=8; p/n=2.59 >1 indicates high-dimensional regime",
  "effective_usable_rowwise": 37,
  "effective_usable_note": "All 37 rows have 96 values (pixel stats imputed via NaN handling already), but SST pixel 89-98% means SST features have low ocean valid pixels (~30k of 287k) - effective ocean sample is small.",
  "sufficient_for_retraining": false,
  "implications": "37x96 violates n\u226bp requirement for supervised deep learning (LSTM 31k params). Risk: severe overfitting, unstable covariance, spurious correlations (see \u00a74). Rule of thumb: need 10-20x samples per feature -> need 1k-2k timestamps or aggressive feature reduction to <=8-10. Temporal coverage is single weather regime (20h), no cyclone diversity, cannot represent Bay variability. Not sufficient for meaningful supervised retraining; suitable for pipeline validation and exploratory analysis only."
}
```


> **p/n = 2.59** - p > n precludes meaningful LSTM retraining (31k params vs 37 samples).


## 9. Recommended Next Steps

1. Collect overlapping satellite+IBTrACS period (2023-2024 Bay cyclones) with 30-min satellite windows aligned to cyclone centers - priority for label availability.

2. Refine SST features: ocean-only mask, add valid_fraction, consider dropping SST_VAR if redundant (FCT vs VAR r≈1).

3. Add 8-12 spatial descriptors (cold fraction, gradient, centroid) without resizing - keep modular.

4. Dimensionality reduction: correlation groups -> keep one per group (e.g., total features constant -> drop all *_total), target p<=12 before any training.

5. Temporal augmentation: extend coverage to multiple weather regimes / monsoon vs cyclone.

6. Do not retrain until n>=500 and labels aligned; use current 37 for unsupervised validation only.


## 10. GO / NO-GO Decision

**Decision: NO-GO**


**Rationale:** Decision NO-GO based on: dataset_size, label_alignment; Blockers: p/n=2.59 >1 (37<96) - insufficient samples for supervised retraining; No cyclone labels aligned to 2026 MOSDAC timestamps - cannot form supervised targets. GO would require: 500-2000 overlapping satellite+track samples, label alignment, reduced p <=10, ocean-masked SST.


**NO-GO reasons:**

- p/n=2.59 >1 (37<96) - insufficient samples for supervised retraining

- No cyclone labels aligned to 2026 MOSDAC timestamps - cannot form supervised targets


---
*Phase 2 complete - no model retraining performed.*
