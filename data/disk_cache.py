"""Persistent on-disk cache for provider API responses."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

from utils.config import PROJECT_ROOT

CACHE_ROOT = PROJECT_ROOT / "data" / "cache"
ALPHA_VANTAGE_CACHE_DIR = CACHE_ROOT / "alpha_vantage"


def _namespace_dir(namespace: str) -> Path:
    path = CACHE_ROOT / namespace
    path.mkdir(parents=True, exist_ok=True)
    return path


def _params_fingerprint(params: dict[str, str]) -> str:
    """Build a stable cache key from request params (apikey excluded)."""
    filtered = {key: value for key, value in sorted(params.items()) if key != "apikey"}
    payload = json.dumps(filtered, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _entry_path(namespace: str, fingerprint: str, suffix: str) -> Path:
    return _namespace_dir(namespace) / f"{fingerprint}{suffix}"


def _is_fresh(fetched_at: float, ttl_seconds: int) -> bool:
    return (time.time() - fetched_at) < max(ttl_seconds, 1)


def get_json(namespace: str, params: dict[str, str], ttl_seconds: int) -> dict[str, Any] | None:
    """Return cached JSON payload when still fresh."""
    fingerprint = _params_fingerprint(params)
    path = _entry_path(namespace, fingerprint, ".json")
    if not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not _is_fresh(float(envelope.get("fetched_at", 0)), ttl_seconds):
        return None
    payload = envelope.get("payload")
    return payload if isinstance(payload, dict) else None


def get_json_stale(namespace: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Return cached JSON payload even when stale."""
    fingerprint = _params_fingerprint(params)
    path = _entry_path(namespace, fingerprint, ".json")
    if not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    payload = envelope.get("payload")
    return payload if isinstance(payload, dict) else None


def set_json(namespace: str, params: dict[str, str], payload: dict[str, Any], ttl_seconds: int) -> None:
    """Persist JSON payload with metadata."""
    fingerprint = _params_fingerprint(params)
    path = _entry_path(namespace, fingerprint, ".json")
    envelope = {
        "fetched_at": time.time(),
        "ttl_seconds": ttl_seconds,
        "params": {key: value for key, value in sorted(params.items()) if key != "apikey"},
        "payload": payload,
    }
    path.write_text(json.dumps(envelope), encoding="utf-8")


def get_text(namespace: str, params: dict[str, str], ttl_seconds: int) -> str | None:
    """Return cached text payload when still fresh."""
    fingerprint = _params_fingerprint(params)
    meta_path = _entry_path(namespace, fingerprint, ".meta.json")
    body_path = _entry_path(namespace, fingerprint, ".txt")
    if not meta_path.exists() or not body_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        body = body_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        return None
    if not _is_fresh(float(meta.get("fetched_at", 0)), ttl_seconds):
        return None
    return body


def get_text_stale(namespace: str, params: dict[str, str]) -> str | None:
    """Return cached text payload even when stale."""
    fingerprint = _params_fingerprint(params)
    body_path = _entry_path(namespace, fingerprint, ".txt")
    if not body_path.exists():
        return None
    try:
        return body_path.read_text(encoding="utf-8")
    except OSError:
        return None


def set_text(namespace: str, params: dict[str, str], payload: str, ttl_seconds: int) -> None:
    """Persist text payload with metadata."""
    fingerprint = _params_fingerprint(params)
    meta_path = _entry_path(namespace, fingerprint, ".meta.json")
    body_path = _entry_path(namespace, fingerprint, ".txt")
    meta = {
        "fetched_at": time.time(),
        "ttl_seconds": ttl_seconds,
        "params": {key: value for key, value in sorted(params.items()) if key != "apikey"},
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    body_path.write_text(payload, encoding="utf-8")


def clear_namespace(namespace: str) -> int:
    """Delete all cache files for a namespace. Returns files removed."""
    target = CACHE_ROOT / namespace
    if not target.exists():
        return 0
    count = sum(1 for path in target.rglob("*") if path.is_file())
    shutil.rmtree(target)
    return count


def clear_all() -> int:
    """Delete all cached provider files."""
    if not CACHE_ROOT.exists():
        return 0
    count = sum(1 for path in CACHE_ROOT.rglob("*") if path.is_file())
    shutil.rmtree(CACHE_ROOT)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return count


def cache_size_bytes(namespace: str | None = None) -> int:
    """Return total cache size in bytes."""
    root = CACHE_ROOT / namespace if namespace else CACHE_ROOT
    if not root.exists():
        return 0
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def cache_file_count(namespace: str | None = None) -> int:
    """Return number of cached files."""
    root = CACHE_ROOT / namespace if namespace else CACHE_ROOT
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())
