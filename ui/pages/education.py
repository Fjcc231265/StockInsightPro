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

_SIMULATOR_TOOLKIT: dict[str, str] = {
    "implied_volatility": (
        "Market-implied expected volatility for this option, as an annualized percentage. "
        "Higher IV means higher option premiums."
    ),
    "days_to_expiration": "Calendar days until the option expires. Time decay accelerates near expiration.",
    "scenario_days_elapsed": (
        "How many days pass before the scenario is priced. Remaining time = days to expiration minus this value. "
        "Used with IV change for before-expiration payoff curves."
    ),
    "iv_change_vol_points": (
        "How much implied volatility (IV) shifts for the scenario, in percentage points—not a percent-of-percent change. "
        "Example: base IV 35% and +5 vol points → scenario IV 40%. "
        "Long options usually gain when IV rises; short options usually lose (vega)."
    ),
    "risk_free_rate": "Annual risk-free interest rate used in Black-Scholes pricing (affects rho and carry).",
    "dividend_yield": "Annual dividend yield on the underlying stock used in Black-Scholes pricing.",
    "option_order_commission": "Flat broker fee charged once per option order (entry and again on exit).",
    "option_contract_fee": "Per-contract fee charged by the broker on each option order (entry and exit).",
    "valuation_model": (
        "European uses Black-Scholes and assumes exercise only at expiration. "
        "American uses a binomial tree approximation that allows early exercise before expiration."
    ),
    "simulation_mode": (
        "At expiration: intrinsic value only. Before expiration / Greeks: selected valuation model with time left, IV shift, and rates."
    ),
    "price_move_scenario": (
        "Starts at 0%. Move right for positive price scenarios and left for negative price scenarios."
    ),
    "strategy_template": (
        "Starter layouts only. Covered call, protective put, collar, and Custom include stock plus options. "
        "Spreads, straddles, and butterflies are options-only templates. You can always edit the table below "
        "to add Stock, Call, or Put rows and build any combination."
    ),
}

_STRATEGY_TEMPLATE_HINTS: dict[str, str] = {
    "Covered call": "Stock + short call (income on shares you own).",
    "Protective put": "Stock + long put (downside insurance).",
    "Collar": "Stock + long put + short call (defined risk band).",
    "Bull call spread": "Options only: long call + short call.",
    "Bear put spread": "Options only: long put + short put.",
    "Long straddle": "Options only: long call + long put (same strike).",
    "Long call butterfly": "Options only: three call legs.",
    "Iron butterfly": "Options only: four option legs.",
    "Custom": "Start here for any mix — stock plus one or more calls/puts.",
}


def render(submenu: str) -> None:
    """Route education submenu."""
    _render_simulator_input_highlight_style()
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


def _render_simulator_input_highlight_style() -> None:
    """Highlight editable simulator number fields on the Education page."""
    st.markdown(
        """
<style>
div[data-testid="stNumberInput"] input {
    background: #fff4bf !important;
    border: 1px solid #e4b100 !important;
    box-shadow: 0 0 0 1px rgba(228, 177, 0, 0.14) !important;
}

div[data-testid="stNumberInput"] label p::after {
    content: " editable";
    display: inline-block;
    margin-left: 0.35rem;
    padding: 0.05rem 0.35rem;
    border-radius: 999px;
    background: #fff4bf;
    color: #6b5200;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}

.sip-editable-note {
    margin: 0.35rem 0 1rem 0;
    padding: 0.65rem 0.85rem;
    border-left: 5px solid #e4b100;
    background: #fff9df;
    border-radius: 0.45rem;
    color: #3f3420;
    font-size: 0.92rem;
}

.sip-editable-table-note {
    margin: 0.6rem 0 0.35rem 0;
    padding: 0.7rem 0.85rem;
    border: 2px solid #e4b100;
    background: #fff4bf;
    border-radius: 0.55rem;
    color: #3f3420;
    font-weight: 700;
}

div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
    background: #fff4bf !important;
    border: 2px solid #e4b100 !important;
    border-radius: 0.65rem !important;
    padding: 0.45rem !important;
    box-shadow: 0 0 0 2px rgba(228, 177, 0, 0.12) !important;
}

div[data-testid="stDataFrame"] [role="grid"],
div[data-testid="stDataEditor"] [role="grid"],
div[data-testid="stDataFrame"] canvas,
div[data-testid="stDataEditor"] canvas {
    background-color: #fff9df !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_editable_assumption_note() -> None:
    """Explain why simulator inputs are highlighted."""
    st.markdown(
        """
<div class="sip-editable-note">
Yellow fields are editable assumptions. Change these numbers to test different prices, strikes,
premiums, volatility, time, rates, contract counts, and commissions.
</div>
""",
        unsafe_allow_html=True,
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
    _render_editable_assumption_note()
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
    st.caption(f"Round-trip commission estimate included in P&L: **\\${round_trip_commission:,.2f}**.")


def _options_pnl_simulator() -> None:
    """Render Greek-aware single-leg options P&L simulator."""
    st.markdown("### Options P&L simulator")
    _render_editable_assumption_note()
    st.caption(
        "Simulate a single option using editable market inputs, model-based Greeks, implied volatility, "
        "time decay, rates, and broker commissions."
    )

    ticker = st.session_state.selected_ticker
    _render_chain_defaults_loader(ticker, "single_option")
    defaults = st.session_state.get("education_single_option_defaults", {})
    reference_chain = st.session_state.get("education_single_option_chain_full")

    col1, col2, col3 = st.columns(3)
    with col1:
        option_type = st.radio(
            "Option type",
            ["Call", "Put"],
            horizontal=True,
            index=0 if defaults.get("option_type", "Call") == "Call" else 1,
        )
        action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
    reference_defaults = _render_single_option_reference_strike_selector(
        reference_chain,
        option_type,
        float(defaults.get("strike", 105.0)),
    )
    input_defaults = {**defaults, **reference_defaults}
    with col2:
        stock_price = st.number_input(
            "Current stock price",
            min_value=0.01,
            value=float(input_defaults.get("stock_price", 100.0)),
            step=1.0,
        )
        strike = st.number_input(
            "Strike",
            min_value=0.01,
            value=float(input_defaults.get("strike", 105.0)),
            step=1.0,
            key=f"single_option_strike_{option_type}_{input_defaults.get('strike', 105.0)}",
        )
    with col3:
        premium = st.number_input(
            "Entry premium per share",
            min_value=0.01,
            value=float(input_defaults.get("premium", 3.0)),
            step=0.25,
            key=f"single_option_premium_{option_type}_{input_defaults.get('strike', 105.0)}",
        )
        contracts = st.number_input("Contracts", min_value=1, value=1, step=1)

    greek_col1, greek_col2, greek_col3 = st.columns(3)
    with greek_col1:
        implied_volatility = st.number_input(
            "Implied volatility (%)",
            min_value=0.01,
            value=float(input_defaults.get("implied_volatility", 35.0)),
            step=1.0,
            help=_SIMULATOR_TOOLKIT["implied_volatility"],
            key=f"single_option_iv_{option_type}_{input_defaults.get('strike', 105.0)}",
        )
        days_to_expiration = st.number_input(
            "Days to expiration",
            min_value=0,
            value=30,
            step=1,
            help=_SIMULATOR_TOOLKIT["days_to_expiration"],
        )
    with greek_col2:
        scenario_days_elapsed = st.number_input(
            "Simulate after days elapsed",
            min_value=0,
            max_value=int(days_to_expiration),
            value=min(7, int(days_to_expiration)),
            step=1,
            help=_SIMULATOR_TOOLKIT["scenario_days_elapsed"],
        )
        volatility_change = st.number_input(
            "IV change for scenario (vol points)",
            value=0.0,
            step=1.0,
            help=_SIMULATOR_TOOLKIT["iv_change_vol_points"],
        )
    with greek_col3:
        valuation_model = st.selectbox(
            "Valuation model",
            ["European (Black-Scholes)", "American (binomial tree)"],
            help=_SIMULATOR_TOOLKIT["valuation_model"],
        )
        risk_free_rate = st.number_input(
            "Risk-free rate (%)",
            min_value=0.0,
            value=4.5,
            step=0.25,
            help=_SIMULATOR_TOOLKIT["risk_free_rate"],
        )
        dividend_yield = st.number_input(
            "Dividend yield (%)",
            min_value=0.0,
            value=0.0,
            step=0.25,
            help=_SIMULATOR_TOOLKIT["dividend_yield"],
        )

    scenario_iv_pct = implied_volatility + volatility_change
    st.caption(
        f"Scenario pricing uses **{_valuation_model_label(valuation_model)}**, **{scenario_iv_pct:.1f}% IV** "
        f"({implied_volatility:.1f}% base {'+' if volatility_change >= 0 else ''}{volatility_change:.1f} vol points) "
        f"with **{max(int(days_to_expiration) - int(scenario_days_elapsed), 0)}** days remaining."
    )

    fee_col1, fee_col2 = st.columns(2)
    with fee_col1:
        option_order_commission = st.number_input(
            "Option commission per order ($)",
            min_value=0.0,
            value=0.0,
            step=0.50,
            help=_SIMULATOR_TOOLKIT["option_order_commission"],
        )
    with fee_col2:
        option_contract_fee = st.number_input(
            "Per-contract fee ($)",
            min_value=0.0,
            value=0.65,
            step=0.05,
            help=_SIMULATOR_TOOLKIT["option_contract_fee"],
        )

    prices = _price_range(stock_price)
    remaining_days = max(int(days_to_expiration) - int(scenario_days_elapsed), 0)
    scenario_iv = max((implied_volatility + volatility_change) / 100, 0.0001)
    direction_sign = 1 if action == "Buy" else -1
    round_trip_commission = _option_round_trip_commission(int(contracts), option_order_commission, option_contract_fee)
    values = [
        _option_model_value(
            option_type,
            price,
            strike,
            remaining_days,
            scenario_iv,
            risk_free_rate / 100,
            dividend_yield / 100,
            valuation_model,
        )
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
    greeks = _option_model_greeks(
        option_type,
        stock_price,
        strike,
        days_to_expiration,
        implied_volatility / 100,
        risk_free_rate / 100,
        dividend_yield / 100,
        valuation_model,
    )
    _render_option_greeks(greeks, int(contracts), direction_sign)
    st.info(
        f"Expiration break-even before commissions: **\\${break_even:.2f}**. "
        f"Modeled max loss for bought options: **{_format_money_or_text(max_loss)}**. "
        f"Round-trip commission included: **\\${round_trip_commission:,.2f}**."
    )
    _render_option_variable_explanations()


def _strategy_payoff_lab() -> None:
    """Render combined stock and options payoff simulator for multi-leg strategies."""
    st.markdown("### Strategy payoff lab")
    _render_editable_assumption_note()
    st.caption(
        "Preview net P&L for stocks, options, and combined positions. "
        "You are not limited to one option type: each row in the strategy table is one leg "
        "(Stock, Call, or Put). Green is profitable, yellow is near break-even, and red is loss."
    )

    ticker = st.session_state.selected_ticker
    _render_chain_defaults_loader(ticker, "strategy")

    preset = st.selectbox(
        "Strategy template",
        [
            "Custom",
            "Covered call",
            "Protective put",
            "Collar",
            "Bull call spread",
            "Bear put spread",
            "Long straddle",
            "Long call butterfly",
            "Iron butterfly",
        ],
        index=0,
        help=_SIMULATOR_TOOLKIT["strategy_template"],
    )
    st.caption(_STRATEGY_TEMPLATE_HINTS.get(preset, ""))
    if preset in {"Bull call spread", "Bear put spread", "Long straddle", "Long call butterfly", "Iron butterfly"}:
        st.info(
            "This template is **options-only**. To add stock, choose **Custom**, **Covered call**, "
            "**Protective put**, or **Collar** — or add a **Stock** row in the table below (+ button)."
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
        days_to_expiration = st.number_input(
            "Days to expiration",
            min_value=0,
            value=30,
            step=1,
            key="strategy_dte",
            help=_SIMULATOR_TOOLKIT["days_to_expiration"],
        )
        st.caption(_SIMULATOR_TOOLKIT["simulation_mode"])
    with sim_col2:
        scenario_days_elapsed = st.number_input(
            "Simulate after days elapsed",
            min_value=0,
            max_value=int(days_to_expiration),
            value=min(7, int(days_to_expiration)),
            step=1,
            key="strategy_elapsed",
            help=_SIMULATOR_TOOLKIT["scenario_days_elapsed"],
        )
        volatility_change = st.number_input(
            "IV change for scenario (vol points)",
            value=0.0,
            step=1.0,
            key="strategy_iv_shift",
            help=_SIMULATOR_TOOLKIT["iv_change_vol_points"],
        )
    with sim_col3:
        risk_free_rate = st.number_input(
            "Risk-free rate (%)",
            min_value=0.0,
            value=4.5,
            step=0.25,
            key="strategy_rate",
            help=_SIMULATOR_TOOLKIT["risk_free_rate"],
        )
        dividend_yield = st.number_input(
            "Dividend yield (%)",
            min_value=0.0,
            value=0.0,
            step=0.25,
            key="strategy_dividend",
            help=_SIMULATOR_TOOLKIT["dividend_yield"],
        )
    if simulation_mode == "Before expiration / Greeks":
        remaining_preview = max(int(days_to_expiration) - int(scenario_days_elapsed), 0)
        valuation_model = st.selectbox(
            "Valuation model",
            ["European (Black-Scholes)", "American (binomial tree)"],
            key="strategy_valuation_model",
            help=_SIMULATOR_TOOLKIT["valuation_model"],
        )
        iv_note = (
            f"Each option leg uses **{_valuation_model_label(valuation_model)}**, its **IV %** plus "
            f"**{volatility_change:+.0f}** vol points at scenario time "
            f"with **{remaining_preview}** days remaining."
        )
        st.caption(iv_note)
    else:
        valuation_model = "Expiration intrinsic value"

    fee_col1, fee_col2, fee_col3, fee_col4 = st.columns(4)
    with fee_col1:
        stock_order_commission = st.number_input("Stock commission/order ($)", min_value=0.0, value=0.0, step=0.50)
    with fee_col2:
        stock_per_share_fee = st.number_input("Stock per-share fee ($)", min_value=0.0, value=0.0, step=0.005, format="%.4f")
    with fee_col3:
        option_order_commission = st.number_input(
            "Option commission/order ($)",
            min_value=0.0,
            value=0.0,
            step=0.50,
            help=_SIMULATOR_TOOLKIT["option_order_commission"],
        )
    with fee_col4:
        option_contract_fee = st.number_input(
            "Option per-contract fee ($)",
            min_value=0.0,
            value=0.65,
            step=0.05,
            help=_SIMULATOR_TOOLKIT["option_contract_fee"],
        )

    st.markdown("**Strategy legs**")
    st.caption(
        "One row = one position. For option contracts, set **Instrument** to Call or Put, "
        "set **Action** to Buy or Sell, and set **Qty** to the number of contracts. "
        "Use **+** to add more legs. Stock rows use **Qty** as share count."
    )
    custom_share_count = int(share_lot)
    custom_call_contracts = int(contract_lot)
    custom_put_contracts = int(contract_lot)
    if preset == "Custom":
        custom_col1, custom_col2, custom_col3 = st.columns(3)
        with custom_col1:
            custom_share_count = st.number_input(
                "Custom stock shares",
                min_value=0,
                value=int(share_lot),
                step=10,
                help="Number of shares in the Stock row. Set to 0 if you do not want stock.",
            )
        with custom_col2:
            custom_call_contracts = st.number_input(
                "Custom call contracts",
                min_value=0,
                value=int(contract_lot),
                step=1,
                help="Number of call option contracts in the Custom call row.",
            )
        with custom_col3:
            custom_put_contracts = st.number_input(
                "Custom put contracts",
                min_value=0,
                value=int(contract_lot),
                step=1,
                help="Number of put option contracts in the Custom put row.",
            )
        st.caption("These yellow Custom controls seed the Qty column below. In the table, Qty means contracts for Call/Put rows.")
    default_legs = _strategy_template_legs(preset, stock_price, int(share_lot), int(contract_lot))
    if preset == "Custom":
        default_legs = [
            leg
            for leg in _strategy_template_legs(
                preset,
                stock_price,
                int(custom_share_count),
                int(max(custom_call_contracts, custom_put_contracts, 1)),
            )
            if not (
                (leg["Instrument"] == "Stock" and int(custom_share_count) == 0)
                or (leg["Instrument"] == "Call" and int(custom_call_contracts) == 0)
                or (leg["Instrument"] == "Put" and int(custom_put_contracts) == 0)
            )
        ]
        for leg in default_legs:
            if leg["Instrument"] == "Call":
                leg["Quantity"] = int(custom_call_contracts)
            elif leg["Instrument"] == "Put":
                leg["Quantity"] = int(custom_put_contracts)
    st.markdown(
        """
<div class="sip-editable-table-note">
Editable yellow strategy table: change Instrument (Stock/Call/Put), Buy / Sell, Qty,
Strike, Premium, and IV %. Use the + row control to add more stock or option legs.
</div>
""",
        unsafe_allow_html=True,
    )
    edited_legs = st.data_editor(
        pd.DataFrame(default_legs),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Instrument": st.column_config.SelectboxColumn(
                "Instrument",
                options=["Stock", "Call", "Put"],
                required=True,
                help="Choose Stock for shares, Call for call contracts, or Put for put contracts.",
            ),
            "Action": st.column_config.SelectboxColumn(
                "Buy / Sell",
                options=["Buy", "Sell"],
                required=True,
                help="Buy means long the shares/contracts. Sell means short the shares/contracts.",
            ),
            "Quantity": st.column_config.NumberColumn(
                "Qty (shares/contracts)",
                min_value=0,
                step=1,
                required=True,
                help="For Stock rows, quantity is shares. For Call or Put rows, quantity is contracts.",
            ),
            "Strike": st.column_config.NumberColumn(
                "Strike (options)",
                min_value=0.0,
                step=1.0,
                help="Option strike price. Stock rows can leave this at 0.",
            ),
            "Premium": st.column_config.NumberColumn(
                "Premium/contract share",
                min_value=0.0,
                step=0.25,
                help="Option premium per share. A 3.00 premium equals $300 per standard contract.",
            ),
            "IV %": st.column_config.NumberColumn(
                "IV % (options)",
                min_value=0.01,
                step=1.0,
                help="Implied volatility for this option leg.",
            ),
        },
        key=f"strategy_legs_{preset}_{stock_price}_{share_lot}_{contract_lot}_{simulation_mode}",
    )
    st.caption(
        "Example: to buy 2 call contracts, use Instrument = Call, Buy / Sell = Buy, "
        "Qty = 2, then enter Strike, Premium, and IV %. Net payoff sums every row in the table."
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
        "valuation_model": valuation_model,
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
                    st.session_state["education_single_option_chain_full"] = chain
                else:
                    st.session_state[f"education_{context}_chain_full"] = chain
                st.session_state[f"education_{context}_chain_reference"] = reference
                st.success(f"Loaded {contract_type.lower()} reference from {chain.attrs.get('source', 'options chain')}.")
                st.rerun()

        reference = st.session_state.get(f"education_{context}_chain_reference")
        if reference is not None and not reference.empty:
            st.caption("Nearest reference contracts from the latest loaded chain:")
            st.dataframe(reference, use_container_width=True, hide_index=True)


def _render_single_option_reference_strike_selector(
    chain: pd.DataFrame | None,
    option_type: str,
    default_strike: float,
) -> dict:
    """Render real-chain strike selector and return the matching market defaults."""
    if chain is None or chain.empty:
        return {}

    bid_col = f"{option_type} Bid"
    ask_col = f"{option_type} Ask"
    if bid_col not in chain.columns or ask_col not in chain.columns:
        return {}

    usable_chain = chain.copy()
    usable_chain = usable_chain[pd.to_numeric(usable_chain["Strike"], errors="coerce").notna()]
    usable_chain = usable_chain[
        (pd.to_numeric(usable_chain[bid_col], errors="coerce").fillna(0) > 0)
        | (pd.to_numeric(usable_chain[ask_col], errors="coerce").fillna(0) > 0)
    ]
    if usable_chain.empty:
        return {}

    strikes = sorted(float(strike) for strike in usable_chain["Strike"].dropna().unique())
    default_index = min(range(len(strikes)), key=lambda index: abs(strikes[index] - default_strike))
    selected_strike = st.selectbox(
        "Reference strike from loaded chain",
        strikes,
        index=default_index,
        format_func=lambda value: f"{value:.2f}",
        key=f"single_option_reference_strike_{option_type}",
        help="When real data is loaded, changing this strike updates premium to the bid/ask midpoint and IV to the matching contract.",
    )
    selected_defaults = _option_defaults_for_strike(usable_chain, option_type, float(selected_strike))
    if selected_defaults:
        st.caption(
            f"Using real-chain midpoint for {option_type.lower()} strike {selected_defaults['strike']:.2f}: "
            f"premium {selected_defaults['premium']:.2f}, IV {selected_defaults['implied_volatility']:.2f}%."
        )
    return selected_defaults


def _option_defaults_from_chain(chain: pd.DataFrame, option_type: str, stock_price: float) -> tuple[dict, pd.DataFrame]:
    """Return editable simulator defaults from the nearest option-chain contract."""
    frame = chain.copy()
    frame["Distance"] = (frame["Strike"] - stock_price).abs()
    reference_cols = ["Strike", "Call Bid", "Call Ask", "Put Bid", "Put Ask", "IV", "Delta"]
    reference = frame.sort_values("Distance").head(7)[[col for col in reference_cols if col in frame.columns]].copy()
    row = frame.sort_values("Distance").iloc[0]
    defaults = _option_defaults_from_chain_row(row, option_type)
    return (defaults, reference)


def _option_defaults_for_strike(chain: pd.DataFrame, option_type: str, strike: float) -> dict:
    """Return option defaults for the closest available strike in a loaded chain."""
    frame = chain.copy()
    frame["Distance"] = (frame["Strike"] - strike).abs()
    row = frame.sort_values("Distance").iloc[0]
    return _option_defaults_from_chain_row(row, option_type)


def _option_defaults_from_chain_row(row: pd.Series, option_type: str) -> dict:
    """Return premium and IV defaults from one option-chain row."""
    bid_col = f"{option_type} Bid"
    ask_col = f"{option_type} Ask"
    bid = _safe_float(row.get(bid_col), 0.0)
    ask = _safe_float(row.get(ask_col), 0.0)
    premium = (bid + ask) / 2 if bid > 0 and ask > 0 else max(bid, ask, 0.01)
    iv = _safe_float(row.get("IV"), 0.35)
    iv_percent = iv * 100 if iv <= 3 else iv
    return {
        "option_type": option_type,
        "strike": float(row["Strike"]),
        "premium": round(premium, 2),
        "implied_volatility": round(iv_percent, 2),
    }


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


def _valuation_model_label(valuation_model: str) -> str:
    """Return a short, user-facing option valuation model label."""
    return "American binomial" if valuation_model.startswith("American") else "European Black-Scholes"


def _option_model_value(
    option_type: str,
    stock_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
    valuation_model: str = "European (Black-Scholes)",
) -> float:
    """Return model-based option value, falling back to intrinsic value at expiration."""
    if days_to_expiration <= 0 or volatility <= 0:
        return max(stock_price - strike, 0) if option_type == "Call" else max(strike - stock_price, 0)
    if valuation_model.startswith("American"):
        return _american_binomial_option_value(
            option_type,
            stock_price,
            strike,
            days_to_expiration,
            volatility,
            risk_free_rate,
            dividend_yield,
        )

    t = days_to_expiration / 365
    d1, d2 = _black_scholes_d1_d2(stock_price, strike, t, volatility, risk_free_rate, dividend_yield)
    discounted_stock = stock_price * math.exp(-dividend_yield * t)
    discounted_strike = strike * math.exp(-risk_free_rate * t)
    if option_type == "Call":
        return discounted_stock * _norm_cdf(d1) - discounted_strike * _norm_cdf(d2)
    return discounted_strike * _norm_cdf(-d2) - discounted_stock * _norm_cdf(-d1)


def _american_binomial_option_value(
    option_type: str,
    stock_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
) -> float:
    """Return American option value using a Cox-Ross-Rubinstein binomial tree."""
    if days_to_expiration <= 0 or volatility <= 0:
        return max(stock_price - strike, 0) if option_type == "Call" else max(strike - stock_price, 0)

    steps = max(25, min(200, int(days_to_expiration) * 2))
    total_time = days_to_expiration / 365
    dt = total_time / steps
    up = math.exp(volatility * math.sqrt(dt))
    down = 1 / up
    discount = math.exp(-risk_free_rate * dt)
    growth = math.exp((risk_free_rate - dividend_yield) * dt)
    probability = (growth - down) / (up - down)
    probability = min(max(probability, 0.0), 1.0)

    values = []
    for node in range(steps + 1):
        node_price = stock_price * (up**node) * (down ** (steps - node))
        values.append(_option_intrinsic_value(option_type, node_price, strike))

    for step in range(steps - 1, -1, -1):
        for node in range(step + 1):
            node_price = stock_price * (up**node) * (down ** (step - node))
            continuation_value = discount * (probability * values[node + 1] + (1 - probability) * values[node])
            exercise_value = _option_intrinsic_value(option_type, node_price, strike)
            values[node] = max(continuation_value, exercise_value)

    return values[0]


def _option_intrinsic_value(option_type: str, stock_price: float, strike: float) -> float:
    """Return intrinsic value for one option share."""
    return max(stock_price - strike, 0) if option_type == "Call" else max(strike - stock_price, 0)


def _option_model_greeks(
    option_type: str,
    stock_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
    valuation_model: str = "European (Black-Scholes)",
) -> dict:
    """Return option Greeks for the selected valuation model."""
    if not valuation_model.startswith("American"):
        return _black_scholes_greeks(
            option_type,
            stock_price,
            strike,
            days_to_expiration,
            volatility,
            risk_free_rate,
            dividend_yield,
        )
    return _finite_difference_greeks(
        option_type,
        stock_price,
        strike,
        days_to_expiration,
        volatility,
        risk_free_rate,
        dividend_yield,
        valuation_model,
    )


def _finite_difference_greeks(
    option_type: str,
    stock_price: float,
    strike: float,
    days_to_expiration: int,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
    valuation_model: str,
) -> dict:
    """Estimate Greeks numerically for models without closed-form Greeks."""
    base_value = _option_model_value(
        option_type,
        stock_price,
        strike,
        days_to_expiration,
        volatility,
        risk_free_rate,
        dividend_yield,
        valuation_model,
    )
    price_step = max(stock_price * 0.01, 0.01)
    up_value = _option_model_value(
        option_type,
        stock_price + price_step,
        strike,
        days_to_expiration,
        volatility,
        risk_free_rate,
        dividend_yield,
        valuation_model,
    )
    down_value = _option_model_value(
        option_type,
        max(stock_price - price_step, 0.01),
        strike,
        days_to_expiration,
        volatility,
        risk_free_rate,
        dividend_yield,
        valuation_model,
    )
    delta = (up_value - down_value) / (2 * price_step)
    gamma = (up_value - 2 * base_value + down_value) / (price_step**2)

    vol_step = 0.01
    vega = (
        _option_model_value(
            option_type,
            stock_price,
            strike,
            days_to_expiration,
            volatility + vol_step,
            risk_free_rate,
            dividend_yield,
            valuation_model,
        )
        - _option_model_value(
            option_type,
            stock_price,
            strike,
            days_to_expiration,
            max(volatility - vol_step, 0.0001),
            risk_free_rate,
            dividend_yield,
            valuation_model,
        )
    ) / 2

    rate_step = 0.01
    rho = (
        _option_model_value(
            option_type,
            stock_price,
            strike,
            days_to_expiration,
            volatility,
            risk_free_rate + rate_step,
            dividend_yield,
            valuation_model,
        )
        - _option_model_value(
            option_type,
            stock_price,
            strike,
            days_to_expiration,
            volatility,
            risk_free_rate - rate_step,
            dividend_yield,
            valuation_model,
        )
    ) / 2

    theta = _option_model_value(
        option_type,
        stock_price,
        strike,
        max(days_to_expiration - 1, 0),
        volatility,
        risk_free_rate,
        dividend_yield,
        valuation_model,
    ) - base_value
    return {"Delta": delta, "Gamma": gamma, "Theta": theta, "Vega": vega, "Rho": rho}


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
        greeks = _option_model_greeks(
            leg["Instrument"],
            stock_price,
            float(leg["Strike"]),
            int(model_inputs.get("days_to_expiration", 30)),
            max(float(leg.get("IV %", 35.0)) / 100, 0.0001),
            float(model_inputs.get("risk_free_rate", 0.0)),
            float(model_inputs.get("dividend_yield", 0.0)),
            str(model_inputs.get("valuation_model", "European (Black-Scholes)")),
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

**Delta:** Shows how much the option price is expected to change for a 1 dollar move in the stock, before contract size. A call with delta `+0.50` should gain about 0.50 per share if the stock rises 1 dollar. Since one contract usually controls 100 shares, that is about 50 dollars per contract. Put deltas are usually negative, so they generally gain when the stock falls. Delta is not fixed; it changes as price, time, and IV change.

**Gamma:** Shows how quickly delta changes when the stock moves. High gamma means the option's directional exposure can change fast. This can help option buyers when the stock moves strongly in their favor, because delta accelerates. It can hurt short-option sellers because losses can speed up as the stock moves against them. Gamma is usually highest for at-the-money options near expiration.

**Theta:** Estimates daily time decay, all else equal. Long options usually have negative theta because time passing removes extrinsic value. Short options usually have positive theta because the seller benefits as time value decays. Theta is not a guaranteed daily amount; it changes with price, IV, and time remaining, and it often accelerates close to expiration.

**Vega:** Shows how much the option value changes for a 1 volatility-point move in implied volatility. Example: if vega is `0.08`, a move from 35% IV to 36% IV adds roughly 0.08 per share, or about 8 dollars per contract. Long options usually benefit when IV rises and lose when IV falls. Short options usually benefit when IV falls but can lose when IV spikes.

**Rho:** Shows sensitivity to a 1 percentage-point move in interest rates. It is usually less important than delta, gamma, theta, or vega for short-dated stock options. It can matter more for long-dated options, high-rate environments, or strategies with many contracts.

**Implied volatility (IV):** The market's embedded expectation of future movement. Higher IV usually makes both calls and puts more expensive because the market is pricing a wider range of possible outcomes. A trader can be right on direction and still lose if IV drops enough after entry, especially after earnings or other scheduled events.

**Valuation model:** European Black-Scholes assumes the option can only be exercised at expiration. American binomial allows early exercise before expiration. U.S. listed equity options are usually American-style, so the American model can be useful for dividend stocks, deep in-the-money puts, short calls near ex-dividend dates, and contracts with very little extrinsic value. The model is still an estimate, not a broker quote.

**IV change (vol points):** Adds or subtracts percentage points from the base IV for the scenario. This is not a relative percentage change. Example: 35% IV plus 5 vol points becomes 40% IV. Use positive values such as +5 or +10 to test a volatility spike. Use negative values such as -5 or -10 to test IV crush after earnings or another event. Set it to 0 if you want the scenario to keep IV unchanged.

**Days to expiration:** The total time left until the contract expires. More time usually means more extrinsic value because the stock has more opportunity to move. Less time usually means less extrinsic value and more sensitivity to whether the option is in, at, or out of the money.

**Simulate after days elapsed:** Moves the scenario forward in time before calculating the payoff. Example: if days to expiration is 30 and days elapsed is 7, the scenario is priced with 23 days left. This lets you test the combined effect of stock movement, time decay, and IV change before expiration.

**Entry premium:** The price paid or received per option share when entering the trade. Since one standard contract controls 100 shares, a 3.00 premium equals 300 dollars per contract before commissions. Buyers pay the premium; sellers receive it but take on obligation risk.

**Strike:** The price where the option begins to have intrinsic value at expiration. A call has intrinsic value when the stock is above the strike. A put has intrinsic value when the stock is below the strike. The distance between stock price and strike affects delta, premium, and probability of finishing in the money.

**Break-even:** The approximate stock price at expiration where the option trade starts to make money before commissions. For a bought call, break-even is strike plus premium. For a bought put, break-even is strike minus premium. Before expiration, break-even is less exact because IV and time value still affect the option price.

**Commissions:** Broker commissions and per-contract fees reduce every strategy's net P&L. They matter more for multi-leg spreads, butterflies, and small premium trades.
"""
    )


def _format_money_or_text(value: object) -> str:
    """Format numeric money values while preserving text descriptions."""
    return f"\\${float(value):,.2f}" if isinstance(value, (int, float)) else str(value)


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
            _option_leg("Call", "Buy", contracts, at_the_money, stock_price * 0.04),
            _option_leg("Put", "Buy", contracts, at_the_money, stock_price * 0.04),
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
            str(model_inputs.get("valuation_model", "European (Black-Scholes)")),
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
    st.caption(f"Estimated net opening cash flow: **\\${net_opening_cash_flow:,.2f}**")
    st.caption(f"Estimated round-trip commissions included in payoff: **\\${round_trip_commission:,.2f}**")
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
        help=_SIMULATOR_TOOLKIT["price_move_scenario"],
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
