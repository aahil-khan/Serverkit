"""Process listing and collection filtering."""

from __future__ import annotations

import psutil

from serverkit.core.collection import FluentCollection
from serverkit.config import Config
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.output.progress import track_iterable
from serverkit.processes.aliases import app_name
from serverkit.processes.factory import ProcessFactory
from serverkit.processes.process import Process


class ProcessCollection(FluentCollection[Process]):
    def named(self, name: str) -> ProcessCollection:
        needle = name.lower()
        self.data = [p for p in self.data if needle in p.name.lower()]
        return self

    def memory_above(self, mb: float) -> ProcessCollection:
        self.data = [p for p in self.data if p.memory_mb > mb]
        return self

    def cpu_above(self, percent: float) -> ProcessCollection:
        self.data = [p for p in self.data if p.cpu_percent > percent]
        return self

    def for_user(self, username: str) -> ProcessCollection:
        needle = username.lower()
        self.data = [
            p for p in self.data if p.username and p.username.lower() == needle
        ]
        return self

    def sort_by_memory(self) -> ProcessCollection:
        self.data = sorted(self.data, key=lambda p: p.memory_mb, reverse=True)
        return self

    def sort_by_cpu(self) -> ProcessCollection:
        self.data = sorted(self.data, key=lambda p: p.cpu_percent, reverse=True)
        return self

    def summarize(self) -> str:
        lines = [f"{p.name}: {p.memory_mb:.1f} MB" for p in self.data[:10]]
        return "\n".join(lines)

    def summarise(self) -> str:
        return self.summarize()

    def display(self, *, use_rich: bool | None = None, limit: int = 25) -> str:
        rows = [
            [p.name, f"{p.memory_mb:.1f}", f"{p.cpu_percent:.1f}", p.pid, p.username or ""]
            for p in self.data[:limit]
        ]
        return display_table(
            "Processes",
            ["Name", "Memory MB", "CPU %", "PID", "User"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> ProcessCollection:
        export_table(
            path,
            ["name", "memory_mb", "cpu_percent", "pid", "username"],
            [
                [p.name, p.memory_mb, p.cpu_percent, p.pid, p.username or ""]
                for p in self.data
            ],
            fmt=fmt,
        )
        return self

    def group_by_name(self, *, use_aliases: bool = True) -> dict[str, ProcessCollection]:
        """Group PIDs by app name; use_aliases rolls Firefox children into firefox."""
        groups: dict[str, list[Process]] = {}
        for proc in self.data:
            key = app_name(proc.name) if use_aliases else proc.name
            groups.setdefault(key, []).append(proc)
        return {name: ProcessCollection(procs) for name, procs in groups.items()}

    def summarize_by_name(self, limit: int = 10) -> str:
        """Top apps by total memory (sum of all PIDs sharing a name)."""
        rows = self._app_totals()
        lines = [
            f"{name}: {memory_mb:.1f} MB ({count} PIDs)"
            for name, memory_mb, count in rows[:limit]
        ]
        return "\n".join(lines)

    def display_by_name(
        self, *, use_rich: bool | None = None, limit: int = 15, use_aliases: bool = True
    ) -> str:
        """Table of apps with aggregated memory (closer to Mission Center view)."""
        rows = [
            [name, f"{memory_mb:.1f}", count, f"{memory_mb / 1024:.2f}"]
            for name, memory_mb, count in self._app_totals(use_aliases=use_aliases)[:limit]
        ]
        title = (
            "Apps (with Firefox child aliases)"
            if use_aliases
            else "Apps (by process name)"
        )
        return display_table(
            title,
            ["App", "Memory MB", "PIDs", "GiB"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def _app_totals(self, *, use_aliases: bool = True) -> list[tuple[str, float, int]]:
        totals: list[tuple[str, float, int]] = []
        for name, collection in self.group_by_name(use_aliases=use_aliases).items():
            memory_mb = sum(p.memory_mb for p in collection.data)
            totals.append((name, memory_mb, len(collection.data)))
        totals.sort(key=lambda item: item[1], reverse=True)
        return totals

    def group_by_user(self) -> dict[str, ProcessCollection]:
        groups: dict[str, list[Process]] = {}
        for proc in self.data:
            user = proc.username or "unknown"
            groups.setdefault(user, []).append(proc)
        return {user: ProcessCollection(procs) for user, procs in groups.items()}

    def kill_all(self) -> int:
        count = 0
        for proc in self.data:
            try:
                proc.kill()
                count += 1
            except Exception:
                pass
        return count

    def terminate_all(self) -> int:
        count = 0
        for proc in self.data:
            try:
                proc.terminate()
                count += 1
            except Exception:
                pass
        return count

    def tree(self) -> dict[int, dict]:
        """Build parent -> children tree from current collection."""
        by_pid = {p.pid: p for p in self.data}
        roots = [p for p in self.data if p.ppid not in by_pid]

        def node(proc: Process) -> dict:
            kids = [c for c in self.data if c.ppid == proc.pid]
            return {"process": proc, "children": [node(k) for k in kids]}

        return {r.pid: node(r) for r in roots}


class ProcessManager:
    def __init__(self, config: Config | None = None) -> None:
        self._config = config

    def all(self) -> ProcessCollection:
        cfg = self._config or Config.load()
        show_progress = bool(cfg.get("output", "show_progress", default=False))
        # psutil returns 0.0 on the first cpu_percent() call per process; prime first.
        raw: list[psutil.Process] = []
        for proc in track_iterable(
            psutil.process_iter(), "Scanning processes", enabled=show_progress
        ):
            try:
                raw.append(proc)
            except psutil.NoSuchProcess:
                continue
        for proc in raw:
            try:
                proc.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        processes: list[Process] = []
        for proc in raw:
            process = ProcessFactory.create(proc)
            if process is not None:
                processes.append(process)
        return ProcessCollection(processes)

    def snapshot(self) -> ProcessCollection:
        return self.all()
