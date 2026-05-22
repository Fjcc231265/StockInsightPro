"""Options intelligence data service facade."""

from __future__ import annotations

import pandas as pd

from data import mock_data


def get_options_chain(ticker: str) -> pd.DataFrame:
    """Return option chain snapshot."""
    # TODO: Replace with live options chain provider.
    return mock_data.get_options_chain(ticker)


def get_options_kpis(ticker: str) -> dict:
    """Return options summary KPIs."""
    # TODO: Replace with analytics.options engine summary.
    return mock_data.get_options_kpis(ticker)


def get_open_interest_by_strike(ticker: str) -> pd.DataFrame:
    """Return call/put open interest by strike."""
    return mock_data.get_open_interest_by_strike(ticker)


def get_put_call_ratio_history() -> pd.DataFrame:
    """Return put/call ratio history."""
    return mock_data.get_put_call_ratio_history()


def get_iv_term_structure(ticker: str) -> pd.DataFrame:
    """Return IV term structure."""
    return mock_data.get_iv_term_structure(ticker)


def get_iv_rank_history() -> pd.DataFrame:
    """Return IV rank history."""
    return mock_data.get_iv_rank_history()


def get_gamma_exposure(ticker: str) -> pd.DataFrame:
    """Return gamma exposure by strike."""
    return mock_data.get_gamma_exposure(ticker)


def get_dealer_positioning() -> pd.DataFrame:
    """Return dealer positioning summary."""
    return mock_data.get_dealer_positioning()


def get_options_flow() -> pd.DataFrame:
    """Return options flow tape."""
    return mock_data.get_options_flow()
