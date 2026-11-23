# OKAR rate matrix (source of truth)

Edit amounts in JSON only — do not hardcode rates in UI code.

| Service | Courier (`config_movix.json`) | Management (`config_management.json`) |
|---------|-------------------------------|----------------------------------------|
| **Del - FWD D2D** | Weight tier RM1 / RM1.80 / RM3 | SPX door-to-door by weight |
| **Del - FWD BSC** | RM0.10 flat (buyer self collect) | RM0.10 flat |
| **PU - RR D2D** | RM0.70 flat (return) | SPX door-to-door by weight |
| **Del - RTS** | RM0.70 flat (return) | SPX door-to-door by weight |
| **Failed Deliveries** | RM0 audit | RM0 audit |

## Courier extras (poster)

| Component | Rule |
|-----------|------|
| Basic | RM1,700 if ≥26 days **and** avg ≥50 parcels/day |
| Attendance | RM200 same gate; MC −RM100/day; ≥2 MC → no allowance |
| Absent | −RM30/day |

Volume gate (`volume_gate_service_prefixes`) counts **Del - FWD D2D only**.
BSC, returns, and Failed still earn commission (or RM0 audit) but do **not** inflate the ≥50/day average.

## Deploy

| App | Branch | Entrypoint | Python |
|-----|--------|------------|--------|
| Courier | `main` | `app.py` | **3.12** (`runtime.txt`) |
| Fleet | `feat/management-fleet-view` | `app_management.py` | **3.12** |

In Streamlit Cloud → App settings → Python version → select **3.12** (do not leave on 3.14).
