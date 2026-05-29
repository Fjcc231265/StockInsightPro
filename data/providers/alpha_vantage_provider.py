"""Alpha Vantage market data provider.

This adapter is intentionally UI-free. It returns normalized Python/Pandas
objects and raises provider-specific errors to be handled by services.
"""

from __future__ import annotations

import io
import time
import urllib.parse
import urllib.request
import json
from typing import Any

import pandas as pd

from analytics.technical.engine import calculate_adx, calculate_macd, calculate_rsi
from data import disk_cache
from utils.config import get_alpha_vantage_api_key
from utils.helpers import format_large_number

DISK_CACHE_NAMESPACE = "alpha_vantage"

BASE_URL = "https://www.alphavantage.co/query"
CACHE_TTL_SECONDS = 300
MIN_REQUEST_INTERVAL_SECONDS = 0.25

INDEX_SERIES = [
    {"label": "S&P 500", "index_symbol": "SPX"},
    {"label": "Nasdaq Composite", "index_symbol": "COMP"},
    {"label": "Dow Jones", "index_symbol": "DJI"},
    {"label": "Volatility", "index_symbol": "VIX"},
]

INDEX_PROXIES: list[tuple[str, str]] = []

SECTOR_ETF_PROXIES = [
    {"sector": "Technology", "symbol": "XLK"},
    {"sector": "Communication Services", "symbol": "XLC"},
    {"sector": "Consumer Cyclical", "symbol": "XLY"},
    {"sector": "Financial Services", "symbol": "XLF"},
    {"sector": "Healthcare", "symbol": "XLV"},
    {"sector": "Industrials", "symbol": "XLI"},
    {"sector": "Energy", "symbol": "XLE"},
    {"sector": "Consumer Defensive", "symbol": "XLP"},
    {"sector": "Utilities", "symbol": "XLU"},
    {"sector": "Real Estate", "symbol": "XLRE"},
    {"sector": "Materials", "symbol": "XLB"},
]

_CACHE: dict[tuple[tuple[str, str], ...], tuple[float, Any]] = {}
_LAST_REQUEST_AT = 0.0
# Bypass IDE/shell HTTP_PROXY values that can return 403 for external API calls.
_DIRECT_HTTP_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage cannot return usable data."""


def is_configured() -> bool:
    """Return True when an Alpha Vantage API key is available."""
    return get_alpha_vantage_api_key() is not None


def clear_caches() -> None:
    """Clear in-memory Alpha Vantage response cache."""
    _CACHE.clear()


def _disk_cache_enabled() -> bool:
    try:
        from services.settings_service import is_disk_cache_enabled

        return is_disk_cache_enabled()
    except Exception:  # noqa: BLE001 - settings may be unavailable during import
        return True


def _ttl_for_params(params: dict[str, str]) -> int:
    try:
        from services.settings_service import get_cache_ttl_for_function

        return get_cache_ttl_for_function(params.get("function", ""))
    except Exception:  # noqa: BLE001
        return CACHE_TTL_SECONDS


def _urlopen_direct(url: str, timeout: int = 20):
    """Open an Alpha Vantage URL without routing through local HTTP proxies."""
    return _DIRECT_HTTP_OPENER.open(url, timeout=timeout)


def _read_url_payload(url: str, timeout: int = 20) -> str:
    """Read an Alpha Vantage URL, retrying system proxy only for DNS failures."""
    try:
        with _urlopen_direct(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except Exception as direct_exc:  # noqa: BLE001 - normalized by provider boundary
        message = str(direct_exc)
        if "nodename nor servname provided" not in message and "Name or service not known" not in message:
            raise
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except Exception as proxy_exc:  # noqa: BLE001
            raise AlphaVantageError(
                "Alpha Vantage network lookup failed both directly and through the configured proxy. "
                f"Direct error: {message}; proxy error: {proxy_exc}"
            ) from proxy_exc


def _format_request_error(exc: Exception) -> str:
    """Return a clearer network error message for proxy/tunnel failures."""
    message = str(exc)
    if "Tunnel connection failed" in message or "403 Forbidden" in message:
        return (
            "A local HTTP proxy blocked the Alpha Vantage request. "
            "Restart Streamlit after updating the app; if it persists, disable VPN/proxy "
            f"or unset HTTP_PROXY/HTTPS_PROXY in the shell that launches Streamlit. ({message})"
        )
    if "nodename nor servname provided" in message or "Name or service not known" in message:
        return (
            "DNS could not resolve Alpha Vantage from this process. "
            "This is a local network/VPN/proxy issue; cached data will be used when available. "
            f"({message})"
        )
    return f"Alpha Vantage request failed: {message}"


def _request(params: dict[str, str]) -> dict[str, Any]:
    """Call Alpha Vantage with in-memory and optional disk TTL cache."""
    global _LAST_REQUEST_AT

    api_key = get_alpha_vantage_api_key()
    if not api_key:
        raise AlphaVantageError("Alpha Vantage API key is not configured.")

    request_params = {**params, "apikey": api_key}
    cache_key = tuple(sorted(request_params.items()))
    ttl_seconds = _ttl_for_params(request_params)
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < ttl_seconds:
        return cached[1]

    if _disk_cache_enabled():
        disk_cached = disk_cache.get_json(DISK_CACHE_NAMESPACE, request_params, ttl_seconds)
        if disk_cached is not None:
            _CACHE[cache_key] = (time.time(), disk_cached)
            return disk_cached

    elapsed = time.time() - _LAST_REQUEST_AT
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    url = f"{BASE_URL}?{urllib.parse.urlencode(request_params)}"
    try:
        payload = _read_url_payload(url, timeout=20)
        _LAST_REQUEST_AT = time.time()
    except AlphaVantageError as exc:
        if _disk_cache_enabled():
            stale_cached = disk_cache.get_json_stale(DISK_CACHE_NAMESPACE, request_params)
            if stale_cached is not None:
                stale_cached.setdefault("_cache_warning", str(exc))
                _CACHE[cache_key] = (time.time(), stale_cached)
                return stale_cached
        raise
    except Exception as exc:  # noqa: BLE001 - provider boundary converts all failures
        if _disk_cache_enabled():
            stale_cached = disk_cache.get_json_stale(DISK_CACHE_NAMESPACE, request_params)
            if stale_cached is not None:
                stale_cached.setdefault("_cache_warning", _format_request_error(exc))
                _CACHE[cache_key] = (time.time(), stale_cached)
                return stale_cached
        raise AlphaVantageError(_format_request_error(exc)) from exc

    try:
        data = json.loads(payload)
    except Exception as exc:  # noqa: BLE001
        raise AlphaVantageError("Alpha Vantage returned invalid JSON.") from exc

    if "Error Message" in data:
        raise AlphaVantageError(data["Error Message"])
    if "Note" in data or "Information" in data:
        raise AlphaVantageError(data.get("Note") or data.get("Information"))

    _CACHE[cache_key] = (time.time(), data)
    if _disk_cache_enabled():
        disk_cache.set_json(DISK_CACHE_NAMESPACE, request_params, data, ttl_seconds)
    return data


def _request_csv(params: dict[str, str]) -> pd.DataFrame:
    """Call an Alpha Vantage endpoint that returns CSV data."""
    global _LAST_REQUEST_AT

    api_key = get_alpha_vantage_api_key()
    if not api_key:
        raise AlphaVantageError("Alpha Vantage API key is not configured.")

    request_params = {**params, "apikey": api_key}
    cache_key = tuple(sorted(request_params.items()))
    ttl_seconds = _ttl_for_params(request_params)
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < ttl_seconds:
        return cached[1].copy()

    if _disk_cache_enabled():
        disk_cached = disk_cache.get_text(DISK_CACHE_NAMESPACE, request_params, ttl_seconds)
        if disk_cached is not None:
            frame = pd.read_csv(io.StringIO(disk_cached))
            _CACHE[cache_key] = (time.time(), frame.copy())
            return frame

    elapsed = time.time() - _LAST_REQUEST_AT
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    url = f"{BASE_URL}?{urllib.parse.urlencode(request_params)}"
    try:
        payload = _read_url_payload(url, timeout=20)
        _LAST_REQUEST_AT = time.time()
    except AlphaVantageError as exc:
        if _disk_cache_enabled():
            stale_cached = disk_cache.get_text_stale(DISK_CACHE_NAMESPACE, request_params)
            if stale_cached is not None:
                frame = pd.read_csv(io.StringIO(stale_cached))
                frame.attrs["cache_warning"] = str(exc)
                _CACHE[cache_key] = (time.time(), frame.copy())
                return frame
        raise
    except Exception as exc:  # noqa: BLE001 - provider boundary converts all failures
        if _disk_cache_enabled():
            stale_cached = disk_cache.get_text_stale(DISK_CACHE_NAMESPACE, request_params)
            if stale_cached is not None:
                frame = pd.read_csv(io.StringIO(stale_cached))
                frame.attrs["cache_warning"] = _format_request_error(exc)
                _CACHE[cache_key] = (time.time(), frame.copy())
                return frame
        raise AlphaVantageError(_format_request_error(exc)) from exc

    if payload.lstrip().startswith("{"):
        try:
            data = json.loads(payload)
        except Exception as exc:  # noqa: BLE001
            raise AlphaVantageError("Alpha Vantage returned invalid CSV/JSON.") from exc
        raise AlphaVantageError(data.get("Note") or data.get("Information") or data.get("Error Message") or payload)

    try:
        frame = pd.read_csv(io.StringIO(payload))
    except Exception as exc:  # noqa: BLE001
        raise AlphaVantageError("Alpha Vantage returned invalid CSV.") from exc

    _CACHE[cache_key] = (time.time(), frame.copy())
    if _disk_cache_enabled():
        disk_cache.set_text(DISK_CACHE_NAMESPACE, request_params, payload, ttl_seconds)
    return frame


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


def get_index_snapshot(label: str, item: dict[str, Any]) -> dict:
    """Return latest index value from Alpha Vantage INDEX_DATA."""
    index_symbol = item.get("index_symbol")
    if not index_symbol:
        raise AlphaVantageError(f"No index symbol configured for {label}.")
    return _get_index_snapshot_from_index_data(label, index_symbol)


def _get_index_snapshot_from_index_data(label: str, symbol: str) -> dict:
    """Return the latest index value from Alpha Vantage INDEX_DATA."""
    errors: list[str] = []
    for interval in ("daily", "weekly"):
        try:
            data = _request({"function": "INDEX_DATA", "symbol": symbol, "interval": interval})
        except AlphaVantageError as exc:
            errors.append(str(exc))
            continue

        rows = data.get("data")
        if not rows:
            series = data.get("Time Series (Daily)", {})
            rows = [
                {"date": date_str, **values}
                for date_str, values in series.items()
            ]
        if not rows or len(rows) < 2:
            errors.append(f"No index data returned for {symbol} ({interval}).")
            continue

        rows = sorted(
            rows,
            key=lambda row: row.get("date") or row.get("timestamp") or row.get("time") or "",
        )
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
            "Source": f"Alpha Vantage INDEX_DATA ({symbol}, {interval})",
        }

    raise AlphaVantageError(
        f"No index data returned for {label} ({symbol}). {' | '.join(errors[:2])}"
    )


def get_market_overview() -> pd.DataFrame:
    """Return index dashboard rows using real Alpha Vantage index data."""
    rows = []
    last_error: AlphaVantageError | None = None
    for item in INDEX_SERIES:
        try:
            rows.append(get_index_snapshot(item["label"], item))
        except AlphaVantageError as exc:
            last_error = exc
            continue
    if not rows:
        detail = str(last_error) if last_error else "No market index data returned."
        raise AlphaVantageError(detail)
    return pd.DataFrame(rows)


def get_sector_performance() -> pd.DataFrame:
    """Return sector performance using compact daily plus native monthly ETF history."""
    rows = []
    for item in SECTOR_ETF_PROXIES:
        try:
            daily_history = get_price_history(item["symbol"], periods=100, timeframe="Daily")
            monthly_history = get_price_history(item["symbol"], periods=48, timeframe="Monthly")
        except AlphaVantageError:
            continue
        rows.append(_sector_performance_row(item["sector"], item["symbol"], daily_history, monthly_history))

    if not rows:
        raise AlphaVantageError("No sector ETF performance data returned.")

    sector_df = pd.DataFrame(rows)
    sector_df.attrs["source"] = "Alpha Vantage sector ETF proxies"
    return sector_df


def get_sector_rsi_history(days: int = 60, time_period: int = 14) -> pd.DataFrame:
    """Return sector ETF RSI history calculated from cached daily price data."""
    series_by_sector = []
    for item in SECTOR_ETF_PROXIES:
        try:
            history = get_price_history(
                item["symbol"],
                periods=max(days + time_period + 10, 100),
                timeframe="Daily",
            ).sort_values("Date")
        except AlphaVantageError:
            continue

        rsi_series = pd.DataFrame(
            {
                "Date": history["Date"],
                "RSI": calculate_rsi(history["Close"], window=time_period).round(2),
            }
        ).tail(days)
        column_name = f"{item['sector']} ({item['symbol']})"
        series_by_sector.append(rsi_series.set_index("Date")["RSI"].rename(column_name))

    if not series_by_sector:
        raise AlphaVantageError("No sector ETF price data returned for RSI rotation.")

    rsi_df = pd.concat(series_by_sector, axis=1).sort_index().tail(days).reset_index()
    rsi_df.attrs["source"] = f"Alpha Vantage sector ETF RSI({time_period}) from daily OHLC"
    return rsi_df


def get_rsi_history(symbol: str, days: int = 60, time_period: int = 14) -> pd.DataFrame:
    """Return RSI history calculated from cached daily OHLC."""
    lookback = 100 if days <= 90 else max(days + time_period + 10, 100)
    history = get_price_history(symbol, periods=lookback, timeframe="Daily").sort_values("Date")
    if history.empty:
        raise AlphaVantageError(f"No daily price history returned for {symbol}.")

    rsi_df = pd.DataFrame(
        {
            "Date": history["Date"],
            "RSI": calculate_rsi(history["Close"], window=time_period).round(2),
        }
    ).tail(days)
    rsi_df.attrs["source"] = f"{history.attrs.get('source', 'Daily OHLC')} · RSI({time_period})"
    return rsi_df.reset_index(drop=True)


def macd_from_history(
    history: pd.DataFrame,
    days: int = 60,
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
) -> pd.DataFrame:
    """Build MACD history from an existing daily OHLC dataframe."""
    if history.empty:
        raise AlphaVantageError("No daily price history available for MACD.")

    macd_values = calculate_macd(
        history["Close"],
        fastperiod=fastperiod,
        slowperiod=slowperiod,
        signalperiod=signalperiod,
    ).round(4)
    macd_df = pd.DataFrame({"Date": history["Date"], **macd_values}).tail(days)
    macd_df.attrs["source"] = (
        f"{history.attrs.get('source', 'Daily OHLC')} · MACD({fastperiod},{slowperiod},{signalperiod})"
    )
    return macd_df.reset_index(drop=True)


def get_macd_history(
    symbol: str,
    days: int = 60,
    fastperiod: int = 12,
    slowperiod: int = 26,
    signalperiod: int = 9,
) -> pd.DataFrame:
    """Return MACD history calculated from cached daily OHLC."""
    lookback = 100 if days <= 60 else max(days + slowperiod + signalperiod + 10, 100)
    history = get_price_history(symbol, periods=lookback, timeframe="Daily").sort_values("Date")
    return macd_from_history(history, days=days, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)


def adx_from_history(history: pd.DataFrame, days: int = 60, time_period: int = 14) -> pd.DataFrame:
    """Build ADX history from an existing daily OHLC dataframe."""
    if history.empty:
        raise AlphaVantageError("No daily price history available for ADX.")

    adx_df = pd.DataFrame(
        {
            "Date": history["Date"],
            "ADX": calculate_adx(history["High"], history["Low"], history["Close"], window=time_period).round(4),
        }
    ).tail(days)
    adx_df.attrs["source"] = f"{history.attrs.get('source', 'Daily OHLC')} · ADX({time_period})"
    return adx_df.reset_index(drop=True)


def get_adx_history(symbol: str, days: int = 60, time_period: int = 14) -> pd.DataFrame:
    """Return ADX history calculated from cached daily OHLC."""
    lookback = max(days + (time_period * 3) + 10, 100)
    history = get_price_history(symbol, periods=lookback, timeframe="Daily").sort_values("Date")
    return adx_from_history(history, days=days, time_period=time_period)


def get_latest_rsi(symbol: str, time_period: int = 9, timeout: int = 10) -> dict[str, Any]:
    """Return latest daily RSI calculated from cached daily OHLC."""
    del timeout  # retained for backward compatibility with screener callers
    rsi_history = get_rsi_history(symbol, days=1, time_period=time_period)
    if rsi_history.empty:
        raise AlphaVantageError(f"No usable RSI data returned for {symbol}.")

    latest = rsi_history.iloc[-1]
    latest_date = latest["Date"]
    if hasattr(latest_date, "strftime"):
        latest_date = latest_date.strftime("%Y-%m-%d")
    return {
        "date": str(latest_date),
        "rsi": round(float(latest["RSI"]), 4),
        "symbol": symbol,
    }


def _sector_performance_row(
    sector: str,
    symbol: str,
    daily_history: pd.DataFrame,
    monthly_history: pd.DataFrame,
) -> dict[str, Any]:
    """Build one sector ETF performance row."""
    daily_prices = daily_history.sort_values("Date").reset_index(drop=True)
    monthly_prices = monthly_history.sort_values("Date").reset_index(drop=True)
    latest = float(daily_prices["Close"].iloc[-1])
    one_month_return = _period_return(daily_prices, 21)
    return {
        "Sector": sector,
        "ETF": symbol,
        "Price": round(latest, 2),
        "1D %": _period_return(daily_prices, 1),
        "1W %": _period_return(daily_prices, 5),
        "1M %": one_month_return,
        "YTD %": _ytd_return(daily_prices),
        "1Y %": _monthly_period_return(monthly_prices, 12),
        "3Y %": _monthly_period_return(monthly_prices, 36),
        "Momentum": _sector_momentum_label(one_month_return),
    }


def _period_return(prices: pd.DataFrame, periods_back: int) -> float:
    """Return percentage change from N trading periods ago."""
    latest = float(prices["Close"].iloc[-1])
    if len(prices) <= periods_back:
        base = float(prices["Close"].iloc[0])
    else:
        base = float(prices["Close"].iloc[-periods_back - 1])
    return round(((latest - base) / base) * 100, 2) if base else 0.0


def _ytd_return(prices: pd.DataFrame) -> float:
    """Return year-to-date percentage change from available daily history."""
    latest_row = prices.iloc[-1]
    latest = float(latest_row["Close"])
    latest_year = pd.to_datetime(latest_row["Date"]).year
    current_year_prices = prices[pd.to_datetime(prices["Date"]).dt.year == latest_year]
    base = float(current_year_prices["Close"].iloc[0]) if not current_year_prices.empty else float(prices["Close"].iloc[0])
    return round(((latest - base) / base) * 100, 2) if base else 0.0


def _monthly_period_return(prices: pd.DataFrame, months_back: int) -> float:
    """Return approximate rolling performance from monthly adjusted history."""
    latest = float(prices["Close"].iloc[-1])
    if len(prices) <= months_back:
        base = float(prices["Close"].iloc[0])
    else:
        base = float(prices["Close"].iloc[-months_back - 1])
    return round(((latest - base) / base) * 100, 2) if base else 0.0


def _sector_momentum_label(one_month_return: float) -> str:
    """Return simple sector momentum label from one-month performance."""
    if one_month_return > 1:
        return "Bullish"
    if one_month_return < -1:
        return "Bearish"
    return "Neutral"


def _fetch_top_gainers_losers() -> dict[str, Any]:
    """Fetch the shared Alpha Vantage top gainers/losers payload once per cache window."""
    return _request({"function": "TOP_GAINERS_LOSERS"})


def get_top_movers(limit: int = 10) -> dict[str, Any]:
    """Return top gainers and losers from Alpha Vantage."""
    data = _fetch_top_gainers_losers()
    gainers = data.get("top_gainers", [])
    losers = data.get("top_losers", [])
    most_active = data.get("most_actively_traded", [])
    if not gainers or not losers:
        raise AlphaVantageError("No top movers returned.")

    return {
        "last_updated": data.get("last_updated", "Unknown"),
        "source": "Alpha Vantage Top Gainers/Losers"
        + (" (stale cache)" if data.get("_cache_warning") else ""),
        "warning": data.get("_cache_warning"),
        "gainers": _normalize_movers(gainers[:limit], "Gainer"),
        "losers": _normalize_movers(losers[:limit], "Loser"),
        "most_active": _normalize_movers(most_active[:limit], "Most active") if most_active else pd.DataFrame(),
    }


def get_market_breadth() -> pd.DataFrame:
    """Return live market breadth proxies from Alpha Vantage top movers data."""
    data = _fetch_top_gainers_losers()
    most_active = data.get("most_actively_traded", [])
    gainers = data.get("top_gainers", [])
    losers = data.get("top_losers", [])
    if not most_active:
        raise AlphaVantageError("No most-active market breadth data returned.")

    active_rows = [
        {
            "ticker": row.get("ticker", ""),
            "change_pct": _parse_float(row.get("change_percentage")),
            "volume": _parse_float(row.get("volume")),
        }
        for row in most_active
    ]
    active_count = len(active_rows)
    advancers = sum(1 for row in active_rows if row["change_pct"] > 0)
    decliners = sum(1 for row in active_rows if row["change_pct"] < 0)
    up_volume = sum(row["volume"] for row in active_rows if row["change_pct"] > 0)
    down_volume = sum(row["volume"] for row in active_rows if row["change_pct"] < 0)
    total_volume = up_volume + down_volume
    average_change = sum(row["change_pct"] for row in active_rows) / active_count if active_count else 0
    strongest = max(active_rows, key=lambda row: row["change_pct"])
    weakest = min(active_rows, key=lambda row: row["change_pct"])

    breadth = pd.DataFrame(
        [
            {
                "Indicator": "Most-active advancers / decliners",
                "Value": f"{advancers} / {decliners}",
                "Signal": _breadth_signal(advancers - decliners),
            },
            {
                "Indicator": "Most-active advance ratio",
                "Value": f"{(advancers / active_count * 100):.1f}%" if active_count else "0.0%",
                "Signal": _breadth_signal(advancers - decliners),
            },
            {
                "Indicator": "Most-active up-volume ratio",
                "Value": f"{(up_volume / total_volume * 100):.1f}%" if total_volume else "0.0%",
                "Signal": _breadth_signal(up_volume - down_volume),
            },
            {
                "Indicator": "Average most-active move",
                "Value": f"{average_change:.2f}%",
                "Signal": _breadth_signal(average_change),
            },
            {
                "Indicator": "Top gainers / losers available",
                "Value": f"{len(gainers)} / {len(losers)}",
                "Signal": "Coverage",
            },
            {
                "Indicator": "Strongest / weakest active",
                "Value": f"{strongest['ticker']} {strongest['change_pct']:.2f}% / {weakest['ticker']} {weakest['change_pct']:.2f}%",
                "Signal": "Range",
            },
        ]
    )
    breadth.attrs["source"] = "Alpha Vantage Top Gainers/Losers breadth proxy"
    if data.get("_cache_warning"):
        breadth.attrs["source"] += " (stale cache)"
        breadth.attrs["warning"] = data["_cache_warning"]
    breadth.attrs["last_updated"] = data.get("last_updated", "Unknown")
    return breadth


def _breadth_signal(value: float) -> str:
    """Convert positive/negative breadth proxy values to display labels."""
    if value > 0:
        return "Positive"
    if value < 0:
        return "Negative"
    return "Neutral"


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


def get_insider_transactions(ticker: str, limit: int = 50) -> pd.DataFrame:
    """Return recent insider transactions from Alpha Vantage."""
    data = _request({"function": "INSIDER_TRANSACTIONS", "symbol": ticker})
    transactions = data.get("data", [])
    if not transactions:
        raise AlphaVantageError(f"No insider transactions returned for {ticker}.")

    rows = []
    for item in transactions[:limit]:
        shares = _parse_optional_float(item.get("shares"))
        share_price = _parse_optional_float(item.get("share_price"))
        transaction_value = shares * share_price if shares is not None and share_price is not None else None
        rows.append(
            {
                "Date": item.get("transaction_date") or "Unknown",
                "Executive": item.get("executive") or "Unknown",
                "Title": item.get("executive_title") or "Unknown",
                "Security": item.get("security_type") or "Unknown",
                "Type": _normalize_insider_transaction_type(item.get("acquisition_or_disposal")),
                "Shares": format_large_number(shares) if shares is not None else "-",
                "Share Price": "-" if share_price is None else f"${share_price:.2f}",
                "Value": "-" if transaction_value is None else f"${transaction_value:,.0f}",
            }
        )

    insider_df = pd.DataFrame(rows)
    insider_df.attrs["source"] = "Alpha Vantage Insider Transactions"
    return insider_df


def get_historical_options(ticker: str, date: str | None = None) -> pd.DataFrame:
    """Return normalized historical options contracts from Alpha Vantage."""
    params = {"function": "HISTORICAL_OPTIONS", "symbol": ticker}
    if date:
        params["date"] = date

    data = _request(params)
    contracts = data.get("data", [])
    if not contracts:
        raise AlphaVantageError(f"No historical options returned for {ticker}.")

    rows = []
    for item in contracts:
        rows.append(
            {
                "Contract ID": item.get("contractID", ""),
                "Symbol": item.get("symbol", ticker),
                "Date": pd.to_datetime(item.get("date"), errors="coerce"),
                "Expiration": pd.to_datetime(item.get("expiration"), errors="coerce"),
                "Type": str(item.get("type", "")).lower(),
                "Strike": _parse_optional_float(item.get("strike")),
                "Last": _parse_optional_float(item.get("last")),
                "Mark": _parse_optional_float(item.get("mark")),
                "Bid": _parse_optional_float(item.get("bid")),
                "Bid Size": _parse_optional_float(item.get("bid_size")),
                "Ask": _parse_optional_float(item.get("ask")),
                "Ask Size": _parse_optional_float(item.get("ask_size")),
                "Volume": _parse_optional_float(item.get("volume")),
                "Open Interest": _parse_optional_float(item.get("open_interest")),
                "Implied Volatility": _parse_optional_float(item.get("implied_volatility")),
                "Delta": _parse_optional_float(item.get("delta")),
                "Gamma": _parse_optional_float(item.get("gamma")),
                "Theta": _parse_optional_float(item.get("theta")),
                "Vega": _parse_optional_float(item.get("vega")),
                "Rho": _parse_optional_float(item.get("rho")),
            }
        )

    options = pd.DataFrame(rows).dropna(subset=["Expiration", "Strike"])
    if options.empty:
        raise AlphaVantageError(f"No usable historical options returned for {ticker}.")

    options.attrs["source"] = "Alpha Vantage Historical Options"
    options.attrs["snapshot_date"] = options["Date"].dropna().max().strftime("%Y-%m-%d")
    return options


def _normalize_insider_transaction_type(value: str | None) -> str:
    """Map Alpha Vantage acquisition/disposal code to a display label."""
    normalized = (value or "").upper()
    if normalized == "A":
        return "Acquisition"
    if normalized == "D":
        return "Disposal"
    return value or "Unknown"


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


def get_latest_earnings_release(ticker: str) -> dict[str, Any]:
    """Return the latest quarterly earnings release from Alpha Vantage EARNINGS."""
    data = _request({"function": "EARNINGS", "symbol": ticker})
    quarterly_earnings = data.get("quarterlyEarnings", [])
    if not quarterly_earnings:
        raise AlphaVantageError(f"No earnings releases returned for {ticker}.")

    latest = quarterly_earnings[0]
    return {
        "ticker": data.get("symbol", ticker),
        "reported_date": latest.get("reportedDate") or "Unknown",
        "fiscal_date_ending": latest.get("fiscalDateEnding") or "Unknown",
        "reported_eps": _parse_optional_float(latest.get("reportedEPS")),
        "estimated_eps": _parse_optional_float(latest.get("estimatedEPS")),
        "surprise": _parse_optional_float(latest.get("surprise")),
        "surprise_percentage": _parse_optional_float(latest.get("surprisePercentage")),
        "report_time": latest.get("reportTime") or "Unknown",
        "source": "Alpha Vantage Earnings",
    }


def get_earnings_calendar(ticker: str, horizon: str = "3month") -> pd.DataFrame:
    """Return upcoming earnings calendar rows from Alpha Vantage."""
    calendar = _request_csv(
        {
            "function": "EARNINGS_CALENDAR",
            "symbol": ticker,
            "horizon": horizon,
        }
    )
    required_columns = {"symbol", "reportDate", "fiscalDateEnding", "estimate", "currency"}
    if not required_columns.issubset(calendar.columns):
        raise AlphaVantageError(f"No earnings calendar returned for {ticker}.")

    if calendar.empty:
        empty = pd.DataFrame(
            columns=["Ticker", "Company", "Report Date", "Fiscal Date Ending", "EPS Estimate", "Currency"]
        )
        empty.attrs["source"] = "Alpha Vantage Earnings Calendar"
        empty.attrs["horizon"] = horizon
        empty.attrs["empty_reason"] = (
            f"Alpha Vantage has no upcoming earnings dates for {ticker} within the selected horizon."
        )
        return empty

    normalized = calendar.rename(
        columns={
            "symbol": "Ticker",
            "name": "Company",
            "reportDate": "Report Date",
            "fiscalDateEnding": "Fiscal Date Ending",
            "estimate": "EPS Estimate",
            "currency": "Currency",
        }
    )
    normalized["Report Date"] = pd.to_datetime(normalized["Report Date"], errors="coerce").dt.date.astype(str)
    normalized["Fiscal Date Ending"] = pd.to_datetime(
        normalized["Fiscal Date Ending"], errors="coerce"
    ).dt.date.astype(str)
    normalized["EPS Estimate"] = normalized["EPS Estimate"].apply(_format_optional_eps)
    normalized = normalized[["Ticker", "Company", "Report Date", "Fiscal Date Ending", "EPS Estimate", "Currency"]]
    normalized.attrs["source"] = "Alpha Vantage Earnings Calendar"
    normalized.attrs["horizon"] = horizon
    return normalized


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


def _format_optional_eps(value: str | float | int | None) -> str:
    """Format optional EPS values from provider data."""
    parsed = _parse_optional_float(value)
    return "-" if parsed is None else f"{parsed:.2f}"
