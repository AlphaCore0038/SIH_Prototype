"""
Train LSTM model for cyclone trajectory prediction.

Uses PyTorch. Trains on IBTrACS Bay of Bengal data.
Evaluates on test set using Haversine distance.

Usage:
  python train_lstm.py                              # default M4 config
  python train_lstm.py --data-suffix _8 --output-dir trajectory_lstm_seq8  # M5.1
"""

import argparse
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = SCRIPT_DIR.parent / "data" / "processed"
MODEL_DIR = SCRIPT_DIR.parent / "models" / "trajectory_lstm"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

HORIZON_LABELS = ["+6h", "+12h", "+24h", "+48h", "+72h"]
HORIZON_STEPS = [1, 2, 4, 8, 12]  # in 3-hour steps
HORIZON_HOURS = [6, 12, 24, 48, 72]
EARTH_RADIUS_KM = 6371.0
SEED = 42

# Features to use (exclude wind/pressure due to 89% missingness)
FEATURE_COLS = ["lat", "lon", "dlat", "dlon", "speed_kmh", "direction_deg",
                "hour_sin", "hour_cos"]
N_FEATURES = len(FEATURE_COLS)
# Feature indices in the full 10-feature array: [lat, lon, wind, pressure, dlat, dlon, speed_kmh, direction_deg, hour_sin, hour_cos]
FEATURE_INDICES = [0, 1, 4, 5, 6, 7, 8, 9]


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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
# Model
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
        out = self.fc(out[:, -1, :])  # take last time step
        return out


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
class Normalizer:
    """Z-score normalization using training set statistics only."""

    def __init__(self):
        self.mean = None
        self.std = None

    def fit(self, data):
        """Compute mean/std from training data. data: (N, seq_len, n_features)"""
        # Flatten to (N*seq_len, n_features) for per-feature stats
        flat = data.reshape(-1, data.shape[-1])
        self.mean = flat.mean(axis=0)
        self.std = flat.std(axis=0)
        self.std[self.std < 1e-8] = 1.0  # avoid division by zero

    def transform(self, data):
        return (data - self.mean) / self.std

    def inverse_transform_features(self, data):
        """Un-normalize feature-space data."""
        return data * self.std + self.mean

    def save(self, path):
        np.savez(path, mean=self.mean, std=self.std)

    def load(self, path):
        npz = np.load(path)
        self.mean = npz["mean"]
        self.std = npz["std"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_split(name):
    data = np.load(PROCESSED_DIR / f"{name}.npz")
    return data["inputs"], data["targets"]


def prepare_data(inputs_raw, targets_raw, normalizer=None, fit=False):
    """
    Select features and normalize inputs.
    Targets: normalize lat/lon using input statistics for consistency.
    """
    # Select features
    inputs = inputs_raw[:, :, FEATURE_INDICES].copy()

    if fit:
        normalizer.fit(inputs)

    inputs_norm = normalizer.transform(inputs)

    # Normalize targets: lat/lon using same stats as input lat/lon
    lat_mean, lat_std = normalizer.mean[0], normalizer.std[0]
    lon_mean, lon_std = normalizer.mean[1], normalizer.std[1]

    targets = targets_raw.copy()
    # Target layout: [lat6h, lon6h, lat12h, lon12h, ...]
    for i in range(0, targets.shape[1], 2):
        targets[:, i] = (targets[:, i] - lat_mean) / lat_std
        targets[:, i + 1] = (targets[:, i + 1] - lon_mean) / lon_std

    return inputs_norm.astype(np.float32), targets.astype(np.float32)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train_model(model, train_loader, val_inputs, val_targets, epochs=200,
                lr=1e-3, patience=20):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=10
    )

    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0
    history = {"train_loss": [], "val_loss": []}

    val_tensor = torch.tensor(val_inputs, dtype=torch.float32)
    val_target_tensor = torch.tensor(val_targets, dtype=torch.float32)

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for xb, yb in train_loader:
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / n_batches

        # Validation
        model.eval()
        with torch.no_grad():
            val_pred = model(val_tensor)
            val_loss = criterion(val_pred, val_target_tensor).item()

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= patience:
            print(f"  Early stopping at epoch {epoch + 1}")
            break

        if (epoch + 1) % 20 == 0:
            print(f"  Epoch {epoch + 1:3d}: train={train_loss:.6f}, val={val_loss:.6f}")

    model.load_state_dict(best_state)
    return model, history, best_val_loss


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def evaluate_lstm(model, inputs, targets_raw, normalizer):
    """
    Evaluate LSTM on test set.
    Converts normalized predictions back to lat/lon, computes Haversine error.
    """
    model.eval()
    with torch.no_grad():
        tensor = torch.tensor(inputs, dtype=torch.float32)
        preds_norm = model(tensor).numpy()

    # De-normalize predictions
    lat_mean, lat_std = normalizer.mean[0], normalizer.std[0]
    lon_mean, lon_std = normalizer.mean[1], normalizer.std[1]

    preds = np.zeros_like(preds_norm)
    for i in range(0, preds_norm.shape[1], 2):
        preds[:, i] = preds_norm[:, i] * lat_std + lat_mean
        preds[:, i + 1] = preds_norm[:, i + 1] * lon_std + lon_mean

    # Compute Haversine errors per horizon
    results = {"model": "LSTM", "horizons": {}, "overall": {}}
    all_errors = []

    for i, label in enumerate(HORIZON_LABELS):
        pred_lat = preds[:, i * 2]
        pred_lon = preds[:, i * 2 + 1]
        true_lat = targets_raw[:, i * 2]
        true_lon = targets_raw[:, i * 2 + 1]

        errors = haversine_km(pred_lat, pred_lon, true_lat, true_lon)
        all_errors.append(errors)

        results["horizons"][label] = {
            "mean": float(np.mean(errors)),
            "median": float(np.median(errors)),
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "max": float(np.max(errors)),
        }

    all_errors_cat = np.concatenate(all_errors)
    results["overall"] = {
        "mean": float(np.mean(all_errors_cat)),
        "median": float(np.median(all_errors_cat)),
        "rmse": float(np.sqrt(np.mean(all_errors_cat ** 2))),
    }

    return results, preds


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------
def plot_training_history(history):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(history["train_loss"], label="Train Loss", color="#3b82f6")
    ax.plot(history["val_loss"], label="Val Loss", color="#ef4444")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title("LSTM Training History")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out = MODEL_DIR / "training_history.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_comparison_table(lstm_results, cv_results):
    """Bar chart comparing LSTM vs Constant Velocity."""
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(HORIZON_LABELS))
    width = 0.35

    cv_means = [cv_results["horizons"][h]["mean"] for h in HORIZON_LABELS]
    lstm_means = [lstm_results["horizons"][h]["mean"] for h in HORIZON_LABELS]

    bars1 = ax.bar(x - width / 2, cv_means, width, label="Constant Velocity",
                   color="#3b82f6", alpha=0.8)
    bars2 = ax.bar(x + width / 2, lstm_means, width, label="LSTM",
                   color="#22c55e", alpha=0.8)

    # Add value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Forecast Horizon")
    ax.set_ylabel("Mean Error (km)")
    ax.set_title("LSTM vs Constant Velocity — Test Set")
    ax.set_xticks(x)
    ax.set_xticklabels(HORIZON_LABELS)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    out = MODEL_DIR / "lstm_vs_baseline.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def plot_example_trajectory(inputs_raw, targets_raw, lstm_preds, cv_preds, idx=0):
    """Plot a single storm trajectory comparison."""
    fig, ax = plt.subplots(figsize=(10, 8))

    # Historical track (from input)
    hist_lat = inputs_raw[idx, :, 0]
    hist_lon = inputs_raw[idx, :, 1]
    ax.plot(hist_lon, hist_lat, "ko-", markersize=6, label="Historical (input)", zorder=5)

    # Actual future track
    true_lats = [targets_raw[idx, i * 2] for i in range(5)]
    true_lons = [targets_raw[idx, i * 2 + 1] for i in range(5)]
    ax.plot(true_lons, true_lats, "gs-", markersize=8, linewidth=2, label="Actual", zorder=4)

    # Constant velocity predictions
    cv_lats = [cv_preds[idx, i * 2] for i in range(5)]
    cv_lons = [cv_preds[idx, i * 2 + 1] for i in range(5)]
    ax.plot(cv_lons, cv_lats, "b^--", markersize=7, label="Constant Velocity", zorder=3)

    # LSTM predictions
    lstm_lats = [lstm_preds[idx, i * 2] for i in range(5)]
    lstm_lons = [lstm_preds[idx, i * 2 + 1] for i in range(5)]
    ax.plot(lstm_lons, lstm_lats, "r*--", markersize=9, label="LSTM", zorder=3)

    # Annotate horizons
    for i, label in enumerate(HORIZON_LABELS):
        ax.annotate(label, (true_lons[i], true_lats[i]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)

    ax.set_xlabel("Longitude (E)")
    ax.set_ylabel("Latitude (N)")
    ax.set_title("Cyclone Trajectory Comparison")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    out = MODEL_DIR / "example_trajectory.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Train LSTM trajectory model")
    parser.add_argument("--data-suffix", type=str, default="",
                        help="Suffix for input data files (e.g., '_8')")
    parser.add_argument("--output-dir", type=str, default="trajectory_lstm",
                        help="Output directory name under ml/models/")
    args = parser.parse_args()

    model_dir = SCRIPT_DIR.parent / "models" / args.output_dir
    model_dir.mkdir(parents=True, exist_ok=True)

    # Override global MODEL_DIR for this run
    global MODEL_DIR
    MODEL_DIR = model_dir

    set_seed(SEED)

    print("=" * 60)
    print(f"LSTM CYCLONE TRAJECTORY MODEL (data_suffix='{args.data_suffix}')")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    train_inputs_raw, train_targets_raw = load_split(f"train{args.data_suffix}")
    val_inputs_raw, val_targets_raw = load_split(f"val{args.data_suffix}")
    test_inputs_raw, test_targets_raw = load_split(f"test{args.data_suffix}")

    print(f"  Train: {train_inputs_raw.shape}")
    print(f"  Val:   {val_inputs_raw.shape}")
    print(f"  Test:  {test_inputs_raw.shape}")

    # Select features and normalize
    print("\nPreparing data...")
    normalizer = Normalizer()
    train_x, train_y = prepare_data(train_inputs_raw, train_targets_raw,
                                     normalizer, fit=True)
    val_x, val_y = prepare_data(val_inputs_raw, val_targets_raw, normalizer)
    test_x, test_y = prepare_data(test_inputs_raw, test_targets_raw, normalizer)

    print(f"  Features: {FEATURE_COLS}")
    print(f"  Input shape: {train_x.shape}")
    print(f"  Target shape: {train_y.shape}")

    # Save normalization
    normalizer.save(MODEL_DIR / "normalization.npz")
    print(f"  Normalization saved.")

    # Create data loader
    train_dataset = TensorDataset(
        torch.tensor(train_x, dtype=torch.float32),
        torch.tensor(train_y, dtype=torch.float32),
    )
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)

    # Build model
    print("\nBuilding model...")
    model = TrajectoryLSTM(n_features=N_FEATURES, hidden1=64, hidden2=32,
                           n_outputs=10)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Architecture: LSTM(64) -> LSTM(32) -> Dense(10)")
    print(f"  Parameters: {n_params:,}")
    print(f"  Input features: {N_FEATURES}")
    print(f"  Sequence length: {train_x.shape[1]}")

    # Train
    print("\nTraining...")
    t0 = time.time()
    model, history, best_val_loss = train_model(
        model, train_loader, val_x, val_y,
        epochs=200, lr=1e-3, patience=25,
    )
    train_time = time.time() - t0
    print(f"  Training time: {train_time:.1f}s")
    print(f"  Best validation loss: {best_val_loss:.6f}")

    # Save model
    torch.save(model.state_dict(), MODEL_DIR / "model.pt")
    print(f"  Model saved: {MODEL_DIR / 'model.pt'}")

    # Save config
    config = {
        "n_features": N_FEATURES,
        "feature_cols": FEATURE_COLS,
        "feature_indices": FEATURE_INDICES,
        "hidden1": 64,
        "hidden2": 32,
        "n_outputs": 10,
        "seq_length": train_x.shape[1],
        "horizon_labels": HORIZON_LABELS,
        "horizon_steps": HORIZON_STEPS,
        "horizon_hours": HORIZON_HOURS,
        "seed": SEED,
        "lr": 1e-3,
        "batch_size": 256,
        "patience": 25,
        "epochs_trained": len(history["train_loss"]),
        "best_val_loss": best_val_loss,
        "training_time_s": train_time,
    }
    with open(MODEL_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Save history
    with open(MODEL_DIR / "history.json", "w") as f:
        json.dump(history, f, indent=2)

    # Plot training history
    print("\nGenerating plots...")
    plot_training_history(history)

    # Evaluate on test set
    print("\nEvaluating on TEST set...")
    # Need raw targets for Haversine
    test_inputs_selected = test_inputs_raw[:, :, FEATURE_INDICES]
    test_x_norm = normalizer.transform(test_inputs_selected.astype(np.float32))
    # Actually, let me re-evaluate with the raw targets from the test set
    # The evaluate_lstm function needs the raw (un-normalized) targets

    # Recreate normalized test inputs for the model
    model.eval()
    with torch.no_grad():
        test_tensor = torch.tensor(test_x, dtype=torch.float32)
        preds_norm = model(test_tensor).numpy()

    # De-normalize predictions
    lat_mean, lat_std = normalizer.mean[0], normalizer.std[0]
    lon_mean, lon_std = normalizer.mean[1], normalizer.std[1]

    lstm_preds = np.zeros_like(preds_norm)
    for i in range(0, preds_norm.shape[1], 2):
        lstm_preds[:, i] = preds_norm[:, i] * lat_std + lat_mean
        lstm_preds[:, i + 1] = preds_norm[:, i + 1] * lon_std + lon_mean

    # Load constant velocity predictions for comparison
    # Re-run constant velocity on test set
    from baselines import constant_velocity
    cv_preds = constant_velocity(test_inputs_raw)

    # Evaluate both
    def eval_predictions(preds, targets_raw, name):
        results = {"model": name, "horizons": {}, "overall": {}}
        all_errors = []
        for i, label in enumerate(HORIZON_LABELS):
            errors = haversine_km(
                preds[:, i * 2], preds[:, i * 2 + 1],
                targets_raw[:, i * 2], targets_raw[:, i * 2 + 1],
            )
            all_errors.append(errors)
            results["horizons"][label] = {
                "mean": float(np.mean(errors)),
                "median": float(np.median(errors)),
                "rmse": float(np.sqrt(np.mean(errors ** 2))),
            }
        all_cat = np.concatenate(all_errors)
        results["overall"] = {
            "mean": float(np.mean(all_cat)),
            "median": float(np.median(all_cat)),
        }
        return results

    lstm_results = eval_predictions(lstm_preds, test_targets_raw, "LSTM")
    cv_results = eval_predictions(cv_preds, test_targets_raw, "Constant Velocity")

    # Print comparison
    print("\n" + "=" * 72)
    print("TEST SET EVALUATION")
    print("=" * 72)
    header = f"{'Model':<20}" + "".join(f"{h:>10}" for h in HORIZON_LABELS) + f"{'Overall':>10}"
    print(header)
    print("-" * 72)

    for res in [cv_results, lstm_results]:
        row = f"{res['model']:<20}"
        for h in HORIZON_LABELS:
            row += f"{res['horizons'][h]['mean']:>10.1f}"
        row += f"{res['overall']['mean']:>10.1f}"
        print(row)

    print("-" * 72)
    print("Values: Mean Haversine distance error (km)")

    # Improvement
    print("\n" + "=" * 72)
    print("IMPROVEMENT OVER CONSTANT VELOCITY")
    print("=" * 72)
    for h in HORIZON_LABELS:
        cv_err = cv_results["horizons"][h]["mean"]
        lstm_err = lstm_results["horizons"][h]["mean"]
        pct = (cv_err - lstm_err) / cv_err * 100
        print(f"  {h:>5s}: CV={cv_err:.1f} km, LSTM={lstm_err:.1f} km, "
              f"improvement={pct:+.1f}%")

    overall_cv = cv_results["overall"]["mean"]
    overall_lstm = lstm_results["overall"]["mean"]
    overall_pct = (overall_cv - overall_lstm) / overall_cv * 100
    print(f"  Overall: CV={overall_cv:.1f} km, LSTM={overall_lstm:.1f} km, "
          f"improvement={overall_pct:+.1f}%")

    # Save evaluation results
    eval_out = {
        "cv_results": cv_results,
        "lstm_results": lstm_results,
        "improvement": {
            h: {
                "cv_mean": cv_results["horizons"][h]["mean"],
                "lstm_mean": lstm_results["horizons"][h]["mean"],
                "pct_improvement": (cv_results["horizons"][h]["mean"] -
                                    lstm_results["horizons"][h]["mean"]) /
                                   cv_results["horizons"][h]["mean"] * 100,
            }
            for h in HORIZON_LABELS
        },
    }
    with open(MODEL_DIR / "evaluation.json", "w") as f:
        json.dump(eval_out, f, indent=2)

    # Visualizations
    plot_comparison_table(lstm_results, cv_results)
    plot_example_trajectory(test_inputs_raw, test_targets_raw, lstm_preds, cv_preds, idx=0)

    # Summary
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"  Model: TrajectoryLSTM (LSTM 64 -> LSTM 32 -> Dense 10)")
    print(f"  Parameters: {n_params:,}")
    print(f"  Training time: {train_time:.1f}s")
    print(f"  Epochs: {len(history['train_loss'])}")
    print(f"  Best val loss: {best_val_loss:.6f}")
    print(f"  Overall LSTM error: {overall_lstm:.1f} km")
    print(f"  Overall CV error:   {overall_cv:.1f} km")
    print(f"  Improvement:        {overall_pct:+.1f}%")
    if overall_lstm < overall_cv:
        print(f"  RESULT: LSTM BEATS Constant Velocity baseline")
    else:
        print(f"  RESULT: LSTM does NOT beat Constant Velocity baseline")
    print(f"\n  Output dir: {MODEL_DIR}")


if __name__ == "__main__":
    main()
