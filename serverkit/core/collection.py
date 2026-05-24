"""Shared fluent collection behavior."""

from __future__ import annotations

from typing import Generic, Iterable, TypeVar

T = TypeVar("T")


class FluentCollection(Generic[T]):
    """Base for eager filter chains over a list of domain objects."""

    def __init__(self, data: Iterable[T] | None = None) -> None:
        self.data: list[T] = list(data) if data else []

    def all(self) -> list[T]:
        return self.data

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({len(self)} items)"
