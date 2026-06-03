"""Education content service backed on local JSON curriculum and rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.config import PROJECT_ROOT

RULES_FILE = PROJECT_ROOT / "data" / "education_rules.json"
LESSONS_FILE = PROJECT_ROOT / "data" / "education_lessons.json"


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk, returning an empty dict on failure."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_education_rules() -> list[dict[str, Any]]:
    """Load educational trading rules from the local JSON file."""
    rules = _load_json(RULES_FILE).get("rules", [])
    return rules if isinstance(rules, list) else []


def filter_rules(market_regime: str | None = None, instrument: str | None = None) -> list[dict[str, Any]]:
    """Return rules matching optional regime and instrument filters."""
    rules = load_education_rules()
    if market_regime and market_regime != "All":
        rules = [rule for rule in rules if rule.get("market_regime") == market_regime]
    if instrument and instrument != "All":
        rules = [rule for rule in rules if instrument.lower() in str(rule.get("instrument", "")).lower()]
    return rules


def load_education_curriculum() -> dict[str, Any]:
    """Load the full education curriculum (roadmap, lessons, playbooks, checklists)."""
    return _load_json(LESSONS_FILE)


def get_roadmap_modules() -> list[dict[str, Any]]:
    """Return ordered roadmap modules."""
    modules = load_education_curriculum().get("roadmap", [])
    if not isinstance(modules, list):
        return []
    return sorted(modules, key=lambda item: int(item.get("order", 0)))


def get_all_lessons() -> list[dict[str, Any]]:
    """Return all lesson records."""
    lessons = load_education_curriculum().get("lessons", [])
    return lessons if isinstance(lessons, list) else []


def get_lesson(lesson_id: str) -> dict[str, Any] | None:
    """Return one lesson by id."""
    for lesson in get_all_lessons():
        if lesson.get("id") == lesson_id:
            return lesson
    return None


def get_lessons_for_module(module_id: str) -> list[dict[str, Any]]:
    """Return lessons belonging to a roadmap module id."""
    module = next((item for item in get_roadmap_modules() if item.get("id") == module_id), None)
    if not module:
        return [lesson for lesson in get_all_lessons() if lesson.get("module") == module_id]
    lesson_ids = module.get("lesson_ids", [])
    lessons_by_id = {lesson["id"]: lesson for lesson in get_all_lessons() if lesson.get("id")}
    return [lessons_by_id[lesson_id] for lesson_id in lesson_ids if lesson_id in lessons_by_id]


def get_strategy_playbook() -> list[dict[str, Any]]:
    """Return strategy playbook entries."""
    strategies = load_education_curriculum().get("strategy_playbook", [])
    return strategies if isinstance(strategies, list) else []


def get_checklists() -> list[dict[str, Any]]:
    """Return checklist definitions."""
    checklists = load_education_curriculum().get("checklists", [])
    return checklists if isinstance(checklists, list) else []


def get_module_title(module_id: str) -> str:
    """Return display title for a module id."""
    for module in get_roadmap_modules():
        if module.get("id") == module_id:
            return str(module.get("title", module_id))
    return module_id.replace("-", " ").title()
