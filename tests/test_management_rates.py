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


def test_spx_bands_at_boundaries():
    cfg = ManagementConfig.load()
    rate, _, _ = rate_for_parcel(2.999, "Del - FWD D2D", cfg)
    assert rate == 1.1
    rate, _, _ = rate_for_parcel(3.0, "Del - FWD D2D", cfg)
    assert rate == 1.4
    rate, _, _ = rate_for_parcel(5.0, "Del - FWD D2D", cfg)
    assert rate == 1.4
    rate, _, _ = rate_for_parcel(5.001, "Del - FWD D2D", cfg)
    assert rate == 1.9


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
