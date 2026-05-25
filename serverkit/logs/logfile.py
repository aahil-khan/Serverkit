"""Log file with fluent line filtering."""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.exceptions import LogFileNotFound


@dataclass
class RateReport:
    count: int
    window_minutes: float
    rate_per_minute: float


class LogFile:
    """Chainable filters over log file lines."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lines = self._read_lines(path)
        self._filtered = self._lines[:]

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        p = Path(path)
        if not p.exists():
            raise LogFileNotFound(f"Log not found: {path}")
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\n") for line in f]
        with open(path, encoding="utf-8", errors="replace") as f:
            return [line.rstrip("\n") for line in f.readlines()]

    def errors(self) -> LogFile:
        self._filtered = [line for line in self._filtered if "ERROR" in line]
        return self

    def warnings(self) -> LogFile:
        self._filtered = [line for line in self._filtered if "WARNING" in line]
        return self

    def contains(self, keyword: str) -> LogFile:
        self._filtered = [line for line in self._filtered if keyword in line]
        return self

    def match(self, pattern: str) -> LogFile:
        rx = re.compile(pattern)
        self._filtered = [line for line in self._filtered if rx.search(line)]
        return self

    def tail(self, n: int) -> LogFile:
        self._filtered = self._filtered[-n:]
        return self

    def since(self, timestamp: datetime) -> LogFile:
        self._filtered = [
            line
            for line in self._filtered
            if (_parse_ts(line) or datetime.min) >= timestamp
        ]
        return self

    def until(self, timestamp: datetime) -> LogFile:
        self._filtered = [
            line
            for line in self._filtered
            if (_parse_ts(line) or datetime.max) <= timestamp
        ]
        return self

    def json_lines(self) -> list[dict]:
        records = []
        for line in self._filtered:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def error_rate(self, window_minutes: float = 5.0) -> RateReport:
        errors = [line for line in self._lines if "ERROR" in line]
        count = len(errors)
        rate = count / window_minutes if window_minutes else 0.0
        return RateReport(count=count, window_minutes=window_minutes, rate_per_minute=rate)

    def all(self) -> list[str]:
        return self._filtered

    def summarize(self) -> str:
        total = len(self._lines)
        errors = sum(1 for line in self._lines if "ERROR" in line)
        warns = sum(1 for line in self._lines if "WARNING" in line)
        return f"Total: {total} lines | Errors: {errors} | Warnings: {warns}"

    def summarise(self) -> str:
        return self.summarize()

    def display(self, *, use_rich: bool | None = None, limit: int = 30) -> str:
        rows = [[line[:120]] for line in self._filtered[:limit]]
        return display_table(
            "Log lines", ["Line"], rows, use_rich=resolve_use_rich(use_rich)
        )

    def export(self, path: str, fmt: str = "csv") -> LogFile:
        export_table(path, ["line"], [[line] for line in self._filtered], fmt=fmt)
        return self

    def __repr__(self) -> str:
        return f"LogFile({self.path!r}, {len(self._filtered)}/{len(self._lines)} lines)"


def _parse_ts(line: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        token = line[:19]
        try:
            return datetime.strptime(token, fmt)
        except ValueError:
            continue
    return None
