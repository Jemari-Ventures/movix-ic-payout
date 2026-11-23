"""Full-month basic / attendance projections for short periods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .calculator import PayoutResult
from .config import MovixConfig


@dataclass(frozen=True)
class FullMonthProjection:
    drivers_short_period: int
    drivers_avg_ok: int
    projected_extra_basic: float
    projected_extra_attendance: float
    projected_extra_total: float
    message: str


def project_full_month_if_short(
    results: Sequence[PayoutResult],
    config: Optional[MovixConfig] = None,
) -> Optional[FullMonthProjection]:
    """If period is under the basic day gate, estimate extra cost if avg stays ≥50."""
    cfg = config or MovixConfig.load()
    if not results:
        return None

    max_days = max((r.working_days for r in results), default=0)
    if max_days >= cfg.basic_required_working_days:
        return None

    short = [r for r in results if r.working_days > 0]
    avg_ok = [
        r
        for r in short
        if r.avg_parcels_per_day >= cfg.basic_min_avg_parcels_per_day
        and not r.qualifies_for_basic
    ]
    extra_basic = len(avg_ok) * float(cfg.basic_amount)
    extra_att = len(avg_ok) * float(cfg.attendance_amount)
    extra = round(extra_basic + extra_att, 2)
    msg = (
        f"Period is only {max_days} working day(s) (need ≥{cfg.basic_required_working_days}). "
        f"{len(avg_ok)} driver(s) already average ≥{cfg.basic_min_avg_parcels_per_day:.0f}/day — "
        f"if they hold that pace for a full month, expect about "
        f"{cfg.currency_symbol}{extra:,.2f} extra "
        f"(basic {cfg.currency_symbol}{extra_basic:,.0f} + attendance {cfg.currency_symbol}{extra_att:,.0f})."
    )
    return FullMonthProjection(
        drivers_short_period=len(short),
        drivers_avg_ok=len(avg_ok),
        projected_extra_basic=round(extra_basic, 2),
        projected_extra_attendance=round(extra_att, 2),
        projected_extra_total=extra,
        message=msg,
    )


def parse_adjustments_csv(df) -> dict:
    """Parse MC/absent CSV with columns driver_id, mc_days, absent_days."""
    import pandas as pd

    if df is None or df.empty:
        return {}
    work = df.copy()
    work.columns = [str(c).strip().lower().replace(" ", "_") for c in work.columns]
    id_col = next((c for c in ("driver_id", "driverid", "id") if c in work.columns), None)
    if id_col is None:
        raise ValueError("Adjustments CSV needs a driver_id column")
    mc_col = next((c for c in ("mc_days", "mc", "mc_day") if c in work.columns), None)
    ab_col = next(
        (c for c in ("absent_days", "absent", "absent_day") if c in work.columns), None
    )
    out = {}
    for row in work.itertuples(index=False):
        raw = getattr(row, id_col)
        driver_id = str(raw).strip()
        if driver_id.endswith(".0") and driver_id.replace(".", "", 1).isdigit():
            driver_id = driver_id[:-2]
        if not driver_id or driver_id.lower() == "nan":
            continue
        mc = int(getattr(row, mc_col) or 0) if mc_col else 0
        ab = int(getattr(row, ab_col) or 0) if ab_col else 0
        out[driver_id] = {"mc_days": max(0, mc), "absent_days": max(0, ab)}
    return out
