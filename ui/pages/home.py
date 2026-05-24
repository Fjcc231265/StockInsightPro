"""Home Dashboard page."""

import streamlit as st

from ui.components.cards import render_metric_card, render_todo_callout
from ui.components.charts import price_line_chart
from ui.components.layout import render_panel
from services.market_data_service import (
    get_market_data_status,
    get_market_overview,
    get_price_history,
    get_quote_summary,
    get_top_movers_by_direction,
)
from utils.helpers import format_large_number, format_percent


def render() -> None:
    """Render executive home dashboard."""
    st.markdown("#### Executive Overview")
    st.caption(f"Market snapshot and key metrics — source: {get_market_data_status()}")

    # Market indices row
    overview = get_market_overview()
    cols = st.columns(5)
    for i, row in overview.iterrows():
        with cols[i]:
            render_metric_card(
                row["Index"],
                f"{row['Value']:,.2f}" if row["Index"] != "VIX" else f"{row['Value']:.2f}",
                delta=format_percent(row["Change %"]),
                delta_value=row["Change %"],
            )
    if "Source" in overview.columns:
        sources = ", ".join(sorted(overview["Source"].unique()))
        st.caption(f"Index source: {sources}")

    st.divider()

    ticker = st.session_state.selected_ticker
    quote = get_quote_summary(ticker)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        render_panel(f"Selected Symbol — {ticker}", lambda: _render_symbol_panel(ticker, quote))

    with col_right:
        render_panel("Top Movers", lambda: _render_movers_panel())

    render_todo_callout("Portfolio sync and intraday refresh controls will be added in a later phase.")


def _render_symbol_panel(ticker: str, quote: dict) -> None:
    """Symbol detail and price chart."""
    st.write(f"**{quote['name']}** · {quote['sector']}")
    st.caption(f"Price source: {quote.get('price_source', 'Unknown')} · Profile source: {quote.get('metadata_source', 'Unknown')}")
    if quote.get("price_source", "").startswith("Mock"):
        st.warning("Live quote unavailable right now. Showing mock fallback values for price/change/volume.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Price", f"${quote['price']:.2f}", format_percent(quote["change_pct"]))
    with c2:
        st.metric("Volume", format_large_number(quote["volume"]))
    with c3:
        st.metric("Mkt Cap (B)", f"${quote['market_cap']:.2f}B")

    prices = get_price_history(ticker)
    st.plotly_chart(price_line_chart(prices, ticker), use_container_width=True)
    # TODO: Add watchlist quick-add and recent news teaser


def _render_movers_panel() -> None:
    """Top movers table."""
    movers = get_top_movers_by_direction(limit=10)
    st.caption(f"Source: {movers['source']} · Last updated: {movers['last_updated']}")

    st.markdown("**Top 10 Gainers**")
    st.dataframe(movers["gainers"], use_container_width=True, hide_index=True)

    st.markdown("**Top 10 Losers**")
    st.dataframe(movers["losers"], use_container_width=True, hide_index=True)
