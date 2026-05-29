"""Settings page."""

from __future__ import annotations

import streamlit as st

from data import disk_cache
from services.settings_service import (
    FUNDAMENTALS_PROVIDER_OPTIONS,
    MARKET_PROVIDER_OPTIONS,
    NEWS_PROVIDER_OPTIONS,
    PROVIDER_ALPHA_VANTAGE,
    PROVIDER_AUTO,
    PROVIDER_MOCK,
    THEME_OPTIONS,
    clear_application_cache,
    get_api_key_status,
    get_effective_fundamentals_provider_label,
    get_effective_market_provider_label,
    get_effective_news_provider_label,
    load_user_settings,
    save_user_settings,
    sync_user_settings_to_session,
)
from ui.components.page_router import render_submenu_page
from utils.config import ENV_FILE, PROJECT_ROOT


def render(submenu: str) -> None:
    """Route settings submenu."""
    sync_user_settings_to_session()
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
    """Read-only API key status and secure setup instructions."""
    st.markdown("**API Keys**")
    st.info(
        "API keys are **not** stored in this app or in settings files. "
        "Set them in your environment or `.env` file and restart Streamlit."
    )
    st.dataframe(
        get_api_key_status(),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("**Setup**")
    st.code(
        f"# {ENV_FILE}\nALPHA_VANTAGE_API_KEY=your_key_here",
        language="bash",
    )
    st.caption(f"Example file: `{PROJECT_ROOT / '.env.example'}`")


def _data_sources() -> None:
    """Data provider selection and cache controls."""
    settings = st.session_state.user_settings
    st.markdown("**Data Source Selection**")
    st.caption(
        f"Active providers — Market: **{get_effective_market_provider_label()}** · "
        f"Fundamentals: **{get_effective_fundamentals_provider_label()}** · "
        f"News: **{get_effective_news_provider_label()}**"
    )

    market = st.selectbox(
        "Market data",
        MARKET_PROVIDER_OPTIONS,
        index=MARKET_PROVIDER_OPTIONS.index(settings.get("market_provider", PROVIDER_AUTO)),
        format_func=_format_provider,
    )
    fundamentals = st.selectbox(
        "Fundamentals",
        FUNDAMENTALS_PROVIDER_OPTIONS,
        index=FUNDAMENTALS_PROVIDER_OPTIONS.index(settings.get("fundamentals_provider", PROVIDER_AUTO)),
        format_func=_format_provider,
    )
    news = st.selectbox(
        "News & sentiment",
        NEWS_PROVIDER_OPTIONS,
        index=NEWS_PROVIDER_OPTIONS.index(settings.get("news_provider", PROVIDER_AUTO)),
        format_func=_format_provider,
    )
    disk_cache_enabled = st.toggle(
        "Use disk cache for Alpha Vantage responses",
        value=bool(settings.get("disk_cache_enabled", True)),
        help="Speeds up menu changes and restarts by reusing recent API responses from data/cache/.",
    )

    st.markdown("**Cache**")
    cache_mb = disk_cache.cache_size_bytes() / (1024 * 1024)
    st.caption(
        f"Disk cache: **{disk_cache.cache_file_count()}** files · **{cache_mb:.2f} MB** in `data/cache/`"
    )
    if st.button("Clear all application cache", type="secondary"):
        result = clear_application_cache()
        st.success(f"Cleared cache ({result['disk_files_removed']} disk files removed).")
        st.rerun()

    if st.button("Save data source settings", type="primary"):
        updated = save_user_settings(
            {
                "market_provider": market,
                "fundamentals_provider": fundamentals,
                "news_provider": news,
                "disk_cache_enabled": disk_cache_enabled,
            }
        )
        sync_user_settings_to_session(updated)
        st.success("Data source settings saved.")
        st.rerun()


def _theme_options() -> None:
    """Theme customization."""
    settings = st.session_state.user_settings
    theme_ids = list(THEME_OPTIONS.keys())
    current_theme = settings.get("theme_id", "executive_blue")
    theme_id = st.selectbox(
        "Color theme",
        theme_ids,
        index=theme_ids.index(current_theme) if current_theme in theme_ids else 0,
        format_func=lambda value: THEME_OPTIONS[value],
    )
    chart_style = st.selectbox(
        "Chart style",
        ["plotly_default", "minimal", "trading_terminal"],
        index=["plotly_default", "minimal", "trading_terminal"].index(
            settings.get("chart_style", "plotly_default")
        ),
    )
    compact_layout = st.toggle("Compact layout", value=bool(settings.get("compact_layout", False)))

    if st.button("Save theme", type="primary"):
        updated = save_user_settings(
            {
                "theme_id": theme_id,
                "chart_style": chart_style,
                "compact_layout": compact_layout,
            }
        )
        sync_user_settings_to_session(updated)
        st.success("Theme saved. Refresh the page if colors do not update immediately.")
        st.rerun()


def _user_preferences() -> None:
    """User preference settings."""
    settings = st.session_state.user_settings
    timeframe_options = ["1D", "5D", "1M", "3M", "1Y", "5Y"]
    default_timeframe = settings.get("default_timeframe", "1M")
    default_timeframe = st.selectbox(
        "Default timeframe",
        timeframe_options,
        index=timeframe_options.index(default_timeframe) if default_timeframe in timeframe_options else 2,
    )
    currency_options = ["USD", "EUR", "GBP"]
    currency = settings.get("currency", "USD")
    currency = st.selectbox(
        "Currency display",
        currency_options,
        index=currency_options.index(currency) if currency in currency_options else 0,
    )
    chart_height = st.number_input(
        "Default chart height (px)",
        value=int(settings.get("chart_height_px", 400)),
        min_value=250,
        max_value=800,
    )
    show_disclaimer = st.checkbox(
        "Show disclaimer on reports",
        value=bool(settings.get("show_report_disclaimer", True)),
    )

    if st.button("Save preferences", type="primary"):
        updated = save_user_settings(
            {
                "default_timeframe": default_timeframe,
                "currency": currency,
                "chart_height_px": int(chart_height),
                "show_report_disclaimer": show_disclaimer,
            }
        )
        sync_user_settings_to_session(updated)
        st.success("Preferences saved to disk.")
        st.rerun()


def _format_provider(value: str) -> str:
    """Human-readable provider label."""
    mapping = {
        PROVIDER_AUTO: "Auto (Alpha Vantage when configured, else mock)",
        PROVIDER_ALPHA_VANTAGE: "Alpha Vantage only",
        PROVIDER_MOCK: "Mock data only",
    }
    return mapping.get(value, value)
