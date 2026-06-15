"""CLI progress indicator for long operations."""

from __future__ import annotations

import itertools
import sys
import threading
import time
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")

SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
PLAIN_FRAMES = ("/", "-", "\\", "|")


def track_iterable(
    items: Iterable[T],
    description: str,
    *,
    enabled: bool = True,
) -> Iterator[T]:
    """Yield items while showing a stderr spinner."""
    if not enabled:
        yield from items
        return

    from serverkit.shell.style import get_active_style

    style = get_active_style()
    frames = SPINNER_FRAMES if style.enabled else PLAIN_FRAMES
    spin = itertools.cycle(frames)
    stop = threading.Event()

    def _draw() -> None:
        while not stop.is_set():
            frame = next(spin)
            if style.enabled:
                prefix = f"{style.dim(description)} {style.accent(frame)} "
            else:
                prefix = f"{description} {frame} "
            sys.stderr.write(f"\r{prefix}")
            sys.stderr.flush()
            time.sleep(0.1)

    thread = threading.Thread(target=_draw, daemon=True)
    thread.start()
    try:
        yield from items
    finally:
        stop.set()
        thread.join(timeout=0.3)
        sys.stderr.write("\r" + " " * (len(description) + 4) + "\r")
        sys.stderr.flush()
