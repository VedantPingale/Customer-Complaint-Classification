"""Complaint reference number generator."""

import datetime
import random
import threading

_counter_lock = threading.Lock()
_counter = random.randint(10000, 99999)


def generate_reference() -> str:
    """Generate a unique complaint reference number.

    Format: CMP-YYYY-NNNNN
    Example: CMP-2026-10482

    Uses a thread-safe counter combined with the current year to produce
    references that are short, human-readable, and unique within a year.
    """
    global _counter
    year = datetime.datetime.now(datetime.timezone.utc).year

    with _counter_lock:
        _counter += 1
        current_count = _counter

    return f"CMP-{year}-{current_count:05d}"
