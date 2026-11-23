"""Unit tests for Movix weight commission (courier poster)."""

from __future__ import annotations

import pytest

from movix_dispatcher.config import MovixConfig
from movix_dispatcher.rates import commission_rate, resolve_weight_band


@pytest.fixture
def config() -> MovixConfig:
    return MovixConfig.load()


@pytest.mark.parametrize(
    "weight,expected_rate,expected_label",
    [
        (0.0, 1.0, "0 – 5.00 kg"),
        (0.08, 1.0, "0 – 5.00 kg"),
        (5.0, 1.0, "0 – 5.00 kg"),
        (5.01, 1.8, "5.01 – 20.00 kg"),
        (7.73, 1.8, "5.01 – 20.00 kg"),
        (20.0, 1.8, "5.01 – 20.00 kg"),
        (20.01, 3.0, "> 20.00 kg"),
        (30.0, 3.0, "> 20.00 kg"),
    ],
)
def test_d2d_commission_bands(config, weight, expected_rate, expected_label):
    rate, label = commission_rate(weight, config, service_type="Del - FWD D2D")
    assert rate == expected_rate
    assert label == expected_label
    band = resolve_weight_band(weight, config)
    assert band is not None
    assert band.rate == expected_rate


def test_bsc_also_uses_weight_card_for_courier(config):
    """Management BSC flat RM0.10 does not apply to courier pay."""
    rate, label = commission_rate(2.0, config, service_type="Del - FWD BSC")
    assert rate == 1.0
    assert label == "0 – 5.00 kg"

    rate, _ = commission_rate(7.0, config, service_type="Del - FWD BSC")
    assert rate == 1.8


def test_pu_rr_and_rts_not_courier_billable_defaults(config):
    assert config.billable_service_prefixes == ("Del - FWD",)
    rate, _ = commission_rate(1.0, config, service_type="PU - RR D2D")
    assert rate == 0.0
    rate, _ = commission_rate(1.0, config, service_type="Del - RTS")
    assert rate == 0.0


def test_negative_weight_unmapped(config):
    rate, label = commission_rate(-1.0, config, service_type="Del - FWD D2D")
    assert rate == 0.0
    assert label == "Unmapped"
