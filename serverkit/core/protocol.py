"""Shared facade method contracts for local and remote servers."""

from __future__ import annotations

from typing import Protocol

from serverkit.logs.logfile import LogFile
from serverkit.memory.snapshot import MemorySnapshot
from serverkit.processes.manager import ProcessCollection


class ServerFacade(Protocol):
    def processes(self) -> ProcessCollection: ...
    def logs(self, path: str) -> LogFile: ...
    def memory(self) -> MemorySnapshot: ...
    def run(self, name: str, *, dry_run: bool = False, executor: str | None = None): ...
