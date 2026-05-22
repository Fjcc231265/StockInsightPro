"""Reusable page routing helpers for menu section modules."""

from __future__ import annotations

from typing import Callable, Mapping, Optional

import streamlit as st

from ui.components.cards import render_quote_cards, render_section_header
from services.market_data_service import get_quote_summary

PageHandler = Callable[[], None]


def render_submenu_page(
    title: str,
    submenu: Optional[str],
    handlers: Mapping[str, PageHandler],
    default_handler: PageHandler,
    subtitle: Optional[str] = None,
) -> None:
    """Render a section header and dispatch the selected submenu."""
    selected_submenu = submenu or next(iter(handlers))
    render_section_header(title, subtitle or f"View: {selected_submenu}")
    st.divider()
    handlers.get(selected_submenu, default_handler)()


def render_ticker_submenu_page(
    title: str,
    submenu: Optional[str],
    handlers: Mapping[str, PageHandler],
    default_handler: PageHandler,
    show_quote_cards: bool = False,
) -> None:
    """Render a submenu page that depends on the active ticker."""
    ticker = st.session_state.selected_ticker
    selected_submenu = submenu or next(iter(handlers))
    render_section_header(title, f"View: {selected_submenu} · {ticker}")

    if show_quote_cards:
        render_quote_cards(get_quote_summary(ticker))

    st.divider()
    handlers.get(selected_submenu, default_handler)()
