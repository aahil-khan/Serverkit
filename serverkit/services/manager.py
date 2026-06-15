"""High-level services API over systemctl."""

from __future__ import annotations

from serverkit.core.collection import FluentCollection
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.services.handle import ServiceHandle, normalize_unit_name
from serverkit.systemctl.manager import SystemctlManager
from serverkit.systemctl.service import Service


class ServiceCollection(FluentCollection[Service]):
    """Fluent collection of systemd service units."""

    def active(self) -> ServiceCollection:
        self.data = [s for s in self.data if s.active_state == "active"]
        return self

    def named(self, text: str) -> ServiceCollection:
        needle = text.lower()
        self.data = [s for s in self.data if needle in s.name.lower()]
        return self

    def summarize(self) -> str:
        return "\n".join(f"{s.name}: {s.active_state}" for s in self.data[:20])

    def display(self, *, use_rich: bool | None = None, limit: int = 25) -> str:
        rows = [
            [s.name, s.active_state, s.load_state, s.description[:50]]
            for s in self.data[:limit]
        ]
        return display_table(
            "Services",
            ["Unit", "Active", "Load", "Description"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> None:
        export_table(
            path,
            ["name", "active_state", "load_state", "description"],
            [[s.name, s.active_state, s.load_state, s.description] for s in self.data],
            fmt=fmt,
        )

    def get(self, name: str) -> ServiceHandle:
        return ServiceHandle(name, self._manager)

    def __init__(
        self,
        data: list[Service] | None = None,
        manager: SystemctlManager | None = None,
    ) -> None:
        super().__init__(data)
        self._manager = manager or SystemctlManager()


class ServicesManager:
    def __init__(self, systemctl: SystemctlManager | None = None) -> None:
        self._systemctl = systemctl or SystemctlManager()

    def list(self) -> ServiceCollection:
        units = self._systemctl.list_units()
        return ServiceCollection(units.data, manager=self._systemctl)

    def get(self, name: str) -> ServiceHandle:
        return ServiceHandle(name, self._systemctl)
