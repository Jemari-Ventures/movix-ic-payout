"""Movix Logistics brand tokens from the official Movix Express logo."""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Sampled from official Movix Express logo tile
PURPLE = "#2E1B5A"
PURPLE_DEEP = "#27145E"
PURPLE_MID = "#3A2470"
PURPLE_LIGHT = "#4A2F88"
YELLOW = "#FFE000"
YELLOW_SOFT = "#FFF6C2"
SOFT_LAVENDER = "#F7F6FA"
SOFT_PURPLE = "#EFEBF8"
INK = "#1A1228"
MUTED = "#5B5670"
LINE = "#E4E0EE"
SURFACE = "#FFFFFF"
BACKGROUND = "#FFFFFF"
DANGER = "#B91C1C"

# Back-compat aliases
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
LOGO_HEADER_PNG = ASSETS_DIR / "movix-logo-header.png"
LOGO_OFFICIAL_PNG = ASSETS_DIR / "movix-logo-official.png"


def streamlit_theme_css() -> str:
    """Light theme: white app/sidebar, violet header band with yellow wordmark."""
    return f"""
    <style>
      :root {{
        --movix-purple: {PURPLE};
        --movix-yellow: {YELLOW};
        --movix-ink: {INK};
      }}
      html, body, .stApp {{
        background: {BACKGROUND} !important;
        color: {INK};
      }}
      [data-testid="stHeader"] {{
        background: {SURFACE} !important;
      }}
      [data-testid="stSidebar"] {{
        background: {SURFACE} !important;
        border-right: 1px solid {LINE};
      }}
      [data-testid="stSidebar"] * {{
        color: {INK} !important;
      }}
      [data-testid="stSidebar"] .stMarkdown strong {{
        color: {PURPLE} !important;
      }}
      [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3 {{
        color: {PURPLE} !important;
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
        margin: 0 0 14px 0;
        padding: 14px 18px;
        border-radius: 16px;
        background: linear-gradient(135deg, {PURPLE} 0%, {PURPLE_MID} 55%, {PURPLE_DEEP} 100%);
        box-shadow: 0 10px 24px rgba(46, 27, 90, 0.22);
      }}
      .movix-hero img {{
        height: 64px;
        width: auto;
        border-radius: 10px;
        background: transparent;
      }}
      .movix-hero .copy h1 {{
        margin: 0 !important;
        font-size: 1.75rem !important;
        color: {YELLOW} !important;
      }}
      .movix-hero .copy p {{
        margin: 4px 0 0 0;
        color: #FFFFFF !important;
        opacity: 0.92;
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


def logo_data_uri(mark: bool = False, prefer_png: bool = True, header: bool = False) -> str:
    import base64

    if prefer_png:
        if header and LOGO_HEADER_PNG.exists():
            path = LOGO_HEADER_PNG
        elif mark:
            path = LOGO_MARK_PNG
        else:
            path = LOGO_PNG if LOGO_PNG.exists() else LOGO_OFFICIAL_PNG
        if path.exists():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"

    path = LOGO_MARK_SVG if mark else LOGO_SVG
    encoded = base64.b64encode(path.read_text(encoding="utf-8").encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
