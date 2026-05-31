"""News & Sentiment page."""

import streamlit as st

from ui.components.charts import sentiment_gauge
from ui.components.page_router import render_ticker_submenu_page
from ai.market_interpreter import summarize_news_and_sentiment
from services.news_data_service import (
    get_insider_transactions,
    get_key_risks,
    get_market_catalysts,
    get_news_items,
    get_news_sentiment_summary,
)


def render(submenu: str) -> None:
    """Route news and sentiment submenu."""
    ticker = st.session_state.selected_ticker
    handlers = {
        "Latest news": lambda: _latest_news(ticker),
        "Sentiment score": _sentiment_score,
        "Insider transactions": lambda: _insider_transactions(ticker),
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
    """Recent news with sentiment badges."""
    limit = st.slider("Number of recent headlines", min_value=5, max_value=30, value=12, step=5)
    news = get_news_items(ticker, limit=limit)
    summary = get_news_sentiment_summary(ticker, limit=limit)

    st.caption(f"Source: {news.attrs.get('source', summary['source'])}")
    _render_sentiment_summary(summary)

    for _, row in news.iterrows():
        _render_news_card(row)


def _sentiment_score() -> None:
    """Sentiment breakdown and gauge."""
    ticker = st.session_state.selected_ticker
    summary = get_news_sentiment_summary(ticker, limit=20)
    live_scores = [
        {"Source": "Recent News Composite", "Score": summary["composite"], "Trend": _sentiment_trend(summary["composite"])},
        {"Source": "Positive Headlines", "Score": summary["positive"], "Trend": "count"},
        {"Source": "Neutral Headlines", "Score": summary["neutral"], "Trend": "count"},
        {"Source": "Negative Headlines", "Score": summary["negative"], "Trend": "count"},
    ]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(sentiment_gauge(summary["composite"]), use_container_width=True)
    with col2:
        st.caption(f"Source: {summary['source']}")
        st.dataframe(live_scores, use_container_width=True, hide_index=True)


def _insider_transactions(ticker: str) -> None:
    """Recent insider transactions from Alpha Vantage."""
    st.markdown("**Insider Transactions**")
    st.caption("Uses Alpha Vantage INSIDER_TRANSACTIONS when configured, with mock fallback if live data is unavailable.")

    limit = st.slider("Number of insider transactions", min_value=10, max_value=100, value=50, step=10)
    transactions_key = f"show_insider_transactions_{ticker}_{limit}"
    if st.button("Load insider transactions", key=f"insider_transactions_button_{ticker}_{limit}", type="primary"):
        st.session_state[transactions_key] = True

    if not st.session_state.get(transactions_key):
        st.info("Click the button to fetch recent insider transactions for the selected ticker.")
        return

    with st.spinner("Loading insider transactions..."):
        transactions = get_insider_transactions(ticker, limit)

    source = transactions.attrs.get("source", "Unknown")
    st.caption(f"Source: {source}")
    if source.startswith("Mock"):
        st.warning("Live Alpha Vantage insider transactions unavailable right now. Showing mock fallback values.")

    if transactions.empty:
        st.info(f"No insider transactions returned for {ticker}.")
        return

    _render_insider_summary(transactions)
    st.dataframe(transactions, use_container_width=True, hide_index=True)


def _render_insider_summary(transactions) -> None:
    """Render acquisition/disposal counts for insider transactions."""
    type_counts = transactions["Type"].value_counts()
    cols = st.columns(3)
    with cols[0]:
        st.metric("Total Transactions", len(transactions))
    with cols[1]:
        st.metric("Acquisitions", int(type_counts.get("Acquisition", 0)))
    with cols[2]:
        st.metric("Disposals", int(type_counts.get("Disposal", 0)))


def _key_risks() -> None:
    """Key risks bullet list."""
    st.markdown("**Identified Risks (Mock)**")
    for risk in get_key_risks():
        st.markdown(f"- {risk}")


def _catalysts() -> None:
    """Market catalysts list."""
    st.markdown("**Upcoming Catalysts (Mock)**")
    for cat in get_market_catalysts():
        st.markdown(f"- {cat}")


def _ai_summary(ticker: str) -> None:
    """AI summary placeholder panel."""
    st.markdown(summarize_news_and_sentiment(ticker))


def _render_news_card(row) -> None:
    """Render one recent news item."""
    sentiment = row.get("Sentiment", "Neutral")
    color = _sentiment_color(sentiment)
    headline = row.get("Headline", "Untitled")
    url = row.get("URL", "")
    headline_html = f'<a href="{url}" target="_blank">{headline}</a>' if url else headline
    score = row.get("Score")
    score_text = "" if score is None else f" · Score: {score}"
    st.markdown(
        f"""
        <div style="border:1px solid #d8dee6;border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#ffffff;">
            <span style="display:inline-block;background:{color};color:white;border-radius:999px;padding:3px 11px;font-size:12px;font-weight:700;">
                {sentiment}
            </span>
            <span style="font-size:12px;color:#6b7c93;margin-left:8px;">
                {row.get('Published', row.get('Date', 'Unknown'))} · {row.get('Source', 'Unknown')}{score_text}
            </span>
            <div style="margin-top:7px;font-weight:650;line-height:1.35;">{headline_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _sentiment_color(sentiment: str) -> str:
    """Return color for sentiment badge."""
    if sentiment == "Positive":
        return "#1a7f4e"
    if sentiment == "Negative":
        return "#c0392b"
    return "#c9a227"


def _sentiment_trend(score: float) -> str:
    """Return simple trend label for sentiment score."""
    if score >= 65:
        return "Positive"
    if score <= 35:
        return "Negative"
    return "Neutral"


def _render_sentiment_summary(summary: dict) -> None:
    """Render green/yellow/red sentiment summary badges."""
    composite_label = _sentiment_trend(summary["composite"])
    cols = st.columns(4)
    with cols[0]:
        _render_sentiment_tile("Composite", f"{summary['composite']:.0f}/100", composite_label)
    with cols[1]:
        _render_sentiment_tile("Positive", str(summary["positive"]), "Positive")
    with cols[2]:
        _render_sentiment_tile("Neutral", str(summary["neutral"]), "Neutral")
    with cols[3]:
        _render_sentiment_tile("Negative", str(summary["negative"]), "Negative")


def _render_sentiment_tile(title: str, value: str, sentiment: str) -> None:
    """Render one sentiment summary tile."""
    color = _sentiment_color(sentiment)
    st.markdown(
        f"""
        <div style="border:1px solid #d8dee6;border-radius:10px;padding:10px 12px;background:white;margin-bottom:12px;">
            <div style="font-size:12px;color:#6b7c93;font-weight:700;text-transform:uppercase;">{title}</div>
            <div style="font-size:22px;font-weight:800;color:{color};line-height:1.4;">{value}</div>
            <span style="display:inline-block;background:{color};color:white;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:700;">
                {sentiment}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
