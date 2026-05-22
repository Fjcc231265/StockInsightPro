"""Settings page."""

import streamlit as st

from ui.components.cards import render_todo_callout
from ui.components.page_router import render_submenu_page


def render(submenu: str) -> None:
    """Route settings submenu."""
    handlers = {
        "API keys placeholder": _api_keys,
        "Data source selection": _data_sources,
        "Theme options": _theme_options,
        "User preferences": _user_preferences,
    }
    render_submenu_page(
        "Settings",
        submenu,
        handlers,
        default_handler=_api_keys,
    )


def _api_keys() -> None:
    """API key configuration placeholders."""
    st.markdown("**API Keys (Placeholder)**")
    st.text_input("Market Data API Key", type="password", placeholder="sk-xxxxxxxx", key="api_market")
    st.text_input("News API Key", type="password", placeholder="sk-xxxxxxxx", key="api_news")
    st.text_input("LLM API Key", type="password", placeholder="sk-xxxxxxxx", key="api_llm")
    if st.button("Save Keys (Mock)"):
        st.success("Keys saved to session (not persisted).")
    render_todo_callout("Store encrypted API keys in secure vault / env file.")


def _data_sources() -> None:
    """Data provider selection."""
    st.markdown("**Data Source Selection**")
    st.selectbox("Primary market data", ["Yahoo Finance (mock)", "Alpha Vantage", "Polygon.io", "IEX Cloud"])
    st.selectbox("Fundamentals provider", ["Mock", "Financial Modeling Prep", "Intrinio"])
    st.selectbox("News provider", ["Mock", "NewsAPI", "Benzinga"])
    render_todo_callout("Wire provider adapters with failover and rate limiting.")


def _theme_options() -> None:
    """Theme customization placeholders."""
    st.markdown("**Theme Options**")
    st.selectbox("Color theme", ["Executive Blue (default)", "Dark Mode", "High Contrast"])
    st.selectbox("Chart style", ["Plotly Default", "Minimal", "Trading Terminal"])
    st.toggle("Compact layout", value=False)
    render_todo_callout("Apply theme tokens across components and Plotly charts.")


def _user_preferences() -> None:
    """User preference settings."""
    st.markdown("**User Preferences**")
    st.selectbox("Default timeframe", ["1D", "5D", "1M", "3M", "1Y", "5Y"])
    st.selectbox("Currency display", ["USD", "EUR", "GBP"])
    st.number_input("Default chart height (px)", value=400, min_value=250, max_value=800)
    st.checkbox("Show disclaimer on reports", value=True)
    if st.button("Save Preferences (Mock)"):
        st.success("Preferences saved (session only).")
    render_todo_callout("Persist user profile to database with auth integration.")
