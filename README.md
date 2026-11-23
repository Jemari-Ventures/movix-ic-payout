# Movix IC Payout

Standalone Streamlit apps for **Movix Logistics (M) Sdn. Bhd** — OS Karangan (OKAR).

Two deployable surfaces share this repo, brand, and Sheet1 contract:

| App | Branch (recommended) | Entrypoint | Audience |
|-----|----------------------|------------|----------|
| **OKAR Courier Payout** | `main` | `app.py` → `movix_dispatcher/app.py` | Couriers / payroll |
| **OKAR Fleet Management** | `feat/management-fleet-view` | `app_management.py` → `movix_management/app.py` | Hub / ops / finance |

Same purple/yellow Movix UI language; copy and KPIs tailored per role.

**Rate matrix (source of truth):** see [`RATES.md`](RATES.md). Edit amounts in JSON only.

## Courier rate card (`config_movix.json`)

| Service / component | Rule |
|---------------------|------|
| **Del - FWD D2D** | Weight tier RM1 / RM1.80 / RM3 |
| **Del - FWD BSC** | RM0.10 flat |
| **PU - RR D2D / Del - RTS** | RM0.70 flat |
| **Failed Deliveries** | RM0 audit (visible, no pay) |
| Basic salary | RM1,700 if ≥26 working days **and** avg ≥50 parcels/day |
| Attendance | RM200 same gate; MC −RM100/day; ≥2 MC → no allowance |
| Absent | −RM30/day |

Volume gate currently counts **all billable** parcels. Ops review of whether BSC/returns count is **on hold**.

## SPX partner rate card (`config_management.json`)

- **Del - FWD D2D / PU - RR / Del - RTS** → SPX door-to-door weight column (contiguous bands; first match at shared edges)
- **Del - FWD BSC** → RM0.10 flat
- **Failed Deliveries** → RM0 audit

Fleet margin = SPX revenue − OKAR courier net payout.

## Input

Excel workbook, **Sheet1** only:

- Service Date, Service Type, LM Type, Shipment ID, Chargeable Weight, Driver ID, Driver Name, TIER (optional)

Optional MC/absent CSV for courier batch: `driver_id`, `mc_days`, `absent_days`.

## Setup

```bash
cd movix-ic-payout
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
# Courier payout (payroll)
streamlit run app.py

# Fleet management (ops)
streamlit run app_management.py
```

### Courier tabs

Batch payout (service mix, full-month projection, freeze JSON) · Single driver · Analytics · Invoice

### Fleet tabs

Fleet overview (P&L by service type, return margin callout, projection) · Driver margin · Analytics · Rate cards

## Streamlit Cloud (two apps, one repo)

Use **Python 3.12** (`runtime.txt`). In App settings → Python version → select **3.12** (not 3.14).

1. **App A — Courier**  
   - Branch: `main`  
   - Main file: `app.py`

2. **App B — Fleet**  
   - Branch: `feat/management-fleet-view`  
   - Main file: `app_management.py`

Keep UI tokens in `movix_dispatcher/brand.py` so both apps stay visually aligned.

## Config

- Courier: [`config_movix.json`](config_movix.json)  
- Fleet / SPX: [`config_management.json`](config_management.json)  
- Rate matrix: [`RATES.md`](RATES.md)

## Tests

```bash
PYTHONPATH=. pytest tests -q
```

## Layout

```
movix_dispatcher/     # Courier payout app + shared brand/ingest/projections
movix_management/     # Fleet SPX revenue + margin app
app.py                # Courier entrypoint
app_management.py     # Fleet entrypoint
config_movix.json
config_management.json
RATES.md
runtime.txt           # python-3.12
assets/
tests/
```
