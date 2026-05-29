"""User settings persistence and provider resolution."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from data import disk_cache
from data.providers import alpha_vantage_provider
from utils.config import PROJECT_ROOT, get_alpha_vantage_api_key
from utils.constants import COLORS

SETTINGS_FILE = PROJECT_ROOT / "data" / "user_settings.json"
_SETTINGS_CACHE: dict[str, Any] | None = None

PROVIDER_AUTO = "auto"
PROVIDER_ALPHA_VANTAGE = "alpha_vantage"
PROVIDER_MOCK = "mock"

MARKET_PROVIDER_OPTIONS = [PROVIDER_AUTO, PROVIDER_ALPHA_VANTAGE, PROVIDER_MOCK]
FUNDAMENTALS_PROVIDER_OPTIONS = [PROVIDER_AUTO, PROVIDER_ALPHA_VANTAGE, PROVIDER_MOCK]
NEWS_PROVIDER_OPTIONS = [PROVIDER_AUTO, PROVIDER_ALPHA_VANTAGE, PROVIDER_MOCK]

THEME_OPTIONS = {
    "executive_blue": "Executive Blue (default)",
    "dark_mode": "Dark Mode",
    "high_contrast": "High Contrast",
}

THEME_PALETTES: dict[str, dict[str, str]] = {
    "executive_blue": COLORS,
    "dark_mode": {
        "primary": "#dbeafe",
        "secondary": "#60a5fa",
        "accent": "#fbbf24",
        "positive": "#34d399",
        "negative": "#f87171",
        "neutral": "#94a3b8",
        "background": "#0f172a",
        "card_border": "#334155",
        "text_muted": "#94a3b8",
    },
    "high_contrast": {
        "primary": "#000000",
        "secondary": "#1d4ed8",
        "accent": "#f59e0b",
        "positive": "#047857",
        "negative": "#b91c1c",
        "neutral": "#374151",
        "background": "#ffffff",
        "card_border": "#111827",
        "text_muted": "#374151",
    },
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "market_provider": PROVIDER_AUTO,
    "fundamentals_provider": PROVIDER_AUTO,
    "news_provider": PROVIDER_AUTO,
    "theme_id": "executive_blue",
    "chart_style": "plotly_default",
    "compact_layout": False,
    "default_timeframe": "1M",
    "currency": "USD",
    "chart_height_px": 400,
    "show_report_disclaimer": True,
    "disk_cache_enabled": True,
}

# TTL seconds by Alpha Vantage function name.
FUNCTION_CACHE_TTL_SECONDS: dict[str, int] = {
    "GLOBAL_QUOTE": 300,
    "TOP_GAINERS_LOSERS": 300,
    "INDEX_DATA": 900,
    "RSI": 86_400,
    "MACD": 86_400,
    "ADX": 86_400,
    "STOCH": 86_400,
    "BBANDS": 86_400,
    "NEWS_SENTIMENT": 21_600,
    "INSIDER_TRANSACTIONS": 86_400,
    "OVERVIEW": 7_776_000,
    "INCOME_STATEMENT": 7_776_000,
    "BALANCE_SHEET": 7_776_000,
    "CASH_FLOW": 7_776_000,
    "EARNINGS": 7_776_000,
    "EARNINGS_CALENDAR": 86_400,
    "HISTORICAL_OPTIONS": 3_600,
    "LISTING_STATUS": 86_400,
}


def load_user_settings() -> dict[str, Any]:
    """Load settings from disk merged with defaults."""
    settings = deepcopy(DEFAULT_SETTINGS)
    if not SETTINGS_FILE.exists():
        return settings
    try:
        stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings
    if isinstance(stored, dict):
        settings.update({key: stored[key] for key in settings if key in stored})
    return settings


def save_user_settings(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into settings and persist to disk."""
    global _SETTINGS_CACHE
    current = load_user_settings()
    current.update(updates)
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    _SETTINGS_CACHE = current
    return current


def get_user_settings() -> dict[str, Any]:
    """Return cached user settings without touching Streamlit on hot paths."""
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is None:
        _SETTINGS_CACHE = load_user_settings()
    return _SETTINGS_CACHE


def sync_user_settings_to_session(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Store settings in Streamlit session state."""
    global _SETTINGS_CACHE
    import streamlit as st

    resolved = settings or load_user_settings()
    _SETTINGS_CACHE = resolved
    st.session_state.user_settings = resolved
    return resolved


def is_disk_cache_enabled() -> bool:
    """Return whether disk cache reads/writes are enabled."""
    return bool(get_user_settings().get("disk_cache_enabled", True))


def get_cache_ttl_for_function(function_name: str) -> int:
    """Return TTL for an Alpha Vantage endpoint."""
    if function_name.startswith("TIME_SERIES"):
        return 86_400
    return FUNCTION_CACHE_TTL_SECONDS.get(function_name, 300)


def get_theme_colors(theme_id: str | None = None) -> dict[str, str]:
    """Return color palette for the active theme."""
    active = theme_id or get_user_settings().get("theme_id", "executive_blue")
    return THEME_PALETTES.get(active, COLORS)


def _resolve_provider_choice(choice: str, domain_label: str) -> str:
    """Resolve auto/mock/alpha_vantage to an effective provider label."""
    if choice == PROVIDER_MOCK:
        return "Mock data"
    if choice == PROVIDER_ALPHA_VANTAGE:
        return "Alpha Vantage" if alpha_vantage_provider.is_configured() else "Alpha Vantage (key missing)"
    if alpha_vantage_provider.is_configured():
        return "Alpha Vantage"
    return "Mock data"


def get_effective_market_provider_label() -> str:
    """Return active market data provider label."""
    return _resolve_provider_choice(get_user_settings().get("market_provider", PROVIDER_AUTO), "market")


def get_effective_fundamentals_provider_label() -> str:
    """Return active fundamentals provider label."""
    return _resolve_provider_choice(
        get_user_settings().get("fundamentals_provider", PROVIDER_AUTO),
        "fundamentals",
    )


def get_effective_news_provider_label() -> str:
    """Return active news provider label."""
    return _resolve_provider_choice(get_user_settings().get("news_provider", PROVIDER_AUTO), "news")


def should_use_alpha_vantage(domain: str) -> bool:
    """Return True when Alpha Vantage should be used for a data domain."""
    settings = get_user_settings()
    key = {
        "market": "market_provider",
        "fundamentals": "fundamentals_provider",
        "news": "news_provider",
    }.get(domain, "market_provider")
    choice = settings.get(key, PROVIDER_AUTO)
    if choice == PROVIDER_MOCK:
        return False
    if choice == PROVIDER_ALPHA_VANTAGE:
        return alpha_vantage_provider.is_configured()
    return alpha_vantage_provider.is_configured()


def get_api_key_status() -> list[dict[str, str]]:
    """Return read-only API key configuration status."""
    av_key = get_alpha_vantage_api_key()
    return [
        {
            "Provider": "Alpha Vantage (market, fundamentals, news, options)",
            "Status": "Configured" if av_key else "Missing",
            "Variable": "ALPHA_VANTAGE_API_KEY",
        },
        {
            "Provider": "News (future alternate)",
            "Status": "Uses Alpha Vantage when configured",
            "Variable": "—",
        },
        {
            "Provider": "LLM (future reports)",
            "Status": "Not configured",
            "Variable": "LLM_API_KEY (future)",
        },
    ]


def clear_application_cache() -> dict[str, int]:
    """Clear disk and in-memory provider caches."""
    from services import market_data_service, options_data_service

    from data import snapshot_store

    disk_removed = disk_cache.clear_all()
    snapshots_removed = snapshot_store.clear_all_snapshots()
    alpha_vantage_provider.clear_caches()
    market_data_service.clear_sector_caches()
    options_data_service.clear_options_cache()
    return {"disk_files_removed": disk_removed, "snapshots_removed": snapshots_removed}
