"""Tests for Movix invoice HTML and analytics helpers."""

from __future__ import annotations

import pandas as pd

from movix_dispatcher.analytics import driver_chart_frames, fleet_chart_frames, fleet_kpi_cards
from movix_dispatcher.calculator import MovixPayoutCalculator
from movix_dispatcher.config import MovixConfig
from movix_dispatcher.ingest import normalize_frame
from movix_dispatcher.invoice import build_invoice_html


def _sample_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Service Date": "2026-10-21",
                "Service Type": "Del - FWD D2D",
                "LM Type": "D2D",
                "Shipment ID": "A1",
                "Chargeable Weight": 0.5,
                "Driver ID": 1001,
                "Driver Name": "[1001] Test Driver",
                "TIER": "T1",
            },
            {
                "Service Date": "2026-10-22",
                "Service Type": "Del - FWD D2D",
                "LM Type": "D2D",
                "Shipment ID": "A2",
                "Chargeable Weight": 8.0,
                "Driver ID": 1001,
                "Driver Name": "[1001] Test Driver",
                "TIER": "T2",
            },
            {
                "Service Date": "2026-10-21",
                "Service Type": "Del - FWD D2D",
                "LM Type": "D2D",
                "Shipment ID": "B1",
                "Chargeable Weight": 1.0,
                "Driver ID": 2002,
                "Driver Name": "[2002] Other",
                "TIER": "T1",
            },
        ]
    )


def test_invoice_html_contains_net_and_okar():
    cfg = MovixConfig.load()
    df = normalize_frame(_sample_rows(), cfg)
    result = MovixPayoutCalculator(cfg).calculate_driver(df, "1001")
    html = build_invoice_html(result, cfg)
    assert "OS Karangan (OKAR)" in html
    assert "Net payable" in html
    assert "Commission by service type" in html
    assert f"{result.net_payout:,.2f}" in html
    assert "1001" in html
    assert "Movix Logistics (M) Sdn. Bhd" in html


def test_analytics_frames_and_kpis():
    cfg = MovixConfig.load()
    df = normalize_frame(_sample_rows(), cfg)
    results = MovixPayoutCalculator(cfg).calculate_all(df)
    kpis = fleet_kpi_cards(results)
    assert kpis["drivers"] == 2
    assert kpis["parcels"] == 3
    fleet = fleet_chart_frames(results, short_labels=True)
    assert "net_by_driver" in fleet
    assert "volume" in fleet
    assert "composition" in fleet
    assert "ranking" in fleet
    assert list(fleet["net_by_driver"].index) == ["1001", "2002"] or set(fleet["net_by_driver"].index) == {
        "1001",
        "2002",
    }
    driver_frames = driver_chart_frames(results[0])
    assert "daily" in driver_frames
    assert "bands" in driver_frames
    assert "daily_table" in driver_frames
