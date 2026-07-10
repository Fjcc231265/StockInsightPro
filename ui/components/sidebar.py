"""Sidebar navigation: main sections and contextual submenus."""

from __future__ import annotations

from typing import Optional, Tuple

import streamlit as st

from services.market_data_service import get_available_tickers, get_market_data_status, load_favorite_symbols
from services.settings_service import load_user_settings
from utils.branding import LOGO_SIDEBAR, logo_as_base64, logo_exists
from utils.constants import APP_NAME, DEFAULT_TICKER, MAIN_SECTIONS, SUBMENUS
from utils.helpers import normalize_ticker


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
    _apply_education_nav_pending()

    defaults = {
        "main_section": "Home Dashboard",
        "submenu": None,
        "selected_ticker": DEFAULT_TICKER,
        "custom_ticker": "",
        "watchlist": load_favorite_symbols(),
        "user_settings": load_user_settings(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "main_nav_radio" not in st.session_state:
        st.session_state.main_nav_radio = st.session_state.main_section

    if "custom_ticker_input" not in st.session_state:
        st.session_state.custom_ticker_input = st.session_state.custom_ticker

    if "sidebar_ticker" not in st.session_state:
        st.session_state.sidebar_ticker = st.session_state.selected_ticker

    main_section = st.session_state.main_nav_radio
    if main_section in SUBMENUS:
        submenu_key = _submenu_widget_key(main_section)
        if submenu_key not in st.session_state:
            current_submenu = st.session_state.submenu
            st.session_state[submenu_key] = (
                current_submenu
                if current_submenu in SUBMENUS[main_section]
                else SUBMENUS[main_section][0]
            )
        st.session_state.submenu = st.session_state[submenu_key]


def _submenu_widget_key(main_section: str) -> str:
    """Return the session-state key for a section's submenu radio."""
    return f"submenu_{main_section}"


def _on_main_section_change() -> None:
    """Keep section/submenu session state aligned when the main menu changes."""
    section = st.session_state.main_nav_radio
    st.session_state.main_section = section
    if section in SUBMENUS:
        submenu_key = _submenu_widget_key(section)
        if submenu_key not in st.session_state:
            st.session_state[submenu_key] = SUBMENUS[section][0]
        st.session_state.submenu = st.session_state[submenu_key]
    else:
        st.session_state.submenu = None


def _on_submenu_change(main_section: str) -> None:
    """Persist the active submenu for the current main section."""
    st.session_state.submenu = st.session_state[_submenu_widget_key(main_section)]


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

        symbol_container = st.container()
        st.divider()
        st.markdown("**Navigation**")

        st.radio(
            "Main menu",
            options=MAIN_SECTIONS,
            label_visibility="collapsed",
            key="main_nav_radio",
            on_change=_on_main_section_change,
        )
        main_section = st.session_state.main_nav_radio
        st.session_state.main_section = main_section

        submenu = None
        if main_section in SUBMENUS:
            st.divider()
            st.markdown("**Submenu**")
            submenu_options = SUBMENUS[main_section]
            submenu_key = _submenu_widget_key(main_section)
            if submenu_key not in st.session_state:
                st.session_state[submenu_key] = submenu_options[0]
            st.radio(
                "Submenu",
                options=submenu_options,
                label_visibility="collapsed",
                key=submenu_key,
                on_change=_on_submenu_change,
                args=(main_section,),
            )
            submenu = st.session_state[submenu_key]
            st.session_state.submenu = submenu

        with symbol_container:
            _render_symbol_selector(available_tickers, main_section)

        st.divider()
        st.caption("v0.1 — UI Preview")
        st.caption("Developed by Sequence Consulting")
        st.caption(f"Market data: {get_market_data_status()}")

    return main_section, submenu


def _render_symbol_selector(available_tickers: list[str], main_section: str) -> None:
    """Render custom ticker input and context-specific suggested symbols."""
    st.markdown("**Symbol**")
    st.text_input(
        "Custom symbol",
        placeholder="e.g. DCTH, PLTR, SMCI",
        key="custom_ticker_input",
        label_visibility="collapsed",
    )
    custom_symbol = normalize_ticker(st.session_state.custom_ticker_input)

    if custom_symbol:
        st.session_state.selected_ticker = custom_symbol
        st.session_state.custom_ticker = custom_symbol
    else:
        st.session_state.custom_ticker = ""
        if main_section == "Home Dashboard":
            if st.session_state.sidebar_ticker not in available_tickers:
                st.session_state.sidebar_ticker = (
                    st.session_state.selected_ticker
                    if st.session_state.selected_ticker in available_tickers
                    else available_tickers[0]
                )
            st.selectbox(
                "Suggested symbols",
                options=available_tickers,
                key="sidebar_ticker",
                label_visibility="collapsed",
            )
            st.session_state.selected_ticker = st.session_state.sidebar_ticker

        st.caption(f"Active: **{st.session_state.selected_ticker}**")
    if main_section != "Home Dashboard" and not custom_symbol:
        st.caption("Suggested symbols are available on the Home Dashboard.")


def _apply_education_nav_pending() -> None:
    """Apply deferred Education submenu navigation before sidebar widgets mount."""
    nav_pending = st.session_state.pop("education_nav_pending", None)
    if not isinstance(nav_pending, dict):
        return

    st.session_state.main_section = "Education"
    st.session_state.main_nav_radio = "Education"
    submenu = nav_pending.get("submenu")
    if submenu and submenu in SUBMENUS.get("Education", []):
        submenu_key = _submenu_widget_key("Education")
        st.session_state[submenu_key] = submenu
        st.session_state.submenu = submenu
