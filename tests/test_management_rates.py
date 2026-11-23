"""SPX management rate card + fleet margin smoke tests."""

from __future__ import annotations

import pandas as pd

from movix_dispatcher.config import MovixConfig
from movix_management.calculator import FleetPayoutCalculator
from movix_management.config import ManagementConfig
from movix_management.rates import rate_for_parcel


def test_spx_bands_match_config():
    cfg = ManagementConfig.load()
    assert len(cfg.spx_weight_rates) == 10
    rate, label, channel = rate_for_parcel(2.5, "D2D", cfg)
    assert channel == "door_to_door"
    assert rate == 1.1
    assert "3kg" in label or label.startswith("<")

    rate, _, channel = rate_for_parcel(2.5, "BSC", cfg)
    assert channel == "drop_off"
    assert rate == 0.1

    rate, _, _ = rate_for_parcel(15.0, "D2D", cfg)
    assert rate == 3.1

    rate, _, _ = rate_for_parcel(55.0, "BSC", cfg)
    assert rate == 3.0


def test_fleet_margin_positive_on_light_d2d():
    """Light D2D parcels at SPX 1.1 vs courier commission 1.0 should leave room before basic."""
    mgmt = ManagementConfig.load()
    courier = MovixConfig.load()
    calc = FleetPayoutCalculator(mgmt, courier)

    rows = []
    for i in range(5):
        rows.append(
            {
                "service_date": pd.Timestamp("2025-10-01"),
                "service_type": "Del - FWD D2D",
                "lm_type": "D2D",
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
    assert result.spx_revenue == 5.5  # 5 × 1.1
    # Low volume → commission only (no basic) → courier cost 5.0
    assert result.courier_cost == 5.0
    assert result.margin == 0.5
