"""Load SPX partner / management rate-card configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config_management.json"


@dataclass(frozen=True)
class SpxWeightBand:
    min_kg: float
    max_kg: Optional[float]
    label: str
    door_to_door: float
    drop_off: float

    def contains(self, weight_kg: float) -> bool:
        if weight_kg < self.min_kg:
            return False
        if self.max_kg is None:
            return True
        return weight_kg <= self.max_kg


@dataclass(frozen=True)
class ServiceTypeRate:
    match: str
    mode: str  # spx_door_to_door | spx_drop_off | flat
    rate: Optional[float] = None
    label: str = ""


@dataclass(frozen=True)
class ManagementConfig:
    currency_symbol: str = "RM"
    sheet_name: str = "Sheet1"
    billable_service_prefixes: tuple = ("Del - FWD", "PU - RR", "Del - RTS")
    service_type_rates: tuple = ()
    default_channel: str = "door_to_door"
    spx_weight_rates: tuple = ()
    lm_type_labels: Dict[str, str] = field(default_factory=dict)
    notes: tuple = ()
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManagementConfig":
        bands = tuple(
            SpxWeightBand(
                min_kg=float(band["min_kg"]),
                max_kg=None if band.get("max_kg") is None else float(band["max_kg"]),
                label=str(band.get("label") or ""),
                door_to_door=float(band["door_to_door"]),
                drop_off=float(band["drop_off"]),
            )
            for band in data.get("spx_weight_rates", [])
        )
        service_rates = tuple(
            ServiceTypeRate(
                match=str(rule["match"]),
                mode=str(rule.get("mode") or "flat"),
                rate=None if rule.get("rate") is None else float(rule["rate"]),
                label=str(rule.get("label") or rule["match"]),
            )
            for rule in data.get("service_type_rates", [])
        )
        return cls(
            currency_symbol=str(data.get("currency_symbol", "RM")),
            sheet_name=str(data.get("sheet_name", "Sheet1")),
            billable_service_prefixes=tuple(
                data.get("billable_service_prefixes")
                or ["Del - FWD", "PU - RR", "Del - RTS"]
            ),
            service_type_rates=service_rates,
            default_channel=str(data.get("default_channel", "door_to_door")),
            spx_weight_rates=bands,
            lm_type_labels={
                str(k).upper(): str(v)
                for k, v in (data.get("lm_type_labels") or {}).items()
            },
            notes=tuple(data.get("notes") or []),
            raw=data,
        )

    @classmethod
    def load(cls, path: Optional[Path | str] = None) -> "ManagementConfig":
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        with config_path.open(encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def find_service_rule(self, service_type: object) -> Optional[ServiceTypeRate]:
        text = str(service_type or "").strip()
        for rule in self.service_type_rates:
            if text == rule.match or text.startswith(rule.match):
                return rule
        return None

    def rate_table_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for rule in self.service_type_rates:
            if rule.mode == "flat":
                rows.append(
                    {
                        "Service": rule.match,
                        "Rule": rule.label,
                        "Rate (RM)": f"{0.0 if rule.rate is None else rule.rate:g}",
                    }
                )
            elif rule.mode == "spx_door_to_door":
                rows.append(
                    {
                        "Service": rule.match,
                        "Rule": rule.label,
                        "Rate (RM)": "SPX door-to-door by weight",
                    }
                )
            else:
                rows.append(
                    {
                        "Service": rule.match,
                        "Rule": rule.label,
                        "Rate (RM)": rule.mode,
                    }
                )
        for band in self.spx_weight_rates:
            rows.append(
                {
                    "Service": "SPX weight card",
                    "Rule": band.label,
                    "Rate (RM)": f"D2D {band.door_to_door} / drop-off {band.drop_off}",
                }
            )
        return rows
