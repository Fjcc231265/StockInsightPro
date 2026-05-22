"""Runtime configuration helpers.

Secrets are read from environment variables first, then from a local `.env`
file. The `.env` file is ignored by git and should never be committed.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_dotenv_if_present() -> None:
    """Load simple KEY=VALUE pairs from `.env` into process environment."""
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


def get_alpha_vantage_api_key() -> str | None:
    """Return configured Alpha Vantage API key, if available."""
    load_dotenv_if_present()
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key or key == "your_key_here":
        return None
    return key
