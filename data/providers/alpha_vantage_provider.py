"""Alpha Vantage market data provider.

This adapter is intentionally UI-free. It returns normalized Python/Pandas
objects and raises provider-specific errors to be handled by services.
"""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
import json
from typing import Any

import pandas as pd

from utils.config import get_alpha_vantage_api_key
from utils.helpers import format_large_number

BASE_URL = "https://www.alphavantage.co/query"
CACHE_TTL_SECONDS = 300
MIN_REQUEST_INTERVAL_SECONDS = 0.25

INDEX_SERIES = [
    {"label": "S&P 500", "symbol": "SPX", "proxy_symbol": "SPY"},
    {"label": "Nasdaq Composite", "symbol": "COMP", "proxy_symbol": "ONEQ"},
    {"label": "Dow Jones", "symbol": "DJI", "proxy_symbol": "DIA"},
    {"label": "Russell 2000", "symbol": "RUT", "proxy_symbol": "IWM"},
    {"label": "Volatility", "symbol": "VIX", "proxy_symbol": "VXX"},
]

INDEX_PROXIES = [(item["label"], item["proxy_symbol"]) for item in INDEX_SERIES]

_CACHE: dict[tuple[tuple[str, str], ...], tuple[float, dict[str, Any]]] = {}
_LAST_REQUEST_AT = 0.0


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage cannot return usable data."""


def is_configured() -> bool:
    """Return True when an Alpha Vantage API key is available."""
    return get_alpha_vantage_api_key() is not None


def _request(params: dict[str, str]) -> dict[str, Any]:
    """Call Alpha Vantage with a small in-memory TTL cache."""
    global _LAST_REQUEST_AT

    api_key = get_alpha_vantage_api_key()
    if not api_key:
        raise AlphaVantageError("Alpha Vantage API key is not configured.")

    request_params = {**params, "apikey": api_key}
    cache_key = tuple(sorted(request_params.items()))
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    elapsed = time.time() - _LAST_REQUEST_AT
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    url = f"{BASE_URL}?{urllib.parse.urlencode(request_params)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = response.read().decode("utf-8")
        _LAST_REQUEST_AT = time.time()
    except Exception as exc:  # noqa: BLE001 - provider boundary converts all failures
        raise AlphaVantageError(f"Alpha Vantage request failed: {exc}") from exc

    try:
        data = json.loads(payload)
    except Exception as exc:  # noqa: BLE001
        raise AlphaVantageError("Alpha Vantage returned invalid JSON.") from exc

    if "Error Message" in data:
        raise AlphaVantageError(data["Error Message"])
    if "Note" in data or "Information" in data:
        raise AlphaVantageError(data.get("Note") or data.get("Information"))

    _CACHE[cache_key] = (time.time(), data)
    return data


def _parse_float(value: str | float | int, default: float = 0.0) -> float:
    """Parse Alpha Vantage numeric fields."""
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return default


def _parse_optional_float(value: str | float | int | None) -> float | None:
    """Parse optional Alpha Vantage numeric fields."""
    if value in (None, "", "None", "none", "null"):
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def get_quote(ticker: str) -> dict:
    """Return normalized real-time/delayed quote data."""
    data = _request({"function": "GLOBAL_QUOTE", "symbol": ticker})
    quote = data.get("Global Quote", {})
    if not quote:
        raise AlphaVantageError(f"No quote returned for {ticker}.")

    price = _parse_float(quote.get("05. price"))
    previous_close = _parse_float(quote.get("08. previous close"), default=price)
    change_abs = _parse_float(quote.get("09. change"), default=price - previous_close)
    change_pct = _parse_float(quote.get("10. change percent"))
    volume = int(_parse_float(quote.get("06. volume")))

    return {
        "ticker": ticker,
        "name": ticker,
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "change_abs": round(change_abs, 2),
        "volume": volume,
    }


def get_company_overview(ticker: str) -> dict:
    """Return normalized company profile data from Alpha Vantage OVERVIEW."""
    data = _request({"function": "OVERVIEW", "symbol": ticker})
    if not data or not data.get("Symbol"):
        raise AlphaVantageError(f"No company overview returned for {ticker}.")

    market_cap = _parse_float(data.get("MarketCapitalization")) / 1_000_000_000
    return {
        "ticker": data.get("Symbol", ticker),
        "name": data.get("Name") or ticker,
        "description": data.get("Description") or "No company description available.",
        "exchange": data.get("Exchange") or "Unknown",
        "currency": data.get("Currency") or "USD",
        "country": data.get("Country") or "Unknown",
        "sector": data.get("Sector") or "Unknown",
        "industry": data.get("Industry") or "Unknown",
        "market_cap": round(market_cap, 2),
        "pe_ratio": _parse_optional_float(data.get("PERatio")),
        "peg_ratio": _parse_optional_float(data.get("PEGRatio")),
        "beta": _parse_optional_float(data.get("Beta")),
        "dividend_yield": _parse_optional_float(data.get("DividendYield")),
        "profit_margin": _parse_optional_float(data.get("ProfitMargin")),
        "52_week_high": _parse_optional_float(data.get("52WeekHigh")),
        "52_week_low": _parse_optional_float(data.get("52WeekLow")),
    }


def get_price_history(ticker: str, periods: int = 90, timeframe: str = "Daily") -> pd.DataFrame:
    """Return OHLCV history for a ticker across Alpha Vantage timeframes."""
    timeframe_key = timeframe.lower()
    if timeframe_key in {"weekly", "monthly"}:
        return _get_resampled_adjusted_history(ticker, periods, timeframe_key)

    request_params, series_key = _history_request(ticker, periods, timeframe)
    data = _request(request_params)
    series = data.get(series_key)
    if not series:
        raise AlphaVantageError(f"No {timeframe.lower()} time series returned for {ticker}.")

    rows = _normalize_history_rows(series)
    history = pd.DataFrame(rows).sort_values("Date").tail(periods).reset_index(drop=True)
    history.attrs["source"] = f"Alpha Vantage {timeframe} (adjusted OHLC)"
    return history


def _normalize_history_rows(series: dict[str, dict[str, str]]) -> list[dict]:
    """Normalize Alpha Vantage OHLCV rows, adjusting OHLC when adjusted close exists."""
    rows = []
    for date_str, values in series.items():
        open_price = _parse_float(values.get("1. open"))
        high_price = _parse_float(values.get("2. high"))
        low_price = _parse_float(values.get("3. low"))
        close_price = _parse_float(values.get("4. close"))
        adjusted_close = _parse_float(values.get("5. adjusted close"), default=close_price)
        adjustment_factor = adjusted_close / close_price if close_price else 1
        rows.append(
            {
                "Date": pd.to_datetime(date_str),
                "Open": round(open_price * adjustment_factor, 2),
                "High": round(high_price * adjustment_factor, 2),
                "Low": round(low_price * adjustment_factor, 2),
                "Close": round(adjusted_close, 2),
                "Volume": int(_parse_float(values.get("6. volume", values.get("5. volume")))),
            }
        )
    return rows


def _get_resampled_adjusted_history(ticker: str, periods: int, timeframe: str) -> pd.DataFrame:
    """Build weekly/monthly candles from adjusted daily data to handle split periods cleanly."""
    lookback_days = max(periods * (8 if timeframe == "weekly" else 35), 140)
    request_params, series_key = _history_request(ticker, lookback_days, "Daily")
    data = _request(request_params)
    series = data.get(series_key)
    if not series:
        raise AlphaVantageError(f"No daily time series returned for {ticker}.")

    daily = pd.DataFrame(_normalize_history_rows(series)).sort_values("Date").set_index("Date")
    rule = "W-FRI" if timeframe == "weekly" else "ME"
    history = (
        daily.resample(rule)
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna()
        .tail(periods)
        .reset_index()
    )
    history[["Open", "High", "Low", "Close"]] = history[["Open", "High", "Low", "Close"]].round(2)
    history["Volume"] = history["Volume"].astype(int)
    history.attrs["source"] = f"Alpha Vantage {timeframe.title()} (resampled adjusted daily OHLC)"
    return history


def get_daily_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """Return daily OHLCV history for a ticker."""
    return get_price_history(ticker, periods=days, timeframe="Daily")


def _history_request(ticker: str, periods: int, timeframe: str) -> tuple[dict[str, str], str]:
    """Build Alpha Vantage request params and response series key."""
    timeframe_key = timeframe.lower()
    if timeframe_key == "daily":
        return (
            {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": ticker,
                "outputsize": "compact" if periods <= 100 else "full",
            },
            "Time Series (Daily)",
        )
    if timeframe_key == "weekly":
        return (
            {"function": "TIME_SERIES_WEEKLY_ADJUSTED", "symbol": ticker},
            "Weekly Adjusted Time Series",
        )
    if timeframe_key == "monthly":
        return (
            {"function": "TIME_SERIES_MONTHLY_ADJUSTED", "symbol": ticker},
            "Monthly Adjusted Time Series",
        )
    if timeframe_key in {"hourly", "hour", "60min", "60-minute"}:
        return (
            {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": ticker,
                "interval": "60min",
                "outputsize": "compact" if periods <= 100 else "full",
                "adjusted": "true",
                "extended_hours": "false",
            },
            "Time Series (60min)",
        )
    raise AlphaVantageError(f"Unsupported timeframe: {timeframe}.")


def get_index_snapshot(label: str, symbol: str) -> dict:
    """Return the latest index value from Alpha Vantage INDEX_DATA."""
    data = _request({"function": "INDEX_DATA", "symbol": symbol, "interval": "daily"})
    rows = data.get("data")
    if not rows:
        series = data.get("Time Series (Daily)", {})
        rows = [
            {"date": date_str, **values}
            for date_str, values in series.items()
        ]
    if not rows or len(rows) < 2:
        raise AlphaVantageError(f"No index data returned for {symbol}.")

    rows = sorted(rows, key=lambda row: row.get("date") or row.get("timestamp") or row.get("time") or "")
    latest = rows[-1]
    previous = rows[-2]
    value = _parse_float(latest.get("close") or latest.get("4. close"))
    previous_close = _parse_float(previous.get("close") or previous.get("4. close"))
    change_pct = ((value - previous_close) / previous_close * 100) if previous_close else 0
    return {
        "Index": label,
        "Symbol": symbol,
        "Value": round(value, 2),
        "Change %": round(change_pct, 2),
        "Source": "Alpha Vantage Index Data",
    }


def get_market_overview() -> pd.DataFrame:
    """Return index dashboard rows using Alpha Vantage index data with explicit proxy fallback."""
    rows = []
    use_index_data = True
    for item in INDEX_SERIES:
        if use_index_data:
            try:
                rows.append(get_index_snapshot(item["label"], item["symbol"]))
                continue
            except AlphaVantageError:
                use_index_data = False

        quote = get_quote(item["proxy_symbol"])
        rows.append(
            {
                "Index": f"{item['label']} Proxy",
                "Symbol": item["proxy_symbol"],
                "Value": quote["price"],
                "Change %": quote["change_pct"],
                "Source": f"ETF proxy fallback ({item['proxy_symbol']})",
            }
        )
    return pd.DataFrame(rows)


def get_top_movers(limit: int = 10) -> dict[str, Any]:
    """Return top gainers and losers from Alpha Vantage."""
    data = _request({"function": "TOP_GAINERS_LOSERS"})
    gainers = data.get("top_gainers", [])
    losers = data.get("top_losers", [])
    if not gainers or not losers:
        raise AlphaVantageError("No top movers returned.")

    return {
        "last_updated": data.get("last_updated", "Unknown"),
        "source": "Alpha Vantage Top Gainers/Losers",
        "gainers": _normalize_movers(gainers[:limit], "Gainer"),
        "losers": _normalize_movers(losers[:limit], "Loser"),
    }


def _normalize_movers(rows: list[dict[str, Any]], move_type: str) -> pd.DataFrame:
    """Normalize Alpha Vantage mover rows for Streamlit display."""
    normalized_rows = []
    for row in rows:
        normalized_rows.append(
            {
                "Ticker": row.get("ticker", ""),
                "Price": round(_parse_float(row.get("price")), 2),
                "Change": round(_parse_float(row.get("change_amount")), 2),
                "Change %": round(_parse_float(row.get("change_percentage")), 2),
                "Volume": format_large_number(_parse_float(row.get("volume"))),
                "Type": move_type,
            }
        )
    return pd.DataFrame(normalized_rows)


def get_news_sentiment(ticker: str, limit: int = 8) -> pd.DataFrame:
    """Return recent ticker news with normalized sentiment labels."""
    data = _request(
        {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "sort": "LATEST",
            "limit": str(limit),
        }
    )
    feed = data.get("feed", [])
    if not feed:
        raise AlphaVantageError(f"No news returned for {ticker}.")

    rows = []
    for item in feed[:limit]:
        label, score = _ticker_news_sentiment(item, ticker)
        rows.append(
            {
                "Published": _format_news_timestamp(item.get("time_published")),
                "Headline": item.get("title", "Untitled"),
                "Source": item.get("source", "Unknown"),
                "Sentiment": label,
                "Score": round(score, 3) if score is not None else None,
                "URL": item.get("url", ""),
            }
        )

    news = pd.DataFrame(rows)
    news.attrs["source"] = "Alpha Vantage News Sentiment"
    return news


def _ticker_news_sentiment(item: dict[str, Any], ticker: str) -> tuple[str, float | None]:
    """Return ticker-specific sentiment when available, otherwise overall sentiment."""
    ticker = ticker.upper()
    for sentiment in item.get("ticker_sentiment", []):
        if sentiment.get("ticker", "").upper() == ticker:
            score = _parse_optional_float(sentiment.get("ticker_sentiment_score"))
            return _normalize_sentiment_label(sentiment.get("ticker_sentiment_label")), score

    score = _parse_optional_float(item.get("overall_sentiment_score"))
    return _normalize_sentiment_label(item.get("overall_sentiment_label")), score


def _normalize_sentiment_label(label: str | None) -> str:
    """Map Alpha Vantage labels to simple UI sentiment states."""
    normalized = (label or "Neutral").lower()
    if "bullish" in normalized:
        return "Positive"
    if "bearish" in normalized:
        return "Negative"
    return "Neutral"


def _format_news_timestamp(raw_timestamp: str | None) -> str:
    """Format Alpha Vantage news timestamps."""
    if not raw_timestamp:
        return "Unknown"
    try:
        return pd.to_datetime(raw_timestamp, format="%Y%m%dT%H%M%S").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw_timestamp


FINANCIAL_STATEMENT_CONFIG = {
    "income": {
        "function": "INCOME_STATEMENT",
        "title": "Income Statement",
        "rows": [
            ("totalRevenue", "Revenue", "money"),
            ("costOfRevenue", "Cost of Revenue", "money"),
            ("grossProfit", "Gross Profit", "money"),
            ("operatingExpenses", "Operating Expenses", "money"),
            ("operatingIncome", "Operating Income", "money"),
            ("ebit", "EBIT", "money"),
            ("ebitda", "EBITDA", "money"),
            ("incomeBeforeTax", "Income Before Tax", "money"),
            ("incomeTaxExpense", "Income Tax Expense", "money"),
            ("netIncome", "Net Income", "money"),
        ],
    },
    "balance": {
        "function": "BALANCE_SHEET",
        "title": "Balance Sheet",
        "rows": [
            ("totalAssets", "Total Assets", "money"),
            ("totalCurrentAssets", "Current Assets", "money"),
            ("cashAndCashEquivalentsAtCarryingValue", "Cash & Equivalents", "money"),
            ("inventory", "Inventory", "money"),
            ("totalLiabilities", "Total Liabilities", "money"),
            ("totalCurrentLiabilities", "Current Liabilities", "money"),
            ("shortLongTermDebtTotal", "Total Debt", "money"),
            ("totalShareholderEquity", "Shareholders' Equity", "money"),
            ("commonStockSharesOutstanding", "Shares Outstanding", "number"),
        ],
    },
    "cashflow": {
        "function": "CASH_FLOW",
        "title": "Cash Flow Statement",
        "rows": [
            ("operatingCashflow", "Operating Cash Flow", "money"),
            ("capitalExpenditures", "Capital Expenditures", "money"),
            ("cashflowFromInvestment", "Investing Cash Flow", "money"),
            ("cashflowFromFinancing", "Financing Cash Flow", "money"),
            ("dividendPayout", "Dividends Paid", "money"),
            ("proceedsFromRepurchaseOfEquity", "Share Repurchases", "money"),
            ("changeInCashAndCashEquivalents", "Change in Cash", "money"),
        ],
    },
}


def get_financial_statement(statement_type: str, ticker: str, period: str = "Annual") -> pd.DataFrame:
    """Return a normalized financial statement from Alpha Vantage fundamentals."""
    config = FINANCIAL_STATEMENT_CONFIG.get(statement_type)
    if not config:
        raise AlphaVantageError(f"Unsupported financial statement: {statement_type}.")

    data = _request({"function": config["function"], "symbol": ticker})
    report_key = "annualReports" if period.lower() == "annual" else "quarterlyReports"
    reports = data.get(report_key, [])
    if not reports:
        raise AlphaVantageError(f"No {period.lower()} {config['title'].lower()} returned for {ticker}.")

    selected_reports = reports[:5 if period.lower() == "annual" else 8]
    rows = []
    for field, label, value_type in config["rows"]:
        row = {"Metric": label}
        for report in selected_reports:
            period_label = _financial_period_label(report, period)
            row[period_label] = _format_financial_statement_value(report.get(field), value_type)
        rows.append(row)

    statement = pd.DataFrame(rows)
    statement.attrs["source"] = f"Alpha Vantage {config['title']} ({period})"
    statement.attrs["currency"] = selected_reports[0].get("reportedCurrency", "USD")
    return statement


def _financial_period_label(report: dict[str, Any], period: str) -> str:
    """Return a compact fiscal period label."""
    fiscal_date = pd.to_datetime(report.get("fiscalDateEnding"))
    if period.lower() == "annual":
        return f"FY {fiscal_date.year}"
    return f"{fiscal_date.year} Q{fiscal_date.quarter}"


def _format_financial_statement_value(value: str | float | int | None, value_type: str) -> str:
    """Format financial statement values for compact display."""
    parsed = _parse_optional_float(value)
    if parsed is None:
        return "-"
    if value_type == "number":
        return format_large_number(parsed)
    return f"{parsed / 1_000_000:,.2f}"
