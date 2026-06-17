"""
StockInsightPro — Main Application Entry Point

Executive stock market analysis platform (UI shell only).
Run with: streamlit run stock_app.py

TODO: Add authentication, database layer, and API integrations.
"""

import sys
from pathlib import Path

# Ensure project root is on Python path for imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from ui.components.layout import render_app_header
from ui.components.sidebar import render_sidebar
from ui.components.styles import get_custom_css
from ui.pages import (
    education,
    fundamental,
    home,
    market_sector,
    news,
    options_intelligence,
    portfolio,
    reports,
    scan_trades,
    settings,
    technical,
)
from services.market_data_service import get_market_data_status
from services.settings_service import load_user_settings
from utils.branding import LOGO_SIDEBAR
from utils.config import load_dotenv_if_present
from utils.constants import APP_NAME

# Browser tab icon: use logo when available
_page_icon = str(LOGO_SIDEBAR) if LOGO_SIDEBAR.exists() else "📈"

load_dotenv_if_present()
_app_settings = load_user_settings()

# ── Page configuration (must be first Streamlit command) ──────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global styling ────────────────────────────────────────────────────────────
# Theme is resolved inside get_custom_css() from user settings (no positional arg for Streamlit reload safety).
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ── Sidebar navigation ────────────────────────────────────────────────────────
main_section, submenu = render_sidebar()

# ── Main content router ─────────────────────────────────────────────────────────
PAGE_REGISTRY = {
    "Home Dashboard": (home.render, False),
    "Market & Sector Analysis": (market_sector.render, True),
    "Technical Analysis": (technical.render, True),
    "Fundamental Analysis": (fundamental.render, True),
    "News & Sentiment": (news.render, True),
    "Options Intelligence": (options_intelligence.render, True),
    "Portfolio Watchlist": (portfolio.render, True),
    "Scan Trades": (scan_trades.render, True),
    "Reports": (reports.render, True),
    "Settings": (settings.render, True),
    "Education": (education.render, True),
}

render_app_header(main_section)

# Route to the appropriate page module based on sidebar selection
page_entry = PAGE_REGISTRY.get(main_section)
if page_entry:
    page_renderer, uses_submenu = page_entry
    loading_label = f"Loading {main_section}" + (f" → {submenu}" if submenu else "")
    with st.spinner(f"{loading_label}..."):
        page_renderer(submenu) if uses_submenu else page_renderer()
else:
    st.error("Unknown section. Please select a menu item from the sidebar.")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"{APP_NAME} v0.1 · Market data: {get_market_data_status()} · "
    f"Active: {main_section}" + (f" → {submenu}" if submenu else "")
)
st.caption(
    "Disclosure: This platform is provided for informational and educational purposes only and does not constitute "
    "financial, investment, tax, legal, or trading advice. Financial markets involve substantial risk, including the "
    "possible loss of principal. Users are solely responsible for their own investment decisions, due diligence, and "
    "risk management. StockInsightPro and its developer assume no responsibility or liability for any losses, damages, "
    "or decisions made based on the information displayed."
)
