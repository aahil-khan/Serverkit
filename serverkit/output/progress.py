"""CLI progress indicator for long operations (ASCII spinner, not Rich bars)."""

from __future__ import annotations

import itertools
import sys
import threading
import time
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")

# Traditional rotating indicator: / -> - -> \
SPINNER_FRAMES = ("/", "-", "\\", "|")


def track_iterable(
    items: Iterable[T],
    description: str,
    *,
    enabled: bool = True,
) -> Iterator[T]:
    """Yield items while showing a simple stderr spinner (no Rich progress bar)."""
    if not enabled:
        yield from items
        return

    spin = itertools.cycle(SPINNER_FRAMES)
    stop = threading.Event()

    def _draw() -> None:
        while not stop.is_set():
            frame = next(spin)
            sys.stderr.write(f"\r{description} {frame} ")
            sys.stderr.flush()
            time.sleep(0.12)

    thread = threading.Thread(target=_draw, daemon=True)
    thread.start()
    try:
        yield from items
    finally:
        stop.set()
        thread.join(timeout=0.3)
        sys.stderr.write("\r" + " " * (len(description) + 4) + "\r")
        sys.stderr.flush()
