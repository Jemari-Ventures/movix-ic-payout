# Movix IC Payout

Standalone Streamlit apps for **Movix Logistics (M) Sdn. Bhd** — OS Karangan (OKAR).

Two deployable surfaces share this repo, brand, and Sheet1 contract:

| App | Branch (recommended) | Entrypoint | Audience |
|-----|----------------------|------------|----------|
| **OKAR Courier Payout** | `main` | `app.py` → `movix_dispatcher/app.py` | Couriers / payroll |
| **OKAR Fleet Management** | `feat/management-fleet-view` | `app_management.py` → `movix_management/app.py` | Hub / ops / finance |

Same purple/yellow Movix UI language; copy and KPIs tailored per role.

## Courier rate card (`config_movix.json`)

| Component | Rule |
|-----------|------|
| Commission | `0–5.00 kg` → RM1.00 · `5.01–20.00 kg` → RM1.80 · `>20 kg` → RM3.00 per parcel |
| Basic salary | RM1,700 if ≥26 working days **and** avg ≥50 parcels/day |
| Attendance | RM200 with the same volume gate; MC deducts RM100/day; ≥2 MC days → no allowance |
| Absent | RM30/day unauthorized absence |

Billable rows: service types starting with `Del - FWD` (D2D / BSC).

## SPX partner rate card (`config_management.json`)

Weight bands from the SPX partner slide (door-to-door / return pickup vs drop-off / return to SPX).

- **D2D** LM type → door-to-door rate  
- **BSC** LM type → drop-off rate  

Fleet margin = SPX revenue − OKAR courier net payout.

Rates are editable in JSON and noted as indicative / tax-inclusive / excluding incentives.

## Input

Excel workbook, **Sheet1** only:

- Service Date, Service Type, LM Type, Shipment ID, Chargeable Weight, Driver ID, Driver Name, TIER (optional)

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

Batch payout · Single driver · Analytics · Invoice

### Fleet tabs

Fleet overview (P&L) · Driver margin · Analytics · Rate cards

## Streamlit Cloud (two apps, one repo)

1. **App A — Courier**  
   - Repo: this repo  
   - Branch: `main`  
   - Main file: `app.py`

2. **App B — Fleet**  
   - Repo: same  
   - Branch: `feat/management-fleet-view` (or merge to a dedicated `deploy/management` branch)  
   - Main file: `app_management.py`

Keep UI tokens in `movix_dispatcher/brand.py` so both apps stay visually aligned.

## Config

- Courier: [`config_movix.json`](config_movix.json)  
- Fleet / SPX: [`config_management.json`](config_management.json)

## Tests

```bash
PYTHONPATH=. pytest tests -q
```

## Layout

```
movix_dispatcher/     # Courier payout app + shared brand/ingest
movix_management/     # Fleet SPX revenue + margin app
app.py                # Courier entrypoint
app_management.py     # Fleet entrypoint
config_movix.json
config_management.json
assets/
tests/
```
