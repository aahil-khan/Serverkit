"""Log file with fluent line filtering."""

from __future__ import annotations


class LogFile:
    """Chainable filters over log file lines."""

    def __init__(self, path: str) -> None:
        self.path = path
        with open(path, encoding="utf-8", errors="replace") as f:
            # readlines() keeps trailing "\n"; strip so .all() returns clean lines
            self._lines = [line.rstrip("\n") for line in f.readlines()]
        self._filtered = self._lines[:]

    def errors(self) -> LogFile:
        self._filtered = [line for line in self._filtered if "ERROR" in line]
        return self

    def warnings(self) -> LogFile:
        self._filtered = [line for line in self._filtered if "WARNING" in line]
        return self

    def contains(self, keyword: str) -> LogFile:
        self._filtered = [line for line in self._filtered if keyword in line]
        return self

    def tail(self, n: int) -> LogFile:
        self._filtered = self._filtered[-n:]
        return self

    def all(self) -> list[str]:
        return self._filtered

    def summarize(self) -> str:
        total = len(self._lines)
        errors = sum(1 for line in self._lines if "ERROR" in line)
        warns = sum(1 for line in self._lines if "WARNING" in line)
        return f"Total: {total} lines | Errors: {errors} | Warnings: {warns}"
