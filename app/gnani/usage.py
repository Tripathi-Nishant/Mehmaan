from collections import defaultdict
from datetime import UTC, date, datetime
from threading import Lock


class GnaniUsageLimitError(RuntimeError):
    """Raised before a Gnani call would exceed the configured daily cap."""


class UsageGuard:
    _counts: dict[tuple[date, str], int] = defaultdict(int)
    _lock = Lock()

    def __init__(self, daily_cap: int, kind: str = "combined"):
        self.daily_cap = daily_cap
        self.kind = kind

    def consume(self) -> None:
        key = (datetime.now(UTC).date(), self.kind)
        with self._lock:
            if self._counts[key] >= self.daily_cap:
                raise GnaniUsageLimitError("Gnani daily call cap reached")
            self._counts[key] += 1

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._lock:
            cls._counts.clear()
