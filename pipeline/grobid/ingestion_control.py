"""Persistent user pause and bounded overnight execution window."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / 'data/grobid/batch'


def paused(output: Path = DEFAULT_OUTPUT, now: dt.datetime | None = None) -> bool:
    path = output / 'pause.json'
    if not path.exists():
        return False
    try:
        policy = json.loads(path.read_text())
        if policy.get('paused', True):
            return True
        now = now or dt.datetime.now(dt.timezone.utc)
        for key, lower in [('resume_not_before', True), ('resume_until', False)]:
            if policy.get(key):
                limit = dt.datetime.fromisoformat(policy[key].replace('Z', '+00:00'))
                if limit.tzinfo is None:
                    return True
                outside_window = now < limit if lower else now >= limit
                if outside_window:
                    return True
        return False
    except (OSError, ValueError, TypeError, AttributeError):
        return True


def require_running() -> None:
    if paused():
        raise ValueError('Ingestion is paused by the user or outside its scheduled window')
