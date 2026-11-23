"""Load Movix IC rate-card configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config_movix.json"


@dataclass(frozen=True)
class WeightBand:
    min_kg: float
    max_kg: Optional[float]
    rate: float
    label: str

    def contains(self, weight_kg: float) -> bool:
        if weight_kg < self.min_kg:
            return False
        if self.max_kg is None:
            return True
        return weight_kg <= self.max_kg


@dataclass(frozen=True)
class ServiceTypeRate:
    match: str
    mode: str  # weight_commission | flat
    rate: Optional[float] = None
    label: str = ""


@dataclass(frozen=True)
class MovixConfig:
    currency_symbol: str = "RM"
    sheet_name: str = "Sheet1"
    billable_service_prefixes: tuple = ("Del - FWD", "PU - RR", "Del - RTS")
    service_type_rates: tuple = ()
    weight_commission: tuple = ()
    basic_amount: float = 1700.0
    basic_required_working_days: int = 26
    basic_min_avg_parcels_per_day: float = 50.0
    attendance_amount: float = 200.0
    attendance_required_working_days: int = 26
    attendance_min_avg_parcels_per_day: float = 50.0
    mc_deduction_per_day: float = 100.0
    mc_days_disqualify_at: int = 2
    absent_penalty_per_day: float = 30.0
    notes: tuple = ()
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MovixConfig":
        bands = tuple(
            WeightBand(
                min_kg=float(band["min_kg"]),
                max_kg=None if band.get("max_kg") is None else float(band["max_kg"]),
                rate=float(band["rate"]),
                label=str(band.get("label") or ""),
            )
            for band in data.get("weight_commission", [])
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
        basic = data.get("basic_salary", {}) or {}
        attendance = data.get("attendance_allowance", {}) or {}
        prefixes = tuple(
            data.get("billable_service_prefixes")
            or ["Del - FWD", "PU - RR", "Del - RTS"]
        )
        return cls(
            currency_symbol=str(data.get("currency_symbol", "RM")),
            sheet_name=str(data.get("sheet_name", "Sheet1")),
            billable_service_prefixes=prefixes,
            service_type_rates=service_rates,
            weight_commission=bands,
            basic_amount=float(basic.get("amount", 1700.0)),
            basic_required_working_days=int(basic.get("required_working_days", 26)),
            basic_min_avg_parcels_per_day=float(basic.get("min_avg_parcels_per_day", 50.0)),
            attendance_amount=float(attendance.get("amount", 200.0)),
            attendance_required_working_days=int(attendance.get("required_working_days", 26)),
            attendance_min_avg_parcels_per_day=float(
                attendance.get("min_avg_parcels_per_day", 50.0)
            ),
            mc_deduction_per_day=float(attendance.get("mc_deduction_per_day", 100.0)),
            mc_days_disqualify_at=int(attendance.get("mc_days_disqualify_at", 2)),
            absent_penalty_per_day=float(data.get("absent_penalty_per_day", 30.0)),
            notes=tuple(data.get("notes") or []),
            raw=data,
        )

    @classmethod
    def load(cls, path: Optional[Path | str] = None) -> "MovixConfig":
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
            else:
                rows.append(
                    {
                        "Service": rule.match,
                        "Rule": rule.label,
                        "Rate (RM)": "weight card",
                    }
                )
        for band in self.weight_commission:
            rows.append(
                {
                    "Service": "Del - FWD D2D weight",
                    "Rule": band.label or f"{band.min_kg} – {band.max_kg}",
                    "Rate (RM)": f"{band.rate:g}",
                }
            )
        return rows
