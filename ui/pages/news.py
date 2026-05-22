"""News & Sentiment page."""

import streamlit as st

from ui.components.cards import render_todo_callout
from ui.components.charts import sentiment_gauge
from ui.components.page_router import render_ticker_submenu_page
from ai.market_interpreter import summarize_news_and_sentiment
from services.news_data_service import (
    get_key_risks,
    get_market_catalysts,
    get_news_items,
    get_sentiment_scores,
)


def render(submenu: str) -> None:
    """Route news and sentiment submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Latest news": lambda: _latest_news(ticker),
        "Sentiment score": _sentiment_score,
        "Key risks": _key_risks,
        "Market catalysts": _catalysts,
        "AI summary placeholder": lambda: _ai_summary(ticker),
    }
    render_ticker_submenu_page(
        "News & Sentiment",
        submenu,
        handlers,
        default_handler=lambda: _latest_news(ticker),
    )


def _latest_news(ticker: str) -> None:
    """News headlines table."""
    news = get_news_items(ticker)
    st.dataframe(news, use_container_width=True, hide_index=True)
    render_todo_callout("Integrate news API with filtering by ticker and date range.")


def _sentiment_score() -> None:
    """Sentiment breakdown and gauge."""
    scores = get_sentiment_scores()
    col1, col2 = st.columns([1, 2])
    with col1:
        composite = scores.loc[scores["Source"] == "Composite", "Score"].iloc[0]
        st.plotly_chart(sentiment_gauge(composite), use_container_width=True)
    with col2:
        st.dataframe(scores, use_container_width=True, hide_index=True)
    render_todo_callout("Implement NLP sentiment scoring on news and social feeds.")


def _key_risks() -> None:
    """Key risks bullet list."""
    st.markdown("**Identified Risks (Mock)**")
    for risk in get_key_risks():
        st.markdown(f"- {risk}")
    render_todo_callout("Extract risks from filings and news via NLP pipeline.")


def _catalysts() -> None:
    """Market catalysts list."""
    st.markdown("**Upcoming Catalysts (Mock)**")
    for cat in get_market_catalysts():
        st.markdown(f"- {cat}")
    render_todo_callout("Link to earnings calendar and corporate event data.")


def _ai_summary(ticker: str) -> None:
    """AI summary placeholder panel."""
    st.markdown(summarize_news_and_sentiment(ticker))
    render_todo_callout("Connect LLM to summarize news, filings, and analyst notes.")
