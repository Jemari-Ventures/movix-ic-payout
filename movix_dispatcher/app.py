"""Streamlit UI for Movix OKAR courier payout (standalone)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Streamlit runs this file as a script; ensure repo root is importable.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from movix_dispatcher import brand
from movix_dispatcher.streamlit_compat import as_arrow_safe, width_kwargs
from movix_dispatcher.analytics import (
    driver_chart_frames,
    fleet_chart_frames,
    fleet_kpi_cards,
)
from movix_dispatcher.calculator import MovixPayoutCalculator, PayoutResult, results_to_summary_frame
from movix_dispatcher.config import MovixConfig
from movix_dispatcher.ingest import date_bounds, driver_directory, load_sheet1
from movix_dispatcher.invoice import build_invoice_html
from movix_dispatcher.projections import parse_adjustments_csv, project_full_month_if_short

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config_movix.json"
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "movix-logo.png"
LOGO_MARK_PATH = Path(__file__).resolve().parent.parent / "assets" / "movix-logo-mark.png"


def _money(amount: float, symbol: str) -> str:
    return f"{symbol}{amount:,.2f}"


def _driver_options(drivers: pd.DataFrame) -> List[str]:
    return [
        f"{row.driver_id} — {row.driver_name}" if row.driver_name else str(row.driver_id)
        for row in drivers.itertuples(index=False)
    ]


def _parse_driver_id(choice: str) -> str:
    return choice.split(" — ", 1)[0].strip() if choice else ""


def _result_lookup(results: Optional[List[PayoutResult]], driver_id: str) -> Optional[PayoutResult]:
    if not results:
        return None
    for result in results:
        if str(result.driver_id) == str(driver_id):
            return result
    return None


def main() -> None:
    st.set_page_config(
        page_title="Movix OKAR Payout",
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
                <h1>OKAR Courier Payout</h1>
                <p>Movix Logistics (M) Sdn. Bhd · OS Karangan (OKAR)</p>
              </div>
              <div class="badge">OKAR</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title("Movix OKAR Courier Payout")
        st.caption(
            "Standalone calculator for OS Karangan (OKAR) couriers. "
            "Uses Sheet1 of the IC Payment export and the Movix weight / basic / attendance rate card."
        )

    config = MovixConfig.load(CONFIG_PATH)
    calc = MovixPayoutCalculator(config)

    with st.sidebar:
        st.header("Data")
        uploaded = st.file_uploader("Upload IC Payment Excel (.xlsx)", type=["xlsx"])
        adj_upload = st.file_uploader(
            "Optional MC / absent CSV (driver_id, mc_days, absent_days)",
            type=["csv"],
            key="courier_adj_csv",
        )
        st.markdown("**Courier rate card** — see [RATES.md](RATES.md)")
        st.dataframe(as_arrow_safe(pd.DataFrame(config.rate_table_rows())), hide_index=True, **width_kwargs())
        st.markdown(
            f"- **Del - FWD D2D** — courier tier RM1 / RM1.80 / RM3\n"
            f"- **PU - RR / Del - RTS** — **RM0.70** flat (return)\n"
            f"- **Del - FWD BSC** — **RM0.10** · **Failed** — RM0 audit\n"
            f"- Basic: **{config.currency_symbol}{config.basic_amount:,.0f}** "
            f"(≥{config.basic_required_working_days} days & avg ≥{config.basic_min_avg_parcels_per_day:.0f}/day)\n"
            f"- Attendance: **{config.currency_symbol}{config.attendance_amount:,.0f}** "
            f"(MC −{config.currency_symbol}{config.mc_deduction_per_day:.0f}/day; "
            f"{config.mc_days_disqualify_at}+ MC → no allowance)\n"
            f"- Absent: **{config.currency_symbol}{config.absent_penalty_per_day:.0f}/day**"
        )
        st.caption("Streamlit Cloud: set Python **3.12** (`runtime.txt`).")

    if uploaded is None:
        st.info("Upload an IC Payment `.xlsx` file (Sheet1) to begin.")
        return

    try:
        df = load_sheet1(uploaded, config)
    except Exception as exc:  # noqa: BLE001 — surface ingest errors in UI
        st.error(f"Failed to load Sheet1: {exc}")
        return

    if df.empty:
        st.warning("No billable forward-delivery rows found after filtering.")
        return

    start, end = date_bounds(df)
    drivers = driver_directory(df)

    st.success(
        f"Loaded **{len(df):,}** billable parcels · "
        f"**{len(drivers)}** drivers · "
        f"period **{start.date() if start is not None else '—'}** → "
        f"**{end.date() if end is not None else '—'}**"
    )

    tab_batch, tab_driver, tab_analytics, tab_invoice = st.tabs(
        ["Batch payout", "Single driver", "Analytics", "Invoice"]
    )

    with tab_batch:
        st.subheader("Batch payout")
        st.caption("MC / absent days default to 0. Adjust per driver in the editor, then recalculate.")

        adj_seed = drivers[["driver_id", "driver_name"]].copy()
        adj_seed["mc_days"] = 0
        adj_seed["absent_days"] = 0
        if adj_upload is not None:
            try:
                csv_adj = parse_adjustments_csv(pd.read_csv(adj_upload))
                adj_seed["mc_days"] = adj_seed["driver_id"].map(
                    lambda d: int((csv_adj.get(str(d)) or {}).get("mc_days", 0))
                )
                adj_seed["absent_days"] = adj_seed["driver_id"].map(
                    lambda d: int((csv_adj.get(str(d)) or {}).get("absent_days", 0))
                )
                st.caption(f"Loaded MC/absent for **{len(csv_adj)}** drivers from CSV.")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Could not parse adjustments CSV: {exc}")
        edited = st.data_editor(
            adj_seed,
            hide_index=True,
            **width_kwargs(),
            disabled=["driver_id", "driver_name"],
            column_config={
                "mc_days": st.column_config.NumberColumn("MC days", min_value=0, step=1),
                "absent_days": st.column_config.NumberColumn("Absent days", min_value=0, step=1),
            },
            key="movix_adj_editor",
        )

        if st.button("Calculate all drivers", type="primary"):
            adjustments: Dict[str, Dict[str, int]] = {}
            for row in edited.itertuples(index=False):
                adjustments[str(row.driver_id)] = {
                    "mc_days": int(row.mc_days or 0),
                    "absent_days": int(row.absent_days or 0),
                }
            results = calc.calculate_all(df, adjustments=adjustments)
            summary = results_to_summary_frame(results)
            st.session_state["movix_batch_summary"] = summary
            st.session_state["movix_batch_results"] = results
            st.session_state["movix_adjustments"] = adjustments
            st.session_state["movix_freeze_payload"] = {
                "frozen_at": pd.Timestamp.utcnow().isoformat(),
                "period_start": str(start.date()) if start is not None else None,
                "period_end": str(end.date()) if end is not None else None,
                "adjustments": adjustments,
                "summary": summary.to_dict(orient="records"),
            }

        summary = st.session_state.get("movix_batch_summary")
        if summary is not None and not summary.empty:
            batch_results_early: List[PayoutResult] = st.session_state.get("movix_batch_results") or []
            proj = project_full_month_if_short(batch_results_early, config)
            if proj is not None:
                st.warning(proj.message)
            display_cols = [
                "driver_id",
                "driver_name",
                "total_parcels",
                "working_days",
                "avg_parcels_per_day",
                "commission_total",
                "basic_salary",
                "attendance_allowance",
                "absent_penalty",
                "net_payout",
                "qualifies_for_basic",
                "eligibility_reason",
            ]
            present = [c for c in display_cols if c in summary.columns]
            st.dataframe(as_arrow_safe(summary[present]), hide_index=True, **width_kwargs())

            totals = {
                "Parcels": int(summary["total_parcels"].sum()),
                "Commission": _money(float(summary["commission_total"].sum()), config.currency_symbol),
                "Basic": _money(float(summary["basic_salary"].sum()), config.currency_symbol),
                "Attendance": _money(float(summary["attendance_allowance"].sum()), config.currency_symbol),
                "Absent penalties": _money(float(summary["absent_penalty"].sum()), config.currency_symbol),
                "Net payout": _money(float(summary["net_payout"].sum()), config.currency_symbol),
            }
            cols = st.columns(len(totals))
            for col, (label, value) in zip(cols, totals.items()):
                col.metric(label, value)

            batch_results: List[PayoutResult] = st.session_state.get("movix_batch_results") or []
            if batch_results:
                service_rows = []
                for result in batch_results:
                    for service, count in result.parcels_by_service.items():
                        service_rows.append(
                            {
                                "Service type": service,
                                "Parcels": count,
                                "Commission": result.commission_by_service.get(service, 0.0),
                            }
                        )
                if service_rows:
                    service_df = (
                        pd.DataFrame(service_rows)
                        .groupby("Service type", as_index=False)
                        .agg(Parcels=("Parcels", "sum"), Commission=("Commission", "sum"))
                        .sort_values("Commission", ascending=False)
                    )
                    st.markdown("**Fleet breakdown by service type**")
                    st.dataframe(as_arrow_safe(service_df), hide_index=True, **width_kwargs())
                    returns = service_df[
                        service_df["Service type"]
                        .astype(str)
                        .str.contains("PU - RR|Del - RTS", regex=True)
                    ]
                    if not returns.empty:
                        st.info(
                            "Returns (PU-RR / RTS) pay **RM0.70** flat on the courier card. "
                            f"This period: **{int(returns['Parcels'].sum()):,}** parcels · "
                            f"{_money(float(returns['Commission'].sum()), config.currency_symbol)}."
                        )

            csv_buf = io.StringIO()
            summary.to_csv(csv_buf, index=False)
            st.download_button(
                "Download batch summary CSV",
                data=csv_buf.getvalue(),
                file_name="movix_okar_payout_summary.csv",
                mime="text/csv",
            )
            freeze = st.session_state.get("movix_freeze_payload")
            if freeze:
                st.download_button(
                    "Freeze / download approved payroll JSON",
                    data=json.dumps(freeze, indent=2, default=str),
                    file_name=f"movix_okar_payroll_freeze_{freeze.get('period_end') or 'na'}.json",
                    mime="application/json",
                )

    with tab_driver:
        st.subheader("Single driver")
        options = _driver_options(drivers)
        choice = st.selectbox("Driver", options, key="single_driver_select")
        driver_id = _parse_driver_id(choice)
        c1, c2 = st.columns(2)
        mc_days = c1.number_input("MC / compassionate days", min_value=0, value=0, step=1, key="single_mc")
        absent_days = c2.number_input(
            "Unauthorized absent days", min_value=0, value=0, step=1, key="single_absent"
        )

        if driver_id:
            result = calc.calculate_driver(df, driver_id, mc_days=mc_days, absent_days=absent_days)
            st.session_state["movix_single_result"] = result

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Parcels", f"{result.total_parcels:,}")
            m2.metric("Working days", result.working_days)
            m3.metric("Avg / day", f"{result.avg_parcels_per_day:.2f}")
            m4.metric("Net payout", _money(result.net_payout, config.currency_symbol))

            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Commission", _money(result.commission_total, config.currency_symbol))
            b2.metric("Basic salary", _money(result.basic_salary, config.currency_symbol))
            b3.metric("Attendance", _money(result.attendance_allowance, config.currency_symbol))
            b4.metric("Absent penalty", _money(result.absent_penalty, config.currency_symbol))

            st.info(result.eligibility_reason)

            service_df = result.service_breakdown_frame()
            if not service_df.empty:
                st.markdown("**Commission by service type**")
                st.dataframe(as_arrow_safe(service_df), hide_index=True, **width_kwargs())

            if result.parcels_by_band:
                band_df = pd.DataFrame(
                    [
                        {
                            "Weight band": band,
                            "Parcels": result.parcels_by_band.get(band, 0),
                            "Commission": result.commission_by_band.get(band, 0.0),
                        }
                        for band in result.parcels_by_band
                    ]
                )
                st.markdown("**Commission by weight / rate label**")
                st.dataframe(as_arrow_safe(band_df), hide_index=True, **width_kwargs())

            if not result.daily_summary.empty:
                st.markdown("**Daily summary**")
                st.dataframe(as_arrow_safe(result.daily_summary), hide_index=True, **width_kwargs())

            if not result.parcel_detail.empty:
                export_cols = [
                    c
                    for c in [
                        "service_date",
                        "service_type",
                        "lm_type",
                        "shipment_id",
                        "chargeable_weight",
                        "weight_band",
                        "commission_rate",
                        "commission_amount",
                        "driver_id",
                        "driver_name",
                        "tier",
                    ]
                    if c in result.parcel_detail.columns
                ]
                detail = result.parcel_detail[export_cols].copy()
                detail["service_date"] = pd.to_datetime(detail["service_date"]).dt.strftime("%Y-%m-%d")
                csv_detail = io.StringIO()
                detail.to_csv(csv_detail, index=False)
                st.download_button(
                    "Download parcel detail CSV",
                    data=csv_detail.getvalue(),
                    file_name=f"movix_okar_parcels_{driver_id}.csv",
                    mime="text/csv",
                )

    with tab_analytics:
        st.subheader("Analytics")
        batch_results: List[PayoutResult] = st.session_state.get("movix_batch_results") or []
        if not batch_results:
            st.info("Run **Calculate all drivers** in the Batch payout tab to unlock fleet analytics.")
        else:
            kpis = fleet_kpi_cards(batch_results)
            # 2+2+1 stacks better on phones than 5 cramped columns
            r1 = st.columns(2)
            r1[0].metric("Drivers", int(kpis["drivers"]))
            r1[1].metric("Parcels", f"{int(kpis['parcels']):,}")
            r2 = st.columns(2)
            r2[0].metric("Commission", _money(kpis["commission"], config.currency_symbol))
            r2[1].metric("Net payout", _money(kpis["net"], config.currency_symbol))
            st.metric(
                "Basic qualified",
                f"{int(kpis['basic_qualified'])}/{int(kpis['drivers'])}",
            )

            frames = fleet_chart_frames(batch_results, short_labels=True)
            if "ranking" in frames:
                st.markdown("**Driver ranking** (readable on mobile)")
                st.caption("Use this table as the source of truth; charts below use short Driver IDs.")
                st.dataframe(as_arrow_safe(frames["ranking"]), hide_index=True, **width_kwargs())

            if "net_by_driver" in frames:
                st.markdown("**Net payout by driver ID**")
                st.bar_chart(frames["net_by_driver"], color=brand.PURPLE, height=280)
            if "volume" in frames:
                st.markdown("**Parcels & daily average**")
                st.bar_chart(frames["volume"], color=[brand.PURPLE, brand.PURPLE_MID], height=280)
            if "service_mix" in frames:
                st.markdown("**Fleet mix by service type**")
                st.bar_chart(
                    frames["service_mix"],
                    color=[brand.PURPLE_LIGHT, brand.YELLOW],
                    height=260,
                )
                st.dataframe(
                    as_arrow_safe(
                        frames["service_mix"]
                        .reset_index()
                        .rename(columns={"service_type": "Service type"})
                    ),
                    hide_index=True,
                    **width_kwargs(),
                )
            if "weight_mix" in frames:
                st.markdown("**Fleet weight / rate-label mix**")
                st.bar_chart(
                    frames["weight_mix"],
                    color=[brand.PURPLE_LIGHT, brand.YELLOW],
                    height=260,
                )
                st.dataframe(
                    frames["weight_mix"].reset_index().rename(columns={"weight_band": "Weight band"}),
                    hide_index=True,
                    **width_kwargs(),
                )
            if "composition" in frames:
                st.markdown("**Payout composition**")
                st.bar_chart(
                    frames["composition"],
                    color=[brand.PURPLE, brand.PURPLE_MID, brand.YELLOW],
                    height=280,
                )

        st.markdown("---")
        st.markdown("**Driver deep-dive**")
        options = _driver_options(drivers)
        analytics_choice = st.selectbox("Driver for charts", options, key="analytics_driver_select")
        analytics_driver_id = _parse_driver_id(analytics_choice)
        if analytics_driver_id:
            adjustments = st.session_state.get("movix_adjustments") or {}
            adj = adjustments.get(analytics_driver_id, {})
            driver_result = _result_lookup(batch_results, analytics_driver_id) or calc.calculate_driver(
                df,
                analytics_driver_id,
                mc_days=int(adj.get("mc_days", 0) or 0),
                absent_days=int(adj.get("absent_days", 0) or 0),
            )
            driver_frames = driver_chart_frames(driver_result)
            if not driver_frames:
                st.warning("No chart data for this driver.")
            else:
                if "daily" in driver_frames:
                    st.markdown("**Daily parcels & commission**")
                    st.line_chart(driver_frames["daily"], color=[brand.PURPLE, brand.YELLOW], height=260)
                if "daily_table" in driver_frames:
                    st.dataframe(as_arrow_safe(driver_frames["daily_table"]), hide_index=True, **width_kwargs())
                if "service" in driver_frames:
                    st.markdown("**Service type mix**")
                    st.bar_chart(
                        driver_frames["service"],
                        color=[brand.PURPLE_LIGHT, brand.YELLOW],
                        height=240,
                    )
                if "service_table" in driver_frames:
                    st.dataframe(
                        as_arrow_safe(driver_frames["service_table"]),
                        hide_index=True,
                        **width_kwargs(),
                    )
                if "bands" in driver_frames:
                    st.markdown("**Weight / rate-label mix**")
                    st.bar_chart(
                        driver_frames["bands"],
                        color=[brand.PURPLE_LIGHT, brand.YELLOW],
                        height=240,
                    )
                if "bands_table" in driver_frames:
                    st.dataframe(as_arrow_safe(driver_frames["bands_table"]), hide_index=True, **width_kwargs())

    with tab_invoice:
        st.subheader("Invoice")
        options = _driver_options(drivers)
        default_index = 0
        single_result: Optional[PayoutResult] = st.session_state.get("movix_single_result")
        if single_result is not None:
            for idx, option in enumerate(options):
                if option.startswith(f"{single_result.driver_id} ") or option == str(single_result.driver_id):
                    default_index = idx
                    break

        invoice_choice = st.selectbox(
            "Driver for invoice",
            options,
            index=default_index if options else 0,
            key="invoice_driver_select",
        )
        invoice_driver_id = _parse_driver_id(invoice_choice)
        adjustments = st.session_state.get("movix_adjustments") or {}
        adj = adjustments.get(invoice_driver_id, {})
        i1, i2 = st.columns(2)
        invoice_mc = i1.number_input(
            "MC / compassionate days",
            min_value=0,
            value=int(adj.get("mc_days", 0) or 0),
            step=1,
            key="invoice_mc_days",
        )
        invoice_absent = i2.number_input(
            "Unauthorized absent days",
            min_value=0,
            value=int(adj.get("absent_days", 0) or 0),
            step=1,
            key="invoice_absent_days",
        )

        if invoice_driver_id:
            batch_results = st.session_state.get("movix_batch_results") or []
            invoice_result = calc.calculate_driver(
                df,
                invoice_driver_id,
                mc_days=invoice_mc,
                absent_days=invoice_absent,
            )
            # Keep batch result only when adjustments match zero defaults and no overrides needed
            cached = _result_lookup(batch_results, invoice_driver_id)
            if (
                cached
                and int(adj.get("mc_days", 0) or 0) == invoice_mc
                and int(adj.get("absent_days", 0) or 0) == invoice_absent
            ):
                invoice_result = cached

            invoice_html = build_invoice_html(invoice_result, config)
            components.html(invoice_html, height=1100, scrolling=True)
            st.download_button(
                "Download invoice (HTML)",
                data=invoice_html,
                file_name=f"movix_okar_invoice_{invoice_driver_id}_{invoice_result.period_start or 'na'}.html",
                mime="text/html",
            )


if __name__ == "__main__":
    main()
