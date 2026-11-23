"""Calculator and ingest tests, including optional live IC Payment.xlsx check."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from movix_dispatcher.calculator import MovixPayoutCalculator, results_to_summary_frame
from movix_dispatcher.config import MovixConfig
from movix_dispatcher.ingest import filter_billable, normalize_frame

SAMPLE_XLSX = Path("/Users/UMARI.ZULKIFLI/Documents/IC Payment.xlsx")


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
                "Service Date": "2026-10-21",
                "Service Type": "Del - FWD BSC",
                "LM Type": "BSC",
                "Shipment ID": "A2",
                "Chargeable Weight": 7.0,
                "Driver ID": 1001,
                "Driver Name": "[1001] Test Driver",
                "TIER": "T2",
            },
            {
                "Service Date": "2026-10-21",
                "Service Type": "Failed Deliveries",
                "LM Type": "D2D",
                "Shipment ID": "A3",
                "Chargeable Weight": 1.0,
                "Driver ID": 1001,
                "Driver Name": "[1001] Test Driver",
                "TIER": "T1",
            },
            {
                "Service Date": "2026-10-22",
                "Service Type": "Del - FWD D2D",
                "LM Type": "D2D",
                "Shipment ID": "A4",
                "Chargeable Weight": 25.0,
                "Driver ID": 1001,
                "Driver Name": "[1001] Test Driver",
                "TIER": "T3",
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


def test_normalize_includes_failed_as_nil():
    cfg = MovixConfig.load()
    df = normalize_frame(_sample_rows(), cfg)
    # Failed kept as RM0 audit; BSC + D2D kept
    assert set(df["shipment_id"]) == {"A1", "A2", "A3", "A4", "B1"}
    result = MovixPayoutCalculator(cfg).calculate_driver(df, "1001")
    assert result.commission_by_service.get("Failed Deliveries", 0.0) == 0.0


def test_pickup_return_and_rts_use_flat_rate():
    cfg = MovixConfig.load()
    raw = _sample_rows()
    raw = pd.concat(
        [
            raw,
            pd.DataFrame(
                [
                    {
                        "Service Date": "2026-10-21",
                        "Service Type": "PU - RR D2D",
                        "LM Type": "D2D",
                        "Shipment ID": "P1",
                        "Chargeable Weight": 2.0,
                        "Driver ID": 1001,
                        "Driver Name": "[1001] Test Driver",
                        "TIER": "T1",
                    },
                    {
                        "Service Date": "2026-10-21",
                        "Service Type": "Del - RTS",
                        "LM Type": "D2D",
                        "Shipment ID": "R1",
                        "Chargeable Weight": 2.0,
                        "Driver ID": 1001,
                        "Driver Name": "[1001] Test Driver",
                        "TIER": "T1",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    df = normalize_frame(raw, cfg)
    assert {"P1", "R1"} <= set(df["shipment_id"])
    result = MovixPayoutCalculator(cfg).calculate_driver(df, "1001")
    # A1 1.00 + A2 BSC 0.10 + A4 3.00 + P1 0.70 + R1 0.70 = 5.50
    assert result.commission_total == 5.50
    assert result.commission_by_service.get("PU - RR D2D") == 0.7
    assert result.commission_by_service.get("Del - RTS") == 0.7


def test_driver_commission_math():
    cfg = MovixConfig.load()
    df = normalize_frame(_sample_rows(), cfg)
    calc = MovixPayoutCalculator(cfg)
    result = calc.calculate_driver(df, "1001")
    # A1 1.00 + A2 BSC 0.10 + A3 Failed 0 + A4 3.00 = 4.10
    assert result.total_parcels == 4
    assert result.volume_parcels == 2  # D2D only (A1, A4); BSC/Failed excluded from gate
    assert result.working_days == 2
    assert result.avg_parcels_per_day == 1.0  # 2 volume / 2 days
    assert result.commission_total == 4.10
    assert result.basic_salary == 0.0  # only 2 days
    assert result.net_payout == 4.10
    assert result.parcels_by_band.get("BSC", 0) == 1
    assert result.parcels_by_service.get("Del - FWD BSC", 0) == 1
    assert result.commission_by_service.get("Del - FWD BSC", 0) == 0.1
    assert result.parcels_by_service.get("Del - FWD D2D", 0) == 2
    assert result.parcels_by_service.get("Failed Deliveries", 0) == 1


def test_volume_gate_ignores_bsc_and_returns():
    """BSC/returns inflate total parcels but not the ≥50/day volume avg."""
    cfg = MovixConfig.load()
    rows = []
    # 26 days × 40 D2D = 1040 volume → avg 40 (fail gate)
    # Plus 26 × 20 BSC = 520 more billable → would look like avg 60 if all counted
    for day in range(1, 27):
        date = f"2026-10-{day:02d}" if day <= 31 else f"2026-11-{day - 31:02d}"
        for i in range(40):
            rows.append(
                {
                    "Service Date": date,
                    "Service Type": "Del - FWD D2D",
                    "LM Type": "D2D",
                    "Shipment ID": f"D{day}-{i}",
                    "Chargeable Weight": 1.0,
                    "Driver ID": 1001,
                    "Driver Name": "[1001] Test",
                    "TIER": "T1",
                }
            )
        for i in range(20):
            rows.append(
                {
                    "Service Date": date,
                    "Service Type": "Del - FWD BSC",
                    "LM Type": "BSC",
                    "Shipment ID": f"B{day}-{i}",
                    "Chargeable Weight": 1.0,
                    "Driver ID": 1001,
                    "Driver Name": "[1001] Test",
                    "TIER": "T1",
                }
            )
    df = normalize_frame(pd.DataFrame(rows), cfg)
    result = MovixPayoutCalculator(cfg).calculate_driver(df, "1001")
    assert result.total_parcels == 26 * 60
    assert result.volume_parcels == 26 * 40
    assert result.avg_parcels_per_day == 40.0
    assert result.qualifies_for_basic is False
    assert result.basic_salary == 0.0


def test_batch_summary():
    cfg = MovixConfig.load()
    df = normalize_frame(_sample_rows(), cfg)
    calc = MovixPayoutCalculator(cfg)
    results = calc.calculate_all(df)
    summary = results_to_summary_frame(results)
    assert len(summary) == 2
    assert set(summary["driver_id"]) == {"1001", "2002"}


def test_filter_billable_prefixes():
    cfg = MovixConfig.load()
    raw = normalize_frame(_sample_rows(), cfg)
    # already filtered; ensure helper is idempotent
    again = filter_billable(raw, cfg)
    assert len(again) == len(raw)


@pytest.mark.skipif(not SAMPLE_XLSX.exists(), reason="IC Payment.xlsx not available")
def test_live_ic_payment_sheet1():
    from movix_dispatcher.ingest import load_sheet1

    cfg = MovixConfig.load()
    df = load_sheet1(SAMPLE_XLSX, cfg)
    assert not df.empty
    assert {"service_date", "shipment_id", "chargeable_weight", "driver_id"} <= set(df.columns)
    allowed = (
        "Del - FWD D2D",
        "Del - FWD BSC",
        "PU - RR D2D",
        "Del - RTS",
        "Failed Deliveries",
    )
    assert df["service_type"].apply(
        lambda s: any(str(s).startswith(p) for p in allowed)
    ).all()

    calc = MovixPayoutCalculator(cfg)
    results = calc.calculate_all(df)
    assert len(results) >= 1
    summary = results_to_summary_frame(results)
    # Partial-week sample cannot meet 26-day basic gate
    assert (summary["basic_salary"] == 0).all()
    assert float(summary["commission_total"].sum()) > 0
