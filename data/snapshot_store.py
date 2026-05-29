"""Persist computed dataframe snapshots for fast page loads."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from utils.config import PROJECT_ROOT

SNAPSHOT_DIR = PROJECT_ROOT / "data" / "cache" / "snapshots"


def _snapshot_path(name: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_DIR / f"{name}.json"


def save_snapshot(name: str, frame: pd.DataFrame, ttl_seconds: int) -> None:
    """Write a dataframe snapshot with metadata."""
    payload: dict[str, Any] = {
        "fetched_at": time.time(),
        "ttl_seconds": ttl_seconds,
        "attrs": dict(frame.attrs),
        "table": json.loads(frame.to_json(orient="table", date_format="iso")),
    }
    _snapshot_path(name).write_text(json.dumps(payload), encoding="utf-8")


def load_snapshot(name: str) -> pd.DataFrame | None:
    """Return a fresh dataframe snapshot when available."""
    path = _snapshot_path(name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = float(payload.get("fetched_at", 0))
        ttl_seconds = int(payload.get("ttl_seconds", 0))
        if (time.time() - fetched_at) >= max(ttl_seconds, 1):
            return None
        frame = pd.read_json(json.dumps(payload["table"]), orient="table")
        if "Date" in frame.columns:
            frame["Date"] = pd.to_datetime(frame["Date"])
        frame.attrs.update(payload.get("attrs", {}))
        return frame
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None


def clear_snapshot(name: str) -> bool:
    """Delete one named snapshot file."""
    path = _snapshot_path(name)
    if not path.exists():
        return False
    path.unlink()
    return True


def clear_all_snapshots() -> int:
    """Delete all snapshot files."""
    if not SNAPSHOT_DIR.exists():
        return 0
    count = 0
    for path in SNAPSHOT_DIR.glob("*.json"):
        path.unlink()
        count += 1
    return count
