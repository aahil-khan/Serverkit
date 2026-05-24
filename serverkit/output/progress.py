"""Optional progress bars for long operations."""

from __future__ import annotations

from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")


def track_iterable(
    items: Iterable[T],
    description: str,
    *,
    enabled: bool = True,
) -> Iterator[T]:
    if not enabled:
        yield from items
        return
    try:
        from rich.progress import track
    except ImportError:
        yield from items
        return
    yield from track(items, description=description)
