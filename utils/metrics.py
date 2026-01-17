import time
from collections import defaultdict
from typing import Dict

# Very small in-memory metrics store for development/testing.
_counters: Dict[str, int] = defaultdict(int)
_timings: Dict[str, list] = defaultdict(list)


def incr(name: str, amount: int = 1) -> None:
    _counters[name] += amount


def get_counter(name: str) -> int:
    return _counters.get(name, 0)


def record_timing(name: str, value_ms: float) -> None:
    _timings[name].append(value_ms)


def get_timings(name: str):
    return list(_timings.get(name, []))


def time_ms() -> float:
    return time.time() * 1000.0
