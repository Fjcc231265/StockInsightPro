"""Technical Analysis page with submenu views."""

import streamlit as st

from components.cards import render_quote_cards, render_section_header, render_todo_callout
from components.charts import (
    candlestick_chart,
    macd_chart,
    price_line_chart,
    rsi_chart,
    volume_bar_chart,
)
from data.mock_data import (
    get_candlestick_patterns,
    get_macd_series,
    get_moving_averages_df,
    get_price_history,
    get_quote_summary,
    get_rsi_series,
    get_support_resistance,
    get_volume_analysis,
)


def render(submenu: str) -> None:
    """Route technical analysis submenu to the appropriate view."""
    ticker = st.session_state.selected_ticker
    quote = get_quote_summary(ticker)
    render_section_header("Technical Analysis", f"View: {submenu}")
    render_quote_cards(quote)
    st.divider()

    handlers = {
        "Price chart": _price_chart,
        "Moving averages": _moving_averages,
        "RSI": _rsi,
        "MACD": _macd,
        "Support and resistance": _support_resistance,
        "Volume analysis": _volume_analysis,
        "Candlestick patterns": _candlestick_patterns,
    }
    handlers.get(submenu, _price_chart)(ticker)


def _price_chart(ticker: str) -> None:
    """Price chart submenu."""
    prices = get_price_history(ticker)
    st.plotly_chart(price_line_chart(prices, ticker), use_container_width=True)
    st.plotly_chart(candlestick_chart(prices, ticker), use_container_width=True)
    render_todo_callout("Add chart timeframe selector, overlays, and drawing tools.")


def _moving_averages(ticker: str) -> None:
    """Moving averages table and chart overlay placeholder."""
    prices = get_price_history(ticker)
    ma_df = get_moving_averages_df(ticker)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(ma_df, use_container_width=True, hide_index=True)
    with col2:
        fig = price_line_chart(prices, ticker)
        # TODO: Overlay SMA/EMA lines on chart
        st.plotly_chart(fig, use_container_width=True)
    render_todo_callout("Calculate and plot SMA 20/50/200 and EMA 12/26 from live data.")


def _rsi(ticker: str) -> None:
    """RSI indicator view."""
    rsi_df = get_rsi_series(ticker)
    st.plotly_chart(rsi_chart(rsi_df, ticker), use_container_width=True)
    latest = rsi_df["RSI"].iloc[-1]
    st.info(f"Latest RSI (mock): **{latest:.1f}** — Neutral zone placeholder.")
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
    prices = get_price_history(ticker, 30)
    st.plotly_chart(price_line_chart(prices, ticker), use_container_width=True)
    render_todo_callout("Auto-detect S/R from swing highs/lows and volume nodes.")


def _volume_analysis(ticker: str) -> None:
    """Volume analysis metrics and chart."""
    vol_stats = get_volume_analysis(ticker)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(vol_stats, use_container_width=True, hide_index=True)
    with col2:
        prices = get_price_history(ticker)
        st.plotly_chart(volume_bar_chart(prices, ticker), use_container_width=True)
    render_todo_callout("Add OBV, VWAP, and relative volume indicators.")


def _candlestick_patterns(ticker: str) -> None:
    """Detected candlestick patterns table."""
    patterns = get_candlestick_patterns()
    st.dataframe(patterns, use_container_width=True, hide_index=True)
    prices = get_price_history(ticker)
    st.plotly_chart(candlestick_chart(prices, ticker), use_container_width=True)
    render_todo_callout("Build pattern recognition engine (engulfing, doji, stars, etc.).")
