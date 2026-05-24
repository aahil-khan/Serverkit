from __future__ import annotations

import psutil

from serverkit.core.collection import FluentCollection
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.disk.partition import FileEntry, Partition, directory_size_mb, scan_largest_files


class DiskCollection(FluentCollection[Partition]):
    def usage_above(self, percent: float) -> DiskCollection:
        self.data = [p for p in self.data if p.percent > percent]
        return self

    def mount_contains(self, text: str) -> DiskCollection:
        needle = text.lower()
        self.data = [p for p in self.data if needle in p.mountpoint.lower()]
        return self

    def sort_by_used(self) -> DiskCollection:
        self.data = sorted(self.data, key=lambda p: p.used_mb, reverse=True)
        return self

    def summarize(self) -> str:
        lines = [
            f"{p.mountpoint}: {p.used_mb:.0f}/{p.total_mb:.0f} MB ({p.percent:.1f}%)"
            for p in self.data[:10]
        ]
        return "\n".join(lines)

    def display(self, *, use_rich: bool | None = None) -> str:
        rows = [
            [p.mountpoint, p.device, f"{p.used_mb:.0f}", f"{p.total_mb:.0f}", f"{p.percent:.1f}"]
            for p in self.data
        ]
        return display_table(
            "Disk partitions",
            ["Mount", "Device", "Used MB", "Total MB", "Use %"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> None:
        export_table(
            path,
            ["mountpoint", "device", "fstype", "used_mb", "total_mb", "percent"],
            [
                [p.mountpoint, p.device, p.fstype, p.used_mb, p.total_mb, p.percent]
                for p in self.data
            ],
            fmt=fmt,
        )

    def largest_files(self, root: str, limit: int = 20) -> list[FileEntry]:
        return scan_largest_files(root, limit)

    def dir_size(self, path: str) -> float:
        return directory_size_mb(path)


class DiskManager:
    def all(self) -> DiskCollection:
        partitions: list[Partition] = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            partitions.append(
                Partition(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total_mb=usage.total / 1024 / 1024,
                    used_mb=usage.used / 1024 / 1024,
                    percent=usage.percent,
                )
            )
        return DiskCollection(partitions)
