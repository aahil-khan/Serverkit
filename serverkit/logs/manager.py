"""Opens log files for the SDK."""

from __future__ import annotations

from pathlib import Path

from serverkit.logs.logfile import LogFile


class LogManager:
    def open(self, path: str) -> LogFile:
        return LogFile(path)

    def open_with_rotations(self, path: str) -> LogFile:
        """Open base log plus .1, .2.gz siblings merged (newest last)."""
        base = Path(path)
        lines: list[str] = []
        candidates = sorted(base.parent.glob(f"{base.name}*"))
        for candidate in candidates:
            if candidate.is_file():
                lines.extend(LogFile._read_lines(str(candidate)))
        log = LogFile.__new__(LogFile)
        log.path = path
        log._lines = lines
        log._filtered = lines[:]
        return log
