"""Display-name cleanup for Movix OKAR driver strings."""

from __future__ import annotations

import re

# SPX style: "[305572]OKAR - D - NAME"
_ID_PREFIX = re.compile(r"^\s*\[\d+\]\s*")
_OKAR_PREFIX = re.compile(r"^\s*OKAR\s*-\s*D\s*-\s*", re.IGNORECASE)


def clean_driver_name(name: object) -> str:
    """Strip SPX id brackets and the OKAR - D - hub prefix."""
    if name is None:
        return ""
    text = str(name).strip()
    if not text or text.lower() == "nan":
        return ""
    text = _ID_PREFIX.sub("", text)
    text = _OKAR_PREFIX.sub("", text)
    return text.strip(" -")
