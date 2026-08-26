# Cyclone Intelligence Dashboard

Prototype ML trajectory forecast for Bay of Bengal cyclones, built for Smart India Hackathon.

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
