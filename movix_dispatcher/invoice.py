"""HTML invoice generation for Movix OKAR courier payouts."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Optional

from . import brand
from .calculator import PayoutResult
from .config import MovixConfig
from .names import clean_driver_name


def _money(amount: float, symbol: str) -> str:
    return f"{escape(symbol)}{amount:,.2f}"


def build_invoice_html(
    result: PayoutResult,
    config: Optional[MovixConfig] = None,
    company_name: str = brand.COMPANY_NAME,
    hub_name: str = brand.HUB_NAME,
    invoice_date: Optional[date] = None,
) -> str:
    """Build a printable HTML invoice for one courier payout result."""
    cfg = config or MovixConfig.load()
    symbol = cfg.currency_symbol
    logo_uri = brand.logo_data_uri(header=True)
    issued = (invoice_date or date.today()).isoformat()
    courier = clean_driver_name(result.driver_name) or "Courier"
    period = " — ".join(
        part for part in [result.period_start or "—", result.period_end or "—"] if part
    )

    service_rows = ""
    for service, count in result.parcels_by_service.items():
        amount = result.commission_by_service.get(service, 0.0)
        service_rows += (
            f"<tr><td>{escape(str(service))}</td>"
            f"<td class='num'>{int(count):,}</td>"
            f"<td class='num'>{_money(float(amount), symbol)}</td></tr>"
        )
    if not service_rows:
        service_rows = "<tr><td colspan='3'>No billable parcels</td></tr>"

    band_rows = ""
    for band, count in result.parcels_by_band.items():
        amount = result.commission_by_band.get(band, 0.0)
        band_rows += (
            f"<tr><td>{escape(str(band))}</td>"
            f"<td class='num'>{int(count):,}</td>"
            f"<td class='num'>{_money(float(amount), symbol)}</td></tr>"
        )
    if not band_rows:
        band_rows = "<tr><td colspan='3'>No billable parcels</td></tr>"

    daily_rows = ""
    if result.daily_summary is not None and not result.daily_summary.empty:
        for row in result.daily_summary.itertuples(index=False):
            daily_rows += (
                f"<tr><td>{escape(str(row.service_date))}</td>"
                f"<td class='num'>{int(row.parcels):,}</td>"
                f"<td class='num'>{_money(float(row.commission), symbol)}</td></tr>"
            )
    if not daily_rows:
        daily_rows = "<tr><td colspan='3'>No daily rows</td></tr>"

    eligibility = escape(result.eligibility_reason or "")
    basic_note = "Qualified" if result.qualifies_for_basic else "Not qualified"
    attendance_note = "Qualified" if result.qualifies_for_attendance else "Not qualified"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Invoice — {escape(courier)} ({escape(result.driver_id)})</title>
  <style>
    :root {{
      --ink: {brand.INK};
      --muted: {brand.MUTED};
      --line: {brand.LINE};
      --brand: {brand.TEAL};
      --brand-navy: {brand.NAVY};
      --brand-blue: {brand.BLUE};
      --brand-yellow: {brand.YELLOW};
      --brand-soft: {brand.SOFT_TEAL};
      --surface: {brand.SURFACE};
      --bg: {brand.BACKGROUND};
      --danger: {brand.DANGER};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
    }}
    .sheet {{
      max-width: 880px;
      margin: 24px auto;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(18, 48, 74, 0.08);
    }}
    .hero {{
      padding: 18px 20px 20px;
      background: {brand.PURPLE};
      color: white;
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
      box-sizing: border-box;
    }}
    .hero-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      width: 100%;
    }}
    .hero-logo {{
      height: 56px;
      width: auto;
      max-width: min(260px, 70%);
      object-fit: contain;
      object-position: left center;
      background: transparent;
      border-radius: 0;
      display: block;
      flex: 0 1 auto;
    }}
    .hero-copy {{
      min-width: 0;
      width: 100%;
    }}
    .brand {{
      font-size: clamp(1rem, 4.2vw, 1.35rem);
      font-weight: 750;
      letter-spacing: -0.02em;
      color: {brand.YELLOW};
      line-height: 1.25;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .sub {{
      margin-top: 4px;
      font-size: 13px;
      color: #FFFFFF;
      opacity: 0.95;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}
    .badge {{
      flex: 0 0 auto;
      background: {brand.YELLOW};
      color: {brand.PURPLE};
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .body {{ padding: 20px 16px 28px; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }}
    .meta .card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
      background: {brand.SOFT_BLUE};
    }}
    .meta .label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }}
    .meta .value {{ margin-top: 4px; font-weight: 650; font-size: 15px; color: var(--brand-navy); }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 15px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 14px; }}
    th {{
      background: {brand.PURPLE};
      color: {brand.YELLOW};
      text-align: left;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    tr:last-child td {{ border-bottom: none; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .totals {{
      margin-top: 22px;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px 16px;
      background: #fff;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 10px 0;
      border-bottom: 1px dashed var(--line);
      font-size: 15px;
    }}
    .row:last-child {{ border-bottom: none; }}
    .row.total {{
      margin-top: 4px;
      font-size: 20px;
      font-weight: 750;
      color: var(--brand-navy);
    }}
    .row.deduct .amount {{ color: var(--danger); }}
    .note {{
      margin-top: 18px;
      padding: 14px 16px;
      border-radius: 12px;
      background: var(--brand-soft);
      color: {brand.NAVY};
      font-size: 13px;
    }}
    .footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 640px) {{
      .sheet {{ margin: 8px auto; border-radius: 12px; }}
      .hero {{ padding: 14px 14px 16px; gap: 10px; }}
      .hero-logo {{ height: 44px; max-width: 65%; }}
      .body {{ padding: 16px 12px 22px; }}
      .meta .card {{ padding: 12px; }}
      .row {{ font-size: 14px; }}
      .row.total {{ font-size: 17px; }}
    }}
    @media print {{
      body {{ background: white; }}
      .sheet {{ margin: 0; border: none; box-shadow: none; border-radius: 0; }}
    }}
  </style>
</head>
<body>
  <div class="sheet">
    <div class="hero">
      <div class="hero-top">
        <img class="hero-logo" src="{logo_uri}" alt="{escape(company_name)}" />
        <div class="badge">Invoice</div>
      </div>
      <div class="hero-copy">
        <div class="brand">{escape(company_name)}</div>
        <div class="sub">{escape(hub_name)} · Courier payout invoice</div>
      </div>
    </div>
    <div class="body">
      <div class="meta">
        <div class="card"><div class="label">Courier</div><div class="value">{escape(courier)}</div></div>
        <div class="card"><div class="label">Driver ID</div><div class="value">{escape(result.driver_id)}</div></div>
        <div class="card"><div class="label">Period</div><div class="value">{escape(period)}</div></div>
        <div class="card"><div class="label">Issued</div><div class="value">{escape(issued)}</div></div>
      </div>

      <div class="meta">
        <div class="card"><div class="label">Parcels</div><div class="value">{result.total_parcels:,}</div></div>
        <div class="card"><div class="label">Working days</div><div class="value">{result.working_days}</div></div>
        <div class="card"><div class="label">Avg / day</div><div class="value">{result.avg_parcels_per_day:.2f}</div></div>
        <div class="card"><div class="label">Net payout</div><div class="value">{_money(result.net_payout, symbol)}</div></div>
      </div>

      <h2>Commission by service type</h2>
      <table>
        <thead><tr><th>Service type</th><th class="num">Parcels</th><th class="num">Amount</th></tr></thead>
        <tbody>{service_rows}</tbody>
      </table>

      <h2>Commission by weight / rate label</h2>
      <table>
        <thead><tr><th>Weight band</th><th class="num">Parcels</th><th class="num">Amount</th></tr></thead>
        <tbody>{band_rows}</tbody>
      </table>

      <h2>Daily delivery</h2>
      <table>
        <thead><tr><th>Date</th><th class="num">Parcels</th><th class="num">Commission</th></tr></thead>
        <tbody>{daily_rows}</tbody>
      </table>

      <div class="totals">
        <div class="row"><span>Commission</span><span class="amount">{_money(result.commission_total, symbol)}</span></div>
        <div class="row"><span>Basic salary ({escape(basic_note)})</span><span class="amount">{_money(result.basic_salary, symbol)}</span></div>
        <div class="row"><span>Attendance allowance ({escape(attendance_note)})</span><span class="amount">{_money(result.attendance_allowance, symbol)}</span></div>
        <div class="row"><span>Gross</span><span class="amount">{_money(result.gross_payout, symbol)}</span></div>
        <div class="row deduct"><span>Absent penalty</span><span class="amount">−{_money(result.absent_penalty, symbol)}</span></div>
        <div class="row total"><span>Net payable</span><span class="amount">{_money(result.net_payout, symbol)}</span></div>
      </div>

      <div class="note">{eligibility}</div>
      <div class="footer">
        Generated for {escape(hub_name)}. Final amounts remain subject to operations verification and IC agreement terms.
      </div>
    </div>
  </div>
</body>
</html>
"""
