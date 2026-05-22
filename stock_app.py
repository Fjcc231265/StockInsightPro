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

from components.layout import render_app_header
from components.sidebar import render_sidebar
from components.styles import get_custom_css
from pages import home, technical, fundamental, news, portfolio, reports
from pages import settings_page
from utils.branding import LOGO_SIDEBAR
from utils.constants import APP_NAME, MAIN_SECTIONS

# Browser tab icon: use logo when available
_page_icon = str(LOGO_SIDEBAR) if LOGO_SIDEBAR.exists() else "📈"

# ── Page configuration (must be first Streamlit command) ──────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global styling ────────────────────────────────────────────────────────────
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ── Sidebar navigation ────────────────────────────────────────────────────────
main_section, submenu = render_sidebar()

# ── Main content router ─────────────────────────────────────────────────────────
section_titles = {
    "Home Dashboard": "Home Dashboard",
    "Technical Analysis": "Technical Analysis",
    "Fundamental Analysis": "Fundamental Analysis",
    "News & Sentiment": "News & Sentiment",
    "Portfolio Watchlist": "Portfolio Watchlist",
    "Reports": "Reports",
    "Settings": "Settings",
}

render_app_header(section_titles.get(main_section, APP_NAME))

# Route to the appropriate page module based on sidebar selection
if main_section == "Home Dashboard":
    home.render()
elif main_section == "Technical Analysis":
    technical.render(submenu)
elif main_section == "Fundamental Analysis":
    fundamental.render(submenu)
elif main_section == "News & Sentiment":
    news.render(submenu)
elif main_section == "Portfolio Watchlist":
    portfolio.render(submenu)
elif main_section == "Reports":
    reports.render(submenu)
elif main_section == "Settings":
    settings_page.render(submenu)
else:
    st.error("Unknown section. Please select a menu item from the sidebar.")

# ── Footer ──────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"{APP_NAME} v0.1 · Mock data only · Not financial advice · "
    f"Active: {main_section}" + (f" → {submenu}" if submenu else "")
)
