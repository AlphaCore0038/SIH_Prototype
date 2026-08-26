"""
Preprocess IBTrACS North Indian Basin data for cyclone trajectory prediction.

Produces:
  processed/train.npz, val.npz, test.npz
  processed/stats.json
  processed/cyclone_tracks.png  (simple track visualization)

Usage:
  python preprocess.py                          # default seq_length=4
  python preprocess.py --seq-length 8           # seq_length=8
  python preprocess.py --seq-length 8 --suffix _8  # output files: train_8.npz etc.
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_CSV = SCRIPT_DIR.parent / "data" / "raw" / "ibtracs_NI.csv"
PROCESSED_DIR = SCRIPT_DIR.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load and initial inspection
# ---------------------------------------------------------------------------
def load_raw() -> pd.DataFrame:
    print("=" * 60)
    print("STEP 1: Loading raw IBTrACS data")
    print("=" * 60)
    # IBTrACS CSV has row 0 = column names, row 1 = units, row 2+ = data
    # Read with skiprows=[1] to drop the units row
    df = pd.read_csv(RAW_CSV, low_memory=False, skiprows=[1])
    print(f"  Raw shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Unique storms (SID): {df['SID'].nunique()}")

    # Show sample of key columns
    key_cols = ["SID", "BASIN", "SUBBASIN", "ISO_TIME", "LAT", "LON", "NAME"]
    avail = [c for c in key_cols if c in df.columns]
    print(f"  Sample (first 3 rows of key cols):")
    print(df[avail].head(3).to_string(index=False))
    return df


# ---------------------------------------------------------------------------
# 2. Filter to Bay of Bengal
# ---------------------------------------------------------------------------
def filter_bay_of_bengal(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("STEP 2: Filtering to Bay of Bengal (subbasin == 'BB')")
    print("=" * 60)

    storms_before = df["SID"].nunique()

    # Subbasin BB = Bay of Bengal within North Indian basin
    bb = df[df["SUBBASIN"] == "BB"].copy()
    storms_after = bb["SID"].nunique()

    print(f"  Storms before filter: {storms_before}")
    print(f"  Storms after BB filter: {storms_after}")
    print(f"  Observations: {len(bb)}")
    print(f"  Storms dropped: {storms_before - storms_after}")

    return bb


# ---------------------------------------------------------------------------
# 3. Select and rename mandatory columns
# ---------------------------------------------------------------------------
def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("STEP 3: Selecting mandatory columns")
    print("=" * 60)

    cols = {
        "SID": "storm_id",
        "ISO_TIME": "timestamp",
        "LAT": "lat",
        "LON": "lon",
        "NAME": "name",
        "WMO_WIND": "wind",       # knots
        "WMO_PRES": "pressure",    # hPa
        "STORM_SPEED": "speed",    # knots
        "STORM_DIR": "direction",  # degrees
        "NATURE": "nature",
    }
    avail = {k: v for k, v in cols.items() if k in df.columns}
    out = df[list(avail.keys())].copy()
    out.rename(columns=avail, inplace=True)

    # Convert numeric columns (some IBTrACS values are empty strings)
    for col in ["wind", "pressure", "speed", "direction"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            missing = out[col].isna().sum()
            print(f"  {col}: {missing} missing ({missing/len(out)*100:.1f}%)")

    print(f"  Mandatory columns (storm_id, timestamp, lat, lon): all present")
    print(f"  Optional columns kept: {[c for c in out.columns if c not in ['storm_id','timestamp','lat','lon','name']]}")
    return out


# ---------------------------------------------------------------------------
# 4. Temporal processing
# ---------------------------------------------------------------------------
def process_temporal(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("STEP 4: Temporal processing")
    print("=" * 60)

    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    df = df.sort_values(["storm_id", "timestamp"]).reset_index(drop=True)

    before = len(df)

    # Remove duplicate timestamps per storm
    df = df.drop_duplicates(subset=["storm_id", "timestamp"], keep="first")
    dups = before - len(df)
    print(f"  Duplicate timestamps removed: {dups}")

    # Validate lat/lon ranges
    invalid = (df["lat"].abs() > 90) | (df["lon"].abs() > 180)
    invalid_count = invalid.sum()
    df = df[~invalid].copy()
    print(f"  Invalid lat/lon removed: {invalid_count}")

    # Drop rows where mandatory trajectory info is missing
    mandatory = ["storm_id", "timestamp", "lat", "lon"]
    before_mand = len(df)
    df = df.dropna(subset=mandatory)
    print(f"  Missing mandatory fields removed: {before_mand - len(df)}")

    # Compute time differences within each storm
    df["dt_hours"] = df.groupby("storm_id")["timestamp"].diff().dt.total_seconds() / 3600
    print(f"  Time gap statistics (hours):")
    dt = df["dt_hours"].dropna()
    print(f"    Median: {dt.median():.1f}")
    print(f"    Mean:   {dt.mean():.1f}")
    print(f"    Min:    {dt.min():.1f}")
    print(f"    Max:    {dt.max():.1f}")
    print(f"    Std:    {dt.std():.1f}")

    # Observation interval distribution
    rounded = dt.round().value_counts().sort_index()
    print(f"  Most common intervals (rounded hours):")
    for hrs, count in rounded.head(5).items():
        print(f"    {int(hrs)}h: {count} observations")

    return df


# ---------------------------------------------------------------------------
# 5. Derive trajectory features
# ---------------------------------------------------------------------------
def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("STEP 5: Deriving trajectory features")
    print("=" * 60)

    # Displacement from previous observation
    df["dlat"] = df.groupby("storm_id")["lat"].diff()
    df["dlon"] = df.groupby("storm_id")["lon"].diff()

    # Translation speed in km/h (approximate)
    # 1 degree latitude ~ 111 km, 1 degree longitude ~ 111 * cos(lat) km
    km_per_deg_lat = 111.0
    df["km_north"] = df["dlat"] * km_per_deg_lat
    df["km_east"] = df["dlon"] * km_per_deg_lat * np.cos(np.radians(df["lat"]))
    df["displacement_km"] = np.sqrt(df["km_north"] ** 2 + df["km_east"] ** 2)

    # Speed in km/h
    df["speed_kmh"] = df["displacement_km"] / df["dt_hours"]

    # Direction in degrees (0=north, 90=east)
    df["direction_rad"] = np.arctan2(df["km_east"], df["km_north"])
    df["direction_deg"] = np.degrees(df["direction_rad"]) % 360

    # Cyclical time features (hour of day)
    df["hour"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    print(f"  Derived: dlat, dlon, displacement_km, speed_kmh, direction_deg")
    print(f"  Derived: hour_sin, hour_cos (cyclical time encoding)")
    return df


# ---------------------------------------------------------------------------
# 6. Generate sequences
# ---------------------------------------------------------------------------
def generate_sequences(
    df: pd.DataFrame,
    seq_length: int = 4,
    horizons: list = None,
) -> tuple:
    """
    Create input/target pairs from storm tracks.

    Input:  seq_length consecutive observations -> features
    Target: future lat/lon at each horizon

    Returns:
        inputs:  (N, seq_length, n_features)
        targets: (N, n_horizons * 2)  [lat, lon pairs]
        meta:    list of dicts with storm_id, end_time for each sample
    """
    if horizons is None:
        horizons = [1, 2, 4, 8, 12]  # in 6-hour steps: +6h, +12h, +24h, +48h, +72h

    print("\n" + "=" * 60)
    print(f"STEP 6: Generating sequences (seq_len={seq_length}, horizons={horizons})")
    print("=" * 60)

    feature_cols = ["lat", "lon", "wind", "pressure", "dlat", "dlon",
                    "speed_kmh", "direction_deg", "hour_sin", "hour_cos"]

    # Available features
    avail_features = [c for c in feature_cols if c in df.columns]
    n_features = len(avail_features)
    print(f"  Features used: {avail_features}")
    print(f"  Feature count: {n_features}")

    # Group by storm
    storms = df.groupby("storm_id")
    n_storms = len(storms)

    inputs_list = []
    targets_list = []
    meta_list = []

    storms_used = set()

    for storm_id, group in storms:
        group = group.sort_values("timestamp").reset_index(drop=True)

        if len(group) < seq_length + max(horizons):
            continue

        features = group[avail_features].values
        lats = group["lat"].values
        lons = group["lon"].values

        for i in range(seq_length, len(group) - max(horizons)):
            # Input: seq_length observations before (and including) index i-1
            x = features[i - seq_length: i]

            # Targets: future lat/lon at each horizon
            y = []
            for h in horizons:
                y.extend([lats[i + h - 1], lons[i + h - 1]])

            inputs_list.append(x)
            targets_list.append(y)
            meta_list.append({
                "storm_id": storm_id,
                "end_time": str(group.iloc[i - 1]["timestamp"]),
            })
            storms_used.add(storm_id)

    inputs = np.array(inputs_list, dtype=np.float32)
    targets = np.array(targets_list, dtype=np.float32)

    # Fill NaN:
    # - wind/pressure: ~89% missing in IBTrACS for NI basin, fill with 0
    # - dlat/dlon/speed/direction: NaN for first observation in each storm (no prior obs)
    inputs = np.nan_to_num(inputs, nan=0.0)

    print(f"  Total storms with enough data: {len(storms_used)} / {n_storms}")
    print(f"  Sequences generated: {len(inputs)}")
    print(f"  Input shape:  {inputs.shape}")
    print(f"  Target shape: {targets.shape}")
    print(f"  NaN in inputs after fill: {np.isnan(inputs).sum()}")

    return inputs, targets, meta_list, avail_features


# ---------------------------------------------------------------------------
# 7. Storm-level train/val/test split
# ---------------------------------------------------------------------------
def storm_split(
    inputs: np.ndarray,
    targets: np.ndarray,
    meta: list,
    train_pct: float = 0.70,
    val_pct: float = 0.15,
    seed: int = 42,
) -> dict:
    print("\n" + "=" * 60)
    print("STEP 7: Storm-level train/val/test split")
    print("=" * 60)

    rng = np.random.RandomState(seed)

    # Get unique storm IDs from meta
    storm_ids = list({m["storm_id"] for m in meta})
    rng.shuffle(storm_ids)

    n = len(storm_ids)
    n_train = int(n * train_pct)
    n_val = int(n * val_pct)

    train_storms = set(storm_ids[:n_train])
    val_storms = set(storm_ids[n_train:n_train + n_val])
    test_storms = set(storm_ids[n_train + n_val:])

    # Verify no overlap
    assert not (train_storms & val_storms), "Train/val overlap!"
    assert not (train_storms & test_storms), "Train/test overlap!"
    assert not (val_storms & test_storms), "Val/test overlap!"

    splits = {"train": train_storms, "val": val_storms, "test": test_storms}

    # Partition arrays
    result = {}
    for name, storm_set in splits.items():
        mask = np.array([m["storm_id"] in storm_set for m in meta])
        x_split = inputs[mask]
        y_split = targets[mask]
        meta_split = [m for m, keep in zip(meta, mask) if keep]
        n_storms = len({m["storm_id"] for m in meta_split})

        result[name] = {
            "inputs": x_split,
            "targets": y_split,
            "meta": meta_split,
            "n_storms": n_storms,
        }

        print(f"  {name:6s}: {n_storms:4d} storms, {len(x_split):6d} sequences")

    total_storms = sum(r["n_storms"] for r in result.values())
    total_seqs = sum(len(r["inputs"]) for r in result.values())
    print(f"  {'total':6s}: {total_storms:4d} storms, {total_seqs:6d} sequences")
    train_n = result["train"]["n_storms"]
    val_n = result["val"]["n_storms"]
    test_n = result["test"]["n_storms"]
    print(f"  Split percentages: "
          f"train={train_n/total_storms*100:.1f}% "
          f"val={val_n/total_storms*100:.1f}% "
          f"test={test_n/total_storms*100:.1f}%")

    return result


# ---------------------------------------------------------------------------
# 8. Save processed data
# ---------------------------------------------------------------------------
def save_processed(splits: dict, feature_cols: list, horizons: list,
                   suffix: str = "") -> None:
    print("\n" + "=" * 60)
    print("STEP 8: Saving processed data")
    print("=" * 60)

    for name, data in splits.items():
        path = PROCESSED_DIR / f"{name}{suffix}.npz"
        np.savez_compressed(
            path,
            inputs=data["inputs"],
            targets=data["targets"],
        )
        size_kb = path.stat().st_size / 1024
        print(f"  Saved {name}: {path.name} ({size_kb:.0f} KB)")

    # Save metadata
    meta_out = {
        "feature_cols": feature_cols,
        "horizons": horizons,
        "horizon_labels": [f"+{h*6}h" for h in horizons],
        "seq_length": int(splits["train"]["inputs"].shape[1]),
        "n_features": int(splits["train"]["inputs"].shape[2]),
        "n_output": int(splits["train"]["targets"].shape[1]),
        "splits": {
            name: {
                "n_storms": data["n_storms"],
                "n_sequences": int(len(data["inputs"])),
            }
            for name, data in splits.items()
        },
    }
    meta_path = PROCESSED_DIR / f"metadata{suffix}.json"
    with open(meta_path, "w") as f:
        json.dump(meta_out, f, indent=2)
    print(f"  Metadata: {meta_path.name}")


# ---------------------------------------------------------------------------
# 9. Quality checks
# ---------------------------------------------------------------------------
def quality_checks(splits: dict) -> None:
    print("\n" + "=" * 60)
    print("STEP 9: Quality checks")
    print("=" * 60)

    for name, data in splits.items():
        x, y = data["inputs"], data["targets"]

        # Check for NaN
        nan_x = np.isnan(x).sum()
        nan_y = np.isnan(y).sum()
        print(f"  {name}: NaN in inputs={nan_x}, targets={nan_y}")

        # Check lat range
        lats = x[:, :, 0]
        print(f"  {name}: lat range [{lats.min():.2f}, {lats.max():.2f}]")

        # Check lon range
        lons = x[:, :, 1]
        print(f"  {name}: lon range [{lons.min():.2f}, {lons.max():.2f}]")

    # Verify no storm leakage
    all_meta = []
    for name, data in splits.items():
        for m in data["meta"]:
            all_meta.append((m["storm_id"], name))

    storm_to_split = {}
    for sid, split in all_meta:
        if sid in storm_to_split:
            assert storm_to_split[sid] == split, f"LEAKAGE: {sid} in both {storm_to_split[sid]} and {split}"
        storm_to_split[sid] = split

    print(f"  No storm leakage verified across {len(storm_to_split)} storms")


# ---------------------------------------------------------------------------
# 10. Simple visualization
# ---------------------------------------------------------------------------
def plot_tracks(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("STEP 10: Generating track visualization")
    print("=" * 60)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    storm_ids = df["storm_id"].unique()
    cmap = plt.cm.viridis(np.linspace(0.1, 0.9, len(storm_ids)))

    for i, sid in enumerate(storm_ids):
        storm = df[df["storm_id"] == sid].sort_values("timestamp")
        ax.plot(storm["lon"], storm["lat"], color=cmap[i], alpha=0.5, linewidth=0.8)
        ax.scatter(storm["lon"].iloc[0], storm["lat"].iloc[0],
                   color=cmap[i], s=10, zorder=5)
        ax.scatter(storm["lon"].iloc[-1], storm["lat"].iloc[-1],
                   color=cmap[i], s=10, marker="x", zorder=5)

    ax.set_xlabel("Longitude (E)")
    ax.set_ylabel("Latitude (N)")
    ax.set_title(f"Bay of Bengal Cyclone Tracks (IBTrACS, {len(storm_ids)} storms)")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(78, 98)
    ax.set_ylim(5, 25)

    out = PROCESSED_DIR / "cyclone_tracks.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess IBTrACS data")
    parser.add_argument("--seq-length", type=int, default=4,
                        help="Sequence length (default: 4)")
    parser.add_argument("--suffix", type=str, default="",
                        help="Output file suffix (e.g., '_8')")
    args = parser.parse_args()

    if not RAW_CSV.exists():
        print(f"ERROR: Raw data not found at {RAW_CSV}")
        print("Run download_data.py first.")
        return

    df = load_raw()
    df = filter_bay_of_bengal(df)
    df = select_columns(df)
    df = process_temporal(df)
    df = derive_features(df)

    horizons = [1, 2, 4, 8, 12]  # +6h, +12h, +24h, +48h, +72h
    seq_length = args.seq_length

    inputs, targets, meta, features = generate_sequences(
        df, seq_length=seq_length, horizons=horizons
    )

    splits = storm_split(inputs, targets, meta)

    save_processed(splits, features, horizons, suffix=args.suffix)
    quality_checks(splits)
    plot_tracks(df)

    # Summary stats
    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"  Dataset: IBTrACS v04r01, North Indian Basin, Bay of Bengal")
    print(f"  Storms: {df['storm_id'].nunique()}")
    print(f"  Observations: {len(df)}")
    print(f"  Sequences: {len(inputs)}")
    print(f"  Features: {features}")
    print(f"  Horizons: {[f'+{h*6}h' for h in horizons]}")
    print(f"  Seq length: {seq_length}")
    print(f"  Output dir: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
