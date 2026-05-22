"""AI interpretation facade for future agent workflows.

The UI calls this module for narrative summaries. For now, responses are
deterministic placeholders; later they can call local or cloud AI agents.
"""

from __future__ import annotations

from data import mock_data


def summarize_news_and_sentiment(ticker: str) -> str:
    """Return placeholder news/sentiment interpretation."""
    # TODO: Replace with AI agent that uses news, sentiment, filings, and price context.
    return mock_data.get_ai_summary_placeholder(ticker)


def summarize_options_intelligence(ticker: str) -> str:
    """Return placeholder options-market interpretation."""
    # TODO: Replace with options-aware AI agent using chain, flow, greeks, and event context.
    return mock_data.get_options_ai_conclusion(ticker)
