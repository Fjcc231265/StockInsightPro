"""Portfolio Watchlist page."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from ui.components.charts import comparison_bar_chart
from ui.components.page_router import render_submenu_page
from services.market_data_service import (
    add_favorite_symbol,
    get_available_tickers,
    get_quote_summary,
    save_favorite_symbols,
    validate_symbol,
)
from utils.helpers import format_large_number
from utils.helpers import normalize_ticker


def render(submenu: str) -> None:
    """Route portfolio watchlist submenu."""
    handlers = {
        "Add ticker": _add_ticker,
        "Track favorites": _track_favorites,
        "Compare stocks": _compare_stocks,
    }
    render_submenu_page(
        "Portfolio Watchlist",
        submenu,
        handlers,
        default_handler=_track_favorites,
        subtitle="Manage favorites and compare selected symbols.",
    )


def _add_ticker() -> None:
    """Add ticker to watchlist form with Alpha Vantage validation."""
    st.markdown("**Add Symbol to Watchlist**")
    proposed_symbol = normalize_ticker(
        st.text_input(
            "Ticker symbol",
            placeholder="e.g. PLTR, SMCI, DCTH",
            key="add_ticker_symbol",
        )
    )
    persist = st.checkbox("Save favorites to disk", value=True, key="persist_added_ticker")

    if st.button("Validate and Add to Watchlist", type="primary"):
        validation = validate_symbol(proposed_symbol)
        if not validation["valid"]:
            st.error(validation["message"])
            return
        symbol = validation["symbol"]
        if symbol in st.session_state.watchlist:
            st.info(f"{symbol} is already in your favorites.")
            return
        st.session_state.watchlist = add_favorite_symbol(symbol, st.session_state.watchlist, persist=persist)
        st.session_state.selected_ticker = symbol
        st.success(f"{validation['message']} Added {symbol} to favorites.")
        if persist:
            st.caption("Saved to disk and available next session.")
        else:
            st.caption("Added for this session only.")

    if st.session_state.watchlist:
        st.caption(f"Current favorites: {', '.join(st.session_state.watchlist)}")


def _track_favorites() -> None:
    """Display current watchlist."""
    rows = []
    for t in st.session_state.watchlist:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": round(q["price"], 2),
                "Change %": round(q["change_pct"], 2),
                "Sector": q["sector"],
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    remove = st.multiselect(
        "Remove tickers",
        options=st.session_state.watchlist,
        help="Select one or more favorites, then remove them all at once.",
    )
    persist = st.checkbox("Save removal to disk", value=True, key="persist_removed_ticker")
    if st.button("Remove Selected", disabled=not remove):
        removed = set(remove)
        remaining = [symbol for symbol in st.session_state.watchlist if symbol not in removed]
        st.session_state.watchlist = save_favorite_symbols(remaining) if persist else remaining
        if st.session_state.selected_ticker in removed and st.session_state.watchlist:
            st.session_state.selected_ticker = st.session_state.watchlist[0]
        elif st.session_state.selected_ticker in removed:
            st.session_state.selected_ticker = ""
        st.success(f"Removed {len(remove)} symbols from favorites: {', '.join(remove)}.")
        st.rerun()

    if st.button("Save Current Favorites to Disk"):
        st.session_state.watchlist = save_favorite_symbols(st.session_state.watchlist)
        st.success("Favorites saved to disk.")


def _compare_stocks() -> None:
    """Side-by-side stock comparison."""
    comparison_options = list(dict.fromkeys([*st.session_state.watchlist, *get_available_tickers()]))
    selected = st.multiselect(
        "Select tickers to compare",
        options=comparison_options,
        default=st.session_state.watchlist[:3],
        max_selections=5,
    )
    if not selected:
        st.warning("Select at least one ticker.")
        return

    rows = []
    for t in selected:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": round(q["price"], 2),
                "Change %": round(q["change_pct"], 2),
                "Volume": format_large_number(q["volume"]),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.plotly_chart(comparison_bar_chart(df, "Change %"), use_container_width=True)
