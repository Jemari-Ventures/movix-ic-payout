# Movix IC Payout

Standalone Streamlit calculator for **Movix Logistics Kulim Independent Contractor (IC)** courier payment.

Extracted from the legacy hub payout tools so this product has a clean repo, deploy path, and rate card.

## Rate card

| Component | Rule |
|-----------|------|
| Commission | `0–5.00 kg` → RM1.00 · `5.01–20.00 kg` → RM1.80 · `>20 kg` → RM3.00 per parcel |
| Basic salary | RM1,700 if ≥26 working days **and** avg ≥50 parcels/day |
| Attendance | RM200 with the same volume gate; MC deducts RM100/day; ≥2 MC days → no allowance |
| Absent | RM30/day unauthorized absence |
| Volume gate fail | Commission only (no basic, no attendance) |

Billable rows: service types starting with `Del - FWD` (D2D / BSC). Failed deliveries, RTS, and pickup rows are excluded.

## Input

Excel workbook, **Sheet1** only:

- Service Date
- Service Type
- LM Type (optional)
- Shipment ID
- Chargeable Weight
- Driver ID
- Driver Name
- TIER (optional)

## Setup

```bash
cd movix-ic-payout
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run movix_dispatcher/app.py
```

Upload the IC Payment `.xlsx` in the sidebar. Use **Batch payout** for all drivers or **Single driver** for detail + CSV export.

## Config

Rates live in [`config_movix.json`](config_movix.json). Change amounts / bands there without touching code.

## Tests

```bash
PYTHONPATH=. pytest tests -q
```

## Layout

```
movix_dispatcher/
  app.py           # Streamlit UI
  calculator.py    # Payout engine
  config.py        # Rate-card loader
  eligibility.py   # Basic + attendance gates
  ingest.py        # Sheet1 load / normalize
  rates.py         # Weight → commission
  schema.py        # Column contract
config_movix.json
requirements.txt
tests/
```
