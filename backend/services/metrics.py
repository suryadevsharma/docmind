import logging
import threading
from typing import Dict

logger = logging.getLogger(__name__)


class MetricsTracker:
    """Thread-safe metrics counter for monitoring Gemini API usage and rate limits."""

    def __init__(self):
        self._lock = threading.Lock()
        self.embedding_calls = 0
        self.generation_calls = 0
        self.rate_limit_429_responses = 0

    def inc_embedding_call(self) -> int:
        with self._lock:
            self.embedding_calls += 1
            total = self.embedding_calls
        logger.info(f"[METRIC] total_gemini_embedding_calls={total}")
        return total

    def inc_generation_call(self, stream: bool = False) -> int:
        with self._lock:
            self.generation_calls += 1
            total = self.generation_calls
        logger.info(f"[METRIC] total_gemini_generation_calls={total} stream={stream}")
        return total

    def inc_429_response(self, context: str = "") -> int:
        with self._lock:
            self.rate_limit_429_responses += 1
            total = self.rate_limit_429_responses
        logger.warning(f"[METRIC] total_429_responses={total} context={context}")
        return total

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "total_embedding_calls": self.embedding_calls,
                "total_generation_calls": self.generation_calls,
                "total_429_responses": self.rate_limit_429_responses,
            }

    def reset(self):
        """Reset counters, useful for isolated test runs."""
        with self._lock:
            self.embedding_calls = 0
            self.generation_calls = 0
            self.rate_limit_429_responses = 0


# Global singleton instance
metrics = MetricsTracker()
