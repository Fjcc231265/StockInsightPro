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

    market_snapshot = _build_market_snapshot(
        overview, breadth, sectors, index_technicals, qqq_technicals, manual_internals
    )
    symbol_context = _build_symbol_context(ticker, symbol_quote, options_kpis)
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


def _build_symbol_context(ticker: str, quote: dict, options_kpis: dict) -> dict[str, Any]:
    iv_rank = options_kpis.get("IV Rank")
    iv_context = _iv_context(iv_rank)
    return {
        "ticker": ticker.upper(),
        "price": quote.get("price"),
        "change_pct": quote.get("change_pct"),
        "sector": quote.get("sector", "Unknown"),
        "name": quote.get("name", ticker.upper()),
        "options_available": iv_rank is not None and str(options_kpis.get("Source", "")).lower().find("unavailable") < 0,
        "options_kpis": options_kpis,
        "iv_context": iv_context,
    }


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
