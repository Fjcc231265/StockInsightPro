"""Interactive Plotly visuals for Education lesson library."""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from utils.constants import COLORS

# Lesson id -> list of visual keys to render (in order).
LESSON_VISUALS: dict[str, list[str]] = {
    "market-mindset": ["market_drivers"],
    "support-resistance": ["support_resistance"],
    "candlestick-patterns": ["candlestick_context"],
    "volume-and-gaps": ["volume_bars"],
    "trend-and-timeframes": ["trend_moving_averages"],
    "market-internals": ["market_internals"],
    "calls-and-puts": ["long_call_payoff", "long_put_payoff"],
    "expiration-calendar": ["theta_decay"],
    "option-quotes": ["bid_ask_spread"],
    "open-interest-volume": ["volume_vs_oi"],
    "order-types-options": ["order_types", "bid_ask_spread"],
    "american-european": ["american_european"],
    "intrinsic-time-value": ["intrinsic_time_value"],
    "iv-and-premium": ["iv_premium_effect"],
    "greeks-overview": ["greeks_sensitivity"],
    "itm-atm-otm-selection": ["delta_by_strike"],
    "rates-dividends": ["rates_dividend_effect"],
    "regime-overview": ["regime_matrix"],
    "volatility-regimes": ["vix_regimes"],
    "iv-classification": ["iv_scale"],
    "regime-decision-map": ["regime_decision_flow"],
    "stock-vs-call": ["stock_vs_call"],
    "protective-put": ["protective_put"],
    "covered-call": ["covered_call"],
    "cash-secured-put": ["cash_secured_put"],
    "vertical-credit-spreads": ["credit_spread"],
    "iron-condor": ["iron_condor"],
    "straddle-strangle": ["long_straddle"],
    "collar": ["collar"],
    "diagonal-calls": ["diagonal_concept"],
    "stock-call-spread": ["bull_call_spread"],
    "rolling-covered-calls": ["roll_covered_call"],
    "close-spread-winners": ["credit_spread_profit_zone"],
    "money-management-basics": ["position_sizing"],
    "margin-awareness": ["margin_comparison"],
    "pre-trade-questions": ["regime_decision_flow"],
    "diagonal-management": ["diagonal_concept"],
    "leaps-short-call": ["leaps_short_call"],
}

# Strategy playbook entry id -> visual keys (usually one payoff chart).
STRATEGY_PLAYBOOK_VISUALS: dict[str, list[str]] = {
    "bullish-long-call": ["long_call_payoff"],
    "bullish-bull-call-spread": ["bull_call_spread"],
    "bullish-covered-call": ["covered_call"],
    "bullish-csp": ["cash_secured_put"],
    "bearish-long-put": ["long_put_payoff"],
    "bearish-bear-put-spread": ["bear_put_spread"],
    "neutral-iron-condor": ["iron_condor"],
    "vol-long-straddle": ["long_straddle"],
    "hedge-protective-put": ["protective_put"],
    "hedge-collar": ["collar"],
}


def render_visual_keys(
    visual_keys: list[str],
    *,
    heading: str | None = "**Interactive concept charts**",
    show_dividers: bool = True,
) -> None:
    """Render a list of registered visual keys."""
    if not visual_keys:
        return
    if heading:
        st.markdown(heading)
    for index, key in enumerate(visual_keys):
        renderer = _VISUAL_RENDERERS.get(key)
        if not renderer:
            continue
        caption = _VISUAL_CAPTIONS.get(key)
        if caption:
            st.caption(caption)
        renderer()
        if show_dividers and index < len(visual_keys) - 1:
            st.divider()


def render_lesson_visuals(lesson_id: str) -> None:
    """Render all configured visuals for a lesson."""
    render_visual_keys(LESSON_VISUALS.get(lesson_id, []))


def render_strategy_playbook_visuals(strategy_id: str) -> None:
    """Render payoff diagram for a strategy playbook entry."""
    render_visual_keys(
        STRATEGY_PLAYBOOK_VISUALS.get(strategy_id, []),
        heading="**Payoff diagram (illustrative)**",
        show_dividers=False,
    )


_VISUAL_CAPTIONS: dict[str, str] = {
    "long_call_payoff": "Long call payoff at expiration: profit rises when the stock finishes above strike + premium.",
    "long_put_payoff": "Long put payoff at expiration: profit rises when the stock finishes below strike − premium.",
    "support_resistance": "Support and resistance are zones where price has repeatedly reacted, not single exact prices.",
    "candlestick_context": "Candle bodies and wicks show who controlled the session; location on the chart matters more than the pattern name alone.",
    "volume_bars": "Volume confirms whether a move had participation from buyers or sellers.",
    "trend_moving_averages": "Higher-time-frame trend (line) with a faster moving average for timing context.",
    "market_internals": "Illustrative market-internal signals: breadth, volatility, and risk appetite.",
    "theta_decay": "Time value usually decays faster as expiration approaches (especially near the money).",
    "bid_ask_spread": "You typically buy near the ask and sell near the bid; the spread is a real trading cost.",
    "volume_vs_oi": "Day volume is today's activity; open interest is contracts still outstanding.",
    "intrinsic_time_value": "Premium = intrinsic value + time value. At expiration, only intrinsic value remains.",
    "iv_premium_effect": "Higher implied volatility generally increases option premium, all else equal.",
    "greeks_sensitivity": "Illustrative Greek exposures for a long at-the-money option (not exact for every trade).",
    "delta_by_strike": "Delta rises as the call moves in the money; puts become more negative in the money.",
    "rates_dividend_effect": "Higher rates tend to help calls slightly; dividends tend to help puts slightly.",
    "regime_matrix": "Match the market environment before choosing a structure.",
    "vix_regimes": "VIX direction is a practical thermometer for risk appetite.",
    "iv_scale": "Judge IV relative to the symbol's own history, not in isolation.",
    "regime_decision_flow": "Decision flow: regime → IV → structure → risk check.",
    "stock_vs_call": "Stock has linear P&L; a long call has capped loss (premium) and leveraged upside.",
    "protective_put": "Stock plus long put: floor below the put strike (minus premium paid).",
    "covered_call": "Long stock plus short call: income from premium, upside capped at the call strike.",
    "cash_secured_put": "Short put: profit if stock stays above strike; assignment risk if stock falls far below.",
    "credit_spread": "Vertical credit spread: max gain = credit received; max loss = width − credit.",
    "iron_condor": "Iron condor: profits when price stays between the short strikes at expiration.",
    "long_straddle": "Long straddle: needs a large move in either direction to overcome double premium.",
    "collar": "Collar: long stock, long put (floor), short call (ceiling).",
    "diagonal_concept": "Diagonal: long dated call + short nearer call to harvest time decay.",
    "bull_call_spread": "Bull call spread: cheaper than a naked call; upside capped at short strike.",
    "roll_covered_call": "Rolling the short call up/out can recover upside when the stock rallies.",
    "credit_spread_profit_zone": "Many traders close credit spreads before expiration after capturing most of max profit.",
    "margin_comparison": "Defined-risk spreads usually use less buying power than naked short options.",
    "bear_put_spread": "Bear put spread: defined-risk bearish trade with profit capped at spread width minus debit.",
    "market_drivers": "Conceptual chart only—the bar heights are not real measured percentages. They show that several forces can influence price at once.",
    "american_european": "American options can be exercised early; European options only at expiration.",
    "order_types": "Limit orders control price; market orders prioritize speed over price.",
    "position_sizing": "Risk per trade as a small fraction of account limits ruin from a string of losses.",
    "leaps_short_call": "LEAPS hold time value longer; short calls against them harvest nearer-term decay.",
}


_VISUAL_RENDERERS: dict[str, object] = {}


def _register(name: str):
    def decorator(func):
        _VISUAL_RENDERERS[name] = func
        return func

    return decorator


def _chart_layout(title: str, x_title: str, y_title: str, height: int = 320, **overrides) -> dict:
    layout = dict(
        title=dict(text=title, font=dict(size=14)),
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    layout.update(overrides)
    return layout


def _price_range(center: float, width: float = 0.3, steps: int = 80) -> list[float]:
    start = center * (1 - width)
    stop = center * (1 + width)
    step = (stop - start) / steps
    return [round(start + step * i, 2) for i in range(steps + 1)]


@_register("long_call_payoff")
def _long_call_payoff() -> None:
    spot, strike, premium = 100.0, 105.0, 4.0
    prices = _price_range(spot, 0.25)
    pnl = [max(price - strike, 0) - premium for price in prices]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=pnl, mode="lines", name="P&L", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash", line_color="#888")
    fig.add_vline(x=strike + premium, line_dash="dot", annotation_text="Break-even", line_color=COLORS["accent"])
    fig.update_layout(**_chart_layout("Long call @ expiration", "Stock price", "P&L per share"))
    st.plotly_chart(fig, use_container_width=True)


@_register("long_put_payoff")
def _long_put_payoff() -> None:
    spot, strike, premium = 100.0, 95.0, 3.5
    prices = _price_range(spot, 0.25)
    pnl = [max(strike - price, 0) - premium for price in prices]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=pnl, mode="lines", name="P&L", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash", line_color="#888")
    fig.add_vline(x=strike - premium, line_dash="dot", annotation_text="Break-even", line_color=COLORS["accent"])
    fig.update_layout(**_chart_layout("Long put @ expiration", "Stock price", "P&L per share"))
    st.plotly_chart(fig, use_container_width=True)


@_register("support_resistance")
def _support_resistance() -> None:
    days = list(range(30))
    prices = [100 + 2 * math.sin(i / 3) + (i % 7) * 0.15 for i in days]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=prices, mode="lines", name="Price", line=dict(color=COLORS["secondary"])))
    fig.add_hrect(y0=103, y1=106, fillcolor=COLORS["negative"], opacity=0.15, line_width=0)
    fig.add_hrect(y0=97, y1=99, fillcolor=COLORS["positive"], opacity=0.15, line_width=0)
    fig.add_annotation(x=28, y=104.5, text="Resistance zone", showarrow=False, font=dict(color=COLORS["negative"]))
    fig.add_annotation(x=28, y=98, text="Support zone", showarrow=False, font=dict(color=COLORS["positive"]))
    fig.update_layout(**_chart_layout("Support & resistance zones", "Time", "Price"))
    st.plotly_chart(fig, use_container_width=True)


@_register("candlestick_context")
def _candlestick_context() -> None:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=["Mon", "Tue", "Wed", "Thu", "Fri"],
                open=[100, 102, 101, 104, 103],
                high=[103, 104, 103, 108, 105],
                low=[99, 100, 99, 102, 100],
                close=[102, 101, 103, 105, 101],
            )
        ]
    )
    fig.update_layout(**_chart_layout("Candlestick context (illustrative week)", "Session", "Price"))
    st.plotly_chart(fig, use_container_width=True)


@_register("volume_bars")
def _volume_bars() -> None:
    days = ["D1", "D2", "D3", "D4", "D5"]
    up_vol = [1.2, 0.8, 1.5, 0.9, 1.1]
    down_vol = [0.9, 1.3, 0.7, 1.4, 0.8]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=days, y=up_vol, name="Up day volume", marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(x=days, y=down_vol, name="Down day volume", marker_color=COLORS["negative"]))
    fig.update_layout(**_chart_layout("Volume on up vs down days", "Day", "Relative volume"), barmode="group")
    st.plotly_chart(fig, use_container_width=True)


@_register("trend_moving_averages")
def _trend_moving_averages() -> None:
    days = list(range(60))
    price = [100 + i * 0.08 + math.sin(i / 5) for i in days]
    ma_fast = [sum(price[max(0, i - 4) : i + 1]) / min(i + 1, 5) for i in days]
    ma_slow = [sum(price[max(0, i - 19) : i + 1]) / min(i + 1, 20) for i in days]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=price, mode="lines", name="Price", line=dict(color="#bbb")))
    fig.add_trace(go.Scatter(x=days, y=ma_fast, mode="lines", name="Fast MA", line=dict(color=COLORS["accent"])))
    fig.add_trace(go.Scatter(x=days, y=ma_slow, mode="lines", name="Slow MA", line=dict(color=COLORS["secondary"], width=3)))
    fig.update_layout(**_chart_layout("Trend with moving averages", "Bars", "Price"))
    st.plotly_chart(fig, use_container_width=True)


@_register("market_internals")
def _market_internals() -> None:
    signals = ["VIX ↓", "Breadth +", "Growth leads", "Credit stable"]
    scores = [1, 0.8, 0.7, 0.6]
    colors = [COLORS["positive"], COLORS["positive"], COLORS["accent"], COLORS["secondary"]]
    fig = go.Figure(go.Bar(x=scores, y=signals, orientation="h", marker_color=colors))
    fig.update_layout(**_chart_layout("Risk-on checklist (illustrative)", "Strength", "Signal"))
    st.plotly_chart(fig, use_container_width=True)


@_register("theta_decay")
def _theta_decay() -> None:
    days = list(range(45, -1, -1))
    value = [max(4.0 * math.sqrt(d / 45), 0.05) for d in days]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=value, mode="lines", fill="tozeroy", name="Time value", line=dict(color=COLORS["accent"])))
    fig.update_layout(**_chart_layout("Time value decay (illustrative)", "Days to expiration", "Extrinsic value"))
    st.plotly_chart(fig, use_container_width=True)


@_register("bid_ask_spread")
def _bid_ask_spread() -> None:
    levels = ["Bid", "Mid", "Ask"]
    prices = [2.10, 2.20, 2.30]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=prices, y=levels, orientation="h", marker_color=[COLORS["positive"], COLORS["accent"], COLORS["negative"]]))
    fig.update_layout(**_chart_layout("Option quote ladder", "Premium ($)", "", height=220))
    st.plotly_chart(fig, use_container_width=True)


@_register("volume_vs_oi")
def _volume_vs_oi() -> None:
    strikes = ["95", "100", "105", "110"]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Day volume", x=strikes, y=[1200, 5400, 3200, 900], marker_color=COLORS["secondary"]))
    fig.add_trace(go.Bar(name="Open interest", x=strikes, y=[8000, 15000, 11000, 4000], marker_color=COLORS["accent"]))
    fig.update_layout(**_chart_layout("Volume vs open interest by strike", "Strike", "Contracts"), barmode="group")
    st.plotly_chart(fig, use_container_width=True)


@_register("intrinsic_time_value")
def _intrinsic_time_value() -> None:
    spots = ["OTM", "ATM", "ITM"]
    intrinsic = [0, 0, 8]
    time_val = [3.5, 4.0, 1.2]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Intrinsic", x=spots, y=intrinsic, marker_color=COLORS["secondary"]))
    fig.add_trace(go.Bar(name="Time value", x=spots, y=time_val, marker_color=COLORS["accent"]))
    fig.update_layout(**_chart_layout("Premium components (call example, strike 100)", "Moneyness", "$ per share"), barmode="stack")
    st.plotly_chart(fig, use_container_width=True)


@_register("iv_premium_effect")
def _iv_premium_effect() -> None:
    iv = [20, 30, 40, 50, 60]
    premium = [2.1, 2.8, 3.6, 4.5, 5.4]
    fig = go.Figure(go.Scatter(x=iv, y=premium, mode="lines+markers", line=dict(color=COLORS["secondary"], width=3)))
    fig.update_layout(**_chart_layout("IV vs option premium (illustrative ATM call)", "Implied volatility (%)", "Premium ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("greeks_sensitivity")
def _greeks_sensitivity() -> None:
    greeks = ["Delta", "Gamma", "Theta/day", "Vega"]
    values = [0.52, 0.08, -0.05, 0.12]
    fig = go.Figure(go.Bar(x=greeks, y=values, marker_color=[COLORS["positive"], COLORS["accent"], COLORS["negative"], COLORS["secondary"]]))
    fig.update_layout(**_chart_layout("Illustrative Greeks (long ATM call)", "Greek", "Per-unit sensitivity"))
    st.plotly_chart(fig, use_container_width=True)


@_register("delta_by_strike")
def _delta_by_strike() -> None:
    strikes = list(range(85, 116, 2))
    call_delta = [max(0, min(1, (s - 90) / 20)) for s in strikes]
    put_delta = [-max(0, min(1, (110 - s) / 20)) for s in strikes]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=strikes, y=call_delta, mode="lines", name="Call delta", line=dict(color=COLORS["positive"])))
    fig.add_trace(go.Scatter(x=strikes, y=put_delta, mode="lines", name="Put delta", line=dict(color=COLORS["negative"])))
    fig.add_vline(x=100, line_dash="dash", line_color="#aaa", annotation_text="Spot")
    fig.update_layout(**_chart_layout("Delta vs strike (illustrative)", "Strike", "Delta"))
    st.plotly_chart(fig, use_container_width=True)


@_register("rates_dividend_effect")
def _rates_dividend_effect() -> None:
    scenarios = ["Base", "Rates +1%", "Dividend +1%"]
    call_prem = [4.0, 4.2, 3.8]
    put_prem = [3.5, 3.3, 3.7]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Call", x=scenarios, y=call_prem, marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(name="Put", x=scenarios, y=put_prem, marker_color=COLORS["negative"]))
    fig.update_layout(**_chart_layout("Rates & dividends (illustrative)", "Scenario", "Premium"), barmode="group")
    st.plotly_chart(fig, use_container_width=True)


@_register("regime_matrix")
def _regime_matrix() -> None:
    regimes = ["Risk-on", "Neutral", "Risk-off"]
    favor = ["Calls / stock", "Credit spreads / condors", "Cash / puts / collars"]
    fig = go.Figure(go.Table(
        header=dict(values=["Regime", "Often favors"], fill_color=COLORS["secondary"], font=dict(color="white")),
        cells=dict(values=[regimes, favor], fill_color=["#f8f9fb", "#fff9df"]),
    ))
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)


@_register("vix_regimes")
def _vix_regimes() -> None:
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=18, fillcolor=COLORS["positive"], opacity=0.2, line_width=0)
    fig.add_hrect(y0=18, y1=25, fillcolor=COLORS["accent"], opacity=0.2, line_width=0)
    fig.add_hrect(y0=25, y1=40, fillcolor=COLORS["negative"], opacity=0.2, line_width=0)
    fig.add_trace(go.Scatter(x=[0, 1], y=[16, 28], mode="lines+markers", name="VIX path", line=dict(color=COLORS["secondary"], width=3)))
    fig.update_layout(**_chart_layout("VIX zones (illustrative)", "Time →", "VIX level"), yaxis=dict(range=[10, 35]))
    fig.add_annotation(x=0.5, y=16, text="Risk-on", showarrow=False)
    fig.add_annotation(x=0.5, y=22, text="Neutral", showarrow=False)
    fig.add_annotation(x=0.5, y=30, text="Risk-off", showarrow=False)
    st.plotly_chart(fig, use_container_width=True)


@_register("iv_scale")
def _iv_scale() -> None:
    labels = ["Low IV", "Medium IV", "High IV", "Extreme IV"]
    fig = go.Figure(go.Bar(x=labels, y=[1, 2, 3, 4], marker_color=[COLORS["positive"], COLORS["accent"], COLORS["negative"], "#8b0000"]))
    fig.update_layout(**_chart_layout("Relative IV buckets (judge vs symbol history)", "Bucket", "Relative level", height=280))
    st.plotly_chart(fig, use_container_width=True)


@_register("regime_decision_flow")
def _regime_decision_flow() -> None:
    fig = go.Figure()
    nodes = {
        "start": (0.5, 1),
        "regime": (0.5, 0.75),
        "iv": (0.5, 0.5),
        "structure": (0.5, 0.25),
    }
    labels = list(nodes.keys())
    xs = [nodes[k][0] for k in labels]
    ys = [nodes[k][1] for k in labels]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=["Regime?", "IV cheap/expensive?", "Pick structure", "Max loss OK?"], textposition="top center", marker=dict(size=40, color=COLORS["secondary"])))
    fig.add_annotation(x=0.5, y=1.05, text="Start with context", showarrow=False, font=dict(size=14))
    for y in [0.75, 0.5, 0.25]:
        fig.add_shape(type="line", x0=0.5, y0=y + 0.08, x1=0.5, y1=y + 0.17, line=dict(color="#888"))
    fig.update_layout(
        **_chart_layout(
            "Pre-trade decision flow",
            "",
            "",
            height=300,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
    )
    st.plotly_chart(fig, use_container_width=True)


@_register("stock_vs_call")
def _stock_vs_call() -> None:
    move = [-20, -10, 0, 10, 20]
    stock_pnl = [m * 10 for m in move]
    call_pnl = [max(m * 10, -5) if m > 5 else -5 for m in move]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=move, y=stock_pnl, mode="lines", name="100 shares", line=dict(color=COLORS["secondary"])))
    fig.add_trace(go.Scatter(x=move, y=call_pnl, mode="lines", name="1 call ($5 premium)", line=dict(color=COLORS["accent"])))
    fig.add_hline(y=0, line_dash="dash", line_color="#888")
    fig.update_layout(**_chart_layout("% move vs P&L (illustrative)", "Stock % change", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("protective_put")
def _protective_put() -> None:
    spot, strike, premium_stock, put_prem = 100.0, 95.0, 100.0, 3.0
    prices = _price_range(spot, 0.2)
    stock = [(p - premium_stock) * 100 for p in prices]
    put_only = [(max(strike - p, 0) - put_prem) * 100 for p in prices]
    combined = [s + p for s, p in zip(stock, put_only)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=stock, mode="lines", name="Stock only"))
    fig.add_trace(go.Scatter(x=prices, y=combined, mode="lines", name="Stock + put", line=dict(width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(**_chart_layout("Protective put @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("covered_call")
def _covered_call() -> None:
    spot, strike, prem = 100.0, 105.0, 4.0
    prices = _price_range(spot, 0.2)
    stock = [(p - spot) * 100 for p in prices]
    combined = [s + min(strike - p, 0) * 100 + prem * 100 for s, p in zip(stock, prices)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=stock, mode="lines", name="Stock only"))
    fig.add_trace(go.Scatter(x=prices, y=combined, mode="lines", name="Covered call", line=dict(width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(**_chart_layout("Covered call @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("cash_secured_put")
def _cash_secured_put() -> None:
    strike, credit = 95.0, 2.5
    prices = _price_range(100, 0.25)
    pnl = [credit * 100 if p >= strike else credit * 100 - (strike - p) * 100 for p in prices]
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.add_vline(x=strike, line_dash="dot", annotation_text="Strike")
    fig.update_layout(**_chart_layout("Short put @ expiration (per contract)", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("credit_spread")
def _credit_spread() -> None:
    strike_short, strike_long, credit = 100.0, 95.0, 2.0
    prices = _price_range(100, 0.2)
    width = strike_short - strike_long
    pnl = []
    for p in prices:
        if p >= strike_short:
            val = credit
        elif p <= strike_long:
            val = credit - width
        else:
            val = credit - (strike_short - p)
        pnl.append(val * 100)
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", fill="tozeroy", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(**_chart_layout("Bull put credit spread @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


_VISUAL_RENDERERS["credit_spread_profit_zone"] = _VISUAL_RENDERERS["credit_spread"]


@_register("iron_condor")
def _iron_condor() -> None:
    prices = _price_range(100, 0.22)
    put_long, put_short, call_short, call_long, credit = 90, 95, 105, 110, 2.0
    put_width = put_short - put_long
    call_width = call_long - call_short
    pnl = []
    for p in prices:
        if p <= put_long:
            val = credit - put_width
        elif p < put_short:
            val = credit - (put_short - p)
        elif p <= call_short:
            val = credit
        elif p < call_long:
            val = credit - (p - call_short)
        else:
            val = credit - call_width
        pnl.append(val * 100)
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", fill="tozeroy", line=dict(color=COLORS["accent"], width=3)))
    fig.add_vrect(x0=put_short, x1=call_short, fillcolor=COLORS["positive"], opacity=0.12, line_width=0)
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(**_chart_layout("Iron condor @ expiration (illustrative)", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("long_straddle")
def _long_straddle() -> None:
    strike, prem = 100.0, 6.0
    prices = _price_range(strike, 0.3)
    pnl = [(max(p - strike, 0) + max(strike - p, 0) - prem) * 100 for p in prices]
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.add_vline(x=strike, line_dash="dot")
    fig.update_layout(**_chart_layout("Long straddle @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("collar")
def _collar() -> None:
    spot, put_k, call_k, put_p, call_c = 100.0, 95.0, 105.0, 2.0, 2.5
    prices = _price_range(spot, 0.2)
    pnl = []
    for p in prices:
        stock = (p - spot) * 100
        put_leg = (max(put_k - p, 0) - put_p) * 100
        call_leg = (min(call_k - p, 0) + call_c) * 100
        pnl.append(stock + put_leg + call_leg)
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", fill="tozeroy", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(**_chart_layout("Collar @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("diagonal_concept")
def _diagonal_concept() -> None:
    days = list(range(0, 91, 15))
    long_val = [4.5 - d * 0.01 for d in days]
    short_vals = [2.0, 1.2, 0.5, 0.1, 0.0, 0.0, 0.0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=long_val, mode="lines", name="Long call (90 DTE)", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=days[:4], y=short_vals[:4], mode="lines+markers", name="Short call (30 DTE cycles)", line=dict(color=COLORS["accent"])))
    fig.update_layout(**_chart_layout("Diagonal: long option + repeated short calls", "Days", "Illustrative value"))
    st.plotly_chart(fig, use_container_width=True)


@_register("bull_call_spread")
def _bull_call_spread() -> None:
    long_k, short_k, debit = 100.0, 110.0, 4.0
    prices = _price_range(105, 0.25)
    pnl = []
    for p in prices:
        val = max(p - long_k, 0) - max(p - short_k, 0) - debit
        pnl.append(val * 100)
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", fill="tozeroy", line=dict(color=COLORS["positive"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(**_chart_layout("Bull call spread @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("roll_covered_call")
def _roll_covered_call() -> None:
    scenarios = ["No roll", "Roll up", "Roll out"]
    upside = [1400, 1600, 1500]
    fig = go.Figure(go.Bar(x=scenarios, y=upside, marker_color=[COLORS["negative"], COLORS["positive"], COLORS["accent"]]))
    fig.update_layout(**_chart_layout("Illustrative outcome when stock rallies past strike", "Management", "P&L if assigned/rolled", height=280))
    st.plotly_chart(fig, use_container_width=True)


@_register("margin_comparison")
def _margin_comparison() -> None:
    structures = ["Naked short call", "Diagonal", "Defined spread"]
    margin = [100, 35, 15]
    fig = go.Figure(go.Bar(x=structures, y=margin, marker_color=[COLORS["negative"], COLORS["accent"], COLORS["positive"]]))
    fig.update_layout(**_chart_layout("Relative margin usage (illustrative index)", "Structure", "Margin index", height=280))
    st.plotly_chart(fig, use_container_width=True)


@_register("bear_put_spread")
def _bear_put_spread() -> None:
    long_k, short_k, debit = 105.0, 95.0, 4.0
    width = long_k - short_k
    prices = _price_range(100, 0.25)
    pnl = []
    for p in prices:
        val = max(long_k - p, 0) - max(short_k - p, 0) - debit
        pnl.append(val * 100)
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", fill="tozeroy", line=dict(color=COLORS["negative"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.add_annotation(x=short_k, y=(width - debit) * 100, text="Max profit", showarrow=False)
    fig.update_layout(**_chart_layout("Bear put spread @ expiration", "Stock price", "P&L ($)"))
    st.plotly_chart(fig, use_container_width=True)


@_register("market_drivers")
def _market_drivers() -> None:
    drivers = ["Macro backdrop", "Earnings / news", "Sector rotation", "Order flow", "Positioning"]
    # Illustrative scores only (0–1 scale), not empirical market data.
    illustrative_scores = [0.7, 0.85, 0.75, 0.9, 0.8]
    fig = go.Figure(go.Bar(x=drivers, y=illustrative_scores, marker_color=COLORS["secondary"]))
    fig.update_layout(
        **_chart_layout(
            "What influences price (conceptual)",
            "Driver",
            "Illustrative influence score (not real data)",
            height=320,
            showlegend=False,
        )
    )
    st.plotly_chart(fig, use_container_width=True)


@_register("american_european")
def _american_european() -> None:
    fig = go.Figure(go.Table(
        header=dict(values=["Feature", "American", "European"], fill_color=COLORS["secondary"], font=dict(color="white")),
        cells=dict(
            values=[
                ["Exercise", "Pricing model", "Typical listing"],
                ["Any time before expiry", "Often binomial / early exercise", "Most U.S. equity options"],
                ["Expiration only", "Often closed-form", "Some index options"],
            ],
            fill_color=[["#f4f6f9"] * 3, ["#fff"] * 3, ["#fff9df"] * 3],
        ),
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)


@_register("order_types")
def _order_types() -> None:
    types = ["Market", "Limit", "Stop", "Stop-limit"]
    price_control = [1, 4, 3, 4]
    fill_speed = [4, 2, 3, 2]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Price control", x=types, y=price_control, marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(name="Fill speed", x=types, y=fill_speed, marker_color=COLORS["accent"]))
    fig.update_layout(**_chart_layout("Order type trade-offs (illustrative)", "Order type", "Score (higher = better)", height=300, barmode="group"))
    st.plotly_chart(fig, use_container_width=True)


@_register("position_sizing")
def _position_sizing() -> None:
    risk_pct = [0.5, 1, 2, 5]
    max_losses_to_halve = [138, 69, 35, 14]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=risk_pct, y=max_losses_to_halve, mode="lines+markers", line=dict(color=COLORS["secondary"], width=3)))
    fig.update_layout(**_chart_layout("Losses to cut account ~50% (illustrative)", "Risk per trade (%)", "Consecutive losses"))
    st.plotly_chart(fig, use_container_width=True)


@_register("leaps_short_call")
def _leaps_short_call() -> None:
    days = list(range(0, 366, 30))
    leaps = [12 - d * 0.02 for d in days]
    short_cycle = [2.5 if d % 90 < 30 else 0.8 for d in days]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=leaps, mode="lines", name="LEAPS time value", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=days, y=short_cycle, mode="lines", name="Short call premium cycles", line=dict(color=COLORS["accent"])))
    fig.update_layout(**_chart_layout("LEAPS + short call (illustrative)", "Days", "Option value ($)"))
    st.plotly_chart(fig, use_container_width=True)
