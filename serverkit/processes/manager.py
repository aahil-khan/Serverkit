"""Process listing and collection filtering."""

from __future__ import annotations

from serverkit.processes.process import Process


class ProcessCollection:
    """Fluent, eager filter chain over Process objects."""

    def __init__(self, data: list[Process] | None = None) -> None:
        self.data: list[Process] = list(data) if data else []

    def named(self, name: str) -> ProcessCollection:
        raise NotImplementedError

    def memory_above(self, mb: float) -> ProcessCollection:
        raise NotImplementedError

    def cpu_above(self, percent: float) -> ProcessCollection:
        raise NotImplementedError

    def sort_by_memory(self) -> ProcessCollection:
        raise NotImplementedError

    def sort_by_cpu(self) -> ProcessCollection:
        raise NotImplementedError

    def all(self) -> list[Process]:
        return self.data

    def summarize(self) -> str:
        raise NotImplementedError

    def __iter__(self):
        return iter(self.data)


class ProcessManager:
    """Loads processes from the OS via psutil."""

    def all(self) -> ProcessCollection:
        raise NotImplementedError
