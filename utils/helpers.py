"""Formatting and display helpers for StockInsightPro."""

from __future__ import annotations

import re


def normalize_ticker(symbol: str) -> str:
    """Normalize a user-entered ticker symbol."""
    return re.sub(r"[^A-Z0-9.\-]", "", symbol.strip().upper())


def format_currency(value: float, decimals: int = 2) -> str:
    """Format a number as USD currency."""
    return f"${value:,.{decimals}f}"


def format_percent(value: float, decimals: int = 2, signed: bool = True) -> str:
    """Format a number as a percentage string."""
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:.{decimals}f}%"


def format_large_number(value: float) -> str:
    """Format large numbers with B/M/K suffixes."""
    abs_val = abs(value)
    if abs_val >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:,.0f}"


def change_color_class(value: float) -> str:
    """Return CSS color token for positive/negative change."""
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"
