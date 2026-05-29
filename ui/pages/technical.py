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
    get_rsi_series_bundle,
    get_support_resistance,
    get_technical_trend_label,
    get_volume_analysis,
    get_written_technical_analysis,
)

TIMEFRAME_PERIODS = {
    "Daily": 100,
    "Weekly": 104,
    "Monthly": 60,
    "Hourly": 100,
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
    _render_written_technical_analysis(ticker)
    render_todo_callout("Add drawing tools and saved chart layouts.")


def _moving_averages(ticker: str) -> None:
    """Moving averages table and chart overlay."""
    ma_df = get_moving_averages_df(ticker)
    _render_timeframe_price_chart(ticker, "moving_averages")

    st.markdown("**Moving Average Signals**")
    _, table_col, _ = st.columns([1, 2, 1])
    with table_col:
        st.dataframe(ma_df, use_container_width=True, hide_index=True)
    render_todo_callout("Expand the moving average table with SMA 50/200 and EMA 12/26.")


def _rsi(ticker: str) -> None:
    """RSI indicator view."""
    try:
        rsi_by_period = get_rsi_series_bundle(ticker, periods=(9, 14), days=90)
    except Exception as exc:  # noqa: BLE001 - provider errors are shown in the UI
        st.error(f"RSI is unavailable for {ticker}: {exc}")
        return

    tabs = st.tabs(["RSI(9)", "RSI(14)"])
    for tab, period in zip(tabs, [9, 14]):
        with tab:
            rsi_df = rsi_by_period[period]
            st.caption(f"Indicator source: {rsi_df.attrs.get('source', 'Daily OHLC RSI')}")
            st.plotly_chart(rsi_chart(rsi_df, ticker, time_period=period), use_container_width=True)
            latest = rsi_df["RSI"].iloc[-1]
            if latest >= 70:
                zone = "Overbought"
            elif latest <= 30:
                zone = "Oversold"
            else:
                zone = "Neutral"
            st.info(f"Latest RSI({period}): **{latest:.2f}** — {zone}.")
    render_todo_callout("Add RSI divergence detection and configurable alert thresholds.")


def _macd(ticker: str) -> None:
    """MACD indicator view."""
    try:
        macd_df = get_macd_series(ticker)
    except Exception as exc:  # noqa: BLE001 - provider errors are shown in the UI
        st.error(f"Alpha Vantage MACD is unavailable for {ticker}: {exc}")
        return

    st.caption(f"Indicator source: {macd_df.attrs.get('source', 'Daily OHLC MACD')}")
    st.plotly_chart(macd_chart(macd_df, ticker), use_container_width=True)
    st.info(_macd_takeaway(macd_df))
    render_todo_callout("Add configurable MACD alerts and divergence detection.")


def _macd_takeaway(macd_df) -> str:
    """Return a concise interpretation of the latest MACD state."""
    if macd_df.empty:
        return "MACD takeaway: no usable MACD values were returned."

    signal_column = "MACD Signal" if "MACD Signal" in macd_df.columns else "Signal"
    histogram_column = "MACD Hist" if "MACD Hist" in macd_df.columns else "Histogram"
    latest = macd_df.iloc[-1]
    previous = macd_df.iloc[-2] if len(macd_df) >= 2 else latest

    macd_value = float(latest["MACD"])
    signal_value = float(latest[signal_column])
    histogram_value = float(latest[histogram_column])
    previous_macd = float(previous["MACD"])
    previous_signal = float(previous[signal_column])
    previous_histogram = float(previous[histogram_column])

    if previous_macd <= previous_signal and macd_value > signal_value:
        crossover = "a fresh bullish crossover"
    elif previous_macd >= previous_signal and macd_value < signal_value:
        crossover = "a fresh bearish crossover"
    elif macd_value > signal_value:
        crossover = "bullish momentum remains in place"
    else:
        crossover = "bearish momentum remains in place"

    zero_context = "above the zero line" if macd_value >= 0 else "below the zero line"
    histogram_context = "expanding" if histogram_value > previous_histogram else "contracting"
    direction = "constructive" if macd_value > signal_value and histogram_value >= 0 else "cautious"

    return (
        f"MACD takeaway: **{direction.title()}** setup. The MACD line is {zero_context} and shows "
        f"{crossover}; the histogram is {histogram_context} at {histogram_value:.4f}."
    )


def _support_resistance(ticker: str) -> None:
    """Support and resistance levels table."""
    levels = get_support_resistance(ticker)
    st.caption(f"Table source: {levels.attrs.get('source', 'Price history')}")
    st.dataframe(levels, use_container_width=True, hide_index=True)
    _render_timeframe_price_chart(ticker, "support_resistance")
    render_todo_callout("Add volume-profile weighting and saved manual levels.")


def _volume_analysis(ticker: str) -> None:
    """Volume analysis metrics and chart."""
    try:
        vol_stats = get_volume_analysis(ticker)
    except Exception as exc:  # noqa: BLE001 - provider errors are shown in the UI
        st.error(f"Alpha Vantage volume analysis is unavailable for {ticker}: {exc}")
        return

    _render_timeframe_price_chart(ticker, "volume_analysis")

    st.markdown("**Volume Metrics**")
    st.caption(f"Table source: {vol_stats.attrs.get('source', 'Alpha Vantage daily OHLCV')}")
    _, table_col, _ = st.columns([1, 2, 1])
    with table_col:
        st.dataframe(vol_stats, use_container_width=True, hide_index=True)
    render_todo_callout("Add OBV, VWAP, and relative volume indicators.")


def _candlestick_patterns(ticker: str) -> None:
    """Detected candlestick patterns table."""
    patterns = get_candlestick_patterns(ticker)
    st.caption(f"Table source: {patterns.attrs.get('source', 'Price history')}")
    st.dataframe(patterns, use_container_width=True, hide_index=True)
    _render_timeframe_price_chart(ticker, "candlestick_patterns")
    render_todo_callout("Expand the pattern engine with confirmation and multi-candle setups.")


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


def _render_technical_trend_badge(trend_label: str) -> None:
    """Render color-coded primary technical trend."""
    color = _technical_trend_color(trend_label)
    display_label = {
        "bullish": "Upward / Bullish",
        "mixed / sideways": "Sideways / Mixed",
        "bearish": "Downward / Bearish",
    }.get(trend_label, trend_label.title())
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
            <span style="display:inline-block;background:{color};color:white;border-radius:999px;padding:6px 14px;font-size:14px;font-weight:700;">
                Technical Trend: {display_label}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _technical_trend_color(trend_label: str) -> str:
    """Return badge color for trend label."""
    if trend_label == "bullish":
        return "#1a7f4e"
    if trend_label == "bearish":
        return "#c0392b"
    if trend_label == "mixed / sideways":
        return "#c9a227"
    return "#5a6a7a"


def _render_written_technical_analysis(ticker: str) -> None:
    """Render on-demand written technical assessment."""
    analysis_key = f"show_technical_analysis_{ticker}"
    result_key = f"technical_analysis_result_{ticker}"
    if st.button("Generate technical analysis", key=f"technical_analysis_button_{ticker}", type="primary"):
        st.session_state[analysis_key] = True
        st.session_state.pop(result_key, None)

    if st.session_state.get(analysis_key):
        with st.expander("Professional technical analysis", expanded=True):
            if result_key not in st.session_state:
                with st.spinner("Analyzing technical charts..."):
                    st.session_state[result_key] = get_written_technical_analysis(ticker)
            analysis = st.session_state[result_key]
            trend_label = get_technical_trend_label(analysis)
            _render_technical_trend_badge(trend_label)
            st.markdown(analysis)
