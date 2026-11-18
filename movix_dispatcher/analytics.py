"""Analytics charts for Movix OKAR payouts."""

from __future__ import annotations

from typing import Dict, List, Optional

import altair as alt
import pandas as pd

from . import brand
from .calculator import PayoutResult, results_to_summary_frame
from .names import clean_driver_name


def summary_frame(results: List[PayoutResult]) -> pd.DataFrame:
    return results_to_summary_frame(results)


def fleet_weight_band_frame(results: List[PayoutResult]) -> pd.DataFrame:
    rows = []
    for result in results:
        for band, count in result.parcels_by_band.items():
            rows.append(
                {
                    "weight_band": band,
                    "parcels": int(count),
                    "commission": float(result.commission_by_band.get(band, 0.0)),
                    "driver_id": result.driver_id,
                }
            )
    if not rows:
        return pd.DataFrame(columns=["weight_band", "parcels", "commission", "driver_id"])
    return pd.DataFrame(rows)


def build_fleet_charts(results: List[PayoutResult], currency_symbol: str = "RM") -> Dict[str, alt.Chart]:
    summary = summary_frame(results)
    charts: Dict[str, alt.Chart] = {}
    if summary.empty:
        return charts

    work = summary.copy()
    work["label"] = work.apply(
        lambda r: f"{r['driver_id']}"
        if not clean_driver_name(r.get("driver_name"))
        else f"{r['driver_id']} · {clean_driver_name(r.get('driver_name'))[:24]}",
        axis=1,
    )

    charts["net_by_driver"] = (
        alt.Chart(work)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("net_payout:Q", title=f"Net payout ({currency_symbol})"),
            y=alt.Y("label:N", sort="-x", title="Driver"),
            color=alt.condition(
                alt.datum.qualifies_for_basic,
                alt.value(brand.TEAL),
                alt.value("#94a3b8"),
            ),
            tooltip=[
                alt.Tooltip("driver_id:N", title="Driver ID"),
                alt.Tooltip("driver_name:N", title="Name"),
                alt.Tooltip("total_parcels:Q", title="Parcels", format=","),
                alt.Tooltip("net_payout:Q", title="Net", format=",.2f"),
                alt.Tooltip("qualifies_for_basic:N", title="Basic eligible"),
            ],
        )
        .properties(height=max(220, 28 * len(work)), title="Net payout by driver")
    )

    charts["parcels_vs_avg"] = (
        alt.Chart(work)
        .mark_circle(size=120, opacity=0.85)
        .encode(
            x=alt.X("total_parcels:Q", title="Total parcels"),
            y=alt.Y("avg_parcels_per_day:Q", title="Avg parcels / day"),
            size=alt.Size("net_payout:Q", title="Net payout", legend=None),
            color=alt.Color(
                "qualifies_for_basic:N",
                title="Basic eligible",
                scale=alt.Scale(range=["#94a3b8", brand.TEAL]),
            ),
            tooltip=[
                alt.Tooltip("driver_id:N", title="Driver ID"),
                alt.Tooltip("total_parcels:Q", title="Parcels", format=","),
                alt.Tooltip("avg_parcels_per_day:Q", title="Avg/day", format=".2f"),
                alt.Tooltip("working_days:Q", title="Days"),
                alt.Tooltip("net_payout:Q", title="Net", format=",.2f"),
            ],
        )
        .properties(height=320, title="Volume vs daily average")
    )

    band = fleet_weight_band_frame(results)
    if not band.empty:
        band_agg = (
            band.groupby("weight_band", as_index=False)
            .agg(parcels=("parcels", "sum"), commission=("commission", "sum"))
        )
        charts["weight_mix"] = (
            alt.Chart(band_agg)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("weight_band:N", title="Weight band", sort="-y"),
                y=alt.Y("parcels:Q", title="Parcels"),
                color=alt.value(brand.BLUE),
                tooltip=[
                    alt.Tooltip("weight_band:N", title="Band"),
                    alt.Tooltip("parcels:Q", title="Parcels", format=","),
                    alt.Tooltip("commission:Q", title="Commission", format=",.2f"),
                ],
            )
            .properties(height=280, title="Fleet parcels by weight band")
        )

        payout_stack = work.melt(
            id_vars=["driver_id", "label"],
            value_vars=["commission_total", "basic_salary", "attendance_allowance"],
            var_name="component",
            value_name="amount",
        )
        payout_stack["component"] = payout_stack["component"].map(
            {
                "commission_total": "Commission",
                "basic_salary": "Basic",
                "attendance_allowance": "Attendance",
            }
        )
        charts["payout_mix"] = (
            alt.Chart(payout_stack)
            .mark_bar()
            .encode(
                x=alt.X("amount:Q", title=f"Amount ({currency_symbol})", stack="zero"),
                y=alt.Y("label:N", sort="-x", title="Driver"),
                color=alt.Color(
                    "component:N",
                    title="Component",
                    scale=alt.Scale(
                        domain=["Commission", "Basic", "Attendance"],
                        range=[brand.TEAL, brand.BLUE, brand.YELLOW],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("label:N", title="Driver"),
                    alt.Tooltip("component:N", title="Component"),
                    alt.Tooltip("amount:Q", title="Amount", format=",.2f"),
                ],
            )
            .properties(height=max(220, 28 * len(work)), title="Payout composition")
        )

    return charts


def build_driver_charts(result: PayoutResult, currency_symbol: str = "RM") -> Dict[str, alt.Chart]:
    charts: Dict[str, alt.Chart] = {}
    daily = result.daily_summary
    if daily is not None and not daily.empty:
        work = daily.copy()
        work["service_date"] = pd.to_datetime(work["service_date"])
        base = alt.Chart(work).encode(x=alt.X("service_date:T", title="Date"))
        parcels = base.mark_bar(color=brand.TEAL, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            y=alt.Y("parcels:Q", title="Parcels"),
            tooltip=[
                alt.Tooltip("service_date:T", title="Date"),
                alt.Tooltip("parcels:Q", title="Parcels"),
                alt.Tooltip("commission:Q", title="Commission", format=",.2f"),
            ],
        )
        commission = base.mark_line(color=brand.YELLOW, point=True).encode(
            y=alt.Y("commission:Q", title=f"Commission ({currency_symbol})"),
            tooltip=[
                alt.Tooltip("service_date:T", title="Date"),
                alt.Tooltip("commission:Q", title="Commission", format=",.2f"),
            ],
        )
        charts["daily"] = (
            alt.layer(parcels, commission)
            .resolve_scale(y="independent")
            .properties(height=320, title="Daily parcels & commission")
        )

    if result.parcels_by_band:
        band_df = pd.DataFrame(
            [
                {
                    "weight_band": band,
                    "parcels": count,
                    "commission": result.commission_by_band.get(band, 0.0),
                }
                for band, count in result.parcels_by_band.items()
            ]
        )
        charts["bands"] = (
            alt.Chart(band_df)
            .mark_arc(innerRadius=55)
            .encode(
                theta=alt.Theta("parcels:Q"),
                color=alt.Color("weight_band:N", title="Weight band"),
                tooltip=[
                    alt.Tooltip("weight_band:N", title="Band"),
                    alt.Tooltip("parcels:Q", title="Parcels"),
                    alt.Tooltip("commission:Q", title="Commission", format=",.2f"),
                ],
            )
            .properties(height=300, title="Parcel mix by weight")
        )

    return charts


def fleet_kpi_cards(results: List[PayoutResult]) -> Dict[str, float]:
    summary = summary_frame(results)
    if summary.empty:
        return {
            "drivers": 0,
            "parcels": 0,
            "commission": 0.0,
            "basic": 0.0,
            "attendance": 0.0,
            "net": 0.0,
            "basic_qualified": 0,
        }
    return {
        "drivers": float(len(summary)),
        "parcels": float(summary["total_parcels"].sum()),
        "commission": float(summary["commission_total"].sum()),
        "basic": float(summary["basic_salary"].sum()),
        "attendance": float(summary["attendance_allowance"].sum()),
        "net": float(summary["net_payout"].sum()),
        "basic_qualified": float(summary["qualifies_for_basic"].sum()),
    }
