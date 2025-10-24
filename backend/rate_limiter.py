# backend/rate_limiter.py
import time
import threading
from collections import deque
from backend import settings

class SlidingWindowRateLimiter:
    """
    Simple, thread-safe sliding window limiter.
    Allows up to `max_calls` within `window_seconds`.
    """
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.events = deque()
        self.lock = threading.Lock()

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - self.window
        with self.lock:
            while self.events and self.events[0] < cutoff:
                self.events.popleft()
            if len(self.events) < self.max_calls:
                self.events.append(now)
                return True
            return False

# One global limiter for your single API key
global_rate_limiter = SlidingWindowRateLimiter(
    max_calls=settings.MAX_REQUESTS_PER_MINUTE,
    window_seconds=60
)

RATE_LIMIT_MESSAGE = "Too many requests right now. Please try again in a few seconds."

__all__ = ["global_rate_limiter", "RATE_LIMIT_MESSAGE", "SlidingWindowRateLimiter"]
