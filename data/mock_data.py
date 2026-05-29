"""
Mock data generators for StockInsightPro.

All data is synthetic placeholder content for UI development only.
TODO: Replace with real API / database integrations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils.constants import DEFAULT_TICKER

# Sample tickers for dropdowns and watchlists
AVAILABLE_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "UNH"]

SECTOR_LABELS = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Communication Services",
    "AMZN": "Consumer Cyclical",
    "NVDA": "Technology",
    "META": "Communication Services",
    "TSLA": "Consumer Cyclical",
    "JPM": "Financial Services",
    "V": "Financial Services",
    "UNH": "Healthcare",
}


def get_quote_summary(ticker: str = DEFAULT_TICKER) -> dict:
    """Return mock quote summary for dashboard cards."""
    # TODO: Fetch live quote from market data provider
    base_prices = {
        "AAPL": 189.42,
        "MSFT": 415.28,
        "GOOGL": 171.56,
        "AMZN": 178.35,
        "NVDA": 875.12,
        "META": 498.67,
        "TSLA": 248.91,
        "JPM": 198.44,
        "V": 278.33,
        "UNH": 512.18,
    }
    price = base_prices.get(ticker, 150.0)
    change_pct = np.random.uniform(-2.5, 2.5)
    return {
        "ticker": ticker,
        "name": f"{ticker} Inc. (Mock)",
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "change_abs": round(price * change_pct / 100, 2),
        "volume": int(np.random.uniform(20_000_000, 80_000_000)),
        "market_cap": round(price * np.random.uniform(15e9, 25e9) / 1e9, 2),
        "sector": SECTOR_LABELS.get(ticker, "Unknown"),
    }


def get_price_history(ticker: str = DEFAULT_TICKER, days: int = 90) -> pd.DataFrame:
    """Generate mock OHLCV price history."""
    # TODO: Load historical prices from data provider
    np.random.seed(hash(ticker) % 2**32)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    base = 100 + hash(ticker) % 50
    returns = np.random.normal(0.0008, 0.015, days)
    close = base * np.cumprod(1 + returns)
    high = close * (1 + np.random.uniform(0.005, 0.02, days))
    low = close * (1 - np.random.uniform(0.005, 0.02, days))
    open_ = close * (1 + np.random.uniform(-0.01, 0.01, days))
    volume = np.random.randint(5_000_000, 50_000_000, days)
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": np.round(open_, 2),
            "High": np.round(high, 2),
            "Low": np.round(low, 2),
            "Close": np.round(close, 2),
            "Volume": volume,
        }
    )


def get_moving_averages_df(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock moving average values."""
    # TODO: Calculate SMA/EMA from real price series
    prices = get_price_history(ticker, 30)
    return pd.DataFrame(
        {
            "Period": ["SMA 20", "SMA 50", "SMA 200", "EMA 12", "EMA 26"],
            "Value": [
                round(prices["Close"].tail(20).mean(), 2),
                round(prices["Close"].mean(), 2),
                round(prices["Close"].mean() * 0.98, 2),
                round(prices["Close"].tail(12).mean(), 2),
                round(prices["Close"].tail(26).mean() * 1.01, 2),
            ],
            "Signal": ["Bullish", "Neutral", "Bullish", "Bullish", "Neutral"],
        }
    )


def get_rsi_series(ticker: str = DEFAULT_TICKER, days: int = 60) -> pd.DataFrame:
    """Mock RSI time series (placeholder values)."""
    # TODO: Implement RSI calculation
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    rsi = 50 + 15 * np.sin(np.linspace(0, 4 * np.pi, days)) + np.random.normal(0, 3, days)
    rsi = np.clip(rsi, 20, 80)
    return pd.DataFrame({"Date": dates, "RSI": np.round(rsi, 2)})


def get_macd_series(ticker: str = DEFAULT_TICKER, days: int = 60) -> pd.DataFrame:
    """Mock MACD components."""
    # TODO: Implement MACD calculation
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    macd = np.random.normal(0, 1, days).cumsum() * 0.1
    signal = macd * 0.8 + np.random.normal(0, 0.05, days)
    hist = macd - signal
    return pd.DataFrame(
        {
            "Date": dates,
            "MACD": np.round(macd, 3),
            "Signal": np.round(signal, 3),
            "Histogram": np.round(hist, 3),
        }
    )


def get_support_resistance(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock support and resistance levels."""
    # TODO: Detect levels from price action
    quote = get_quote_summary(ticker)
    p = quote["price"]
    return pd.DataFrame(
        {
            "Level Type": ["Resistance 2", "Resistance 1", "Pivot", "Support 1", "Support 2"],
            "Price": [round(level, 2) for level in [p * 1.08, p * 1.04, p, p * 0.96, p * 0.92]],
            "Strength": ["Strong", "Moderate", "Key", "Moderate", "Strong"],
        }
    )


def get_volume_analysis(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock volume statistics."""
    prices = get_price_history(ticker, 20)
    return pd.DataFrame(
        {
            "Metric": ["Avg Volume (20d)", "Today Volume", "Volume Ratio", "OBV Trend"],
            "Value": [
                f"{prices['Volume'].mean():,.0f}",
                f"{prices['Volume'].iloc[-1]:,.0f}",
                f"{prices['Volume'].iloc[-1] / prices['Volume'].mean():.2f}x",
                "Rising (mock)",
            ],
        }
    )


def get_candlestick_patterns() -> pd.DataFrame:
    """Mock detected candlestick patterns."""
    # TODO: Implement pattern recognition
    return pd.DataFrame(
        {
            "Pattern": ["Bullish Engulfing", "Hammer", "Doji", "Morning Star"],
            "Date": ["2024-05-15", "2024-05-10", "2024-05-08", "2024-05-02"],
            "Reliability": ["High", "Medium", "Low", "High"],
            "Direction": ["Bullish", "Bullish", "Neutral", "Bullish"],
        }
    )


def get_financial_statement(statement_type: str, ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock income / balance / cash flow tables."""
    # TODO: Pull from financial data API
    periods = ["FY 2021", "FY 2022", "FY 2023", "TTM"]
    if statement_type == "income":
        rows = ["Revenue", "Cost of Revenue", "Gross Profit", "Operating Income", "Net Income"]
        mult = [1.0, 0.55, 0.45, 0.28, 0.22]
    elif statement_type == "balance":
        rows = ["Total Assets", "Total Liabilities", "Shareholders Equity", "Cash", "Total Debt"]
        mult = [1.0, 0.62, 0.38, 0.12, 0.25]
    else:
        rows = ["Operating Cash Flow", "Investing Cash Flow", "Financing Cash Flow", "Free Cash Flow"]
        mult = [0.25, -0.08, -0.12, 0.18]

    base = 80_000 + hash(ticker) % 40_000
    data = {p: [round(base * m * (1 + 0.1 * i), 0) for i, m in enumerate(mult)] for p in periods}
    return pd.DataFrame(data, index=rows)


def get_latest_earnings_release(ticker: str = DEFAULT_TICKER) -> dict:
    """Mock latest earnings release summary."""
    reported_eps = 2.18 + (hash(ticker) % 18) / 100
    estimated_eps = reported_eps - 0.07
    surprise = reported_eps - estimated_eps
    return {
        "ticker": ticker,
        "reported_date": "2026-04-25",
        "fiscal_date_ending": "2026-03-31",
        "reported_eps": round(reported_eps, 2),
        "estimated_eps": round(estimated_eps, 2),
        "surprise": round(surprise, 2),
        "surprise_percentage": round((surprise / estimated_eps) * 100, 2),
        "report_time": "post-market",
        "source": "Mock fallback",
    }


def get_earnings_calendar(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock upcoming earnings calendar rows."""
    today = pd.Timestamp.today().normalize()
    report_dates = pd.bdate_range(start=today + pd.Timedelta(days=12), periods=3, freq="65B")
    rows = []
    for index, report_date in enumerate(report_dates):
        fiscal_date = report_date - pd.offsets.QuarterEnd(startingMonth=3)
        rows.append(
            {
                "Ticker": ticker,
                "Company": f"{ticker} Inc. (Mock)",
                "Report Date": report_date.strftime("%Y-%m-%d"),
                "Fiscal Date Ending": fiscal_date.strftime("%Y-%m-%d"),
                "EPS Estimate": f"{2.15 + index * 0.08:.2f}",
                "Currency": "USD",
            }
        )
    calendar = pd.DataFrame(rows)
    calendar.attrs["source"] = "Mock fallback"
    calendar.attrs["horizon"] = "12month"
    return calendar


def get_valuation_ratios(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock valuation ratio table."""
    return pd.DataFrame(
        {
            "Ratio": ["P/E (TTM)", "Forward P/E", "P/S", "P/B", "EV/EBITDA", "PEG"],
            "Value": [28.4, 24.1, 7.2, 12.5, 18.3, 1.4],
            "Sector Avg": [25.1, 22.0, 5.8, 8.2, 15.1, 1.2],
            "Assessment": ["Above", "Above", "Above", "Above", "Above", "Fair"],
        }
    )


def get_growth_metrics() -> pd.DataFrame:
    """Mock growth metrics."""
    return pd.DataFrame(
        {
            "Metric": ["Revenue Growth (YoY)", "EPS Growth (YoY)", "FCF Growth", "3Y Revenue CAGR"],
            "Value": ["12.4%", "18.2%", "9.8%", "11.5%"],
            "Trend": ["↑ Improving", "↑ Improving", "→ Stable", "↑ Improving"],
        }
    )


def get_profitability_metrics() -> pd.DataFrame:
    """Mock profitability metrics."""
    return pd.DataFrame(
        {
            "Metric": ["Gross Margin", "Operating Margin", "Net Margin", "ROE", "ROA"],
            "Value": ["42.1%", "28.5%", "22.3%", "31.2%", "18.7%"],
            "vs Sector": ["Above", "Above", "Above", "Above", "Above"],
        }
    )


def get_debt_liquidity() -> pd.DataFrame:
    """Mock debt and liquidity metrics."""
    return pd.DataFrame(
        {
            "Metric": ["Debt/Equity", "Current Ratio", "Quick Ratio", "Interest Coverage", "Net Debt/EBITDA"],
            "Value": [1.42, 1.85, 1.52, 12.4, 1.8],
            "Rating": ["Moderate", "Healthy", "Healthy", "Strong", "Moderate"],
        }
    )


def get_news_items(ticker: str = DEFAULT_TICKER, limit: int = 8) -> pd.DataFrame:
    """Mock news headlines."""
    # TODO: Integrate news API
    limit = max(int(limit), 1)
    headline_templates = [
        f"{ticker} beats earnings expectations in Q1",
        f"Analysts raise price target on {ticker}",
        f"{ticker} announces new product line expansion",
        "Fed signals cautious stance on rate cuts",
        f"Sector rotation boosts {ticker} peers",
        f"{ticker} CEO discusses long-term AI strategy",
        "Market volatility rises amid geopolitical headlines",
        f"Institutional investors increase {ticker} holdings",
    ]
    headlines = [headline_templates[index % len(headline_templates)] for index in range(limit)]
    return pd.DataFrame(
        {
            "Date": pd.date_range(end=pd.Timestamp.today(), periods=limit, freq="D")[::-1],
            "Headline": headlines,
            "Source": np.random.choice(["Reuters", "Bloomberg", "CNBC", "WSJ"], limit),
            "Sentiment": np.random.choice(["Positive", "Neutral", "Negative"], limit, p=[0.5, 0.35, 0.15]),
        }
    )


def get_sentiment_scores() -> pd.DataFrame:
    """Mock sentiment breakdown."""
    return pd.DataFrame(
        {
            "Source": ["News", "Social", "Analyst", "Insider", "Composite"],
            "Score": [72, 65, 78, 55, 70],
            "Trend": ["↑", "→", "↑", "↓", "↑"],
        }
    )


def get_insider_transactions(ticker: str = DEFAULT_TICKER, limit: int = 20) -> pd.DataFrame:
    """Mock insider transaction table."""
    names = [
        "Alex Morgan",
        "Jordan Lee",
        "Casey Rivera",
        "Taylor Chen",
        "Riley Patel",
        "Morgan Smith",
    ]
    titles = ["CEO", "CFO", "Director", "COO", "General Counsel", "Chief Product Officer"]
    transaction_types = ["Acquisition", "Disposal", "Disposal", "Acquisition", "Disposal", "Acquisition"]
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=max(limit, len(names)))[::-1]
    rows = []
    for index in range(min(limit, len(names))):
        shares = int(1_000 + (index + 1) * 750)
        share_price = 125 + index * 6.5
        rows.append(
            {
                "Date": dates[index].strftime("%Y-%m-%d"),
                "Executive": names[index],
                "Title": titles[index],
                "Security": "Common Stock",
                "Type": transaction_types[index],
                "Shares": f"{shares:,.0f}",
                "Share Price": f"${share_price:.2f}",
                "Value": f"${shares * share_price:,.0f}",
            }
        )

    insider_df = pd.DataFrame(rows)
    insider_df.attrs["source"] = "Mock fallback"
    return insider_df


def get_key_risks() -> list[str]:
    """Mock key risk bullets."""
    return [
        "Regulatory scrutiny in primary operating markets",
        "Supply chain concentration with single-region exposure",
        "Competitive pressure from emerging low-cost entrants",
        "Foreign exchange headwinds on international revenue",
    ]


def get_market_catalysts() -> list[str]:
    """Mock market catalyst bullets."""
    return [
        "Upcoming earnings release (placeholder date)",
        "Product launch event scheduled next quarter",
        "Potential index rebalancing inclusion",
        "Share buyback program expansion announcement",
    ]


def get_ai_summary_placeholder(ticker: str) -> str:
    """Placeholder AI-generated summary text."""
    # TODO: Connect to LLM for real summarization
    return (
        f"**AI Summary (Placeholder)** — {ticker} shows mixed near-term signals. "
        "Technical indicators suggest moderate momentum with neutral RSI. "
        "Fundamental metrics remain above sector averages on profitability. "
        "News sentiment is cautiously positive. This is mock content only."
    )


def get_options_chain(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock options chain around spot price."""
    # TODO: Replace with live options chain API including greeks and NBBO quotes
    quote = get_quote_summary(ticker)
    spot = quote["price"]
    strikes = np.round(np.arange(spot * 0.85, spot * 1.16, spot * 0.03), 2)
    rows = []
    for strike in strikes:
        moneyness = (spot - strike) / spot
        rows.append(
            {
                "Strike": strike,
                "Call Bid": round(max(0.4, spot * 0.035 + moneyness * spot * 0.35), 2),
                "Call Ask": round(max(0.6, spot * 0.04 + moneyness * spot * 0.35), 2),
                "Call OI": int(np.random.uniform(1_000, 18_000)),
                "Put Bid": round(max(0.4, spot * 0.035 - moneyness * spot * 0.35), 2),
                "Put Ask": round(max(0.6, spot * 0.04 - moneyness * spot * 0.35), 2),
                "Put OI": int(np.random.uniform(1_000, 18_000)),
                "IV": round(np.random.uniform(18, 55), 2),
                "Delta": round(np.clip(0.5 + moneyness * 2.5, 0.05, 0.95), 2),
            }
        )
    return pd.DataFrame(rows)


def get_options_kpis(ticker: str = DEFAULT_TICKER) -> dict:
    """Mock options intelligence KPI summary."""
    # TODO: Calculate from full option surface, expirations, and historical IV
    return {
        "Put/Call Ratio": round(np.random.uniform(0.6, 1.4), 2),
        "IV Rank": round(np.random.uniform(25, 75), 2),
        "30D IV": round(np.random.uniform(22, 48), 2),
        "Max Pain": round(get_quote_summary(ticker)["price"] * np.random.uniform(0.96, 1.04), 2),
    }


def get_open_interest_by_strike(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock open interest by strike."""
    # TODO: Aggregate live open interest across selected expirations
    chain = get_options_chain(ticker)
    return chain[["Strike", "Call OI", "Put OI"]].copy()


def get_put_call_ratio_history(days: int = 30) -> pd.DataFrame:
    """Mock put/call ratio time series."""
    # TODO: Persist historical options volume and OI ratios
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    ratio = 0.95 + 0.25 * np.sin(np.linspace(0, 3 * np.pi, days)) + np.random.normal(0, 0.08, days)
    return pd.DataFrame({"Date": dates, "Put/Call Ratio": np.round(np.clip(ratio, 0.4, 1.8), 2)})


def get_iv_term_structure(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock implied volatility by expiration."""
    # TODO: Build IV term structure from option mid prices and greeks
    expirations = ["7D", "14D", "30D", "45D", "60D", "90D", "180D"]
    base_iv = np.random.uniform(25, 38)
    iv = base_iv + np.array([6, 4, 2, 1, 0, -1, -2]) + np.random.normal(0, 1.2, len(expirations))
    return pd.DataFrame({"Expiration": expirations, "Implied Volatility": np.round(iv, 2)})


def get_iv_rank_history(days: int = 52) -> pd.DataFrame:
    """Mock IV rank trend."""
    # TODO: Compare current IV to one-year IV range
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    rank = 45 + 20 * np.sin(np.linspace(0, 2 * np.pi, days)) + np.random.normal(0, 5, days)
    return pd.DataFrame({"Date": dates, "IV Rank": np.round(np.clip(rank, 0, 100), 2)})


def get_gamma_exposure(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Mock gamma exposure by strike."""
    # TODO: Estimate dealer gamma exposure from live greeks, OI, and contract multipliers
    quote = get_quote_summary(ticker)
    spot = quote["price"]
    strikes = np.round(np.arange(spot * 0.86, spot * 1.15, spot * 0.025), 2)
    exposure = np.random.normal(0, 1.5, len(strikes)).cumsum()
    exposure = exposure - exposure.mean()
    return pd.DataFrame({"Strike": strikes, "Gamma Exposure ($MM)": np.round(exposure, 2)})


def get_dealer_positioning() -> pd.DataFrame:
    """Mock dealer positioning summary."""
    # TODO: Infer positioning from GEX, vanna, charm, and flow data
    return pd.DataFrame(
        {
            "Metric": ["Net Gamma", "Net Delta", "Vanna Risk", "Charm Pressure", "Regime"],
            "Value": ["+1.8B", "-420M", "Moderate", "Positive", "Long Gamma"],
            "Interpretation": ["Stabilizing", "Dealer short delta", "Watch IV moves", "Supportive", "Mean-reversion bias"],
        }
    )


def get_options_flow() -> pd.DataFrame:
    """Mock options flow tape."""
    # TODO: Stream unusual options activity and classify opening vs closing flow
    return pd.DataFrame(
        {
            "Time": ["09:38", "10:12", "10:47", "11:25", "13:03", "14:18"],
            "Side": ["CALL", "PUT", "CALL", "CALL", "PUT", "CALL"],
            "Strike": [190, 185, 200, 195, 180, 205],
            "Expiry": ["7D", "14D", "30D", "7D", "45D", "60D"],
            "Premium": ["1.2M", "840K", "2.4M", "690K", "1.1M", "760K"],
            "Sentiment": ["Bullish", "Hedge", "Bullish", "Speculative", "Bearish", "Upside"],
        }
    )


def get_options_ai_conclusion(ticker: str = DEFAULT_TICKER) -> str:
    """Mock AI-generated options interpretation."""
    # TODO: Connect options surface analytics to AI narrative generation
    return (
        f"**AI Options Interpretation (Placeholder)** — {ticker} options activity suggests a balanced but "
        "slightly constructive setup. Mock open interest is concentrated near the spot-adjacent strikes, "
        "while implied volatility remains mid-range versus its historical band. Dealer positioning appears "
        "stabilizing in this placeholder view. This is synthetic content only and not investment advice."
    )


def get_watchlist() -> pd.DataFrame:
    """Default mock watchlist."""
    rows = []
    for t in ["AAPL", "MSFT", "NVDA", "GOOGL"]:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": round(q["price"], 2),
                "Change %": round(q["change_pct"], 2),
                "Sector": q["sector"],
                "Alert": "—",
            }
        )
    return pd.DataFrame(rows)


def get_market_overview() -> pd.DataFrame:
    """Mock indices for home dashboard."""
    return pd.DataFrame(
        {
            "Index": ["S&P 500", "NASDAQ", "DOW", "VIX"],
            "Value": [5234.2, 16452.3, 39127.5, 14.8],
            "Change %": [0.4, 0.7, 0.2, -2.3],
        }
    )


def get_sector_performance() -> pd.DataFrame:
    """Return mock sector performance snapshot."""
    sectors = [
        "Technology",
        "Communication Services",
        "Consumer Cyclical",
        "Financial Services",
        "Healthcare",
        "Industrials",
        "Energy",
        "Consumer Defensive",
        "Utilities",
        "Real Estate",
        "Materials",
    ]
    one_day = np.array([1.35, 0.82, -0.34, 0.44, -0.18, 0.28, -1.12, 0.16, -0.42, -0.71, 0.09])
    one_week = np.array([2.84, 1.92, 0.48, 1.11, -0.62, 0.74, -2.45, 0.31, -0.88, -1.36, 0.22])
    one_month = np.array([6.15, 4.21, 1.35, 2.74, -0.95, 1.88, -4.16, 0.76, -1.42, -2.71, 0.58])
    ytd = np.array([18.4, 15.2, 8.6, 9.9, 4.8, 6.7, -3.2, 5.1, 2.2, -1.8, 3.4])
    return pd.DataFrame(
        {
            "Sector": sectors,
            "1D %": one_day,
            "1W %": one_week,
            "1M %": one_month,
            "YTD %": ytd,
            "1Y %": np.array([31.6, 24.8, 13.5, 16.2, 8.4, 11.9, -6.1, 7.6, 4.3, -2.8, 6.2]),
            "3Y %": np.array([78.4, 42.5, 29.1, 35.7, 20.6, 24.8, 11.2, 15.9, 10.4, -8.5, 13.7]),
            "Momentum": ["Bullish" if value > 1 else "Neutral" if value > -1 else "Bearish" for value in one_month],
        }
    )


def get_sector_rotation_history(days: int = 60) -> pd.DataFrame:
    """Return mock RSI history for major sector groups."""
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    x = np.linspace(0, 3 * np.pi, days)
    return pd.DataFrame(
        {
            "Date": dates,
            "Technology (XLK)": np.round(55 + np.sin(x) * 9 + np.linspace(0, 7, days), 2),
            "Financial Services (XLF)": np.round(52 + np.sin(x + 0.8) * 7 + np.linspace(0, 4, days), 2),
            "Healthcare (XLV)": np.round(49 + np.cos(x) * 6 + np.linspace(0, 2, days), 2),
            "Energy (XLE)": np.round(47 + np.sin(x + 1.6) * 10 + np.linspace(-2, 3, days), 2),
            "Utilities (XLU)": np.round(45 + np.cos(x + 0.5) * 5 + np.linspace(1, 0, days), 2),
        }
    )


def get_market_breadth() -> pd.DataFrame:
    """Return mock market breadth indicators."""
    return pd.DataFrame(
        {
            "Indicator": [
                "Advancers / Decliners",
                "Stocks above 50D MA",
                "Stocks above 200D MA",
                "New highs / New lows",
                "Up volume ratio",
            ],
            "Value": ["1.42x", "62.5%", "58.1%", "2.15x", "57.8%"],
            "Signal": ["Positive", "Positive", "Neutral", "Positive", "Neutral"],
        }
    )


def get_top_movers() -> pd.DataFrame:
    """Mock top gainers/losers."""
    return pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD", "TSLA", "INTC", "BA"],
            "Change %": [4.8, 3.2, 2.9, -2.4, -1.9],
            "Volume": ["85.2M", "62.1M", "98.4M", "45.3M", "12.8M"],
        }
    )
