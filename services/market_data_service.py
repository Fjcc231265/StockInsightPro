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
    fallback = mock_data.get_quote_summary(ticker)
    if not alpha_vantage_provider.is_configured():
        return fallback

    try:
        quote = alpha_vantage_provider.get_quote(ticker)
    except alpha_vantage_provider.AlphaVantageError:
        return fallback

    # Alpha Vantage quote does not include sector/market cap in GLOBAL_QUOTE.
    return {
        **fallback,
        **quote,
        "sector": mock_data.SECTOR_LABELS.get(ticker, "ETF / Index Proxy" if ticker in INDEX_PROXY_TICKERS else "Unknown"),
    }


def get_price_history(ticker: str, days: int = 90) -> pd.DataFrame:
    """Return historical OHLCV data."""
    if alpha_vantage_provider.is_configured():
        try:
            return alpha_vantage_provider.get_daily_history(ticker, days)
        except alpha_vantage_provider.AlphaVantageError:
            pass
    return mock_data.get_price_history(ticker, days)


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


def get_watchlist() -> pd.DataFrame:
    """Return default watchlist data."""
    return mock_data.get_watchlist()
