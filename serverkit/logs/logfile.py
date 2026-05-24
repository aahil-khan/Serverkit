"""Log file with fluent line filtering."""

from __future__ import annotations


class LogFile:
    """Chainable filters over log file lines."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lines: list[str] = []
        self._filtered: list[str] = []

    def errors(self) -> LogFile:
        raise NotImplementedError

    def warnings(self) -> LogFile:
        raise NotImplementedError

    def contains(self, keyword: str) -> LogFile:
        raise NotImplementedError

    def tail(self, n: int) -> LogFile:
        raise NotImplementedError

    def all(self) -> list[str]:
        raise NotImplementedError

    def summarize(self) -> str:
        raise NotImplementedError
