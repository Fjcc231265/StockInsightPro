"""Fundamental analysis data service facade."""

from __future__ import annotations

import pandas as pd

from data import mock_data


def get_financial_statement(statement_type: str, ticker: str) -> pd.DataFrame:
    """Return income, balance sheet, or cash flow statement."""
    # TODO: Replace with SEC/provider-backed financial statements.
    return mock_data.get_financial_statement(statement_type, ticker)


def get_valuation_ratios(ticker: str) -> pd.DataFrame:
    """Return valuation ratio table."""
    # TODO: Replace with valuation analytics engine.
    return mock_data.get_valuation_ratios(ticker)


def get_growth_metrics() -> pd.DataFrame:
    """Return growth metrics."""
    return mock_data.get_growth_metrics()


def get_profitability_metrics() -> pd.DataFrame:
    """Return profitability metrics."""
    return mock_data.get_profitability_metrics()


def get_debt_liquidity() -> pd.DataFrame:
    """Return debt and liquidity metrics."""
    return mock_data.get_debt_liquidity()
