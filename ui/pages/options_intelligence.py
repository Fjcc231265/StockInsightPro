"""Options Intelligence page with institutional-style placeholder dashboards."""

from __future__ import annotations

import streamlit as st

from ui.components.cards import render_metric_card
from ui.components.charts import (
    gamma_exposure_chart,
    max_pain_chart,
    open_interest_chart,
    options_line_chart,
)
from ui.components.page_router import render_ticker_submenu_page
from services.market_data_service import get_quote_summary
from services.options_data_service import (
    get_gamma_exposure,
    get_iv_rank_history,
    get_iv_term_structure,
    get_open_interest_by_strike,
    get_options_chain,
    get_options_kpis,
    get_put_call_ratio_history,
)


def render(submenu: str) -> None:
    """Route options intelligence submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Options Chain Viewer": lambda: _options_chain(ticker),
        "Open Interest Analysis": lambda: _open_interest(ticker),
        "Put/Call Ratio": lambda: _put_call_ratio(ticker),
        "Implied Volatility": lambda: _implied_volatility(ticker),
        "IV Rank": lambda: _iv_rank(ticker),
        "Gamma Exposure": lambda: _gamma_exposure(ticker),
        "Max Pain": lambda: _max_pain(ticker),
        "AI Conclusions": lambda: _ai_conclusions(ticker),
    }
    st.info(
        "Options Intelligence now uses Alpha Vantage HISTORICAL_OPTIONS when available. "
        "Mock options data is disabled. Dealer positioning and options flow are hidden until a provider "
        "with those datasets is added."
    )
    render_ticker_submenu_page(
        "Options Intelligence",
        submenu,
        handlers,
        default_handler=lambda: _options_chain(ticker),
        show_quote_cards=False,
    )


def _render_options_kpis(ticker: str) -> None:
    """Render core options intelligence KPIs."""
    kpis = get_options_kpis(ticker)
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Put/Call", _format_optional_metric(kpis["Put/Call Ratio"]))
    with cols[1]:
        render_metric_card("IV Rank", _format_optional_metric(kpis["IV Rank"], suffix="%"))
    with cols[2]:
        render_metric_card("30D IV", _format_optional_metric(kpis["30D IV"], suffix="%"))
    with cols[3]:
        render_metric_card("Max Pain", _format_optional_metric(kpis["Max Pain"], prefix="$"))
    st.caption(
        f"Options source: {kpis.get('Source', 'Unknown')}"
        + (f" · Snapshot: {kpis['Snapshot Date']}" if kpis.get("Snapshot Date") else "")
    )
    if kpis.get("Error"):
        st.warning(kpis["Error"])
        return
    _render_options_kpi_explanations(ticker, kpis)


def _render_options_kpi_explanations(ticker: str, kpis: dict) -> None:
    """Explain the options KPI cards in plain language."""
    put_call = kpis["Put/Call Ratio"]
    iv_rank = kpis["IV Rank"]
    iv_30d = kpis["30D IV"]
    max_pain = kpis["Max Pain"]
    quote = get_quote_summary(ticker)
    has_live_spot = not str(quote.get("price_source", "")).startswith("Mock")
    spot_price = quote["price"] if has_live_spot else None
    expected_move = spot_price * (iv_30d / 100) / (12 ** 0.5) if spot_price and iv_30d is not None else None
    max_pain_gap = ((max_pain - spot_price) / spot_price) * 100 if spot_price and max_pain is not None else None

    with st.expander("How to read these options indicators", expanded=True):
        st.markdown(
            f"""
            **Put/Call Ratio: {_format_optional_metric(put_call)} — {_put_call_regime(put_call)}**  
            Compares put open interest to call open interest. Below `0.70` is usually call-heavy / bullish, `0.70-1.00` is neutral, above `1.00` is bearish, and above `1.30` can indicate fear or heavy hedging.

            **IV Rank: {_format_optional_metric(iv_rank, suffix="%")} — {_iv_rank_regime(iv_rank)}**  
            Measures where current implied volatility sits versus its recent range. `0-20` suggests cheap options, `20-50` normal, `50-80` expensive, and `80+` very expensive / fear.

            **30D IV: {_format_optional_metric(iv_30d, suffix="%")}**  
            This is the market's annualized implied volatility around the 30-day area. Higher values mean the options market is pricing a larger move. { _expected_move_text(expected_move) }

            **Max Pain: {_format_optional_metric(max_pain, prefix="$")}**  
            Max pain is the strike where total option-buyer payout would be lowest for the selected expiration. It is **not** a consensus forecast, but it can act like a potential magnet or pinning zone near expiration. { _max_pain_gap_text(max_pain_gap) }
            """
        )


def _format_optional_metric(value: object, prefix: str = "", suffix: str = "") -> str:
    """Format optional KPI values."""
    return "-" if value is None else f"{prefix}{float(value):.2f}{suffix}"


def _put_call_regime(value: float | None) -> str:
    """Return a plain-language put/call regime."""
    if value is None:
        return "Unavailable"
    if value < 0.70:
        return "Bullish / call-heavy"
    if value <= 1.00:
        return "Neutral"
    if value <= 1.30:
        return "Bearish / put-heavy"
    return "Fear / heavy hedging"


def _iv_rank_regime(value: float | None) -> str:
    """Return a plain-language IV rank regime."""
    if value is None:
        return "Unavailable"
    if value < 20:
        return "Cheap options"
    if value < 50:
        return "Normal options pricing"
    if value < 80:
        return "Expensive options"
    return "Very expensive / fear"


def _expected_move_text(expected_move: float | None) -> str:
    """Return optional 30-day expected move text."""
    if expected_move is None:
        return "Expected-move dollars are hidden when live spot price is unavailable."
    return f"Approximate 30-day expected move: **+/- ${expected_move:.2f}**."


def _max_pain_gap_text(max_pain_gap: float | None) -> str:
    """Return optional max pain distance text."""
    if max_pain_gap is None:
        return "Distance from spot is hidden when live spot price is unavailable."
    return f"Current max pain is **{max_pain_gap:+.2f}%** from live spot."


def _render_source_caption(frame) -> None:
    """Render source metadata for options dataframes."""
    source = frame.attrs.get("source", "Unknown")
    snapshot = frame.attrs.get("snapshot_date")
    caption = f"Source: {source}"
    if snapshot:
        caption += f" · Snapshot: {snapshot}"
    st.caption(caption)
    if frame.attrs.get("error"):
        st.warning(frame.attrs["error"])


def _has_options_data(frame) -> bool:
    """Return True when a table has real Alpha Vantage options rows."""
    return not frame.empty and frame.attrs.get("source") == "Alpha Vantage Historical Options"


def _render_ai_panel(ticker: str, focus: str) -> None:
    """Render a deterministic options-market interpretation."""
    kpis = get_options_kpis(ticker)
    if kpis.get("Error"):
        st.warning(kpis["Error"])
        return
    quote = get_quote_summary(ticker)
    if str(quote.get("price_source", "")).startswith("Mock"):
        st.warning("Live Alpha Vantage spot quote is unavailable. Directional read is hidden to avoid mixing mock price data.")
        return
    price = quote["price"]
    put_call = kpis["Put/Call Ratio"]
    max_pain = kpis["Max Pain"]
    iv_30d = kpis["30D IV"]
    expected_move = price * (iv_30d / 100) / (12 ** 0.5)
    max_pain_gap = ((max_pain - price) / price) * 100 if price else 0
    directional_read = _options_directional_read(put_call, max_pain_gap)

    st.markdown("#### AI Market Interpretation")
    st.info(
        f"**Options market read:** {directional_read}\n\n"
        f"- Current focus: {focus}\n"
        f"- Spot reference: ${price:.2f}\n"
        f"- Max pain: ${max_pain:.2f} ({max_pain_gap:+.2f}% vs spot)\n"
        f"- Put/call ratio: {put_call:.2f}\n"
        f"- Approx. 30D expected move: ${expected_move:.2f} ({iv_30d:.2f}% annualized IV)\n\n"
        f"Source: {kpis.get('Source', 'Unknown')}"
    )


def _options_directional_read(put_call: float, max_pain_gap: float) -> str:
    """Classify the option market's directional message."""
    if put_call < 0.75 and max_pain_gap > 1:
        return "Bullish tilt. Call-side positioning and max-pain levels sit above spot."
    if put_call > 1.15 and max_pain_gap < -1:
        return "Bearish / defensive tilt. Put-side positioning is elevated and max pain sits below spot."
    if abs(max_pain_gap) <= 1:
        return "Neutral / pinning setup. Options open interest is centered close to spot."
    if max_pain_gap > 1:
        return "Constructive but mixed. Max pain is above spot, while put/call positioning is not strongly bullish."
    return "Cautious but mixed. Max pain is below spot, while put/call positioning is not strongly bearish."


def _options_chain(ticker: str) -> None:
    """Options chain placeholder view."""
    load_key = f"load_options_chain_{ticker}"
    if not st.session_state.get(load_key):
        st.info(
            "Historical options can be a large Alpha Vantage payload. "
            "Click below to load the chain; derived options submenus reuse the same in-memory data afterward."
        )
        if st.button("Load options chain", key=f"load_options_chain_button_{ticker}", type="primary"):
            st.session_state[load_key] = True
            st.rerun()
        return

    _render_options_kpis(ticker)
    chain = get_options_chain(ticker)
    st.markdown("#### Options Chain Snapshot")
    _render_source_caption(chain)
    if not _has_options_data(chain):
        return
    st.dataframe(chain, use_container_width=True, hide_index=True)
    _render_ai_panel(ticker, "surface liquidity and strike-level positioning")


def _open_interest(ticker: str) -> None:
    """Open interest analysis placeholder."""
    _render_options_kpis(ticker)
    oi = get_open_interest_by_strike(ticker)
    _render_source_caption(oi)
    if not _has_options_data(oi):
        return
    st.plotly_chart(open_interest_chart(oi, ticker), use_container_width=True)
    _render_open_interest_interpretation(ticker, oi)
    st.dataframe(oi, use_container_width=True, hide_index=True)
    _render_ai_panel(ticker, "open interest concentration and pinning risk")


def _render_open_interest_interpretation(ticker: str, oi) -> None:
    """Explain open-interest concentration by strike."""
    call_total = float(oi["Call OI"].sum())
    put_total = float(oi["Put OI"].sum())
    total_oi = call_total + put_total
    if total_oi == 0:
        st.info("Open interest is zero for the selected expiration, so there is no strike concentration to interpret.")
        return

    top_call = oi.loc[oi["Call OI"].idxmax()]
    top_put = oi.loc[oi["Put OI"].idxmax()]
    put_call_oi = put_total / call_total if call_total else 0
    dominant_side = _open_interest_dominant_side(put_call_oi)
    quote = get_quote_summary(ticker)
    spot_text = ""
    if not str(quote.get("price_source", "")).startswith("Mock"):
        spot = quote["price"]
        call_gap = ((float(top_call["Strike"]) - spot) / spot) * 100 if spot else 0
        put_gap = ((float(top_put["Strike"]) - spot) / spot) * 100 if spot else 0
        spot_text = (
            f" Live spot is **${spot:.2f}**; the largest call-OI strike is **{call_gap:+.2f}%** from spot "
            f"and the largest put-OI strike is **{put_gap:+.2f}%** from spot."
        )

    st.info(
        f"**Open interest read:** {dominant_side}\n\n"
        f"- Largest call open interest: **{int(top_call['Call OI']):,} contracts** at strike **${float(top_call['Strike']):.2f}**. "
        "Large call-OI strikes can become resistance or upside magnet zones near expiration.\n"
        f"- Largest put open interest: **{int(top_put['Put OI']):,} contracts** at strike **${float(top_put['Strike']):.2f}**. "
        "Large put-OI strikes can become support, hedge concentration, or downside magnet zones near expiration.\n"
        f"- Put/call open-interest ratio for this expiration: **{put_call_oi:.2f}**."
        f"{spot_text}\n\n"
        "Interpretation note: open interest shows where contracts are concentrated; it is not a price forecast by itself. "
        "It is most useful near expiration and should be read together with IV, max pain, news, and earnings catalysts."
    )


def _open_interest_dominant_side(put_call_oi: float) -> str:
    """Return open-interest positioning summary."""
    if put_call_oi < 0.70:
        return "Call-heavy positioning, which can indicate bullish interest or upside speculation."
    if put_call_oi <= 1.00:
        return "Balanced to mildly call-heavy positioning."
    if put_call_oi <= 1.30:
        return "Put-heavy positioning, which can indicate caution or downside hedging."
    return "Strong put-heavy positioning, which can indicate fear or heavy downside protection."


def _put_call_ratio(ticker: str) -> None:
    """Put/call ratio view."""
    ratio = get_put_call_ratio_history(ticker)
    _render_source_caption(ratio)
    if not _has_options_data(ratio):
        return
    title = "Put/Call Ratio by Expiration"
    st.plotly_chart(
        options_line_chart(ratio, "Date", "Put/Call Ratio", title),
        use_container_width=True,
    )
    _render_put_call_ratio_interpretation(ratio)
    st.dataframe(ratio.tail(10), use_container_width=True, hide_index=True)


def _render_put_call_ratio_interpretation(ratio) -> None:
    """Explain put/call ratio by expiration."""
    if ratio.empty:
        st.info("No put/call ratio data is available to interpret.")
        return

    nearest = ratio.iloc[0]
    highest = ratio.loc[ratio["Put/Call Ratio"].idxmax()]
    lowest = ratio.loc[ratio["Put/Call Ratio"].idxmin()]
    latest_value = float(nearest["Put/Call Ratio"])
    fear_expirations = ratio[ratio["Put/Call Ratio"] > 1.30]
    bearish_expirations = ratio[(ratio["Put/Call Ratio"] > 1.00) & (ratio["Put/Call Ratio"] <= 1.30)]
    bullish_expirations = ratio[ratio["Put/Call Ratio"] < 0.70]

    st.info(
        f"**Put/call by expiration read:** {_put_call_regime(latest_value)} for the nearest expiration "
        f"(**{nearest['Date']}**, ratio **{latest_value:.2f}**).\n\n"
        f"- Highest put/call ratio: **{float(highest['Put/Call Ratio']):.2f}** on **{highest['Date']}**. "
        "This is the most defensive / put-heavy expiration on the curve.\n"
        f"- Lowest put/call ratio: **{float(lowest['Put/Call Ratio']):.2f}** on **{lowest['Date']}**. "
        "This is the most call-heavy expiration on the curve.\n"
        f"- Expiration mix: **{len(bullish_expirations)} bullish/call-heavy**, "
        f"**{len(bearish_expirations)} bearish/put-heavy**, "
        f"**{len(fear_expirations)} fear/heavy-hedging**.\n\n"
        "Interpretation note: a rising put/call ratio into an expiration usually points to more downside hedging or caution. "
        "A low ratio usually points to call demand or bullish speculation. It should be read together with open interest strikes, IV, and catalysts."
    )


def _implied_volatility(ticker: str) -> None:
    """Implied volatility term structure placeholder."""
    _render_options_kpis(ticker)
    iv = get_iv_term_structure(ticker)
    _render_source_caption(iv)
    if not _has_options_data(iv):
        return
    st.plotly_chart(
        options_line_chart(iv, "Expiration", "Implied Volatility", f"{ticker} — IV Term Structure"),
        use_container_width=True,
    )
    _render_iv_term_structure_interpretation(iv)
    st.dataframe(iv, use_container_width=True, hide_index=True)
    _render_ai_panel(ticker, "implied volatility term structure")


def _render_iv_term_structure_interpretation(iv) -> None:
    """Explain the implied-volatility term structure."""
    if iv.empty:
        st.info("No implied-volatility term structure is available to interpret.")
        return

    front = iv.iloc[0]
    back = iv.iloc[-1]
    front_iv = float(front["Implied Volatility"])
    back_iv = float(back["Implied Volatility"])
    avg_iv = float(iv["Implied Volatility"].mean())
    slope = back_iv - front_iv
    peak = iv.loc[iv["Implied Volatility"].idxmax()]
    trough = iv.loc[iv["Implied Volatility"].idxmin()]

    st.info(
        f"**IV term structure read:** {_iv_curve_regime(slope)}\n\n"
        f"- Front expiration IV: **{front_iv:.2f}%** on **{front['Expiration']}**.\n"
        f"- Back expiration IV: **{back_iv:.2f}%** on **{back['Expiration']}**.\n"
        f"- Average IV across expirations: **{avg_iv:.2f}%**.\n"
        f"- Highest IV: **{float(peak['Implied Volatility']):.2f}%** on **{peak['Expiration']}**.\n"
        f"- Lowest IV: **{float(trough['Implied Volatility']):.2f}%** on **{trough['Expiration']}**.\n\n"
        "Interpretation note: high front-end IV usually means the market is pricing near-term movement or event risk. "
        "A normal upward-sloping curve suggests uncertainty is spread more evenly over time. "
        "This is expected volatility, not direction."
    )


def _iv_curve_regime(slope: float) -> str:
    """Return a plain-language IV curve regime."""
    if slope < -5:
        return "Inverted / front-loaded. Near-term options are much more expensive than longer expirations."
    if slope < -1:
        return "Mildly inverted. The market is pricing more near-term event risk."
    if slope <= 5:
        return "Relatively flat. The market is pricing similar volatility across expirations."
    return "Upward sloping. Longer-dated options carry higher implied volatility than the front expiration."


def _iv_rank(ticker: str) -> None:
    """IV rank view."""
    rank = get_iv_rank_history(ticker)
    _render_source_caption(rank)
    if not _has_options_data(rank):
        return
    title = "IV Rank by Expiration"
    st.plotly_chart(
        options_line_chart(rank, "Date", "IV Rank", title),
        use_container_width=True,
    )
    _render_iv_rank_interpretation(rank)
    st.dataframe(rank.tail(12), use_container_width=True, hide_index=True)


def _render_iv_rank_interpretation(rank) -> None:
    """Explain IV rank by expiration."""
    if rank.empty:
        st.info("No IV rank data is available to interpret.")
        return

    nearest = rank.iloc[0]
    highest = rank.loc[rank["IV Rank"].idxmax()]
    lowest = rank.loc[rank["IV Rank"].idxmin()]
    cheap = rank[rank["IV Rank"] < 20]
    normal = rank[(rank["IV Rank"] >= 20) & (rank["IV Rank"] < 50)]
    expensive = rank[(rank["IV Rank"] >= 50) & (rank["IV Rank"] < 80)]
    very_expensive = rank[rank["IV Rank"] >= 80]

    st.info(
        f"**IV rank by expiration read:** {_iv_rank_regime(float(nearest['IV Rank']))} for the nearest expiration "
        f"(**{nearest['Date']}**, IV rank **{float(nearest['IV Rank']):.2f}%**).\n\n"
        f"- Highest IV rank: **{float(highest['IV Rank']):.2f}%** on **{highest['Date']}**. "
        "This is the most expensive volatility point on the curve.\n"
        f"- Lowest IV rank: **{float(lowest['IV Rank']):.2f}%** on **{lowest['Date']}**. "
        "This is the cheapest volatility point on the curve.\n"
        f"- Expiration mix: **{len(cheap)} cheap**, **{len(normal)} normal**, "
        f"**{len(expensive)} expensive**, **{len(very_expensive)} very expensive/fear**.\n\n"
        "Interpretation note: low IV rank means options are relatively cheap versus this options-chain range; "
        "high IV rank means options are expensive and the market is demanding more premium for movement risk. "
        "IV rank measures price of volatility, not direction."
    )


def _gamma_exposure(ticker: str) -> None:
    """Gamma exposure placeholder."""
    _render_options_kpis(ticker)
    gex = get_gamma_exposure(ticker)
    _render_source_caption(gex)
    if not _has_options_data(gex):
        return
    st.plotly_chart(gamma_exposure_chart(gex, ticker), use_container_width=True)
    _render_gamma_exposure_interpretation(ticker, gex)
    st.dataframe(gex, use_container_width=True, hide_index=True)
    _render_ai_panel(ticker, "dealer gamma regime and volatility dampening/amplification")


def _render_gamma_exposure_interpretation(ticker: str, gex) -> None:
    """Explain gamma exposure by strike."""
    if gex.empty:
        st.info("No gamma exposure data is available to interpret.")
        return

    net_gamma = float(gex["Gamma Exposure ($MM)"].sum())
    positive = gex[gex["Gamma Exposure ($MM)"] > 0]
    negative = gex[gex["Gamma Exposure ($MM)"] < 0]
    strongest_positive = positive.loc[positive["Gamma Exposure ($MM)"].idxmax()] if not positive.empty else None
    strongest_negative = negative.loc[negative["Gamma Exposure ($MM)"].idxmin()] if not negative.empty else None
    quote = get_quote_summary(ticker)
    spot_text = ""
    if not str(quote.get("price_source", "")).startswith("Mock"):
        spot = quote["price"]
        spot_text = f" Live spot is **${spot:.2f}**."

    st.info(
        f"**Gamma exposure read:** {_gamma_regime(net_gamma)}{spot_text}\n\n"
        f"- Net gamma exposure: **{net_gamma:+.4f} USD MM**.\n"
        f"{_gamma_peak_text('Strongest positive gamma', strongest_positive)}"
        f"{_gamma_peak_text('Strongest negative gamma', strongest_negative)}"
        "\nInterpretation note: positive gamma zones can dampen movement and encourage mean reversion, "
        "while negative gamma zones can amplify movement and increase volatility. "
        "This is an estimate from Alpha Vantage contract greeks/open interest, not a direct dealer-position feed."
    )


def _gamma_regime(net_gamma: float) -> str:
    """Return a plain-language gamma regime."""
    if net_gamma > 0:
        return "Positive net gamma. Market-maker hedging may dampen price swings around key strikes."
    if net_gamma < 0:
        return "Negative net gamma. Hedging flows may amplify moves and increase volatility."
    return "Balanced gamma. No clear damping or amplification bias from this snapshot."


def _gamma_peak_text(label: str, row) -> str:
    """Return formatted gamma peak text."""
    if row is None:
        return f"- {label}: none visible in this expiration.\n"
    return (
        f"- {label}: **{float(row['Gamma Exposure ($MM)']):+.4f} USD MM** "
        f"at strike **{float(row['Strike']):.2f}**.\n"
    )


def _max_pain(ticker: str) -> None:
    """Max pain placeholder."""
    kpis = get_options_kpis(ticker)
    oi = get_open_interest_by_strike(ticker)
    _render_options_kpis(ticker)
    _render_source_caption(oi)
    if not _has_options_data(oi) or kpis.get("Max Pain") is None:
        return
    st.plotly_chart(max_pain_chart(oi, kpis["Max Pain"], ticker), use_container_width=True)
    _render_max_pain_interpretation(ticker, oi, kpis["Max Pain"])
    st.dataframe(oi, use_container_width=True, hide_index=True)
    _render_ai_panel(ticker, "expiration pinning and max-pain magnet risk")


def _render_max_pain_interpretation(ticker: str, oi, max_pain: float) -> None:
    """Explain the max pain map."""
    call_total = float(oi["Call OI"].sum())
    put_total = float(oi["Put OI"].sum())
    total_oi = call_total + put_total
    if total_oi == 0:
        st.info("Open interest is zero for the selected expiration, so max pain cannot be interpreted reliably.")
        return

    quote = get_quote_summary(ticker)
    spot_text = ""
    if not str(quote.get("price_source", "")).startswith("Mock"):
        spot = quote["price"]
        gap = ((max_pain - spot) / spot) * 100 if spot else 0
        spot_text = f" Live spot is **{spot:.2f}**, so max pain is **{gap:+.2f}%** from spot."

    put_call_oi = put_total / call_total if call_total else 0
    st.info(
        f"**Max pain read:** max pain is **{max_pain:.2f}**.{spot_text}\n\n"
        f"- Total call open interest: **{int(call_total):,} contracts**.\n"
        f"- Total put open interest: **{int(put_total):,} contracts**.\n"
        f"- Put/call open-interest ratio: **{put_call_oi:.2f}**.\n\n"
        "Interpretation note: max pain is the strike where total option-buyer payout would be lowest at expiration. "
        "It can act like a potential pinning or magnet zone when expiration is close and open interest is large. "
        "It is **not** a consensus price target or guaranteed forecast for the next 30 days."
    )


def _ai_conclusions(ticker: str) -> None:
    """Consolidated options conclusion."""
    _render_options_kpis(ticker)
    _render_ai_panel(ticker, "overall directional message from options positioning")
    st.markdown(
        """
        **How to use this read**
        - Max pain and open-interest clusters can act like magnets near expiration.
        - Put/call ratio helps identify whether positioning is call-heavy, put-heavy, or balanced.
        - Implied volatility defines the market's expected move, not guaranteed direction.
        - Use this with the earnings calendar and news catalyst views before acting.
        """
    )
