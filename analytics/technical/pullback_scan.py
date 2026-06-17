"""Pullback scan analytics — uptrend pullbacks and sideways support reversals."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analytics.technical.engine import (
    calculate_adx,
    calculate_macd,
    calculate_rsi,
    calculate_simple_moving_average,
)


@dataclass(frozen=True)
class PullbackScanConfig:
    """Tunable thresholds for pullback pattern detection."""

    ma_fast: int = 20
    ma_slow: int = 40
    history_periods: int = 90
    slope_lookback: int = 5
    red_candle_lookback: int = 8
    min_red_candles: int = 3
    ma_proximity_pct: float = 2.5
    prior_rsi_lookback: int = 12
    min_prior_rsi: float = 55.0
    support_lookback: int = 20
    support_proximity_pct: float = 4.0
    rsi_period: int = 9
    min_history_rows: int = 45
    include_sideways_support: bool = True
    max_ma_slope_pct: float = 0.8
    max_ma_spread_pct: float = 3.5
    range_low_pct: float = 30.0
    prior_hammer_lookback: int = 8
    refinement_rsi_min: float = 30.0
    refinement_rsi_max: float = 58.0


def evaluate_pullback_setup(history: pd.DataFrame, config: PullbackScanConfig | None = None) -> dict | None:
    """Return pullback metrics when the symbol matches an uptrend or sideways-support setup."""
    cfg = config or PullbackScanConfig()
    frame = history.sort_values("Date").reset_index(drop=True)
    if len(frame) < cfg.min_history_rows:
        return None

    close = frame["Close"]
    ma_fast = calculate_simple_moving_average(close, cfg.ma_fast)
    ma_slow = calculate_simple_moving_average(close, cfg.ma_slow)
    rsi = calculate_rsi(close, window=cfg.rsi_period)

    latest = frame.iloc[-1]
    latest_close = float(latest["Close"])
    latest_ma_fast = float(ma_fast.iloc[-1])
    latest_ma_slow = float(ma_slow.iloc[-1])
    latest_rsi = float(rsi.iloc[-1])

    if pd.isna(latest_ma_fast) or pd.isna(latest_ma_slow) or pd.isna(latest_rsi):
        return None

    trend = _trend_metrics(ma_fast, ma_slow, cfg.slope_lookback)
    sideways = _sideways_metrics(ma_fast, ma_slow, latest_close, cfg)
    ma_zone = _ma_pullback_zone(latest_close, latest_ma_fast, latest_ma_slow, cfg.ma_proximity_pct)
    red_stats = _red_candle_stats(frame, cfg.red_candle_lookback, cfg.min_red_candles)
    prior_rsi = _prior_rsi_before_pullback(rsi, red_stats["red_indices"], cfg.prior_rsi_lookback, cfg.min_prior_rsi)
    support = _support_proximity(frame, latest_close, cfg.support_lookback, cfg.support_proximity_pct)
    range_position = _range_position(frame, latest_close, cfg.support_lookback, cfg.range_low_pct)
    hammer = _is_hammer_candle(latest)
    support_hammers = _support_hammer_stats(
        frame,
        support_level=support["support_level"],
        proximity_pct=cfg.support_proximity_pct,
        lookback=cfg.prior_hammer_lookback,
    )

    uptrend_setup = trend["uptrend"] and ma_zone["in_zone"] and red_stats["enough_reds"]
    sideways_setup = (
        cfg.include_sideways_support
        and sideways["is_sideways"]
        and support["near_support"]
        and range_position["in_lower_range"]
        and (red_stats["red_count"] >= 1 or hammer or support_hammers["count"] >= 1)
    )
    if not (uptrend_setup or sideways_setup):
        return None

    setup_type = "Uptrend Pullback" if uptrend_setup else "Sideways Support"
    if uptrend_setup and sideways_setup:
        setup_type = "Uptrend Pullback + Sideways Support"

    pattern_score = _pattern_score(
        setup_type=setup_type,
        trend=trend,
        sideways=sideways,
        ma_zone=ma_zone,
        red_stats=red_stats,
        prior_rsi=prior_rsi,
        support=support,
        range_position=range_position,
        hammer=hammer,
        support_hammers=support_hammers,
    )
    avg_volume = int(frame["Volume"].tail(20).mean())
    latest_volume = int(latest["Volume"])

    return {
        "Ticker": None,
        "Setup Type": setup_type,
        "Date": latest["Date"].strftime("%Y-%m-%d") if hasattr(latest["Date"], "strftime") else str(latest["Date"]),
        "Price": round(latest_close, 2),
        "Change %": round(_session_change_pct(latest), 2),
        "Volume": latest_volume,
        "Avg Volume 20D": avg_volume,
        "RSI": round(latest_rsi, 2),
        "Prior RSI High": round(prior_rsi["max_rsi"], 2) if prior_rsi["was_elevated"] else None,
        "MA20": round(latest_ma_fast, 2),
        "MA40": round(latest_ma_slow, 2),
        "Distance to MA20 %": round(ma_zone["distance_to_ma20_pct"], 2),
        "Red Candles": red_stats["red_count"],
        "Near Support": support["near_support"],
        "Support Level": round(support["support_level"], 2) if support["support_level"] is not None else None,
        "Distance to Support %": round(support["distance_pct"], 2) if support["distance_pct"] is not None else None,
        "Range Position %": round(range_position["position_pct"], 2),
        "Hammer": hammer,
        "Prior Support Hammers": support_hammers["count"],
        "Pattern Score": pattern_score,
        "Refinement Score": None,
        "Total Score": pattern_score,
        "MACD Reversal": None,
        "ADX Rising": None,
        "RSI In Pullback Zone": None,
        "Notes": _build_notes(
            setup_type,
            trend,
            sideways,
            ma_zone,
            red_stats,
            prior_rsi,
            support,
            range_position,
            hammer,
            support_hammers,
        ),
    }


def score_pullback_refinement(
    history: pd.DataFrame,
    pattern_row: dict,
    config: PullbackScanConfig | None = None,
) -> dict:
    """Add MACD, ADX, and RSI-zone refinement to a previously matched setup."""
    cfg = config or PullbackScanConfig()
    frame = history.sort_values("Date").reset_index(drop=True)
    if frame.empty:
        return {**pattern_row, "Refinement Score": 0, "Total Score": pattern_row.get("Pattern Score", 0)}

    rsi_series = calculate_rsi(frame["Close"], window=cfg.rsi_period)
    latest_rsi = float(rsi_series.iloc[-1])
    macd_history = calculate_macd(frame["Close"]).tail(5)
    adx_history = pd.DataFrame({"ADX": calculate_adx(frame["High"], frame["Low"], frame["Close"])}).tail(5)

    macd_reversal = has_macd_oversold_signal(macd_history)
    adx_rising = is_adx_rising(adx_history)
    rsi_in_zone = cfg.refinement_rsi_min <= latest_rsi <= cfg.refinement_rsi_max

    macd_score = 15 if macd_reversal else 0
    adx_score = 15 if adx_rising else 0
    rsi_score = 10 if rsi_in_zone else 0
    refinement_score = macd_score + adx_score + rsi_score

    pattern_score = int(pattern_row.get("Pattern Score", pattern_row.get("Pullback Score", 0)) or 0)
    total_score = min(100, pattern_score + refinement_score)

    macd_latest = macd_history.iloc[-1] if not macd_history.empty else pd.Series(dtype="float64")
    adx_latest = adx_history.iloc[-1] if not adx_history.empty else pd.Series(dtype="float64")

    return {
        **pattern_row,
        "RSI": round(latest_rsi, 2),
        "Pattern Score": pattern_score,
        "Refinement Score": refinement_score,
        "Total Score": total_score,
        "MACD Reversal": macd_reversal,
        "ADX Rising": adx_rising,
        "RSI In Pullback Zone": rsi_in_zone,
        "MACD": _optional_round(macd_latest.get("MACD")),
        "MACD Signal": _optional_round(macd_latest.get("MACD Signal")),
        "MACD Hist": _optional_round(macd_latest.get("MACD Hist")),
        "ADX": _optional_round(adx_latest.get("ADX")),
    }


def has_macd_oversold_signal(macd_history: pd.DataFrame) -> bool:
    """Treat bullish MACD momentum below zero as an oversold reversal signal."""
    if macd_history.empty:
        return False

    latest = macd_history.iloc[-1]
    macd_value = float(latest["MACD"])
    signal_value = float(latest["MACD Signal"])
    hist_value = float(latest["MACD Hist"])
    return macd_value < 0 and macd_value > signal_value and hist_value > 0


def is_adx_rising(adx_history: pd.DataFrame) -> bool:
    """Return True when the latest ADX is above the prior ADX value."""
    if len(adx_history) < 2:
        return False

    latest_adx = float(adx_history["ADX"].iloc[-1])
    previous_adx = float(adx_history["ADX"].iloc[-2])
    return latest_adx > previous_adx


def _trend_metrics(ma_fast: pd.Series, ma_slow: pd.Series, slope_lookback: int) -> dict:
    """Check rising 20/40 MA structure with constructive slope alignment."""
    fast_latest = float(ma_fast.iloc[-1])
    slow_latest = float(ma_slow.iloc[-1])
    fast_prior = float(ma_fast.iloc[-1 - slope_lookback])
    slow_prior = float(ma_slow.iloc[-1 - slope_lookback])

    fast_slope = fast_latest - fast_prior
    slow_slope = slow_latest - slow_prior
    stacked = fast_latest > slow_latest
    rising = fast_slope > 0 and slow_slope > 0
    parallel = slow_slope != 0 and 0.35 <= (fast_slope / slow_slope) <= 2.75

    return {
        "uptrend": stacked and rising and parallel,
        "fast_slope": fast_slope,
        "slow_slope": slow_slope,
        "parallel": parallel,
    }


def _sideways_metrics(
    ma_fast: pd.Series,
    ma_slow: pd.Series,
    close: float,
    config: PullbackScanConfig,
) -> dict:
    """Detect compressed, flat moving averages typical of sideways markets."""
    fast_latest = float(ma_fast.iloc[-1])
    slow_latest = float(ma_slow.iloc[-1])
    fast_prior = float(ma_fast.iloc[-1 - config.slope_lookback])
    slow_prior = float(ma_slow.iloc[-1 - config.slope_lookback])

    fast_slope_pct = ((fast_latest - fast_prior) / fast_latest) * 100 if fast_latest else 0.0
    slow_slope_pct = ((slow_latest - slow_prior) / slow_latest) * 100 if slow_latest else 0.0
    spread_pct = abs(fast_latest - slow_latest) / slow_latest * 100 if slow_latest else 0.0
    flat = abs(fast_slope_pct) <= config.max_ma_slope_pct and abs(slow_slope_pct) <= config.max_ma_slope_pct
    compressed = spread_pct <= config.max_ma_spread_pct

    return {
        "is_sideways": flat and compressed,
        "fast_slope_pct": fast_slope_pct,
        "slow_slope_pct": slow_slope_pct,
        "spread_pct": spread_pct,
    }


def _ma_pullback_zone(close: float, ma_fast: float, ma_slow: float, proximity_pct: float) -> dict:
    """Price should be at the 20 MA or between the 20 and 40 MA during a pullback."""
    tolerance = proximity_pct / 100.0
    distance_to_ma20_pct = ((close - ma_fast) / ma_fast) * 100 if ma_fast else 0.0
    near_ma20 = abs(distance_to_ma20_pct) <= proximity_pct
    between_mas = ma_slow <= close <= ma_fast * (1 + tolerance)
    slightly_above_ma20 = ma_fast <= close <= ma_fast * (1 + tolerance)
    in_zone = near_ma20 or between_mas or slightly_above_ma20
    return {
        "in_zone": in_zone,
        "distance_to_ma20_pct": distance_to_ma20_pct,
        "near_ma20": near_ma20,
        "between_mas": between_mas,
    }


def _red_candle_stats(frame: pd.DataFrame, lookback: int, minimum: int) -> dict:
    """Count recent red candles before the latest session."""
    recent = frame.iloc[-(lookback + 1):-1] if len(frame) > lookback + 1 else frame.iloc[:-1]
    red_mask = recent["Close"] < recent["Open"]
    red_indices = recent.index[red_mask].tolist()
    red_count = int(red_mask.sum())
    return {
        "enough_reds": red_count >= minimum,
        "red_count": red_count,
        "red_indices": red_indices,
    }


def _prior_rsi_before_pullback(
    rsi: pd.Series,
    red_indices: list[int],
    lookback: int,
    min_prior_rsi: float,
) -> dict:
    """RSI should have been elevated before the recent red-candle pullback."""
    if not red_indices:
        return {"was_elevated": False, "max_rsi": float("nan")}

    first_red_index = min(red_indices)
    start = max(0, first_red_index - lookback)
    end = max(0, first_red_index - 1)
    if end < start:
        return {"was_elevated": False, "max_rsi": float("nan")}

    prior_window = rsi.iloc[start : end + 1]
    if prior_window.empty:
        return {"was_elevated": False, "max_rsi": float("nan")}

    max_rsi = float(prior_window.max())
    return {"was_elevated": max_rsi >= min_prior_rsi, "max_rsi": max_rsi}


def _support_proximity(frame: pd.DataFrame, close: float, lookback: int, proximity_pct: float) -> dict:
    """Check whether price is retesting a recent support zone."""
    recent = frame.tail(lookback)
    support_level = float(recent["Low"].min())
    if support_level <= 0:
        return {"near_support": False, "support_level": None, "distance_pct": None}

    distance_pct = ((close - support_level) / support_level) * 100
    near_support = 0 <= distance_pct <= proximity_pct
    return {
        "near_support": near_support,
        "support_level": support_level,
        "distance_pct": distance_pct,
    }


def _range_position(frame: pd.DataFrame, close: float, lookback: int, low_range_pct: float) -> dict:
    """Measure where price sits inside the recent trading range."""
    recent = frame.tail(lookback)
    range_high = float(recent["High"].max())
    range_low = float(recent["Low"].min())
    if range_high <= range_low:
        return {"in_lower_range": False, "position_pct": 50.0}

    position_pct = ((close - range_low) / (range_high - range_low)) * 100
    return {
        "in_lower_range": position_pct <= low_range_pct,
        "position_pct": position_pct,
    }


def _support_hammer_stats(
    frame: pd.DataFrame,
    support_level: float | None,
    proximity_pct: float,
    lookback: int,
) -> dict:
    """Count prior hammer candles that tested the support zone."""
    if support_level is None or support_level <= 0:
        return {"count": 0, "dates": []}

    recent = frame.iloc[-(lookback + 1):-1] if len(frame) > lookback + 1 else frame.iloc[:-1]
    tolerance = proximity_pct * 1.5
    dates: list[str] = []
    for _, candle in recent.iterrows():
        if not _is_hammer_candle(candle):
            continue
        low_distance_pct = ((float(candle["Low"]) - support_level) / support_level) * 100
        if -0.5 <= low_distance_pct <= tolerance:
            date_value = candle["Date"]
            dates.append(date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value))

    return {"count": len(dates), "dates": dates}


def _is_hammer_candle(candle: pd.Series) -> bool:
    """Detect hammer-like rejection with a long lower shadow."""
    open_price = float(candle["Open"])
    high_price = float(candle["High"])
    low_price = float(candle["Low"])
    close_price = float(candle["Close"])
    candle_range = high_price - low_price
    body = abs(close_price - open_price)
    if candle_range <= 0:
        return False

    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    return lower_shadow >= body * 2 and upper_shadow <= max(body, candle_range * 0.15)


def _pattern_score(
    setup_type: str,
    trend: dict,
    sideways: dict,
    ma_zone: dict,
    red_stats: dict,
    prior_rsi: dict,
    support: dict,
    range_position: dict,
    hammer: bool,
    support_hammers: dict,
) -> int:
    """Score the initial pattern out of 65 before MACD/ADX refinement."""
    score = 0
    if "Uptrend" in setup_type:
        score += 20 if trend["uptrend"] else 0
        score += 15 if ma_zone["in_zone"] else 0
    if "Sideways" in setup_type:
        score += 20 if sideways["is_sideways"] else 0
        score += 10 if range_position["in_lower_range"] else 0

    score += 10 if red_stats["enough_reds"] else min(8, red_stats["red_count"] * 2)
    score += 10 if prior_rsi["was_elevated"] else 0
    score += 10 if support["near_support"] else 0
    score += 5 if hammer else 0
    score += min(10, support_hammers["count"] * 5)
    return min(score, 65)


def _optional_round(value: object, digits: int = 4) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _session_change_pct(candle: pd.Series) -> float:
    open_price = float(candle["Open"])
    close_price = float(candle["Close"])
    if open_price == 0:
        return 0.0
    return ((close_price - open_price) / open_price) * 100


def _build_notes(
    setup_type: str,
    trend: dict,
    sideways: dict,
    ma_zone: dict,
    red_stats: dict,
    prior_rsi: dict,
    support: dict,
    range_position: dict,
    hammer: bool,
    support_hammers: dict,
) -> str:
    notes: list[str] = [setup_type]
    if trend["uptrend"]:
        notes.append("20 MA above 40 MA with rising slopes")
    if sideways["is_sideways"]:
        notes.append("Sideways MA compression")
    if ma_zone["between_mas"]:
        notes.append("Price between 20 and 40 MA")
    elif ma_zone["near_ma20"]:
        notes.append("Price near 20 MA")
    if range_position["in_lower_range"]:
        notes.append("Price in lower third of recent range")
    if red_stats["red_count"] >= 1:
        notes.append(f"{red_stats['red_count']} recent red candles")
    if prior_rsi["was_elevated"]:
        notes.append("RSI was elevated before pullback")
    if support["near_support"]:
        notes.append("Near recent support")
    if support_hammers["count"] > 0:
        notes.append(f"{support_hammers['count']} prior hammer(s) at support")
    if hammer:
        notes.append("Latest candle looks like a hammer")
    return "; ".join(notes)
