"""Education content service backed by local rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.config import PROJECT_ROOT

RULES_FILE = PROJECT_ROOT / "data" / "education_rules.json"


def load_education_rules() -> list[dict[str, Any]]:
    """Load educational trading rules from the local JSON file."""
    if not RULES_FILE.exists():
        return []
    try:
        payload = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rules = payload.get("rules", [])
    return rules if isinstance(rules, list) else []


def filter_rules(market_regime: str | None = None, instrument: str | None = None) -> list[dict[str, Any]]:
    """Return rules matching optional regime and instrument filters."""
    rules = load_education_rules()
    if market_regime and market_regime != "All":
        rules = [rule for rule in rules if rule.get("market_regime") == market_regime]
    if instrument and instrument != "All":
        rules = [rule for rule in rules if instrument.lower() in str(rule.get("instrument", "")).lower()]
    return rules
