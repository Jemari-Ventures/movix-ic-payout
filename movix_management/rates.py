"""SPX / management revenue rates by service type + weight."""

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


def rate_for_parcel(
    weight_kg: float,
    service_type: object,
    config: ManagementConfig,
    lm_type: object = None,
) -> Tuple[float, str, str]:
    """Return (rate, band_or_rule_label, channel_key)."""
    rule = config.find_service_rule(service_type)
    if rule is None:
        text = str(service_type or "")
        if text.startswith("Del - FWD") and "BSC" in text.upper():
            return 0.1, "Buyer self collect", "bsc_flat"
        if text.startswith("Del - FWD"):
            band = resolve_band(weight_kg, config)
            if band is None:
                return 0.0, "Unmapped", "door_to_door"
            return float(band.door_to_door), band.label, "door_to_door"
        return 0.0, "Unmapped service", "unmapped"

    if rule.mode == "flat":
        rate = 0.0 if rule.rate is None else float(rule.rate)
        channel = "bsc_flat" if "BSC" in rule.match.upper() else (
            "pickup_return" if "PU" in rule.match.upper() else "flat"
        )
        if "RTS" in rule.match.upper():
            channel = "rts_nil"
        return rate, rule.label or rule.match, channel

    band = resolve_band(weight_kg, config)
    if band is None:
        return 0.0, "Unmapped weight", "door_to_door"

    if rule.mode == "spx_door_to_door":
        return float(band.door_to_door), band.label, "door_to_door"
    if rule.mode == "spx_drop_off":
        return float(band.drop_off), band.label, "drop_off"

    return 0.0, f"Unknown mode:{rule.mode}", "unmapped"


def apply_spx_rates(df: pd.DataFrame, config: ManagementConfig) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["spx_rate"] = pd.Series(dtype=float)
        out["weight_band"] = pd.Series(dtype=object)
        out["channel"] = pd.Series(dtype=object)
        out["spx_revenue"] = pd.Series(dtype=float)
        return out

    rates, labels, channels = [], [], []
    service_col = df["service_type"] if "service_type" in df.columns else None
    lm_col = df["lm_type"] if "lm_type" in df.columns else None
    for idx, weight in enumerate(df["chargeable_weight"]):
        st = service_col.iloc[idx] if service_col is not None else "Del - FWD D2D"
        lm = lm_col.iloc[idx] if lm_col is not None else None
        rate, label, channel = rate_for_parcel(weight, st, config, lm_type=lm)
        rates.append(rate)
        labels.append(label)
        channels.append(channel)

    out = df.copy()
    out["spx_rate"] = rates
    out["weight_band"] = labels
    out["channel"] = channels
    out["spx_revenue"] = pd.Series(rates, index=out.index).round(2)
    return out
