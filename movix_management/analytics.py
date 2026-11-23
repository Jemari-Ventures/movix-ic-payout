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

    channel_mix = pd.DataFrame(
        [
            {
                "channel": "Door-to-door",
                "parcels": sum(r.door_to_door_parcels for r in results),
                "revenue": sum(r.door_to_door_revenue for r in results),
            },
            {
                "channel": "Drop-off",
                "parcels": sum(r.drop_off_parcels for r in results),
                "revenue": sum(r.drop_off_revenue for r in results),
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
    channel_mix = (
        detail.groupby("channel", as_index=False)
        .agg(parcels=("shipment_id", "count"), revenue=("spx_revenue", "sum"))
    )
    channel_mix["channel"] = channel_mix["channel"].map(
        {"door_to_door": "Door-to-door", "drop_off": "Drop-off"}
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
