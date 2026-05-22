"""Brand assets paths and helpers."""

from __future__ import annotations

import base64
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# Icon-only mark
LOGO_FULL = ASSETS_DIR / "logo.png"
LOGO_HEADER = ASSETS_DIR / "logo_header.png"
LOGO_SIDEBAR = ASSETS_DIR / "logo_sidebar.png"

# Wordmark (icon + StockInsightPro text)
WORDMARK_FULL = ASSETS_DIR / "wordmark.png"
WORDMARK_HEADER = ASSETS_DIR / "wordmark_header.png"
WORDMARK_SIDEBAR = ASSETS_DIR / "wordmark_sidebar.png"


def wordmark_exists() -> bool:
    """Return True if wordmark assets are present."""
    return WORDMARK_HEADER.exists()


def logo_exists() -> bool:
    """Return True if icon-only logo is present."""
    return LOGO_HEADER.exists()


def image_as_base64(path: Path) -> str:
    """Encode an image file for inline HTML embedding."""
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def wordmark_as_base64(variant: str = "header") -> str:
    """Return base64 wordmark for header or sidebar."""
    paths = {
        "header": WORDMARK_HEADER,
        "sidebar": WORDMARK_SIDEBAR,
        "full": WORDMARK_FULL,
    }
    return image_as_base64(paths.get(variant, WORDMARK_HEADER))


def logo_as_base64(path: Path = LOGO_HEADER) -> str:
    """Encode icon logo (fallback when wordmark unavailable)."""
    return image_as_base64(path)
