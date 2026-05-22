"""Options analytics engine placeholder.

This module is intentionally UI-free. Future calculations such as IV rank,
max pain, gamma exposure, vanna/charm, and dealer positioning should live here
or in sibling analytics modules.
"""

from __future__ import annotations

import pandas as pd


def estimate_max_pain(open_interest: pd.DataFrame) -> float:
    """Return a placeholder max-pain estimate from open interest data."""
    # TODO: Implement payout-minimization across strikes and expirations.
    if open_interest.empty:
        return 0.0
    return float(open_interest["Strike"].median())


def classify_gamma_regime(gamma_exposure: pd.DataFrame) -> str:
    """Classify the placeholder dealer gamma regime."""
    # TODO: Implement real gamma regime classification from greeks and OI.
    net_gamma = gamma_exposure.get("Gamma Exposure ($MM)", pd.Series(dtype=float)).sum()
    if net_gamma > 0:
        return "Long Gamma"
    if net_gamma < 0:
        return "Short Gamma"
    return "Neutral Gamma"
