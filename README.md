# VayuDrishti

ML-powered cyclone trajectory forecast for Bay of Bengal, built for Smart India Hackathon.

## Problem

Cyclone trajectory prediction is critical for disaster preparedness in the Bay of Bengal region. This project combines a machine learning model with a real-time GIS dashboard to forecast cyclone positions at 5 time horizons (+6h, +12h, +24h, +48h, +72h).

## Architecture

```
User opens dashboard
  ↓
React + TypeScript + Leaflet renders cyclone map
  ↓
FastAPI inference server (port 8000)
  ↓
Hybrid trajectory prediction:
  ├── Constant Velocity → +6h, +12h
  └── LSTM (M4, 31K params) → +24h, +48h, +72h
  ↓
Forecast coordinates returned as JSON
  ↓
Dashboard renders: forecast line, markers, uncertainty cone
```

If the ML server is unavailable, the dashboard automatically falls back to demonstration forecast data.

## Frontend

- **Framework:** React 19 + TypeScript
- **Build tool:** Vite
- **Map:** Leaflet (react-leaflet) with CartoDB Dark Matter tiles
- **Design:** Dark mission-control GIS aesthetic
- **Components:** Header, OverviewPanel, MapView, CycloneOverlay, RiskOverlay, ForecastPanel, CurrentConditions, CycloneInfo, DetailsPanel, LayerBar, Footer

## ML Pipeline

### Dataset

- **Source:** IBTrACS v04r01 (International Best Track Archive for Climate Stewardship)
- **Provider:** NOAA National Centers for Environmental Information (NCEI)
- **Region:** North Indian Basin, Bay of Bengal (SUBBASIN == "BB")
- **Storms:** 1,186 historical cyclones
- **Observations:** 42,415 position records
- **Time span:** 1842–2024
- **Natural interval:** 3 hours (99.5% of observations)
- **License:** Public domain

To download the dataset:
```bash
cd ml/scripts
python download_data.py
```

### Preprocessing

- Temporal sorting and deduplication per storm
- Feature derivation: displacement (dlat, dlon), speed (km/h), direction (degrees), cyclical time encoding (hour_sin, hour_cos)
- Sequence generation: 4 consecutive observations → 5 future position predictions
- Storm-level train/validation/test split (70%/15%/15%) with no data leakage

### Model

- **Architecture:** 2-layer LSTM → Linear output
  - LSTM(8 features → 64 hidden)
  - LSTM(64 → 32 hidden)
  - Linear(32 → 10 outputs)
- **Parameters:** 31,818
- **Features (8):** lat, lon, dlat, dlon, speed_kmh, direction_deg, hour_sin, hour_cos
- **Excluded:** wind, pressure (89% missing in IBTrACS for North Indian storms)
- **Training:** Adam optimizer, MSE loss, early stopping (patience 25), batch size 256
- **Normalization:** Z-score using training set statistics only

### Hybrid Strategy

Experiments showed different models perform best at different forecast horizons:

| Horizon | Model | Reason |
|---|---|---|
| +6h | Constant Velocity | Linear extrapolation is near-optimal within 12h |
| +12h | Constant Velocity | Recent motion vector dominates |
| +24h | LSTM | Non-linear trajectory patterns emerge |
| +48h | LSTM | Steering currents, curvature |
| +72h | LSTM | Coriolis, recurvature, large-scale flow |

## Results

Test set evaluation using mean Haversine distance error (km):

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---:|---:|---:|---:|---:|---:|
| Persistence | 34.2 | 67.9 | 135.5 | 272.5 | 408.8 | 183.8 |
| Constant Velocity | 12.4 | 25.2 | 58.7 | 147.7 | 255.5 | 99.9 |
| LSTM | 23.3 | 30.7 | 54.0 | 120.0 | 194.2 | 84.4 |
| **Hybrid** | **12.4** | **25.2** | **54.0** | **120.0** | **194.2** | **81.2** |

- Hybrid vs Constant Velocity: **+18.8%** improvement
- Hybrid vs LSTM: **+3.9%** improvement
- Hybrid vs Persistence: **+55.8%** improvement

## How to Run

### Prerequisites

- Python 3.10+
- Node.js 18+

### Setup

```bash
# Install Python dependencies
pip install fastapi uvicorn numpy torch

# Install frontend dependencies
npm install

# Download dataset (optional — processed data is included)
cd ml/scripts
python download_data.py
cd ../..
```

### Run

```bash
# Terminal 1: Start ML inference server
cd ml/api
python server.py

# Terminal 2: Start frontend
npm run dev
```

Open http://localhost:5173 in your browser.

### Fallback Behavior

If the ML server is unavailable (not started, crashed, or unreachable), the dashboard automatically falls back to demonstration forecast data. The footer shows:
- **Green dot "ML FORECAST"** — ML server active, predictions are live
- **Yellow dot "DEMO — API OFFLINE"** — fallback to demonstration data

## Project Structure

```
├── src/                          # Frontend source
│   ├── components/               # React components
│   ├── data/mockCyclone.ts       # Demonstration cyclone data
│   ├── services/mlApi.ts         # ML API fetch wrapper
│   ├── types/cyclone.ts          # TypeScript interfaces
│   └── utils/format.ts           # Formatting utilities
├── ml/                           # Machine learning
│   ├── api/server.py             # FastAPI inference server
│   ├── api/requirements.txt      # Python dependencies
│   ├── scripts/                  # Training pipeline
│   │   ├── download_data.py      # Downloads IBTrACS dataset
│   │   ├── preprocess.py         # Data preprocessing
│   │   ├── train_lstm.py         # LSTM training
│   │   ├── baselines.py          # Baseline models
│   │   ├── evaluate_baselines.py # Baseline evaluation
│   │   └── hybrid.py             # Hybrid inference + evaluation
│   ├── models/trajectory_lstm/   # Trained M4 model
│   │   ├── model.pt              # Model weights (128 KB)
│   │   ├── normalization.npz     # Z-score parameters
│   │   └── config.json           # Model configuration
│   └── data/processed/           # Preprocessed data
│       ├── train.npz             # Training set
│       ├── val.npz               # Validation set
│       ├── test.npz              # Test set
│       └── metadata.json         # Dataset metadata
├── README.md
├── package.json
└── vite.config.ts
```

## Limitations

- **Prototype, not operational** — This is a research/hackathon demonstration, not a meteorological forecasting system
- **Historical data only** — Trained on IBTrACS Bay of Bengal data (1842–2024)
- **Trajectory-only** — Predicts position only, not intensity or wind speed
- **No environmental features** — Does not use sea surface temperature, wind shear, or atmospheric pressure fields
- **No real-time data** — Demonstration uses simulated cyclone track input
- **Deterministic routing** — Hybrid switches by horizon, not learned
- **Uncertainty cone is geometric** — Not a calibrated probability forecast
- **Single basin** — Trained on Bay of Bengal only, not generalizable to other basins without retraining

## Future Work

- Real-time satellite observation integration
- Environmental features (SST, wind shear, steering flow)
- Intensity prediction alongside trajectory
- Learned routing model (instead of deterministic horizon switching)
- Operational meteorological validation
- Multi-basin generalization

## Dataset Attribution

IBTrACS v04r01 — International Best Track Archive for Climate Stewardship
NOAA National Centers for Environmental Information (NCEI)
https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/

## MOSDAC INSAT-3DS Data Pipeline

### Overview

This project includes a modular pipeline for processing **INSAT-3DS MOSDAC** (Meteorological and Oceanographic Satellite Data Archival Centre) satellite data. The pipeline is designed for near-real-time capable data ingestion but currently operates on locally downloaded historical files.

**Status:** Data processing pipeline only — not yet integrated into the trajectory forecast model.

### Products Used

| Product | Description | Key Datasets | Resolution |
|---|---|---|---|
| **3SIMG_L1C_ASIA_MER** | INSAT-3DS Imager Level-1C | IMG_TIR1, IMG_TIR2, IMG_WV, IMG_VIS, IMG_SWIR, IMG_MIR (raw counts + radiance/temp LUTs) | 1616 × 1737 (~4 km) |
| **3SIMG_L2B_CTP** | Cloud Top Properties | CTP (hPa), CTT (K), EFF_EMISS | 313 × 312 |
| **3SIMG_L2B_HEM** | Hydro-Estimator Precipitation | HEM (mm/hr) | 2816 × 2805 |
| **3SIMG_L2B_SST** | Sea Surface Temperature | SST_FCT, SST_REG, SST_VAR (Kelvin) | 2816 × 2805 |

All products share matching timestamps in filenames (e.g., `28AUG2026_0600`).

### Data Placement

Place downloaded `.h5` files in the following structure (already present locally):

```
data_download/
├── 3SIMG_L1C_ASIA_MER/
│   └── 2026/
│       └── 28AUG/
│           └── *.h5
├── 3SIMG_L2B_CTP/
│   └── 2026/
│       └── 28AUG/
│           └── *.h5
├── 3SIMG_L2B_HEM/
│   └── 2026/
│       └── 28AUG/
│           └── *.h5
└── 3SIMG_L2B_SST/
    └── 2026/
        └── 28AUG/
            └── *.h5
```

**Important:** Raw `.h5` files are excluded from Git via `.gitignore`.

### Timestamp Matching

Files are matched by timestamp extracted from filenames:
```
3SIMG_{DDMMMYYYY}_{HHMM}_{PRODUCT}_V01R00.h5
```

Example: `3SIMG_28AUG2026_0600_L1C_ASIA_MER_V01R00.h5` → timestamp key `28AUG2026_0600`

If one product is missing for a timestamp, the observation is marked **incomplete** and logged. Processing continues for other timestamps.

### Processing Pipeline

```
RAW MOSDAC DATA (.h5)
    ↓
TIMESTAMP MATCHING (across 4 products)
    ↓
HDF5 READING (preserves raw counts, calibration LUTs, metadata, lat/lon grids)
    ↓
GEOSPATIAL HANDLING (ROI subsetting via lat/lon masks — NO array resizing)
    ↓
FEATURE EXTRACTION (statistics per band/dataset within ROI)
    ↓
MOSDAC FEATURES (NPZ)
    ↓
FUTURE: ML INTEGRATION (retrain trajectory model with satellite features)
```

**Key principles:**
- Raw L1C counts kept available; calibration applied explicitly via optional functions
- Each product's native lat/lon grid used for ROI subsetting (no reprojection in Phase 1)
- One timestamp processed at a time to control memory (L1C ~28 MB/file)
- Output: `ml/data/mosdac_processed/features_{timestamp}.npz` + grid metadata

### Dependencies

Added to `ml/api/requirements.txt`:
```
h5py>=3.8
pyproj>=3.5
```

### How to Run

#### Prerequisites
```bash
pip install h5py pyproj
```

#### Single Timestamp Test (recommended first)
```bash
cd ml
python -m mosdac.pipeline test 28AUG2026_0600
```

This will:
1. Find the 4 matching `.h5` files for 2026-08-28 06:00 UTC
2. Read all datasets, print shapes/dtypes/min/max/mean/NaN%
3. Extract ROI (Bay of Bengal: 5-25°N, 78-98°E)
4. Compute satellite-derived features
5. Save `features_28AUG2026_0600.npz` and `grid_28AUG2026_0600.json`

#### Batch Process All Timestamps
```bash
cd ml
python -m mosdac.pipeline batch
```

Options:
- `--include-incomplete` — also process timestamps missing one or more products
- `--lat-min/--lat-max/--lon-min/--lon-max` — override ROI
- `--log-level DEBUG` — verbose output

#### Scan Only (no processing)
```bash
cd ml
python -m mosdac.pipeline scan
```

### Output Structure

```
ml/data/mosdac_processed/
├── features_28AUG2026_0600.npz      # Feature arrays + metadata
├── grid_28AUG2026_0600.json         # Grid bounds, projection info
├── ...
├── manifest.json                    # Timestamp matching manifest
└── batch_summary.json               # Batch run summary
```

Each `features_*.npz` contains:
- `feature_array`: flat float32 array of all numeric features
- `feature_names`: list of feature name strings
- `metadata`: JSON with timestamp, ROI bounds, feature count
- `full_features`: JSON with complete nested feature dict

### Current Limitations (Phase 1)

- **No reprojection/resampling** — each product uses its native grid; ROI masking via lat/lon arrays
- **No ML integration yet** — features extracted but not fed to trajectory model
- **Fixed ROI** — Bay of Bengal bounding box (configurable, not cyclone-relative)
- **Historical files only** — not connected to live MOSDAC API/NRT feed
- **Calibration optional** — L1C raw counts preserved; physical conversion via explicit function calls

### Future Work (Post-Phase 1)

- Add `rasterio` for full reprojection to common grid
- Cyclone-relative feature extraction (center detection → radial sectors)
- Integrate MOSDAC features into trajectory LSTM training
- Live/NRT data ingestion from MOSDAC API
- Uncertainty quantification for satellite-derived features
