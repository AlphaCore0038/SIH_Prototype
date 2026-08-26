"""
Minimal FastAPI inference server for hybrid cyclone trajectory prediction.

Loads the trained M4 LSTM model once at startup.
Accepts recent track observations, computes features, returns forecast.

Usage:
  cd ml/api
  python server.py
"""

import math
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Add ml/scripts to sys.path so we can import hybrid module
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from hybrid import load_hybrid, predict_hybrid  # noqa: E402

# ---------------------------------------------------------------------------
# Constants — must match preprocess.py exactly
# ---------------------------------------------------------------------------
KM_PER_DEG_LAT = 111.0
HORIZON_HOURS = [6, 12, 24, 48, 72]

# ---------------------------------------------------------------------------
# Model state
# ---------------------------------------------------------------------------
loaded_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global loaded_model
    try:
        loaded_model = load_hybrid()
        print("[ML API] Model loaded successfully", flush=True)
    except Exception as e:
        print(f"[ML API] WARNING: Model failed to load: {e}", flush=True)
        loaded_model = None
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Cyclone Trajectory ML API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class TrackPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    wind: float | None = None
    timestamp: str | None = None


class ForecastRequest(BaseModel):
    track: list[TrackPoint] = Field(..., min_length=4, max_length=4)


class ForecastPoint(BaseModel):
    hoursAhead: int
    lat: float
    lon: float


class ForecastResponse(BaseModel):
    forecast: list[ForecastPoint]
    model: str
    source: str


# ---------------------------------------------------------------------------
# Feature construction — replicates preprocess.py exactly
# ---------------------------------------------------------------------------
def compute_features(track: list[TrackPoint]) -> np.ndarray:
    """
    Build (4, 10) feature array from 4 raw track points.

    Feature order (preprocess.py line 226):
      [lat, lon, wind, pressure, dlat, dlon,
       speed_kmh, direction_deg, hour_sin, hour_cos]

    First point gets zeros for derived features (no prior observation).
    """
    n = len(track)
    arr = np.zeros((n, 10), dtype=np.float64)

    # Parse timestamps for hour encoding
    hours = []
    for pt in track:
        if pt.timestamp:
            try:
                dt = datetime.fromisoformat(pt.timestamp.replace("Z", "+00:00"))
                h = dt.hour + dt.minute / 60.0
            except ValueError:
                h = 0.0
        else:
            h = 0.0
        hours.append(h)

    for i, pt in enumerate(track):
        arr[i, 0] = pt.lat                    # lat
        arr[i, 1] = pt.lon                    # lon
        arr[i, 2] = pt.wind or 0.0            # wind (0 if missing)
        arr[i, 3] = 0.0                       # pressure (not available)
        arr[i, 8] = math.sin(2 * math.pi * hours[i] / 24)  # hour_sin
        arr[i, 9] = math.cos(2 * math.pi * hours[i] / 24)  # hour_cos

        if i == 0:
            continue

        # dt_hours from timestamps
        if track[i].timestamp and track[i - 1].timestamp:
            try:
                t0 = datetime.fromisoformat(track[i - 1].timestamp.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(track[i].timestamp.replace("Z", "+00:00"))
                dt_hours = (t1 - t0).total_seconds() / 3600.0
            except ValueError:
                dt_hours = 3.0
        else:
            dt_hours = 3.0

        if dt_hours <= 0:
            dt_hours = 3.0

        # Displacement (preprocess.py lines 173-181)
        dlat = track[i].lat - track[i - 1].lat
        dlon = track[i].lon - track[i - 1].lon
        km_north = dlat * KM_PER_DEG_LAT
        km_east = dlon * KM_PER_DEG_LAT * math.cos(math.radians(track[i].lat))
        displacement_km = math.sqrt(km_north ** 2 + km_east ** 2)

        # Speed (preprocess.py line 184)
        speed_kmh = displacement_km / dt_hours

        # Direction (preprocess.py lines 187-188)
        direction_rad = math.atan2(km_east, km_north)
        direction_deg = math.degrees(direction_rad) % 360

        arr[i, 4] = dlat
        arr[i, 5] = dlon
        arr[i, 6] = speed_kmh
        arr[i, 7] = direction_deg

    return arr.astype(np.float32)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": loaded_model is not None,
    }


# ---------------------------------------------------------------------------
# Forecast endpoint
# ---------------------------------------------------------------------------
@app.post("/api/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    if loaded_model is None:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    # Build feature array from raw track points
    features = compute_features(req.track)  # (4, 10)

    # Run hybrid inference
    try:
        results, raw_preds = predict_hybrid(loaded_model, features)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    # Validate predictions
    forecast_points = []
    for pt in results[0]:  # single sample
        lat = pt["lat"]
        lon = pt["lon"]
        if not (math.isfinite(lat) and math.isfinite(lon)):
            raise HTTPException(
                status_code=500,
                detail=f"Invalid prediction: lat={lat}, lon={lon}",
            )
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(
                status_code=500,
                detail=f"Prediction out of range: lat={lat}, lon={lon}",
            )
        forecast_points.append(ForecastPoint(
            hoursAhead=pt["hoursAhead"],
            lat=round(lat, 4),
            lon=round(lon, 4),
        ))

    return ForecastResponse(
        forecast=forecast_points,
        model="hybrid_cv_lstm",
        source="ml",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("Cyclone Trajectory ML API")
    print("=" * 50)
    print(f"  Model dir: {SCRIPTS_DIR.parent / 'models' / 'trajectory_lstm'}")
    print(f"  CORS: localhost:5173")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
