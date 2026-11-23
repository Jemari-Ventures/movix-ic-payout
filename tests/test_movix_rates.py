"""Unit tests for Movix courier service-type rates."""

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
        (5.0, 1.0, "0 – 5.00 kg"),
        (5.01, 1.8, "5.01 – 20.00 kg"),
        (20.0, 1.8, "5.01 – 20.00 kg"),
        (20.01, 3.0, "> 20.00 kg"),
    ],
)
def test_d2d_courier_tier(config, weight, expected_rate, expected_label):
    rate, label = commission_rate(weight, config, service_type="Del - FWD D2D")
    assert rate == expected_rate
    assert label == expected_label
    assert resolve_weight_band(weight, config).rate == expected_rate


def test_courier_flat_overrides(config):
    rate, label = commission_rate(2.0, config, service_type="Del - FWD BSC")
    assert rate == 0.1
    assert label == "BSC"

    rate, _ = commission_rate(25.0, config, service_type="PU - RR D2D")
    assert rate == 0.7

    rate, _ = commission_rate(25.0, config, service_type="Del - RTS")
    assert rate == 0.7


def test_negative_weight_unmapped(config):
    rate, label = commission_rate(-1.0, config, service_type="Del - FWD D2D")
    assert rate == 0.0
    assert label == "Unmapped"
