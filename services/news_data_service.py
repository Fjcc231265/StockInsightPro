"""News and sentiment data service facade."""

from __future__ import annotations

import pandas as pd

from data import mock_data


def get_news_items(ticker: str) -> pd.DataFrame:
    """Return latest news items."""
    # TODO: Replace with news provider integration.
    return mock_data.get_news_items(ticker)


def get_sentiment_scores() -> pd.DataFrame:
    """Return sentiment source scores."""
    # TODO: Replace with NLP sentiment pipeline output.
    return mock_data.get_sentiment_scores()


def get_key_risks() -> list[str]:
    """Return key risk bullets."""
    return mock_data.get_key_risks()


def get_market_catalysts() -> list[str]:
    """Return market catalyst bullets."""
    return mock_data.get_market_catalysts()
