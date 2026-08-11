"""Live market context and guided trading recommendations for the Education tutor."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from analytics.technical.engine import calculate_rsi, calculate_simple_moving_average
from services.education_service import filter_rules, get_checklists, get_strategy_playbook
from services.market_data_service import get_market_breadth, get_market_overview, get_price_history, get_quote_summary
from services.options_data_service import get_options_kpis

GROWTH_SECTORS = {"Technology", "Communication Services", "Consumer Cyclical", "Financial Services"}
DEFENSIVE_SECTORS = {"Consumer Defensive", "Utilities", "Healthcare", "Real Estate"}

REGIME_TO_RULES = {
    "Risk-on": "Bullish",
    "Mildly bullish": "Bullish",
    "Neutral / range-bound": "Sideways",
    "Risk-off": "Bearish",
    "High volatility": "High volatility",
    "Event-driven": "High volatility",
}

REGIME_TO_STRATEGY_BIASES: dict[str, list[str]] = {
    "Risk-on": ["Bullish / risk-on"],
    "Mildly bullish": ["Bullish / risk-on", "Mildly bullish / income"],
    "Neutral / range-bound": ["Neutral / range-bound", "Mildly bullish / income"],
    "Risk-off": ["Bearish / risk-off", "Defensive / hedge"],
    "High volatility": ["High-movement event", "Defensive / hedge", "Bearish / risk-off"],
    "Event-driven": ["High-movement event", "Defensive / hedge"],
}

TUTOR_ACTION_CANDIDATES: list[dict[str, Any]] = [
    {
        "id": "long_stock",
        "name": "Long stock",
        "direction": "bullish",
        "regimes": {"Risk-on", "Mildly bullish"},
        "iv_preference": "any",
        "ownership": "either",
        "simulator": "Stock P&L simulator",
        "template": None,
        "lesson_id": "stock-vs-call",
        "purpose": "Participate in upside without expiration or theta.",
    },
    {
        "id": "long_call",
        "name": "Long call",
        "direction": "bullish",
        "regimes": {"Risk-on", "Mildly bullish", "Event-driven"},
        "iv_preference": "low",
        "ownership": "either",
        "simulator": "Options P&L simulator",
        "template": None,
        "lesson_id": "calls-and-puts",
        "purpose": "Defined-risk upside with less capital than stock.",
    },
    {
        "id": "bull_call_spread",
        "name": "Bull call spread",
        "direction": "bullish",
        "regimes": {"Risk-on", "Mildly bullish"},
        "iv_preference": "fair_or_high",
        "ownership": "either",
        "simulator": "Strategy payoff lab",
        "template": "Bull call spread",
        "lesson_id": "close-spread-winners",
        "purpose": "Defined-risk bullish exposure toward a realistic upside target.",
    },
    {
        "id": "covered_call",
        "name": "Covered call",
        "direction": "neutral_bullish",
        "regimes": {"Mildly bullish", "Neutral / range-bound"},
        "iv_preference": "high",
        "ownership": "required",
        "simulator": "Strategy payoff lab",
        "template": "Covered call",
        "lesson_id": "covered-call",
        "purpose": "Collect premium on shares when upside is expected to be limited.",
    },
    {
        "id": "cash_secured_put",
        "name": "Cash-secured put",
        "direction": "neutral_bullish",
        "regimes": {"Mildly bullish", "Neutral / range-bound"},
        "iv_preference": "high",
        "ownership": "not_required",
        "simulator": "Options P&L simulator",
        "template": None,
        "lesson_id": "cash-secured-put",
        "purpose": "Seek premium or a lower effective entry at an acceptable strike.",
    },
    {
        "id": "protective_put",
        "name": "Protective put",
        "direction": "hedge",
        "regimes": {"Risk-off", "High volatility", "Event-driven"},
        "iv_preference": "not_extreme",
        "ownership": "required",
        "simulator": "Strategy payoff lab",
        "template": "Protective put",
        "lesson_id": "protective-put",
        "purpose": "Keep shares while defining a downside floor.",
    },
    {
        "id": "collar",
        "name": "Collar",
        "direction": "hedge",
        "regimes": {"Risk-off", "High volatility", "Event-driven", "Neutral / range-bound"},
        "iv_preference": "fair_or_high",
        "ownership": "required",
        "simulator": "Strategy payoff lab",
        "template": "Collar",
        "lesson_id": "collar",
        "purpose": "Finance downside protection by accepting an upside cap.",
    },
    {
        "id": "bear_put_spread",
        "name": "Bear put spread",
        "direction": "bearish",
        "regimes": {"Risk-off", "High volatility"},
        "iv_preference": "fair_or_high",
        "ownership": "either",
        "simulator": "Strategy payoff lab",
        "template": "Bear put spread",
        "lesson_id": "calls-and-puts",
        "purpose": "Defined-risk bearish exposure with reduced premium versus a long put.",
    },
    {
        "id": "long_put",
        "name": "Long put",
        "direction": "bearish",
        "regimes": {"Risk-off", "Event-driven"},
        "iv_preference": "low",
        "ownership": "either",
        "simulator": "Options P&L simulator",
        "template": None,
        "lesson_id": "calls-and-puts",
        "purpose": "Defined-risk downside participation when IV is not already extreme.",
    },
    {
        "id": "iron_condor",
        "name": "Iron condor",
        "direction": "neutral",
        "regimes": {"Neutral / range-bound"},
        "iv_preference": "high",
        "ownership": "either",
        "simulator": "Strategy payoff lab",
        "template": "Custom",
        "lesson_id": "iron-condor",
        "purpose": "Defined-risk premium selling when price is expected to remain in a range.",
    },
    {
        "id": "long_straddle",
        "name": "Long straddle",
        "direction": "volatility",
        "regimes": {"Event-driven", "High volatility"},
        "iv_preference": "low",
        "ownership": "either",
        "simulator": "Strategy payoff lab",
        "template": "Long straddle",
        "lesson_id": "straddle-strangle",
        "purpose": "Seek a move in either direction that exceeds premium and IV crush.",
    },
]


def build_trading_tutor_report(
    ticker: str,
    sector_frame: pd.DataFrame | None = None,
    manual_internals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a unified tutor report from live market, sector, and symbol options data."""
    manual_internals = manual_internals or {}
    overview = get_market_overview()
    breadth = get_market_breadth()
    sectors = sector_frame if sector_frame is not None and not sector_frame.empty else pd.DataFrame()
    symbol_quote = get_quote_summary(ticker)
    options_kpis = get_options_kpis(ticker)
    index_technicals = _index_technical_snapshot("SPY")
    qqq_technicals = _index_technical_snapshot("QQQ")
    symbol_technicals = _symbol_technical_snapshot(ticker)

    market_snapshot = _build_market_snapshot(
        overview, breadth, sectors, index_technicals, qqq_technicals, manual_internals
    )
    symbol_context = _build_symbol_context(ticker, symbol_quote, options_kpis, symbol_technicals)
    regime = _classify_regime(market_snapshot, symbol_context, manual_internals)
    critical_paths = _build_critical_paths(regime, market_snapshot, symbol_context)
    strategies = _recommended_strategies(regime, symbol_context)
    checklist_hints = _build_checklist_hints(regime, market_snapshot, symbol_context)
    rules = filter_rules(REGIME_TO_RULES.get(regime["primary"], "All"), "Stocks and Options")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticker": ticker.upper(),
        "market_snapshot": market_snapshot,
        "symbol_context": symbol_context,
        "regime": regime,
        "critical_paths": critical_paths,
        "recommended_strategies": strategies,
        "checklist_hints": checklist_hints,
        "applicable_rules": rules[:8],
    }


def _index_technical_snapshot(symbol: str) -> dict[str, Any]:
    """Return simple trend diagnostics for a benchmark ETF."""
    try:
        history = get_price_history(symbol, days=120, timeframe="Daily").sort_values("Date")
        if history.empty:
            return {"symbol": symbol, "available": False}
        close = history["Close"]
        latest = float(close.iloc[-1])
        ma20 = float(calculate_simple_moving_average(close, 20).iloc[-1])
        ma40 = float(calculate_simple_moving_average(close, 40).iloc[-1])
        rsi = float(calculate_rsi(close, 14).iloc[-1])
        week_return = _period_return_pct(close, 5)
        trend = "Uptrend" if latest > ma20 > ma40 else "Downtrend" if latest < ma20 < ma40 else "Mixed"
        return {
            "symbol": symbol,
            "available": True,
            "price": round(latest, 2),
            "ma20": round(ma20, 2),
            "ma40": round(ma40, 2),
            "rsi14": round(rsi, 1),
            "week_return_pct": round(week_return, 2),
            "trend": trend,
            "source": history.attrs.get("source", "Daily OHLC"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"symbol": symbol, "available": False, "error": str(exc)}


def _period_return_pct(close: pd.Series, periods_back: int) -> float:
    latest = float(close.iloc[-1])
    if len(close) <= periods_back:
        base = float(close.iloc[0])
    else:
        base = float(close.iloc[-periods_back - 1])
    return ((latest - base) / base) * 100 if base else 0.0


def _symbol_technical_snapshot(symbol: str) -> dict[str, Any]:
    """Return trend, momentum, volume, and nearby-level evidence for the active symbol."""
    try:
        history = get_price_history(symbol, days=260, timeframe="Daily").sort_values("Date")
        if history.empty:
            return {"available": False}

        close = pd.to_numeric(history["Close"], errors="coerce").dropna()
        if close.empty:
            return {"available": False}
        latest = float(close.iloc[-1])
        ma20 = float(calculate_simple_moving_average(close, 20).iloc[-1])
        ma50 = float(calculate_simple_moving_average(close, 50).iloc[-1])
        ma200 = float(calculate_simple_moving_average(close, 200).iloc[-1]) if len(close) >= 200 else None
        rsi = float(calculate_rsi(close, 14).iloc[-1])
        recent_20 = history.tail(20)
        support = float(pd.to_numeric(recent_20["Low"], errors="coerce").min())
        resistance = float(pd.to_numeric(recent_20["High"], errors="coerce").max())
        high_52w = float(pd.to_numeric(history.tail(252)["High"], errors="coerce").max())
        low_52w = float(pd.to_numeric(history.tail(252)["Low"], errors="coerce").min())

        volume = pd.to_numeric(history.get("Volume"), errors="coerce").dropna()
        relative_volume = None
        if not volume.empty:
            average_volume = float(volume.tail(20).mean())
            relative_volume = float(volume.iloc[-1] / average_volume) if average_volume else None

        if ma200 is not None and latest > ma20 > ma50 > ma200:
            trend = "Strong uptrend"
            trend_score = 2
        elif latest > ma20 and latest > ma50:
            trend = "Uptrend"
            trend_score = 1
        elif ma200 is not None and latest < ma20 < ma50 < ma200:
            trend = "Strong downtrend"
            trend_score = -2
        elif latest < ma20 and latest < ma50:
            trend = "Downtrend"
            trend_score = -1
        else:
            trend = "Mixed / range"
            trend_score = 0

        momentum = "Overbought" if rsi >= 70 else "Oversold" if rsi <= 30 else "Positive" if rsi >= 55 else "Weak" if rsi <= 45 else "Balanced"
        return {
            "available": True,
            "price": round(latest, 2),
            "trend": trend,
            "trend_score": trend_score,
            "momentum": momentum,
            "rsi14": round(rsi, 1),
            "ma20": round(ma20, 2),
            "ma50": round(ma50, 2),
            "ma200": round(ma200, 2) if ma200 is not None else None,
            "week_return_pct": round(_period_return_pct(close, 5), 2),
            "month_return_pct": round(_period_return_pct(close, 21), 2),
            "quarter_return_pct": round(_period_return_pct(close, 63), 2),
            "relative_volume": round(relative_volume, 2) if relative_volume is not None else None,
            "support_20d": round(support, 2),
            "resistance_20d": round(resistance, 2),
            "support_distance_pct": round(((support - latest) / latest) * 100, 2) if latest else None,
            "resistance_distance_pct": round(((resistance - latest) / latest) * 100, 2) if latest else None,
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "source": history.attrs.get("source", "Daily OHLC"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": str(exc)}


def _build_market_snapshot(
    overview: pd.DataFrame,
    breadth: pd.DataFrame,
    sectors: pd.DataFrame,
    index_technicals: dict[str, Any],
    qqq_technicals: dict[str, Any],
    manual_internals: dict[str, Any],
) -> dict[str, Any]:
    indices = []
    vix_row = None
    for _, row in overview.iterrows():
        label = str(row.get("Index", ""))
        entry = {
            "name": label,
            "value": row.get("Value"),
            "change_pct": float(row.get("Change %", 0.0) or 0.0),
        }
        indices.append(entry)
        if "VIX" in label.upper():
            vix_row = entry

    breadth_rows = breadth.to_dict("records") if not breadth.empty else []
    sector_leaders, sector_laggards, rotation = _sector_leadership(sectors)

    internals = {
        "vix_level": vix_row["value"] if vix_row else None,
        "vix_change_pct": vix_row["change_pct"] if vix_row else None,
        "vix_signal": _vix_signal(vix_row),
        "breadth_rows": breadth_rows,
        "breadth_signal": _breadth_aggregate_signal(breadth_rows),
        "manual_tick": manual_internals.get("tick"),
        "manual_trin": manual_internals.get("trin"),
        "manual_adv_decline": manual_internals.get("adv_decline"),
        "manual_note": (
            "TICK and TRIN are optional manual inputs. Live TICK/TRIN feeds are not wired yet; "
            "use your platform values when available."
        ),
    }
    if manual_internals.get("tick") is not None:
        tick = float(manual_internals["tick"])
        internals["tick_signal"] = "Positive pressure" if tick > 200 else "Negative pressure" if tick < -200 else "Neutral"
    if manual_internals.get("trin") is not None:
        trin = float(manual_internals["trin"])
        internals["trin_signal"] = "Risk-off skew" if trin > 1.2 else "Risk-on skew" if trin < 0.8 else "Balanced"

    return {
        "source": overview.attrs.get("source", "Market overview"),
        "indices": indices,
        "index_technicals": index_technicals,
        "qqq_technicals": qqq_technicals,
        "internals": internals,
        "sector_leaders": sector_leaders,
        "sector_laggards": sector_laggards,
        "sector_rotation": rotation,
        "sectors_available": not sectors.empty,
        "sector_source": sectors.attrs.get("source", "") if not sectors.empty else "",
    }


def _sector_leadership(sectors: pd.DataFrame) -> tuple[list[dict], list[dict], dict[str, Any]]:
    if sectors.empty or "Sector" not in sectors.columns:
        return [], [], {"summary": "Sector data unavailable", "growth_avg_1m": None, "defensive_avg_1m": None}

    frame = sectors.copy()
    sort_col = "1M %" if "1M %" in frame.columns else "1W %" if "1W %" in frame.columns else None
    if sort_col is None:
        return [], [], {"summary": "Sector performance columns unavailable"}

    frame[sort_col] = pd.to_numeric(frame[sort_col], errors="coerce").fillna(0.0)
    leaders = frame.nlargest(3, sort_col)[["Sector", sort_col]].to_dict("records")
    laggards = frame.nsmallest(3, sort_col)[["Sector", sort_col]].to_dict("records")

    growth = frame[frame["Sector"].isin(GROWTH_SECTORS)][sort_col]
    defensive = frame[frame["Sector"].isin(DEFENSIVE_SECTORS)][sort_col]
    growth_avg = float(growth.mean()) if not growth.empty else 0.0
    defensive_avg = float(defensive.mean()) if not defensive.empty else 0.0
    if growth_avg - defensive_avg > 1.5:
        summary = "Growth sectors are leading — risk appetite is improving."
        leadership = "Growth leading"
    elif defensive_avg - growth_avg > 1.5:
        summary = "Defensive sectors are leading — investors are playing defense."
        leadership = "Defensive leading"
    else:
        summary = "Sector leadership is mixed — stock selection matters more than beta."
        leadership = "Mixed"

    return leaders, laggards, {
        "summary": summary,
        "leadership": leadership,
        "growth_avg_1m": round(growth_avg, 2),
        "defensive_avg_1m": round(defensive_avg, 2),
        "sort_column": sort_col,
    }


def _vix_signal(vix_row: dict[str, Any] | None) -> str:
    if not vix_row:
        return "Unknown"
    change = float(vix_row.get("change_pct", 0.0) or 0.0)
    if change <= -3:
        return "Fear easing — supports risk-on setups"
    if change >= 5:
        return "Fear rising — favor defense and defined risk"
    if change > 1:
        return "Volatility ticking up — reduce size"
    if change < -1:
        return "Volatility drifting lower — bullish structures more efficient"
    return "Volatility stable"


def _breadth_aggregate_signal(breadth_rows: list[dict]) -> str:
    if not breadth_rows:
        return "Unknown"
    bullish = sum(1 for row in breadth_rows if str(row.get("Signal", "")).lower() == "bullish")
    bearish = sum(1 for row in breadth_rows if str(row.get("Signal", "")).lower() == "bearish")
    if bullish > bearish:
        return "Participation improving"
    if bearish > bullish:
        return "Participation weakening"
    return "Mixed participation"


def _build_symbol_context(
    ticker: str,
    quote: dict,
    options_kpis: dict,
    technicals: dict[str, Any],
) -> dict[str, Any]:
    iv_rank = options_kpis.get("IV Rank")
    iv_context = _iv_context(iv_rank)
    fundamental = _fundamental_snapshot(quote, technicals)
    return {
        "ticker": ticker.upper(),
        "price": quote.get("price"),
        "change_pct": quote.get("change_pct"),
        "sector": quote.get("sector", "Unknown"),
        "name": quote.get("name", ticker.upper()),
        "options_available": iv_rank is not None and str(options_kpis.get("Source", "")).lower().find("unavailable") < 0,
        "options_kpis": options_kpis,
        "iv_context": iv_context,
        "technical": technicals,
        "fundamental": fundamental,
    }


def _fundamental_snapshot(quote: dict[str, Any], technicals: dict[str, Any]) -> dict[str, Any]:
    """Turn available company-overview fields into a concise, explainable context label."""
    pe_ratio = _optional_float(quote.get("pe_ratio"))
    peg_ratio = _optional_float(quote.get("peg_ratio"))
    profit_margin = _optional_float(quote.get("profit_margin"))
    beta = _optional_float(quote.get("beta"))
    dividend_yield = _optional_float(quote.get("dividend_yield"))
    market_cap = _optional_float(quote.get("market_cap"))
    price = _optional_float(quote.get("price"))
    high_52w = _optional_float(quote.get("52_week_high")) or _optional_float(technicals.get("high_52w"))
    low_52w = _optional_float(quote.get("52_week_low")) or _optional_float(technicals.get("low_52w"))

    evidence: list[str] = []
    cautions: list[str] = []
    score = 0
    if profit_margin is not None:
        margin_pct = profit_margin * 100 if abs(profit_margin) <= 1 else profit_margin
        if margin_pct >= 20:
            score += 2
            evidence.append(f"Strong reported profit margin ({margin_pct:.1f}%).")
        elif margin_pct >= 8:
            score += 1
            evidence.append(f"Positive reported profit margin ({margin_pct:.1f}%).")
        elif margin_pct < 0:
            score -= 2
            cautions.append(f"Negative reported profit margin ({margin_pct:.1f}%).")
    if pe_ratio is not None:
        if pe_ratio <= 0:
            score -= 1
            cautions.append("P/E is not meaningful because reported earnings are non-positive.")
        elif pe_ratio > 45:
            score -= 1
            cautions.append(f"High P/E ({pe_ratio:.1f}) raises expectation risk.")
        else:
            evidence.append(f"Reported P/E is {pe_ratio:.1f}.")
    if peg_ratio is not None and peg_ratio > 2.5:
        cautions.append(f"PEG ({peg_ratio:.1f}) implies a demanding growth valuation.")
    if beta is not None:
        (cautions if beta >= 1.5 else evidence).append(f"Beta is {beta:.2f}.")
    if price and high_52w:
        distance_from_high = ((price - high_52w) / high_52w) * 100
        if distance_from_high >= -5:
            evidence.append(f"Price is within {abs(distance_from_high):.1f}% of its 52-week high.")
        elif distance_from_high <= -25:
            cautions.append(f"Price is {abs(distance_from_high):.1f}% below its 52-week high.")

    label = "Supportive" if score >= 2 else "Fragile" if score <= -2 else "Mixed / valuation-dependent"
    return {
        "label": label,
        "score": score,
        "pe_ratio": pe_ratio,
        "peg_ratio": peg_ratio,
        "profit_margin": profit_margin,
        "beta": beta,
        "dividend_yield": dividend_yield,
        "market_cap": market_cap,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "evidence": evidence,
        "cautions": cautions,
        "source": quote.get("metadata_source", "Company overview"),
    }


def _optional_float(value: object) -> float | None:
    if value in (None, "", "None", "N/A", "n/a"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _iv_context(iv_rank: object) -> str:
    if iv_rank is None:
        return "Unknown"
    rank = float(iv_rank)
    if rank >= 80:
        return "Expensive / event-like"
    if rank >= 60:
        return "Elevated — favor spreads or premium selling"
    if rank >= 35:
        return "Fair"
    return "Low — long premium more efficient"


def _classify_regime(
    market_snapshot: dict[str, Any],
    symbol_context: dict[str, Any],
    manual_internals: dict[str, Any],
) -> dict[str, Any]:
    score = 0
    breakdown: list[dict[str, Any]] = []

    tech = market_snapshot.get("index_technicals", {})
    if tech.get("available"):
        if tech.get("trend") == "Uptrend":
            score += 2
            breakdown.append({"factor": "SPY trend", "reading": "Uptrend (price > MA20 > MA40)", "impact": +2})
        elif tech.get("trend") == "Downtrend":
            score -= 2
            breakdown.append({"factor": "SPY trend", "reading": "Downtrend (price < MA20 < MA40)", "impact": -2})
        else:
            breakdown.append({"factor": "SPY trend", "reading": "Mixed moving-average structure", "impact": 0})

    vix_change = market_snapshot.get("internals", {}).get("vix_change_pct")
    if vix_change is not None:
        if vix_change <= -2:
            score += 1
            breakdown.append({"factor": "VIX proxy move", "reading": f"{vix_change:+.1f}%", "impact": +1})
        elif vix_change >= 3:
            score -= 2
            breakdown.append({"factor": "VIX proxy move", "reading": f"{vix_change:+.1f}%", "impact": -2})
        elif vix_change > 0:
            score -= 1
            breakdown.append({"factor": "VIX proxy move", "reading": f"{vix_change:+.1f}%", "impact": -1})

    breadth_signal = market_snapshot.get("internals", {}).get("breadth_signal", "")
    if "improving" in breadth_signal.lower():
        score += 1
        breakdown.append({"factor": "Market breadth", "reading": breadth_signal, "impact": +1})
    elif "weakening" in breadth_signal.lower():
        score -= 1
        breakdown.append({"factor": "Market breadth", "reading": breadth_signal, "impact": -1})

    rotation = market_snapshot.get("sector_rotation", {})
    leadership = rotation.get("leadership")
    if leadership == "Growth leading":
        score += 1
        breakdown.append({"factor": "Sector rotation", "reading": rotation.get("summary", ""), "impact": +1})
    elif leadership == "Defensive leading":
        score -= 1
        breakdown.append({"factor": "Sector rotation", "reading": rotation.get("summary", ""), "impact": -1})

    if manual_internals.get("tick") is not None:
        tick = float(manual_internals["tick"])
        tick_impact = 1 if tick > 300 else -1 if tick < -300 else 0
        score += tick_impact
        breakdown.append({"factor": "NYSE TICK (manual)", "reading": f"{tick:+.0f}", "impact": tick_impact})
    if manual_internals.get("trin") is not None:
        trin = float(manual_internals["trin"])
        trin_impact = -1 if trin > 1.2 else 1 if trin < 0.8 else 0
        score += trin_impact
        breakdown.append({"factor": "TRIN (manual)", "reading": f"{trin:.2f}", "impact": trin_impact})

    tags: list[str] = []
    iv_context = symbol_context.get("iv_context", "Unknown")
    if iv_context in {"Elevated — favor spreads or premium selling", "Expensive / event-like"}:
        tags.append("Elevated IV")

    primary = "Neutral / range-bound"
    if score >= 3:
        primary = "Risk-on"
    elif score == 2:
        primary = "Mildly bullish"
    elif score <= -3:
        primary = "Risk-off"
    elif score == -2:
        primary = "Risk-off"

    if vix_change is not None and abs(float(vix_change)) >= 5:
        primary = "High volatility"
        tags.append("Volatility spike")
    if iv_context == "Expensive / event-like" and primary not in {"Risk-off"}:
        tags.append("Event premium")
        if score <= 0:
            primary = "Event-driven"

    confidence = "High" if abs(score) >= 3 else "Moderate" if abs(score) >= 1 else "Low"
    summary = _regime_summary(primary, score, market_snapshot, symbol_context)

    return {
        "primary": primary,
        "tags": tags,
        "score": score,
        "confidence": confidence,
        "breakdown": breakdown,
        "summary": summary,
        "rules_regime": REGIME_TO_RULES.get(primary, "All"),
    }


def _regime_summary(
    primary: str,
    score: int,
    market_snapshot: dict[str, Any],
    symbol_context: dict[str, Any],
) -> str:
    rotation = market_snapshot.get("sector_rotation", {}).get("summary", "")
    iv_context = symbol_context.get("iv_context", "Unknown")
    ticker = symbol_context.get("ticker", "the symbol")
    return (
        f"Current read: **{primary}** (score {score:+d}, {market_snapshot.get('internals', {}).get('vix_signal', '')}). "
        f"{rotation} For **{ticker}**, IV looks **{iv_context.lower()}**."
    )


def _build_critical_paths(
    regime: dict[str, Any],
    market_snapshot: dict[str, Any],
    symbol_context: dict[str, Any],
) -> list[dict[str, Any]]:
    primary = regime["primary"]
    iv_context = symbol_context.get("iv_context", "Unknown")
    leaders = [row.get("Sector") for row in market_snapshot.get("sector_leaders", [])]
    laggards = [row.get("Sector") for row in market_snapshot.get("sector_laggards", [])]
    paths: list[dict[str, Any]] = []

    if primary in {"Risk-on", "Mildly bullish"}:
        paths.append(
            {
                "title": "Primary path — participate with the trend",
                "market_read": "Indexes and internals support constructive risk-taking.",
                "stocks": "Favor leading sectors and stocks above key moving averages with tight risk.",
                "options": _options_guidance(primary, iv_context, bullish=True),
                "sectors_favor": leaders[:3],
                "sectors_avoid": laggards[:2],
                "structures": _structure_names(primary, iv_context, bullish=True),
                "avoid": ["Oversized naked short puts", "Chasing extended breakouts without a stop"],
            }
        )
        paths.append(
            {
                "title": "Alternative — income without giving up all upside",
                "market_read": "Trend is positive but moves may be slower than a pure breakout.",
                "stocks": "Hold core shares in leaders; add selectively on pullbacks.",
                "options": "If IV is elevated, compare covered calls or cash-secured puts at strikes you would accept.",
                "sectors_favor": leaders[:2],
                "sectors_avoid": laggards[:2],
                "structures": ["Covered call", "Cash-secured put", "Bull call spread"],
                "avoid": ["Selling undefined-risk puts into a volatility spike"],
            }
        )
    elif primary == "Neutral / range-bound":
        paths.append(
            {
                "title": "Primary path — range and premium discipline",
                "market_read": "Directional edge is limited; respect support/resistance.",
                "stocks": "Be selective; smaller size unless the chart is sector-supported.",
                "options": _options_guidance(primary, iv_context, bullish=False),
                "sectors_favor": leaders[:2] if leaders else ["Sector leaders from table"],
                "sectors_avoid": ["Low-quality laggards without a catalyst"],
                "structures": ["Iron condor", "Covered call", "Cash-secured put", "Collar"],
                "avoid": ["Large naked long premium without a catalyst", "Undefined-risk short options"],
            }
        )
    elif primary in {"Risk-off", "High volatility"}:
        paths.append(
            {
                "title": "Primary path — defense first",
                "market_read": "Weak breadth, rising fear, or defensive leadership favors protection.",
                "stocks": "Reduce new long exposure; tighten stops on winners; raise cash selectively.",
                "options": _options_guidance(primary, iv_context, bullish=False),
                "sectors_favor": ["Utilities", "Consumer Defensive", "Healthcare"] if not leaders else laggards[:2],
                "sectors_avoid": leaders[:2] if leaders else ["High-beta growth"],
                "structures": ["Protective put", "Collar", "Bear put spread", "Long put"],
                "avoid": ["Aggressive call buying into weak breadth", "Full-size bullish premium selling"],
            }
        )
    else:
        paths.append(
            {
                "title": "Primary path — event premium discipline",
                "market_read": "IV is rich and direction may be binary.",
                "stocks": "Smaller size; consider waiting for clarity after the event.",
                "options": "Compare implied move vs your thesis before buying straddles; prefer defined-risk spreads.",
                "sectors_favor": leaders[:2],
                "sectors_avoid": laggards[:2],
                "structures": ["Long straddle", "Iron butterfly", "Bull call spreads", "Collar"],
                "avoid": ["Short straddle without risk controls", "Illiquid strikes around events"],
            }
        )

    paths.append(
        {
            "title": "If you already own shares",
            "market_read": "Portfolio overlay depends on the same regime, not just the chart.",
            "stocks": "Keep the core only if the thesis and risk limits still hold.",
            "options": (
                "Risk-on: optional covered calls. "
                "Neutral/high IV: collars or covered calls. "
                "Risk-off: protective puts or collars."
            ),
            "sectors_favor": [],
            "sectors_avoid": [],
            "structures": ["Protective put", "Collar", "Covered call"],
            "avoid": ["Adding shares without rechecking max loss"],
        }
    )
    return paths


def _options_guidance(regime: str, iv_context: str, bullish: bool) -> str:
    if bullish:
        if "Low" in iv_context:
            return "Long calls or stock may be efficient; compare bull call spreads if you have a target."
        if "Elevated" in iv_context or "Expensive" in iv_context:
            return "Prefer bull call spreads over naked long calls; IV is not cheap."
        return "Compare stock, long call, and bull call spread; size down if breadth is mixed."
    if "Elevated" in iv_context or "Expensive" in iv_context:
        return "Credit structures can pay well, but use defined risk and respect gap risk."
    return "Favor hedges and defined-risk bearish structures; avoid oversized directional bets."


def _structure_names(regime: str, iv_context: str, bullish: bool) -> list[str]:
    if bullish:
        if "Low" in iv_context:
            return ["Long call", "Stock", "Bull call spread"]
        return ["Bull call spread", "Stock", "Long call"]
    if regime == "Neutral / range-bound":
        return ["Iron condor", "Covered call", "Cash-secured put"]
    return ["Protective put", "Bear put spread", "Collar"]


def _recommended_strategies(regime: dict[str, Any], symbol_context: dict[str, Any]) -> list[dict[str, Any]]:
    biases = REGIME_TO_STRATEGY_BIASES.get(regime["primary"], [])
    strategies = get_strategy_playbook()
    iv_context = symbol_context.get("iv_context", "")

    selected = [entry for entry in strategies if entry.get("market_bias") in biases]
    if "Low" in iv_context:
        selected.sort(key=lambda item: 0 if "Low" in str(item.get("iv_bias", "")) else 1)
    elif "Elevated" in iv_context or "Expensive" in iv_context:
        selected.sort(key=lambda item: 0 if "high" in str(item.get("iv_bias", "")).lower() else 1)
    return selected[:5]


def build_tutor_action_plan(
    report: dict[str, Any],
    *,
    effective_regime: str | None = None,
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rank educational structures using the confirmed regime and active-symbol evidence."""
    profile = user_profile or {}
    model_regime = str(report.get("regime", {}).get("primary", "Neutral / range-bound"))
    regime = effective_regime or model_regime
    symbol = report.get("symbol_context", {})
    technical = symbol.get("technical", {})
    fundamental = symbol.get("fundamental", {})
    iv_context = str(symbol.get("iv_context", "Unknown"))
    user_bias = str(profile.get("bias", "Tutor infer from chart"))
    inferred_bias = _inferred_symbol_bias(technical)
    working_bias = inferred_bias if user_bias == "Tutor infer from chart" else user_bias

    candidates = [
        _score_action_candidate(
            candidate,
            regime=regime,
            model_regime=model_regime,
            working_bias=working_bias,
            technical=technical,
            fundamental=fundamental,
            iv_context=iv_context,
            profile=profile,
            symbol=symbol,
        )
        for candidate in TUTOR_ACTION_CANDIDATES
    ]
    candidates.sort(key=lambda item: (-int(item["score"]), str(item["name"])))

    confidence = str(report.get("regime", {}).get("confidence", "Low"))
    contradiction = _evidence_contradiction(regime, working_bias, technical)
    no_trade_score = 40
    no_trade_reasons = []
    if confidence == "Low":
        no_trade_score += 25
        no_trade_reasons.append("Market-regime confidence is low.")
    if contradiction:
        no_trade_score += 20
        no_trade_reasons.append(contradiction)
    if iv_context == "Unknown":
        no_trade_score += 10
        no_trade_reasons.append("Options volatility context is unavailable.")
    if profile.get("catalyst") not in (None, "", "None known") and not profile.get("catalyst_days"):
        no_trade_score += 5
        no_trade_reasons.append("A catalyst is known, but timing is not defined.")

    return {
        "effective_regime": regime,
        "model_regime": model_regime,
        "regime_was_overridden": regime != model_regime,
        "working_bias": working_bias,
        "inferred_bias": inferred_bias,
        "symbol_assessment": _build_symbol_assessment(symbol, regime, working_bias),
        "candidates": candidates[:5],
        "no_trade_gate": {
            "score": min(no_trade_score, 95),
            "label": _fit_label(min(no_trade_score, 95)),
            "reasons": no_trade_reasons or ["Evidence is sufficiently aligned to compare defined-risk scenarios."],
        },
        "profile": profile,
    }


def _score_action_candidate(
    candidate: dict[str, Any],
    *,
    regime: str,
    model_regime: str,
    working_bias: str,
    technical: dict[str, Any],
    fundamental: dict[str, Any],
    iv_context: str,
    profile: dict[str, Any],
    symbol: dict[str, Any],
) -> dict[str, Any]:
    score = 45
    reasons: list[str] = []
    cautions: list[str] = []

    if regime in candidate["regimes"]:
        score += 25
        reasons.append(f"Fits the effective **{regime}** playbook used for this comparison.")
    else:
        score -= 18
        cautions.append(f"Usually not a first-choice structure in **{regime}**.")

    direction = str(candidate["direction"])
    bias_delta, bias_note = _bias_fit(direction, working_bias)
    score += bias_delta
    (reasons if bias_delta >= 0 else cautions).append(bias_note)

    trend_score = int(technical.get("trend_score", 0) or 0)
    rsi14 = _optional_float(technical.get("rsi14"))
    if direction in {"bullish", "neutral_bullish"}:
        score += trend_score * 6
        if trend_score > 0:
            reasons.append(f"The symbol is in a **{technical.get('trend', 'constructive trend').lower()}**.")
        elif trend_score < 0:
            cautions.append("The symbol trend currently opposes a bullish structure.")
        if rsi14 is not None and rsi14 >= 70:
            score -= 8
            cautions.append(f"RSI(14) is {rsi14:.1f}; bullish entry timing is extended.")
    elif direction == "bearish":
        score -= trend_score * 6
        if trend_score < 0:
            reasons.append(f"The symbol is in a **{technical.get('trend', 'weak trend').lower()}**.")
        elif trend_score > 0:
            cautions.append("The symbol trend currently opposes a bearish structure.")

    iv_delta, iv_note = _iv_fit(str(candidate["iv_preference"]), iv_context)
    score += iv_delta
    (reasons if iv_delta >= 0 else cautions).append(iv_note)

    owns_shares = bool(profile.get("owns_shares", False))
    ownership = str(candidate["ownership"])
    if ownership == "required":
        if owns_shares:
            score += 15
            reasons.append("You indicated that you already own shares, so the stock overlay is structurally valid.")
        else:
            score -= 35
            cautions.append("This overlay requires shares; you indicated that you do not own them.")
    elif ownership == "not_required" and owns_shares:
        cautions.append("Assignment would add shares to an existing position; check concentration risk.")

    catalyst = str(profile.get("catalyst", "None known"))
    if catalyst != "None known":
        if direction == "volatility":
            score += 12
            reasons.append(f"A known **{catalyst.lower()}** catalyst makes a two-sided move scenario relevant.")
        elif direction in {"neutral", "neutral_bullish"}:
            score -= 12
            cautions.append(f"A known **{catalyst.lower()}** catalyst increases gap risk for premium-selling structures.")

    if candidate["id"] == "long_stock":
        fundamental_score = int(fundamental.get("score", 0) or 0)
        score += fundamental_score * 3
        if fundamental_score > 0:
            reasons.append("Available fundamental context is supportive of holding shares.")
        elif fundamental_score < 0:
            cautions.append("Available fundamental context is fragile; price risk is not defined by the structure.")

    price = float(symbol.get("price") or 100)
    risk_budget = float(profile.get("risk_budget") or 0)
    stop_pct = float(profile.get("stop_pct") or 5)
    if risk_budget > 0:
        if candidate["id"] == "cash_secured_put":
            approximate_assignment = price * 0.95 * 100
            score -= 30
            cautions.append(
                f"One cash-secured contract reserves about ${approximate_assignment:,.0f}, "
                f"far above the stated ${risk_budget:,.0f} maximum-loss learning budget."
            )
        elif candidate["id"] == "long_stock":
            one_hundred_share_risk = price * (stop_pct / 100) * 100
            if one_hundred_share_risk > risk_budget:
                score -= 5
                cautions.append(
                    f"100 shares risk about ${one_hundred_share_risk:,.0f} to the stated invalidation; resize the share count."
                )
        elif candidate["id"] in {"long_call", "long_put"}:
            illustrative_premium = price * 0.04 * 100
            if illustrative_premium > risk_budget:
                score -= 12
                cautions.append(
                    f"An illustrative one-contract premium near ${illustrative_premium:,.0f} exceeds the stated budget."
                )

    if model_regime != regime:
        cautions.append(f"The user-confirmed regime differs from the tutor model (**{model_regime}**).")

    final_score = max(5, min(95, score))
    setup = _candidate_setup(candidate, symbol, profile)
    return {
        **candidate,
        "regimes": sorted(candidate["regimes"]),
        "score": final_score,
        "fit_label": _fit_label(final_score),
        "reasons": reasons[:4],
        "cautions": cautions[:4],
        "setup": setup,
        "scenario": _candidate_scenario(candidate, setup),
        "option_defaults": _candidate_option_defaults(candidate, symbol),
    }


def _inferred_symbol_bias(technical: dict[str, Any]) -> str:
    trend_score = int(technical.get("trend_score", 0) or 0)
    if trend_score > 0:
        return "Bullish"
    if trend_score < 0:
        return "Bearish"
    return "Neutral"


def _bias_fit(direction: str, bias: str) -> tuple[int, str]:
    compatible = {
        "Bullish": {"bullish", "neutral_bullish"},
        "Bearish": {"bearish", "hedge"},
        "Neutral": {"neutral", "neutral_bullish"},
        "Large move / direction uncertain": {"volatility", "hedge"},
    }
    if direction in compatible.get(bias, set()):
        return 15, f"The structure matches the working symbol view: **{bias}**."
    if direction == "hedge" and bias == "Bullish":
        return 2, "A hedge can preserve a bullish holding while defining downside."
    return -12, f"The structure does not directly express the working symbol view: **{bias}**."


def _iv_fit(preference: str, iv_context: str) -> tuple[int, str]:
    is_low = "Low" in iv_context
    is_high = "Elevated" in iv_context or "Expensive" in iv_context
    if iv_context == "Unknown" or preference == "any":
        return 0, "IV does not materially improve the ranking, or is unavailable."
    if preference == "low":
        return (12, "IV is low enough to make long premium more efficient.") if is_low else (
            -12,
            "IV is not low; long premium faces richer pricing and possible IV contraction.",
        )
    if preference == "high":
        return (12, "Elevated IV improves the premium available, subject to gap risk.") if is_high else (
            -8,
            "IV is not elevated enough to strongly favor premium selling.",
        )
    if preference == "fair_or_high":
        return (8, "A spread helps offset fair-to-elevated option premium.") if not is_low else (
            2,
            "The structure still defines risk, although low IV reduces the financing benefit.",
        )
    if preference == "not_extreme":
        return (-10, "Protection is expensive after the volatility spike.") if "Expensive" in iv_context else (
            6,
            "Protection is not priced at the most extreme IV classification.",
        )
    return 0, "IV fit is neutral."


def _candidate_setup(
    candidate: dict[str, Any],
    symbol: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    price = float(symbol.get("price") or symbol.get("technical", {}).get("price") or 100)
    target_pct = float(profile.get("target_pct") or 8)
    stop_pct = float(profile.get("stop_pct") or 5)
    target = price * (1 + target_pct / 100)
    downside = price * (1 - stop_pct / 100)
    horizon = str(profile.get("horizon", "Weeks"))
    strike_text = {
        "long_stock": f"Entry near ${price:.2f}; thesis target ${target:.2f}; invalidation near ${downside:.2f}.",
        "long_call": f"Compare an ATM call near ${price:.2f} with enough time for the {horizon.lower()} thesis.",
        "bull_call_spread": f"Illustrative long strike ${price:.2f}; short strike near target ${target:.2f}.",
        "covered_call": f"Own shares near ${price:.2f}; compare a short call near ${target:.2f}.",
        "cash_secured_put": f"Illustrative short put near ${downside:.2f}; reserve cash for assignment.",
        "protective_put": f"Own shares near ${price:.2f}; compare a protective put near ${downside:.2f}.",
        "collar": f"Own shares; compare a ${downside:.2f} put with a ${target:.2f} short call.",
        "bear_put_spread": f"Illustrative long put near ${price:.2f}; short put near ${downside:.2f}.",
        "long_put": f"Compare an ATM put near ${price:.2f}; bearish objective near ${downside:.2f}.",
        "iron_condor": (
            f"Illustrative short strikes near ${price * 0.95:.2f}/${price * 1.05:.2f}; "
            f"protective wings near ${price * 0.90:.2f}/${price * 1.10:.2f}."
        ),
        "long_straddle": f"Illustrative call + put near the ${price:.2f} ATM strike; required move must exceed total premium.",
    }
    risk_budget = float(profile.get("risk_budget") or 0)
    return {
        "spot": round(price, 2),
        "up_price": round(target, 2),
        "down_price": round(downside, 2),
        "horizon": horizon,
        "structure": strike_text.get(candidate["id"], ""),
        "risk_budget": risk_budget,
        "risk_note": (
            f"Keep modeled maximum loss at or below the stated ${risk_budget:,.0f} learning budget."
            if risk_budget > 0
            else "Enter a maximum-loss budget before treating the scenario as trade-ready."
        ),
    }


def _candidate_scenario(candidate: dict[str, Any], setup: dict[str, Any]) -> list[dict[str, str]]:
    direction = str(candidate["direction"])
    outcomes = {
        "bullish": ("Adverse: test stop/max loss.", "Stall risk: stock is flat; options lose time value.", "Favorable if price clears break-even."),
        "neutral_bullish": ("Adverse: assignment or stock downside can dominate premium.", "Favorable if price remains controlled.", "Gain may be capped or put expires."),
        "bearish": ("Favorable if downside exceeds break-even.", "Stall risk: long puts/spreads may lose time value.", "Adverse: test defined max loss."),
        "neutral": ("Adverse if price breaks the lower range.", "Favorable inside the short-strike range.", "Adverse if price breaks the upper range."),
        "volatility": ("Potentially favorable only if move exceeds total premium.", "Worst zone: theta and IV crush can dominate.", "Potentially favorable only if move exceeds total premium."),
        "hedge": ("Protection activates; compare loss reduction with hedge cost.", "Insurance cost or capped income is visible.", "Shares participate, but a collar may cap upside."),
    }
    down, flat, up = outcomes.get(direction, ("Stress the downside.", "Review the flat case.", "Stress the upside."))
    return [
        {"case": "Downside", "price": f"${setup['down_price']:.2f}", "lesson": down},
        {"case": "Flat", "price": f"${setup['spot']:.2f}", "lesson": flat},
        {"case": "Upside", "price": f"${setup['up_price']:.2f}", "lesson": up},
    ]


def _candidate_option_defaults(candidate: dict[str, Any], symbol: dict[str, Any]) -> dict[str, Any] | None:
    price = float(symbol.get("price") or 100)
    iv = _optional_float(symbol.get("options_kpis", {}).get("30D IV")) or 30.0
    if candidate["id"] == "long_call":
        return {
            "option_type": "Call",
            "action": "Buy",
            "stock_price": price,
            "strike": price,
            "premium": max(price * 0.04, 0.25),
            "implied_volatility": iv,
        }
    if candidate["id"] == "long_put":
        return {
            "option_type": "Put",
            "action": "Buy",
            "stock_price": price,
            "strike": price,
            "premium": max(price * 0.04, 0.25),
            "implied_volatility": iv,
        }
    if candidate["id"] == "cash_secured_put":
        return {
            "option_type": "Put",
            "action": "Sell",
            "stock_price": price,
            "strike": price * 0.95,
            "premium": max(price * 0.02, 0.15),
            "implied_volatility": iv,
        }
    return None


def _build_symbol_assessment(symbol: dict[str, Any], regime: str, bias: str) -> dict[str, Any]:
    technical = symbol.get("technical", {})
    fundamental = symbol.get("fundamental", {})
    options = symbol.get("options_kpis", {})
    evidence = [
        f"Trend: **{technical.get('trend', 'Unavailable')}**; RSI(14): **{technical.get('rsi14', 'n/a')}**.",
        (
            f"20D support/resistance: **${float(technical.get('support_20d')):.2f} / "
            f"${float(technical.get('resistance_20d')):.2f}**."
            if technical.get("support_20d") is not None and technical.get("resistance_20d") is not None
            else "Support/resistance: unavailable."
        ),
        f"Fundamental context: **{fundamental.get('label', 'Unknown')}**.",
        (
            f"Options: IV Rank **{options.get('IV Rank', 'n/a')}**, 30D IV **{options.get('30D IV', 'n/a')}%**, "
            f"put/call OI **{options.get('Put/Call Ratio', 'n/a')}**."
        ),
    ]
    alignment = _evidence_contradiction(regime, bias, technical)
    return {
        "headline": f"{symbol.get('ticker', 'Symbol')} is **{bias.lower()}** under a **{regime}** market assumption.",
        "evidence": evidence,
        "fundamental_evidence": fundamental.get("evidence", []),
        "risks": [*fundamental.get("cautions", []), *([alignment] if alignment else [])],
        "alignment": "Mixed evidence" if alignment else "Evidence broadly aligned",
    }


def _evidence_contradiction(regime: str, bias: str, technical: dict[str, Any]) -> str:
    trend_score = int(technical.get("trend_score", 0) or 0)
    if regime in {"Risk-on", "Mildly bullish"} and (bias == "Bearish" or trend_score < 0):
        return "The market regime is constructive, but the symbol evidence is bearish."
    if regime in {"Risk-off", "High volatility"} and (bias == "Bullish" or trend_score > 0):
        return "The market regime is defensive, but the symbol evidence is bullish."
    return ""


def _fit_label(score: int) -> str:
    if score >= 80:
        return "Strong fit"
    if score >= 65:
        return "Worth comparing"
    if score >= 50:
        return "Conditional"
    return "Weak fit"


def _build_checklist_hints(
    regime: dict[str, Any],
    market_snapshot: dict[str, Any],
    symbol_context: dict[str, Any],
) -> list[dict[str, str]]:
    internals = market_snapshot.get("internals", {})
    rotation = market_snapshot.get("sector_rotation", {})
    hints = [
        {
            "checklist_id": "daily-regime",
            "question": "Is VIX rising, falling, or stable?",
            "auto_read": internals.get("vix_signal", "Review VIX proxy in market snapshot."),
        },
        {
            "checklist_id": "daily-regime",
            "question": "Are more stocks advancing than declining?",
            "auto_read": internals.get("breadth_signal", "Review breadth table."),
        },
        {
            "checklist_id": "daily-regime",
            "question": "Is growth or defensives leading?",
            "auto_read": rotation.get("summary", "Review sector leaders/laggards."),
        },
        {
            "checklist_id": "daily-regime",
            "question": "Is my symbol's IV above or below its recent average?",
            "auto_read": (
                f"IV Rank {symbol_context.get('options_kpis', {}).get('IV Rank', 'n/a')} — "
                f"{symbol_context.get('iv_context', 'unknown')}."
            ),
        },
        {
            "checklist_id": "pre-trade-options",
            "question": "What regime am I in (risk-on, neutral, risk-off, event-driven)?",
            "auto_read": f"Tutor classification: {regime['primary']}.",
        },
        {
            "checklist_id": "pre-trade-options",
            "question": "Is IV cheap, fair, expensive, or event-driven for this symbol?",
            "auto_read": symbol_context.get("iv_context", "Unknown"),
        },
    ]
    return hints


def get_tutor_checklists() -> list[dict[str, Any]]:
    """Return checklist definitions used by the tutor UI."""
    return get_checklists()


def format_decision_flow_live_context(report: dict[str, Any] | None) -> dict[str, str]:
    """Turn a Trading tutor report into step-by-step text for the decision-flow guide."""
    if not report:
        return {}

    snapshot = report.get("market_snapshot", {})
    regime = report.get("regime", {})
    symbol = report.get("symbol_context", {})
    ticker = str(report.get("ticker", symbol.get("ticker", "—")))
    internals = snapshot.get("internals", {})
    rotation = snapshot.get("sector_rotation", {})
    options_kpis = symbol.get("options_kpis", {})

    index_lines = []
    for row in snapshot.get("indices", []):
        name = row.get("name", "Index")
        value = row.get("value")
        change = float(row.get("change_pct", 0.0) or 0.0)
        if value is not None:
            index_lines.append(f"- **{name}:** {float(value):,.2f} ({change:+.2f}% today)")
        else:
            index_lines.append(f"- **{name}:** {change:+.2f}% today")

    tech_lines = []
    for label, payload in (
        ("SPY", snapshot.get("index_technicals", {})),
        ("QQQ", snapshot.get("qqq_technicals", {})),
    ):
        if not payload.get("available"):
            continue
        tech_lines.append(
            f"- **{label}:** {payload.get('trend')} · price {payload.get('price')} · "
            f"RSI(14) {payload.get('rsi14')} · 1W {float(payload.get('week_return_pct', 0)):+.2f}% · "
            f"MA20 {payload.get('ma20')} / MA40 {payload.get('ma40')}"
        )

    breadth_lines = []
    for row in internals.get("breadth_rows", [])[:4]:
        breadth_lines.append(f"- **{row.get('Indicator', 'Breadth')}:** {row.get('Value', '—')} · {row.get('Signal', '')}")

    leader_names = [str(row.get("Sector", "")) for row in snapshot.get("sector_leaders", []) if row.get("Sector")]
    laggard_names = [str(row.get("Sector", "")) for row in snapshot.get("sector_laggards", []) if row.get("Sector")]

    step1 = "\n".join(
        [
            f"**Live read for {ticker}** (generated {report.get('generated_at', '')})",
            "",
            "**Indexes**",
            *(index_lines or ["- Index data unavailable"]),
            "",
            "**Index ETF technicals**",
            *(tech_lines or ["- Technical snapshot unavailable"]),
            "",
            f"**Volatility:** {internals.get('vix_signal', 'Review VIX proxy.')}",
            *( [f"**TICK (manual):** {internals['tick_signal']}"] if internals.get("tick_signal") else [] ),
            *( [f"**TRIN (manual):** {internals['trin_signal']}"] if internals.get("trin_signal") else [] ),
            "",
            f"**Breadth:** {internals.get('breadth_signal', 'Review breadth table.')}",
            *(breadth_lines or []),
            "",
            f"**Sector rotation:** {rotation.get('summary', 'Sector data unavailable.')}",
            *( [f"- **Leaders:** {', '.join(leader_names)}"] if leader_names else [] ),
            *( [f"- **Laggards:** {', '.join(laggard_names)}"] if laggard_names else [] ),
        ]
    )

    breakdown_lines = [
        f"- **{item.get('factor', 'Factor')}:** {item.get('reading', '')} (impact {int(item.get('impact', 0)):+d})"
        for item in regime.get("breakdown", [])
    ]
    step2 = "\n".join(
        [
            f"**Tutor classification:** **{regime.get('primary', '—')}** "
            f"(score {int(regime.get('score', 0)):+d}, confidence {regime.get('confidence', '—')})",
            "",
            regime.get("summary", ""),
            "",
            "**Evidence used**",
            *(breakdown_lines or ["- No breakdown available"]),
            "",
            "Compare this label to the regime definitions below if the term is new.",
        ]
    )

    step3_parts = [
        (
            f"**Symbol:** {ticker} · sector **{symbol.get('sector', '—')}** · "
            f"price **${float(symbol.get('price', 0)):,.2f}**"
            if symbol.get("price")
            else f"**Symbol:** {ticker}"
        ),
        "",
        f"**IV context:** **{symbol.get('iv_context', 'Unknown')}**",
        f"- IV Rank: **{options_kpis.get('IV Rank', 'n/a')}**",
        f"- 30D IV: **{options_kpis.get('30D IV', 'n/a')}%**",
        f"- Put/Call ratio (OI): **{options_kpis.get('Put/Call Ratio', 'n/a')}**",
        "",
        "Use the IV definitions below to decide whether to buy premium, sell premium, or use spreads.",
    ]
    step3 = "\n".join(step3_parts)

    paths = report.get("critical_paths", [])
    primary_path = paths[0] if paths else {}
    strategies = report.get("recommended_strategies", [])
    strategy_names = [str(item.get("name", "")) for item in strategies[:4] if item.get("name")]
    step4 = "\n".join(
        [
            f"**Primary path from today's read:** {primary_path.get('title', 'See critical paths above.')}",
            "",
            f"- **Stocks:** {primary_path.get('stocks', '—')}",
            f"- **Options:** {primary_path.get('options', '—')}",
            *( [f"- **Sectors to favor:** {', '.join(primary_path.get('sectors_favor', []))}"] if primary_path.get("sectors_favor") else [] ),
            "",
            "**Structures to compare:** "
            + (", ".join(primary_path.get("structures", [])) if primary_path.get("structures") else "See strategy recommendations"),
            "",
            "**Playbook matches for this regime:** "
            + (", ".join(strategy_names) if strategy_names else "None matched"),
        ]
    )

    return {
        "step1": step1,
        "step2": step2,
        "step3": step3,
        "step4": step4,
        "has_live_context": "true",
    }
