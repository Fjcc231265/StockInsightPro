"""Market data service facade.

UI code should use this module instead of importing mock data directly. Future
implementations can swap these functions for API/database-backed providers.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from data import mock_data
from data import snapshot_store
from data.providers import alpha_vantage_provider
from services.settings_service import get_effective_market_provider_label, should_use_alpha_vantage

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL"]
WATCHLIST_FILE = Path(__file__).resolve().parents[1] / "data" / "favorite_symbols.json"
INDEX_PROXY_TICKERS = [symbol for _, symbol in alpha_vantage_provider.INDEX_PROXIES]
SECTOR_PROXY_TICKERS = [item["symbol"] for item in alpha_vantage_provider.SECTOR_ETF_PROXIES]
SECTOR_PERFORMANCE_CACHE_TTL_SECONDS = 900
SECTOR_SNAPSHOT_NAME = "sector_performance"
SECTOR_ROTATION_SNAPSHOT_NAME = "sector_rotation"
_SECTOR_PERFORMANCE_CACHE: tuple[float, pd.DataFrame] | None = None
_SECTOR_ROTATION_CACHE: tuple[float, pd.DataFrame] | None = None
_MARKET_OVERVIEW_CACHE: tuple[float, pd.DataFrame] | None = None
_QUOTE_SUMMARY_CACHE: dict[str, tuple[float, dict]] = {}
_TOP_MOVERS_ERROR: str | None = None
QUOTE_SUMMARY_CACHE_TTL_SECONDS = 300
MARKET_OVERVIEW_CACHE_TTL_SECONDS = 900


def get_market_data_status() -> str:
    """Return the active market data source label."""
    return get_effective_market_provider_label()


def clear_sector_caches() -> None:
    """Clear in-memory and on-disk sector snapshot caches."""
    global _SECTOR_PERFORMANCE_CACHE, _SECTOR_ROTATION_CACHE, _MARKET_OVERVIEW_CACHE, _QUOTE_SUMMARY_CACHE, _TOP_MOVERS_ERROR
    _SECTOR_PERFORMANCE_CACHE = None
    _SECTOR_ROTATION_CACHE = None
    _MARKET_OVERVIEW_CACHE = None
    _QUOTE_SUMMARY_CACHE.clear()
    _TOP_MOVERS_ERROR = None
    snapshot_store.clear_snapshot(SECTOR_SNAPSHOT_NAME)
    snapshot_store.clear_snapshot(SECTOR_ROTATION_SNAPSHOT_NAME)


def get_available_tickers() -> list[str]:
    """Return supported ticker symbols."""
    return list(
        dict.fromkeys(
            [
                *load_favorite_symbols(),
                *mock_data.AVAILABLE_TICKERS,
                *INDEX_PROXY_TICKERS,
                *SECTOR_PROXY_TICKERS,
            ]
        )
    )


def load_favorite_symbols() -> list[str]:
    """Load favorite symbols from disk, falling back to defaults only when missing/invalid."""
    if not WATCHLIST_FILE.exists():
        return DEFAULT_WATCHLIST.copy()
    try:
        data = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_WATCHLIST.copy()
    if not isinstance(data, dict) or "symbols" not in data:
        return DEFAULT_WATCHLIST.copy()
    symbols = data.get("symbols", [])
    if not isinstance(symbols, list):
        return DEFAULT_WATCHLIST.copy()
    normalized = [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()]
    return list(dict.fromkeys(normalized))


def save_favorite_symbols(symbols: list[str]) -> list[str]:
    """Persist favorite symbols to disk and return normalized symbols."""
    normalized = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_FILE.write_text(json.dumps({"symbols": normalized}, indent=2), encoding="utf-8")
    return normalized


def add_favorite_symbol(symbol: str, symbols: list[str] | None = None, persist: bool = True) -> list[str]:
    """Add a symbol to favorites, optionally persisting to disk."""
    current = list(symbols if symbols is not None else load_favorite_symbols())
    normalized = symbol.strip().upper()
    if normalized and normalized not in current:
        current.append(normalized)
    return save_favorite_symbols(current) if persist else current


def remove_favorite_symbol(symbol: str, symbols: list[str] | None = None, persist: bool = True) -> list[str]:
    """Remove a symbol from favorites, optionally persisting to disk."""
    normalized = symbol.strip().upper()
    current = [item for item in (symbols if symbols is not None else load_favorite_symbols()) if item != normalized]
    return save_favorite_symbols(current) if persist else current


def validate_symbol(symbol: str) -> dict:
    """Validate that a symbol exists in Alpha Vantage."""
    normalized = symbol.strip().upper()
    if not normalized:
        return {"valid": False, "symbol": normalized, "message": "Enter a symbol first."}
    if not alpha_vantage_provider.is_configured():
        return {
            "valid": False,
            "symbol": normalized,
            "message": "Alpha Vantage API key is required to validate symbols.",
        }
    try:
        quote = alpha_vantage_provider.get_quote(normalized)
    except alpha_vantage_provider.AlphaVantageError as exc:
        return {"valid": False, "symbol": normalized, "message": f"{normalized} was not found in Alpha Vantage: {exc}"}
    return {
        "valid": True,
        "symbol": normalized,
        "message": f"{normalized} found in Alpha Vantage.",
        "quote": quote,
    }


def get_quote_summary(ticker: str) -> dict:
    """Return normalized quote summary."""
    cache_key = ticker.strip().upper()
    cached = _QUOTE_SUMMARY_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < QUOTE_SUMMARY_CACHE_TTL_SECONDS:
        return dict(cached[1])

    fallback = {
        **mock_data.get_quote_summary(ticker),
        "price_source": "Mock fallback",
        "metadata_source": "Mock fallback",
    }
    if not should_use_alpha_vantage("market") or not alpha_vantage_provider.is_configured():
        result = {**fallback, "price_source": "Mock data", "metadata_source": "Mock data"}
        _QUOTE_SUMMARY_CACHE[cache_key] = (time.time(), result)
        return result

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
            "description": "Company overview unavailable from Alpha Vantage right now.",
            "exchange": "Unknown",
            "currency": "USD",
            "country": "Unknown",
            "sector": mock_data.SECTOR_LABELS.get(
                ticker,
                "ETF / Index Proxy" if ticker in INDEX_PROXY_TICKERS else "Unknown",
            ),
            "industry": "Unknown",
            "market_cap": fallback["market_cap"],
            "pe_ratio": None,
            "peg_ratio": None,
            "beta": None,
            "dividend_yield": None,
            "profit_margin": None,
            "52_week_high": None,
            "52_week_low": None,
        }

    result = {
        **fallback,
        **quote,
        **overview,
    }
    _QUOTE_SUMMARY_CACHE[cache_key] = (time.time(), result)
    return result


def get_price_history(ticker: str, days: int = 90, timeframe: str = "Daily") -> pd.DataFrame:
    """Return historical OHLCV data."""
    if should_use_alpha_vantage("market") and alpha_vantage_provider.is_configured():
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
    global _MARKET_OVERVIEW_CACHE

    if _MARKET_OVERVIEW_CACHE:
        cached_at, cached_df = _MARKET_OVERVIEW_CACHE
        if time.time() - cached_at < MARKET_OVERVIEW_CACHE_TTL_SECONDS:
            return cached_df.copy()

    if should_use_alpha_vantage("market") and alpha_vantage_provider.is_configured():
        try:
            overview = alpha_vantage_provider.get_market_overview()
            _MARKET_OVERVIEW_CACHE = (time.time(), overview.copy())
            return overview
        except alpha_vantage_provider.AlphaVantageError as exc:
            fallback = mock_data.get_market_overview()
            fallback.attrs["source"] = f"Mock fallback - Alpha Vantage ETF proxy data unavailable: {exc}"
            _MARKET_OVERVIEW_CACHE = (time.time(), fallback.copy())
            return fallback
    fallback = mock_data.get_market_overview()
    fallback.attrs["source"] = "Mock data - Alpha Vantage API key not configured"
    _MARKET_OVERVIEW_CACHE = (time.time(), fallback.copy())
    return fallback


def get_sector_performance(
    force_refresh: bool = False,
    fetch_if_missing: bool = True,
) -> pd.DataFrame:
    """Return sector performance snapshot from memory, disk, or Alpha Vantage."""
    global _SECTOR_PERFORMANCE_CACHE

    if not force_refresh:
        if _SECTOR_PERFORMANCE_CACHE:
            cached_at, cached_df = _SECTOR_PERFORMANCE_CACHE
            if time.time() - cached_at < SECTOR_PERFORMANCE_CACHE_TTL_SECONDS:
                return cached_df.copy()

        disk_cached = snapshot_store.load_snapshot(SECTOR_SNAPSHOT_NAME)
        if disk_cached is not None:
            _SECTOR_PERFORMANCE_CACHE = (time.time(), disk_cached.copy())
            return disk_cached

    if not fetch_if_missing and not force_refresh:
        return pd.DataFrame()

    if should_use_alpha_vantage("market") and alpha_vantage_provider.is_configured():
        try:
            sector_df = alpha_vantage_provider.get_sector_performance()
            _cache_sector_performance(sector_df)
            return sector_df
        except alpha_vantage_provider.AlphaVantageError:
            pass

    sector_df = mock_data.get_sector_performance()
    sector_df.attrs["source"] = "Mock fallback"
    _cache_sector_performance(sector_df)
    return sector_df


def _cache_sector_performance(sector_df: pd.DataFrame) -> None:
    """Store sector performance in memory and on disk."""
    global _SECTOR_PERFORMANCE_CACHE
    _SECTOR_PERFORMANCE_CACHE = (time.time(), sector_df.copy())
    snapshot_store.save_snapshot(SECTOR_SNAPSHOT_NAME, sector_df, SECTOR_PERFORMANCE_CACHE_TTL_SECONDS)


def get_sector_rotation_history(
    days: int = 60,
    force_refresh: bool = False,
    fetch_if_missing: bool = True,
) -> pd.DataFrame:
    """Return sector rotation RSI history from memory, disk, or Alpha Vantage."""
    global _SECTOR_ROTATION_CACHE

    if not force_refresh:
        if _SECTOR_ROTATION_CACHE:
            cached_at, cached_df = _SECTOR_ROTATION_CACHE
            if time.time() - cached_at < SECTOR_PERFORMANCE_CACHE_TTL_SECONDS:
                return cached_df.copy()

        disk_cached = snapshot_store.load_snapshot(SECTOR_ROTATION_SNAPSHOT_NAME)
        if disk_cached is not None:
            _SECTOR_ROTATION_CACHE = (time.time(), disk_cached.copy())
            return disk_cached

    if not fetch_if_missing and not force_refresh:
        return pd.DataFrame()

    live_error = None
    if should_use_alpha_vantage("market") and alpha_vantage_provider.is_configured():
        try:
            rotation = alpha_vantage_provider.get_sector_rsi_history(days=days)
            _cache_sector_rotation(rotation)
            return rotation
        except alpha_vantage_provider.AlphaVantageError as exc:
            live_error = str(exc)

    rotation = mock_data.get_sector_rotation_history(days)
    rotation.attrs["source"] = "Mock fallback"
    if live_error:
        rotation.attrs["error"] = live_error
    _cache_sector_rotation(rotation)
    return rotation


def _cache_sector_rotation(rotation: pd.DataFrame) -> None:
    """Store sector rotation in memory and on disk."""
    global _SECTOR_ROTATION_CACHE
    _SECTOR_ROTATION_CACHE = (time.time(), rotation.copy())
    snapshot_store.save_snapshot(SECTOR_ROTATION_SNAPSHOT_NAME, rotation, SECTOR_PERFORMANCE_CACHE_TTL_SECONDS)


def _fetch_live_top_movers(limit: int = 10) -> dict | None:
    """Return live top movers payload, recording the latest Alpha Vantage error."""
    global _TOP_MOVERS_ERROR
    if not should_use_alpha_vantage("market") or not alpha_vantage_provider.is_configured():
        _TOP_MOVERS_ERROR = "Alpha Vantage is not configured for market data."
        return None
    try:
        payload = alpha_vantage_provider.get_top_movers(limit)
    except alpha_vantage_provider.AlphaVantageError as exc:
        _TOP_MOVERS_ERROR = str(exc)
        return None
    _TOP_MOVERS_ERROR = None
    return payload


def get_market_breadth() -> pd.DataFrame:
    """Return market breadth indicators."""
    global _TOP_MOVERS_ERROR
    if should_use_alpha_vantage("market") and alpha_vantage_provider.is_configured():
        try:
            breadth = alpha_vantage_provider.get_market_breadth()
            _TOP_MOVERS_ERROR = None
            return breadth
        except alpha_vantage_provider.AlphaVantageError as exc:
            _TOP_MOVERS_ERROR = str(exc)

    breadth = mock_data.get_market_breadth()
    breadth.attrs["source"] = "Mock fallback"
    breadth.attrs["last_updated"] = "Mock data"
    if _TOP_MOVERS_ERROR:
        breadth.attrs["error"] = _TOP_MOVERS_ERROR
    return breadth


def get_top_movers() -> pd.DataFrame:
    """Return top mover snapshot."""
    return mock_data.get_top_movers()


def get_top_movers_by_direction(limit: int = 10) -> dict:
    """Return top gainers and losers with source metadata."""
    live_payload = _fetch_live_top_movers(limit)
    if live_payload is not None:
        return live_payload

    movers = mock_data.get_top_movers().copy()
    gainers = movers[movers["Change %"] > 0].sort_values("Change %", ascending=False).head(limit)
    losers = movers[movers["Change %"] < 0].sort_values("Change %", ascending=True).head(limit)
    return {
        "last_updated": "Mock data",
        "source": "Mock fallback",
        "error": _TOP_MOVERS_ERROR or "Alpha Vantage top movers request failed.",
        "gainers": gainers,
        "losers": losers,
        "most_active": movers.sort_values("Volume", ascending=False).head(limit) if "Volume" in movers else movers.head(limit),
    }


def get_watchlist() -> pd.DataFrame:
    """Return default watchlist data."""
    return mock_data.get_watchlist()
