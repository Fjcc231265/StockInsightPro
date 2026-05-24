"""News and sentiment data service facade."""

from __future__ import annotations

import pandas as pd

from data import mock_data
from data.providers import alpha_vantage_provider


def get_news_items(ticker: str, limit: int = 8) -> pd.DataFrame:
    """Return latest news items."""
    if alpha_vantage_provider.is_configured():
        try:
            return alpha_vantage_provider.get_news_sentiment(ticker, limit)
        except alpha_vantage_provider.AlphaVantageError:
            pass

    news = mock_data.get_news_items(ticker, limit)
    news.attrs["source"] = "Mock fallback"
    return news


def get_sentiment_scores() -> pd.DataFrame:
    """Return sentiment source scores."""
    # TODO: Replace with NLP sentiment pipeline output.
    return mock_data.get_sentiment_scores()


def get_news_sentiment_summary(ticker: str, limit: int = 20) -> dict:
    """Return aggregate sentiment metrics from recent ticker news."""
    news = get_news_items(ticker, limit)
    if news.empty:
        return {
            "source": news.attrs.get("source", "Unknown"),
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "composite": 50,
        }

    counts = news["Sentiment"].value_counts()
    score_map = {"Positive": 80, "Neutral": 50, "Negative": 20}
    scored = news["Sentiment"].map(score_map).fillna(50)
    return {
        "source": news.attrs.get("source", "Unknown"),
        "positive": int(counts.get("Positive", 0)),
        "neutral": int(counts.get("Neutral", 0)),
        "negative": int(counts.get("Negative", 0)),
        "composite": round(float(scored.mean()), 2),
    }


def get_key_risks() -> list[str]:
    """Return key risk bullets."""
    return mock_data.get_key_risks()


def get_market_catalysts() -> list[str]:
    """Return market catalyst bullets."""
    return mock_data.get_market_catalysts()
