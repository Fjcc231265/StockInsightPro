"""AI interpretation facade for future agent workflows.

The UI calls this module for narrative summaries. For now, responses are
deterministic placeholders; later they can call local or cloud AI agents.
"""

from __future__ import annotations

import pandas as pd

from analytics.technical.engine import calculate_rsi, calculate_simple_moving_average
from data import mock_data


def summarize_news_and_sentiment(ticker: str) -> str:
    """Return placeholder news/sentiment interpretation."""
    # TODO: Replace with AI agent that uses news, sentiment, filings, and price context.
    return mock_data.get_ai_summary_placeholder(ticker)


def summarize_options_intelligence(ticker: str) -> str:
    """Return placeholder options-market interpretation."""
    # TODO: Replace with options-aware AI agent using chain, flow, greeks, and event context.
    return mock_data.get_options_ai_conclusion(ticker)


def summarize_technical_charts(ticker: str, daily: pd.DataFrame, weekly: pd.DataFrame, monthly: pd.DataFrame) -> str:
    """Return an English technical-analysis narrative from chart data."""
    daily_view = _chart_snapshot(daily)
    weekly_view = _chart_snapshot(weekly)
    monthly_view = _chart_snapshot(monthly)
    support_levels = _support_levels(daily)
    resistance_levels = _resistance_levels(daily)
    volume_text = _volume_read(daily)

    primary_trend = _trend_label(daily_view)
    weekly_trend = _trend_label(weekly_view)
    monthly_trend = _trend_label(monthly_view)

    return f"""
### Technical analysis — {ticker}

Generated from the **daily, weekly, and monthly** charts shown in the platform. This is technical commentary only, not financial advice.

#### 1. Overall trend

On the daily chart, {ticker} shows a **{primary_trend}** structure. The latest close is **{daily_view['close']:.2f}**, with the 20-period average at **{daily_view['ma20']:.2f}** and the 40-period average at **{daily_view['ma40']:.2f}**.

The weekly read is **{weekly_trend}**, while the monthly context is **{monthly_trend}**. When daily, weekly, and monthly align, the technical signal is more reliable; when they diverge, short-term moves are often rebounds or pullbacks within a larger structure.

#### 2. Key resistance levels

- **{resistance_levels[0]:.2f}**: immediate near-term resistance.
- **{resistance_levels[1]:.2f}**: zone where profit-taking may appear.
- **{resistance_levels[2]:.2f}**: major resistance from the recent range.

A break above **{resistance_levels[0]:.2f}** on above-average volume would be constructive. Stronger confirmation would be holding above **{resistance_levels[1]:.2f}**.

#### 3. Support levels

- **{support_levels[0]:.2f}**: immediate support.
- **{support_levels[1]:.2f}**: intermediate support.
- **{support_levels[2]:.2f}**: most relevant technical support in the recent range.

While price holds above **{support_levels[1]:.2f}**, the short-term structure looks healthier. A clear loss of that level opens room to test **{support_levels[2]:.2f}**.

#### 4. Moving averages and momentum

Price is **{_position_vs_ma(daily_view['close'], daily_view['ma20'])}** the 20-period average and **{_position_vs_ma(daily_view['close'], daily_view['ma40'])}** the 40-period average. The relationship between the two averages is **{_ma_relationship(daily_view)}**.

Daily RSI(9) is **{daily_view['rsi']:.2f}**, suggesting a **{_rsi_label(daily_view['rsi'])}** condition. Weekly RSI is **{weekly_view['rsi']:.2f}**, useful to see whether the daily move has higher-timeframe support.

#### 5. Volume read

{volume_text}

#### 6. Technical scenarios

Bullish path:

```text
{daily_view['close']:.2f} -> {resistance_levels[0]:.2f} -> {resistance_levels[1]:.2f}
```

Extension path:

```text
{resistance_levels[1]:.2f} -> {resistance_levels[2]:.2f}
```

Defensive path:

```text
{daily_view['close']:.2f} -> {support_levels[0]:.2f} -> {support_levels[1]:.2f}
```

#### 7. Bottom line

{ticker} looks **{primary_trend}** on the short-term chart, with weekly confirmation **{weekly_trend}** and monthly context **{monthly_trend}**. Watch **{resistance_levels[0]:.2f}** overhead and **{support_levels[1]:.2f}** below. The most positive signal would be a breakout with volume; the caution signal would be losing support on rising sell-side volume.
""".strip()


def _chart_snapshot(df: pd.DataFrame) -> dict[str, float]:
    """Calculate the latest technical snapshot for a price series."""
    close = df["Close"]
    return {
        "close": float(close.iloc[-1]),
        "ma20": float(calculate_simple_moving_average(close, 20).iloc[-1]),
        "ma40": float(calculate_simple_moving_average(close, 40).iloc[-1]),
        "rsi": float(calculate_rsi(close, 9).iloc[-1]),
    }


def _support_levels(df: pd.DataFrame) -> list[float]:
    """Return three support levels from recent lows."""
    lows = [
        float(df["Low"].tail(20).min()),
        float(df["Low"].tail(40).min()),
        float(df["Low"].tail(80).min()),
    ]
    levels = sorted(set(round(value, 2) for value in lows), reverse=True)
    if not levels:
        levels = [round(float(df["Close"].iloc[-1]), 2)]
    while len(levels) < 3:
        levels.append(round(levels[-1] * 0.97, 2))
    return levels[:3]


def _resistance_levels(df: pd.DataFrame) -> list[float]:
    """Return three resistance levels from recent highs."""
    highs = [
        float(df["High"].tail(20).max()),
        float(df["High"].tail(40).max()),
        float(df["High"].tail(80).max()),
    ]
    levels = sorted(set(round(value, 2) for value in highs))
    while len(levels) < 3:
        levels.append(round(levels[-1] * 1.03, 2))
    return levels[:3]


def _trend_label(snapshot: dict[str, float]) -> str:
    """Classify trend from price and moving averages."""
    close = snapshot["close"]
    ma20 = snapshot["ma20"]
    ma40 = snapshot["ma40"]
    if close > ma20 > ma40:
        return "bullish"
    if close < ma20 < ma40:
        return "bearish"
    return "mixed / sideways"


def _position_vs_ma(close: float, moving_average: float) -> str:
    return "above" if close >= moving_average else "below"


def _ma_relationship(snapshot: dict[str, float]) -> str:
    if snapshot["ma20"] > snapshot["ma40"]:
        return "positive, with the 20-period average above the 40-period average"
    if snapshot["ma20"] < snapshot["ma40"]:
        return "defensive, with the 20-period average below the 40-period average"
    return "neutral"


def _rsi_label(rsi: float) -> str:
    if rsi >= 70:
        return "overbought or extended"
    if rsi <= 30:
        return "oversold or rebound-prone"
    if rsi >= 55:
        return "constructive"
    if rsi <= 45:
        return "weak"
    return "neutral"


def _volume_read(df: pd.DataFrame) -> str:
    """Describe latest volume compared with recent average."""
    latest_volume = float(df["Volume"].iloc[-1])
    average_volume = float(df["Volume"].tail(20).mean())
    ratio = latest_volume / average_volume if average_volume else 0
    if ratio >= 1.5:
        return (
            f"Recent volume is above the 20-session average ({ratio:.2f}x), "
            "which adds credibility to the current move."
        )
    if ratio <= 0.7:
        return (
            f"Recent volume is below the 20-session average ({ratio:.2f}x), "
            "so confirmation is needed before trusting a breakout too much."
        )
    return (
        f"Volume is near the 20-session average ({ratio:.2f}x), "
        "suggesting moderate—not extreme—confirmation."
    )
