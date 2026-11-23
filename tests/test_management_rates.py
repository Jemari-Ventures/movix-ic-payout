"""SPX management rate card + fleet margin smoke tests."""

from __future__ import annotations

import pandas as pd

from movix_dispatcher.config import MovixConfig
from movix_management.calculator import FleetPayoutCalculator
from movix_management.config import ManagementConfig
from movix_management.rates import rate_for_parcel


def test_spx_d2d_and_service_overrides():
    cfg = ManagementConfig.load()
    assert len(cfg.spx_weight_rates) == 10

    rate, label, channel = rate_for_parcel(2.5, "Del - FWD D2D", cfg)
    assert channel == "door_to_door"
    assert rate == 1.1

    rate, _, channel = rate_for_parcel(2.5, "Del - FWD BSC", cfg)
    assert channel == "bsc_flat"
    assert rate == 0.1

    # Heavy BSC stays flat RM0.10 (not SPX drop-off ladder)
    rate, _, _ = rate_for_parcel(55.0, "Del - FWD BSC", cfg)
    assert rate == 0.1

    rate, _, _ = rate_for_parcel(15.0, "Del - FWD D2D", cfg)
    assert rate == 3.1

    rate, _, channel = rate_for_parcel(1.0, "PU - RR D2D", cfg)
    assert rate == 0.7
    assert channel == "pickup_return"

    rate, _, channel = rate_for_parcel(1.0, "Del - RTS", cfg)
    assert rate == 0.0
    assert channel == "rts_nil"


def test_spx_drop_off_column_matches_card():
    cfg = ManagementConfig.load()
    # Official SPX drop-off column (reference); not used for BSC flat rule
    assert cfg.spx_weight_rates[4].drop_off == 1.0  # 20–30kg
    assert cfg.spx_weight_rates[5].drop_off == 2.0  # 30–40kg
    assert cfg.spx_weight_rates[7].drop_off == 2.5  # 50–60kg


def test_fleet_bsc_both_sides_spx_flat():
    mgmt = ManagementConfig.load()
    courier = MovixConfig.load()
    calc = FleetPayoutCalculator(mgmt, courier)

    rows = []
    for i in range(5):
        rows.append(
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
        )
    df = pd.DataFrame(rows)
    result = calc.calculate_driver(df, "D1")
    assert result.total_parcels == 5
    assert result.spx_revenue == 0.5  # management: 5 × RM0.10
    assert result.courier_cost == 0.5  # courier BSC also SPX RM0.10
    assert result.margin == 0.0
