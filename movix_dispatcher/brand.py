"""Movix Logistics brand tokens from the OKAR courier incentive poster."""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Poster palette (sampled from Movix_Courier_Payment_Incentive_Poster_A4)
NAVY = "#12304A"
NAVY_DEEP = "#0A2944"
TEAL = "#16A085"
BLUE = "#1476B7"
YELLOW = "#F5C518"
SOFT_TEAL = "#EAF4EC"
SOFT_BLUE = "#EAF2FB"
SOFT_CREAM = "#FFF3DF"
INK = "#12304A"
MUTED = "#54697C"
LINE = "#D7E0E8"
SURFACE = "#FFFFFF"
BACKGROUND = "#F5F7FA"
DANGER = "#B91C1C"

COMPANY_NAME = "Movix Logistics"
HUB_NAME = "OS Karangan (OKAR)"
FACEBOOK_URL = "https://www.facebook.com/p/Movix-Logistics-Sdn-Bhd-61596114287063/"

LOGO_SVG = ASSETS_DIR / "movix-logo.svg"
LOGO_MARK_SVG = ASSETS_DIR / "movix-logo-mark.svg"
LOGO_PNG = ASSETS_DIR / "movix-logo.png"
LOGO_MARK_PNG = ASSETS_DIR / "movix-logo-mark.png"


def streamlit_theme_css() -> str:
    """Custom Streamlit chrome aligned to the poster."""
    return f"""
    <style>
      :root {{
        --movix-navy: {NAVY};
        --movix-teal: {TEAL};
        --movix-blue: {BLUE};
        --movix-yellow: {YELLOW};
      }}
      .stApp {{
        background:
          radial-gradient(circle at top right, {SOFT_BLUE} 0%, transparent 42%),
          linear-gradient(180deg, {SOFT_TEAL} 0%, {BACKGROUND} 36%, {BACKGROUND} 100%);
      }}
      [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {NAVY} 0%, {NAVY_DEEP} 100%);
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
        color: {NAVY} !important;
        letter-spacing: -0.02em;
      }}
      div[data-testid="stMetricValue"] {{
        color: {NAVY} !important;
      }}
      .stButton > button[kind="primary"],
      .stButton > button[data-testid="baseButton-primary"] {{
        background: {TEAL};
        border-color: {TEAL};
        color: white;
      }}
      .stButton > button[kind="primary"]:hover {{
        background: #12856f;
        border-color: #12856f;
      }}
      .stTabs [aria-selected="true"] {{
        color: {NAVY} !important;
        border-bottom-color: {TEAL} !important;
        font-weight: 700;
      }}
      .movix-hero {{
        display: flex;
        align-items: center;
        gap: 18px;
        margin: 0 0 8px 0;
      }}
      .movix-hero img {{
        height: 56px;
        width: auto;
      }}
      .movix-hero .copy h1 {{
        margin: 0 !important;
        font-size: 1.8rem !important;
      }}
      .movix-hero .copy p {{
        margin: 4px 0 0 0;
        color: {MUTED};
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
