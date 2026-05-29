"""Technical analysis data service facade."""

from __future__ import annotations

import time

import pandas as pd

from analytics.technical.engine import calculate_rsi, calculate_simple_moving_average
from ai.market_interpreter import summarize_technical_charts
from data import mock_data
from data.providers import alpha_vantage_provider
from services.market_data_service import get_price_history
from services.settings_service import should_use_alpha_vantage

_TECHNICAL_ANALYSIS_CACHE: dict[str, tuple[float, str]] = {}
TECHNICAL_ANALYSIS_CACHE_TTL_SECONDS = 900


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


def get_rsi_series(ticker: str, time_period: int = 9, days: int = 90) -> pd.DataFrame:
    """Return RSI series calculated from cached daily OHLC."""
    rsi = alpha_vantage_provider.get_rsi_history(ticker, days=days, time_period=time_period)
    rsi.attrs["time_period"] = time_period
    return rsi


def get_rsi_series_bundle(ticker: str, periods: tuple[int, ...] = (9, 14), days: int = 90) -> dict[int, pd.DataFrame]:
    """Return multiple RSI series from one compact daily OHLC fetch."""
    lookback = 100 if days <= 90 else max(days + max(periods) + 10, 100)
    prices = get_price_history(ticker, days=lookback, timeframe="Daily").sort_values("Date").reset_index(drop=True)
    if prices.empty:
        raise alpha_vantage_provider.AlphaVantageError(f"No daily price history returned for {ticker}.")

    source = prices.attrs.get("source", "Daily OHLC")
    series_by_period: dict[int, pd.DataFrame] = {}
    for period in periods:
        rsi = pd.DataFrame(
            {
                "Date": prices["Date"],
                "RSI": calculate_rsi(prices["Close"], window=period).round(2),
            }
        ).tail(days)
        rsi.attrs["source"] = f"{source} · RSI({period})"
        rsi.attrs["time_period"] = period
        series_by_period[period] = rsi.reset_index(drop=True)
    return series_by_period


def get_macd_series(ticker: str, days: int = 60) -> pd.DataFrame:
    """Return MACD series calculated from cached daily OHLC."""
    return alpha_vantage_provider.get_macd_history(ticker, days=days)


def get_support_resistance(ticker: str) -> pd.DataFrame:
    """Return support/resistance levels derived from recent price history."""
    prices = get_price_history(ticker, days=100, timeframe="Daily").sort_values("Date").reset_index(drop=True)
    if prices.empty:
        levels = pd.DataFrame(columns=["Level Type", "Price", "Strength", "Distance %"])
        levels.attrs["source"] = prices.attrs.get("source", "Price history")
        return levels

    latest_close = float(prices["Close"].iloc[-1])
    recent = prices.tail(90)
    candidates = [
        ("Resistance", float(recent["High"].max()), "90D high"),
        ("Support", float(recent["Low"].min()), "90D low"),
        ("Resistance", float(recent["Close"].tail(20).max()), "20D closing high"),
        ("Support", float(recent["Close"].tail(20).min()), "20D closing low"),
        ("Pivot", _latest_pivot(prices), "Prior session pivot"),
    ]

    rows = []
    for level_type, price, strength in candidates:
        if price <= 0:
            continue
        rows.append(
            {
                "Level Type": level_type,
                "Price": round(price, 2),
                "Strength": strength,
                "Distance %": round(((price - latest_close) / latest_close) * 100, 2) if latest_close else 0,
            }
        )

    levels = pd.DataFrame(rows).drop_duplicates(subset=["Level Type", "Price"]).sort_values("Price", ascending=False)
    levels.attrs["source"] = prices.attrs.get("source", "Price history")
    return levels.reset_index(drop=True)


def get_volume_analysis(ticker: str) -> pd.DataFrame:
    """Return volume analysis calculated from cached daily OHLCV data."""
    if not should_use_alpha_vantage("market") or not alpha_vantage_provider.is_configured():
        raise alpha_vantage_provider.AlphaVantageError("Alpha Vantage API key is not configured.")

    prices = get_price_history(ticker, days=100, timeframe="Daily")
    if prices.empty or "Volume" not in prices:
        raise alpha_vantage_provider.AlphaVantageError(f"No usable volume history returned for {ticker}.")

    prices = prices.sort_values("Date").reset_index(drop=True)
    latest_volume = float(prices["Volume"].iloc[-1])
    previous_volume = float(prices["Volume"].iloc[-2]) if len(prices) >= 2 else latest_volume
    avg_20 = float(prices["Volume"].tail(20).mean())
    avg_50 = float(prices["Volume"].tail(50).mean())
    relative_volume = latest_volume / avg_20 if avg_20 else 0
    volume_change_pct = ((latest_volume - previous_volume) / previous_volume * 100) if previous_volume else 0

    latest_5_avg = float(prices["Volume"].tail(5).mean())
    prior_5_avg = float(prices["Volume"].iloc[-10:-5].mean()) if len(prices) >= 10 else latest_5_avg
    trend_change_pct = ((latest_5_avg - prior_5_avg) / prior_5_avg * 100) if prior_5_avg else 0

    rows = [
        {
            "Metric": "Latest Volume",
            "Value": f"{latest_volume:,.0f}",
            "Signal": "Above 20D average" if latest_volume > avg_20 else "Below 20D average",
        },
        {
            "Metric": "Day-over-Day Volume Change",
            "Value": f"{volume_change_pct:.1f}%",
            "Signal": "Volume expanding" if volume_change_pct > 0 else "Volume contracting",
        },
        {
            "Metric": "20D Average Volume",
            "Value": f"{avg_20:,.0f}",
            "Signal": "Recent baseline",
        },
        {
            "Metric": "50D Average Volume",
            "Value": f"{avg_50:,.0f}",
            "Signal": "Longer baseline",
        },
        {
            "Metric": "Relative Volume vs 20D Avg",
            "Value": f"{relative_volume:.2f}x",
            "Signal": "Elevated activity" if relative_volume >= 1.5 else "Normal activity",
        },
        {
            "Metric": "5D Volume Trend",
            "Value": f"{trend_change_pct:.1f}%",
            "Signal": "Rising" if trend_change_pct > 0 else "Falling",
        },
    ]
    analysis = pd.DataFrame(rows)
    analysis.attrs["source"] = prices.attrs.get("source", "Alpha Vantage daily OHLCV")
    return analysis


def get_candlestick_patterns(ticker: str) -> pd.DataFrame:
    """Return simple candlestick patterns detected from recent OHLC data."""
    prices = get_price_history(ticker, days=60, timeframe="Daily").sort_values("Date").reset_index(drop=True)
    rows = []
    for index in range(1, len(prices)):
        previous = prices.iloc[index - 1]
        current = prices.iloc[index]
        pattern = _detect_candlestick_pattern(previous, current)
        if pattern is not None:
            rows.append(pattern)

    patterns = pd.DataFrame(rows).tail(10)
    if patterns.empty:
        patterns = pd.DataFrame(columns=["Pattern", "Date", "Reliability", "Direction"])
    patterns.attrs["source"] = prices.attrs.get("source", "Price history")
    return patterns.reset_index(drop=True)


def _latest_pivot(prices: pd.DataFrame) -> float:
    """Return the prior session classic floor-trader pivot."""
    if len(prices) < 2:
        latest = prices.iloc[-1]
    else:
        latest = prices.iloc[-2]
    return float((latest["High"] + latest["Low"] + latest["Close"]) / 3)


def _detect_candlestick_pattern(previous: pd.Series, current: pd.Series) -> dict | None:
    """Detect a small set of common candle patterns."""
    open_price = float(current["Open"])
    high_price = float(current["High"])
    low_price = float(current["Low"])
    close_price = float(current["Close"])
    previous_open = float(previous["Open"])
    previous_close = float(previous["Close"])
    candle_range = high_price - low_price
    body = abs(close_price - open_price)
    if candle_range <= 0:
        return None

    date = current["Date"].strftime("%Y-%m-%d") if hasattr(current["Date"], "strftime") else str(current["Date"])
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price

    if body / candle_range <= 0.1:
        return {"Pattern": "Doji", "Date": date, "Reliability": "Medium", "Direction": "Neutral"}
    if lower_shadow >= body * 2 and upper_shadow <= body:
        direction = "Bullish" if close_price >= open_price else "Potential Reversal"
        return {"Pattern": "Hammer", "Date": date, "Reliability": "Medium", "Direction": direction}
    if upper_shadow >= body * 2 and lower_shadow <= body:
        direction = "Bearish" if close_price <= open_price else "Potential Reversal"
        return {"Pattern": "Shooting Star", "Date": date, "Reliability": "Medium", "Direction": direction}
    if previous_close < previous_open and close_price > open_price and close_price >= previous_open and open_price <= previous_close:
        return {"Pattern": "Bullish Engulfing", "Date": date, "Reliability": "High", "Direction": "Bullish"}
    if previous_close > previous_open and close_price < open_price and open_price >= previous_close and close_price <= previous_open:
        return {"Pattern": "Bearish Engulfing", "Date": date, "Reliability": "High", "Direction": "Bearish"}
    return None


def get_written_technical_analysis(ticker: str) -> str:
    """Return a written technical analysis from daily, weekly, and monthly charts."""
    cache_key = ticker.strip().upper()
    cached = _TECHNICAL_ANALYSIS_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < TECHNICAL_ANALYSIS_CACHE_TTL_SECONDS:
        return cached[1]

    # The written analysis only needs recent context for MAs/RSI/support levels.
    # Keeping daily compact avoids the slow full daily payload.
    daily = get_price_history(ticker, 100, timeframe="Daily")
    weekly = get_price_history(ticker, 156, timeframe="Weekly")
    monthly = get_price_history(ticker, 120, timeframe="Monthly")
    analysis = summarize_technical_charts(ticker, daily=daily, weekly=weekly, monthly=monthly)
    _TECHNICAL_ANALYSIS_CACHE[cache_key] = (time.time(), analysis)
    return analysis


def get_technical_trend_label(analysis: str) -> str:
    """Extract the primary technical trend label from written analysis."""
    marker = "shows a **"
    if marker not in analysis:
        return "Unknown"
    return analysis.split(marker, 1)[1].split("**", 1)[0]
