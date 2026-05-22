"""Technical analysis data service facade."""

from __future__ import annotations

import pandas as pd

from data import mock_data


def get_moving_averages_df(ticker: str) -> pd.DataFrame:
    """Return moving average summary."""
    # TODO: Replace with analytics.technical engine output.
    return mock_data.get_moving_averages_df(ticker)


def get_rsi_series(ticker: str) -> pd.DataFrame:
    """Return RSI series."""
    # TODO: Replace with RSI calculation engine.
    return mock_data.get_rsi_series(ticker)


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
