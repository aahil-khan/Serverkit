"""Opens log files for the SDK."""

from __future__ import annotations

from serverkit.logs.logfile import LogFile


class LogManager:
    def open(self, path: str) -> LogFile:
        return LogFile(path)
