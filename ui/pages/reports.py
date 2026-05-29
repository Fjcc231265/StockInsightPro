"""Reports generation page."""

from __future__ import annotations

import streamlit as st

from services.fundamental_data_service import get_fundamental_health_label, get_written_fundamental_analysis
from services.market_data_service import get_quote_summary
from services.options_data_service import get_options_kpis
from services.technical_data_service import get_technical_trend_label, get_written_technical_analysis
from ui.components.page_router import render_submenu_page
from utils.constants import COLORS


def render(submenu: str) -> None:
    """Route reports submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "AI summary report": lambda: _ai_summary_report(ticker),
        "Export placeholder": lambda: _export_placeholder(ticker),
    }
    render_submenu_page(
        "Reports",
        submenu,
        handlers,
        default_handler=lambda: _ai_summary_report(ticker),
    )


def _ai_summary_report(ticker: str) -> None:
    """Render a combined AI-style directional report."""
    st.markdown(f"### AI Summary Report — {ticker}")
    st.caption("Wrap-up of technical analysis, fundamental health, and options intelligence.")

    with st.spinner("Building combined analysis..."):
        report = _build_summary_report(ticker)

    _render_direction_badge(report["direction"], report["color"], report["score"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Technical takeaway", report["technical"]["label"].title(), _score_delta(report["technical"]["score"]))
    with col2:
        st.metric("Fundamental takeaway", report["fundamental"]["label"], _score_delta(report["fundamental"]["score"]))
    with col3:
        st.metric("Options takeaway", report["options"]["label"], _score_delta(report["options"]["score"]))

    st.markdown("#### Rationale")
    for rationale in report["rationales"]:
        st.markdown(f"- {rationale}")

    st.text_area("Report narrative", value=report["narrative"], height=360)

    with st.expander("Technical analysis used"):
        st.markdown(report["technical"]["analysis"])
    with st.expander("Fundamental analysis used"):
        st.markdown(report["fundamental"]["analysis"])

    st.caption("This report is analytical commentary only, not financial advice.")


def _build_summary_report(ticker: str) -> dict:
    """Build a directional wrap-up from available analysis modules."""
    quote = get_quote_summary(ticker)
    price = quote.get("price")

    technical_analysis = _safe_text(get_written_technical_analysis, ticker)
    technical_label = get_technical_trend_label(technical_analysis)
    technical = _score_technical(technical_label, technical_analysis)

    fundamental_analysis = _safe_text(get_written_fundamental_analysis, ticker)
    fundamental_label = get_fundamental_health_label(fundamental_analysis)
    fundamental = _score_fundamental(fundamental_label, fundamental_analysis)

    options_kpis = get_options_kpis(ticker)
    options = _score_options(options_kpis, price)

    score = technical["score"] + fundamental["score"] + options["score"]
    direction, color, opinion = _overall_direction(score)
    rationales = [technical["rationale"], fundamental["rationale"], options["rationale"]]

    narrative = f"""AI SUMMARY REPORT — {ticker}

Current price: {_format_price(price)}
Overall directional opinion: {direction}
Signal color: {color.upper()}
Composite score: {score:+.1f}

Bottom line:
{opinion}

Technical takeaway:
{technical["takeaway"]}

Fundamental takeaway:
{fundamental["takeaway"]}

Options intelligence takeaway:
{options["takeaway"]}

Rationale:
- {technical["rationale"]}
- {fundamental["rationale"]}
- {options["rationale"]}

What would change the view:
- More bullish: price confirms above resistance with supportive volume, fundamentals remain healthy, and options positioning supports higher strikes.
- More sideways: technical trend stays mixed, fundamentals are adequate but not accelerating, and options positioning remains balanced.
- More bearish: price loses support, fundamental health weakens, or options data shows defensive put demand and max-pain pressure below spot.

DISCLAIMER: This is an analytical synthesis, not investment advice."""

    return {
        "direction": direction,
        "color": color,
        "score": score,
        "technical": technical,
        "fundamental": fundamental,
        "options": options,
        "rationales": rationales,
        "narrative": narrative,
    }


def _safe_text(callback, ticker: str) -> str:
    """Return analysis text while keeping the report available if one section fails."""
    try:
        return callback(ticker)
    except Exception as exc:  # noqa: BLE001 - report should degrade gracefully across providers
        return f"Analysis unavailable for {ticker}: {exc}"


def _score_technical(label: str, analysis: str) -> dict:
    normalized = label.lower()
    if "bullish" in normalized:
        score = 1.0
        takeaway = "The chart structure supports upside because price action and moving averages are constructive."
        rationale = f"Technical read is bullish, adding green directional evidence."
    elif "bearish" in normalized:
        score = -1.0
        takeaway = "The chart structure warns of downside risk because price action is below key trend measures."
        rationale = "Technical read is bearish, adding red directional evidence."
    else:
        score = 0.0
        takeaway = "The chart structure is mixed, so technicals support a sideways or wait-for-confirmation stance."
        rationale = "Technical read is mixed / sideways, adding neutral evidence."
    return {"label": label or "Unknown", "score": score, "takeaway": takeaway, "rationale": rationale, "analysis": analysis}


def _score_fundamental(label: str, analysis: str) -> dict:
    normalized = label.lower()
    if "strong" in normalized:
        score = 1.0
        takeaway = "Fundamentals support a more constructive view because financial health screens as strong."
        rationale = "Fundamental health is strong, supporting green medium-term evidence."
    elif "weak" in normalized:
        score = -1.0
        takeaway = "Fundamentals add caution because financial health requires close monitoring."
        rationale = "Fundamental health is weak, adding red medium-term evidence."
    elif "adequate" in normalized:
        score = 0.0
        takeaway = "Fundamentals look acceptable but not decisive enough to drive the stock call by themselves."
        rationale = "Fundamental health is adequate / watchlist, adding yellow evidence."
    else:
        score = 0.0
        takeaway = "Fundamental evidence is incomplete, so it is treated as neutral in the final opinion."
        rationale = "Fundamental health is unavailable or unclear, adding neutral evidence."
    return {"label": label or "Unknown", "score": score, "takeaway": takeaway, "rationale": rationale, "analysis": analysis}


def _score_options(kpis: dict, price: float | None) -> dict:
    if kpis.get("Source") == "Unavailable":
        reason = kpis.get("Error", "Options data is unavailable.")
        return {
            "label": "Unavailable",
            "score": 0.0,
            "takeaway": f"Options intelligence is unavailable, so it is not pushing the final call up or down. {reason}",
            "rationale": "Options data is unavailable, adding neutral evidence.",
        }

    score = 0.0
    notes = []
    put_call = kpis.get("Put/Call Ratio")
    iv_rank = kpis.get("IV Rank")
    max_pain = kpis.get("Max Pain")

    if put_call is not None:
        if put_call < 0.8:
            score += 0.5
            notes.append(f"put/call ratio is call-leaning at {put_call:.2f}")
        elif put_call > 1.2:
            score -= 0.5
            notes.append(f"put/call ratio is defensive at {put_call:.2f}")
        else:
            notes.append(f"put/call ratio is balanced at {put_call:.2f}")

    if price and max_pain:
        distance = (max_pain - price) / price
        if distance > 0.02:
            score += 0.5
            notes.append(f"max pain is above spot ({max_pain:.2f} vs {_format_price(price)})")
        elif distance < -0.02:
            score -= 0.5
            notes.append(f"max pain is below spot ({max_pain:.2f} vs {_format_price(price)})")
        else:
            notes.append(f"max pain is close to spot ({max_pain:.2f} vs {_format_price(price)})")

    if iv_rank is not None:
        if iv_rank >= 70:
            notes.append(f"IV rank is elevated at {iv_rank:.2f}, so the market is pricing wider movement")
        elif iv_rank <= 30:
            notes.append(f"IV rank is low at {iv_rank:.2f}, so options imply calmer movement")
        else:
            notes.append(f"IV rank is moderate at {iv_rank:.2f}")

    label = _component_label(score)
    takeaway = "Options positioning is " + (", ".join(notes) if notes else "available but not decisive") + "."
    rationale = f"Options read is {label.lower()}, adding {score:+.1f} to the composite score."
    return {"label": label, "score": score, "takeaway": takeaway, "rationale": rationale}


def _component_label(score: float) -> str:
    if score > 0:
        return "Bullish"
    if score < 0:
        return "Bearish"
    return "Neutral"


def _overall_direction(score: float) -> tuple[str, str, str]:
    if score >= 1.5:
        return (
            "Going up",
            "green",
            "The evidence leans bullish. Technicals and/or fundamentals are constructive, and the options read is not strong enough to offset that positive setup.",
        )
    if score <= -1.5:
        return (
            "Going down",
            "red",
            "The evidence leans bearish. Downside risk dominates because weak trend, weak fundamentals, or defensive options positioning outweigh the positive evidence.",
        )
    return (
        "Sideways",
        "yellow",
        "The evidence is mixed. The better stance is neutral until price, fundamentals, or options positioning gives cleaner confirmation.",
    )


def _render_direction_badge(direction: str, color: str, score: float) -> None:
    color_map = {
        "green": COLORS["positive"],
        "yellow": COLORS["accent"],
        "red": COLORS["negative"],
    }
    bg = color_map[color]
    st.markdown(
        f"""
        <div style="border-left: 8px solid {bg}; padding: 1rem; background: #ffffff; border-radius: 0.5rem; border-top: 1px solid #d8dee6; border-right: 1px solid #d8dee6; border-bottom: 1px solid #d8dee6;">
            <div style="font-size: 0.85rem; color: {COLORS["text_muted"]}; text-transform: uppercase;">Overall opinion</div>
            <div style="font-size: 1.6rem; font-weight: 700; color: {bg};">{direction}</div>
            <div style="color: {COLORS["neutral"]};">Composite score: {score:+.1f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _score_delta(score: float) -> str:
    return f"{score:+.1f}"


def _format_price(price: float | None) -> str:
    return "Unavailable" if price is None else f"${price:,.2f}"


def _export_placeholder(ticker: str) -> None:
    """Show and download the complete AI summary report."""
    st.markdown(f"### Export AI Summary Report — {ticker}")
    st.caption("This is the complete report shown in AI summary report, prepared as plain text for export.")

    with st.spinner("Preparing report export..."):
        report = _build_summary_report(ticker)

    st.text_area("Complete AI summary report", value=report["narrative"], height=520)
    st.download_button(
        "Download AI summary report",
        data=report["narrative"],
        file_name=f"{ticker}_ai_summary_report.txt",
        mime="text/plain",
    )
