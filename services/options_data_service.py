"""Options intelligence data service facade."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data.providers import alpha_vantage_provider
from services.settings_service import should_use_alpha_vantage

_LIVE_OPTIONS_CACHE: dict[str, pd.DataFrame] = {}
_LIVE_OPTIONS_ERRORS: dict[str, str] = {}


def clear_options_cache() -> None:
    """Clear in-memory options chain cache."""
    _LIVE_OPTIONS_CACHE.clear()
    _LIVE_OPTIONS_ERRORS.clear()


def _get_live_options(ticker: str) -> pd.DataFrame | None:
    """Return Alpha Vantage options data, or None when unavailable."""
    cache_key = ticker.upper()
    if not should_use_alpha_vantage("market") or not alpha_vantage_provider.is_configured():
        _LIVE_OPTIONS_ERRORS[cache_key] = "Alpha Vantage is not configured for market/options data."
        return None
    if cache_key in _LIVE_OPTIONS_CACHE:
        return _LIVE_OPTIONS_CACHE[cache_key].copy()

    try:
        options = alpha_vantage_provider.get_historical_options(ticker)
    except alpha_vantage_provider.AlphaVantageError as exc:
        _LIVE_OPTIONS_ERRORS[cache_key] = str(exc)
        return None
    _LIVE_OPTIONS_ERRORS.pop(cache_key, None)
    _LIVE_OPTIONS_CACHE[cache_key] = options.copy()
    return options


def _options_unavailable_reason(ticker: str) -> str:
    """Return the most recent Alpha Vantage options failure reason."""
    detail = _LIVE_OPTIONS_ERRORS.get(ticker.upper())
    if detail:
        return f"Alpha Vantage historical options are unavailable for {ticker}: {detail}"
    return f"Alpha Vantage historical options are unavailable for {ticker}. Mock options data is disabled."


def _primary_expiration(options: pd.DataFrame) -> pd.Timestamp:
    """Return the nearest expiration at or after the snapshot date."""
    snapshot_date = options["Date"].dropna().max()
    expirations = options["Expiration"].dropna().sort_values()
    future_expirations = expirations[expirations >= snapshot_date]
    return future_expirations.iloc[0] if not future_expirations.empty else expirations.iloc[0]


def _primary_expiration_options(options: pd.DataFrame) -> pd.DataFrame:
    """Return contracts for the nearest usable expiration."""
    expiration = _primary_expiration(options)
    return options[options["Expiration"] == expiration].copy()


def _format_source(frame: pd.DataFrame, source: str, snapshot_date: str | None = None) -> pd.DataFrame:
    """Attach source metadata to derived option tables."""
    frame.attrs["source"] = source
    if snapshot_date:
        frame.attrs["snapshot_date"] = snapshot_date
    return frame


def _unavailable_frame(columns: list[str], reason: str) -> pd.DataFrame:
    """Return an empty options table with explicit unavailable metadata."""
    frame = pd.DataFrame(columns=columns)
    frame.attrs["source"] = "Unavailable"
    frame.attrs["error"] = reason
    return frame


def _unavailable_kpis(reason: str) -> dict:
    """Return empty KPI values with explicit unavailable metadata."""
    return {
        "Put/Call Ratio": None,
        "IV Rank": None,
        "30D IV": None,
        "Max Pain": None,
        "Source": "Unavailable",
        "Error": reason,
    }


def get_options_chain(ticker: str) -> pd.DataFrame:
    """Return option chain snapshot."""
    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_frame(
            ["Strike", "Call Bid", "Call Ask", "Call OI", "Put Bid", "Put Ask", "Put OI", "IV", "Delta"],
            _options_unavailable_reason(ticker),
        )

    primary = _primary_expiration_options(live_options)
    calls = primary[primary["Type"] == "call"][["Strike", "Bid", "Ask", "Open Interest", "Implied Volatility", "Delta"]]
    puts = primary[primary["Type"] == "put"][["Strike", "Bid", "Ask", "Open Interest"]]
    chain = calls.merge(puts, on="Strike", how="outer", suffixes=("_Call", "_Put")).sort_values("Strike")
    chain = chain.rename(
        columns={
            "Bid_Call": "Call Bid",
            "Ask_Call": "Call Ask",
            "Open Interest_Call": "Call OI",
            "Bid_Put": "Put Bid",
            "Ask_Put": "Put Ask",
            "Open Interest_Put": "Put OI",
            "Implied Volatility": "IV",
        }
    )
    chain = chain[["Strike", "Call Bid", "Call Ask", "Call OI", "Put Bid", "Put Ask", "Put OI", "IV", "Delta"]]
    chain[["Call OI", "Put OI"]] = chain[["Call OI", "Put OI"]].fillna(0).astype(int)
    numeric_cols = ["Strike", "Call Bid", "Call Ask", "Put Bid", "Put Ask", "IV", "Delta"]
    chain[numeric_cols] = chain[numeric_cols].round(4)
    return _format_source(chain, live_options.attrs["source"], live_options.attrs.get("snapshot_date"))


def get_options_kpis(ticker: str) -> dict:
    """Return options summary KPIs."""
    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_kpis(_options_unavailable_reason(ticker))

    primary = _primary_expiration_options(live_options)
    call_oi = primary.loc[primary["Type"] == "call", "Open Interest"].fillna(0).sum()
    put_oi = primary.loc[primary["Type"] == "put", "Open Interest"].fillna(0).sum()
    put_call_ratio = float(put_oi / call_oi) if call_oi else 0
    iv_values = live_options["Implied Volatility"].dropna()
    atm_iv = _atm_implied_volatility(primary)
    iv_rank = _percent_rank(atm_iv, iv_values)
    thirty_day_iv = _term_iv_nearest_days(live_options, 30)
    max_pain = _calculate_max_pain(primary)
    return {
        "Put/Call Ratio": round(put_call_ratio, 2),
        "IV Rank": round(iv_rank, 2),
        "30D IV": round(thirty_day_iv * 100, 2),
        "Max Pain": round(max_pain, 2),
        "Source": live_options.attrs["source"],
        "Snapshot Date": live_options.attrs.get("snapshot_date", "Unknown"),
    }


def get_open_interest_by_strike(ticker: str) -> pd.DataFrame:
    """Return call/put open interest by strike."""
    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_frame(
            ["Strike", "Call OI", "Put OI"],
            _options_unavailable_reason(ticker),
        )

    primary = _primary_expiration_options(live_options)
    oi = (
        primary.pivot_table(index="Strike", columns="Type", values="Open Interest", aggfunc="sum", fill_value=0)
        .reset_index()
        .rename(columns={"call": "Call OI", "put": "Put OI"})
    )
    if "Call OI" not in oi:
        oi["Call OI"] = 0
    if "Put OI" not in oi:
        oi["Put OI"] = 0
    oi[["Call OI", "Put OI"]] = oi[["Call OI", "Put OI"]].astype(int)
    return _format_source(oi[["Strike", "Call OI", "Put OI"]], live_options.attrs["source"], live_options.attrs.get("snapshot_date"))


def get_put_call_ratio_history(ticker: str | None = None) -> pd.DataFrame:
    """Return put/call ratio by expiration from live options or mock history."""
    if ticker is None:
        return _unavailable_frame(
            ["Date", "Put/Call Ratio"],
            "A ticker is required for Alpha Vantage historical options. Mock options data is disabled.",
        )

    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_frame(
            ["Date", "Put/Call Ratio"],
            _options_unavailable_reason(ticker),
        )

    by_expiry = live_options.pivot_table(
        index="Expiration", columns="Type", values="Open Interest", aggfunc="sum", fill_value=0
    ).reset_index()
    by_expiry["Put/Call Ratio"] = by_expiry.apply(
        lambda row: float(row.get("put", 0) / row.get("call", 0)) if row.get("call", 0) else 0,
        axis=1,
    )
    ratio = pd.DataFrame(
        {
            "Date": by_expiry["Expiration"].dt.strftime("%Y-%m-%d"),
            "Put/Call Ratio": by_expiry["Put/Call Ratio"].round(2),
        }
    )
    return _format_source(ratio, live_options.attrs["source"], live_options.attrs.get("snapshot_date"))


def get_iv_term_structure(ticker: str) -> pd.DataFrame:
    """Return IV term structure."""
    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_frame(
            ["Expiration", "Implied Volatility"],
            _options_unavailable_reason(ticker),
        )

    term = (
        live_options.dropna(subset=["Implied Volatility"])
        .groupby("Expiration")["Implied Volatility"]
        .mean()
        .reset_index()
    )
    term["Expiration"] = term["Expiration"].dt.strftime("%Y-%m-%d")
    term["Implied Volatility"] = (term["Implied Volatility"] * 100).round(2)
    return _format_source(term, live_options.attrs["source"], live_options.attrs.get("snapshot_date"))


def get_iv_rank_history(ticker: str | None = None) -> pd.DataFrame:
    """Return IV rank proxy by expiration."""
    if ticker is None:
        return _unavailable_frame(
            ["Date", "IV Rank"],
            "A ticker is required for Alpha Vantage historical options. Mock options data is disabled.",
        )

    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_frame(
            ["Date", "IV Rank"],
            _options_unavailable_reason(ticker),
        )

    term = get_iv_term_structure(ticker)
    values = term["Implied Volatility"]
    min_iv = values.min()
    max_iv = values.max()
    if max_iv == min_iv:
        term["IV Rank"] = 50.0
    else:
        term["IV Rank"] = ((values - min_iv) / (max_iv - min_iv) * 100).round(2)
    rank = term.rename(columns={"Expiration": "Date"})[["Date", "IV Rank"]]
    return _format_source(rank, live_options.attrs["source"], live_options.attrs.get("snapshot_date"))


def get_gamma_exposure(ticker: str) -> pd.DataFrame:
    """Return gamma exposure by strike."""
    live_options = _get_live_options(ticker)
    if live_options is None:
        return _unavailable_frame(
            ["Strike", "Gamma Exposure ($MM)"],
            _options_unavailable_reason(ticker),
        )

    primary = _primary_expiration_options(live_options)
    signed_gamma = primary["Gamma"].fillna(0) * primary["Open Interest"].fillna(0) * 100
    signed_gamma = signed_gamma.where(primary["Type"] == "call", -signed_gamma)
    gex = (
        pd.DataFrame({"Strike": primary["Strike"], "Gamma Exposure ($MM)": signed_gamma / 1_000_000})
        .groupby("Strike", as_index=False)["Gamma Exposure ($MM)"]
        .sum()
    )
    gex["Gamma Exposure ($MM)"] = gex["Gamma Exposure ($MM)"].round(4)
    return _format_source(gex, live_options.attrs["source"], live_options.attrs.get("snapshot_date"))


def get_dealer_positioning() -> pd.DataFrame:
    """Return dealer positioning summary."""
    return _unavailable_frame(
        ["Metric", "Value", "Interpretation"],
        "Dealer positioning requires a dedicated model and is not shown with mock data.",
    )


def get_options_flow() -> pd.DataFrame:
    """Return options flow tape."""
    return _unavailable_frame(
        ["Time", "Side", "Strike", "Expiry", "Premium", "Sentiment"],
        "Live options flow is not available from Alpha Vantage HISTORICAL_OPTIONS and mock data is disabled.",
    )


def _calculate_max_pain(options: pd.DataFrame) -> float:
    """Estimate max pain from call/put open interest by strike."""
    oi = options.pivot_table(index="Strike", columns="Type", values="Open Interest", aggfunc="sum", fill_value=0)
    strikes = oi.index.to_numpy(dtype=float)
    call_oi = oi["call"].to_numpy(dtype=float) if "call" in oi else np.zeros(len(strikes))
    put_oi = oi["put"].to_numpy(dtype=float) if "put" in oi else np.zeros(len(strikes))
    candidate_prices = strikes[:, None]
    strike_prices = strikes[None, :]
    call_payout = np.maximum(candidate_prices - strike_prices, 0) @ call_oi
    put_payout = np.maximum(strike_prices - candidate_prices, 0) @ put_oi
    total_payout = call_payout + put_payout
    return float(strikes[int(np.argmin(total_payout))])


def _atm_implied_volatility(options: pd.DataFrame) -> float:
    """Return a simple ATM IV proxy from the most balanced delta contract."""
    candidates = options.dropna(subset=["Implied Volatility", "Delta"]).copy()
    if candidates.empty:
        return float(options["Implied Volatility"].dropna().mean())
    candidates["Delta Distance"] = (candidates["Delta"].abs() - 0.5).abs()
    return float(candidates.sort_values("Delta Distance").iloc[0]["Implied Volatility"])


def _percent_rank(value: float, values: pd.Series) -> float:
    """Return the percentile rank of a value within a numeric series."""
    clean = values.dropna()
    if clean.empty:
        return 0
    return float((clean <= value).mean() * 100)


def _term_iv_nearest_days(options: pd.DataFrame, target_days: int) -> float:
    """Return average IV for the expiration nearest a target days-to-expiry."""
    snapshot_date = options["Date"].dropna().max()
    term = options.dropna(subset=["Implied Volatility"]).copy()
    term["Days To Expiry"] = (term["Expiration"] - snapshot_date).dt.days
    term = term[term["Days To Expiry"] >= 0]
    if term.empty:
        return float(options["Implied Volatility"].dropna().mean())
    nearest_days = (term["Days To Expiry"] - target_days).abs().min()
    nearest = term[(term["Days To Expiry"] - target_days).abs() == nearest_days]
    return float(nearest["Implied Volatility"].mean())
