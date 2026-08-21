"""Runtime configuration helpers.

Secrets are read in this order:
1. Process environment variables
2. Local `.env` file (Mac only; never uploaded)
3. Streamlit Cloud Secrets (`st.secrets`)

The `.env` file and `.streamlit/secrets.toml` must never be committed.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
_DOTENV_LOADED = False
_STREAMLIT_SECRETS_LOADED = False


def load_dotenv_if_present() -> None:
    """Load simple KEY=VALUE pairs from `.env` into process environment."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_streamlit_secrets_if_present() -> None:
    """Copy Streamlit Cloud / local secrets.toml values into environment variables.

    On Streamlit Cloud you paste secrets in the website Settings → Secrets.
    Locally you can keep them in `.streamlit/secrets.toml` (also git-ignored).
    """
    global _STREAMLIT_SECRETS_LOADED
    if _STREAMLIT_SECRETS_LOADED:
        return
    _STREAMLIT_SECRETS_LOADED = True

    try:
        import streamlit as st
    except Exception:
        return

    try:
        secrets = st.secrets
    except Exception:
        return

    for key in ("ALPHA_VANTAGE_API_KEY", "APP_PASSWORD"):
        if key in os.environ and os.environ.get(key, "").strip():
            continue
        try:
            value = secrets.get(key)
        except Exception:
            value = None
        if value is None:
            continue
        text = str(value).strip()
        if text:
            os.environ[key] = text


def load_runtime_secrets() -> None:
    """Load local .env first, then Streamlit secrets (cloud or local secrets.toml)."""
    load_dotenv_if_present()
    load_streamlit_secrets_if_present()


def get_alpha_vantage_api_key() -> str | None:
    """Return configured Alpha Vantage API key, if available."""
    load_runtime_secrets()
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key or key in {"your_key_here", "replace_with_your_alpha_vantage_key"}:
        return None
    return key


def get_app_password() -> str | None:
    """Return the shared app password used to open StockInsightPro in the browser.

    If no password is configured, the login screen is skipped (useful on your Mac).
    On Streamlit Cloud you should always set APP_PASSWORD so strangers cannot open the URL.
    """
    load_runtime_secrets()
    password = os.getenv("APP_PASSWORD", "").strip()
    if not password or password in {"change_me", "replace_with_a_password"}:
        return None
    return password
