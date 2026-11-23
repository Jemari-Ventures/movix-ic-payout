"""Streamlit API helpers that work on both 1.37 (local) and newer Cloud builds."""

from __future__ import annotations

import inspect
from typing import Any, Dict

import pandas as pd
import streamlit as st


def width_kwargs(stretch: bool = True) -> Dict[str, Any]:
    """Prefer use_container_width on older Streamlit; width=stretch on newer Cloud."""
    params = inspect.signature(st.dataframe).parameters
    # Streamlit < ~1.49: width is int-only; use_container_width is the stretch API.
    if "use_container_width" in params:
        return {"use_container_width": stretch}
    return {"width": "stretch" if stretch else "content"}


def chart_width_kwargs(stretch: bool = True) -> Dict[str, Any]:
    params = inspect.signature(st.bar_chart).parameters
    if "use_container_width" in params:
        return {"use_container_width": stretch}
    return {"width": "stretch" if stretch else "content"}


def as_arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce object columns to string so PyArrow never sees mixed float/str cells."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda v: "" if v is None else str(v))
    return out
