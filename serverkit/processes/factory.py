"""Factory for building Process objects from psutil records."""

from __future__ import annotations

from serverkit.processes.process import Process


class ProcessFactory:
    """Creates Process instances from raw psutil process handles."""

    @staticmethod
    def create(proc) -> Process | None:
        """Build a Process from a psutil.Process, or None if inaccessible."""
        raise NotImplementedError
