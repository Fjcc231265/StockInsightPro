"""Education page with trading concepts and interactive payoff simulators."""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from services.education_service import filter_rules, load_education_rules
from services.market_data_service import get_quote_summary
from services.options_data_service import get_options_chain
from ui.components.page_router import render_submenu_page
from utils.constants import COLORS


def render(submenu: str) -> None:
    """Route education submenu."""
    handlers = {
        "Learning roadmap": _learning_roadmap,
        "Rules playbook": _rules_playbook,
        "Stock P&L simulator": _stock_pnl_simulator,
        "Options P&L simulator": _options_pnl_simulator,
        "Strategy payoff lab": _strategy_payoff_lab,
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

    fee_col1, fee_col2 = st.columns(2)
    with fee_col1:
        stock_order_commission = st.number_input(
            "Stock commission per order ($)",
            min_value=0.0,
            value=0.0,
            step=0.50,
            help="Applied once on entry and once on exit.",
        )
    with fee_col2:
        stock_per_share_fee = st.number_input(
            "Per-share fee ($)",
            min_value=0.0,
            value=0.0,
            step=0.005,
            format="%.4f",
            help="Applied to every share on entry and exit.",
        )

    prices = _price_range(entry_price)
    sign = 1 if direction == "Long stock" else -1
    round_trip_commission = _stock_round_trip_commission(int(shares), stock_order_commission, stock_per_share_fee)
    pnl = [(price - entry_price) * shares * sign - round_trip_commission for price in prices]
    return_basis = entry_price * int(shares) + round_trip_commission
    frame = _payoff_frame(prices, pnl, entry_price, return_basis)
    _render_interactive_payoff_chart(
        _line_chart(frame, "Underlying Price", "P&L", f"{direction} payoff"),
        frame,
        key="stock_pnl_selected_scenario",
    )
    st.caption(f"Round-trip commission estimate included in P&L: **${round_trip_commission:,.2f}**.")


def _options_pnl_simulator() -> None:
    """Render Greek-aware single-leg options P&L simulator."""
    st.markdown("### Options P&L simulator")
    st.caption(
        "Simulate a single option using editable market inputs, Black-Scholes Greeks, implied volatility, "
        "time decay, rates, and broker commissions."
    )

    ticker = st.session_state.selected_ticker
    _render_chain_defaults_loader(ticker, "single_option")
    defaults = st.session_state.get("education_single_option_defaults", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        option_type = st.radio(
            "Option type",
            ["Call", "Put"],
            horizontal=True,
            index=0 if defaults.get("option_type", "Call") == "Call" else 1,
        )
        action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
    with col2:
        stock_price = st.number_input(
            "Current stock price",
            min_value=0.01,
            value=float(defaults.get("stock_price", 100.0)),
            step=1.0,
        )
        strike = st.number_input("Strike", min_value=0.01, value=float(defaults.get("strike", 105.0)), step=1.0)
    with col3:
        premium = st.number_input(
            "Entry premium per share",
            min_value=0.01,
            value=float(defaults.get("premium", 3.0)),
            step=0.25,
        )
        contracts = st.number_input("Contracts", min_value=1, value=1, step=1)

    greek_col1, greek_col2, greek_col3 = st.columns(3)
    with greek_col1:
        implied_volatility = st.number_input(
            "Implied volatility (%)",
            min_value=0.01,
            value=float(defaults.get("implied_volatility", 35.0)),
            step=1.0,
        )
        days_to_expiration = st.number_input("Days to expiration", min_value=0, value=30, step=1)
    with greek_col2:
        scenario_days_elapsed = st.number_input(
            "Simulate after days elapsed",
            min_value=0,
            max_value=int(days_to_expiration),
            value=min(7, int(days_to_expiration)),
            step=1,
        )
        volatility_change = st.number_input("IV change for scenario (vol points)", value=0.0, step=1.0)
    with greek_col3:
        risk_free_rate = st.number_input("Risk-free rate (%)", min_value=0.0, value=4.5, step=0.25)
        dividend_yield = st.number_input("Dividend yield (%)", min_value=0.0, value=0.0, step=0.25)

    fee_col1, fee_col2 = st.columns(2)
    with fee_col1:
        option_order_commission = st.number_input("Option commission per order ($)", min_value=0.0, value=0.0, step=0.50)
    with fee_col2:
        option_contract_fee = st.number_input("Per-contract fee ($)", min_value=0.0, value=0.65, step=0.05)

    prices = _price_range(stock_price)
    remaining_days = max(int(days_to_expiration) - int(scenario_days_elapsed), 0)
    scenario_iv = max((implied_volatility + volatility_change) / 100, 0.0001)
    direction_sign = 1 if action == "Buy" else -1
    round_trip_commission = _option_round_trip_commission(int(contracts), option_order_commission, option_contract_fee)
    values = [
        _option_model_value(option_type, price, strike, remaining_days, scenario_iv, risk_free_rate / 100, dividend_yield / 100)
        for price in prices
    ]
    pnl = [(value - premium) * 100 * contracts * direction_sign - round_trip_commission for value in values]
    return_basis = premium * 100 * int(contracts) + round_trip_commission
    frame = _payoff_frame(prices, pnl, stock_price, return_basis)
    _render_interactive_payoff_chart(
        _line_chart(frame, "Underlying Price", "P&L", f"{action} {option_type} scenario payoff"),
        frame,
        key="option_pnl_selected_scenario",
    )

    break_even = strike + premium if option_type == "Call" else strike - premium
    max_loss = premium * 100 * contracts + round_trip_commission if action == "Buy" else "Undefined / strategy dependent"
    greeks = _black_scholes_greeks(
        option_type,
        stock_price,
        strike,
        days_to_expiration,
        implied_volatility / 100,
        risk_free_rate / 100,
        dividend_yield / 100,
    )
    _render_option_greeks(greeks, int(contracts), direction_sign)
    st.info(
        f"Expiration break-even before commissions: **${break_even:.2f}**. "
        f"Modeled max loss for bought options: **{_format_money_or_text(max_loss)}**. "
        f"Round-trip commission included: **${round_trip_commission:,.2f}**."
    )
    _render_option_variable_explanations()


def _strategy_payoff_lab() -> None:
    """Render combined stock and options payoff simulator for multi-leg strategies."""
    st.markdown("### Strategy payoff lab")
    st.caption(
        "Preview net P&L for stocks, options, and combined positions. "
        "Green is profitable, yellow is near break-even, and red is loss."
    )

    ticker = st.session_state.selected_ticker
    _render_chain_defaults_loader(ticker, "strategy")

    preset = st.selectbox(
        "Strategy template",
        [
            "Covered call",
            "Protective put",
            "Collar",
            "Bull call spread",
            "Bear put spread",
            "Long straddle",
            "Long call butterfly",
            "Iron butterfly",
            "Custom",
        ],
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        stock_price = st.number_input("Current / stock entry price", min_value=0.01, value=100.0, step=1.0)
    with col2:
        share_lot = st.number_input("Stock shares for stock-based templates", min_value=1, value=100, step=10)
    with col3:
        contract_lot = st.number_input("Option contracts for option templates", min_value=1, value=1, step=1)

    sim_col1, sim_col2, sim_col3 = st.columns(3)
    with sim_col1:
        simulation_mode = st.radio("Simulation mode", ["At expiration", "Before expiration / Greeks"], horizontal=True)
        days_to_expiration = st.number_input("Days to expiration", min_value=0, value=30, step=1, key="strategy_dte")
    with sim_col2:
        scenario_days_elapsed = st.number_input(
            "Simulate after days elapsed",
            min_value=0,
            max_value=int(days_to_expiration),
            value=min(7, int(days_to_expiration)),
            step=1,
            key="strategy_elapsed",
        )
        volatility_change = st.number_input("IV change for scenario (vol points)", value=0.0, step=1.0, key="strategy_iv_shift")
    with sim_col3:
        risk_free_rate = st.number_input("Risk-free rate (%)", min_value=0.0, value=4.5, step=0.25, key="strategy_rate")
        dividend_yield = st.number_input("Dividend yield (%)", min_value=0.0, value=0.0, step=0.25, key="strategy_dividend")

    fee_col1, fee_col2, fee_col3, fee_col4 = st.columns(4)
    with fee_col1:
        stock_order_commission = st.number_input("Stock commission/order ($)", min_value=0.0, value=0.0, step=0.50)
    with fee_col2:
        stock_per_share_fee = st.number_input("Stock per-share fee ($)", min_value=0.0, value=0.0, step=0.005, format="%.4f")
    with fee_col3:
        option_order_commission = st.number_input("Option commission/order ($)", min_value=0.0, value=0.0, step=0.50)
    with fee_col4:
        option_contract_fee = st.number_input("Option per-contract fee ($)", min_value=0.0, value=0.65, step=0.05)

    default_legs = _strategy_template_legs(preset, stock_price, int(share_lot), int(contract_lot))
    edited_legs = st.data_editor(
        pd.DataFrame(default_legs),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Instrument": st.column_config.SelectboxColumn("Instrument", options=["Stock", "Call", "Put"], required=True),
            "Action": st.column_config.SelectboxColumn("Action", options=["Buy", "Sell"], required=True),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1, required=True),
            "Strike": st.column_config.NumberColumn("Strike", min_value=0.0, step=1.0),
            "Premium": st.column_config.NumberColumn("Premium", min_value=0.0, step=0.25),
            "IV %": st.column_config.NumberColumn("IV %", min_value=0.01, step=1.0),
        },
        key=f"strategy_legs_{preset}_{stock_price}_{share_lot}_{contract_lot}_{simulation_mode}",
    )

    valid_legs = _normalize_strategy_legs(edited_legs)
    if not valid_legs:
        st.warning("Add at least one stock or option leg to run the strategy simulation.")
        return

    prices = _price_range(stock_price)
    model_inputs = {
        "simulation_mode": simulation_mode,
        "days_to_expiration": int(days_to_expiration),
        "remaining_days": max(int(days_to_expiration) - int(scenario_days_elapsed), 0),
        "volatility_change": float(volatility_change),
        "risk_free_rate": risk_free_rate / 100,
        "dividend_yield": dividend_yield / 100,
        "stock_order_commission": float(stock_order_commission),
        "stock_per_share_fee": float(stock_per_share_fee),
        "option_order_commission": float(option_order_commission),
        "option_contract_fee": float(option_contract_fee),
    }
    model_inputs["return_basis"] = _strategy_return_basis(valid_legs, stock_price, model_inputs)
    frame = _strategy_payoff_frame(prices, valid_legs, stock_price, model_inputs)
    _render_interactive_payoff_chart(
        _strategy_payoff_chart(frame, preset),
        frame,
        key=f"strategy_pnl_selected_scenario_{preset}_{simulation_mode}",
    )
    _render_strategy_table(valid_legs, stock_price, model_inputs)
    _render_strategy_greeks(valid_legs, stock_price, model_inputs)

    with st.expander("How to read this strategy", expanded=True):
        st.markdown(_strategy_teaching_note(preset))
        _render_option_variable_explanations()


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


def _payoff_frame(prices: list[float], pnl: list[float], anchor_price: float, return_basis: float) -> pd.DataFrame:
    """Return a payoff frame with price and percentage move scenarios."""
    return pd.DataFrame(
        {
            "Underlying Price": prices,
            "Underlying Change %": [round(((price / anchor_price) - 1) * 100, 2) for price in prices],
            "P&L": pnl,
            "P&L %": [_pnl_percent(value, return_basis) for value in pnl],
        }
    )


def _render_chain_defaults_loader(ticker: str, context: str) -> None:
    """Render on-demand Alpha Vantage option-chain reference controls."""
    with st.expander("Use Alpha Vantage historical options as editable reference", expanded=False):
        st.caption(
            "Loads the nearest available chain snapshot. The values seed or inform the simulator, "
            "but you can still edit strikes, premiums, implied volatility, and commissions."
        )
        contract_type = st.radio(
            "Reference contract type",
            ["Call", "Put"],
            horizontal=True,
            key=f"{context}_reference_contract_type",
        )
        if st.button("Load option-chain reference", key=f"{context}_load_chain"):
            chain = get_options_chain(ticker)
            if chain.empty:
                st.warning(chain.attrs.get("error", f"No option-chain reference was available for {ticker}."))
            else:
                quote = get_quote_summary(ticker)
                defaults, reference = _option_defaults_from_chain(chain, contract_type, float(quote["price"]))
                defaults["stock_price"] = float(quote["price"])
                if context == "single_option":
                    st.session_state["education_single_option_defaults"] = defaults
                st.session_state[f"education_{context}_chain_reference"] = reference
                st.success(f"Loaded {contract_type.lower()} reference from {chain.attrs.get('source', 'options chain')}.")
                st.rerun()

        reference = st.session_state.get(f"education_{context}_chain_reference")
        if reference is not None and not reference.empty:
            st.caption("Nearest reference contracts from the latest loaded chain:")
            st.dataframe(reference, use_container_width=True, hide_index=True)


def _option_defaults_from_chain(chain: pd.DataFrame, option_type: str, stock_price: float) -> tuple[dict, pd.DataFrame]:
    """Return editable simulator defaults from the nearest option-chain contract."""
    frame = chain.copy()
    frame["Distance"] = (frame["Strike"] - stock_price).abs()
    reference_cols = ["Strike", "Call Bid", "Call Ask", "Put Bid", "Put Ask", "IV", "Delta"]
    reference = frame.sort_values("Distance").head(7)[[col for col in reference_cols if col in frame.columns]].copy()
    row = frame.sort_values("Distance").iloc[0]
    bid_col = f"{option_type} Bid"
    ask_col = f"{option_type} Ask"
    bid = _safe_float(row.get(bid_col), 0.0)
    ask = _safe_float(row.get(ask_col), 0.0)
    premium = (bid + ask) / 2 if bid > 0 and ask > 0 else max(bid, ask, 0.01)
    iv = _safe_float(row.get("IV"), 0.35)
    iv_percent = iv * 100 if iv <= 3 else iv
    return (
        {
            "option_type": option_type,
            "strike": float(row["Strike"]),
            "premium": round(premium, 2),
            "implied_volatility": round(iv_percent, 2),
        },
        reference,
    )


def _stock_round_trip_commission(shares: int, order_commission: float, per_share_fee: float) -> float:
    """Return estimated stock entry plus exit commission."""
    return 2 * (float(order_commission) + shares * float(per_share_fee))


def _option_round_trip_commission(contracts: int, order_commission: float, per_contract_fee: float) -> float:
    """Return estimated option entry plus exit commission."""
    return 2 * (float(order_commission) + contracts * float(per_contract_fee))


def _pnl_percent(pnl: float, return_basis: float) -> float:
    """Return P&L as a percentage of the estimated capital basis."""
    if return_basis <= 0:
        return 0.0
    return round((float(pnl) / return_basis) * 100, 2)


def _option_model_value(
    option_type: str,
    stock_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
) -> float:
    """Return Black-Scholes option value, falling back to intrinsic value at expiration."""
    if days_to_expiration <= 0 or volatility <= 0:
        return max(stock_price - strike, 0) if option_type == "Call" else max(strike - stock_price, 0)

    t = days_to_expiration / 365
    d1, d2 = _black_scholes_d1_d2(stock_price, strike, t, volatility, risk_free_rate, dividend_yield)
    discounted_stock = stock_price * math.exp(-dividend_yield * t)
    discounted_strike = strike * math.exp(-risk_free_rate * t)
    if option_type == "Call":
        return discounted_stock * _norm_cdf(d1) - discounted_strike * _norm_cdf(d2)
    return discounted_strike * _norm_cdf(-d2) - discounted_stock * _norm_cdf(-d1)


def _black_scholes_greeks(
    option_type: str,
    stock_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
) -> dict:
    """Return Black-Scholes Greeks per one option contract share."""
    if days_to_expiration <= 0 or volatility <= 0:
        intrinsic_delta = 1.0 if option_type == "Call" and stock_price > strike else -1.0 if option_type == "Put" and stock_price < strike else 0.0
        return {"Delta": intrinsic_delta, "Gamma": 0.0, "Theta": 0.0, "Vega": 0.0, "Rho": 0.0}

    t = days_to_expiration / 365
    d1, d2 = _black_scholes_d1_d2(stock_price, strike, t, volatility, risk_free_rate, dividend_yield)
    pdf_d1 = _norm_pdf(d1)
    discount_dividend = math.exp(-dividend_yield * t)
    discount_rate = math.exp(-risk_free_rate * t)
    if option_type == "Call":
        delta = discount_dividend * _norm_cdf(d1)
        theta = (
            -(stock_price * discount_dividend * pdf_d1 * volatility) / (2 * math.sqrt(t))
            - risk_free_rate * strike * discount_rate * _norm_cdf(d2)
            + dividend_yield * stock_price * discount_dividend * _norm_cdf(d1)
        ) / 365
        rho = strike * t * discount_rate * _norm_cdf(d2) / 100
    else:
        delta = discount_dividend * (_norm_cdf(d1) - 1)
        theta = (
            -(stock_price * discount_dividend * pdf_d1 * volatility) / (2 * math.sqrt(t))
            + risk_free_rate * strike * discount_rate * _norm_cdf(-d2)
            - dividend_yield * stock_price * discount_dividend * _norm_cdf(-d1)
        ) / 365
        rho = -strike * t * discount_rate * _norm_cdf(-d2) / 100
    gamma = discount_dividend * pdf_d1 / (stock_price * volatility * math.sqrt(t))
    vega = stock_price * discount_dividend * pdf_d1 * math.sqrt(t) / 100
    return {"Delta": delta, "Gamma": gamma, "Theta": theta, "Vega": vega, "Rho": rho}


def _black_scholes_d1_d2(
    stock_price: float,
    strike: float,
    t: float,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
) -> tuple[float, float]:
    """Return Black-Scholes d1 and d2 terms."""
    d1 = (
        math.log(stock_price / strike)
        + (risk_free_rate - dividend_yield + 0.5 * volatility**2) * t
    ) / (volatility * math.sqrt(t))
    d2 = d1 - volatility * math.sqrt(t)
    return d1, d2


def _norm_cdf(value: float) -> float:
    """Return standard normal cumulative probability."""
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def _norm_pdf(value: float) -> float:
    """Return standard normal probability density."""
    return math.exp(-0.5 * value**2) / math.sqrt(2 * math.pi)


def _render_option_greeks(greeks: dict, contracts: int, direction_sign: int) -> None:
    """Render contract-adjusted Greeks for the single-leg option simulator."""
    multiplier = contracts * 100 * direction_sign
    cols = st.columns(5)
    greek_specs = [
        ("Delta", greeks["Delta"] * multiplier, "Approx. $ change for a $1 stock move."),
        ("Gamma", greeks["Gamma"] * multiplier, "Approx. delta change for a $1 stock move."),
        ("Theta/day", greeks["Theta"] * multiplier, "Approx. daily time decay, all else equal."),
        ("Vega/vol pt", greeks["Vega"] * multiplier, "Approx. $ change for a 1-point IV move."),
        ("Rho/rate pt", greeks["Rho"] * multiplier, "Approx. $ change for a 1-point rate move."),
    ]
    for col, (label, value, help_text) in zip(cols, greek_specs):
        with col:
            st.metric(label, f"{value:+.2f}", help=help_text)


def _render_strategy_greeks(legs: list[dict], stock_price: float, model_inputs: dict) -> None:
    """Render aggregate Greeks for option legs in a strategy."""
    totals = {"Delta": 0.0, "Gamma": 0.0, "Theta": 0.0, "Vega": 0.0, "Rho": 0.0}
    has_options = False
    for leg in legs:
        if leg["Instrument"] == "Stock":
            totals["Delta"] += (1 if leg["Action"] == "Buy" else -1) * int(leg["Quantity"])
            continue
        has_options = True
        direction_sign = 1 if leg["Action"] == "Buy" else -1
        greeks = _black_scholes_greeks(
            leg["Instrument"],
            stock_price,
            float(leg["Strike"]),
            int(model_inputs.get("days_to_expiration", 30)),
            max(float(leg.get("IV %", 35.0)) / 100, 0.0001),
            float(model_inputs.get("risk_free_rate", 0.0)),
            float(model_inputs.get("dividend_yield", 0.0)),
        )
        for greek, value in greeks.items():
            totals[greek] += value * int(leg["Quantity"]) * 100 * direction_sign

    if not has_options and totals["Delta"] == 0:
        return
    st.markdown("**Approximate aggregate Greeks at current price**")
    cols = st.columns(5)
    for col, label in zip(cols, ["Delta", "Gamma", "Theta", "Vega", "Rho"]):
        suffix = "/day" if label == "Theta" else "/vol pt" if label == "Vega" else "/rate pt" if label == "Rho" else ""
        with col:
            st.metric(f"{label}{suffix}", f"{totals[label]:+.2f}")


def _render_option_variable_explanations() -> None:
    """Explain option variables and their P&L implications."""
    st.markdown(
        """
**Variable definitions and implications**

**Delta:** Measures directional exposure. A delta near `+0.50` behaves like roughly 50 shares per contract; negative delta benefits from price declines.

**Gamma:** Measures how quickly delta changes when the stock moves. High gamma means the position becomes more sensitive as price moves, which can help buyers and hurt short-option sellers.

**Theta:** Measures time decay. Long options usually have negative theta; short options usually collect theta but carry tail risk.

**Vega:** Measures sensitivity to implied volatility. Long options usually benefit when IV rises; short options usually benefit when IV falls.

**Rho:** Measures sensitivity to interest rates. It is usually smaller than delta, gamma, theta, or vega for short-dated equity options, but it can matter more for long-dated options.

**Implied volatility:** Higher IV makes options more expensive. A correct directional view can still lose money if IV drops enough after entry.

**Days elapsed / days to expiration:** As time passes, extrinsic value usually decays. The decay tends to accelerate near expiration, especially for at-the-money options.

**Commissions:** Broker commissions and per-contract fees reduce every strategy's net P&L. They matter more for multi-leg spreads, butterflies, and small premium trades.
"""
    )


def _format_money_or_text(value: object) -> str:
    """Format numeric money values while preserving text descriptions."""
    return f"${float(value):,.2f}" if isinstance(value, (int, float)) else str(value)


def _strategy_template_legs(preset: str, stock_price: float, shares: int, contracts: int) -> list[dict]:
    """Return editable strategy legs for common stock/options structures."""
    low = round(stock_price * 0.9, 2)
    lower_mid = round(stock_price * 0.95, 2)
    at_the_money = round(stock_price, 2)
    upper_mid = round(stock_price * 1.05, 2)
    high = round(stock_price * 1.1, 2)

    templates = {
        "Covered call": [
            _stock_leg("Buy", shares),
            _option_leg("Call", "Sell", contracts, upper_mid, stock_price * 0.025),
        ],
        "Protective put": [
            _stock_leg("Buy", shares),
            _option_leg("Put", "Buy", contracts, lower_mid, stock_price * 0.03),
        ],
        "Collar": [
            _stock_leg("Buy", shares),
            _option_leg("Put", "Buy", contracts, lower_mid, stock_price * 0.025),
            _option_leg("Call", "Sell", contracts, upper_mid, stock_price * 0.025),
        ],
        "Bull call spread": [
            _option_leg("Call", "Buy", contracts, at_the_money, stock_price * 0.045),
            _option_leg("Call", "Sell", contracts, high, stock_price * 0.018),
        ],
        "Bear put spread": [
            _option_leg("Put", "Buy", contracts, at_the_money, stock_price * 0.045),
            _option_leg("Put", "Sell", contracts, low, stock_price * 0.018),
        ],
        "Long straddle": [
            _option_leg("Call", "Buy", contracts, at_the_money, stock_price * 0.04),
            _option_leg("Put", "Buy", contracts, at_the_money, stock_price * 0.04),
        ],
        "Long call butterfly": [
            _option_leg("Call", "Buy", contracts, low, stock_price * 0.11),
            _option_leg("Call", "Sell", contracts * 2, at_the_money, stock_price * 0.05),
            _option_leg("Call", "Buy", contracts, high, stock_price * 0.015),
        ],
        "Iron butterfly": [
            _option_leg("Put", "Buy", contracts, low, stock_price * 0.015),
            _option_leg("Put", "Sell", contracts, at_the_money, stock_price * 0.045),
            _option_leg("Call", "Sell", contracts, at_the_money, stock_price * 0.045),
            _option_leg("Call", "Buy", contracts, high, stock_price * 0.015),
        ],
        "Custom": [
            _stock_leg("Buy", shares),
            _option_leg("Call", "Buy", contracts, upper_mid, stock_price * 0.03),
        ],
    }
    return templates[preset]


def _stock_leg(action: str, quantity: int) -> dict:
    """Return a stock leg row for the strategy editor."""
    return {"Instrument": "Stock", "Action": action, "Quantity": quantity, "Strike": 0.0, "Premium": 0.0}


def _option_leg(instrument: str, action: str, quantity: int, strike: float, premium: float) -> dict:
    """Return an option leg row for the strategy editor."""
    return {
        "Instrument": instrument,
        "Action": action,
        "Quantity": quantity,
        "Strike": round(strike, 2),
        "Premium": round(premium, 2),
        "IV %": 35.0,
    }


def _normalize_strategy_legs(legs: pd.DataFrame) -> list[dict]:
    """Convert edited strategy rows into validated leg dictionaries."""
    normalized = []
    for _, row in legs.iterrows():
        instrument = str(row.get("Instrument", "")).strip().title()
        action = str(row.get("Action", "")).strip().title()
        quantity = int(_safe_float(row.get("Quantity"), 0))
        strike = _safe_float(row.get("Strike"), 0.0)
        premium = _safe_float(row.get("Premium"), 0.0)
        implied_volatility = _safe_float(row.get("IV %"), 35.0)
        if instrument not in {"Stock", "Call", "Put"} or action not in {"Buy", "Sell"} or quantity <= 0:
            continue
        if instrument in {"Call", "Put"} and strike <= 0:
            continue
        normalized.append(
            {
                "Instrument": instrument,
                "Action": action,
                "Quantity": quantity,
                "Strike": strike,
                "Premium": premium,
                "IV %": implied_volatility,
            }
        )
    return normalized


def _safe_float(value: object, default: float) -> float:
    """Return a float while treating blank editor cells as defaults."""
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _strategy_payoff_frame(
    prices: list[float],
    legs: list[dict],
    stock_entry_price: float,
    model_inputs: dict | None = None,
) -> pd.DataFrame:
    """Calculate total expiration payoff across all strategy legs."""
    model_inputs = model_inputs or {}
    rows = []
    for price in prices:
        total_pnl = sum(_leg_pnl(price, leg, stock_entry_price, model_inputs) for leg in legs)
        rows.append(
            {
                "Underlying Price": price,
                "Underlying Change %": round(((price / stock_entry_price) - 1) * 100, 2),
                "P&L": round(total_pnl, 2),
                "P&L %": _pnl_percent(total_pnl, float(model_inputs.get("return_basis", 0.0))),
            }
        )
    return pd.DataFrame(rows)


def _leg_pnl(price: float, leg: dict, stock_entry_price: float, model_inputs: dict | None = None) -> float:
    """Calculate expiration P&L for one stock or option leg."""
    model_inputs = model_inputs or {}
    sign = 1 if leg["Action"] == "Buy" else -1
    quantity = int(leg["Quantity"])
    if leg["Instrument"] == "Stock":
        commission = _stock_round_trip_commission(
            quantity,
            float(model_inputs.get("stock_order_commission", 0.0)),
            float(model_inputs.get("stock_per_share_fee", 0.0)),
        )
        return (price - stock_entry_price) * quantity * sign - commission

    strike = float(leg["Strike"])
    premium = float(leg["Premium"])
    if model_inputs.get("simulation_mode") == "Before expiration / Greeks":
        volatility = max((float(leg.get("IV %", 35.0)) + float(model_inputs.get("volatility_change", 0.0))) / 100, 0.0001)
        value = _option_model_value(
            leg["Instrument"],
            price,
            strike,
            int(model_inputs.get("remaining_days", 0)),
            volatility,
            float(model_inputs.get("risk_free_rate", 0.0)),
            float(model_inputs.get("dividend_yield", 0.0)),
        )
    else:
        value = max(price - strike, 0) if leg["Instrument"] == "Call" else max(strike - price, 0)
    commission = _option_round_trip_commission(
        quantity,
        float(model_inputs.get("option_order_commission", 0.0)),
        float(model_inputs.get("option_contract_fee", 0.0)),
    )
    return (value - premium) * 100 * quantity * sign - commission


def _strategy_payoff_chart(frame: pd.DataFrame, title: str) -> go.Figure:
    """Build payoff chart with red, yellow, and green P&L areas."""
    max_abs_pnl = max(float(frame["P&L"].abs().max()), 1.0)
    yellow_band = max_abs_pnl * 0.08
    colors = [
        COLORS["positive"] if value > yellow_band else COLORS["negative"] if value < -yellow_band else COLORS["accent"]
        for value in frame["P&L"]
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=frame["Underlying Price"],
            y=frame["P&L"],
            customdata=frame[["Underlying Change %"]],
            marker_color=colors,
            name="Loss / break-even / profit zones",
            opacity=0.28,
            selected=dict(marker=dict(opacity=0.28)),
            unselected=dict(marker=dict(opacity=0.28)),
            hovertemplate="Price: $%{x:,.2f}<br>Move: %{customdata[0]:+.2f}%<br>P&L: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["Underlying Price"],
            y=frame["P&L"],
            customdata=frame[["Underlying Change %"]],
            mode="lines",
            name="Total strategy P&L",
            line=dict(color=COLORS["secondary"], width=4),
            hovertemplate="Price: $%{x:,.2f}<br>Move: %{customdata[0]:+.2f}%<br>P&L: $%{y:,.2f}<extra></extra>",
        )
    )
    _add_clickable_scenario_markers(fig, frame)
    fig.add_hrect(y0=-yellow_band, y1=yellow_band, fillcolor=COLORS["accent"], opacity=0.12, line_width=0)
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"], annotation_text="Break-even")
    fig.update_layout(
        title=f"{title} expiration payoff",
        height=460,
        margin=dict(l=40, r=30, t=55, b=45),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        xaxis_title="Underlying Price and % Move",
        yaxis_title="Profit / Loss ($)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    _apply_price_percent_ticks(fig, frame, "Underlying Price")
    return fig


def _render_strategy_table(legs: list[dict], stock_entry_price: float, model_inputs: dict | None = None) -> None:
    """Render a cleaned strategy leg table with total net opening cash flow."""
    model_inputs = model_inputs or {}
    frame = pd.DataFrame(legs)
    net_opening_cash_flow = 0.0
    round_trip_commission = 0.0
    for leg in legs:
        sign = -1 if leg["Action"] == "Buy" else 1
        if leg["Instrument"] == "Stock":
            net_opening_cash_flow += stock_entry_price * leg["Quantity"] * sign
            round_trip_commission += _stock_round_trip_commission(
                int(leg["Quantity"]),
                float(model_inputs.get("stock_order_commission", 0.0)),
                float(model_inputs.get("stock_per_share_fee", 0.0)),
            )
        else:
            net_opening_cash_flow += leg["Premium"] * 100 * leg["Quantity"] * sign
            round_trip_commission += _option_round_trip_commission(
                int(leg["Quantity"]),
                float(model_inputs.get("option_order_commission", 0.0)),
                float(model_inputs.get("option_contract_fee", 0.0)),
            )
    st.caption(f"Estimated net opening cash flow: **${net_opening_cash_flow:,.2f}**")
    st.caption(f"Estimated round-trip commissions included in payoff: **${round_trip_commission:,.2f}**")
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _strategy_return_basis(legs: list[dict], stock_entry_price: float, model_inputs: dict) -> float:
    """Estimate a practical percentage-return basis for a multi-leg strategy."""
    gross_basis = 0.0
    commissions = 0.0
    for leg in legs:
        quantity = int(leg["Quantity"])
        if leg["Instrument"] == "Stock":
            gross_basis += stock_entry_price * quantity
            commissions += _stock_round_trip_commission(
                quantity,
                float(model_inputs.get("stock_order_commission", 0.0)),
                float(model_inputs.get("stock_per_share_fee", 0.0)),
            )
        else:
            gross_basis += float(leg["Premium"]) * 100 * quantity
            commissions += _option_round_trip_commission(
                quantity,
                float(model_inputs.get("option_order_commission", 0.0)),
                float(model_inputs.get("option_contract_fee", 0.0)),
            )
    return max(gross_basis + commissions, 1.0)


def _strategy_teaching_note(preset: str) -> str:
    """Return educational guidance for the selected strategy."""
    notes = {
        "Covered call": """
**When it is used:** A covered call is often used when you already own the stock and expect it to move sideways or rise moderately, but not explode higher.

**Pros:** You receive option premium upfront, which can reduce your effective cost basis and create income from a stock position. It can be useful when you are willing to sell the shares at the call strike.

**Cons:** Your upside is capped above the short call strike. If the stock rallies strongly, the covered call underperforms simply holding the stock.

**Risk and reward:** Reward is limited to stock appreciation up to the strike plus the premium collected. Downside risk is still mostly stock risk: if the stock falls sharply, the premium helps only a little.
""",
        "Protective put": """
**When it is used:** A protective put is used when you own stock but want insurance against a large downside move, such as before earnings, a major event, or a volatile market period.

**Pros:** It defines a floor below the put strike, giving you a clearer maximum downside at expiration. You keep upside participation if the stock rises.

**Cons:** The put premium is an insurance cost. If the stock stays flat or rises only slightly, the premium can reduce or eliminate your net profit.

**Risk and reward:** Downside is limited after the put protection starts, while upside remains open. The trade-off is that your break-even moves higher because you paid for protection.
""",
        "Collar": """
**When it is used:** A collar is used when you own stock and want downside protection, but you are willing to cap upside to reduce or offset the cost of that protection.

**Pros:** It creates a defined risk zone: the long put protects the downside and the short call helps finance the put. It can be practical for preserving gains after a strong stock move.

**Cons:** The short call limits upside. If the stock rallies above the call strike, you may miss additional gains or have the shares called away.

**Risk and reward:** Loss is limited below the put strike, reward is capped above the call strike, and the net cost depends on the premiums paid and received.
""",
        "Bull call spread": """
**When it is used:** A bull call spread is used when you are moderately bullish and expect the stock to rise toward a target, but you do not want to pay for an uncovered long call.

**Pros:** It costs less than buying a call alone because the short call helps finance the long call. Maximum loss and maximum reward are both defined.

**Cons:** Upside is capped at the short call strike. If the stock rallies far beyond that level, the spread stops gaining after the maximum profit zone.

**Risk and reward:** Maximum loss is usually the net debit paid. Maximum reward is the width between strikes minus the net debit. Best results happen when the stock finishes at or above the short call strike.
""",
        "Bear put spread": """
**When it is used:** A bear put spread is used when you are moderately bearish and expect a controlled move lower, not necessarily a crash.

**Pros:** It gives bearish exposure with defined risk and usually costs less than buying a put outright because the short put offsets part of the premium.

**Cons:** Profit is capped below the short put strike. If the stock collapses far below that strike, the spread will not keep gaining beyond its maximum value.

**Risk and reward:** Maximum loss is usually the net debit paid. Maximum reward is the strike width minus the net debit. Best results happen when the stock finishes at or below the short put strike.
""",
        "Long straddle": """
**When it is used:** A long straddle is used when you expect a large move but are uncertain about direction. It is common around earnings, regulatory decisions, macro events, or volatility breakouts.

**Pros:** It can profit from a large move up or down. Direction matters less than the size of the move.

**Cons:** It is expensive because you buy both a call and a put. If the stock stays near the strike, both options can lose value and the strategy can suffer a large percentage loss.

**Risk and reward:** Maximum loss is the total premium paid. Upside profit is theoretically unlimited through the call, and downside profit grows through the put until the stock approaches zero. The stock must move far enough to recover both premiums.
""",
        "Long call butterfly": """
**When it is used:** A long call butterfly is used when you expect the stock to finish near a specific target price, usually the middle strike, by expiration.

**Pros:** It is a defined-risk structure with a relatively low net cost. It can offer attractive reward if the stock pins near the center strike.

**Cons:** It has a narrow profit zone. If the stock moves too little or too much, the payoff can deteriorate quickly.

**Risk and reward:** Maximum loss is usually the net debit paid. Maximum reward occurs near the middle strike and is limited by the wing width minus net cost. This is a precision strategy, not a broad bullish bet.
""",
        "Iron butterfly": """
**When it is used:** An iron butterfly is used when you expect the stock to stay near a central price and implied volatility or option premiums are attractive enough to sell.

**Pros:** It collects premium upfront and has defined risk because the long wings limit extreme losses. It can perform well when price stays near the short strike.

**Cons:** It is vulnerable to large moves in either direction. The profit zone can be narrow, and assignment risk can exist when short options are in the money.

**Risk and reward:** Maximum reward is the net credit collected, usually achieved near the short strike. Maximum loss is limited by the wing width minus the credit received. The strategy benefits from stability, not movement.
""",
        "Custom": """
**When it is used:** Custom mode is for learning and experimentation. Use it to combine stock, calls, and puts into your own structure and see how each leg changes the payoff curve.

**Pros:** It helps you understand how strategies are built from basic components. You can test covered calls, spreads, collars, ratios, or mixed stock/options structures.

**Cons:** Custom combinations can create unexpected exposures, especially when selling options or mixing different quantities. A payoff that looks attractive in one price range may hide major risk elsewhere.

**Risk and reward:** The risk and reward depend entirely on the legs you build. Always inspect the worst simulated P&L, best simulated P&L, break-even area, and where the payoff curve changes slope.
""",
    }
    return notes[preset].strip()


def _line_chart(frame: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    """Build a P&L line chart."""
    colors = [COLORS["positive"] if value >= 0 else COLORS["negative"] for value in frame[y_col]]
    fig = go.Figure()
    customdata = frame[["Underlying Change %"]] if "Underlying Change %" in frame.columns else None
    hovertemplate = (
        "Price: $%{x:,.2f}<br>Move: %{customdata[0]:+.2f}%<br>P&L: $%{y:,.2f}<extra></extra>"
        if customdata is not None
        else None
    )
    fig.add_trace(
        go.Scatter(
            x=frame[x_col],
            y=frame[y_col],
            customdata=customdata,
            mode="lines",
            name="P&L",
            line=dict(color=COLORS["secondary"], width=3),
            hovertemplate=hovertemplate,
        )
    )
    fig.add_trace(
        go.Bar(
            x=frame[x_col],
            y=frame[y_col],
            customdata=customdata,
            marker_color=colors,
            name="P&L zones",
            opacity=0.2,
            selected=dict(marker=dict(opacity=0.2)),
            unselected=dict(marker=dict(opacity=0.2)),
            hovertemplate=hovertemplate,
        )
    )
    _add_clickable_scenario_markers(fig, frame)
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"])
    fig.update_layout(
        title=title,
        height=420,
        margin=dict(l=40, r=30, t=55, b=45),
        paper_bgcolor="white",
        plot_bgcolor="#fafbfc",
        xaxis_title=f"{x_col} and % Move" if "Underlying Change %" in frame.columns else x_col,
        yaxis_title="Profit / Loss ($)",
        hovermode="x unified",
    )
    if "Underlying Change %" in frame.columns:
        _apply_price_percent_ticks(fig, frame, x_col)
    return fig


def _render_interactive_payoff_chart(fig: go.Figure, frame: pd.DataFrame, key: str) -> None:
    """Render a payoff chart and show a selected scenario result."""
    state_key = f"{key}_selected_row"
    st.caption("Move the mouse over the chart for details, then choose a scenario below to calculate exact P&L.")
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"{key}_chart",
        config={"displayModeBar": True},
    )
    selected_row = _scenario_selector_row(frame, key, state_key)
    _render_selected_pnl_result(selected_row)


def _scenario_selector_row(frame: pd.DataFrame, key: str, state_key: str) -> pd.Series:
    """Return the row selected through a percent-move scenario slider."""
    slider_key = f"{key}_scenario_pct_slider"
    min_change = int(frame["Underlying Change %"].min())
    max_change = int(frame["Underlying Change %"].max())
    if slider_key not in st.session_state:
        st.session_state[slider_key] = 0
    else:
        st.session_state[slider_key] = min(max(int(st.session_state[slider_key]), min_change), max_change)

    st.slider(
        "Selected scenario (% price move)",
        min_value=min_change,
        max_value=max_change,
        step=1,
        format="%d%%",
        key=slider_key,
        help="Starts at 0%. Move right for positive price scenarios and left for negative price scenarios.",
        on_change=_sync_selected_scenario,
        args=(frame, slider_key, state_key),
    )
    _sync_selected_scenario(frame, slider_key, state_key)
    return pd.Series(st.session_state[state_key])


def _sync_selected_scenario(frame: pd.DataFrame, slider_key: str, state_key: str) -> None:
    """Sync the selected scenario row from the slider into session state."""
    selected_change = float(st.session_state.get(slider_key, 0))
    distances = (frame["Underlying Change %"] - selected_change).abs()
    st.session_state[state_key] = frame.loc[distances.idxmin()].to_dict()


def _add_clickable_scenario_markers(fig: go.Figure, frame: pd.DataFrame) -> None:
    """Add point markers that make Plotly scenario selection explicit."""
    fig.add_trace(
        go.Scatter(
            x=frame["Underlying Price"],
            y=frame["P&L"],
            customdata=frame[["Underlying Change %"]],
            mode="markers",
            name="Click scenario",
            marker=dict(size=8, color=COLORS["secondary"], opacity=0.55, line=dict(color="white", width=1)),
            selected=dict(marker=dict(opacity=1.0, size=11, color=COLORS["accent"])),
            unselected=dict(marker=dict(opacity=0.55)),
            hovertemplate="Price: $%{x:,.2f}<br>Move: %{customdata[0]:+.2f}%<br>P&L: $%{y:,.2f}<extra></extra>",
        )
    )


def _render_selected_pnl_result(row: pd.Series | None) -> None:
    """Render the third P&L result for the clicked chart scenario."""
    if row is None:
        st.info("Use the selected scenario control to show P&L and percentage gain/loss.")
        return
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Selected scenario P&L",
            f"${float(row['P&L']):,.2f}",
            _price_and_pct_label(row),
        )
    with col2:
        st.metric("Selected scenario gain/loss", f"{float(row.get('P&L %', 0.0)):+.2f}%")


def _apply_price_percent_ticks(fig: go.Figure, frame: pd.DataFrame, x_col: str) -> None:
    """Show both price and percent variation on payoff chart x-axis ticks."""
    tick_indices = list(range(0, len(frame), 10))
    if len(frame) - 1 not in tick_indices:
        tick_indices.append(len(frame) - 1)
    tick_rows = frame.iloc[tick_indices]
    fig.update_xaxes(
        tickmode="array",
        tickvals=tick_rows[x_col],
        ticktext=[
            f"${float(row[x_col]):,.2f}<br>{float(row['Underlying Change %']):+.0f}%"
            for _, row in tick_rows.iterrows()
        ],
    )


def _price_and_pct_label(row: pd.Series) -> str:
    """Return a compact price plus percentage scenario label."""
    if "Underlying Change %" not in row:
        return f"at ${float(row['Underlying Price']):.2f}"
    return f"at ${float(row['Underlying Price']):.2f} ({float(row['Underlying Change %']):+.2f}%)"
