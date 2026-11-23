"""Streamlit API helpers that work on both 1.37 (local) and newer Cloud builds."""

from __future__ import annotations

import inspect
from typing import Any, Dict

import pandas as pd
import streamlit as st


def width_kwargs(stretch: bool = True) -> Dict[str, Any]:
    """Prefer width=stretch/content on new Streamlit; fall back to use_container_width."""
    params = inspect.signature(st.dataframe).parameters
    if "width" in params:
        return {"width": "stretch" if stretch else "content"}
    return {"use_container_width": stretch}


def chart_width_kwargs(stretch: bool = True) -> Dict[str, Any]:
    params = inspect.signature(st.bar_chart).parameters
    if "width" in params:
        return {"width": "stretch" if stretch else "content"}
    return {"use_container_width": stretch}


def as_arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce object columns to string so PyArrow never sees mixed float/str cells."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(lambda v: "" if v is None else str(v))
    return out
