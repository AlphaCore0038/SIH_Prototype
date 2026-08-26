"""
Hybrid trajectory inference: Constant Velocity (short-term) + LSTM (long-term).

+6h, +12h → Constant Velocity
+24h, +48h, +72h → LSTM

Loads saved M4 model, evaluates on M4 test set.

Usage:
  python hybrid.py
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

SCRIPT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = SCRIPT_DIR.parent / "data" / "processed"
MODEL_DIR = SCRIPT_DIR.parent / "models" / "trajectory_lstm"
HORIZON_LABELS = ["+6h", "+12h", "+24h", "+48h", "+72h"]
HORIZON_HOURS = [6, 12, 24, 48, 72]
HORIZON_STEPS = [1, 2, 4, 8, 12]
EARTH_RADIUS_KM = 6371.0
FEATURE_INDICES = [0, 1, 4, 5, 6, 7, 8, 9]
FEATURE_COLS = ["lat", "lon", "dlat", "dlon", "speed_kmh", "direction_deg",
                "hour_sin", "hour_cos"]


# ---------------------------------------------------------------------------
# Model (copied from train_lstm.py — must match exactly)
# ---------------------------------------------------------------------------
class TrajectoryLSTM(nn.Module):
    def __init__(self, n_features, hidden1=64, hidden2=32, n_outputs=10):
        super().__init__()
        self.lstm1 = nn.LSTM(n_features, hidden1, batch_first=True)
        self.lstm2 = nn.LSTM(hidden1, hidden2, batch_first=True)
        self.fc = nn.Linear(hidden2, n_outputs)

    def forward(self, x):
        out, _ = self.lstm1(x)
        out, _ = self.lstm2(out)
        out = self.fc(out[:, -1, :])
        return out


# ---------------------------------------------------------------------------
# Normalizer (copied from train_lstm.py — must match exactly)
# ---------------------------------------------------------------------------
class Normalizer:
    def __init__(self):
        self.mean = None
        self.std = None

    def transform(self, data):
        return (data - self.mean) / self.std

    def load(self, path):
        npz = np.load(path)
        self.mean = npz["mean"]
        self.std = npz["std"]


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# Constant Velocity (from baselines.py — inlined for independence)
# ---------------------------------------------------------------------------
def constant_velocity(inputs: np.ndarray) -> np.ndarray:
    last_lat = inputs[:, -1, 0]
    last_lon = inputs[:, -1, 1]
    prev_lat = inputs[:, -2, 0]
    prev_lon = inputs[:, -2, 1]
    dlat_per_step = last_lat - prev_lat
    dlon_per_step = last_lon - prev_lon
    preds = np.zeros((len(inputs), 10), dtype=np.float32)
    for i, steps in enumerate(HORIZON_STEPS):
        preds[:, i * 2] = last_lat + dlat_per_step * steps
        preds[:, i * 2 + 1] = last_lon + dlon_per_step * steps
    return preds


# ---------------------------------------------------------------------------
# Load hybrid model
# ---------------------------------------------------------------------------
def load_hybrid():
    """Load LSTM model + normalizer from saved M4 files."""
    with open(MODEL_DIR / "config.json") as f:
        cfg = json.load(f)

    model = TrajectoryLSTM(
        n_features=cfg["n_features"],
        hidden1=cfg["hidden1"],
        hidden2=cfg["hidden2"],
        n_outputs=cfg["n_outputs"],
    )
    model.load_state_dict(torch.load(MODEL_DIR / "model.pt", weights_only=True))
    model.eval()

    normalizer = Normalizer()
    normalizer.load(MODEL_DIR / "normalization.npz")

    return {"model": model, "normalizer": normalizer, "config": cfg}


# ---------------------------------------------------------------------------
# Predict hybrid
# ---------------------------------------------------------------------------
def predict_hybrid(loaded, inputs_raw: np.ndarray) -> list:
    """
    Hybrid prediction: CV for +6h/+12h, LSTM for +24h/+48h/+72h.

    Args:
        loaded: dict from load_hybrid()
        inputs_raw: np.ndarray shape (N, seq_len, n_features) — raw features
                    (can include wind/pressure, indices 0-9)

    Returns:
        list of dicts with hoursAhead, lat, lon for each horizon
    """
    model = loaded["model"]
    normalizer = loaded["normalizer"]

    # Ensure batch dimension
    if inputs_raw.ndim == 2:
        inputs_raw = inputs_raw[np.newaxis, :]

    n_samples = inputs_raw.shape[0]

    # --- Constant Velocity for ALL horizons first ---
    cv_preds = constant_velocity(inputs_raw)  # (N, 10)

    # --- LSTM for ALL horizons ---
    inputs_selected = inputs_raw[:, :, FEATURE_INDICES].copy()  # (N, 4, 8)
    inputs_norm = normalizer.transform(inputs_selected.astype(np.float32))

    with torch.no_grad():
        tensor = torch.tensor(inputs_norm, dtype=torch.float32)
        lstm_preds_norm = model(tensor).numpy()  # (N, 10)

    # De-normalize LSTM predictions
    lat_mean, lat_std = normalizer.mean[0], normalizer.std[0]
    lon_mean, lon_std = normalizer.mean[1], normalizer.std[1]
    lstm_preds = np.zeros_like(lstm_preds_norm)
    for i in range(0, 10, 2):
        lstm_preds[:, i] = lstm_preds_norm[:, i] * lat_std + lat_mean
        lstm_preds[:, i + 1] = lstm_preds_norm[:, i + 1] * lon_std + lon_mean

    # --- Hybrid routing ---
    hybrid = np.zeros_like(cv_preds)
    hybrid[:, 0:4] = cv_preds[:, 0:4]    # +6h, +12h → CV
    hybrid[:, 4:10] = lstm_preds[:, 4:10]  # +24h, +48h, +72h → LSTM

    # Format output
    results = []
    for j in range(n_samples):
        forecast = []
        for i, hours in enumerate(HORIZON_HOURS):
            forecast.append({
                "hoursAhead": hours,
                "lat": float(hybrid[j, i * 2]),
                "lon": float(hybrid[j, i * 2 + 1]),
            })
        results.append(forecast)

    return results, hybrid


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------
def evaluate_all(test_inputs_raw, test_targets_raw, loaded):
    """Run all models on test set and compute Haversine errors."""
    # Persistence
    last_lat = test_inputs_raw[:, -1, 0]
    last_lon = test_inputs_raw[:, -1, 1]
    pers_preds = np.zeros_like(test_targets_raw)
    for i in range(5):
        pers_preds[:, i * 2] = last_lat
        pers_preds[:, i * 2 + 1] = last_lon

    # Constant Velocity
    cv_preds = constant_velocity(test_inputs_raw)

    # LSTM
    model = loaded["model"]
    normalizer = loaded["normalizer"]
    inputs_sel = test_inputs_raw[:, :, FEATURE_INDICES].copy()
    inputs_norm = normalizer.transform(inputs_sel.astype(np.float32))
    with torch.no_grad():
        lstm_norm = model(torch.tensor(inputs_norm, dtype=torch.float32)).numpy()
    lat_m, lat_s = normalizer.mean[0], normalizer.std[0]
    lon_m, lon_s = normalizer.mean[1], normalizer.std[1]
    lstm_preds = np.zeros_like(lstm_norm)
    for i in range(0, 10, 2):
        lstm_preds[:, i] = lstm_norm[:, i] * lat_s + lat_m
        lstm_preds[:, i + 1] = lstm_norm[:, i + 1] * lon_s + lon_m

    # Hybrid
    hybrid_preds = np.zeros_like(cv_preds)
    hybrid_preds[:, 0:4] = cv_preds[:, 0:4]
    hybrid_preds[:, 4:10] = lstm_preds[:, 4:10]

    # Compute errors
    models = {
        "Persistence": pers_preds,
        "Constant Velocity": cv_preds,
        "M4 LSTM": lstm_preds,
        "Hybrid": hybrid_preds,
    }

    all_results = {}
    for name, preds in models.items():
        res = {"model": name, "horizons": {}, "overall": {}}
        all_errors = []
        for i, label in enumerate(HORIZON_LABELS):
            errors = haversine_km(
                preds[:, i * 2], preds[:, i * 2 + 1],
                test_targets_raw[:, i * 2], test_targets_raw[:, i * 2 + 1],
            )
            all_errors.append(errors)
            res["horizons"][label] = {
                "mean": float(np.mean(errors)),
                "median": float(np.median(errors)),
                "rmse": float(np.sqrt(np.mean(errors ** 2))),
            }
        all_cat = np.concatenate(all_errors)
        res["overall"] = {
            "mean": float(np.mean(all_cat)),
            "median": float(np.median(all_cat)),
        }
        all_results[name] = res

    return all_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Hybrid trajectory inference")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 72)
    print("M6: HYBRID TRAJECTORY INFERENCE")
    print("=" * 72)

    # Load M4 test set
    print("\nLoading M4 test set...")
    test_data = np.load(PROCESSED_DIR / "test.npz")
    test_inputs_raw = test_data["inputs"]
    test_targets_raw = test_data["targets"]
    print(f"  Test sequences: {test_inputs_raw.shape[0]}")
    print(f"  Input shape: {test_inputs_raw.shape}")

    # Load hybrid model
    print("Loading hybrid model...")
    loaded = load_hybrid()
    print(f"  LSTM model loaded: {MODEL_DIR / 'model.pt'}")
    print(f"  Normalization loaded: {MODEL_DIR / 'normalization.npz'}")

    # Evaluate all models
    print("\nEvaluating all models on test set...")
    results = evaluate_all(test_inputs_raw, test_targets_raw, loaded)

    # Print comparison table
    print("\n" + "=" * 72)
    print("TEST SET EVALUATION — COMPLETE COMPARISON")
    print("=" * 72)
    header = f"{'Model':<20}" + "".join(f"{h:>10}" for h in HORIZON_LABELS) + f"{'Overall':>10}"
    print(header)
    print("-" * 72)

    for name in ["Persistence", "Constant Velocity", "M4 LSTM", "Hybrid"]:
        res = results[name]
        row = f"{res['model']:<20}"
        for h in HORIZON_LABELS:
            row += f"{res['horizons'][h]['mean']:>10.1f}"
        row += f"{res['overall']['mean']:>10.1f}"
        print(row)

    print("-" * 72)
    print("Values: Mean Haversine distance error (km)")

    # Median table
    print("\nMEDIAN ERRORS:")
    header2 = f"{'Model':<20}" + "".join(f"{h:>10}" for h in HORIZON_LABELS) + f"{'Overall':>10}"
    print(header2)
    print("-" * 72)
    for name in ["Persistence", "Constant Velocity", "M4 LSTM", "Hybrid"]:
        res = results[name]
        row = f"{res['model']:<20}"
        for h in HORIZON_LABELS:
            row += f"{res['horizons'][h]['median']:>10.1f}"
        row += f"{res['overall']['median']:>10.1f}"
        print(row)
    print("-" * 72)
    print("Values: Median Haversine distance error (km)")

    # Hybrid improvement over individual models
    cv = results["Constant Velocity"]
    lstm = results["M4 LSTM"]
    hybrid = results["Hybrid"]

    print("\n" + "=" * 72)
    print("HYBRID vs INDIVIDUAL MODELS")
    print("=" * 72)
    for h in HORIZON_LABELS:
        cv_err = cv["horizons"][h]["mean"]
        lstm_err = lstm["horizons"][h]["mean"]
        hyb_err = hybrid["horizons"][h]["mean"]
        print(f"  {h:>5s}: CV={cv_err:.1f}, LSTM={lstm_err:.1f}, Hybrid={hyb_err:.1f}")

    cv_overall = cv["overall"]["mean"]
    lstm_overall = lstm["overall"]["mean"]
    hyb_overall = hybrid["overall"]["mean"]
    print(f"  Overall: CV={cv_overall:.1f}, LSTM={lstm_overall:.1f}, Hybrid={hyb_overall:.1f}")

    # Verdict
    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    print(f"  Hybrid overall mean: {hyb_overall:.1f} km")
    print(f"  CV overall mean:     {cv_overall:.1f} km")
    print(f"  LSTM overall mean:   {lstm_overall:.1f} km")
    if hyb_overall < cv_overall:
        pct = (cv_overall - hyb_overall) / cv_overall * 100
        print(f"  Hybrid beats CV by {pct:.1f}%")
    if hyb_overall < lstm_overall:
        pct = (lstm_overall - hyb_overall) / lstm_overall * 100
        print(f"  Hybrid beats LSTM by {pct:.1f}%")
    elif hyb_overall > lstm_overall:
        pct = (hyb_overall - lstm_overall) / lstm_overall * 100
        print(f"  Hybrid is {pct:.1f}% worse than LSTM")

    # Save results
    eval_out = {}
    for name, res in results.items():
        eval_out[name] = res
    out_path = MODEL_DIR.parent / "trajectory_hybrid" / "evaluation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(eval_out, f, indent=2)
    print(f"\n  Results saved: {out_path}")

    # Verbose: show a few sample predictions
    if args.verbose:
        print("\n" + "=" * 72)
        print("SAMPLE PREDICTIONS (first 3 sequences)")
        print("=" * 72)
        forecasts, _ = predict_hybrid(loaded, test_inputs_raw[:3])
        for j, fc in enumerate(forecasts):
            print(f"\n  Sequence {j + 1}:")
            for pt in fc:
                print(f"    +{pt['hoursAhead']:2d}h: lat={pt['lat']:.2f}, lon={pt['lon']:.2f}")


if __name__ == "__main__":
    main()
