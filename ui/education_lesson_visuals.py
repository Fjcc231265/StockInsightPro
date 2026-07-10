"""Interactive Plotly visuals for Education lesson library."""

from __future__ import annotations

import csv
import math
import re
import urllib.request
from contextvars import ContextVar
from html.parser import HTMLParser
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from services.market_data_service import get_price_history
from services.technical_data_service import get_support_resistance
from services.trading_tutor_service import format_decision_flow_live_context
from utils.constants import COLORS

_LONG_TERM_MARKET_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "us_gdp_sp500_long_term.csv"
_LONG_TERM_MARKET_DATA_SOURCE_NOTE = (
    "Cached local dataset. GDP source: BEA/FRED annual real GDP. "
    "Equity source: NYU Stern/Damodaran annual S&P 500 total-return history."
)

_visual_key_prefix: ContextVar[str] = ContextVar("visual_key_prefix", default="")
_chart_part_counter: ContextVar[int] = ContextVar("chart_part_counter", default=0)
_tutor_report_context: ContextVar[dict | None] = ContextVar("tutor_report_context", default=None)


def _plotly_chart(fig, *, part: str | None = None) -> None:
    """Render Plotly with a stable unique key when the same visual appears on one page."""
    prefix = _visual_key_prefix.get()
    if part is None:
        counter = _chart_part_counter.get()
        part = f"chart_{counter}"
        _chart_part_counter.set(counter + 1)
    key = f"{prefix}_{part}" if prefix else part
    st.plotly_chart(fig, use_container_width=True, key=key)

# Lesson id -> list of visual keys to render (in order).
LESSON_VISUALS: dict[str, list[str]] = {
    "market-mindset": ["market_drivers", "long_term_market_gdp"],
    "support-resistance": ["support_resistance"],
    "candlestick-patterns": ["candle_anatomy", "candlestick_context"],
    "volume-and-gaps": ["volume_bars"],
    "trend-and-timeframes": ["trend_moving_averages"],
    "market-internals": ["market_internals", "vix_explainer", "tick_explainer", "trin_explainer"],
    "calls-and-puts": ["long_call_payoff", "long_put_payoff"],
    "greeks-basics": ["greeks_sensitivity", "delta_by_strike", "theta_decay"],
    "option-quotes": ["option_chain_example", "bid_ask_spread"],
    "open-interest-volume": ["volume_vs_oi"],
    "order-types-options": ["order_action_examples", "order_types", "bid_ask_spread"],
    "american-european": ["american_european"],
    "intrinsic-time-value": ["intrinsic_time_value"],
    "iv-and-premium": ["iv_premium_effect"],
    "itm-atm-otm-selection": ["strike_selection_matrix", "delta_by_strike"],
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
    key_prefix: str = "",
    tutor_report: dict | None = None,
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
        prefix = f"{key_prefix}_{key}" if key_prefix else key
        prefix_token = _visual_key_prefix.set(prefix)
        counter_token = _chart_part_counter.set(0)
        report_token = _tutor_report_context.set(tutor_report)
        try:
            renderer()
        finally:
            _visual_key_prefix.reset(prefix_token)
            _chart_part_counter.reset(counter_token)
            _tutor_report_context.reset(report_token)
        if show_dividers and index < len(visual_keys) - 1:
            st.divider()


def render_lesson_visuals(lesson_id: str) -> None:
    """Render all configured visuals for a lesson."""
    render_visual_keys(LESSON_VISUALS.get(lesson_id, []), key_prefix=lesson_id)


def render_strategy_playbook_visuals(strategy_id: str) -> None:
    """Render payoff diagram for a strategy playbook entry."""
    render_visual_keys(
        STRATEGY_PLAYBOOK_VISUALS.get(strategy_id, []),
        heading="**Payoff diagram (illustrative)**",
        show_dividers=False,
        key_prefix=f"strategy_{strategy_id}",
    )


_VISUAL_CAPTIONS: dict[str, str] = {
    "long_call_payoff": "Long call payoff at expiration: profit rises when the stock finishes above strike + premium.",
    "long_put_payoff": "Long put payoff at expiration: profit rises when the stock finishes below strike − premium.",
    "support_resistance": "Daily candlestick view for the selected ticker. Support and resistance are treated as zones around recent highs, lows, closes, and pivots—not exact prices.",
    "candle_anatomy": "A single candle summarizes one period of trading: open, high, low, close, body, and wicks.",
    "candlestick_context": "Candle bodies and wicks show who controlled the session; location on the chart matters more than the pattern name alone.",
    "volume_bars": "Volume confirms whether a move had participation from buyers or sellers.",
    "trend_moving_averages": "Higher-time-frame trend (line) with a faster moving average for timing context.",
    "market_internals": "Illustrative market-internal signals: breadth, volatility, and risk appetite.",
    "vix_explainer": "VIX is an options-implied volatility gauge for the S&P 500; rising VIX often means protection demand is increasing.",
    "tick_explainer": "TICK is an intraday pressure gauge: NYSE stocks ticking up minus stocks ticking down.",
    "trin_explainer": "TRIN compares breadth with volume to show whether advancing or declining stocks have stronger volume confirmation.",
    "theta_decay": "Time value usually decays faster as expiration approaches (especially near the money).",
    "option_chain_example": "Illustrative option chain around a $100 stock. Use it to compare strike, moneyness, bid/ask, mark, volume, and open interest.",
    "bid_ask_spread": "You typically buy near the ask and sell near the bid; the spread is a real trading cost.",
    "volume_vs_oi": "Day volume is today's activity; open interest is contracts still outstanding.",
    "intrinsic_time_value": "Premium = intrinsic value + time value. At expiration, only intrinsic value remains.",
    "iv_premium_effect": "Higher implied volatility generally increases option premium, all else equal.",
    "greeks_sensitivity": "Illustrative Greek exposures for a long at-the-money option (not exact for every trade).",
    "strike_selection_matrix": "Strike selection matrix: match ITM, ATM, or OTM to purpose, probability, cost, and risk.",
    "delta_by_strike": "Delta rises as the call moves in the money; puts become more negative in the money.",
    "rates_dividend_effect": "Higher rates tend to help calls slightly; dividends tend to help puts slightly.",
    "regime_matrix": "Match the market environment before choosing a structure.",
    "vix_regimes": "VIX direction is a practical thermometer for risk appetite.",
    "iv_scale": "Judge IV relative to the symbol's own history, not in isolation.",
    "regime_decision_flow": "Five-step pre-trade workflow with regime, IV, structure, and risk definitions below the chart.",
    "stock_vs_call": "Stock has linear P&L; a long call has capped loss (premium) and leveraged upside.",
    "protective_put": "Stock plus long put: floor below the put strike (minus premium paid).",
    "covered_call": "Long stock plus short call: income from premium, upside capped at the call strike.",
    "cash_secured_put": "Short put: profit if stock stays above strike; assignment risk if stock falls far below.",
    "credit_spread": "Bear call spread: max gain = credit received; max loss = width − credit.",
    "iron_condor": "Iron condor: profits when price stays between the short strikes at expiration.",
    "long_straddle": "Long straddle: needs a large move in either direction to overcome double premium.",
    "collar": "Collar: long stock, long put (floor), short call (ceiling).",
    "diagonal_concept": "Diagonal: long dated call + short nearer call to harvest time decay.",
    "bull_call_spread": "Bull call spread: cheaper than a naked call; upside capped at short strike.",
    "roll_covered_call": "Rolling the short call up/out can recover upside when the stock rallies.",
    "credit_spread_profit_zone": "Many traders close bull put spreads and bear call spreads before expiration after capturing most of max profit.",
    "margin_comparison": "Defined-risk spreads usually use less buying power than naked short options.",
    "bear_put_spread": "Bear put spread: defined-risk bearish trade with profit capped at spread width minus debit.",
    "market_drivers": "Conceptual chart only—the bar heights are not real measured percentages. They show that several forces can influence price at once.",
    "long_term_market_gdp": "Long-run indexed view: markets are volatile and forward-looking, while GDP reflects the slower compounding of the economy over time.",
    "american_european": "American options can be exercised early; European options only at expiration.",
    "order_action_examples": "Examples of correct option order language for opening and closing long options, short options, and spreads.",
    "order_types": "Limit orders control price; market orders prioritize speed over price.",
    "position_sizing": "Position sizing asks: if this trade loses, how much of my account is at risk? Small risk per trade helps the account survive inevitable losing streaks.",
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
    breakeven = strike + premium
    prices = _price_range(spot, 0.25)
    pnl = [max(price - strike, 0) - premium for price in prices]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=prices,
            y=pnl,
            mode="lines",
            name="Long call P&L",
            line=dict(color=COLORS["secondary"], width=3),
            hovertemplate="Stock price: $%{x:.2f}<br>P&L/share: $%{y:.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#888")
    fig.add_hline(y=-premium, line_dash="dot", line_color=COLORS["negative"])
    fig.add_vline(x=strike, line_dash="dash", annotation_text="Strike", line_color="#64748b")
    fig.add_vline(x=breakeven, line_dash="dot", annotation_text="Break-even", line_color=COLORS["accent"])
    fig.update_layout(
        **_chart_layout(
            "Long call at expiration: bullish, defined-risk payoff",
            "Stock price at expiration",
            "P&L per share",
            showlegend=False,
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Below the strike:** the call expires worthless, so the loss is limited to the premium paid "
        f"(\\${premium:.2f} per share, or \\${premium * 100:.0f} per contract).\n"
        f"- **Break-even:** stock price must finish above \\${breakeven:.2f} "
        f"(strike \\${strike:.2f} + premium \\${premium:.2f}).\n"
        "- **Above break-even:** profit grows dollar-for-dollar with the stock because the right to buy at the strike becomes valuable."
    )


@_register("long_put_payoff")
def _long_put_payoff() -> None:
    spot, strike, premium = 100.0, 95.0, 3.5
    breakeven = strike - premium
    prices = _price_range(spot, 0.25)
    pnl = [max(strike - price, 0) - premium for price in prices]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=prices,
            y=pnl,
            mode="lines",
            name="Long put P&L",
            line=dict(color=COLORS["secondary"], width=3),
            hovertemplate="Stock price: $%{x:.2f}<br>P&L/share: $%{y:.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#888")
    fig.add_hline(y=-premium, line_dash="dot", line_color=COLORS["negative"])
    fig.add_vline(x=strike, line_dash="dash", annotation_text="Strike", line_color="#64748b")
    fig.add_vline(x=breakeven, line_dash="dot", annotation_text="Break-even", line_color=COLORS["accent"])
    fig.update_layout(
        **_chart_layout(
            "Long put at expiration: bearish or protective payoff",
            "Stock price at expiration",
            "P&L per share",
            showlegend=False,
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Above the strike:** the put expires worthless, so the loss is limited to the premium paid "
        f"(\\${premium:.2f} per share, or \\${premium * 100:.0f} per contract).\n"
        f"- **Break-even:** stock price must finish below \\${breakeven:.2f} "
        f"(strike \\${strike:.2f} - premium \\${premium:.2f}).\n"
        "- **Below break-even:** profit grows as the stock falls because the right to sell at the strike becomes valuable."
    )


@_register("support_resistance")
def _support_resistance() -> None:
    ticker = str(st.session_state.get("selected_ticker", "AAPL")).upper()
    prices = get_price_history(ticker, days=120, timeframe="Daily").sort_values("Date").reset_index(drop=True)
    levels = get_support_resistance(ticker)
    if prices.empty:
        st.info(f"No daily price history is available for {ticker}.")
        return

    prices = prices.tail(90).copy()
    prices["MA20"] = prices["Close"].rolling(20).mean()
    prices["MA50"] = prices["Close"].rolling(50).mean()
    volume_colors = [
        COLORS["positive"] if close_price >= open_price else COLORS["negative"]
        for open_price, close_price in zip(prices["Open"], prices["Close"])
    ]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )
    fig.add_trace(
        go.Candlestick(
            x=prices["Date"],
            open=prices["Open"],
            high=prices["High"],
            low=prices["Low"],
            close=prices["Close"],
            name=ticker,
            increasing_line_color=COLORS["positive"],
            decreasing_line_color=COLORS["negative"],
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=prices["Date"], y=prices["MA20"], mode="lines", name="20D MA", line=dict(color=COLORS["accent"], width=1.7)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=prices["Date"], y=prices["MA50"], mode="lines", name="50D MA", line=dict(color=COLORS["secondary"], width=1.7)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(x=prices["Date"], y=prices["Volume"], name="Volume", marker_color=volume_colors, opacity=0.35),
        row=2,
        col=1,
    )

    avg_range = float((prices["High"] - prices["Low"]).tail(20).mean())
    latest_close = float(prices["Close"].iloc[-1])
    zone_half_width = max(avg_range * 0.25, latest_close * 0.004)
    for _, level in levels.iterrows():
        price = float(level["Price"])
        level_type = str(level["Level Type"])
        if level_type == "Support":
            color = COLORS["positive"]
        elif level_type == "Resistance":
            color = COLORS["negative"]
        else:
            color = COLORS["accent"]
        fig.add_hrect(
            y0=price - zone_half_width,
            y1=price + zone_half_width,
            fillcolor=color,
            opacity=0.12,
            line_width=0,
            row=1,
            col=1,
        )

    fig.update_layout(
        **_chart_layout(
            f"{ticker} daily support/resistance zones",
            "",
            "Price",
            height=620,
            xaxis_rangeslider_visible=False,
            showlegend=True,
            margin=dict(l=55, r=30, t=90, b=45),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        )
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    st.caption(f"Chart source: {prices.attrs.get('source', 'Price history')} · Levels source: {levels.attrs.get('source', 'Price history')}")
    _plotly_chart(fig)
    if not levels.empty:
        display_levels = levels.copy()
        display_levels["Price"] = display_levels["Price"].map(lambda price: f"${float(price):,.2f}")
        st.dataframe(display_levels, use_container_width=True, hide_index=True)


@_register("candle_anatomy")
def _candle_anatomy() -> None:
    col1, col2 = st.columns(2)
    with col1:
        _plotly_chart(
            _single_candle_anatomy_figure(
                title="Bullish candle",
                open_price=100,
                close_price=108,
                high_price=113,
                low_price=96,
                color=COLORS["positive"],
                border_color="#0b5130",
                note="Close > Open",
            ),
            part="bullish",
        )
    with col2:
        _plotly_chart(
            _single_candle_anatomy_figure(
                title="Bearish candle",
                open_price=108,
                close_price=100,
                high_price=113,
                low_price=96,
                color=COLORS["negative"],
                border_color="#7f1d1d",
                note="Close < Open",
            ),
            part="bearish",
        )


def _single_candle_anatomy_figure(
    *,
    title: str,
    open_price: float,
    close_price: float,
    high_price: float,
    low_price: float,
    color: str,
    border_color: str,
    note: str,
) -> go.Figure:
    x_center = 0
    body_half_width = 0.18
    body_low = min(open_price, close_price)
    body_high = max(open_price, close_price)

    fig = go.Figure()
    fig.add_shape(
        type="line",
        x0=x_center,
        x1=x_center,
        y0=low_price,
        y1=high_price,
        line=dict(color=color, width=4),
    )
    fig.add_shape(
        type="rect",
        x0=x_center - body_half_width,
        x1=x_center + body_half_width,
        y0=body_low,
        y1=body_high,
        fillcolor=color,
        opacity=0.82,
        line=dict(color=border_color, width=2),
    )

    annotations = [
        ("High", high_price, "Highest price"),
        ("Open", open_price, "Start"),
        ("Close", close_price, "End"),
        ("Low", low_price, "Lowest price"),
    ]
    for label, price, detail in annotations:
        fig.add_annotation(
            x=x_center + 0.58,
            y=price,
            text=f"<b>{label}</b><br>{detail}",
            showarrow=True,
            arrowhead=2,
            ax=30,
            ay=0,
            font=dict(size=11, color="#123"),
            align="left",
        )

    fig.add_annotation(
        x=x_center - 0.52,
        y=(body_low + body_high) / 2,
        text="<b>Body</b><br>Open-close range",
        showarrow=True,
        arrowhead=2,
        ax=-35,
        ay=0,
        font=dict(size=11, color="#123"),
        align="center",
    )
    fig.add_annotation(
        x=x_center - 0.45,
        y=(body_high + high_price) / 2,
        text="Upper wick",
        showarrow=False,
        font=dict(size=10, color=COLORS["neutral"]),
    )
    fig.add_annotation(
        x=x_center - 0.45,
        y=(low_price + body_low) / 2,
        text="Lower wick",
        showarrow=False,
        font=dict(size=10, color=COLORS["neutral"]),
    )
    fig.add_annotation(
        x=x_center,
        y=92.5,
        text=f"<b>{note}</b>",
        showarrow=False,
        font=dict(size=12, color=color),
    )
    fig.update_layout(
        **_chart_layout(
            title,
            "",
            "Price",
            height=430,
            showlegend=False,
            margin=dict(l=40, r=120, t=55, b=45),
            xaxis=dict(range=[-0.95, 1.25], visible=False),
            yaxis=dict(range=[91, 115]),
        )
    )
    return fig


@_register("candlestick_context")
def _candlestick_context() -> None:
    sessions = [f"D{i}" for i in range(1, 11)]
    open_prices = [105, 106, 104, 101, 99, 98, 100, 103, 106, 109]
    high_prices = [107, 107, 105, 102, 101, 101, 104, 107, 110, 111]
    low_prices = [103, 103, 100, 98, 96, 95, 99, 102, 105, 106]
    close_prices = [106, 104, 101, 99, 98, 100, 103, 106, 109, 107]

    fig = go.Figure()
    fig.add_hrect(
        y0=96,
        y1=99,
        fillcolor=COLORS["positive"],
        opacity=0.12,
        line_width=0,
    )
    fig.add_hrect(
        y0=108,
        y1=111,
        fillcolor=COLORS["negative"],
        opacity=0.12,
        line_width=0,
    )
    fig.add_trace(
        go.Candlestick(
            x=sessions,
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            name="Price candles",
            increasing=dict(line=dict(color=COLORS["positive"], width=2), fillcolor=COLORS["positive"]),
            decreasing=dict(line=dict(color=COLORS["negative"], width=2), fillcolor=COLORS["negative"]),
        )
    )

    annotations = [
        ("Support zone", "D2", 97.5, COLORS["positive"], -75, -45),
        ("Long lower wick:<br>buyers defend support", "D6", 95.2, COLORS["positive"], -85, 70),
        ("Wide bullish candle:<br>buyers take control", "D7", 104.3, COLORS["positive"], 85, -70),
        ("Resistance zone", "D9", 109.5, COLORS["negative"], -80, -55),
        ("Upper wick:<br>sellers reject higher prices", "D10", 110.8, COLORS["negative"], 95, 85),
    ]
    for text, x_value, y_value, color, ax, ay in annotations:
        fig.add_annotation(
            x=x_value,
            y=y_value,
            text=text,
            showarrow=True,
            arrowhead=2,
            ax=ax,
            ay=ay,
            font=dict(size=11, color=color),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=color,
            borderwidth=1,
        )

    fig.update_layout(
        **_chart_layout(
            "Candlestick context: location matters",
            "Session",
            "Price",
            height=520,
            showlegend=False,
            margin=dict(l=50, r=30, t=70, b=55),
            xaxis_rangeslider_visible=False,
        )
    )
    st.caption(
        "This example shows why a candle should be read with location: the same wick or body means more near support, resistance, or a recent change in control."
    )
    _plotly_chart(fig)


@_register("volume_bars")
def _volume_bars() -> None:
    sessions = [f"D{i}" for i in range(1, 13)]
    closes = [100, 101, 102, 102.5, 103, 104, 108, 111, 110, 112, 111, 107]
    opens = [99.5, 100.5, 101.5, 102.2, 102.7, 103.3, 104.2, 108.5, 111.2, 110.5, 112.2, 111.0]
    volume = [0.8, 0.9, 0.75, 0.7, 0.85, 0.95, 2.8, 2.4, 1.1, 0.9, 1.0, 2.6]
    avg_volume = 1.0
    volume_colors = [
        COLORS["positive"] if close_price >= open_price else COLORS["negative"]
        for open_price, close_price in zip(opens, closes)
    ]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.38],
        vertical_spacing=0.06,
        subplot_titles=("Price reaction", "Volume confirms or questions the move"),
    )
    fig.add_trace(
        go.Scatter(
            x=sessions,
            y=closes,
            mode="lines+markers",
            name="Close",
            line=dict(color=COLORS["secondary"], width=3),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=sessions,
            y=volume,
            name="Relative volume",
            marker_color=volume_colors,
            opacity=0.72,
        ),
        row=2,
        col=1,
    )
    fig.add_hline(
        y=avg_volume,
        line_dash="dash",
        line_color=COLORS["neutral"],
        annotation_text="Average volume",
        annotation_position="top left",
        row=2,
        col=1,
    )

    callouts = [
        ("Low-volume drift:<br>move has less conviction", "D4", 102.5, COLORS["neutral"], -45, -45, 1),
        ("Breakout on high volume:<br>institutions may be participating", "D7", 108, COLORS["positive"], 85, -45, 1),
        ("Heavy down volume:<br>selling pressure matters", "D12", 2.6, COLORS["negative"], -95, -55, 2),
    ]
    for text, x_value, y_value, color, ax, ay, row in callouts:
        fig.add_annotation(
            x=x_value,
            y=y_value,
            text=text,
            showarrow=True,
            arrowhead=2,
            ax=ax,
            ay=ay,
            font=dict(size=11, color=color),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=color,
            borderwidth=1,
            row=row,
            col=1,
        )

    fig.update_layout(
        **_chart_layout(
            "Volume: participation behind price movement",
            "Session",
            "",
            height=540,
            showlegend=False,
            margin=dict(l=55, r=35, t=85, b=55),
        )
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Relative volume", row=2, col=1)
    st.caption(
        "Volume is context for price. A breakout on above-average volume carries more weight than a quiet drift; heavy volume against the move can warn of distribution."
    )
    _plotly_chart(fig)


@_register("trend_moving_averages")
def _trend_moving_averages() -> None:
    ticker = str(st.session_state.get("selected_ticker", "AAPL")).upper()
    prices = get_price_history(ticker, days=260, timeframe="Daily").sort_values("Date").reset_index(drop=True)
    if prices.empty:
        st.info(f"No daily price history is available for {ticker}.")
        return

    prices["MA20"] = prices["Close"].rolling(20).mean()
    prices["MA50"] = prices["Close"].rolling(50).mean()
    prices["MA200"] = prices["Close"].rolling(200).mean()
    visible_prices = prices.tail(180).copy()
    volume_colors = [
        COLORS["positive"] if close_price >= open_price else COLORS["negative"]
        for open_price, close_price in zip(visible_prices["Open"], visible_prices["Close"])
    ]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )
    fig.add_trace(
        go.Candlestick(
            x=visible_prices["Date"],
            open=visible_prices["Open"],
            high=visible_prices["High"],
            low=visible_prices["Low"],
            close=visible_prices["Close"],
            name=ticker,
            increasing_line_color=COLORS["positive"],
            decreasing_line_color=COLORS["negative"],
        ),
        row=1,
        col=1,
    )
    moving_averages = [
        ("20D MA", "MA20", COLORS["accent"], 1.8),
        ("50D MA", "MA50", COLORS["secondary"], 2.1),
        ("200D MA", "MA200", COLORS["neutral"], 2.2),
    ]
    for label, column, color, width in moving_averages:
        if visible_prices[column].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=visible_prices["Date"],
                    y=visible_prices[column],
                    mode="lines",
                    name=label,
                    line=dict(color=color, width=width),
                    hovertemplate=f"{label}: %{{y:,.2f}}<extra></extra>",
                ),
                row=1,
                col=1,
            )
    fig.add_trace(
        go.Bar(
            x=visible_prices["Date"],
            y=visible_prices["Volume"],
            name="Volume",
            marker_color=volume_colors,
            opacity=0.35,
        ),
        row=2,
        col=1,
    )

    latest = prices.iloc[-1]
    trend_note = _moving_average_trend_note(latest)
    fig.update_layout(
        **_chart_layout(
            f"{ticker} daily trend with moving averages",
            "",
            "Price",
            height=620,
            xaxis_rangeslider_visible=False,
            margin=dict(l=55, r=30, t=90, b=45),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        )
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    st.caption(
        f"Chart source: {prices.attrs.get('source', 'Price history')} · "
        "Moving averages are dynamic trend reference lines, not automatic buy/sell signals."
    )
    st.info(trend_note)
    _plotly_chart(fig)


def _moving_average_trend_note(latest_price_row) -> str:
    """Return a concise educational interpretation of the latest moving-average stack."""
    close = float(latest_price_row["Close"])
    ma20 = latest_price_row.get("MA20")
    ma50 = latest_price_row.get("MA50")
    ma200 = latest_price_row.get("MA200")
    available = [value for value in [ma20, ma50, ma200] if value == value]
    if len(available) < 2:
        return "Trend note: not enough history yet to compare the major moving averages."

    above_20 = ma20 == ma20 and close >= float(ma20)
    above_50 = ma50 == ma50 and close >= float(ma50)
    above_200 = ma200 == ma200 and close >= float(ma200)
    if above_20 and above_50 and above_200:
        return "Trend note: price is above the 20D, 50D, and 200D averages, which is usually a constructive trend structure."
    if not above_20 and not above_50 and not above_200:
        return "Trend note: price is below the 20D, 50D, and 200D averages, which is usually a cautious or bearish trend structure."
    return "Trend note: price is mixed versus the moving averages, suggesting a transition or sideways phase rather than a clean trend."


@_register("market_internals")
def _market_internals() -> None:
    signals = [
        "Volatility",
        "Market breadth",
        "Sector leadership",
        "Credit conditions",
        "Volume confirmation",
    ]
    risk_on_scores = [0.85, 0.78, 0.72, 0.68, 0.63]
    explanations = [
        "VIX falling or stable: investors demand less protection.",
        "More stocks advancing than declining: participation is broad.",
        "Growth/cyclical sectors leading: capital is seeking risk.",
        "Credit spreads stable: stress is not spreading through debt markets.",
        "Breakouts on stronger volume: institutions may be participating.",
    ]
    colors = [COLORS["positive"], COLORS["positive"], COLORS["secondary"], COLORS["accent"], COLORS["neutral"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=risk_on_scores,
            y=signals,
            orientation="h",
            marker_color=colors,
            text=[f"{score:.0%}" for score in risk_on_scores],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="<b>%{y}</b><br>Risk-on alignment: %{x:.0%}<extra></extra>",
        )
    )
    for signal, score, explanation in zip(signals, risk_on_scores, explanations):
        fig.add_annotation(
            x=min(score + 0.03, 0.98),
            y=signal,
            text=explanation,
            showarrow=False,
            xanchor="left",
            align="left",
            font=dict(size=11, color=COLORS["neutral"]),
        )
    fig.add_vrect(x0=0, x1=0.33, fillcolor=COLORS["negative"], opacity=0.06, line_width=0)
    fig.add_vrect(x0=0.33, x1=0.66, fillcolor=COLORS["accent"], opacity=0.08, line_width=0)
    fig.add_vrect(x0=0.66, x1=1.0, fillcolor=COLORS["positive"], opacity=0.06, line_width=0)
    fig.update_layout(
        **_chart_layout(
            "Market internals: risk-on checklist",
            "Alignment with risk-on conditions",
            "",
            height=420,
            showlegend=False,
            margin=dict(l=135, r=320, t=70, b=50),
            xaxis=dict(range=[0, 1.05], tickformat=".0%"),
        )
    )
    st.caption(
        "These are context clues, not trade signals by themselves. A stronger market backdrop usually combines falling volatility, broad participation, leadership from risk-seeking sectors, stable credit, and volume confirmation."
    )
    _plotly_chart(fig)


@_register("vix_explainer")
def _vix_explainer() -> None:
    days = list(range(1, 16))
    vix = [15.2, 15.8, 16.4, 17.1, 19.3, 22.6, 25.8, 28.4, 24.7, 22.1, 20.2, 18.4, 17.2, 16.6, 16.0]
    fig = go.Figure()
    fig.add_hrect(y0=10, y1=18, fillcolor=COLORS["positive"], opacity=0.12, line_width=0)
    fig.add_hrect(y0=18, y1=25, fillcolor=COLORS["accent"], opacity=0.14, line_width=0)
    fig.add_hrect(y0=25, y1=35, fillcolor=COLORS["negative"], opacity=0.12, line_width=0)
    fig.add_trace(
        go.Scatter(
            x=days,
            y=vix,
            mode="lines+markers",
            name="VIX",
            line=dict(color=COLORS["secondary"], width=3),
            hovertemplate="Day %{x}<br>VIX: %{y:.1f}<extra></extra>",
        )
    )
    fig.add_annotation(x=3, y=14.5, text="Calmer risk backdrop", showarrow=False, font=dict(size=11))
    fig.add_annotation(x=8, y=29.5, text="Protection demand rises", showarrow=True, arrowhead=2, ax=-40, ay=-30)
    fig.add_annotation(x=13, y=18.5, text="Volatility cools", showarrow=True, arrowhead=2, ax=35, ay=-35)
    fig.update_layout(
        **_chart_layout(
            "VIX: expected volatility and protection demand",
            "Illustrative trading days",
            "VIX level",
            height=360,
            showlegend=False,
            yaxis=dict(range=[10, 35]),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Low or falling VIX:** traders are demanding less index protection, which often supports risk-on behavior.\n"
        "- **Rising VIX:** option premiums usually expand and equity breakouts can become less reliable.\n"
        "- **Use with price:** VIX rising while indexes hold flat can be an early warning that uncertainty is building."
    )


@_register("tick_explainer")
def _tick_explainer() -> None:
    times = ["9:35", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "1:00", "1:30", "2:00", "2:30", "3:00"]
    tick_values = [220, 680, 940, 420, -180, -760, -980, -510, 130, 610, 880, 520]
    bar_colors = [
        COLORS["positive"] if value >= 600 else COLORS["negative"] if value <= -600 else COLORS["accent"]
        for value in tick_values
    ]
    fig = go.Figure()
    fig.add_hrect(y0=600, y1=1200, fillcolor=COLORS["positive"], opacity=0.10, line_width=0)
    fig.add_hrect(y0=-1200, y1=-600, fillcolor=COLORS["negative"], opacity=0.10, line_width=0)
    fig.add_trace(
        go.Bar(
            x=times,
            y=tick_values,
            marker_color=bar_colors,
            name="TICK",
            hovertemplate="%{x}<br>TICK: %{y:+.0f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"])
    fig.add_hline(y=800, line_dash="dot", line_color=COLORS["positive"])
    fig.add_hline(y=-800, line_dash="dot", line_color=COLORS["negative"])
    fig.add_annotation(x="10:30", y=1030, text="Broad buying pressure", showarrow=True, arrowhead=2, ax=30, ay=-35)
    fig.add_annotation(x="12:30", y=-1080, text="Broad selling pressure", showarrow=True, arrowhead=2, ax=45, ay=35)
    fig.update_layout(
        **_chart_layout(
            "TICK: intraday upticks minus downticks",
            "Intraday time",
            "NYSE TICK",
            height=360,
            showlegend=False,
            yaxis=dict(range=[-1200, 1200]),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Positive TICK:** more stocks are trading on upticks than downticks at that moment.\n"
        "- **Negative TICK:** selling pressure is broader across the tape.\n"
        "- **Repeated extremes matter more than one print:** several readings above +800 or below -800 can confirm intraday participation."
    )


@_register("trin_explainer")
def _trin_explainer() -> None:
    scenarios = ["Bullish volume", "Balanced", "Bearish volume"]
    trin_values = [0.68, 1.00, 1.62]
    colors = [COLORS["positive"], COLORS["accent"], COLORS["negative"]]
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=0.8, fillcolor=COLORS["positive"], opacity=0.12, line_width=0)
    fig.add_hrect(y0=0.8, y1=1.2, fillcolor=COLORS["accent"], opacity=0.14, line_width=0)
    fig.add_hrect(y0=1.2, y1=2.0, fillcolor=COLORS["negative"], opacity=0.12, line_width=0)
    fig.add_trace(
        go.Bar(
            x=scenarios,
            y=trin_values,
            marker_color=colors,
            text=[f"{value:.2f}" for value in trin_values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>TRIN: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color=COLORS["neutral"])
    fig.update_layout(
        **_chart_layout(
            "TRIN: breadth confirmed by volume",
            "Scenario",
            "TRIN level",
            height=360,
            showlegend=False,
            yaxis=dict(range=[0, 1.9]),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Formula:** TRIN = (advancing stocks / declining stocks) divided by (advancing volume / declining volume).\n"
        "- **Below 1.00:** advancing stocks have stronger volume confirmation, often a healthier risk-on sign.\n"
        "- **Above 1.00:** declining stocks have heavier volume confirmation, often a risk-off warning.\n"
        "- **Important:** very low or very high TRIN can become stretched intraday, so use it with trend, VIX, and TICK."
    )


@_register("theta_decay")
def _theta_decay() -> None:
    days = list(range(45, -1, -1))
    value = [max(4.0 * math.sqrt(d / 45), 0.05) for d in days]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=days,
            y=value,
            mode="lines",
            fill="tozeroy",
            name="Time value",
            line=dict(color=COLORS["accent"], width=3),
            hovertemplate="Days left: %{x}<br>Extrinsic value: $%{y:.2f}<extra></extra>",
        )
    )
    fig.add_annotation(
        x=7,
        y=1.2,
        text="Decay accelerates<br>near expiration",
        showarrow=True,
        arrowhead=2,
        ax=-80,
        ay=-45,
        font=dict(size=11, color=COLORS["neutral"]),
    )
    fig.update_layout(
        **_chart_layout(
            "Theta: time value decay before expiration",
            "Days to expiration",
            "Extrinsic value ($ per share)",
            showlegend=False,
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **More days left:** the option still has time value because the stock has room to move.\n"
        "- **Near expiration:** time value can disappear quickly, especially for at-the-money options.\n"
        "- **Long options:** usually lose from theta each day unless price movement or IV offsets it."
    )


@_register("bid_ask_spread")
def _bid_ask_spread() -> None:
    levels = ["Bid", "Mid", "Ask"]
    prices = [2.10, 2.20, 2.30]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=prices, y=levels, orientation="h", marker_color=[COLORS["positive"], COLORS["accent"], COLORS["negative"]]))
    fig.update_layout(**_chart_layout("Option quote ladder", "Premium ($)", "", height=220))
    _plotly_chart(fig)


@_register("option_chain_example")
def _option_chain_example() -> None:
    stock_price = 100
    rows = [
        {
            "strike": 95,
            "call_bid": 6.20,
            "call_ask": 6.55,
            "call_vol": 430,
            "call_oi": 4200,
            "put_bid": 1.10,
            "put_ask": 1.25,
            "put_vol": 180,
            "put_oi": 3100,
        },
        {
            "strike": 100,
            "call_bid": 3.10,
            "call_ask": 3.30,
            "call_vol": 1800,
            "call_oi": 12500,
            "put_bid": 3.00,
            "put_ask": 3.25,
            "put_vol": 1650,
            "put_oi": 11800,
        },
        {
            "strike": 105,
            "call_bid": 1.45,
            "call_ask": 1.70,
            "call_vol": 920,
            "call_oi": 7600,
            "put_bid": 6.05,
            "put_ask": 6.40,
            "put_vol": 310,
            "put_oi": 5400,
        },
    ]
    strikes = [row["strike"] for row in rows]
    call_mark = [(row["call_bid"] + row["call_ask"]) / 2 for row in rows]
    put_mark = [(row["put_bid"] + row["put_ask"]) / 2 for row in rows]
    call_moneyness = ["ITM" if strike < stock_price else "ATM" if strike == stock_price else "OTM" for strike in strikes]
    put_moneyness = ["OTM" if strike < stock_price else "ATM" if strike == stock_price else "ITM" for strike in strikes]

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[0.9, 0.8, 0.8, 0.8, 0.9, 0.8, 0.9, 0.8, 0.8, 0.8, 0.9, 0.8],
                header=dict(
                    values=[
                        "<b>Call bid</b>",
                        "<b>Call ask</b>",
                        "<b>Call mark</b>",
                        "<b>Call vol</b>",
                        "<b>Call OI</b>",
                        "<b>Call</b>",
                        "<b>Strike</b>",
                        "<b>Put</b>",
                        "<b>Put bid</b>",
                        "<b>Put ask</b>",
                        "<b>Put mark</b>",
                        "<b>Put vol/OI</b>",
                    ],
                    fill_color=COLORS["secondary"],
                    font=dict(color="white", size=12),
                    align="center",
                ),
                cells=dict(
                    values=[
                        [f"${row['call_bid']:.2f}" for row in rows],
                        [f"${row['call_ask']:.2f}" for row in rows],
                        [f"${value:.2f}" for value in call_mark],
                        [f"{row['call_vol']:,}" for row in rows],
                        [f"{row['call_oi']:,}" for row in rows],
                        call_moneyness,
                        [f"${strike}" for strike in strikes],
                        put_moneyness,
                        [f"${row['put_bid']:.2f}" for row in rows],
                        [f"${row['put_ask']:.2f}" for row in rows],
                        [f"${value:.2f}" for value in put_mark],
                        [f"{row['put_vol']:,} / {row['put_oi']:,}" for row in rows],
                    ],
                    fill_color=[
                        ["#ecfdf5", "#ecfdf5", "#ecfdf5"],
                        ["#ecfdf5", "#ecfdf5", "#ecfdf5"],
                        ["#ecfdf5", "#ecfdf5", "#ecfdf5"],
                        ["#ecfdf5", "#ecfdf5", "#ecfdf5"],
                        ["#ecfdf5", "#ecfdf5", "#ecfdf5"],
                        ["#dcfce7", "#fef3c7", "#f8fafc"],
                        ["#e0f2fe", "#fef3c7", "#e0f2fe"],
                        ["#f8fafc", "#fef3c7", "#dcfce7"],
                        ["#fef2f2", "#fef2f2", "#fef2f2"],
                        ["#fef2f2", "#fef2f2", "#fef2f2"],
                        ["#fef2f2", "#fef2f2", "#fef2f2"],
                        ["#fef2f2", "#fef2f2", "#fef2f2"],
                    ],
                    align="center",
                    height=30,
                    font=dict(size=12),
                ),
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Example option chain: stock near $100", font=dict(size=14)),
        height=260,
        margin=dict(l=10, r=10, t=45, b=10),
        template="plotly_white",
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Start at the stock price:** the \\$100 strike is at the money because the stock is near \\$100.\n"
        "- **Compare calls and puts by strike:** lower-strike calls are in the money, while higher-strike puts are in the money.\n"
        "- **Check tradability:** tighter bid/ask spreads, stronger volume, and higher open interest usually make entries and exits cleaner.\n"
        "- **Convert premium to dollars:** a \\$3.20 mark represents about \\$320 per contract before commissions and fees."
    )


@_register("volume_vs_oi")
def _volume_vs_oi() -> None:
    strikes = ["95", "100", "105", "110"]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Day volume", x=strikes, y=[1200, 5400, 3200, 900], marker_color=COLORS["secondary"]))
    fig.add_trace(go.Bar(name="Open interest", x=strikes, y=[8000, 15000, 11000, 4000], marker_color=COLORS["accent"]))
    fig.update_layout(**_chart_layout("Volume vs open interest by strike", "Strike", "Contracts"), barmode="group")
    _plotly_chart(fig)


@_register("intrinsic_time_value")
def _intrinsic_time_value() -> None:
    spots = ["OTM", "ATM", "ITM"]
    intrinsic = [0, 0, 8]
    time_val = [3.5, 4.0, 1.2]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Intrinsic", x=spots, y=intrinsic, marker_color=COLORS["secondary"]))
    fig.add_trace(go.Bar(name="Time value", x=spots, y=time_val, marker_color=COLORS["accent"]))
    fig.update_layout(
        **_chart_layout(
            "Premium components",
            "Moneyness",
            "$ per share",
            height=360,
            barmode="stack",
            margin=dict(l=55, r=25, t=70, b=85),
            legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **OTM:** the option has no intrinsic value yet. The premium is entirely time value, so it can disappear if the stock does not move enough.\n"
        "- **ATM:** the stock is near the strike. Intrinsic value is small or zero, but time value is often high because the option is sensitive to the next move.\n"
        "- **ITM:** part of the premium is already intrinsic value. The remaining time value can still decay or change with IV before expiration."
    )


@_register("iv_premium_effect")
def _iv_premium_effect() -> None:
    iv = [20, 30, 40, 50, 60]
    premium = [2.1, 2.8, 3.6, 4.5, 5.4]
    fig = go.Figure(
        go.Scatter(
            x=iv,
            y=premium,
            mode="lines+markers",
            line=dict(color=COLORS["secondary"], width=3),
            marker=dict(size=8),
            hovertemplate="IV: %{x}%<br>Premium: $%{y:.2f}<extra></extra>",
        )
    )
    fig.add_annotation(
        x=50,
        y=4.5,
        text="Higher uncertainty<br>means richer premium",
        showarrow=True,
        arrowhead=2,
        ax=-80,
        ay=-45,
        font=dict(size=11, color=COLORS["neutral"]),
    )
    fig.update_layout(
        **_chart_layout(
            "IV impact on option premium",
            "Implied volatility (%)",
            "Premium ($ per share)",
            height=360,
            showlegend=False,
            margin=dict(l=55, r=30, t=70, b=55),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Same stock, same strike, same expiration:** higher IV usually means a higher option premium because the market is pricing a wider possible move.\n"
        "- **For option buyers:** rising IV after entry can help; falling IV can hurt even when direction is partly correct.\n"
        "- **For option sellers:** high IV can create richer credits, but the premium is high because the market is pricing more risk.\n"
        "- **IV crush:** after an event, IV can fall quickly and remove extrinsic value from long options."
    )


@_register("greeks_sensitivity")
def _greeks_sensitivity() -> None:
    greeks = ["Delta", "Gamma", "Theta/day", "Vega", "Rho"]
    values = [0.52, 0.08, -0.05, 0.12, 0.04]
    descriptions = [
        "Option gains about $0.52 if stock rises $1",
        "Delta changes about 0.08 after a $1 stock move",
        "Option loses about $0.05 per day if nothing else changes",
        "Option gains about $0.12 if IV rises 1 vol point",
        "Option gains about $0.04 if rates rise 1 percentage point",
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=values,
            y=greeks,
            orientation="h",
            marker_color=[
                COLORS["positive"],
                COLORS["accent"],
                COLORS["negative"],
                COLORS["secondary"],
                COLORS["neutral"],
            ],
            text=[f"{value:+.2f}" for value in values],
            textposition="outside",
            hovertext=descriptions,
            hovertemplate="<b>%{y}</b><br>%{hovertext}<extra></extra>",
        )
    )
    fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
    fig.update_layout(
        **_chart_layout(
            "Greeks snapshot: long at-the-money call",
            "Estimated sensitivity per share",
            "",
            height=370,
            showlegend=False,
            margin=dict(l=105, r=80, t=60, b=45),
            xaxis=dict(range=[-0.15, 0.62], zeroline=False),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Positive delta and vega:** this long call benefits from stock price rising and IV rising.\n"
        "- **Negative theta:** time passing hurts the option if price and IV do not help.\n"
        "- **Gamma:** tells you the option's directional exposure can change as the stock moves.\n"
        "- **Rho:** shows interest-rate exposure; it is usually smaller for short-term options and more relevant for long-dated contracts."
    )


@_register("strike_selection_matrix")
def _strike_selection_matrix() -> None:
    rows = [
        [
            "ITM",
            "Higher",
            "Higher delta; more stock-like",
            "Directional exposure, stronger hedge, higher-probability thesis",
            "Larger dollars at risk; still has extrinsic value that can decay",
        ],
        [
            "ATM",
            "Medium / high",
            "Balanced delta; high gamma",
            "Balanced directional trades, event setups, straddles, spread anchors",
            "High time value; sensitive to theta and IV crush",
        ],
        [
            "OTM",
            "Lower",
            "Lower delta; needs larger move",
            "Low-cost speculation, tail hedge, long leg of spreads",
            "Higher chance of expiring worthless; cheap is not always good value",
        ],
    ]
    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[0.55, 0.9, 1.25, 1.8, 1.8],
                header=dict(
                    values=[
                        "<b>Strike zone</b>",
                        "<b>Premium</b>",
                        "<b>Behavior</b>",
                        "<b>Often fits</b>",
                        "<b>Main trade-off</b>",
                    ],
                    fill_color=COLORS["secondary"],
                    font=dict(color="white", size=12),
                    align="left",
                ),
                cells=dict(
                    values=list(map(list, zip(*rows))),
                    fill_color=[
                        ["#e0f2fe", "#fef3c7", "#f8fafc"],
                        ["#e0f2fe", "#fef3c7", "#f8fafc"],
                        ["#e0f2fe", "#fef3c7", "#f8fafc"],
                        ["#e0f2fe", "#fef3c7", "#f8fafc"],
                        ["#e0f2fe", "#fef3c7", "#f8fafc"],
                    ],
                    align="left",
                    height=42,
                    font=dict(size=12),
                ),
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Choosing ITM, ATM, or OTM: practical trade-offs", font=dict(size=14)),
        height=300,
        margin=dict(l=10, r=10, t=45, b=10),
        template="plotly_white",
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Start with the trade purpose:** hedge, directional exposure, speculation, income, or spread construction.\n"
        "- **Then compare cost versus probability:** ITM costs more but responds more; OTM costs less but needs a larger move.\n"
        "- **Finally check execution:** a theoretically good strike can still be a poor trade if the bid/ask spread is too wide."
    )


@_register("delta_by_strike")
def _delta_by_strike() -> None:
    spot = 100
    strikes = list(range(80, 121, 2))
    call_delta = [1 / (1 + math.exp((strike - spot) / 4)) for strike in strikes]
    put_delta = [delta - 1 for delta in call_delta]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=strikes,
            y=call_delta,
            mode="lines",
            name="Call delta",
            line=dict(color=COLORS["positive"], width=3),
            hovertemplate="Strike: %{x}<br>Call delta: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=strikes,
            y=put_delta,
            mode="lines",
            name="Put delta",
            line=dict(color=COLORS["negative"], width=3),
            hovertemplate="Strike: %{x}<br>Put delta: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#cbd5e1")
    fig.add_vrect(x0=80, x1=100, fillcolor=COLORS["positive"], opacity=0.05, line_width=0)
    fig.add_vrect(x0=100, x1=120, fillcolor=COLORS["negative"], opacity=0.04, line_width=0)
    fig.add_vline(x=spot, line_dash="dash", line_color="#64748b", annotation_text="Stock price / ATM")
    fig.update_layout(
        **_chart_layout(
            "Delta evolution by strike (stock fixed at $100)",
            "Option strike price",
            "Delta (approx. share exposure)",
            height=340,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            yaxis=dict(range=[-1.05, 1.05], tickformat=".2f"),
        )
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Call delta evolves from high to low as strike increases:** with the stock near \\$100, lower-strike calls are already in the money and behave more like stock, so their delta is closer to +1. Higher-strike calls are out of the money and need a bigger move before they behave like stock, so their delta is closer to 0.\n"
        "- **Put delta evolves from near 0 to more negative as strike increases:** lower-strike puts are out of the money and have less immediate downside exposure. Higher-strike puts are more in the money, so they behave more like short stock and move toward -1 delta.\n"
        "- **At the money is the transition zone:** around the stock price, both calls and puts usually have delta near +/-0.50. This is where delta changes fastest as price moves, which is why gamma matters most near the strike.\n"
        "- **How to read this during a trade:** if you buy an out-of-the-money call and the stock rallies toward your strike, delta can rise from small exposure toward stock-like exposure. If the move stalls or reverses, delta can fall again, and the option loses directional power."
    )


@_register("rates_dividend_effect")
def _rates_dividend_effect() -> None:
    scenarios = ["Base", "Rates +1%", "Dividend +1%"]
    call_prem = [4.0, 4.2, 3.8]
    put_prem = [3.5, 3.3, 3.7]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Call", x=scenarios, y=call_prem, marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(name="Put", x=scenarios, y=put_prem, marker_color=COLORS["negative"]))
    fig.update_layout(**_chart_layout("Rates & dividends (illustrative)", "Scenario", "Premium"), barmode="group")
    _plotly_chart(fig)


@_register("regime_matrix")
def _regime_matrix() -> None:
    rows = [
        ["Risk-on", "VIX falling, breadth strong, growth leads", "Long stock, bull call spreads, long calls", "Capping upside too early"],
        ["Neutral / range", "Chop, rotations, failed breakouts", "Covered calls, calendars, iron condors", "Buying short-dated premium without catalyst"],
        ["Risk-off", "VIX rising, support breaks, correlations rise", "Cash, collars, protective puts, smaller size", "Oversized directional bets"],
        ["Event / high IV", "Premium rich before known catalyst", "Defined-risk credits or event debit trades", "Ignoring IV crush and expected move"],
    ]
    fig = go.Figure(
        go.Table(
            columnwidth=[0.9, 1.8, 1.8, 1.6],
            header=dict(
                values=["<b>Regime</b>", "<b>Evidence</b>", "<b>Often fits</b>", "<b>Often avoid</b>"],
                fill_color=COLORS["secondary"],
                font=dict(color="white", size=12),
                align="left",
            ),
            cells=dict(
                values=list(map(list, zip(*rows))),
                fill_color=[
                    ["#ecfdf5", "#fef3c7", "#fef2f2", "#eef6ff"],
                    ["#ecfdf5", "#fef3c7", "#fef2f2", "#eef6ff"],
                    ["#ecfdf5", "#fef3c7", "#fef2f2", "#eef6ff"],
                    ["#ecfdf5", "#fef3c7", "#fef2f2", "#eef6ff"],
                ],
                align="left",
                height=42,
                font=dict(size=12),
            ),
        )
    )
    fig.update_layout(
        title=dict(text="Regime map: evidence before structure", font=dict(size=14)),
        height=300,
        margin=dict(l=10, r=10, t=45, b=10),
        template="plotly_white",
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Start with evidence:** trend, VIX, breadth, leadership, credit stress, and catalyst timing.\n"
        "- **Then choose structure:** the same bullish thesis may call for stock in risk-on, a bull call spread in moderate IV, or no trade in risk-off.\n"
        "- **Avoid one-strategy thinking:** regime decides whether you want direction, income, hedge, or patience."
    )


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
    _plotly_chart(fig)
    st.markdown(
        "- **VIX falling:** often supports risk-on trades because protection demand is cooling.\n"
        "- **VIX stable:** can fit range/income structures if price is also range-bound.\n"
        "- **VIX rising:** reduce size and define risk; option premiums expand but losses can accelerate."
    )


@_register("iv_scale")
def _iv_scale() -> None:
    labels = ["Low IV", "Medium IV", "High IV", "Extreme IV"]
    fig = go.Figure(go.Bar(x=labels, y=[1, 2, 3, 4], marker_color=[COLORS["positive"], COLORS["accent"], COLORS["negative"], "#8b0000"]))
    fig.update_layout(**_chart_layout("Relative IV buckets (judge vs symbol history)", "Bucket", "Relative level", height=280))
    _plotly_chart(fig)
    st.markdown(
        "- **Low IV:** premium is cheaper relative to history, but a movement thesis is still required.\n"
        "- **High IV:** premium is richer, which can favor defined-risk selling only if max loss is acceptable.\n"
        "- **Extreme IV:** usually event-driven; compare premium to expected move before buying or selling options."
    )


@_register("regime_decision_flow")
def _regime_decision_flow() -> None:
    steps = [
        {"y": 0.90, "title": "Start with context", "subtitle": "What is the market doing today?"},
        {"y": 0.68, "title": "Classify regime", "subtitle": "Name the environment before picking a trade"},
        {"y": 0.46, "title": "Read IV for the symbol", "subtitle": "Is option premium cheap or rich?"},
        {"y": 0.24, "title": "Pick structure", "subtitle": "Stock, option, spread, hedge, or no trade"},
        {"y": 0.02, "title": "Risk check", "subtitle": "Confirm dollars at risk and exit plan"},
    ]
    box_width = 0.86
    box_height = 0.14
    x_center = 0.5
    fig = go.Figure()

    for index, step in enumerate(steps):
        y = step["y"]
        fig.add_shape(
            type="rect",
            x0=x_center - box_width / 2,
            x1=x_center + box_width / 2,
            y0=y - box_height / 2,
            y1=y + box_height / 2,
            line=dict(color=COLORS["secondary"], width=2),
            fillcolor="rgba(45, 106, 159, 0.10)",
            layer="below",
        )
        fig.add_annotation(
            x=x_center,
            y=y + 0.022,
            text=f"<b>{index + 1}. {step['title']}</b>",
            showarrow=False,
            font=dict(size=12, color=COLORS["primary"]),
            align="center",
        )
        fig.add_annotation(
            x=x_center,
            y=y - 0.028,
            text=step["subtitle"],
            showarrow=False,
            font=dict(size=10, color=COLORS.get("text_muted", "#5a6a7a")),
            align="center",
        )
        if index < len(steps) - 1:
            next_y = steps[index + 1]["y"]
            upper_bottom = y - box_height / 2
            lower_top = next_y + box_height / 2
            connector_y = (upper_bottom + lower_top) / 2
            fig.add_shape(
                type="line",
                x0=x_center,
                x1=x_center,
                y0=upper_bottom,
                y1=lower_top,
                line=dict(color="#9aa8b8", width=2),
                layer="below",
            )
            fig.add_annotation(
                x=x_center,
                y=connector_y,
                text="▼",
                showarrow=False,
                font=dict(size=11, color="#9aa8b8"),
                align="center",
            )

    fig.update_layout(
        **_chart_layout(
            "Pre-trade decision flow",
            "",
            "",
            height=520,
            xaxis=dict(visible=False, range=[0, 1], fixedrange=True),
            yaxis=dict(visible=False, range=[-0.12, 1.02], fixedrange=True),
            margin=dict(l=24, r=24, t=56, b=16),
            showlegend=False,
        )
    )
    _plotly_chart(fig)
    tutor_report = _tutor_report_context.get()
    live_context = format_decision_flow_live_context(tutor_report)
    _render_regime_decision_flow_guide(live_context)


def _render_tutor_live_suggestion(content: str) -> None:
    """Render tutor live market/regime suggestions in a blue callout."""
    text = str(content or "").strip()
    if text:
        st.info(text)


def _render_regime_decision_flow_guide(live_context: dict[str, str] | None = None) -> None:
    """Render detailed definitions for each step in the pre-trade decision flow."""
    live_context = live_context or {}
    has_live = bool(live_context.get("has_live_context"))

    st.markdown(
        """
**How to use this flow**

Do not jump straight to a favorite strategy. Answer the steps in order. Each later step depends on the
answers from the steps above it. If step 5 fails, the correct action is often **no trade** or **smaller size** —
not forcing the original idea.
"""
    )
    if has_live:
        st.caption(
            "Steps 1–4 below are pre-filled from the **Trading tutor** live market read above. "
            "Blue boxes are the tutor suggestion; reference definitions follow each divider."
        )

    with st.expander(
        "Step 1 — Start with context (what to observe)",
        expanded=True,
    ):
        if has_live and live_context.get("step1"):
            st.markdown("#### Your live context read")
            _render_tutor_live_suggestion(live_context["step1"])
            st.divider()
            st.markdown("#### What each input means (reference)")
        st.markdown(
            """
| Input | What it tells you | Practical read |
|-------|-------------------|----------------|
| **Index trend (SPY / QQQ)** | Is the broad market rising, falling, or chopping? | Uptrend supports bullish trades; breakdown supports defense |
| **VIX (or VIX proxy)** | Is fear entering or leaving the market? | Falling VIX often supports risk-taking; rising VIX warns to reduce size |
| **Breadth** | Are many stocks participating, or only a few leaders? | Strong breadth supports breakouts; weak breadth makes breakouts fragile |
| **Sector leadership** | Is money flowing into growth/cyclicals or into defensives? | Growth leading = risk appetite; defensives leading = caution |
"""
        )
        if not has_live:
            st.markdown(
                """
**Example:** SPY is above its 20-day average, VIX is falling, technology leads, and breadth is positive.
That context supports looking for bullish structures — but you still have not chosen the trade yet.

Open **Trading tutor** and run **Refresh market read** to auto-fill this step with live data.
"""
            )

    with st.expander("Step 2 — Classify regime (definitions)", expanded=True):
        if has_live and live_context.get("step2"):
            st.markdown("#### Your live regime read")
            _render_tutor_live_suggestion(live_context["step2"])
            st.divider()
            st.markdown("#### Regime definitions (reference)")
        st.markdown(
            """
A **regime** is a short label for the market environment. Use the evidence from step 1 to pick one primary regime.

#### Risk-on
Investors are willing to buy risk assets. Upside moves tend to hold, dips are often bought, and volatility often cools.

- **Typical evidence:** indexes trend up or hold support; VIX stable or falling; growth sectors lead; breadth positive; bad headlines are often ignored
- **Often fits:** long stock, long calls, bull call spreads, buying breakouts with defined risk
- **Often avoid:** capping upside too early with tight covered calls in a strong trend

#### Neutral / range-bound
The market is chopping between support and resistance without a clean directional edge.

- **Typical evidence:** repeated failed breakouts; indexes flat over several sessions; rotations between sectors; IV may be elevated even without a strong trend
- **Often fits:** covered calls, cash-secured puts, bull put spreads, bear call spreads, iron condors, calendars
- **Often avoid:** buying short-dated ATM options without a catalyst (theta works against you)

#### Risk-off
Investors are reducing risk. Support breaks more easily, correlations rise, and protection demand increases.

- **Typical evidence:** indexes break support; VIX rising; defensives lead; breadth weak; bad news is punished quickly
- **Often fits:** cash, smaller size, protective puts, collars, bear put spreads
- **Often avoid:** oversized bullish bets or naked short puts into a falling market

#### Event-driven / high IV
A known catalyst (earnings, Fed, macro release) may create a large move, and option premiums are often rich.

- **Typical evidence:** scheduled event within days; IV rank elevated; implied move priced into options
- **Often fits:** defined-risk spreads, hedges, comparing implied move vs your thesis before buying premium
- **Often avoid:** undefined-risk short options and illiquid strikes around the event

**Rule of thumb:** write one sentence: *"Today looks mostly ___ because ___."* If you cannot complete that sentence, pause before trading.
"""
        )

    with st.expander("Step 3 — Read IV for the symbol (cheap, fair, expensive, extreme)", expanded=has_live):
        if has_live and live_context.get("step3"):
            st.markdown("#### Your live IV read")
            _render_tutor_live_suggestion(live_context["step3"])
            st.divider()
            st.markdown("#### IV definitions (reference)")
        st.markdown(
            """
**Implied volatility (IV)** is what the options market charges for expected movement. Judge IV **relative to that symbol's own history** (IV Rank), not in isolation.

| IV Rank (illustrative) | Label | What it usually means | Buyer implication | Seller implication |
|------------------------|-------|----------------------|-------------------|-------------------|
| **Below ~35** | Cheap / low | Premium is low vs recent history | Long options cost less, but you still need a move | Less credit for sellers; need strong range thesis |
| **~35–60** | Fair / medium | Normal premium for this name | Bull call spreads and stock both reasonable | Bull put spreads and bear call spreads need clear range or willingness to own |
| **~60–80** | Elevated / expensive | Premium is rich | Prefer spreads over naked long options | Credit may pay well, but gap risk rises |
| **Above ~80** | Extreme / event-like | Market prices a large move | Buying premium is costly; IV crush risk after event | Selling premium is risky unless defined-risk and sized small |

**Example:** IV Rank is 78 one week before earnings. A naked long call is expensive and may lose from IV crush even if direction is right. Compare the implied move to your thesis, or use a spread / wait.
"""
        )

    with st.expander("Step 4 — Pick structure (match regime + IV to the trade)", expanded=has_live):
        if has_live and live_context.get("step4"):
            st.markdown("#### Your live structure suggestions")
            _render_tutor_live_suggestion(live_context["step4"])
            st.divider()
            st.markdown("#### Structure map (reference)")
        st.markdown(
            """
The structure is *how* you express the idea after regime and IV are clear.

| Your read | IV cheap / fair | IV elevated / expensive |
|-----------|-----------------|-------------------------|
| **Risk-on bullish** | Stock, long call, bull call spread | Bull call spread preferred over naked call |
| **Neutral / range** | Stock only if range is clear; otherwise income structures | Covered call, CSP, bull put spread, bear call spread, iron condor |
| **Risk-off / hedge** | Protective put, collar, reduce stock size | Same hedges; puts may already be expensive — use spreads |
| **Event / unclear direction** | Long straddle only if implied move < your expected move | Iron butterfly / defined-risk credit with strict max loss |

**Structure definitions (quick)**

- **Stock:** full upside and downside; no expiration; needs more capital
- **Long call / put:** defined risk (premium); leveraged; time decay works against you
- **Bull call spread / bear put spread:** cheaper than naked option; caps profit and loss
- **Bull put spread / bear call spread / iron condor:** collect premium; profits if price stays in range; gap risk remains
- **Covered call / CSP:** income structures; assignment must be acceptable
- **Collar / protective put:** hedge stock you already own
- **No trade:** valid outcome when regime, IV, or risk check does not support the idea
"""
        )

    with st.expander("Step 5 — Risk check (final gate before the order)", expanded=False):
        st.markdown(
            """
Even a good-looking setup fails this step if risk is undefined.

1. **Max loss in dollars and % of account** — convert contracts into real money. If uncomfortable, reduce size.
2. **Invalidation** — what price or date proves the thesis wrong? Options also need a **time stop** (theta).
3. **If price does nothing** — many option losses come from no movement, not wrong direction.
4. **Liquidity** — tight bid/ask on the strikes you plan to trade; wide spreads increase true cost.
5. **Assignment / margin** — for short options and stock-plus-option structures, know what assignment means.
6. **Exit plan** — profit target, loss limit, and roll rules written before entry.

**If any answer is vague, revise the trade or skip it.** The flow ends here — not at the order ticket.
"""
        )

    if has_live:
        st.markdown(
            """
**Worked example (from today's tutor read)**

Use the live sections in steps 1–4 above as your answer key, then complete **step 5 — Risk check**
before opening **Strategy payoff lab** or sending an order.
"""
        )
    else:
        st.markdown(
            """
**Worked example (short)**

1. **Context:** SPY uptrend, VIX falling, tech leading, breadth positive.
2. **Regime:** **Risk-on** — dips are being bought and volatility is cooling.
3. **IV:** Stock IV Rank = 28 → **cheap / fair** for a directional bullish trade.
4. **Structure:** Compare **stock** vs **bull call spread** (defined risk) vs **long call** (more leverage).
5. **Risk check:** Max loss = spread debit; invalidation = close below breakout support; skip if spread is illiquid.

Only after all five steps should you open **Strategy payoff lab** or send an order.
"""
        )


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
    _plotly_chart(fig)
    st.markdown(
        "- **Stock:** no expiration and linear exposure, but requires more capital and carries full downside.\n"
        "- **Long call:** lower upfront cost and capped loss, but needs enough upside before expiration to overcome premium.\n"
        "- **Key decision:** use stock when timing is uncertain; use calls when the move is time-bound and premium is reasonable."
    )


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
    _plotly_chart(fig)
    st.markdown(
        "- **Stock only:** downside keeps increasing as price falls.\n"
        "- **Stock + put:** the put creates a floor below the strike, but the premium reduces upside.\n"
        "- **Insurance trade-off:** closer puts protect sooner and cost more; farther puts cost less and protect later."
    )


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
    _plotly_chart(fig)
    st.markdown(
        "- **Premium helps:** the call credit improves flat or slightly down outcomes.\n"
        "- **Upside is capped:** above the short call strike, gains stop increasing because shares may be called away.\n"
        "- **Downside remains:** the premium is only a cushion, not full protection."
    )


@_register("cash_secured_put")
def _cash_secured_put() -> None:
    strike, credit = 95.0, 2.5
    prices = _price_range(100, 0.25)
    pnl = [credit * 100 if p >= strike else credit * 100 - (strike - p) * 100 for p in prices]
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.add_vline(x=strike, line_dash="dot", annotation_text="Strike")
    fig.update_layout(**_chart_layout("Short put @ expiration (per contract)", "Stock price", "P&L ($)"))
    _plotly_chart(fig)
    st.markdown(
        "- **Max gain:** the premium received if the stock stays above the strike.\n"
        "- **Assignment zone:** below the strike, losses grow as if you bought stock at the strike minus premium.\n"
        "- **Best fit:** only sell puts on stocks you are willing and able to own."
    )


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
    fig.update_layout(**_chart_layout("Bull put spread @ expiration", "Stock price", "P&L ($)"))
    _plotly_chart(fig)
    st.markdown(
        "- **Max gain:** net credit received when price stays above the short put strike.\n"
        "- **Max loss:** spread width minus credit if price finishes below the long put strike.\n"
        "- **Why use it:** defined risk premium selling when you expect price to hold above support."
    )


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
    _plotly_chart(fig)
    st.markdown(
        "- **Profit zone:** price stays between the short put and short call strikes.\n"
        "- **Defined risk:** long wings cap loss if price breaks far outside the range.\n"
        "- **Best fit:** elevated IV and a range-bound thesis, not a strong trend."
    )


@_register("long_straddle")
def _long_straddle() -> None:
    strike, prem = 100.0, 6.0
    prices = _price_range(strike, 0.3)
    pnl = [(max(p - strike, 0) + max(strike - p, 0) - prem) * 100 for p in prices]
    fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", line=dict(color=COLORS["secondary"], width=3)))
    fig.add_hline(y=0, line_dash="dash")
    fig.add_vline(x=strike, line_dash="dot")
    fig.update_layout(**_chart_layout("Long straddle @ expiration", "Stock price", "P&L ($)"))
    _plotly_chart(fig)
    st.markdown(
        "- **Needs movement:** profit requires a move larger than the combined call + put premium.\n"
        "- **Two break-evens:** strike plus total premium and strike minus total premium.\n"
        "- **Event risk:** IV crush can hurt both legs after the catalyst if the move is too small."
    )


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
    _plotly_chart(fig)
    st.markdown(
        "- **Put floor:** the long put limits downside below the put strike.\n"
        "- **Call ceiling:** the short call helps finance the put but caps upside above the call strike.\n"
        "- **Best fit:** protecting stock gains when you can accept a capped upside range."
    )


@_register("diagonal_concept")
def _diagonal_concept() -> None:
    days = list(range(0, 91, 15))
    long_val = [4.5 - d * 0.01 for d in days]
    short_vals = [2.0, 1.2, 0.5, 0.1, 0.0, 0.0, 0.0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=long_val, mode="lines", name="Long call (90 DTE)", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=days[:4], y=short_vals[:4], mode="lines+markers", name="Short call (30 DTE cycles)", line=dict(color=COLORS["accent"])))
    fig.update_layout(**_chart_layout("Diagonal: long option + repeated short calls", "Days", "Illustrative value"))
    _plotly_chart(fig)
    st.markdown(
        "- **Long call:** the anchor leg keeps longer-term bullish exposure.\n"
        "- **Short call:** the income leg decays faster but can cap or offset gains during a fast rally.\n"
        "- **Management matters:** diagonals are path-dependent; flat, slow-up, fast-up, and down paths require different decisions."
    )


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
    _plotly_chart(fig)
    st.markdown(
        "- **Defined risk:** max loss is the debit paid for the spread.\n"
        "- **Capped upside:** max value is the distance between strikes, so profit is capped above the short call.\n"
        "- **With stock:** the spread adds time-bound upside leverage; it does not protect the share position."
    )


@_register("roll_covered_call")
def _roll_covered_call() -> None:
    scenarios = ["No roll", "Roll up", "Roll out"]
    upside = [1400, 1600, 1500]
    fig = go.Figure(go.Bar(x=scenarios, y=upside, marker_color=[COLORS["negative"], COLORS["positive"], COLORS["accent"]]))
    fig.update_layout(**_chart_layout("Illustrative outcome when stock rallies past strike", "Management", "P&L if assigned/rolled", height=280))
    _plotly_chart(fig)
    st.markdown(
        "- **No roll:** can be correct if assignment matches the original plan.\n"
        "- **Roll up:** recovers more upside, but often costs debit or reduces credit.\n"
        "- **Roll out:** collects more time premium, but keeps the obligation open longer.\n"
        "- **Rule:** roll only when the new strike, credit/debit, and added time improve the expected outcome."
    )


@_register("margin_comparison")
def _margin_comparison() -> None:
    structures = ["Naked short call", "Diagonal", "Defined spread"]
    margin = [100, 35, 15]
    fig = go.Figure(go.Bar(x=structures, y=margin, marker_color=[COLORS["negative"], COLORS["accent"], COLORS["positive"]]))
    fig.update_layout(**_chart_layout("Relative margin usage (illustrative index)", "Structure", "Margin index", height=280))
    _plotly_chart(fig)
    st.markdown(
        "- **Naked short options:** highest buying-power risk because loss can expand quickly.\n"
        "- **Diagonals:** the long leg may reduce risk, but expiration mismatch can still require margin.\n"
        "- **Defined spreads:** usually use less buying power because max loss is known.\n"
        "- **Always preview:** broker margin can change when volatility rises or the trade moves against you."
    )


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
    _plotly_chart(fig)


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
    _plotly_chart(fig)


class _SimpleTableParser(HTMLParser):
    """Small HTML table parser for the NYU Stern annual returns page."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._cell_buffer: list[str] = []
        self._in_row = False
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._in_row = True
            self._current_row = []
        if tag.lower() in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._cell_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._in_cell:
            text = "".join(self._cell_buffer).replace("\xa0", " ").strip()
            self._current_row.append(re.sub(r"\s+", " ", text))
            self._in_cell = False
        if tag.lower() == "tr" and self._in_row:
            if any(cell for cell in self._current_row):
                self.rows.append(self._current_row)
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_buffer.append(data)


def _load_long_term_market_data() -> dict[str, list[float]]:
    """Load cached long-term GDP/market data from disk."""
    data = {"year": [], "gdp": [], "sp500": []}
    with _LONG_TERM_MARKET_DATA_PATH.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            data["year"].append(int(row["year"]))
            data["gdp"].append(float(row["real_gdp_index_1929_100"]))
            data["sp500"].append(float(row["sp500_total_return_index_1929_100"]))
    return data


def _fetch_text(url: str, timeout: int = 45, attempts: int = 2) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("latin1", "ignore")
        except Exception as exc:  # noqa: BLE001 - retry network timeouts and source hiccups
            last_error = exc
    raise RuntimeError(f"External source unavailable after {attempts} attempts: {last_error}")


def _parse_money(value: str) -> float:
    return float(value.replace("$", "").replace(",", "").strip())


def _refresh_long_term_market_data() -> int:
    """Fetch source data, rebuild the local cache, and return row count."""
    gdp_csv = _fetch_text("https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPCA")
    gdp_by_year: dict[int, float] = {}
    for row in csv.DictReader(gdp_csv.splitlines()):
        value = row.get("GDPCA")
        if value and value != ".":
            gdp_by_year[int(row["observation_date"][:4])] = float(value)

    html = _fetch_text("https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html", timeout=60)
    parser = _SimpleTableParser()
    parser.feed(html)
    sp500_by_year: dict[int, float] = {}
    for row in parser.rows:
        if not row or not row[0].isdigit() or len(row) < 9:
            continue
        year = int(row[0])
        if year >= 1928 and row[8].strip():
            sp500_by_year[year] = _parse_money(row[8])

    start_year = 1929
    end_year = min(max(gdp_by_year), max(sp500_by_year))
    base_gdp = gdp_by_year[start_year]
    base_sp500 = sp500_by_year[start_year]
    rows = []
    for year in range(start_year, end_year + 1):
        if year not in gdp_by_year or year not in sp500_by_year:
            continue
        rows.append(
            {
                "year": year,
                "real_gdp_index_1929_100": round(gdp_by_year[year] / base_gdp * 100, 3),
                "sp500_total_return_index_1929_100": round(sp500_by_year[year] / base_sp500 * 100, 3),
            }
        )

    if not rows:
        raise ValueError("No long-term market rows were generated.")

    _LONG_TERM_MARKET_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LONG_TERM_MARKET_DATA_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _long_term_market_recession_periods() -> list[tuple[float, float, str]]:
    return [
        (1929.6, 1933.25, "Great Depression"),
        (1937.4, 1938.5, "1937-38 recession"),
        (1945.1, 1945.8, "1945 recession"),
        (1948.9, 1949.8, "1948-49 recession"),
        (1953.5, 1954.4, "1953-54 recession"),
        (1957.6, 1958.3, "1957-58 recession"),
        (1960.3, 1961.1, "1960-61 recession"),
        (1969.9, 1970.9, "1969-70 recession"),
        (1973.9, 1975.2, "1973-75 recession"),
        (1980.0, 1980.6, "1980 recession"),
        (1981.5, 1982.9, "1981-82 recession"),
        (1990.5, 1991.25, "1990-91 recession"),
        (2001.2, 2001.9, "2001 recession"),
        (2007.9, 2009.5, "Great Recession"),
        (2020.1, 2020.35, "2020 recession"),
    ]


@_register("long_term_market_gdp")
def _long_term_market_gdp() -> None:
    """Show why long-run investing is tied to economic compounding."""
    col1, col2 = st.columns([1, 3])
    with col1:
        prefix = _visual_key_prefix.get() or "long_term_market_gdp"
        if st.button(
            "Update cached data",
            key=f"{prefix}_update_cached_data",
            help="Optional. The chart uses saved local data by default; this tries to refresh from FRED and NYU Stern.",
        ):
            with st.spinner("Fetching GDP and S&P 500 history..."):
                try:
                    row_count = _refresh_long_term_market_data()
                    st.success(f"Updated local cache with {row_count} annual rows.")
                except Exception as exc:  # noqa: BLE001 - external data failures should not break the lesson
                    st.info("External sources did not respond in time. The chart is still using the saved local dataset.")
                    with st.expander("Technical details"):
                        st.write(str(exc))
    with col2:
        st.caption(_LONG_TERM_MARKET_DATA_SOURCE_NOTE)

    data = _load_long_term_market_data()
    years = data["year"]
    gdp_index = data["gdp"]
    sp500_total_return_index = data["sp500"]
    recessions = _long_term_market_recession_periods()

    fig = go.Figure()
    for start, end, _label in recessions:
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="#c7c7c7",
            opacity=0.22,
            line_width=0,
        )

    fig.add_trace(
        go.Scatter(
            x=years,
            y=gdp_index,
            mode="lines+markers",
            name="Real U.S. GDP index",
            line=dict(color=COLORS["secondary"], width=3),
            hovertemplate="Year: %{x}<br>Real GDP index: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=sp500_total_return_index,
            mode="lines+markers",
            name="S&P 500 total-return index",
            line=dict(color=COLORS["positive"], width=3),
            hovertemplate="Year: %{x}<br>S&P 500 total-return index: %{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        **_chart_layout(
            "Real GDP and S&P 500 (1929 = 100)",
            "Year",
            "Indexed value (log scale)",
            height=520,
            margin=dict(l=55, r=25, t=70, b=55),
            yaxis=dict(type="log", tickformat=","),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
    )
    st.caption(
        "Educational indexed reference view. GDP is shown as a real-output growth proxy; "
        "S&P 500 is shown as total-return compounding. Grey bands mark major U.S. recessions/depressions. "
        "The stock market can turn before GDP because investors price future expectations."
    )
    _plotly_chart(fig)


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
    _plotly_chart(fig)


@_register("order_types")
def _order_types() -> None:
    types = ["Market", "Limit", "Stop", "Stop-limit"]
    price_control = [1, 4, 3, 4]
    fill_speed = [4, 2, 3, 2]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Price control", x=types, y=price_control, marker_color=COLORS["positive"]))
    fig.add_trace(go.Bar(name="Fill speed", x=types, y=fill_speed, marker_color=COLORS["accent"]))
    fig.update_layout(
        **_chart_layout(
            "Order type trade-offs",
            "Order type",
            "Score (higher = better)",
            height=360,
            barmode="group",
            margin=dict(l=50, r=25, t=70, b=85),
            legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        )
    )
    _plotly_chart(fig)


@_register("order_action_examples")
def _order_action_examples() -> None:
    examples = [
        ["Open long call", "Buy to open", "1 AAPL 100 Call", "Limit debit", "Creates long call; max loss is premium paid."],
        ["Close long call", "Sell to close", "1 AAPL 100 Call", "Limit credit", "Exits the long call you already own."],
        ["Open short put", "Sell to open", "1 AAPL 95 Put", "Limit credit", "Creates obligation to buy shares if assigned."],
        ["Close short put", "Buy to close", "1 AAPL 95 Put", "Limit debit", "Removes the short put obligation."],
        ["Open bull call spread", "Buy to open + Sell to open", "100 Call / 105 Call", "Net debit", "Open both legs as one combo order."],
        ["Close bull call spread", "Sell to close + Buy to close", "100 Call / 105 Call", "Net credit/debit", "Reverse the opening actions on the same legs."],
    ]
    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[1.05, 1.25, 1.35, 1.05, 2.0],
                header=dict(
                    values=["<b>Goal</b>", "<b>Correct action</b>", "<b>Example contract</b>", "<b>Price control</b>", "<b>Why it matters</b>"],
                    fill_color=COLORS["secondary"],
                    font=dict(color="white", size=12),
                    align="left",
                ),
                cells=dict(
                    values=list(map(list, zip(*examples))),
                    fill_color=[["#f8fafc", "#eef6ff"] * 3],
                    align="left",
                    height=34,
                    font=dict(size=12),
                ),
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Correct option order language examples", font=dict(size=14)),
        height=330,
        margin=dict(l=10, r=10, t=45, b=10),
        template="plotly_white",
    )
    _plotly_chart(fig)
    st.markdown(
        "- **Opening vs closing is critical:** opening creates a new position; closing reduces or exits an existing position.\n"
        "- **Selling is not always closing:** `Sell to open` creates a short option obligation, while `Sell to close` exits a long option.\n"
        "- **For spreads:** use one combo order when possible and control the total net debit or net credit."
    )


@_register("position_sizing")
def _position_sizing() -> None:
    starting_account = 100_000
    loss_numbers = list(range(0, 31))
    risk_levels = [
        (0.005, "0.5% risk/trade", COLORS["positive"]),
        (0.01, "1% risk/trade", COLORS["secondary"]),
        (0.02, "2% risk/trade", COLORS["accent"]),
        (0.05, "5% risk/trade", COLORS["negative"]),
    ]

    fig = go.Figure()
    for risk_fraction, label, color in risk_levels:
        account_values = [starting_account * ((1 - risk_fraction) ** losses) for losses in loss_numbers]
        fig.add_trace(
            go.Scatter(
                x=loss_numbers,
                y=account_values,
                mode="lines",
                name=label,
                line=dict(color=color, width=3),
                hovertemplate=f"{label}<br>Consecutive losses: %{{x}}<br>Account: $%{{y:,.0f}}<extra></extra>",
            )
        )

    fig.add_hline(
        y=starting_account * 0.75,
        line_dash="dot",
        line_color=COLORS["accent"],
        annotation_text="25% drawdown",
        annotation_position="bottom left",
    )
    fig.add_hline(
        y=starting_account * 0.5,
        line_dash="dash",
        line_color=COLORS["negative"],
        annotation_text="50% drawdown",
        annotation_position="bottom left",
    )
    fig.add_annotation(
        x=14,
        y=starting_account * ((1 - 0.05) ** 14),
        text="At 5% risk/trade,<br>14 losses nearly cut<br>the account in half.",
        showarrow=True,
        arrowhead=2,
        ax=90,
        ay=-35,
        font=dict(size=11, color=COLORS["negative"]),
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor=COLORS["negative"],
        borderwidth=1,
    )
    fig.add_annotation(
        x=30,
        y=starting_account * ((1 - 0.01) ** 30),
        text="At 1% risk/trade,<br>the same streak is<br>damaging but survivable.",
        showarrow=True,
        arrowhead=2,
        ax=-100,
        ay=-35,
        font=dict(size=11, color=COLORS["secondary"]),
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor=COLORS["secondary"],
        borderwidth=1,
    )
    fig.update_layout(
        **_chart_layout(
            "Position sizing: surviving losing streaks",
            "Consecutive losing trades",
            "Account value ($)",
            height=500,
            margin=dict(l=65, r=30, t=75, b=55),
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
    )
    st.caption(
        "Example starts with a $100,000 account and assumes each loss risks the same percentage of the current account. "
        "The lesson: larger position sizes recover much more slowly after a losing streak."
    )
    _plotly_chart(fig)


@_register("leaps_short_call")
def _leaps_short_call() -> None:
    days = list(range(0, 366, 30))
    leaps = [12 - d * 0.02 for d in days]
    short_cycle = [2.5 if d % 90 < 30 else 0.8 for d in days]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=leaps, mode="lines", name="LEAPS time value", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=days, y=short_cycle, mode="lines", name="Short call premium cycles", line=dict(color=COLORS["accent"])))
    fig.update_layout(**_chart_layout("LEAPS + short call (illustrative)", "Days", "Option value ($)"))
    _plotly_chart(fig)
    st.markdown(
        "- **LEAPS anchor:** longer-dated calls decay more slowly than short-term calls, but they still lose time value if the thesis stalls.\n"
        "- **Short call cycles:** short calls can reduce cost through repeated premium collection.\n"
        "- **Main risk:** a fast rally can make the short call the problem even while the LEAPS gains value."
    )
