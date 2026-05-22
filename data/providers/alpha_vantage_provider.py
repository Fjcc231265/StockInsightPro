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

BASE_URL = "https://www.alphavantage.co/query"
CACHE_TTL_SECONDS = 300

INDEX_PROXIES = [
    ("S&P 500", "SPY"),
    ("NASDAQ 100", "QQQ"),
    ("DOW", "DIA"),
    ("Russell 2000", "IWM"),
    ("Volatility", "VXX"),
]

_CACHE: dict[tuple[tuple[str, str], ...], tuple[float, dict[str, Any]]] = {}


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage cannot return usable data."""


def is_configured() -> bool:
    """Return True when an Alpha Vantage API key is available."""
    return get_alpha_vantage_api_key() is not None


def _request(params: dict[str, str]) -> dict[str, Any]:
    """Call Alpha Vantage with a small in-memory TTL cache."""
    api_key = get_alpha_vantage_api_key()
    if not api_key:
        raise AlphaVantageError("Alpha Vantage API key is not configured.")

    request_params = {**params, "apikey": api_key}
    cache_key = tuple(sorted(request_params.items()))
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    url = f"{BASE_URL}?{urllib.parse.urlencode(request_params)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = response.read().decode("utf-8")
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
        "name": f"{ticker} (Alpha Vantage)",
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "change_abs": round(change_abs, 2),
        "volume": volume,
    }


def get_daily_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """Return daily OHLCV history for a ticker."""
    data = _request(
        {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": "compact" if days <= 100 else "full",
        }
    )
    series = data.get("Time Series (Daily)")
    if not series:
        raise AlphaVantageError(f"No daily time series returned for {ticker}.")

    rows = []
    for date_str, values in series.items():
        rows.append(
            {
                "Date": pd.to_datetime(date_str),
                "Open": round(_parse_float(values.get("1. open")), 2),
                "High": round(_parse_float(values.get("2. high")), 2),
                "Low": round(_parse_float(values.get("3. low")), 2),
                "Close": round(_parse_float(values.get("5. adjusted close", values.get("4. close"))), 2),
                "Volume": int(_parse_float(values.get("6. volume"))),
            }
        )

    return pd.DataFrame(rows).sort_values("Date").tail(days).reset_index(drop=True)


def get_market_overview() -> pd.DataFrame:
    """Return index dashboard rows using ETF/index proxies."""
    rows = []
    for label, symbol in INDEX_PROXIES:
        quote = get_quote(symbol)
        rows.append({"Index": label, "Symbol": symbol, "Value": quote["price"], "Change %": quote["change_pct"]})
    return pd.DataFrame(rows)
