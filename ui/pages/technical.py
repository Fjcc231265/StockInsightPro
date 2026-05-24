"""Technical Analysis page with submenu views."""

import streamlit as st

from ui.components.cards import render_todo_callout
from ui.components.charts import (
    macd_chart,
    price_line_chart,
    rsi_chart,
)
from ui.components.page_router import render_ticker_submenu_page
from services.market_data_service import get_price_history
from services.technical_data_service import (
    get_candlestick_patterns,
    get_macd_series,
    get_moving_averages_df,
    get_rsi_series,
    get_support_resistance,
    get_volume_analysis,
    get_written_technical_analysis,
)

TIMEFRAME_PERIODS = {
    "Daily": 180,
    "Weekly": 156,
    "Monthly": 120,
    "Hourly": 240,
}


def render(submenu: str) -> None:
    """Route technical analysis submenu to the appropriate view."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Price chart": lambda: _price_chart(ticker),
        "Moving averages": lambda: _moving_averages(ticker),
        "RSI": lambda: _rsi(ticker),
        "MACD": lambda: _macd(ticker),
        "Support and resistance": lambda: _support_resistance(ticker),
        "Volume analysis": lambda: _volume_analysis(ticker),
        "Candlestick patterns": lambda: _candlestick_patterns(ticker),
    }
    render_ticker_submenu_page(
        "Technical Analysis",
        submenu,
        handlers,
        default_handler=lambda: _price_chart(ticker),
        show_quote_cards=True,
    )


def _price_chart(ticker: str) -> None:
    """Price chart submenu."""
    _render_timeframe_price_chart(ticker, "price_chart")
    with st.expander("Written technical analysis", expanded=False):
        st.markdown(get_written_technical_analysis(ticker))
    render_todo_callout("Add drawing tools and saved chart layouts.")


def _moving_averages(ticker: str) -> None:
    """Moving averages table and chart overlay placeholder."""
    ma_df = get_moving_averages_df(ticker)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(ma_df, use_container_width=True, hide_index=True)
    with col2:
        _render_timeframe_price_chart(ticker, "moving_averages")
    render_todo_callout("Expand the moving average table with SMA 50/200 and EMA 12/26.")


def _rsi(ticker: str) -> None:
    """RSI indicator view."""
    rsi_df = get_rsi_series(ticker)
    st.plotly_chart(rsi_chart(rsi_df, ticker), use_container_width=True)
    latest = rsi_df["RSI"].iloc[-1]
    st.info(f"Latest RSI (mock): **{latest:.2f}** — Neutral zone placeholder.")
    render_todo_callout("Implement 14-period RSI with divergence detection.")


def _macd(ticker: str) -> None:
    """MACD indicator view."""
    macd_df = get_macd_series(ticker)
    st.plotly_chart(macd_chart(macd_df, ticker), use_container_width=True)
    render_todo_callout("Implement standard MACD (12, 26, 9) with crossover alerts.")


def _support_resistance(ticker: str) -> None:
    """Support and resistance levels table."""
    levels = get_support_resistance(ticker)
    st.dataframe(levels, use_container_width=True, hide_index=True)
    _render_timeframe_price_chart(ticker, "support_resistance")
    render_todo_callout("Auto-detect S/R from swing highs/lows and volume nodes.")


def _volume_analysis(ticker: str) -> None:
    """Volume analysis metrics and chart."""
    vol_stats = get_volume_analysis(ticker)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(vol_stats, use_container_width=True, hide_index=True)
    with col2:
        _render_timeframe_price_chart(ticker, "volume_analysis")
    render_todo_callout("Add OBV, VWAP, and relative volume indicators.")


def _candlestick_patterns(ticker: str) -> None:
    """Detected candlestick patterns table."""
    patterns = get_candlestick_patterns()
    st.dataframe(patterns, use_container_width=True, hide_index=True)
    _render_timeframe_price_chart(ticker, "candlestick_patterns")
    render_todo_callout("Build pattern recognition engine (engulfing, doji, stars, etc.).")


def _render_timeframe_price_chart(ticker: str, key_suffix: str) -> None:
    """Render the shared candlestick chart with an Alpha Vantage timeframe selector."""
    timeframe = st.radio(
        "Chart timeframe",
        list(TIMEFRAME_PERIODS),
        horizontal=True,
        key=f"technical_timeframe_{key_suffix}",
    )
    prices = get_price_history(ticker, TIMEFRAME_PERIODS[timeframe], timeframe=timeframe)
    st.caption(f"Chart source: {prices.attrs.get('source', 'Unknown')}")
    st.plotly_chart(price_line_chart(prices, ticker), use_container_width=True)
