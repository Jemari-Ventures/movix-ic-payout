"""Streamlit UI for Movix OKAR fleet management (SPX revenue + margin)."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st

from movix_dispatcher import brand
from movix_dispatcher.calculator import MovixPayoutCalculator
from movix_dispatcher.config import MovixConfig
from movix_dispatcher.ingest import date_bounds, driver_directory, load_sheet1

from movix_management.analytics import driver_chart_frames, fleet_chart_frames, fleet_kpi_cards
from movix_management.calculator import (
    DriverFleetResult,
    FleetPayoutCalculator,
    results_to_summary_frame,
)
from movix_management.config import ManagementConfig

MGMT_CONFIG_PATH = _ROOT / "config_management.json"
COURIER_CONFIG_PATH = _ROOT / "config_movix.json"
LOGO_PATH = _ROOT / "assets" / "movix-logo.png"
LOGO_MARK_PATH = _ROOT / "assets" / "movix-logo-mark.png"


def _money(amount: float, symbol: str) -> str:
    return f"{symbol}{amount:,.2f}"


def _driver_options(drivers: pd.DataFrame) -> List[str]:
    return [
        f"{row.driver_id} — {row.driver_name}" if row.driver_name else str(row.driver_id)
        for row in drivers.itertuples(index=False)
    ]


def _parse_driver_id(choice: str) -> str:
    return choice.split(" — ", 1)[0].strip() if choice else ""


def _result_lookup(
    results: Optional[List[DriverFleetResult]], driver_id: str
) -> Optional[DriverFleetResult]:
    if not results:
        return None
    for result in results:
        if str(result.driver_id) == str(driver_id):
            return result
    return None


def _render_kpis(cards: List[Dict[str, str]]) -> None:
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        col.metric(card["label"], card["value"])


def main() -> None:
    st.set_page_config(
        page_title="Movix OKAR Fleet",
        page_icon=str(LOGO_MARK_PATH) if LOGO_MARK_PATH.exists() else None,
        layout="wide",
    )
    st.markdown(brand.streamlit_theme_css(), unsafe_allow_html=True)

    if LOGO_PATH.exists():
        st.markdown(
            f"""
            <div class="movix-hero">
              <img src="{brand.logo_data_uri(header=True)}" alt="Movix Logistics (M) Sdn. Bhd" />
              <div class="copy">
                <h1>OKAR Fleet Management</h1>
                <p>SPX partner revenue · courier cost · margin · OS Karangan (OKAR)</p>
              </div>
              <div class="badge">Fleet</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title("Movix OKAR Fleet Management")
        st.caption(
            "Management view for OS Karangan (OKAR). "
            "SPX weight rate card revenue vs OKAR courier payout cost."
        )

    mgmt = ManagementConfig.load(MGMT_CONFIG_PATH)
    courier_cfg = MovixConfig.load(COURIER_CONFIG_PATH)
    fleet_calc = FleetPayoutCalculator(mgmt, courier_cfg)
    courier_calc = MovixPayoutCalculator(courier_cfg)
    symbol = mgmt.currency_symbol

    with st.sidebar:
        st.header("Data")
        uploaded = st.file_uploader("Upload IC Payment Excel (.xlsx)", type=["xlsx"])
        st.markdown("**SPX partner rate card**")
        st.caption("Door-to-door / return pickup · Drop-off / return to SPX")
        st.dataframe(
            pd.DataFrame(mgmt.rate_table_rows()),
            hide_index=True,
            width="stretch",
        )
        with st.expander("Channel mapping"):
            st.markdown(
                "- **D2D** → door-to-door rate\n"
                "- **BSC** → drop-off rate\n"
                "- Billable rows: `Del - FWD*` (same Sheet1 as courier app)"
            )
        for note in mgmt.notes:
            st.caption(f"• {note}")

    if uploaded is None:
        st.info(
            "Upload the IC Payment Excel to see fleet revenue, courier cost, and margin. "
            "This app is for hub / ops managers — couriers use the separate OKAR Payout app."
        )
        return

    try:
        df = load_sheet1(uploaded, courier_cfg)
    except Exception as exc:  # noqa: BLE001 — surface parse errors in UI
        st.error(f"Could not read Sheet1: {exc}")
        return

    if df.empty:
        st.warning("No billable `Del - FWD` parcels found in this file.")
        return

    start, end = date_bounds(df)
    drivers = driver_directory(df)
    st.caption(
        f"Period **{start}** → **{end}** · "
        f"**{len(df):,}** billable parcels · **{len(drivers)}** drivers"
    )

    tab_fleet, tab_driver, tab_analytics, tab_rates = st.tabs(
        ["Fleet overview", "Driver margin", "Analytics", "Rate cards"]
    )

    with tab_fleet:
        st.subheader("Fleet P&L snapshot")
        st.caption(
            "SPX revenue from the partner weight card minus OKAR courier net payout "
            "(commission + basic + attendance − absences)."
        )
        if st.button("Calculate fleet", type="primary", key="calc_fleet"):
            with st.spinner("Calculating SPX revenue and courier cost…"):
                payouts = courier_calc.calculate_all(df)
                results = fleet_calc.calculate_all(df, payouts=payouts)
                st.session_state["mgmt_results"] = results
                st.session_state["mgmt_summary"] = fleet_calc.fleet_summary(results)

        results: Optional[List[DriverFleetResult]] = st.session_state.get("mgmt_results")
        summary = st.session_state.get("mgmt_summary")
        if summary is not None:
            _render_kpis(fleet_kpi_cards(summary, symbol))
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Channel mix**")
                st.write(
                    f"Door-to-door: **{summary.door_to_door_parcels:,}** parcels · "
                    f"{_money(summary.door_to_door_revenue, symbol)}"
                )
                st.write(
                    f"Drop-off: **{summary.drop_off_parcels:,}** parcels · "
                    f"{_money(summary.drop_off_revenue, symbol)}"
                )
            with c2:
                st.markdown("**Takeaway**")
                if summary.margin >= 0:
                    st.success(
                        f"Fleet covers courier cost with "
                        f"{_money(summary.margin, symbol)} gross margin "
                        f"({summary.margin_pct:.1f}%)."
                    )
                else:
                    st.error(
                        f"Courier cost exceeds SPX revenue by "
                        f"{_money(abs(summary.margin), symbol)}. "
                        "Review mix of D2D vs BSC and heavy parcels."
                    )

        if results:
            summary_df = results_to_summary_frame(results)
            display_cols = [
                "driver_id",
                "driver_name",
                "total_parcels",
                "working_days",
                "spx_revenue",
                "courier_cost",
                "margin",
                "margin_pct",
                "door_to_door_parcels",
                "drop_off_parcels",
            ]
            show = summary_df[[c for c in display_cols if c in summary_df.columns]].copy()
            show = show.sort_values("margin", ascending=False)
            st.dataframe(show, hide_index=True, width="stretch")
            buf = io.BytesIO()
            show.to_csv(buf, index=False)
            st.download_button(
                "Download fleet CSV",
                data=buf.getvalue(),
                file_name="okar_fleet_margin.csv",
                mime="text/csv",
            )

    with tab_driver:
        st.subheader("Driver contribution")
        choice = st.selectbox("Driver", options=_driver_options(drivers))
        driver_id = _parse_driver_id(choice)
        col_a, col_b = st.columns(2)
        with col_a:
            mc_days = st.number_input("MC days", min_value=0, max_value=31, value=0, step=1)
        with col_b:
            absent_days = st.number_input(
                "Absent days", min_value=0, max_value=31, value=0, step=1
            )

        run_driver = st.button("Calculate driver", type="primary", key="calc_driver")
        result = None
        if run_driver:
            result = fleet_calc.calculate_driver(
                df, driver_id, mc_days=int(mc_days), absent_days=int(absent_days)
            )
            st.session_state["mgmt_driver_result"] = result
        elif st.session_state.get("mgmt_driver_result") and str(
            st.session_state["mgmt_driver_result"].driver_id
        ) == str(driver_id):
            result = st.session_state["mgmt_driver_result"]
        else:
            result = _result_lookup(st.session_state.get("mgmt_results"), driver_id)

        if result is not None:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("SPX revenue", _money(result.spx_revenue, symbol))
            k2.metric("Courier cost", _money(result.courier_cost, symbol))
            k3.metric("Margin", _money(result.margin, symbol))
            k4.metric("Margin %", f"{result.margin_pct:.1f}%")

            m1, m2, m3 = st.columns(3)
            m1.metric("Parcels", f"{result.total_parcels:,}")
            m2.metric("Door-to-door", f"{result.door_to_door_parcels:,}")
            m3.metric("Drop-off", f"{result.drop_off_parcels:,}")

            charts = driver_chart_frames(result)
            if not charts["weight_band"].empty:
                st.markdown("**Revenue by weight band**")
                st.bar_chart(
                    charts["weight_band"].set_index("weight_band")["revenue"],
                    width="stretch",
                )
            if not charts["channel_mix"].empty:
                st.markdown("**Channel mix**")
                st.bar_chart(
                    charts["channel_mix"].set_index("channel")["revenue"],
                    width="stretch",
                )
            if not charts["daily"].empty:
                st.markdown("**Daily SPX revenue**")
                daily = charts["daily"].copy()
                daily["service_date"] = pd.to_datetime(daily["service_date"]).dt.date.astype(str)
                st.line_chart(daily.set_index("service_date")["revenue"], width="stretch")

            st.markdown("**Parcel detail**")
            detail_cols = [
                c
                for c in [
                    "service_date",
                    "service_type",
                    "lm_type",
                    "shipment_id",
                    "chargeable_weight",
                    "weight_band",
                    "channel",
                    "spx_rate",
                    "spx_revenue",
                ]
                if c in result.parcel_detail.columns
            ]
            st.dataframe(
                result.parcel_detail[detail_cols],
                hide_index=True,
                width="stretch",
            )

    with tab_analytics:
        st.subheader("Fleet analytics")
        results = st.session_state.get("mgmt_results")
        if not results:
            st.info("Run **Calculate fleet** on the Fleet overview tab first.")
        else:
            frames = fleet_chart_frames(results)
            if not frames["margin_by_driver"].empty:
                st.markdown("**Margin by driver**")
                chart_df = frames["margin_by_driver"].set_index("driver")[
                    ["spx_revenue", "courier_cost", "margin"]
                ]
                st.bar_chart(chart_df, width="stretch")
            c1, c2 = st.columns(2)
            with c1:
                if not frames["channel_mix"].empty:
                    st.markdown("**Channel revenue**")
                    st.bar_chart(
                        frames["channel_mix"].set_index("channel")["revenue"],
                        width="stretch",
                    )
            with c2:
                if not frames["weight_band"].empty:
                    st.markdown("**Parcels by weight band**")
                    st.bar_chart(
                        frames["weight_band"].set_index("weight_band")["parcels"],
                        width="stretch",
                    )

    with tab_rates:
        st.subheader("SPX partner rates (management)")
        st.dataframe(
            pd.DataFrame(mgmt.rate_table_rows()),
            hide_index=True,
            width="stretch",
        )
        st.subheader("OKAR courier rates (cost side)")
        st.dataframe(
            pd.DataFrame(courier_cfg.rate_table_rows()),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Basic {symbol}{courier_cfg.basic_amount:,.0f} · "
            f"Attendance {symbol}{courier_cfg.attendance_amount:,.0f} · "
            f"Absent −{symbol}{courier_cfg.absent_penalty_per_day:,.0f}/day"
        )


if __name__ == "__main__":
    main()
