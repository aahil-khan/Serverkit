"""Factory for building Process objects from psutil records."""

from __future__ import annotations

import psutil

from serverkit.processes.process import Process


class ProcessFactory:
    """Creates Process instances from raw psutil process handles."""

    @staticmethod
    def create(proc: psutil.Process) -> Process | None:
        """Build a Process from a psutil.Process, or None if inaccessible."""
        try:
            with proc.oneshot():
                return Process(
                    pid=proc.pid,
                    name=proc.name(),
                    memory_mb=proc.memory_info().rss / 1024 / 1024,
                    cpu_percent=proc.cpu_percent(),
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
