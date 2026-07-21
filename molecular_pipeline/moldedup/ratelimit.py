"""A tiny thread-safe minimum-interval rate limiter.

PubChem asks clients to stay at or below 5 requests/second. A 0.2s+ minimum
interval between requests keeps us compliant without a heavier token bucket.
"""
from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = max(0.0, min_interval)
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        """Block until at least `min_interval` has elapsed since the previous call."""
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
            self._last = time.monotonic()
