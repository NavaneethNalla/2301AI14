"""
p2p.rate_limiter
================
Token-bucket rate limiter for protecting async P2P sockets against spam and DoS.
"""

from __future__ import annotations

import time


class TokenBucket:
    """
    Token-bucket rate limiter.
    Tokens refill continuously at refill_rate tokens/second up to capacity.
    """

    def __init__(self, capacity: float = 20.0, refill_rate: float = 10.0) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(capacity)
        self.last_update = time.perf_counter()

    def allow(self, tokens: float = 1.0) -> bool:
        now = time.perf_counter()
        elapsed = now - self.last_update
        self.last_update = now

        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

