"""Options Intelligence page with institutional-style placeholder dashboards."""

from __future__ import annotations

import streamlit as st

from ui.components.cards import render_metric_card, render_todo_callout
from ui.components.charts import (
    gamma_exposure_chart,
    max_pain_chart,
    open_interest_chart,
    options_line_chart,
)
from ui.components.page_router import render_ticker_submenu_page
from ai.market_interpreter import summarize_options_intelligence
from services.options_data_service import (
    get_dealer_positioning,
    get_gamma_exposure,
    get_iv_rank_history,
    get_iv_term_structure,
    get_open_interest_by_strike,
    get_options_chain,
    get_options_flow,
    get_options_kpis,
    get_put_call_ratio_history,
)


def render(submenu: str) -> None:
    """Route options intelligence submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Options Chain Viewer": lambda: _options_chain(ticker),
        "Open Interest Analysis": lambda: _open_interest(ticker),
        "Put/Call Ratio": _put_call_ratio,
        "Implied Volatility": lambda: _implied_volatility(ticker),
        "IV Rank": _iv_rank,
        "Gamma Exposure": lambda: _gamma_exposure(ticker),
        "Max Pain": lambda: _max_pain(ticker),
        "Dealer Positioning": _dealer_positioning,
        "Options Flow": _options_flow,
        "AI Conclusions": lambda: _ai_conclusions(ticker),
    }
    render_ticker_submenu_page(
        "Options Intelligence",
        submenu,
        handlers,
        default_handler=lambda: _options_chain(ticker),
        show_quote_cards=True,
    )


def _render_options_kpis(ticker: str) -> None:
    """Render core options intelligence KPIs."""
    kpis = get_options_kpis(ticker)
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Put/Call", f"{kpis['Put/Call Ratio']:.2f}")
    with cols[1]:
        render_metric_card("IV Rank", f"{kpis['IV Rank']:.2f}%")
    with cols[2]:
        render_metric_card("30D IV", f"{kpis['30D IV']:.2f}%")
    with cols[3]:
        render_metric_card("Max Pain", f"${kpis['Max Pain']:.2f}")


def _render_ai_panel(ticker: str, focus: str) -> None:
    """Render placeholder AI interpretation panel."""
    st.markdown("#### AI Market Interpretation")
    st.info(
        f"{summarize_options_intelligence(ticker)}\n\n"
        f"**Current focus:** {focus}. TODO: Replace with model-generated interpretation from live options data."
    )


def _options_chain(ticker: str) -> None:
    """Options chain placeholder view."""
    _render_options_kpis(ticker)
    chain = get_options_chain(ticker)
    st.markdown("#### Options Chain Snapshot")
    st.dataframe(chain, use_container_width=True, hide_index=True)
    render_todo_callout("Connect live options chain with expirations, greeks, bid/ask, and volume filters.")
    _render_ai_panel(ticker, "surface liquidity and strike-level positioning")


def _open_interest(ticker: str) -> None:
    """Open interest analysis placeholder."""
    _render_options_kpis(ticker)
    oi = get_open_interest_by_strike(ticker)
    st.plotly_chart(open_interest_chart(oi, ticker), use_container_width=True)
    st.dataframe(oi, use_container_width=True, hide_index=True)
    render_todo_callout("Aggregate open interest across expirations and classify call/put concentration zones.")
    _render_ai_panel(ticker, "open interest concentration and pinning risk")


def _put_call_ratio() -> None:
    """Put/call ratio placeholder."""
    ratio = get_put_call_ratio_history()
    st.plotly_chart(
        options_line_chart(ratio, "Date", "Put/Call Ratio", "Put/Call Ratio Trend (Mock)"),
        use_container_width=True,
    )
    st.dataframe(ratio.tail(10), use_container_width=True, hide_index=True)
    render_todo_callout("Compute put/call ratio from option volume and open interest by expiration.")


def _implied_volatility(ticker: str) -> None:
    """Implied volatility term structure placeholder."""
    _render_options_kpis(ticker)
    iv = get_iv_term_structure(ticker)
    st.plotly_chart(
        options_line_chart(iv, "Expiration", "Implied Volatility", f"{ticker} — IV Term Structure (Mock)"),
        use_container_width=True,
    )
    st.dataframe(iv, use_container_width=True, hide_index=True)
    render_todo_callout("Derive IV from option prices and show term structure / skew by expiration.")
    _render_ai_panel(ticker, "implied volatility term structure")


def _iv_rank() -> None:
    """IV rank placeholder."""
    rank = get_iv_rank_history()
    st.plotly_chart(
        options_line_chart(rank, "Date", "IV Rank", "IV Rank History (Mock)"),
        use_container_width=True,
    )
    st.dataframe(rank.tail(12), use_container_width=True, hide_index=True)
    render_todo_callout("Calculate IV rank from current IV vs historical one-year implied volatility range.")


def _gamma_exposure(ticker: str) -> None:
    """Gamma exposure placeholder."""
    _render_options_kpis(ticker)
    gex = get_gamma_exposure(ticker)
    st.plotly_chart(gamma_exposure_chart(gex, ticker), use_container_width=True)
    st.dataframe(gex, use_container_width=True, hide_index=True)
    render_todo_callout("Estimate gamma exposure using greeks, open interest, spot, and contract multipliers.")
    _render_ai_panel(ticker, "dealer gamma regime and volatility dampening/amplification")


def _max_pain(ticker: str) -> None:
    """Max pain placeholder."""
    kpis = get_options_kpis(ticker)
    oi = get_open_interest_by_strike(ticker)
    _render_options_kpis(ticker)
    st.plotly_chart(max_pain_chart(oi, kpis["Max Pain"], ticker), use_container_width=True)
    st.dataframe(oi, use_container_width=True, hide_index=True)
    render_todo_callout("Calculate max pain by expiration using option holder payout minimization.")
    _render_ai_panel(ticker, "expiration pinning and max-pain magnet risk")


def _dealer_positioning() -> None:
    """Dealer positioning placeholder."""
    positioning = get_dealer_positioning()
    st.markdown("#### Dealer Positioning Dashboard")
    st.dataframe(positioning, use_container_width=True, hide_index=True)
    render_todo_callout("Add dealer positioning model using gamma, vanna, charm, and directional flow.")
    st.info(
        "**AI Interpretation (Placeholder)** — Dealer positioning appears stabilizing in the mock regime. "
        "Future logic will infer whether dealers are likely buying dips, selling rallies, or amplifying moves."
    )


def _options_flow() -> None:
    """Options flow placeholder."""
    flow = get_options_flow()
    st.markdown("#### Institutional Options Flow Tape")
    st.dataframe(flow, use_container_width=True, hide_index=True)
    render_todo_callout("Stream unusual options activity and classify sweeps, blocks, opening trades, and hedges.")
    st.info(
        "**AI Flow Read (Placeholder)** — Mock flow shows selective upside call activity with some protective put hedging. "
        "Future implementation will score urgency, size, moneyness, and directional conviction."
    )


def _ai_conclusions(ticker: str) -> None:
    """Consolidated AI options conclusion placeholder."""
    _render_options_kpis(ticker)
    st.markdown(summarize_options_intelligence(ticker))
    st.markdown(
        """
        **Placeholder Institutional Takeaways**
        - Options surface: mid-range implied volatility with balanced skew.
        - Positioning: dealer gamma appears stabilizing near spot.
        - Flow: selective upside call demand with protective hedge activity.
        - Risk: headline or earnings volatility could reprice the surface quickly.
        """
    )
    render_todo_callout("Generate conclusions from live chain, flow, greeks, IV history, and event calendar context.")
