"""Technical analysis data service facade."""

from __future__ import annotations

import pandas as pd

from analytics.technical.engine import calculate_rsi, calculate_simple_moving_average
from ai.market_interpreter import summarize_technical_charts
from data import mock_data
from services.market_data_service import get_price_history


def get_moving_averages_df(ticker: str) -> pd.DataFrame:
    """Return moving average summary."""
    prices = get_price_history(ticker)
    close = prices["Close"]
    return pd.DataFrame(
        {
            "Period": ["20 MA", "40 MA"],
            "Value": [
                round(calculate_simple_moving_average(close, 20).iloc[-1], 2),
                round(calculate_simple_moving_average(close, 40).iloc[-1], 2),
            ],
            "Signal": [
                "Bullish" if close.iloc[-1] >= calculate_simple_moving_average(close, 20).iloc[-1] else "Bearish",
                "Bullish" if close.iloc[-1] >= calculate_simple_moving_average(close, 40).iloc[-1] else "Bearish",
            ],
        }
    )


def get_rsi_series(ticker: str) -> pd.DataFrame:
    """Return RSI series."""
    prices = get_price_history(ticker)
    return pd.DataFrame({"Date": prices["Date"], "RSI": calculate_rsi(prices["Close"], 9)})


def get_macd_series(ticker: str) -> pd.DataFrame:
    """Return MACD series."""
    # TODO: Replace with MACD calculation engine.
    return mock_data.get_macd_series(ticker)


def get_support_resistance(ticker: str) -> pd.DataFrame:
    """Return support/resistance levels."""
    # TODO: Replace with swing/volume-profile detection engine.
    return mock_data.get_support_resistance(ticker)


def get_volume_analysis(ticker: str) -> pd.DataFrame:
    """Return volume analysis table."""
    # TODO: Replace with OBV/VWAP/relative-volume engine.
    return mock_data.get_volume_analysis(ticker)


def get_candlestick_patterns() -> pd.DataFrame:
    """Return detected candlestick patterns."""
    # TODO: Replace with candlestick recognition engine.
    return mock_data.get_candlestick_patterns()


def get_written_technical_analysis(ticker: str) -> str:
    """Return a written technical analysis from daily, weekly, and monthly charts."""
    daily = get_price_history(ticker, 180, timeframe="Daily")
    weekly = get_price_history(ticker, 156, timeframe="Weekly")
    monthly = get_price_history(ticker, 120, timeframe="Monthly")
    return summarize_technical_charts(ticker, daily=daily, weekly=weekly, monthly=monthly)
