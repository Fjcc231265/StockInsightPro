"""Breakout scan analytics — closes above recent highs with volume and momentum confirmation."""

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
class BreakoutScanConfig:
    """Tunable thresholds for breakout pattern detection."""

    ma_fast: int = 20
    ma_slow: int = 40
    history_periods: int = 90
    breakout_lookback: int = 20
    min_volume_multiple: float = 1.5
    rsi_period: int = 9
    rsi_min: float = 55.0
    rsi_max: float = 75.0
    min_history_rows: int = 45
    require_above_mas: bool = True
    refinement_rsi_min: float = 55.0
    refinement_rsi_max: float = 80.0


def evaluate_breakout_setup(history: pd.DataFrame, config: BreakoutScanConfig | None = None) -> dict | None:
    """Return breakout metrics when close clears the prior N-day high with volume support."""
    cfg = config or BreakoutScanConfig()
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

    prior = frame.iloc[-(cfg.breakout_lookback + 1) : -1]
    if prior.empty:
        return None
    resistance = float(prior["High"].max())
    if resistance <= 0:
        return None

    cleared_resistance = latest_close > resistance
    above_mas = latest_close > latest_ma_fast and latest_close > latest_ma_slow
    if cfg.require_above_mas and not above_mas:
        return None
    if not cleared_resistance:
        return None

    avg_volume = float(frame["Volume"].tail(20).mean()) if "Volume" in frame.columns else 0.0
    latest_volume = float(latest.get("Volume", 0) or 0)
    volume_multiple = (latest_volume / avg_volume) if avg_volume else 0.0
    volume_expanding = volume_multiple >= cfg.min_volume_multiple
    rsi_in_band = cfg.rsi_min <= latest_rsi <= cfg.rsi_max

    # Require volume expansion for a clean Stage 1 match; RSI band is scored but not mandatory.
    if not volume_expanding:
        return None

    distance_above_pct = ((latest_close - resistance) / resistance) * 100
    pattern_score = _pattern_score(
        distance_above_pct=distance_above_pct,
        volume_multiple=volume_multiple,
        above_mas=above_mas,
        rsi_in_band=rsi_in_band,
        latest_rsi=latest_rsi,
        cfg=cfg,
    )

    setup_type = "Breakout above prior high"
    if above_mas and rsi_in_band:
        setup_type = "Confirmed breakout"

    return {
        "Ticker": None,
        "Setup Type": setup_type,
        "Date": latest["Date"].strftime("%Y-%m-%d") if hasattr(latest["Date"], "strftime") else str(latest["Date"]),
        "Price": round(latest_close, 2),
        "Change %": round(_session_change_pct(latest), 2),
        "Volume": int(latest_volume),
        "Avg Volume 20D": int(avg_volume),
        "Volume Multiple": round(volume_multiple, 2),
        "RSI": round(latest_rsi, 2),
        "MA20": round(latest_ma_fast, 2),
        "MA40": round(latest_ma_slow, 2),
        "Resistance": round(resistance, 2),
        "Distance Above Resistance %": round(distance_above_pct, 2),
        "Above MAs": above_mas,
        "RSI In Breakout Band": rsi_in_band,
        "Pattern Score": pattern_score,
        "Refinement Score": None,
        "Total Score": pattern_score,
        "MACD Positive Turn": None,
        "ADX Rising": None,
        "RSI Momentum Zone": None,
        "Notes": _build_notes(
            resistance=resistance,
            distance_above_pct=distance_above_pct,
            volume_multiple=volume_multiple,
            above_mas=above_mas,
            rsi_in_band=rsi_in_band,
            latest_rsi=latest_rsi,
        ),
    }


def score_breakout_refinement(
    history: pd.DataFrame,
    pattern_row: dict,
    config: BreakoutScanConfig | None = None,
) -> dict:
    """Add MACD turn, ADX rising, and RSI momentum refinement to a breakout match."""
    cfg = config or BreakoutScanConfig()
    frame = history.sort_values("Date").reset_index(drop=True)
    if frame.empty:
        return {**pattern_row, "Refinement Score": 0, "Total Score": pattern_row.get("Pattern Score", 0)}

    rsi_series = calculate_rsi(frame["Close"], window=cfg.rsi_period)
    latest_rsi = float(rsi_series.iloc[-1])
    macd_history = calculate_macd(frame["Close"]).tail(5)
    adx_history = pd.DataFrame({"ADX": calculate_adx(frame["High"], frame["Low"], frame["Close"])}).tail(5)

    macd_positive_turn = has_macd_positive_turn(macd_history)
    adx_rising = is_adx_rising(adx_history)
    rsi_momentum = cfg.refinement_rsi_min <= latest_rsi <= cfg.refinement_rsi_max

    macd_score = 15 if macd_positive_turn else 0
    adx_score = 15 if adx_rising else 0
    rsi_score = 10 if rsi_momentum else 0
    refinement_score = macd_score + adx_score + rsi_score

    pattern_score = int(pattern_row.get("Pattern Score", 0) or 0)
    total_score = min(100, pattern_score + refinement_score)

    macd_latest = macd_history.iloc[-1] if not macd_history.empty else pd.Series(dtype="float64")
    adx_latest = adx_history.iloc[-1] if not adx_history.empty else pd.Series(dtype="float64")

    return {
        **pattern_row,
        "RSI": round(latest_rsi, 2),
        "Pattern Score": pattern_score,
        "Refinement Score": refinement_score,
        "Total Score": total_score,
        "MACD Positive Turn": macd_positive_turn,
        "ADX Rising": adx_rising,
        "RSI Momentum Zone": rsi_momentum,
        "MACD": _optional_round(macd_latest.get("MACD")),
        "MACD Signal": _optional_round(macd_latest.get("MACD Signal")),
        "MACD Hist": _optional_round(macd_latest.get("MACD Hist")),
        "ADX": _optional_round(adx_latest.get("ADX")),
    }


def has_macd_positive_turn(macd_history: pd.DataFrame) -> bool:
    """Return True when MACD histogram is positive and improving through the signal line."""
    if macd_history.empty or len(macd_history) < 2:
        return False
    latest = macd_history.iloc[-1]
    previous = macd_history.iloc[-2]
    macd_value = float(latest["MACD"])
    signal_value = float(latest["MACD Signal"])
    hist_value = float(latest["MACD Hist"])
    prior_hist = float(previous["MACD Hist"])
    return hist_value > 0 and hist_value >= prior_hist and macd_value >= signal_value


def is_adx_rising(adx_history: pd.DataFrame) -> bool:
    """Return True when the latest ADX is above the prior ADX value."""
    if len(adx_history) < 2:
        return False
    latest_adx = float(adx_history["ADX"].iloc[-1])
    previous_adx = float(adx_history["ADX"].iloc[-2])
    return latest_adx > previous_adx


def _pattern_score(
    *,
    distance_above_pct: float,
    volume_multiple: float,
    above_mas: bool,
    rsi_in_band: bool,
    latest_rsi: float,
    cfg: BreakoutScanConfig,
) -> int:
    score = 35  # base for clearing resistance with volume
    if above_mas:
        score += 15
    if rsi_in_band:
        score += 15
    elif latest_rsi > cfg.rsi_max:
        score += 5  # strong momentum, slightly overextended
    if volume_multiple >= cfg.min_volume_multiple * 2:
        score += 15
    elif volume_multiple >= cfg.min_volume_multiple * 1.25:
        score += 10
    else:
        score += 5
    if 0 < distance_above_pct <= 3:
        score += 10  # fresh breakout, not extended
    elif 3 < distance_above_pct <= 6:
        score += 5
    return min(65, score)


def _build_notes(
    *,
    resistance: float,
    distance_above_pct: float,
    volume_multiple: float,
    above_mas: bool,
    rsi_in_band: bool,
    latest_rsi: float,
) -> str:
    parts = [
        f"Cleared prior high ${resistance:.2f} by {distance_above_pct:.2f}%",
        f"volume {volume_multiple:.2f}x the 20-day average",
    ]
    if above_mas:
        parts.append("price above MA20 and MA40")
    else:
        parts.append("price not fully above both MAs")
    if rsi_in_band:
        parts.append(f"RSI {latest_rsi:.1f} inside breakout band")
    else:
        parts.append(f"RSI {latest_rsi:.1f} outside preferred band")
    return "; ".join(parts)


def _session_change_pct(row: pd.Series) -> float:
    open_price = float(row.get("Open", 0) or 0)
    close_price = float(row.get("Close", 0) or 0)
    if open_price <= 0:
        return 0.0
    return ((close_price - open_price) / open_price) * 100


def _optional_round(value: object, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None
