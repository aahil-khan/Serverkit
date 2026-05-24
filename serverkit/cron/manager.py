from __future__ import annotations

from pathlib import Path

from serverkit.core.collection import FluentCollection
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.cron.job import CronJob


class CronCollection(FluentCollection[CronJob]):
    def suspicious_only(self) -> CronCollection:
        self.data = [j for j in self.data if j.suspicious]
        return self

    def summarize(self) -> str:
        return "\n".join(repr(j) for j in self.data[:20])

    def display(self, *, use_rich: bool | None = None, limit: int = 25) -> str:
        rows = [
            [j.schedule, j.command[:60], j.source, "yes" if j.suspicious else ""]
            for j in self.data[:limit]
        ]
        return display_table(
            "Cron jobs",
            ["Schedule", "Command", "Source", "Suspicious"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> None:
        export_table(
            path,
            ["schedule", "command", "source", "suspicious"],
            [
                [j.schedule, j.command, j.source, j.suspicious]
                for j in self.data
            ],
            fmt=fmt,
        )


class CronManager:
    def all(self) -> CronCollection:
        jobs: list[CronJob] = []
        paths = [Path("/etc/crontab"), *Path("/etc/cron.d").glob("*")]
        for path in paths:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 5)
                if len(parts) < 6:
                    continue
                schedule = " ".join(parts[:5])
                jobs.append(CronJob(schedule, parts[5], str(path)))
        return CronCollection(jobs)
