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
            "Price": [p * 1.08, p * 1.04, p, p * 0.96, p * 0.92],
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


def get_news_items(ticker: str = DEFAULT_TICKER, count: int = 8) -> pd.DataFrame:
    """Mock news headlines."""
    # TODO: Integrate news API
    headlines = [
        f"{ticker} beats earnings expectations in Q1",
        f"Analysts raise price target on {ticker}",
        f"{ticker} announces new product line expansion",
        "Fed signals cautious stance on rate cuts",
        f"Sector rotation boosts {ticker} peers",
        f"{ticker} CEO discusses long-term AI strategy",
        "Market volatility rises amid geopolitical headlines",
        f"Institutional investors increase {ticker} holdings",
    ]
    return pd.DataFrame(
        {
            "Date": pd.date_range(end=pd.Timestamp.today(), periods=count, freq="D")[::-1],
            "Headline": headlines[:count],
            "Source": np.random.choice(["Reuters", "Bloomberg", "CNBC", "WSJ"], count),
            "Sentiment": np.random.choice(["Positive", "Neutral", "Negative"], count, p=[0.5, 0.35, 0.15]),
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


def get_watchlist() -> pd.DataFrame:
    """Default mock watchlist."""
    rows = []
    for t in ["AAPL", "MSFT", "NVDA", "GOOGL"]:
        q = get_quote_summary(t)
        rows.append(
            {
                "Ticker": t,
                "Price": q["price"],
                "Change %": q["change_pct"],
                "Sector": q["sector"],
                "Alert": "—",
            }
        )
    return pd.DataFrame(rows)


def get_market_overview() -> pd.DataFrame:
    """Mock indices for home dashboard."""
    return pd.DataFrame(
        {
            "Index": ["S&P 500", "NASDAQ", "DOW", "Russell 2000", "VIX"],
            "Value": [5234.18, 16452.33, 39127.45, 2048.12, 14.82],
            "Change %": [0.42, 0.68, 0.21, -0.15, -2.31],
        }
    )


def get_top_movers() -> pd.DataFrame:
    """Mock top gainers/losers."""
    return pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD", "TSLA", "INTC", "BA"],
            "Change %": [4.82, 3.15, 2.88, -2.41, -1.92],
            "Volume": ["85.2M", "62.1M", "98.4M", "45.3M", "12.8M"],
        }
    )
