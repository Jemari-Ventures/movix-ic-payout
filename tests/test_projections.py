"""Full-month projection + MC/absent CSV helpers."""

from __future__ import annotations

import pandas as pd

from movix_dispatcher.calculator import PayoutResult
from movix_dispatcher.config import MovixConfig
from movix_dispatcher.projections import parse_adjustments_csv, project_full_month_if_short


def _payout(
    driver_id: str,
    working_days: int,
    avg: float,
    qualifies: bool = False,
) -> PayoutResult:
    basic = 1700.0 if qualifies else 0.0
    attendance = 200.0 if qualifies else 0.0
    commission = 10.0
    return PayoutResult(
        driver_id=driver_id,
        driver_name=f"Driver {driver_id}",
        period_start=None,
        period_end=None,
        total_parcels=int(round(avg * max(working_days, 0))),
        volume_parcels=int(round(avg * max(working_days, 0))),
        working_days=working_days,
        avg_parcels_per_day=avg,
        commission_total=commission,
        basic_salary=basic,
        attendance_allowance=attendance,
        attendance_deduction=0.0,
        absent_penalty=0.0,
        gross_payout=commission + basic + attendance,
        net_payout=commission + basic + attendance,
        qualifies_for_basic=qualifies,
        qualifies_for_attendance=qualifies,
        eligibility_reason="ok" if qualifies else "short period",
    )


def test_project_full_month_when_short():
    cfg = MovixConfig.load()
    results = [
        _payout("1", working_days=10, avg=55.0),
        _payout("2", working_days=10, avg=40.0),
        _payout("3", working_days=0, avg=0.0),
    ]
    proj = project_full_month_if_short(results, cfg)
    assert proj is not None
    assert proj.drivers_avg_ok == 1
    assert proj.projected_extra_total == 1900.0


def test_no_projection_when_full_month():
    cfg = MovixConfig.load()
    results = [_payout("1", working_days=26, avg=55.0, qualifies=True)]
    assert project_full_month_if_short(results, cfg) is None


def test_parse_adjustments_csv():
    df = pd.DataFrame(
        [
            {"driver_id": "1001", "mc_days": 1, "absent_days": 2},
            {"driver_id": 2002.0, "mc_days": 0, "absent_days": 1},
        ]
    )
    out = parse_adjustments_csv(df)
    assert out["1001"] == {"mc_days": 1, "absent_days": 2}
    assert out["2002"] == {"mc_days": 0, "absent_days": 1}
