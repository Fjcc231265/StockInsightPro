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


def calculate_macd(
    prices: pd.Series,
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
) -> pd.DataFrame:
    """Calculate MACD line, signal line, and histogram from close prices."""
    ema_fast = prices.ewm(span=fastperiod, adjust=False).mean()
    ema_slow = prices.ewm(span=slowperiod, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signalperiod, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {
            "MACD": macd_line,
            "MACD Signal": signal_line,
            "MACD Hist": histogram,
        }
    )


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calculate Average Directional Index (ADX) using Wilder smoothing."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    smoothing = 1 / window
    atr = true_range.ewm(alpha=smoothing, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=smoothing, adjust=False).mean() / atr.replace(0, float("nan")))
    minus_di = 100 * (minus_dm.ewm(alpha=smoothing, adjust=False).mean() / atr.replace(0, float("nan")))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    return dx.ewm(alpha=smoothing, adjust=False).mean().fillna(0)
