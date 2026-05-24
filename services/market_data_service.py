"""Market data service facade.

UI code should use this module instead of importing mock data directly. Future
implementations can swap these functions for API/database-backed providers.
"""

from __future__ import annotations

import pandas as pd

from data import mock_data
from data.providers import alpha_vantage_provider

INDEX_PROXY_TICKERS = [symbol for _, symbol in alpha_vantage_provider.INDEX_PROXIES]


def get_market_data_status() -> str:
    """Return the active market data source label."""
    return "Alpha Vantage" if alpha_vantage_provider.is_configured() else "Mock data"


def get_available_tickers() -> list[str]:
    """Return supported ticker symbols."""
    # TODO: Replace static ticker universe with user-managed watchlists.
    return list(dict.fromkeys([*mock_data.AVAILABLE_TICKERS, *INDEX_PROXY_TICKERS]))


def get_quote_summary(ticker: str) -> dict:
    """Return normalized quote summary."""
    fallback = {
        **mock_data.get_quote_summary(ticker),
        "price_source": "Mock fallback",
        "metadata_source": "Mock fallback",
    }
    if not alpha_vantage_provider.is_configured():
        return {**fallback, "price_source": "Mock data", "metadata_source": "Mock data"}

    try:
        quote = {
            **alpha_vantage_provider.get_quote(ticker),
            "price_source": "Alpha Vantage Global Quote",
        }
    except alpha_vantage_provider.AlphaVantageError:
        quote = _quote_from_daily_history(ticker) or {**fallback, "name": ticker}

    try:
        overview = {
            **alpha_vantage_provider.get_company_overview(ticker),
            "metadata_source": "Alpha Vantage Company Overview",
        }
    except alpha_vantage_provider.AlphaVantageError:
        overview = {
            "name": ticker,
            "sector": mock_data.SECTOR_LABELS.get(
                ticker,
                "ETF / Index Proxy" if ticker in INDEX_PROXY_TICKERS else "Unknown",
            ),
            "market_cap": fallback["market_cap"],
        }

    return {
        **fallback,
        **quote,
        **overview,
    }


def get_price_history(ticker: str, days: int = 90, timeframe: str = "Daily") -> pd.DataFrame:
    """Return historical OHLCV data."""
    if alpha_vantage_provider.is_configured():
        try:
            return alpha_vantage_provider.get_price_history(ticker, periods=days, timeframe=timeframe)
        except alpha_vantage_provider.AlphaVantageError:
            pass
    history = mock_data.get_price_history(ticker, days)
    history.attrs["source"] = f"Mock data ({timeframe})"
    return history


def _quote_from_daily_history(ticker: str) -> dict | None:
    """Build a quote from Alpha Vantage daily history when GLOBAL_QUOTE is unavailable."""
    try:
        history = alpha_vantage_provider.get_daily_history(ticker, days=2)
    except alpha_vantage_provider.AlphaVantageError:
        return None

    if len(history) < 2:
        return None

    latest = history.iloc[-1]
    previous = history.iloc[-2]
    price = float(latest["Close"])
    previous_close = float(previous["Close"])
    change_abs = price - previous_close
    change_pct = (change_abs / previous_close * 100) if previous_close else 0
    return {
        "ticker": ticker,
        "name": ticker,
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "change_abs": round(change_abs, 2),
        "volume": int(latest["Volume"]),
        "price_source": "Alpha Vantage Daily History",
    }


def get_market_overview() -> pd.DataFrame:
    """Return market index overview."""
    if alpha_vantage_provider.is_configured():
        try:
            return alpha_vantage_provider.get_market_overview()
        except alpha_vantage_provider.AlphaVantageError:
            pass
    return mock_data.get_market_overview()


def get_top_movers() -> pd.DataFrame:
    """Return top mover snapshot."""
    return mock_data.get_top_movers()


def get_top_movers_by_direction(limit: int = 10) -> dict:
    """Return top gainers and losers with source metadata."""
    if alpha_vantage_provider.is_configured():
        try:
            return alpha_vantage_provider.get_top_movers(limit)
        except alpha_vantage_provider.AlphaVantageError:
            pass

    movers = mock_data.get_top_movers().copy()
    gainers = movers[movers["Change %"] > 0].sort_values("Change %", ascending=False).head(limit)
    losers = movers[movers["Change %"] < 0].sort_values("Change %", ascending=True).head(limit)
    return {
        "last_updated": "Mock data",
        "source": "Mock fallback",
        "gainers": gainers,
        "losers": losers,
    }


def get_watchlist() -> pd.DataFrame:
    """Return default watchlist data."""
    return mock_data.get_watchlist()
