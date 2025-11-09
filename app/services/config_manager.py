"""Configuration override manager.

This module allows runtime read/write for a small set of configuration keys
without restarting the backend. Data is stored in a JSON file defined by
settings.CONFIG_FILE_PATH. Access is cached with a short TTL to avoid
excessive disk I/O.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import settings

_ALLOWED_KEYS = {
    "admin_openids": list,
    "rate_limit_max_requests": int,
    "rate_limit_window_seconds": int,
}

_CACHE_TTL_SECONDS = 5
_cache_lock = threading.Lock()
_cache_data: Dict[str, Any] | None = None
_cache_timestamp: float = 0.0

_config_path = Path(settings.CONFIG_FILE_PATH).resolve()


def _ensure_file() -> None:
    if not _config_path.exists():
        _config_path.write_text("{}", encoding="utf-8")


def _load_config() -> Dict[str, Any]:
    global _cache_data, _cache_timestamp
    now = time.time()
    with _cache_lock:
        if _cache_data is not None and now - _cache_timestamp < _CACHE_TTL_SECONDS:
            return dict(_cache_data)

        _ensure_file()
        try:
            data = json.loads(_config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            data = {}

        _cache_data = data
        _cache_timestamp = now
        return dict(data)


def _save_config(data: Dict[str, Any]) -> None:
    with _cache_lock:
        _config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        # invalidate cache immediately
        global _cache_data, _cache_timestamp
        _cache_data = dict(data)
        _cache_timestamp = time.time()


def get_config_snapshot() -> Dict[str, Any]:
    config = _load_config()
    return {k: config.get(k) for k in _ALLOWED_KEYS.keys()}


def update_config(values: Dict[str, Any]) -> Dict[str, Any]:
    current = _load_config()

    for key, value in values.items():
        if key not in _ALLOWED_KEYS:
            raise ValueError(f"Unsupported config key: {key}")
        expected_type = _ALLOWED_KEYS[key]
        if value is None:
            current.pop(key, None)
            continue
        if expected_type is list:
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"Config '{key}' must be a list of strings")
            current[key] = value
        elif expected_type is int:
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            if not isinstance(value, int):
                raise ValueError(f"Config '{key}' must be an integer")
            current[key] = value
        else:
            raise ValueError(f"Unsupported type for key {key}")

    _save_config(current)
    return get_config_snapshot()


def get_admin_openids() -> List[str]:
    config = _load_config()
    overrides = config.get("admin_openids")
    result = list(settings.ADMIN_OPENIDS)
    if isinstance(overrides, list):
        result.extend(str(item) for item in overrides if item)
    # remove duplicates while preserving order
    seen = set()
    deduped: List[str] = []
    for item in result:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def get_rate_limit_settings() -> Tuple[int, int]:
    config = _load_config()
    max_requests = config.get("rate_limit_max_requests", settings.RATE_LIMIT_MAX_REQUESTS)
    window_seconds = config.get("rate_limit_window_seconds", settings.RATE_LIMIT_WINDOW_SECONDS)

    try:
        max_requests = int(max_requests)
    except (TypeError, ValueError):
        max_requests = settings.RATE_LIMIT_MAX_REQUESTS

    try:
        window_seconds = int(window_seconds)
    except (TypeError, ValueError):
        window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS

    return max(1, max_requests), max(1, window_seconds)