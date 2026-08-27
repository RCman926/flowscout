"""
Shared Yahoo / yfinance throttle gate.

Prevents Stage A from hammering Yahoo: min spacing between fetches,
shared last-good snapshot reuse while cooling, exponential backoff on
rate-limit / 429 style errors.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Conservative for Yahoo-only Stage A (options chain is expensive)
MIN_INTERVAL_SECONDS = 2.5
CACHE_TTL_SECONDS = 2.5
CLOSED_SESSION_MIN_INTERVAL = 120.0
BACKOFF_STEPS = (5.0, 15.0, 45.0, 120.0, 300.0)


class YahooThrottle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_request_at = 0.0
        self._backoff_until = 0.0
        self._backoff_level = 0
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._stats = {
            "allowed": 0,
            "cache_hits": 0,
            "blocked_cooldown": 0,
            "blocked_backoff": 0,
            "rate_limit_hits": 0,
        }

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            return {
                **self._stats,
                "min_interval_seconds": MIN_INTERVAL_SECONDS,
                "cache_ttl_seconds": CACHE_TTL_SECONDS,
                "backoff_remaining_seconds": max(0.0, round(self._backoff_until - now, 1)),
                "backoff_level": self._backoff_level,
                "seconds_since_last_request": (
                    None if self._last_request_at <= 0 else round(now - self._last_request_at, 2)
                ),
            }

    def get_cached(self, key: str, max_age: Optional[float] = None) -> Optional[Any]:
        ttl = CACHE_TTL_SECONDS if max_age is None else max_age
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            data, ts = entry
            if time.time() - ts <= ttl:
                self._stats["cache_hits"] += 1
                return data
            return None

    def get_stale(self, key: str) -> Optional[Any]:
        """Return last snapshot even if TTL expired (for cooldown UI)."""
        with self._lock:
            entry = self._cache.get(key)
            return entry[0] if entry else None

    def put_cache(self, key: str, data: Any) -> None:
        with self._lock:
            self._cache[key] = (data, time.time())

    def can_fetch(self, min_interval: float = MIN_INTERVAL_SECONDS) -> Tuple[bool, str]:
        now = time.time()
        with self._lock:
            if now < self._backoff_until:
                self._stats["blocked_backoff"] += 1
                wait = self._backoff_until - now
                return False, f"yahoo backoff {wait:.0f}s remaining"
            since = now - self._last_request_at
            if self._last_request_at > 0 and since < min_interval:
                self._stats["blocked_cooldown"] += 1
                return False, f"yahoo cooldown {min_interval - since:.1f}s remaining"
            return True, "ok"

    def mark_request_started(self) -> None:
        with self._lock:
            self._last_request_at = time.time()
            self._stats["allowed"] += 1

    def record_success(self) -> None:
        with self._lock:
            self._backoff_level = 0
            self._backoff_until = 0.0

    def record_rate_limit(self, error: Optional[str] = None) -> float:
        """Apply exponential backoff; returns seconds until retry allowed."""
        with self._lock:
            idx = min(self._backoff_level, len(BACKOFF_STEPS) - 1)
            wait = BACKOFF_STEPS[idx]
            self._backoff_level = min(self._backoff_level + 1, len(BACKOFF_STEPS) - 1)
            self._backoff_until = time.time() + wait
            self._stats["rate_limit_hits"] += 1
            msg = f"Yahoo rate limited — backing off {wait:.0f}s"
            if error:
                msg = f"{msg} ({error[:120]})"
            logger.warning(msg)
            return wait

    def is_rate_limit_error(self, err: Any) -> bool:
        text = str(err or "").lower()
        return any(
            token in text
            for token in ("rate limit", "too many", "429", "unauthorized", "will be blocked")
        )

    def gated_call(
        self,
        cache_key: str,
        fetch_fn: Callable[[], Any],
        *,
        min_interval: float = MIN_INTERVAL_SECONDS,
        cache_ttl: float = CACHE_TTL_SECONDS,
        allow_stale_on_block: bool = True,
    ) -> Tuple[Optional[Any], str]:
        """
        Returns (data, source_note).
        source_note: cache | fresh | stale_cooldown | stale_backoff | blocked | error
        """
        cached = self.get_cached(cache_key, max_age=cache_ttl)
        if cached is not None:
            return cached, "cache"

        ok, reason = self.can_fetch(min_interval=min_interval)
        if not ok:
            if allow_stale_on_block:
                stale = self.get_stale(cache_key)
                if stale is not None:
                    note = "stale_backoff" if "backoff" in reason else "stale_cooldown"
                    return stale, note
            return None, "blocked"

        self.mark_request_started()
        try:
            data = fetch_fn()
            if data is not None:
                self.put_cache(cache_key, data)
                self.record_success()
                return data, "fresh"
            stale = self.get_stale(cache_key) if allow_stale_on_block else None
            return stale, "error" if stale is None else "stale_cooldown"
        except Exception as e:
            if self.is_rate_limit_error(e):
                self.record_rate_limit(str(e))
                stale = self.get_stale(cache_key) if allow_stale_on_block else None
                return stale, "stale_backoff" if stale is not None else "blocked"
            logger.debug(f"Yahoo gated_call error: {e}")
            stale = self.get_stale(cache_key) if allow_stale_on_block else None
            return stale, "error" if stale is None else "stale_cooldown"


yahoo_throttle = YahooThrottle()
