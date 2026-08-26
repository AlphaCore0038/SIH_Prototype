"""
Baseline trajectory models for cyclone position prediction.

Models:
  1. Persistence — cyclone stays at last observed position
  2. Constant Velocity — extrapolate from last movement vector
"""

import numpy as np

HORIZON_STEPS = [1, 2, 4, 8, 12]  # in 3-hour steps: +6h, +12h, +24h, +48h, +72h


def persistence(inputs: np.ndarray) -> np.ndarray:
    """
    Predict future position = last observed position.

    Args:
        inputs: (N, seq_len, n_features) — features[0]=lat, features[1]=lon

    Returns:
        predictions: (N, 10) — [lat6h, lon6h, lat12h, lon12h, ..., lat72h, lon72h]
    """
    last_lat = inputs[:, -1, 0]
    last_lon = inputs[:, -1, 1]

    preds = np.zeros((len(inputs), 10), dtype=np.float32)
    for i, steps in enumerate(HORIZON_STEPS):
        preds[:, i * 2] = last_lat
        preds[:, i * 2 + 1] = last_lon

    return preds


def constant_velocity(inputs: np.ndarray) -> np.ndarray:
    """
    Predict future position by extrapolating from last movement vector.

    Movement = last_obs - second_last_obs (one 3h time step).
    Project forward by the number of 3h steps to each horizon.

    Args:
        inputs: (N, seq_len, n_features) — features[0]=lat, features[1]=lon

    Returns:
        predictions: (N, 10) — [lat6h, lon6h, lat12h, lon12h, ..., lat72h, lon72h]
    """
    last_lat = inputs[:, -1, 0]
    last_lon = inputs[:, -1, 1]
    prev_lat = inputs[:, -2, 0]
    prev_lon = inputs[:, -2, 1]

    # Displacement per 3-hour step
    dlat_per_step = last_lat - prev_lat
    dlon_per_step = last_lon - prev_lon

    preds = np.zeros((len(inputs), 10), dtype=np.float32)
    for i, steps in enumerate(HORIZON_STEPS):
        preds[:, i * 2] = last_lat + dlat_per_step * steps
        preds[:, i * 2 + 1] = last_lon + dlon_per_step * steps

    return preds
