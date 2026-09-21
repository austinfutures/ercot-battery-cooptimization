import numpy as np
import pandas as pd


def generate_demo_data(hours=168, seed=42):
    """
    Generate synthetic ERCOT-like hourly LMP data.

    This is only for demonstrating the optimization engine.
    It is NOT historical ERCOT market data.
    """

    rng = np.random.default_rng(seed)

    timestamps = pd.date_range(
        start="2025-01-01",
        periods=hours,
        freq="h"
    )

    hour = timestamps.hour.values

    # Daily price pattern
    daily_pattern = (
        25
        + 20 * np.sin((hour - 7) / 24 * 2 * np.pi)
    )

    # Morning/evening peaks
    morning_peak = 35 * np.exp(
        -((hour - 8) ** 2) / 8
    )

    evening_peak = 55 * np.exp(
        -((hour - 19) ** 2) / 10
    )

    noise = rng.normal(0, 12, hours)

    prices = (
        daily_pattern
        + morning_peak
        + evening_peak
        + noise
    )

    # Add occasional ERCOT-style price spikes.
    spike_indices = rng.choice(
        hours,
        size=max(1, hours // 40),
        replace=False
    )

    prices[spike_indices] += rng.uniform(
        80,
        250,
        len(spike_indices)
    )

    prices = np.maximum(prices, -20)

    # Simple ancillary-service price series.
    reserve_prices = np.maximum(
        2 + rng.normal(0, 1.5, hours),
        0
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "lmp": prices,
            "reserve_price": reserve_prices,
        }
    )


def load_lmp_csv(uploaded_file):
    """
    Load a CSV containing at least:

        timestamp
        lmp

    Optional:

        reserve_price
    """

    df = pd.read_csv(uploaded_file)

    required = {"timestamp", "lmp"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}"
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df = df.sort_values("timestamp").reset_index(drop=True)

    if "reserve_price" not in df.columns:
        df["reserve_price"] = 0.0

    df["lmp"] = pd.to_numeric(
        df["lmp"],
        errors="coerce"
    )

    df["reserve_price"] = pd.to_numeric(
        df["reserve_price"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp", "lmp"]
    )

    return df