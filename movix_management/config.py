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
class ManagementConfig:
    currency_symbol: str = "RM"
    sheet_name: str = "Sheet1"
    billable_service_prefixes: tuple = ("Del - FWD",)
    service_channel_map: Dict[str, str] = field(default_factory=dict)
    default_channel: str = "door_to_door"
    spx_weight_rates: tuple = ()
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
        return cls(
            currency_symbol=str(data.get("currency_symbol", "RM")),
            sheet_name=str(data.get("sheet_name", "Sheet1")),
            billable_service_prefixes=tuple(
                data.get("billable_service_prefixes") or ["Del - FWD"]
            ),
            service_channel_map={
                str(k).upper(): str(v)
                for k, v in (data.get("service_channel_map") or {}).items()
            },
            default_channel=str(data.get("default_channel", "door_to_door")),
            spx_weight_rates=bands,
            notes=tuple(data.get("notes") or []),
            raw=data,
        )

    @classmethod
    def load(cls, path: Optional[Path | str] = None) -> "ManagementConfig":
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        with config_path.open(encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def rate_table_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for band in self.spx_weight_rates:
            rows.append(
                {
                    "Weight band": band.label,
                    "Door-to-door / Return pickup (RM)": band.door_to_door,
                    "Drop-off / Return to SPX (RM)": band.drop_off,
                }
            )
        return rows
