"""Going Up scan analytics — universe metrics for filter-then-report verification."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analytics.technical.engine import calculate_rsi, calculate_simple_moving_average


@dataclass(frozen=True)
class GoingUpScanConfig:
    """Tunable settings for Going Up universe metrics."""

    ma_fast: int = 20
    ma_slow: int = 40
    history_periods: int = 90
    rsi_period: int = 9
    min_history_rows: int = 45


def evaluate_going_up_metrics(history: pd.DataFrame, config: GoingUpScanConfig | None = None) -> dict | None:
    """Return price, volume, RSI, and distance-above-MA metrics for one symbol."""
    cfg = config or GoingUpScanConfig()
    frame = history.sort_values("Date").reset_index(drop=True)
    if len(frame) < cfg.min_history_rows:
        return None

    close = frame["Close"]
    ma_fast = calculate_simple_moving_average(close, cfg.ma_fast)
    ma_slow = calculate_simple_moving_average(close, cfg.ma_slow)
    rsi = calculate_rsi(close, window=cfg.rsi_period)

    latest = frame.iloc[-1]
    latest_close = float(latest["Close"])
    latest_ma_fast = float(ma_fast.iloc[-1])
    latest_ma_slow = float(ma_slow.iloc[-1])
    latest_rsi = float(rsi.iloc[-1])
    if pd.isna(latest_ma_fast) or pd.isna(latest_ma_slow) or pd.isna(latest_rsi):
        return None
    if latest_ma_fast <= 0 or latest_ma_slow <= 0:
        return None

    latest_volume = float(latest.get("Volume", 0) or 0)
    avg_volume = float(frame["Volume"].tail(20).mean()) if "Volume" in frame.columns else 0.0
    pct_above_ma20 = ((latest_close - latest_ma_fast) / latest_ma_fast) * 100
    pct_above_ma40 = ((latest_close - latest_ma_slow) / latest_ma_slow) * 100

    return {
        "Ticker": None,
        "Date": latest["Date"].strftime("%Y-%m-%d") if hasattr(latest["Date"], "strftime") else str(latest["Date"]),
        "Price": round(latest_close, 2),
        "Volume": int(latest_volume),
        "Avg Volume 20D": int(avg_volume),
        "RSI": round(latest_rsi, 2),
        "MA20": round(latest_ma_fast, 2),
        "MA40": round(latest_ma_slow, 2),
        "% Above MA20": round(pct_above_ma20, 2),
        "% Above MA40": round(pct_above_ma40, 2),
    }
