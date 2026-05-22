"""Portfolio Watchlist page."""

import streamlit as st
import pandas as pd

from components.cards import render_section_header, render_todo_callout
from components.charts import comparison_bar_chart
from data.mock_data import AVAILABLE_TICKERS, get_quote_summary, get_watchlist


def render(submenu: str) -> None:
    """Route portfolio watchlist submenu."""
    render_section_header("Portfolio Watchlist", f"View: {submenu}")
    st.divider()

    handlers = {
        "Add ticker": _add_ticker,
        "Track favorites": _track_favorites,
        "Alerts placeholder": _alerts,
        "Compare stocks": _compare_stocks,
    }
    handlers.get(submenu, _track_favorites)()


def _add_ticker() -> None:
    """Add ticker to watchlist form."""
    st.markdown("**Add Symbol to Watchlist**")
    new_ticker = st.selectbox(
        "Select ticker",
        options=[t for t in AVAILABLE_TICKERS if t not in st.session_state.watchlist],
        key="add_ticker_select",
    )
    if st.button("Add to Watchlist", type="primary"):
        if new_ticker and new_ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_ticker)
            st.success(f"Added {new_ticker} to watchlist (session only).")
        # TODO: Persist watchlist to database / file
    render_todo_callout("Persist watchlist and support custom ticker validation.")


def _track_favorites() -> None:
    """Display current watchlist."""
    rows = []
    for t in st.session_state.watchlist:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": q["price"],
                "Change %": q["change_pct"],
                "Sector": q["sector"],
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    remove = st.selectbox("Remove ticker", options=["—"] + st.session_state.watchlist)
    if st.button("Remove Selected") and remove != "—":
        st.session_state.watchlist.remove(remove)
        st.rerun()
    render_todo_callout("Add drag-and-drop sorting and portfolio grouping.")


def _alerts() -> None:
    """Price alerts placeholder UI."""
    st.markdown("**Price Alerts (Placeholder)**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Ticker", st.session_state.watchlist, key="alert_ticker")
    with col2:
        st.selectbox("Condition", ["Above", "Below", "Change %"], key="alert_cond")
    with col3:
        st.number_input("Target value", value=100.0, key="alert_value")
    if st.button("Create Alert (Mock)"):
        st.info("Alert saved locally — not active. TODO: Enable notification delivery.")
    render_todo_callout("Implement alert engine with email/push notifications.")


def _compare_stocks() -> None:
    """Side-by-side stock comparison."""
    selected = st.multiselect(
        "Select tickers to compare",
        options=AVAILABLE_TICKERS,
        default=st.session_state.watchlist[:3],
        max_selections=5,
    )
    if not selected:
        st.warning("Select at least one ticker.")
        return

    rows = []
    for t in selected:
        q = get_quote_summary(t)
        rows.append({"Ticker": t, "Price": q["price"], "Change %": q["change_pct"], "Volume": q["volume"]})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.plotly_chart(comparison_bar_chart(df, "Change %"), use_container_width=True)
    render_todo_callout("Add multi-metric comparison and correlation matrix.")
