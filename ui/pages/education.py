"""Education page with trading concepts and interactive payoff simulators."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from services.education_service import filter_rules, load_education_rules
from ui.components.page_router import render_submenu_page
from utils.constants import COLORS


def render(submenu: str) -> None:
    """Route education submenu."""
    handlers = {
        "Learning roadmap": _learning_roadmap,
        "Rules playbook": _rules_playbook,
        "Stock P&L simulator": _stock_pnl_simulator,
        "Options P&L simulator": _options_pnl_simulator,
        "Market scenario lab": _market_scenario_lab,
    }
    render_submenu_page(
        "Education",
        submenu,
        handlers,
        default_handler=_learning_roadmap,
        subtitle="Learn market basics, options mechanics, and risk using interactive examples.",
    )


def _learning_roadmap() -> None:
    """Render beginner-oriented education modules."""
    st.markdown("### Learning roadmap")
    st.caption("A practical sequence for users who are new to stocks, options, and risk management.")
    modules = [
        (
            "1. Market structure",
            "Understand stocks, ETFs, indexes, volume, volatility, bid/ask spreads, and why liquidity matters.",
        ),
        (
            "2. Technical context",
            "Use trend, support/resistance, RSI, MACD, and volume as evidence, not as guarantees.",
        ),
        (
            "3. Fundamental context",
            "Review revenue, profitability, balance sheet strength, cash flow, and valuation before sizing a trade.",
        ),
        (
            "4. Options basics",
            "Learn calls, puts, strikes, expirations, premium, intrinsic value, time value, and break-even levels.",
        ),
        (
            "5. Risk and P&L",
            "Use simulators to understand maximum loss, leverage, expiration risk, and scenario-based outcomes.",
        ),
    ]
    for title, description in modules:
        st.markdown(f"**{title}**")
        st.write(description)

    st.info(
        "Education mode should help users ask better questions: What is my thesis? What can go wrong? "
        "What is my maximum loss? What price or time invalidates the idea?"
    )


def _rules_playbook() -> None:
    """Render local-file educational rules."""
    st.markdown("### Rules playbook")
    rules = load_education_rules()
    if not rules:
        st.warning("No education rules were found in `data/education_rules.json`.")
        return

    regimes = ["All", *sorted({rule.get("market_regime", "Unknown") for rule in rules})]
    instruments = ["All", "Stocks", "Options", "Stocks and Options"]
    col1, col2 = st.columns(2)
    with col1:
        regime = st.selectbox("Market regime", regimes)
    with col2:
        instrument = st.selectbox("Instrument", instruments)

    matching_rules = filter_rules(regime, instrument)
    st.caption(f"Showing {len(matching_rules)} rule(s) from `data/education_rules.json`.")
    for rule in matching_rules:
        with st.expander(rule.get("title", "Untitled rule"), expanded=True):
            st.markdown(f"**Regime:** {rule.get('market_regime', 'Unknown')}")
            st.markdown(f"**Instrument:** {rule.get('instrument', 'Unknown')}")
            st.write(rule.get("lesson", ""))
            st.caption(f"Example: {rule.get('example', '')}")
            st.warning(rule.get("risk_note", "Risk management is required."))


def _stock_pnl_simulator() -> None:
    """Render long/short stock P&L simulator."""
    st.markdown("### Stock P&L simulator")
    col1, col2, col3 = st.columns(3)
    with col1:
        entry_price = st.number_input("Entry price", min_value=0.01, value=100.0, step=1.0)
    with col2:
        shares = st.number_input("Shares", min_value=1, value=100, step=10)
    with col3:
        direction = st.radio("Position", ["Long stock", "Short stock"], horizontal=True)

    prices = _price_range(entry_price)
    sign = 1 if direction == "Long stock" else -1
    pnl = [(price - entry_price) * shares * sign for price in prices]
    frame = pd.DataFrame({"Underlying Price": prices, "P&L": pnl})
    st.plotly_chart(_line_chart(frame, "Underlying Price", "P&L", f"{direction} payoff"), use_container_width=True)
    _render_pnl_summary(frame)


def _options_pnl_simulator() -> None:
    """Render simple single-leg options payoff simulator at expiration."""
    st.markdown("### Options P&L simulator")
    st.caption("This is an expiration payoff simulator. It does not model changing implied volatility or time decay before expiration.")
    col1, col2, col3 = st.columns(3)
    with col1:
        option_type = st.radio("Option type", ["Call", "Put"], horizontal=True)
        action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
    with col2:
        stock_price = st.number_input("Current stock price", min_value=0.01, value=100.0, step=1.0)
        strike = st.number_input("Strike", min_value=0.01, value=105.0, step=1.0)
    with col3:
        premium = st.number_input("Premium per share", min_value=0.01, value=3.0, step=0.25)
        contracts = st.number_input("Contracts", min_value=1, value=1, step=1)

    prices = _price_range(stock_price)
    multiplier = 100 * contracts
    direction_sign = 1 if action == "Buy" else -1
    intrinsic_values = [
        max(price - strike, 0) if option_type == "Call" else max(strike - price, 0)
        for price in prices
    ]
    pnl = [(intrinsic - premium) * multiplier * direction_sign for intrinsic in intrinsic_values]
    frame = pd.DataFrame({"Underlying Price": prices, "P&L": pnl})
    st.plotly_chart(
        _line_chart(frame, "Underlying Price", "P&L", f"{action} {option_type} expiration payoff"),
        use_container_width=True,
    )

    break_even = strike + premium if option_type == "Call" else strike - premium
    max_loss = premium * multiplier if action == "Buy" else "Undefined / strategy dependent"
    st.info(f"Break-even at expiration: **${break_even:.2f}**. Maximum loss: **{max_loss}**.")
    _render_pnl_summary(frame)


def _market_scenario_lab() -> None:
    """Render rule-driven scenario explanations."""
    st.markdown("### Market scenario lab")
    regime = st.selectbox("Market regime", ["Bullish", "Bearish", "Sideways", "High volatility"])
    instrument = st.selectbox("Instrument focus", ["Stocks", "Options", "Stocks and Options"])
    matching_rules = filter_rules(regime, instrument)
    st.caption("Scenario guidance is loaded from the local education rules file.")

    if not matching_rules:
        st.info("No matching local rule yet. Add one to `data/education_rules.json` to enrich this scenario.")
        return

    for rule in matching_rules:
        st.markdown(f"**{rule.get('title', 'Rule')}**")
        st.write(rule.get("lesson", ""))
        st.caption(rule.get("example", ""))
        st.warning(rule.get("risk_note", "Risk management is required."))


def _price_range(anchor_price: float) -> list[float]:
    """Return a +/- 30% price range around an anchor."""
    start = anchor_price * 0.7
    stop = anchor_price * 1.3
    step = (stop - start) / 60
    return [round(start + step * index, 2) for index in range(61)]


def _line_chart(frame: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    """Build a P&L line chart."""
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in frame[y_col]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame[x_col], y=frame[y_col], mode="lines", name="P&L", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_trace(go.Bar(x=frame[x_col], y=frame[y_col], marker_color=colors, name="P&L zones", opacity=0.2))
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"])
    fig.update_layout(
        title=title,
        height=420,
        margin=dict(l=40, r=30, t=55, b=45),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        xaxis_title=x_col,
        yaxis_title="Profit / Loss ($)",
        hovermode="x unified",
    )
    return fig


def _render_pnl_summary(frame: pd.DataFrame) -> None:
    """Render simple P&L summary stats."""
    min_row = frame.loc[frame["P&L"].idxmin()]
    max_row = frame.loc[frame["P&L"].idxmax()]
    cols = st.columns(3)
    with cols[0]:
        st.metric("Worst simulated P&L", f"${float(min_row['P&L']):,.2f}", f"at ${float(min_row['Underlying Price']):.2f}")
    with cols[1]:
        st.metric("Best simulated P&L", f"${float(max_row['P&L']):,.2f}", f"at ${float(max_row['Underlying Price']):.2f}")
    with cols[2]:
        profitable = (frame["P&L"] > 0).mean() * 100
        st.metric("Profitable price points", f"{profitable:.0f}%")
