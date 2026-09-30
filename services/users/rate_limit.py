"""In-memory sliding-window rate limiter.

Scoped per key (e.g. ``login:<email>``, ``login-ip:<addr>``). Only ever
holds the last ``MAX_KEYS`` entries, so memory stays bounded even under a
key-flooding attack.
"""
import threading
import time
from collections import deque

WINDOW_SECONDS = 15 * 60
MAX_ATTEMPTS = 5
MAX_KEYS = 10_000

_lock = threading.Lock()
_events: dict[str, deque[float]] = {}


def allow(key: str, limit: int = MAX_ATTEMPTS) -> bool:
    """Return True if the key is under its quota, recording the attempt."""
    now = time.monotonic()
    with _lock:
        events = _events.get(key)
        if events is None:
            if len(_events) >= MAX_KEYS:
                _events.clear()  # bounded memory beats precision under attack
            events = deque()
            _events[key] = events
        while events and now - events[0] > WINDOW_SECONDS:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True


def reset() -> None:
    with _lock:
        _events.clear()
