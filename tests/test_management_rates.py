"""SPX management rate card + fleet margin tests."""

from __future__ import annotations

import pandas as pd

from movix_dispatcher.config import MovixConfig
from movix_management.calculator import FleetPayoutCalculator
from movix_management.config import ManagementConfig
from movix_management.rates import rate_for_parcel


def test_management_service_rates():
    cfg = ManagementConfig.load()

    rate, _, channel = rate_for_parcel(2.5, "Del - FWD D2D", cfg)
    assert channel == "door_to_door"
    assert rate == 1.1

    rate, _, channel = rate_for_parcel(2.5, "Del - FWD BSC", cfg)
    assert channel == "bsc_flat"
    assert rate == 0.1

    # Returns use SPX door-to-door column (not flat 0.7 / nil)
    rate, _, channel = rate_for_parcel(2.5, "PU - RR D2D", cfg)
    assert channel == "door_to_door"
    assert rate == 1.1

    rate, _, channel = rate_for_parcel(15.0, "Del - RTS", cfg)
    assert channel == "door_to_door"
    assert rate == 3.1


def test_spx_bands_contiguous_no_gaps():
    cfg = ManagementConfig.load()
    rate, _, _ = rate_for_parcel(2.999, "Del - FWD D2D", cfg)
    assert rate == 1.1
    rate, _, _ = rate_for_parcel(3.0, "Del - FWD D2D", cfg)
    assert rate == 1.4
    # Shared edge 5.0 → first match (3–5kg @ 1.4); 5.0005 → next band
    rate, _, _ = rate_for_parcel(5.0, "Del - FWD D2D", cfg)
    assert rate == 1.4
    rate, _, _ = rate_for_parcel(5.0005, "Del - FWD D2D", cfg)
    assert rate == 1.9
    rate, _, _ = rate_for_parcel(5.001, "Del - FWD D2D", cfg)
    assert rate == 1.9


def test_failed_deliveries_nil_on_management():
    cfg = ManagementConfig.load()
    rate, label, channel = rate_for_parcel(2.5, "Failed Deliveries", cfg)
    assert rate == 0.0
    assert channel == "flat"


def test_service_pnl_frame_margin():
    from movix_management.analytics import service_pnl_frame
    from movix_management.calculator import DriverFleetResult

    detail = pd.DataFrame(
        [
            {
                "service_type": "Del - FWD D2D",
                "spx_revenue": 1.1,
                "shipment_id": "A",
            },
            {
                "service_type": "PU - RR D2D",
                "spx_revenue": 1.1,
                "shipment_id": "B",
            },
        ]
    )
    fleet = DriverFleetResult(
        driver_id="D1",
        driver_name="T",
        period_start=None,
        period_end=None,
        total_parcels=2,
        working_days=1,
        spx_revenue=2.2,
        courier_cost=1.7,
        margin=0.5,
        margin_pct=22.7,
        door_to_door_parcels=2,
        drop_off_parcels=0,
        door_to_door_revenue=2.2,
        drop_off_revenue=0.0,
        revenue_by_band={},
        parcel_detail=detail,
    )
    courier_priced = pd.DataFrame(
        [
            {"service_type": "Del - FWD D2D", "commission_amount": 1.0},
            {"service_type": "PU - RR D2D", "commission_amount": 0.7},
        ]
    )
    pnl = service_pnl_frame([fleet], courier_priced)
    assert set(pnl["Service type"]) == {"Del - FWD D2D", "PU - RR D2D"}
    rr = pnl.loc[pnl["Service type"] == "PU - RR D2D"].iloc[0]
    assert rr["Margin"] == round(1.1 - 0.7, 2)


def test_fleet_bsc_both_sides_flat():
    mgmt = ManagementConfig.load()
    courier = MovixConfig.load()
    calc = FleetPayoutCalculator(mgmt, courier)

    rows = [
        {
            "service_date": pd.Timestamp("2025-10-01"),
            "service_type": "Del - FWD BSC",
            "lm_type": "BSC",
            "shipment_id": f"S{i}",
            "chargeable_weight": 2.0,
            "driver_id": "D1",
            "driver_name": "Test Driver",
            "tier": "",
        }
        for i in range(5)
    ]
    result = calc.calculate_driver(pd.DataFrame(rows), "D1")
    assert result.spx_revenue == 0.5
    assert result.courier_cost == 0.5
    assert result.margin == 0.0
