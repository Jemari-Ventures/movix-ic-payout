"""Service-type + weight → commission rate mapping for Movix IC parcels."""

from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd

from .config import MovixConfig, WeightBand


def resolve_weight_band(weight_kg: float, config: MovixConfig) -> Optional[WeightBand]:
    """Pick the first matching band. Weights are inclusive on both ends per poster."""
    if pd.isna(weight_kg):
        return None
    weight = float(weight_kg)
    if weight < 0:
        return None
    for band in config.weight_commission:
        if band.contains(weight):
            return band
    for band in config.weight_commission:
        if band.max_kg is None or weight <= band.max_kg + 0.01:
            return band
    return None


def weight_commission_rate(weight_kg: float, config: MovixConfig) -> Tuple[float, str]:
    band = resolve_weight_band(weight_kg, config)
    if band is None:
        return 0.0, "Unmapped"
    return float(band.rate), band.label or "Weight band"


def commission_rate(
    weight_kg: float,
    config: MovixConfig,
    service_type: object = "Del - FWD D2D",
) -> Tuple[float, str]:
    """Resolve courier pay for a parcel (service-type rules + D2D weight card)."""
    rule = config.find_service_rule(service_type)
    if rule is None:
        # Legacy fallback: treat unknown Del - FWD* as weight commission
        text = str(service_type or "")
        if text.startswith("Del - FWD"):
            return weight_commission_rate(weight_kg, config)
        return 0.0, "Unmapped service"

    if rule.mode == "flat":
        rate = 0.0 if rule.rate is None else float(rule.rate)
        return rate, rule.label or rule.match

    if rule.mode == "weight_commission":
        return weight_commission_rate(weight_kg, config)

    return 0.0, f"Unknown mode:{rule.mode}"


def apply_commission_rates(df: pd.DataFrame, config: MovixConfig) -> pd.DataFrame:
    """Add commission_rate / weight_band / commission_amount columns."""
    out = df.copy()
    if out.empty:
        out["commission_rate"] = pd.Series(dtype=float)
        out["weight_band"] = pd.Series(dtype=object)
        out["commission_amount"] = pd.Series(dtype=float)
        return out

    rates = []
    labels = []
    service_col = out["service_type"] if "service_type" in out.columns else None
    for idx, weight in enumerate(out["chargeable_weight"]):
        st = service_col.iloc[idx] if service_col is not None else "Del - FWD D2D"
        rate, label = commission_rate(weight, config, service_type=st)
        rates.append(rate)
        labels.append(label)

    out["commission_rate"] = rates
    out["weight_band"] = labels
    out["commission_amount"] = pd.Series(rates, index=out.index).round(2)
    return out
