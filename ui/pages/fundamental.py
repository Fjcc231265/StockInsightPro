"""Fundamental Analysis page with submenu views."""

import streamlit as st

from ui.components.cards import render_todo_callout
from ui.components.page_router import render_ticker_submenu_page
from services.fundamental_data_service import (
    get_debt_liquidity,
    get_financial_statement,
    get_growth_metrics,
    get_income_statement_margins,
    get_profitability_metrics,
    get_statement_variation,
    get_valuation_ratios,
)


def render(submenu: str) -> None:
    """Route fundamental analysis submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Income statement": lambda: _statement("income", ticker),
        "Balance sheet": lambda: _statement("balance", ticker),
        "Cash flow statement": lambda: _statement("cashflow", ticker),
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
    if source.startswith("Mock"):
        st.warning("Live Alpha Vantage fundamentals unavailable right now. Showing mock fallback values.")
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
