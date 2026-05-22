"""Shared market domain models.

These lightweight dataclasses define the data shapes that future services,
analytics engines, and AI agents can exchange without depending on Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuoteSummary:
    """Normalized quote summary for a selected ticker."""

    ticker: str
    name: str
    price: float
    change_pct: float
    change_abs: float
    volume: int
    market_cap: float
    sector: str


@dataclass(frozen=True)
class OptionsInsightSummary:
    """High-level options intelligence metrics."""

    ticker: str
    put_call_ratio: float
    iv_rank: float
    thirty_day_iv: float
    max_pain: float
