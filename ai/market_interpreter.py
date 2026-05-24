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


def summarize_fundamental_health(
    ticker: str,
    income_annual: pd.DataFrame,
    income_quarterly: pd.DataFrame,
    balance_annual: pd.DataFrame,
    balance_quarterly: pd.DataFrame,
    cashflow_annual: pd.DataFrame,
) -> str:
    """Return a professional fundamental-health narrative from financial statements."""
    annual_income = _statement_values(income_annual)
    quarterly_income = _statement_values(income_quarterly)
    annual_balance = _statement_values(balance_annual)
    quarterly_balance = _statement_values(balance_quarterly)
    annual_cashflow = _statement_values(cashflow_annual)

    latest_revenue, prior_revenue = _latest_pair(annual_income, "Revenue")
    latest_net_income, prior_net_income = _latest_pair(annual_income, "Net Income")
    latest_gross_profit, _ = _latest_pair(annual_income, "Gross Profit")
    latest_operating_income, _ = _latest_pair(annual_income, "Operating Income")
    latest_ebitda, _ = _latest_pair(annual_income, "EBITDA")

    latest_quarter_revenue, prior_quarter_revenue = _latest_pair(quarterly_income, "Revenue")
    latest_quarter_net_income, prior_quarter_net_income = _latest_pair(quarterly_income, "Net Income")

    cash = _latest_value(quarterly_balance, "Cash & Equivalents")
    current_assets = _latest_value(quarterly_balance, "Current Assets")
    current_liabilities = _latest_value(quarterly_balance, "Current Liabilities")
    total_assets = _latest_value(quarterly_balance, "Total Assets")
    total_liabilities = _latest_value(quarterly_balance, "Total Liabilities")
    total_debt = _latest_value(quarterly_balance, "Total Debt")
    equity = _latest_value(quarterly_balance, "Shareholders' Equity")

    operating_cash_flow = _latest_value(annual_cashflow, "Operating Cash Flow")
    capex = _latest_value(annual_cashflow, "Capital Expenditures")
    free_cash_flow = _free_cash_flow(operating_cash_flow, capex)

    revenue_growth = _growth_rate(latest_revenue, prior_revenue)
    net_income_growth = _growth_rate(latest_net_income, prior_net_income)
    quarterly_revenue_growth = _growth_rate(latest_quarter_revenue, prior_quarter_revenue)
    quarterly_net_income_growth = _growth_rate(latest_quarter_net_income, prior_quarter_net_income)

    gross_margin = _ratio(latest_gross_profit, latest_revenue)
    operating_margin = _ratio(latest_operating_income, latest_revenue)
    ebitda_margin = _ratio(latest_ebitda, latest_revenue)
    net_margin = _ratio(latest_net_income, latest_revenue)
    current_ratio = _ratio(current_assets, current_liabilities)
    cash_to_debt = _ratio(cash, total_debt)
    debt_to_equity = _ratio(total_debt, equity)
    liability_to_assets = _ratio(total_liabilities, total_assets)
    fcf_margin = _ratio(free_cash_flow, latest_revenue)

    health_label = _fundamental_health_label(
        current_ratio=current_ratio,
        cash_to_debt=cash_to_debt,
        debt_to_equity=debt_to_equity,
        free_cash_flow=free_cash_flow,
        net_margin=net_margin,
        revenue_growth=revenue_growth,
    )

    cash_assessment = _cash_assessment(cash, total_debt, free_cash_flow)
    growth_assessment = _growth_assessment(revenue_growth, quarterly_revenue_growth, net_margin, free_cash_flow)

    return f"""
### Fundamental financial health analysis — {ticker}

This assessment is based on the latest Alpha Vantage annual and quarterly income statement, balance sheet, and cash flow statement available in the app. Monetary figures are shown in **USD millions**.

#### 1. Growth profile

- Latest annual revenue: **{_money(latest_revenue)}**, versus **{_money(prior_revenue)}** in the prior year (**{_percent(revenue_growth)}**).
- Latest annual net income: **{_money(latest_net_income)}**, versus **{_money(prior_net_income)}** in the prior year (**{_percent(net_income_growth)}**).
- Latest quarterly revenue trend: **{_percent(quarterly_revenue_growth)}** versus the immediately prior quarter.
- Latest quarterly net income trend: **{_percent(quarterly_net_income_growth)}** versus the immediately prior quarter.

The revenue trend is **{_trend_word(revenue_growth)}** on an annual basis and **{_trend_word(quarterly_revenue_growth)}** on the latest quarterly comparison. This helps separate durable annual growth from short-term seasonality.

#### 2. Profitability and margins

- Gross margin: **{_percent(gross_margin)}**
- Operating margin: **{_percent(operating_margin)}**
- EBITDA margin: **{_percent(ebitda_margin)}**
- Net margin: **{_percent(net_margin)}**
- Free cash flow margin: **{_percent(fcf_margin)}**

The margin profile looks **{_margin_quality(net_margin, operating_margin)}**. A company with positive operating and net margins has more flexibility to fund growth internally; weak or negative margins make cash reserves and access to capital much more important.

#### 3. Balance sheet and liquidity

- Cash and equivalents: **{_money(cash)}**
- Total debt: **{_money(total_debt)}**
- Current ratio: **{_number(current_ratio)}**
- Cash-to-debt ratio: **{_number(cash_to_debt)}**
- Debt-to-equity ratio: **{_number(debt_to_equity)}**
- Liabilities / assets: **{_percent(liability_to_assets)}**

{cash_assessment}

#### 4. Cash generation

- Operating cash flow: **{_money(operating_cash_flow)}**
- Capital expenditures: **{_money(capex)}**
- Estimated free cash flow: **{_money(free_cash_flow)}**

Free cash flow is a key test of whether growth can be self-funded. Positive free cash flow suggests the business can invest, reduce debt, or return capital without relying entirely on new financing. Negative free cash flow means the company must rely more heavily on cash reserves, debt capacity, equity issuance, or external funding.

#### 5. Ability to keep growing

{growth_assessment}

#### 6. Final assessment

Overall fundamental health: **{health_label}**.

My fundamental read is that {ticker} has **{_balance_sheet_phrase(current_ratio, cash_to_debt, debt_to_equity)}** and **{_profitability_phrase(net_margin, free_cash_flow)}**. The most important items to monitor next are revenue growth persistence, margin stability, free cash flow conversion, and whether cash remains sufficient relative to debt and operating needs.
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


def _statement_values(statement: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Convert a displayed statement table into metric -> period values."""
    normalized = statement.copy()
    if "Metric" not in normalized.columns:
        normalized = normalized.reset_index().rename(columns={normalized.index.name or "index": "Metric"})

    period_columns = [column for column in normalized.columns if column != "Metric"]
    values: dict[str, dict[str, float]] = {}
    for _, row in normalized.iterrows():
        values[str(row["Metric"])] = {
            period: _parse_financial_value(row[period])
            for period in period_columns
        }
    return values


def _parse_financial_value(value: object) -> float | None:
    """Parse financial display values in millions."""
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def _latest_pair(values: dict[str, dict[str, float]], metric: str) -> tuple[float | None, float | None]:
    """Return latest and prior values for a metric."""
    metric_values = values.get(metric, {})
    periods = list(metric_values)
    latest = metric_values.get(periods[0]) if periods else None
    prior = metric_values.get(periods[1]) if len(periods) > 1 else None
    return latest, prior


def _latest_value(values: dict[str, dict[str, float]], metric: str) -> float | None:
    """Return latest value for a metric."""
    latest, _ = _latest_pair(values, metric)
    return latest


def _growth_rate(current: float | None, prior: float | None) -> float | None:
    """Return percentage growth rate."""
    if current is None or prior in (None, 0):
        return None
    return ((current - prior) / abs(prior)) * 100


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Return a ratio with zero/None protection."""
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _free_cash_flow(operating_cash_flow: float | None, capex: float | None) -> float | None:
    """Return estimated free cash flow from operating cash flow and capex."""
    if operating_cash_flow is None:
        return None
    return operating_cash_flow - abs(capex or 0)


def _money(value: float | None) -> str:
    """Format USD millions."""
    return "-" if value is None else f"USD {value:,.2f}M"


def _percent(value: float | None) -> str:
    """Format ratios or percent values."""
    if value is None:
        return "-"
    if abs(value) <= 3:
        value *= 100
    return f"{value:+.2f}%" if value < 0 else f"{value:.2f}%"


def _number(value: float | None) -> str:
    """Format numeric ratio."""
    return "-" if value is None else f"{value:.2f}x"


def _trend_word(growth_rate: float | None) -> str:
    """Return a plain-English trend label."""
    if growth_rate is None:
        return "unclear"
    if growth_rate >= 10:
        return "strong"
    if growth_rate >= 3:
        return "positive"
    if growth_rate >= -3:
        return "stable"
    return "weak"


def _margin_quality(net_margin: float | None, operating_margin: float | None) -> str:
    """Assess margin profile."""
    if net_margin is None or operating_margin is None:
        return "unclear"
    if net_margin >= 0.15 and operating_margin >= 0.2:
        return "strong"
    if net_margin > 0 and operating_margin > 0:
        return "positive but should be monitored"
    return "weak or under pressure"


def _cash_assessment(cash: float | None, total_debt: float | None, free_cash_flow: float | None) -> str:
    """Return a liquidity and cash sufficiency assessment."""
    cash_to_debt = _ratio(cash, total_debt)
    if cash is None:
        return "Cash visibility is limited from the current statement data."
    if total_debt in (None, 0):
        debt_phrase = "The company has little or no reported debt, which gives the balance sheet more flexibility."
    elif cash_to_debt is not None and cash_to_debt >= 1:
        debt_phrase = "Cash is greater than reported debt, which is a strong liquidity position."
    elif cash_to_debt is not None and cash_to_debt >= 0.5:
        debt_phrase = "Cash covers a meaningful portion of debt, but leverage still needs monitoring."
    else:
        debt_phrase = "Cash does not fully cover debt, so refinancing risk and cash generation matter more."

    if free_cash_flow is not None and free_cash_flow > 0:
        fcf_phrase = "Positive free cash flow supports ongoing operations and growth investment."
    elif free_cash_flow is not None:
        fcf_phrase = "Negative free cash flow means cash reserves or external capital may be needed to keep investing."
    else:
        fcf_phrase = "Free cash flow could not be clearly assessed from the available data."
    return f"{debt_phrase} {fcf_phrase}"


def _growth_assessment(
    annual_revenue_growth: float | None,
    quarterly_revenue_growth: float | None,
    net_margin: float | None,
    free_cash_flow: float | None,
) -> str:
    """Assess fundamental ability to keep growing."""
    positive_growth = (annual_revenue_growth or 0) > 0 or (quarterly_revenue_growth or 0) > 0
    profitable = net_margin is not None and net_margin > 0
    cash_generative = free_cash_flow is not None and free_cash_flow > 0

    if positive_growth and profitable and cash_generative:
        return "The company appears fundamentally capable of continuing to grow because revenue is expanding, margins are positive, and free cash flow is supportive."
    if positive_growth and profitable:
        return "The company has growth and profitability, but cash-flow conversion should be monitored to confirm that growth can be funded internally."
    if positive_growth:
        return "The company is growing, but the quality of that growth depends on improving profitability and cash-flow generation."
    return "Growth capacity looks limited unless revenue momentum, profitability, or cash generation improves."


def _fundamental_health_label(
    current_ratio: float | None,
    cash_to_debt: float | None,
    debt_to_equity: float | None,
    free_cash_flow: float | None,
    net_margin: float | None,
    revenue_growth: float | None,
) -> str:
    """Classify overall fundamental health."""
    score = 0
    score += 1 if current_ratio is not None and current_ratio >= 1.0 else 0
    score += 1 if cash_to_debt is not None and cash_to_debt >= 0.3 else 0
    score += 1 if debt_to_equity is None or debt_to_equity <= 2 else 0
    score += 1 if free_cash_flow is not None and free_cash_flow > 0 else 0
    score += 1 if net_margin is not None and net_margin > 0 else 0
    score += 1 if revenue_growth is not None and revenue_growth > 0 else 0

    if score >= 5:
        return "Strong"
    if score >= 3:
        return "Adequate / watchlist"
    return "Weak / high monitoring required"


def _balance_sheet_phrase(current_ratio: float | None, cash_to_debt: float | None, debt_to_equity: float | None) -> str:
    """Summarize balance sheet condition."""
    if current_ratio is not None and current_ratio >= 1.5 and (cash_to_debt or 0) >= 1:
        return "a strong liquidity position"
    if current_ratio is not None and current_ratio >= 1 and (debt_to_equity is None or debt_to_equity <= 2):
        return "an acceptable balance sheet"
    return "a balance sheet that requires close monitoring"


def _profitability_phrase(net_margin: float | None, free_cash_flow: float | None) -> str:
    """Summarize profitability and cash generation."""
    if net_margin is not None and net_margin > 0 and free_cash_flow is not None and free_cash_flow > 0:
        return "positive profitability with cash generation"
    if net_margin is not None and net_margin > 0:
        return "positive profitability, though cash generation needs confirmation"
    return "profitability or cash generation that needs improvement"
