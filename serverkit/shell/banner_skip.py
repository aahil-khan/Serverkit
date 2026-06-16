"""Interruptible banner animation helpers."""

from __future__ import annotations

import select
import sys
import threading
import time


class SkipWatcher:
    """Detect keypresses during banner animation so the user can skip ahead."""

    def __init__(self) -> None:
        self._requested = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
            return
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self) -> None:
        try:
            import termios
            import tty
        except ImportError:  # pragma: no cover — Windows
            return

        fd = sys.stdin.fileno()
        try:
            old = termios.tcgetattr(fd)
        except termios.error:
            return

        try:
            tty.setcbreak(fd)
            while not self._stop.is_set():
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not ready:
                    continue
                if sys.stdin.read(1):
                    self._requested.set()
                    return
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except termios.error:
                pass

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.25)

    @property
    def skipped(self) -> bool:
        return self._requested.is_set()


def interruptible_sleep(seconds: float, skip: SkipWatcher | None) -> bool:
    """Sleep in small slices. Returns True when skip was requested."""
    if skip is None:
        time.sleep(seconds)
        return False
    if skip.skipped:
        return True
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if skip.skipped:
            return True
        time.sleep(min(0.02, end - time.monotonic()))
    return skip.skipped
