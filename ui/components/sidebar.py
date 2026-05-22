"""Sidebar navigation: main sections and contextual submenus."""

from __future__ import annotations

from typing import Optional, Tuple

import streamlit as st

from services.market_data_service import get_available_tickers
from utils.branding import LOGO_SIDEBAR, logo_as_base64, logo_exists
from utils.constants import APP_NAME, DEFAULT_TICKER, MAIN_SECTIONS, SUBMENUS


def _render_sidebar_brand() -> None:
    """Sidebar brand block with larger icon and readable app name."""
    if logo_exists():
        logo_b64 = logo_as_base64(LOGO_SIDEBAR)
        st.markdown(
            f"""
            <div class="sip-sidebar-brand-row">
                <img src="data:image/png;base64,{logo_b64}"
                     alt="{APP_NAME}" class="sip-sidebar-logo" />
                <div class="sip-sidebar-brand">{APP_NAME}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="sip-sidebar-brand">{APP_NAME}</div>', unsafe_allow_html=True)


def init_session_state() -> None:
    """Initialize navigation and ticker session state."""
    defaults = {
        "main_section": "Home Dashboard",
        "submenu": None,
        "selected_ticker": DEFAULT_TICKER,
        "watchlist": ["AAPL", "MSFT", "NVDA", "GOOGL"],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> Tuple[str, Optional[str]]:
    """
    Render left sidebar with main menu and optional submenu.

    Returns:
        Tuple of (main_section, submenu_key or None)
    """
    init_session_state()
    available_tickers = get_available_tickers()

    with st.sidebar:
        _render_sidebar_brand()
        st.caption("Stock Market Analysis Platform")
        st.divider()

        # Global ticker selector (available on all pages)
        st.session_state.selected_ticker = st.selectbox(
            "Symbol",
            options=available_tickers,
            index=available_tickers.index(st.session_state.selected_ticker)
            if st.session_state.selected_ticker in available_tickers
            else 0,
            key="sidebar_ticker",
        )

        st.divider()
        st.markdown("**Navigation**")

        main_section = st.radio(
            "Main menu",
            options=MAIN_SECTIONS,
            index=MAIN_SECTIONS.index(st.session_state.main_section)
            if st.session_state.main_section in MAIN_SECTIONS
            else 0,
            label_visibility="collapsed",
            key="main_nav_radio",
        )
        st.session_state.main_section = main_section

        submenu = None
        if main_section in SUBMENUS:
            st.divider()
            st.markdown("**Submenu**")
            submenu_options = SUBMENUS[main_section]
            default_sub = st.session_state.submenu
            if default_sub not in submenu_options:
                default_sub = submenu_options[0]
            submenu = st.radio(
                "Submenu",
                options=submenu_options,
                index=submenu_options.index(default_sub),
                label_visibility="collapsed",
                key=f"submenu_{main_section}",
            )
            st.session_state.submenu = submenu

        st.divider()
        st.caption("v0.1 — UI Preview")
        st.caption("Mock data only")

    return main_section, submenu
