"""
Evaluate baseline trajectory models on the test set.

Metric: Great-circle distance (Haversine) in kilometers.

Usage:
  python evaluate_baselines.py
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Add parent to path so we can import baselines
sys.path.insert(0, str(Path(__file__).resolve().parent))
from baselines import persistence, constant_velocity, HORIZON_STEPS

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
HORIZON_LABELS = ["+6h", "+12h", "+24h", "+48h", "+72h"]
EARTH_RADIUS_KM = 6371.0


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    """
    Great-circle distance between two points using Haversine formula.

    All inputs in degrees. Returns distance in kilometers.
    Handles array inputs via numpy.
    """
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_KM * c


# ---------------------------------------------------------------------------
# Evaluate one model
# ---------------------------------------------------------------------------
def evaluate_model(name, preds, targets):
    """
    Compute Haversine error at each horizon.

    Args:
        name: model name
        preds: (N, 10) predicted [lat6h, lon6h, ...]
        targets: (N, 10) actual [lat6h, lon6h, ...]

    Returns:
        dict with per-horizon and overall stats
    """
    results = {"model": name, "horizons": {}, "overall": {}}

    all_errors = []

    for i, label in enumerate(HORIZON_LABELS):
        pred_lat = preds[:, i * 2]
        pred_lon = preds[:, i * 2 + 1]
        true_lat = targets[:, i * 2]
        true_lon = targets[:, i * 2 + 1]

        errors = haversine_km(pred_lat, pred_lon, true_lat, true_lon)
        all_errors.append(errors)

        results["horizons"][label] = {
            "mean": float(np.mean(errors)),
            "median": float(np.median(errors)),
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "max": float(np.max(errors)),
            "std": float(np.std(errors)),
        }

    all_errors = np.concatenate(all_errors)
    results["overall"] = {
        "mean": float(np.mean(all_errors)),
        "median": float(np.median(all_errors)),
        "rmse": float(np.sqrt(np.mean(all_errors ** 2))),
    }

    return results


# ---------------------------------------------------------------------------
# Print results table
# ---------------------------------------------------------------------------
def print_table(all_results):
    print("\n" + "=" * 72)
    print("BASELINE EVALUATION RESULTS (Test Set)")
    print("=" * 72)

    header = f"{'Model':<20}" + "".join(f"{label:>10}" for label in HORIZON_LABELS) + f"{'Overall':>10}"
    print(header)
    print("-" * 72)

    for res in all_results:
        row = f"{res['model']:<20}"
        for label in HORIZON_LABELS:
            row += f"{res['horizons'][label]['mean']:>10.1f}"
        row += f"{res['overall']['mean']:>10.1f}"
        print(row)

    print("-" * 72)
    print("Values: Mean Haversine distance error (km)")
    print()


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------
def plot_comparison(all_results):
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(HORIZON_LABELS))
    width = 0.35
    colors = ["#ef4444", "#3b82f6", "#22c55e"]

    for i, res in enumerate(all_results):
        means = [res["horizons"][label]["mean"] for label in HORIZON_LABELS]
        medians = [res["horizons"][label]["median"] for label in HORIZON_LABELS]
        offset = (i - len(all_results) / 2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, label=f"{res['model']} (mean)",
                      color=colors[i], alpha=0.8)
        ax.scatter(x + offset, medians, color=colors[i], marker="D", s=30, zorder=5)

    ax.set_xlabel("Forecast Horizon")
    ax.set_ylabel("Error (km)")
    ax.set_title("Baseline Model Comparison — Test Set")
    ax.set_xticks(x)
    ax.set_xticklabels(HORIZON_LABELS)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    out = PROCESSED_DIR / "baseline_comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading test data...")
    test = np.load(PROCESSED_DIR / "test.npz")
    inputs, targets = test["inputs"], test["targets"]
    print(f"  Test sequences: {len(inputs)}")
    print(f"  Input shape: {inputs.shape}")
    print(f"  Target shape: {targets.shape}")

    # Sanity checks
    assert not np.isnan(inputs).any(), "NaN in inputs"
    assert not np.isnan(targets).any(), "NaN in targets"
    assert inputs.shape[0] == targets.shape[0], "Input/target length mismatch"
    print("  Sanity checks passed.")

    # Run baselines
    models = [
        ("Persistence", persistence(inputs)),
        ("Constant Velocity", constant_velocity(inputs)),
    ]

    all_results = []
    for name, preds in models:
        # Validate predictions
        assert not np.isnan(preds).any(), f"NaN in {name} predictions"
        assert preds.shape == targets.shape, f"Shape mismatch for {name}"
        assert np.all(preds[:, 0::2] >= -90) and np.all(preds[:, 0::2] <= 90), \
            f"Invalid lat in {name}"
        assert np.all(preds[:, 1::2] >= -180) and np.all(preds[:, 1::2] <= 180), \
            f"Invalid lon in {name}"

        res = evaluate_model(name, preds, targets)
        all_results.append(res)

    # Print results
    print_table(all_results)

    # Print detailed per-horizon breakdown
    print("DETAILED BREAKDOWN:")
    print("-" * 72)
    for res in all_results:
        print(f"\n{res['model']}:")
        for label in HORIZON_LABELS:
            h = res["horizons"][label]
            print(f"  {label:>5s}: mean={h['mean']:.1f} km, "
                  f"median={h['median']:.1f} km, "
                  f"RMSE={h['rmse']:.1f} km, "
                  f"max={h['max']:.1f} km")

    # Visualization
    plot_comparison(all_results)

    # Save results as JSON
    out_path = PROCESSED_DIR / "baseline_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved: {out_path}")

    # Summary
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    pers_mean = all_results[0]["overall"]["mean"]
    cv_mean = all_results[1]["overall"]["mean"]
    print(f"  Persistence overall mean error:       {pers_mean:.1f} km")
    print(f"  Constant Velocity overall mean error:  {cv_mean:.1f} km")
    if cv_mean < pers_mean:
        pct = (pers_mean - cv_mean) / pers_mean * 100
        print(f"  Constant Velocity is better by {pct:.1f}%")
    else:
        pct = (cv_mean - pers_mean) / cv_mean * 100
        print(f"  Persistence is better by {pct:.1f}%")


if __name__ == "__main__":
    main()
