"""Fleet SPX revenue vs OKAR courier cost."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from movix_dispatcher.calculator import MovixPayoutCalculator, PayoutResult
from movix_dispatcher.config import MovixConfig

from .config import ManagementConfig
from .rates import apply_spx_rates


@dataclass
class DriverFleetResult:
    driver_id: str
    driver_name: str
    period_start: Optional[str]
    period_end: Optional[str]
    total_parcels: int
    working_days: int
    spx_revenue: float
    courier_cost: float
    margin: float
    margin_pct: float
    door_to_door_parcels: int
    drop_off_parcels: int
    door_to_door_revenue: float
    drop_off_revenue: float
    revenue_by_band: Dict[str, float] = field(default_factory=dict)
    parcels_by_band: Dict[str, int] = field(default_factory=dict)
    parcel_detail: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)

    def to_summary_row(self) -> Dict:
        row = asdict(self)
        row.pop("parcel_detail", None)
        row.pop("revenue_by_band", None)
        row.pop("parcels_by_band", None)
        for band, count in self.parcels_by_band.items():
            row[f"parcels::{band}"] = count
        for band, amount in self.revenue_by_band.items():
            row[f"revenue::{band}"] = amount
        return row


@dataclass
class FleetSummary:
    total_parcels: int
    drivers: int
    working_days: int
    spx_revenue: float
    courier_cost: float
    margin: float
    margin_pct: float
    door_to_door_parcels: int
    drop_off_parcels: int
    door_to_door_revenue: float
    drop_off_revenue: float
    period_start: Optional[str]
    period_end: Optional[str]


class FleetPayoutCalculator:
    def __init__(
        self,
        management_config: Optional[ManagementConfig] = None,
        courier_config: Optional[MovixConfig] = None,
    ):
        self.mgmt = management_config or ManagementConfig.load()
        self.courier_config = courier_config or MovixConfig.load()
        self.courier_calc = MovixPayoutCalculator(self.courier_config)

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        return apply_spx_rates(df, self.mgmt)

    @staticmethod
    def _courier_billable(df: pd.DataFrame) -> pd.DataFrame:
        """Courier poster applies to Del - FWD only (not management PU-RR / RTS rows)."""
        if df.empty or "service_type" not in df.columns:
            return df
        return df[df["service_type"].astype(str).str.startswith("Del - FWD")].copy()

    def calculate_driver(
        self,
        df: pd.DataFrame,
        driver_id: str,
        mc_days: int = 0,
        absent_days: int = 0,
        payout: Optional[PayoutResult] = None,
    ) -> DriverFleetResult:
        driver_id = str(driver_id).strip()
        scoped = df[df["driver_id"].astype(str) == driver_id].copy()
        payout = payout or self.courier_calc.calculate_driver(
            self._courier_billable(scoped),
            driver_id,
            mc_days=mc_days,
            absent_days=absent_days,
        )
        return self._from_scoped(scoped, payout)

    def calculate_all(
        self,
        df: pd.DataFrame,
        adjustments: Optional[Dict[str, Dict[str, int]]] = None,
        payouts: Optional[List[PayoutResult]] = None,
    ) -> List[DriverFleetResult]:
        adjustments = adjustments or {}
        payout_map: Dict[str, PayoutResult] = {}
        if payouts:
            payout_map = {str(p.driver_id): p for p in payouts}
        elif not df.empty:
            payout_map = {
                str(p.driver_id): p
                for p in self.courier_calc.calculate_all(
                    self._courier_billable(df), adjustments=adjustments
                )
            }

        results: List[DriverFleetResult] = []
        if df.empty:
            return results
        for driver_id in sorted(df["driver_id"].astype(str).unique()):
            adj = adjustments.get(driver_id, {}) or adjustments.get(str(driver_id), {})
            payout = payout_map.get(str(driver_id))
            results.append(
                self.calculate_driver(
                    df,
                    driver_id,
                    mc_days=int(adj.get("mc_days", 0) or 0),
                    absent_days=int(adj.get("absent_days", 0) or 0),
                    payout=payout,
                )
            )
        return results

    def fleet_summary(self, results: List[DriverFleetResult]) -> FleetSummary:
        if not results:
            return FleetSummary(
                total_parcels=0,
                drivers=0,
                working_days=0,
                spx_revenue=0.0,
                courier_cost=0.0,
                margin=0.0,
                margin_pct=0.0,
                door_to_door_parcels=0,
                drop_off_parcels=0,
                door_to_door_revenue=0.0,
                drop_off_revenue=0.0,
                period_start=None,
                period_end=None,
            )

        revenue = round(sum(r.spx_revenue for r in results), 2)
        cost = round(sum(r.courier_cost for r in results), 2)
        margin = round(revenue - cost, 2)
        starts = [r.period_start for r in results if r.period_start]
        ends = [r.period_end for r in results if r.period_end]
        return FleetSummary(
            total_parcels=sum(r.total_parcels for r in results),
            drivers=len(results),
            working_days=max((r.working_days for r in results), default=0),
            spx_revenue=revenue,
            courier_cost=cost,
            margin=margin,
            margin_pct=round((margin / revenue) * 100, 1) if revenue else 0.0,
            door_to_door_parcels=sum(r.door_to_door_parcels for r in results),
            drop_off_parcels=sum(r.drop_off_parcels for r in results),
            door_to_door_revenue=round(sum(r.door_to_door_revenue for r in results), 2),
            drop_off_revenue=round(sum(r.drop_off_revenue for r in results), 2),
            period_start=min(starts) if starts else None,
            period_end=max(ends) if ends else None,
        )

    def _from_scoped(self, scoped: pd.DataFrame, payout: PayoutResult) -> DriverFleetResult:
        enriched = self.enrich(scoped)
        if enriched.empty:
            return DriverFleetResult(
                driver_id=payout.driver_id,
                driver_name=payout.driver_name,
                period_start=payout.period_start,
                period_end=payout.period_end,
                total_parcels=0,
                working_days=0,
                spx_revenue=0.0,
                courier_cost=float(payout.net_payout),
                margin=round(0.0 - float(payout.net_payout), 2),
                margin_pct=0.0,
                door_to_door_parcels=0,
                drop_off_parcels=0,
                door_to_door_revenue=0.0,
                drop_off_revenue=0.0,
            )

        revenue = round(float(enriched["spx_revenue"].sum()), 2)
        cost = float(payout.net_payout)
        margin = round(revenue - cost, 2)
        d2d = enriched[enriched["channel"] == "door_to_door"]
        drop = enriched[enriched["channel"] == "drop_off"]
        parcels_by_band = (
            enriched.groupby("weight_band", dropna=False).size().astype(int).to_dict()
        )
        revenue_by_band = (
            enriched.groupby("weight_band", dropna=False)["spx_revenue"]
            .sum()
            .round(2)
            .astype(float)
            .to_dict()
        )
        return DriverFleetResult(
            driver_id=payout.driver_id,
            driver_name=payout.driver_name or (
                str(enriched["driver_name"].iloc[0]) if "driver_name" in enriched else ""
            ),
            period_start=payout.period_start,
            period_end=payout.period_end,
            total_parcels=int(len(enriched)),
            working_days=int(payout.working_days),
            spx_revenue=revenue,
            courier_cost=cost,
            margin=margin,
            margin_pct=round((margin / revenue) * 100, 1) if revenue else 0.0,
            door_to_door_parcels=int(len(d2d)),
            drop_off_parcels=int(len(drop)),
            door_to_door_revenue=round(float(d2d["spx_revenue"].sum()), 2) if len(d2d) else 0.0,
            drop_off_revenue=round(float(drop["spx_revenue"].sum()), 2) if len(drop) else 0.0,
            revenue_by_band=revenue_by_band,
            parcels_by_band=parcels_by_band,
            parcel_detail=enriched,
        )


def results_to_summary_frame(results: List[DriverFleetResult]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame()
    return pd.DataFrame([r.to_summary_row() for r in results])
