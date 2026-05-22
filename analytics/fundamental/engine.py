"""Fundamental analytics engine placeholder."""

from __future__ import annotations

import pandas as pd


def calculate_growth_rate(current: float, previous: float) -> float:
    """Calculate period-over-period growth rate."""
    # TODO: Extend to CAGR, margin, quality, and valuation scoring engines.
    if previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100
