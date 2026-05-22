"""Fundamental Analysis page with submenu views."""

import streamlit as st

from components.cards import render_quote_cards, render_section_header, render_todo_callout
from data.mock_data import (
    get_debt_liquidity,
    get_financial_statement,
    get_growth_metrics,
    get_profitability_metrics,
    get_quote_summary,
    get_valuation_ratios,
)


def render(submenu: str) -> None:
    """Route fundamental analysis submenu."""
    ticker = st.session_state.selected_ticker
    quote = get_quote_summary(ticker)
    render_section_header("Fundamental Analysis", f"View: {submenu} · {ticker}")
    render_quote_cards(quote)
    st.divider()

    handlers = {
        "Income statement": lambda: _statement("income", ticker),
        "Balance sheet": lambda: _statement("balance", ticker),
        "Cash flow statement": lambda: _statement("cashflow", ticker),
        "Valuation ratios": lambda: _valuation(ticker),
        "Growth metrics": _growth,
        "Profitability metrics": _profitability,
        "Debt and liquidity": _debt_liquidity,
    }
    handlers.get(submenu, lambda: _statement("income", ticker))()


def _statement(stmt_type: str, ticker: str) -> None:
    """Render financial statement table."""
    label_map = {
        "income": "Income Statement",
        "balance": "Balance Sheet",
        "cashflow": "Cash Flow Statement",
    }
    df = get_financial_statement(stmt_type, ticker)
    st.markdown(f"**{label_map[stmt_type]}** (USD millions, mock)")
    st.dataframe(df, use_container_width=True)
    render_todo_callout(f"Fetch real {label_map[stmt_type].lower()} from SEC filings / financial API.")


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
