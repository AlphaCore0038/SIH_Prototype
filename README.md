# Cyclone Intelligence Dashboard

## Problem

Cyclone trajectory prediction for the Bay of Bengal using machine learning.

## Architecture

```
React + TypeScript + Leaflet → FastAPI → Hybrid CV + LSTM → Forecast
```

## Frontend

- React 19
- TypeScript
- Vite
- Leaflet (react-leaflet)
- Dark mission-control GIS aesthetic
- CartoDB Dark Matter tiles

## ML Pipeline

- **Dataset:** IBTrACS v04r01, Bay of Bengal
- **Historical storms used:** 1,186
- **Features:** lat, lon, dlat, dlon, speed, direction, hour_sin, hour_cos
- **Model:** 2-layer LSTM (64 → 32 → Dense(10))
- **Parameters:** 31,818
- **Hybrid routing:**
  - +6h/+12h → Constant Velocity
  - +24h/+48h/+72h → LSTM

## Results

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---:|---:|---:|---:|---:|---:|
| Persistence | 34.2 | 67.9 | 135.5 | 272.5 | 408.8 | 183.8 |
| Constant Velocity | 12.4 | 25.2 | 58.7 | 147.7 | 255.5 | 99.9 |
| LSTM | 23.3 | 30.7 | 54.0 | 120.0 | 194.2 | 84.4 |
| **Hybrid** | **12.4** | **25.2** | **54.0** | **120.0** | **194.2** | **81.2** |

Metric: mean Haversine distance error in km. Lower is better.

## Why Hybrid?

Experiments showed that different models perform best at different forecast horizons:

- **Constant Velocity** performs best at short horizons (+6h, +12h) where cyclone motion is approximately linear.
- **LSTM** performs better at longer horizons (+24h to +72h) where non-linear trajectory patterns (curvature, acceleration, steering flows) accumulate.
- **Hybrid** combines them deterministically by horizon, achieving 81.2 km overall mean error — 18.8% better than Constant Velocity alone and 3.9% better than LSTM alone.

## How to Run

```bash
# Terminal 1: Start ML inference server
cd ml/api
python server.py

# Terminal 2: Start frontend
npm install
npm run dev
```

The dashboard falls back to demonstration forecast data if the ML API is unavailable.

## Limitations

- Research/hackathon prototype
- Trained on historical IBTrACS Bay of Bengal data only
- Not an operational meteorological forecast
- Demonstration uses simulated cyclone input
- No real-time satellite integration
- No environmental features (SST, wind shear)

## Future Work

- Real-time satellite observation integration
- Environmental features (SST, wind shear)
- Operational meteorological validation
- More advanced routing/model architectures
