"""Fundamental Analysis page with submenu views."""

import streamlit as st

from ui.components.cards import render_todo_callout
from ui.components.page_router import render_ticker_submenu_page
from services.fundamental_data_service import (
    get_debt_liquidity,
    get_earnings_calendar,
    get_financial_statement,
    get_fundamental_health_label,
    get_growth_metrics,
    get_latest_earnings_release,
    get_income_statement_margins,
    get_profitability_metrics,
    get_statement_variation,
    get_valuation_ratios,
    get_written_fundamental_analysis,
)


def render(submenu: str) -> None:
    """Route fundamental analysis submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Income statement": lambda: _statement("income", ticker),
        "Balance sheet": lambda: _statement("balance", ticker),
        "Cash flow statement": lambda: _statement("cashflow", ticker),
        "Latest earnings release": lambda: _latest_earnings_release(ticker),
        "Earnings calendar": lambda: _earnings_calendar(ticker),
        "Valuation ratios": lambda: _valuation(ticker),
        "Growth metrics": _growth,
        "Profitability metrics": _profitability,
        "Debt and liquidity": _debt_liquidity,
    }
    render_ticker_submenu_page(
        "Fundamental Analysis",
        submenu,
        handlers,
        default_handler=lambda: _statement("income", ticker),
        show_quote_cards=True,
    )


def _statement(stmt_type: str, ticker: str) -> None:
    """Render financial statement table."""
    label_map = _statement_label_map()
    reverse_label_map = {label: key for key, label in label_map.items()}
    selected_label = st.radio(
        "Statement",
        list(reverse_label_map),
        index=list(label_map).index(stmt_type) if stmt_type in label_map else 0,
        horizontal=True,
        key=f"fundamental_statement_{stmt_type}_{ticker}",
    )
    selected_stmt_type = reverse_label_map[selected_label]

    period = st.radio(
        "Reporting period",
        ["Annual", "Quarterly"],
        horizontal=True,
        key=f"fundamental_period_{selected_stmt_type}_{ticker}",
    )
    df = get_financial_statement(selected_stmt_type, ticker, period)
    source = df.attrs.get("source", "Unknown")
    currency = df.attrs.get("currency", "USD")
    st.markdown(f"**{label_map[selected_stmt_type]}**")
    st.caption(f"Source: {source} · Currency: {currency} · Monetary values in millions")
    if df.attrs.get("error"):
        st.warning(f"Alpha Vantage did not return this statement for {ticker}: {df.attrs['error']}")
    if source.startswith("Mock"):
        st.warning("Live Alpha Vantage fundamentals unavailable right now. Showing mock fallback values.")
    if df.empty:
        st.info(f"No {label_map[selected_stmt_type].lower()} rows are available for {ticker}.")
        return
    st.dataframe(df, use_container_width=True)
    variation = get_statement_variation(df)
    with st.expander("Period-over-period percentage variation", expanded=True):
        st.caption("Each column compares the current period against the immediately prior period.")
        st.dataframe(variation, use_container_width=True, hide_index=True)

    if selected_stmt_type == "income":
        margins = get_income_statement_margins(df)
        with st.expander("P&L margins", expanded=True):
            st.caption("Margins are calculated as a percentage of revenue for each period.")
            st.dataframe(margins, use_container_width=True, hide_index=True)

    _render_financial_health_analysis(ticker)

    render_todo_callout(
        f"Add common-size chart visualizations and export for {label_map[selected_stmt_type].lower()}."
    )


def _statement_label_map() -> dict[str, str]:
    """Return financial statement display labels by statement type."""
    return {
        "income": "P&L / Income Statement",
        "balance": "Balance Sheet",
        "cashflow": "Cash Flow Statement",
    }


def _latest_earnings_release(ticker: str) -> None:
    """Render the latest Alpha Vantage earnings release on demand."""
    st.markdown("**Latest Earnings Release**")
    st.caption("Uses Alpha Vantage EARNINGS when configured, with mock fallback if live data is unavailable.")

    earnings_key = f"show_latest_earnings_{ticker}"
    if st.button("Load latest earnings release", key=f"latest_earnings_button_{ticker}", type="primary"):
        st.session_state[earnings_key] = True

    if not st.session_state.get(earnings_key):
        st.info("Click the button to fetch the latest reported EPS release for the selected ticker.")
        return

    with st.spinner("Loading latest earnings release..."):
        release = get_latest_earnings_release(ticker)

    source = release.get("source", "Unknown")
    st.caption(f"Source: {source}")
    if source.startswith("Mock"):
        st.warning("Live Alpha Vantage earnings unavailable right now. Showing mock fallback values.")

    surprise_pct = release.get("surprise_percentage")
    surprise_value = release.get("surprise")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Reported EPS", _format_eps(release.get("reported_eps")))
    with cols[1]:
        st.metric("Estimated EPS", _format_eps(release.get("estimated_eps")))
    with cols[2]:
        st.metric("EPS Surprise", _format_eps(surprise_value), _format_percent_value(surprise_pct))
    with cols[3]:
        st.metric("Report Time", str(release.get("report_time", "Unknown")).title())

    details = {
        "Ticker": release.get("ticker", ticker),
        "Reported Date": release.get("reported_date", "Unknown"),
        "Fiscal Date Ending": release.get("fiscal_date_ending", "Unknown"),
        "Reported EPS": _format_eps(release.get("reported_eps")),
        "Estimated EPS": _format_eps(release.get("estimated_eps")),
        "Surprise": _format_eps(surprise_value),
        "Surprise %": _format_percent_value(surprise_pct),
    }
    st.dataframe(
        [{"Field": field, "Value": value} for field, value in details.items()],
        use_container_width=True,
        hide_index=True,
    )


def _earnings_calendar(ticker: str) -> None:
    """Render upcoming Alpha Vantage earnings calendar dates."""
    st.markdown("**Earnings Calendar**")
    st.caption(
        "Uses Alpha Vantage EARNINGS_CALENDAR. Mock data is only used when no API key is configured."
    )

    horizon_label = st.radio(
        "Calendar horizon",
        ["3 months", "6 months", "12 months"],
        horizontal=True,
        key=f"earnings_calendar_horizon_{ticker}",
    )
    horizon = {"3 months": "3month", "6 months": "6month", "12 months": "12month"}[horizon_label]
    calendar_key = f"show_earnings_calendar_{ticker}_{horizon}"
    if st.button("Load earnings calendar", key=f"earnings_calendar_button_{ticker}_{horizon}", type="primary"):
        st.session_state[calendar_key] = True

    if not st.session_state.get(calendar_key):
        st.info("Click the button to fetch upcoming earnings dates for the selected ticker.")
        return

    with st.spinner("Loading earnings calendar..."):
        calendar = get_earnings_calendar(ticker, horizon)

    source = calendar.attrs.get("source", "Unknown")
    st.caption(f"Source: {source} · Horizon: {calendar.attrs.get('horizon', horizon)}")
    if source.startswith("Mock"):
        st.warning(
            "Alpha Vantage API key is not configured. Add ALPHA_VANTAGE_API_KEY to `.env` and restart Streamlit."
        )
    elif calendar.attrs.get("error"):
        st.warning(f"Alpha Vantage calendar request failed: {calendar.attrs['error']}")
    elif calendar.empty:
        st.info(
            calendar.attrs.get(
                "empty_reason",
                f"Alpha Vantage returned no upcoming earnings dates for {ticker} in this horizon.",
            )
        )

    next_release = calendar.iloc[0].to_dict() if not calendar.empty else {}
    cols = st.columns(4)
    with cols[0]:
        st.metric("Next Report Date", next_release.get("Report Date", "-"))
    with cols[1]:
        st.metric("Fiscal Period Ending", next_release.get("Fiscal Date Ending", "-"))
    with cols[2]:
        st.metric("EPS Estimate", next_release.get("EPS Estimate", "-"))
    with cols[3]:
        st.metric("Currency", next_release.get("Currency", "-"))

    st.dataframe(calendar, use_container_width=True, hide_index=True)


def _format_eps(value: object) -> str:
    """Format optional EPS values."""
    return "-" if value is None else f"{float(value):.2f}"


def _format_percent_value(value: object) -> str:
    """Format optional percentage values."""
    return "-" if value is None else f"{float(value):+.2f}%"


def _render_financial_health_analysis(ticker: str) -> None:
    """Render on-demand written financial health assessment."""
    analysis_key = f"show_fundamental_health_analysis_{ticker}"
    if st.button("Generate financial health analysis", key=f"fundamental_health_button_{ticker}", type="primary"):
        st.session_state[analysis_key] = True

    if st.session_state.get(analysis_key):
        with st.expander("Professional financial health analysis", expanded=True):
            with st.spinner("Analyzing financial statements..."):
                analysis = get_written_fundamental_analysis(ticker)
                health_label = get_fundamental_health_label(analysis)
                _render_health_badge(health_label)
                st.markdown(analysis)


def _render_health_badge(health_label: str) -> None:
    """Render color-coded overall fundamental health."""
    color = _health_color(health_label)
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
            <span style="display:inline-block;background:{color};color:white;border-radius:999px;padding:6px 14px;font-size:14px;font-weight:700;">
                Overall Fundamental Health: {health_label}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _health_color(health_label: str) -> str:
    """Return badge color for health label."""
    if health_label == "Strong":
        return "#1a7f4e"
    if health_label.startswith("Adequate"):
        return "#c9a227"
    if health_label.startswith("Weak"):
        return "#c0392b"
    return "#5a6a7a"


def _valuation(ticker: str) -> None:
    """Valuation ratios comparison."""
    ratios = get_valuation_ratios(ticker)
    st.dataframe(ratios, use_container_width=True, hide_index=True)
    render_todo_callout("Add peer comparison and historical ratio trends.")


def _growth() -> None:
    """Growth metrics table."""
    st.dataframe(get_growth_metrics(), use_container_width=True, hide_index=True)
    render_todo_callout("Compute growth rates from quarterly financial statements.")


def _profitability() -> None:
    """Profitability metrics table."""
    st.dataframe(get_profitability_metrics(), use_container_width=True, hide_index=True)
    render_todo_callout("Derive margins and returns from live fundamental data.")


def _debt_liquidity() -> None:
    """Debt and liquidity metrics."""
    st.dataframe(get_debt_liquidity(), use_container_width=True, hide_index=True)
    render_todo_callout("Add credit rating and covenant analysis modules.")
