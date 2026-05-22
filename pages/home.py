"""Home Dashboard page."""

import streamlit as st

from components.cards import render_metric_card, render_todo_callout
from components.charts import price_line_chart
from components.layout import render_panel
from data.mock_data import get_market_overview, get_price_history, get_quote_summary, get_top_movers


def render() -> None:
    """Render executive home dashboard."""
    st.markdown("#### Executive Overview")
    st.caption("Market snapshot and key metrics — placeholder data")

    # Market indices row
    overview = get_market_overview()
    cols = st.columns(5)
    for i, row in overview.iterrows():
        with cols[i]:
            render_metric_card(
                row["Index"],
                f"{row['Value']:,.2f}" if row["Index"] != "VIX" else f"{row['Value']:.2f}",
                delta=f"{row['Change %']:+.2f}%",
                delta_value=row["Change %"],
            )

    st.divider()

    ticker = st.session_state.selected_ticker
    quote = get_quote_summary(ticker)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        render_panel(f"Selected Symbol — {ticker}", lambda: _render_symbol_panel(ticker, quote))

    with col_right:
        render_panel("Top Movers", lambda: _render_movers_panel())

    render_todo_callout("Connect live market data feed and portfolio sync on home dashboard.")


def _render_symbol_panel(ticker: str, quote: dict) -> None:
    """Symbol detail and price chart."""
    st.write(f"**{quote['name']}** · {quote['sector']}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Price", f"${quote['price']:.2f}", f"{quote['change_pct']:+.2f}%")
    with c2:
        st.metric("Volume", f"{quote['volume']:,}")
    with c3:
        st.metric("Mkt Cap (B)", f"${quote['market_cap']:.1f}B")

    prices = get_price_history(ticker)
    st.plotly_chart(price_line_chart(prices, ticker), use_container_width=True)
    # TODO: Add watchlist quick-add and recent news teaser


def _render_movers_panel() -> None:
    """Top movers table."""
    movers = get_top_movers()
    st.dataframe(movers, use_container_width=True, hide_index=True)
