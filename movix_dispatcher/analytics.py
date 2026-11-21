"""Analytics helpers for Movix OKAR payouts (Streamlit-native charts, no Altair)."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

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


def fleet_chart_frames(results: List[PayoutResult]) -> Dict[str, pd.DataFrame]:
    """Return dataframes ready for st.bar_chart / st.line_chart."""
    summary = summary_frame(results)
    frames: Dict[str, pd.DataFrame] = {}
    if summary.empty:
        return frames

    work = summary.copy()
    work["label"] = work.apply(
        lambda r: f"{r['driver_id']}"
        if not clean_driver_name(r.get("driver_name"))
        else f"{r['driver_id']} · {clean_driver_name(r.get('driver_name'))[:24]}",
        axis=1,
    )

    net = work.set_index("label")[["net_payout"]].rename(columns={"net_payout": "Net payout"})
    frames["net_by_driver"] = net

    volume = work.set_index("label")[["total_parcels", "avg_parcels_per_day"]].rename(
        columns={"total_parcels": "Parcels", "avg_parcels_per_day": "Avg / day"}
    )
    frames["volume"] = volume

    composition = work.set_index("label")[
        ["commission_total", "basic_salary", "attendance_allowance"]
    ].rename(
        columns={
            "commission_total": "Commission",
            "basic_salary": "Basic",
            "attendance_allowance": "Attendance",
        }
    )
    frames["composition"] = composition

    band = fleet_weight_band_frame(results)
    if not band.empty:
        frames["weight_mix"] = (
            band.groupby("weight_band", as_index=True)[["parcels", "commission"]]
            .sum()
            .rename(columns={"parcels": "Parcels", "commission": "Commission"})
        )

    return frames


def driver_chart_frames(result: PayoutResult) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    daily = result.daily_summary
    if daily is not None and not daily.empty:
        work = daily.copy()
        work["service_date"] = pd.to_datetime(work["service_date"]).dt.strftime("%Y-%m-%d")
        frames["daily"] = work.set_index("service_date")[["parcels", "commission"]].rename(
            columns={"parcels": "Parcels", "commission": "Commission"}
        )

    if result.parcels_by_band:
        band_df = pd.DataFrame(
            [
                {
                    "weight_band": band,
                    "Parcels": count,
                    "Commission": result.commission_by_band.get(band, 0.0),
                }
                for band, count in result.parcels_by_band.items()
            ]
        ).set_index("weight_band")
        frames["bands"] = band_df

    return frames


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
