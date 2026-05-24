"""Technical analytics engine placeholder.

Keep calculations independent from Streamlit so they can be reused by services,
batch jobs, tests, and future AI agents.
"""

from __future__ import annotations

import pandas as pd


def calculate_simple_moving_average(prices: pd.Series, window: int) -> pd.Series:
    """Calculate a simple moving average."""
    # TODO: Expand into a full indicator library.
    return prices.rolling(window=window).mean()


def calculate_rsi(prices: pd.Series, window: int = 9) -> pd.Series:
    """Calculate RSI using rolling average gains and losses."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(window=window, min_periods=window).mean()
    average_loss = loss.rolling(window=window, min_periods=window).mean()
    relative_strength = average_gain / average_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + relative_strength))
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_gain == 0) & (average_loss > 0), 0)
    return rsi.fillna(50)
