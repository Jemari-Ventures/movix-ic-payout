"""SPX partner weight → revenue rate mapping."""

from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd

from .config import ManagementConfig, SpxWeightBand


def resolve_band(weight_kg: float, config: ManagementConfig) -> Optional[SpxWeightBand]:
    if pd.isna(weight_kg):
        return None
    weight = float(weight_kg)
    if weight < 0:
        return None
    for band in config.spx_weight_rates:
        if band.contains(weight):
            return band
    return None


def resolve_channel(lm_type: object, config: ManagementConfig) -> str:
    key = str(lm_type or "").strip().upper()
    return config.service_channel_map.get(key, config.default_channel)


def rate_for_parcel(
    weight_kg: float,
    lm_type: object,
    config: ManagementConfig,
) -> Tuple[float, str, str]:
    """Return (rate, weight_band_label, channel)."""
    band = resolve_band(weight_kg, config)
    channel = resolve_channel(lm_type, config)
    if band is None:
        return 0.0, "Unmapped", channel
    rate = band.door_to_door if channel == "door_to_door" else band.drop_off
    return float(rate), band.label, channel


def apply_spx_rates(df: pd.DataFrame, config: ManagementConfig) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["spx_rate"] = pd.Series(dtype=float)
        out["weight_band"] = pd.Series(dtype=object)
        out["channel"] = pd.Series(dtype=object)
        out["spx_revenue"] = pd.Series(dtype=float)
        return out

    rates, labels, channels = [], [], []
    lm_series = df["lm_type"] if "lm_type" in df.columns else pd.Series([""] * len(df))
    for weight, lm in zip(df["chargeable_weight"], lm_series):
        rate, label, channel = rate_for_parcel(weight, lm, config)
        rates.append(rate)
        labels.append(label)
        channels.append(channel)

    out = df.copy()
    out["spx_rate"] = rates
    out["weight_band"] = labels
    out["channel"] = channels
    out["spx_revenue"] = pd.Series(rates, index=out.index).round(2)
    return out
