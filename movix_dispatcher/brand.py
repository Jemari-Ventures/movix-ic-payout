"""Movix Logistics brand tokens from the Movix Express recruitment poster."""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Sampled from Movix Express recruitment poster
PURPLE = "#2C1760"
PURPLE_DEEP = "#230E55"
PURPLE_MID = "#41227E"
PURPLE_LIGHT = "#553299"
YELLOW = "#FED504"
YELLOW_SOFT = "#FFF6C2"
SOFT_LAVENDER = "#F3F2F6"
SOFT_PURPLE = "#EDEAF5"
INK = "#1A1228"
MUTED = "#5B5670"
LINE = "#D8D4E4"
SURFACE = "#FFFFFF"
BACKGROUND = "#F7F6FA"
DANGER = "#B91C1C"

# Back-compat aliases used by older chart/invoice references
NAVY = PURPLE
NAVY_DEEP = PURPLE_DEEP
TEAL = PURPLE_MID
BLUE = PURPLE_LIGHT
SOFT_TEAL = SOFT_PURPLE
SOFT_BLUE = SOFT_LAVENDER
SOFT_CREAM = YELLOW_SOFT

COMPANY_NAME = "Movix Logistics (M) Sdn. Bhd"
COMPANY_SHORT = "Movix Logistics"
HUB_NAME = "OS Karangan (OKAR)"
FACEBOOK_URL = "https://www.facebook.com/p/Movix-Logistics-Sdn-Bhd-61596114287063/"

LOGO_SVG = ASSETS_DIR / "movix-logo.svg"
LOGO_MARK_SVG = ASSETS_DIR / "movix-logo-mark.svg"
LOGO_PNG = ASSETS_DIR / "movix-logo.png"
LOGO_MARK_PNG = ASSETS_DIR / "movix-logo-mark.png"


def streamlit_theme_css() -> str:
    """Custom Streamlit chrome aligned to the Movix Express poster."""
    return f"""
    <style>
      :root {{
        --movix-purple: {PURPLE};
        --movix-yellow: {YELLOW};
        --movix-lavender: {SOFT_LAVENDER};
      }}
      .stApp {{
        background:
          radial-gradient(circle at top right, {SOFT_PURPLE} 0%, transparent 45%),
          linear-gradient(180deg, {SOFT_LAVENDER} 0%, {BACKGROUND} 40%, {BACKGROUND} 100%);
      }}
      [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {PURPLE} 0%, {PURPLE_DEEP} 100%);
      }}
      [data-testid="stSidebar"] * {{
        color: #F8FAFC !important;
      }}
      [data-testid="stSidebar"] .stMarkdown strong {{
        color: {YELLOW} !important;
      }}
      [data-testid="stSidebar"] div[data-testid="stDataFrame"] * {{
        color: {INK} !important;
      }}
      h1, h2, h3 {{
        color: {PURPLE} !important;
        letter-spacing: -0.02em;
      }}
      div[data-testid="stMetricValue"] {{
        color: {PURPLE} !important;
      }}
      .stButton > button[kind="primary"],
      .stButton > button[data-testid="baseButton-primary"] {{
        background: {PURPLE};
        border-color: {PURPLE};
        color: white;
      }}
      .stButton > button[kind="primary"]:hover {{
        background: {PURPLE_MID};
        border-color: {PURPLE_MID};
      }}
      .stTabs [aria-selected="true"] {{
        color: {PURPLE} !important;
        border-bottom-color: {YELLOW} !important;
        font-weight: 700;
      }}
      .movix-hero {{
        display: flex;
        align-items: center;
        gap: 18px;
        margin: 0 0 10px 0;
        padding: 14px 16px;
        border: 1px solid {LINE};
        border-radius: 16px;
        background: linear-gradient(90deg, {SURFACE} 0%, {SOFT_LAVENDER} 100%);
      }}
      .movix-hero img {{
        height: 56px;
        width: auto;
      }}
      .movix-hero .copy h1 {{
        margin: 0 !important;
        font-size: 1.75rem !important;
        color: {PURPLE} !important;
      }}
      .movix-hero .copy p {{
        margin: 4px 0 0 0;
        color: {MUTED};
      }}
      .movix-hero .badge {{
        margin-left: auto;
        background: {YELLOW};
        color: {PURPLE};
        font-weight: 800;
        font-size: 12px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border-radius: 999px;
        padding: 8px 12px;
      }}
    </style>
    """


def logo_data_uri(mark: bool = False, prefer_png: bool = True) -> str:
    import base64

    if prefer_png:
        path = LOGO_MARK_PNG if mark else LOGO_PNG
        if path.exists():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"

    path = LOGO_MARK_SVG if mark else LOGO_SVG
    encoded = base64.b64encode(path.read_text(encoding="utf-8").encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
