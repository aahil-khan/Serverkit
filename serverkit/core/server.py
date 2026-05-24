"""Server class — thin facade delegating to domain managers."""

from __future__ import annotations

from serverkit.logs.manager import LogManager
from serverkit.processes.manager import ProcessManager
from serverkit.workflows.manager import WorkflowManager


class Server:
    """Entry point for all SDK usage."""

    def __init__(self) -> None:
        self._process_manager = ProcessManager()
        self._log_manager = LogManager()
        self._workflow_manager = WorkflowManager()

    def processes(self):
        """Return a chainable collection of running processes."""
        return self._process_manager.all()

    def logs(self, path: str):
        """Open a log file for chained filtering."""
        return self._log_manager.open(path)

    def workflow(self, name: str):
        """Start building a named workflow."""
        return self._workflow_manager.create(name)

    def run(self, name: str):
        """Load and execute a saved workflow by name."""
        return self._workflow_manager.run(name)
