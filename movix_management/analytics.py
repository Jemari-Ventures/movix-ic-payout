"""Chart frames and KPI helpers for the management fleet view."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from .calculator import DriverFleetResult, FleetSummary


def fleet_kpi_cards(summary: FleetSummary, symbol: str = "RM") -> List[Dict[str, str]]:
    return [
        {"label": "SPX revenue", "value": f"{symbol}{summary.spx_revenue:,.2f}"},
        {"label": "Courier cost", "value": f"{symbol}{summary.courier_cost:,.2f}"},
        {"label": "Gross margin", "value": f"{symbol}{summary.margin:,.2f}"},
        {"label": "Margin %", "value": f"{summary.margin_pct:.1f}%"},
        {"label": "Parcels", "value": f"{summary.total_parcels:,}"},
        {"label": "Drivers", "value": f"{summary.drivers:,}"},
    ]


def service_pnl_frame(
    results: List[DriverFleetResult],
    courier_priced: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Revenue (SPX) by service type; optional courier cost join by service_type."""
    rows = []
    for r in results:
        if r.parcel_detail.empty or "service_type" not in r.parcel_detail.columns:
            continue
        for service, grp in r.parcel_detail.groupby("service_type"):
            rows.append(
                {
                    "Service type": service,
                    "Parcels": int(len(grp)),
                    "SPX revenue": round(float(grp["spx_revenue"].sum()), 2),
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["Service type", "Parcels", "SPX revenue", "Courier cost", "Margin"]
        )
    rev = (
        pd.DataFrame(rows)
        .groupby("Service type", as_index=False)
        .agg(Parcels=("Parcels", "sum"), **{"SPX revenue": ("SPX revenue", "sum")})
    )
    if courier_priced is not None and not courier_priced.empty and "service_type" in courier_priced:
        cost = (
            courier_priced.groupby("service_type", as_index=False)["commission_amount"]
            .sum()
            .rename(columns={"service_type": "Service type", "commission_amount": "Courier cost"})
        )
        rev = rev.merge(cost, on="Service type", how="left")
    else:
        rev["Courier cost"] = 0.0
    rev["Courier cost"] = rev["Courier cost"].fillna(0.0).round(2)
    rev["Margin"] = (rev["SPX revenue"] - rev["Courier cost"]).round(2)
    return rev.sort_values("Margin", ascending=False)


def fleet_chart_frames(results: List[DriverFleetResult]) -> Dict[str, pd.DataFrame]:
    if not results:
        empty = pd.DataFrame()
        return {
            "margin_by_driver": empty,
            "channel_mix": empty,
            "weight_band": empty,
            "revenue_vs_cost": empty,
        }

    margin_by_driver = (
        pd.DataFrame(
            [
                {
                    "driver": r.driver_name or r.driver_id,
                    "spx_revenue": r.spx_revenue,
                    "courier_cost": r.courier_cost,
                    "margin": r.margin,
                    "parcels": r.total_parcels,
                }
                for r in results
            ]
        )
        .sort_values("margin", ascending=False)
        .reset_index(drop=True)
    )

    # Prefer LM-type mix (D2D vs BSC) when parcel detail is present
    d2d_n = bsc_n = 0
    d2d_rev = bsc_rev = 0.0
    for r in results:
        if r.parcel_detail.empty or "lm_type" not in r.parcel_detail.columns:
            d2d_n += r.door_to_door_parcels
            d2d_rev += r.door_to_door_revenue
            continue
        d2d_mask = r.parcel_detail["lm_type"] == "D2D"
        bsc_mask = r.parcel_detail["lm_type"] == "BSC"
        d2d_n += int(d2d_mask.sum())
        bsc_n += int(bsc_mask.sum())
        d2d_rev += float(r.parcel_detail.loc[d2d_mask, "spx_revenue"].sum())
        bsc_rev += float(r.parcel_detail.loc[bsc_mask, "spx_revenue"].sum())

    channel_mix = pd.DataFrame(
        [
            {
                "channel": "Door-to-door (D2D)",
                "parcels": d2d_n,
                "revenue": round(d2d_rev, 2),
            },
            {
                "channel": "Buyer self collect (BSC)",
                "parcels": bsc_n,
                "revenue": round(bsc_rev, 2),
            },
        ]
    )

    band_rows = []
    for r in results:
        for band, count in r.parcels_by_band.items():
            band_rows.append(
                {
                    "weight_band": band,
                    "parcels": count,
                    "revenue": r.revenue_by_band.get(band, 0.0),
                }
            )
    if band_rows:
        weight_band = (
            pd.DataFrame(band_rows)
            .groupby("weight_band", as_index=False)
            .agg(parcels=("parcels", "sum"), revenue=("revenue", "sum"))
        )
    else:
        weight_band = pd.DataFrame(columns=["weight_band", "parcels", "revenue"])

    revenue_vs_cost = margin_by_driver[
        ["driver", "spx_revenue", "courier_cost", "margin"]
    ].copy()

    return {
        "margin_by_driver": margin_by_driver,
        "channel_mix": channel_mix,
        "weight_band": weight_band,
        "revenue_vs_cost": revenue_vs_cost,
    }


def driver_chart_frames(result: Optional[DriverFleetResult]) -> Dict[str, pd.DataFrame]:
    if result is None or result.parcel_detail.empty:
        empty = pd.DataFrame()
        return {"weight_band": empty, "channel_mix": empty, "daily": empty}

    detail = result.parcel_detail
    weight_band = (
        detail.groupby("weight_band", as_index=False)
        .agg(parcels=("shipment_id", "count"), revenue=("spx_revenue", "sum"))
        .sort_values("revenue", ascending=False)
    )
    if "lm_type" in detail.columns:
        channel_mix = (
            detail.groupby("lm_type", as_index=False)
            .agg(parcels=("shipment_id", "count"), revenue=("spx_revenue", "sum"))
        )
        channel_mix["channel"] = channel_mix["lm_type"].map(
            {"D2D": "Door-to-door (D2D)", "BSC": "Buyer self collect (BSC)"}
        ).fillna(channel_mix["lm_type"])
        channel_mix = channel_mix[["channel", "parcels", "revenue"]]
    else:
        channel_mix = (
            detail.groupby("channel", as_index=False)
            .agg(parcels=("shipment_id", "count"), revenue=("spx_revenue", "sum"))
        )
        channel_mix["channel"] = channel_mix["channel"].map(
            {"door_to_door": "Door-to-door", "drop_off": "Drop-off / return to SPX"}
        ).fillna(channel_mix["channel"])

    daily = pd.DataFrame()
    if "service_date" in detail.columns:
        daily = (
            detail.assign(service_date=pd.to_datetime(detail["service_date"]))
            .groupby("service_date", as_index=False)
            .agg(parcels=("shipment_id", "count"), revenue=("spx_revenue", "sum"))
            .sort_values("service_date")
        )

    return {"weight_band": weight_band, "channel_mix": channel_mix, "daily": daily}
