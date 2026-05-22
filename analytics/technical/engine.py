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
