"""HTML invoice generation for Movix OKAR courier payouts."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Optional

from .calculator import PayoutResult
from .config import MovixConfig
from .names import clean_driver_name


def _money(amount: float, symbol: str) -> str:
    return f"{escape(symbol)}{amount:,.2f}"


def build_invoice_html(
    result: PayoutResult,
    config: Optional[MovixConfig] = None,
    company_name: str = "Movix Logistics",
    hub_name: str = "OS Karangan (OKAR)",
    invoice_date: Optional[date] = None,
) -> str:
    """Build a printable HTML invoice for one courier payout result."""
    cfg = config or MovixConfig.load()
    symbol = cfg.currency_symbol
    issued = (invoice_date or date.today()).isoformat()
    courier = clean_driver_name(result.driver_name) or "Courier"
    period = " — ".join(
        part for part in [result.period_start or "—", result.period_end or "—"] if part
    )

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
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --brand: #0f766e;
      --brand-soft: #ccfbf1;
      --surface: #ffffff;
      --bg: #f8fafc;
      --danger: #b91c1c;
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
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    }}
    .hero {{
      padding: 28px 32px;
      background:
        linear-gradient(135deg, rgba(15,118,110,0.95), rgba(15,118,110,0.75)),
        radial-gradient(circle at top right, #99f6e4, transparent 55%);
      color: white;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
    }}
    .brand {{ font-size: 28px; font-weight: 700; letter-spacing: -0.03em; }}
    .sub {{ opacity: 0.9; margin-top: 6px; font-size: 14px; }}
    .badge {{
      align-self: start;
      background: rgba(255,255,255,0.16);
      border: 1px solid rgba(255,255,255,0.28);
      border-radius: 999px;
      padding: 8px 14px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .body {{ padding: 28px 32px 36px; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }}
    .meta .card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
      background: var(--bg);
    }}
    .meta .label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }}
    .meta .value {{ margin-top: 4px; font-weight: 650; font-size: 15px; }}
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
      background: var(--brand-soft);
      color: var(--brand);
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
      color: var(--brand);
    }}
    .row.deduct .amount {{ color: var(--danger); }}
    .note {{
      margin-top: 18px;
      padding: 14px 16px;
      border-radius: 12px;
      background: var(--brand-soft);
      color: #115e59;
      font-size: 13px;
    }}
    .footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 12px;
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
      <div>
        <div class="brand">{escape(company_name)}</div>
        <div class="sub">{escape(hub_name)} · Courier payout invoice</div>
      </div>
      <div class="badge">Invoice</div>
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

      <h2>Commission by weight</h2>
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
