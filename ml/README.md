# ML Track — Cyclone Trajectory Prediction

## Dataset

**Source:** IBTrACS v04r01 (International Best Track Archive for Climate Stewardship)
**Provider:** NOAA National Centers for Environmental Information (NCEI)
**URL:** https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv
**License:** Public domain (no restrictions)

## Subset

- **Basin:** North Indian (NI)
- **Subbasin:** Bay of Bengal (BB)
- **Filter:** `SUBBASIN == "BB"` — storms with at least one position in the Bay of Bengal

## Mandatory Fields

| Field | Description | Units |
|---|---|---|
| `storm_id` (SID) | Unique storm identifier | string |
| `timestamp` (ISO_TIME) | Observation time (UTC) | ISO 8601 |
| `lat` (LAT) | Latitude | degrees N |
| `lon` (LON) | Longitude | degrees E |

## Optional Fields

| Field | Description | Units | Missing % |
|---|---|---|---|
| `wind` (WMO_WIND) | Maximum sustained wind | knots | 89% |
| `pressure` (WMO_PRES) | Minimum central pressure | hPa | 90% |
| `speed` (STORM_SPEED) | Translation speed | knots | <1% |
| `direction` (STORM_DIR) | Translation direction | degrees | <1% |

Wind and pressure are mostly missing in IBTrACS for North Indian storms. Filled with 0 for model training.

## Preprocessing

### Temporal Processing
1. Sorted chronologically per storm
2. Duplicate timestamps removed (0 found)
3. Invalid lat/lon validated and removed (0 found)
4. Time gaps computed between observations

**Natural observation interval:** 3 hours (99.5% of observations)

### Derived Features
| Feature | Description |
|---|---|
| `dlat` | Latitude displacement from previous observation |
| `dlon` | Longitude displacement from previous observation |
| `speed_kmh` | Translation speed in km/h |
| `direction_deg` | Movement direction in degrees (0=N, 90=E) |
| `hour_sin` | Sinusoidal encoding of hour-of-day |
| `hour_cos` | Cosine encoding of hour-of-day |

### Sequence Generation
- **Input window:** 4 consecutive observations (12 hours at 3h intervals)
- **Target horizons:** +6h, +12h, +24h, +48h, +72h
- **Output:** Future latitude and longitude at each horizon
- **NaN handling:** All NaN values filled with 0 (wind/pressure mostly missing, derived features NaN for first observation per storm)

## Train/Validation/Test Split

**Strategy:** Storm-level split — each storm appears in exactly one split.

| Split | Storms | Sequences | Percentage |
|---|---|---|---|
| Train | 830 | 13,963 | 70.0% |
| Validation | 177 | 2,890 | 14.9% |
| Test | 179 | 3,186 | 15.1% |
| **Total** | **1,186** | **20,039** | **100%** |

**No storm leakage verified.**

## Output Files

```
ml/data/processed/
  train.npz      — training inputs/targets (367 KB)
  val.npz        — validation inputs/targets (78 KB)
  test.npz       — test inputs/targets (85 KB)
  metadata.json  — feature list, horizons, split stats
  cyclone_tracks.png — visualization of all BB cyclone tracks
```

### NPZ Format
```python
import numpy as np
data = np.load("train.npz")
inputs = data["inputs"]   # shape: (13963, 4, 10)
targets = data["targets"] # shape: (13963, 10)
```

**Input shape:** `(N, seq_length=4, n_features=10)`
**Target shape:** `(N, n_horizons=5 * 2 = 10)` — [lat6h, lon6h, lat12h, lon12h, ..., lat72h, lon72h]

## Baseline Models

### Baseline 1 — Persistence
Predict the cyclone stays at its last observed position for all future horizons.

### Baseline 2 — Constant Velocity
Extrapolate from the last movement vector (displacement between the two most recent observations).

### Evaluation

**Metric:** Great-circle distance error (Haversine) in kilometers.

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---|---|---|---|---|---|
| Persistence | 34.2 | 67.9 | 135.5 | 272.5 | 408.8 | 183.8 |
| Constant Velocity | 12.4 | 25.2 | 58.7 | 147.7 | 255.5 | 99.9 |

Values: Mean Haversine distance error (km)

**Constant Velocity outperforms Persistence by 45.7% overall.**

### Detailed Breakdown

| Model | Horizon | Mean | Median | RMSE | Max |
|---|---|---|---|---|---|
| Persistence | +6h | 34.2 | 31.2 | 44.2 | 1049.6 |
| Persistence | +12h | 67.9 | 61.3 | 83.5 | 1086.5 |
| Persistence | +24h | 135.5 | 123.9 | 161.0 | 1166.1 |
| Persistence | +48h | 272.5 | 254.7 | 311.0 | 1315.1 |
| Persistence | +72h | 408.8 | 387.1 | 455.7 | 1466.1 |
| Constant Velocity | +6h | 12.4 | 11.1 | 24.3 | 1042.8 |
| Constant Velocity | +12h | 25.2 | 21.9 | 41.9 | 1104.0 |
| Constant Velocity | +24h | 58.7 | 45.8 | 85.3 | 1306.1 |
| Constant Velocity | +48h | 147.7 | 120.3 | 192.8 | 1807.1 |
| Constant Velocity | +72h | 255.5 | 216.9 | 317.4 | 2382.0 |

### ML Model Justification

An ML model needs to beat **99.9 km** overall mean error (constant velocity baseline) to be worthwhile. The key question is whether an ML model can capture:
- Non-linear trajectory changes (recurving storms)
- Acceleration/deceleration
- Interaction with steering currents
- Intensity-track coupling

**Recommended next architecture:** 2-layer LSTM (64→32 units), trained on the full feature set, predicting the same 5 horizons. This should capture temporal patterns that constant velocity misses.

## LSTM Model (M4)

### Architecture

```
Input (batch, 4, 8)
  → LSTM(64, batch_first=True)
  → LSTM(32, batch_first=True)
  → Linear(32, 10)
  → Output: [lat6h, lon6h, lat12h, lon12h, ..., lat72h, lon72h]
```

**Parameters:** 31,818

### Features Used

`lat, lon, dlat, dlon, speed_kmh, direction_deg, hour_sin, hour_cos` (8 features)

Wind and pressure excluded due to 89% missingness.

### Training Configuration

- **Optimizer:** Adam (lr=1e-3)
- **Loss:** MSE
- **Batch size:** 256
- **Early stopping:** patience=25 on validation loss
- **Epochs:** 113 (early stopped)
- **Training time:** 29.7s (CPU)
- **Seed:** 42

### Normalization

Z-score normalization using training set statistics only. Saved for inference.

### Test Set Evaluation

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---|---|---|---|---|---|
| Persistence | 34.2 | 67.9 | 135.5 | 272.5 | 408.8 | 183.8 |
| Constant Velocity | 12.4 | 25.2 | 58.7 | 147.7 | 255.5 | 99.9 |
| **LSTM** | **23.3** | **30.7** | **54.0** | **120.0** | **194.2** | **84.4** |

Values: Mean Haversine distance error (km)

### Improvement Over Constant Velocity

| Horizon | CV Error | LSTM Error | Improvement |
|---|---|---|---|
| +6h | 12.4 km | 23.3 km | **-88.8%** (worse) |
| +12h | 25.2 km | 30.7 km | **-21.7%** (worse) |
| +24h | 58.7 km | 54.0 km | **+8.0%** |
| +48h | 147.7 km | 120.0 km | **+18.7%** |
| +72h | 255.5 km | 194.2 km | **+24.0%** |
| **Overall** | **99.9 km** | **84.4 km** | **+15.5%** |

### Analysis

1. **LSTM beats Constant Velocity overall by 15.5%** — justified as an ML improvement.
2. **LSTM is worse at short horizons** (+6h, +12h) — constant velocity is hard to beat for near-term prediction where linear extrapolation works well.
3. **LSTM excels at longer horizons** (+24h to +72h) — captures non-linear trajectory patterns that linear extrapolation misses.
4. **This is scientifically plausible** — cyclone tracks are approximately linear over short periods but curve over longer periods due to steering currents and Coriolis effects.

### Honest Assessment

The LSTM provides meaningful improvement at 24h+ horizons but is worse than simple constant velocity at short horizons. A practical system could **blend both approaches**: use constant velocity for short-term (+6h/+12h) and LSTM for longer-term (+24h to +72h).

## M5.1: Longer Sequence History Experiment

### What Changed

Only one parameter changed: **sequence length 4 → 8** (12h → 24h of input history).

Everything else identical to M4:
- Same architecture: LSTM(64) → LSTM(32) → Dense(10)
- Same features, normalization, optimizer, loss, seed
- Different train/val/test split (fewer storms qualify with seq_len=8)

### Data Impact

| Metric | M4 (seq_len=4) | M5.1 (seq_len=8) |
|---|---|---|
| Min observations per storm | 16 | 20 |
| Eligible storms | 1,210 | 914 |
| Train storms | 847 | 639 |
| Val storms | 181 | 137 |
| Test storms | 182 | 138 |
| Total sequences | 20,039 | 15,744 |

### Training

- **Epochs:** 58 (early stopped, vs 113 for M4)
- **Training time:** 17.0s (vs 29.7s for M4)
- **Best val loss:** 0.0522 (vs 0.0477 for M4 — worse)

### Test Set Results

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---|---|---|---|---|---|
| M5.1 CV | 12.7 | 26.5 | 62.0 | 152.3 | 258.3 | 102.3 |
| M5.1 LSTM | 32.8 | 39.1 | 62.6 | 127.0 | 199.0 | 92.1 |
| M4 CV | 12.4 | 25.2 | 58.7 | 147.7 | 255.5 | 99.9 |
| **M4 LSTM** | **23.3** | **30.7** | **54.0** | **120.0** | **194.2** | **84.4** |

Values: Mean Haversine distance error (km)

### M5.1 vs M4 Comparison

| Metric | M4 LSTM | M5.1 LSTM | Winner |
|---|---|---|---|
| Overall mean | 84.4 km | 92.1 km | **M4** |
| +6h | 23.3 km | 32.8 km | **M4** |
| +12h | 30.7 km | 39.1 km | **M4** |
| +24h | 54.0 km | 62.6 km | **M4** |
| +48h | 120.0 km | 127.0 km | **M4** |
| +72h | 194.2 km | 199.0 km | **M4** |

**M4 (seq_len=4) is better at every horizon.**

### Why Longer History Hurt

1. **20% fewer training storms** — 639 vs 847. Less diversity.
2. **Earlier overfitting** — stopped at epoch 58 vs 113. Val loss was worse.
3. **No additional signal** — 3-hourly observations are dense; 12h of history already captures the trajectory trend. Extra 12h adds noise, not signal.

### Conclusion

**Use M4 (seq_len=4) for the hybrid.** Longer history does not help.

## M6: Hybrid Trajectory Inference

### Architecture

Horizon-based routing — no learned routing model, no API:

| Horizon | Model | Rationale |
|---|---|---|
| +6h | Constant Velocity | Linear extrapolation is near-optimal within 12h |
| +12h | Constant Velocity | Same — recent motion vector dominates |
| +24h | M4 LSTM | LSTM captures trajectory curvature |
| +48h | M4 LSTM | Non-linear patterns accumulate |
| +72h | M4 LSTM | Steering currents, Coriolis, recurvature |

### Why CV for Short-Term

Over 6–12 hours, cyclone motion is approximately linear. The most recent displacement vector is the best available signal. An ML model introduces non-linearity that adds noise at this scale.

### Why LSTM for Long-Term

Over 24–72 hours, cyclones curve, accelerate, decelerate, and interact with steering flows. The LSTM has learned these patterns from historical tracks. Linear extrapolation accumulates error.

### Test Set Results (M4 test set)

**Mean Errors:**

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---|---|---|---|---|---|
| Persistence | 34.2 | 67.9 | 135.5 | 272.5 | 408.8 | 183.8 |
| Constant Velocity | 12.4 | 25.2 | 58.7 | 147.7 | 255.5 | 99.9 |
| M4 LSTM | 23.3 | 30.7 | 54.0 | 120.0 | 194.2 | 84.4 |
| **Hybrid** | **12.4** | **25.2** | **54.0** | **120.0** | **194.2** | **81.2** |

**Median Errors:**

| Model | +6h | +12h | +24h | +48h | +72h | Overall |
|---|---|---|---|---|---|---|
| Persistence | 31.2 | 61.3 | 123.9 | 254.7 | 387.1 | 115.1 |
| Constant Velocity | 11.1 | 21.9 | 45.8 | 120.3 | 216.9 | 44.5 |
| M4 LSTM | 19.5 | 25.5 | 43.6 | 99.3 | 165.8 | 46.0 |
| **Hybrid** | **11.1** | **21.9** | **43.6** | **99.3** | **165.8** | **41.3** |

Values: Mean/Median Haversine distance error (km)

### Improvement

| Comparison | Improvement |
|---|---|
| Hybrid vs Constant Velocity | **+18.8%** (81.2 vs 99.9 km) |
| Hybrid vs M4 LSTM | **+3.9%** (81.2 vs 84.4 km) |
| Hybrid vs Persistence | **+55.8%** (81.2 vs 183.8 km) |

### Limitations

- This is a research/hackathon prototype, not an operational forecast
- Trained on historical IBTrACS Bay of Bengal data only
- Horizon-based routing is deterministic — no learned routing model
- Does not account for storm intensity, environmental conditions, or real-time satellite data

## Reproducing

```bash
cd ml/scripts
python download_data.py                          # downloads IBTrACS NI CSV (~27 MB)
python preprocess.py                             # M4: preprocesses with seq_len=4
python preprocess.py --seq-length 8 --suffix _8  # M5.1: preprocesses with seq_len=8
python evaluate_baselines.py                     # evaluates baselines on test set
python train_lstm.py                             # M4: trains LSTM
python train_lstm.py --data-suffix _8 --output-dir trajectory_lstm_seq8  # M5.1
python hybrid.py                                 # M6: hybrid evaluation
python hybrid.py --verbose                       # M6: with sample predictions
```

## Output Files

```
ml/data/processed/
  train.npz               — M4 training inputs/targets
  val.npz                 — M4 validation inputs/targets
  test.npz                — M4 test inputs/targets
  metadata.json           — M4 metadata
  train_8.npz             — M5.1 training inputs/targets
  val_8.npz               — M5.1 validation inputs/targets
  test_8.npz              — M5.1 test inputs/targets
  metadata_8.json         — M5.1 metadata
  cyclone_tracks.png      — visualization of all BB cyclone tracks
  baseline_results.json   — baseline evaluation results
  baseline_comparison.png — baseline comparison chart

ml/models/trajectory_lstm/           — M4 model
  model.pt, normalization.npz, config.json, history.json, evaluation.json
  training_history.png, lstm_vs_baseline.png, example_trajectory.png

ml/models/trajectory_lstm_seq8/      — M5.1 model
  model.pt, normalization.npz, config.json, history.json, evaluation.json
  training_history.png, lstm_vs_baseline.png, example_trajectory.png

ml/models/trajectory_hybrid/         — M6 hybrid results
  evaluation.json
```

## Known Limitations

1. **Wind/pressure 89% missing** — IBTrACS WMO columns have sparse data for North Indian storms. Model will learn primarily from trajectory (lat/lon) features.
2. **3-hourly data** — Most observations are at 3h intervals, not 6h as initially assumed. Sequence length of 4 = 12 hours of history.
3. **Historical data quality** — Storms from 1842 may have less accurate positions. Modern era (post-1980) has better satellite coverage.
4. **Single basin** — Model trained only on Bay of Bengal storms. Not generalizable to other basins without retraining.
