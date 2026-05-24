"""Process domain object."""

from __future__ import annotations


class Process:
    """A single OS process with chainable actions."""

    def __init__(
        self,
        pid: int,
        name: str,
        memory_mb: float,
        cpu_percent: float,
    ) -> None:
        self.pid = pid
        self.name = name
        self.memory_mb = memory_mb
        self.cpu_percent = cpu_percent

    def kill(self) -> None:
        """Send SIGKILL to the process."""
        raise NotImplementedError

    def terminate(self) -> None:
        """Send SIGTERM to the process."""
        raise NotImplementedError

    def details(self) -> dict:
        """Return process attributes as a plain dict."""
        return {
            "pid": self.pid,
            "name": self.name,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
        }

    def __repr__(self) -> str:
        return (
            f"Process({self.name!r}, pid={self.pid}, "
            f"mem={self.memory_mb:.1f}MB)"
        )
