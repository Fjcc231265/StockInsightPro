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
from services.news_data_service import get_news_items
from utils.helpers import format_large_number, format_percent


def render() -> None:
    """Render executive home dashboard."""
    st.markdown("#### Executive Overview")
    st.caption(f"Market snapshot and key metrics — source: {get_market_data_status()}")

    # Market indices row
    overview = get_market_overview()
    cols = st.columns(len(overview))
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
    elif overview.attrs.get("source"):
        st.caption(f"Index source: {overview.attrs['source']}")

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

    _render_company_overview(quote)
    _render_recent_news(ticker)

    prices = get_price_history(ticker)
    st.plotly_chart(price_line_chart(prices, ticker), use_container_width=True)


def _render_company_overview(quote: dict) -> None:
    """Render company profile details above the chart."""
    st.markdown("**Company Overview**")
    overview_cols = st.columns(4)
    with overview_cols[0]:
        st.caption("Exchange")
        st.write(f"**{quote.get('exchange', 'Unknown')}**")
    with overview_cols[1]:
        st.caption("Industry")
        st.write(f"**{quote.get('industry', 'Unknown')}**")
    with overview_cols[2]:
        st.caption("P/E")
        st.write(f"**{_format_optional_number(quote.get('pe_ratio'))}**")
    with overview_cols[3]:
        st.caption("Beta")
        st.write(f"**{_format_optional_number(quote.get('beta'))}**")

    extra_cols = st.columns(4)
    with extra_cols[0]:
        st.caption("52W High")
        st.write(f"**{_format_optional_currency(quote.get('52_week_high'))}**")
    with extra_cols[1]:
        st.caption("52W Low")
        st.write(f"**{_format_optional_currency(quote.get('52_week_low'))}**")
    with extra_cols[2]:
        st.caption("Dividend Yield")
        st.write(f"**{_format_optional_ratio_percent(quote.get('dividend_yield'))}**")
    with extra_cols[3]:
        st.caption("Profit Margin")
        st.write(f"**{_format_optional_ratio_percent(quote.get('profit_margin'))}**")

    st.write(quote.get("description", "No company description available."))


def _render_recent_news(ticker: str) -> None:
    """Render recent news with color-coded sentiment badges."""
    if not st.toggle("Show recent news", value=False, key=f"home_recent_news_{ticker}"):
        return

    news = get_news_items(ticker, limit=6)
    st.caption(f"News source: {news.attrs.get('source', 'Unknown')}")
    for _, row in news.iterrows():
        sentiment = row.get("Sentiment", "Neutral")
        badge_color = _sentiment_color(sentiment)
        headline = row.get("Headline", "Untitled")
        url = row.get("URL", "")
        headline_html = f'<a href="{url}" target="_blank">{headline}</a>' if url else headline
        st.markdown(
            f"""
            <div style="border:1px solid #d8dee6;border-radius:8px;padding:8px 10px;margin-bottom:8px;background:#ffffff;">
                <span style="display:inline-block;background:{badge_color};color:white;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:700;">
                    {sentiment}
                </span>
                <span style="font-size:12px;color:#6b7c93;margin-left:8px;">
                    {row.get('Published', row.get('Date', 'Unknown'))} · {row.get('Source', 'Unknown')}
                </span>
                <div style="margin-top:6px;font-weight:600;">{headline_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _sentiment_color(sentiment: str) -> str:
    """Return badge color for normalized sentiment."""
    if sentiment == "Positive":
        return "#1a7f4e"
    if sentiment == "Negative":
        return "#c0392b"
    return "#c9a227"


def _format_optional_number(value: object) -> str:
    """Format optional numeric values."""
    return "-" if value is None else f"{float(value):.2f}"


def _format_optional_currency(value: object) -> str:
    """Format optional currency values."""
    return "-" if value is None else f"${float(value):.2f}"


def _format_optional_ratio_percent(value: object) -> str:
    """Format optional ratio values from Alpha Vantage as percentages."""
    return "-" if value is None else f"{float(value) * 100:.2f}%"


def _render_movers_panel() -> None:
    """Top movers table."""
    movers = get_top_movers_by_direction(limit=10)
    st.caption(f"Source: {movers['source']} · Last updated: {movers['last_updated']}")
    if movers.get("source", "").startswith("Mock") and movers.get("error"):
        st.warning(f"Live top movers unavailable: {movers['error']}")
    elif movers.get("warning"):
        st.warning(f"Using cached top movers because live refresh failed: {movers['warning']}")

    st.markdown("**Top 10 Gainers**")
    st.dataframe(movers["gainers"], use_container_width=True, hide_index=True)

    st.markdown("**Top 10 Losers**")
    st.dataframe(movers["losers"], use_container_width=True, hide_index=True)
