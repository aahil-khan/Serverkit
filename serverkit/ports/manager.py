from __future__ import annotations

import psutil

from serverkit.core.collection import FluentCollection
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.ports.port import Port


def _process_name(pid: int | None) -> str | None:
    if pid is None:
        return None
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


class PortCollection(FluentCollection[Port]):
    def listening(self) -> PortCollection:
        self.data = [p for p in self.data if p.status == "LISTEN"]
        return self

    def owned_by(self, pid: int) -> PortCollection:
        self.data = [p for p in self.data if p.pid == pid]
        return self

    def port(self, number: int) -> PortCollection:
        self.data = [p for p in self.data if p.port == number]
        return self

    def summarize(self) -> str:
        return "\n".join(
            f":{p.port} {p.status} pid={p.pid} ({p.process_name})"
            for p in self.data[:15]
        )

    def display(self, *, use_rich: bool | None = None, limit: int = 30) -> str:
        rows = [
            [p.port, p.status, p.pid or "", p.process_name or "", p.local_addr]
            for p in self.data[:limit]
        ]
        return display_table(
            "Open ports",
            ["Port", "Status", "PID", "Process", "Local"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> PortCollection:
        export_table(
            path,
            ["port", "status", "pid", "process_name", "local_addr"],
            [
                [p.port, p.status, p.pid, p.process_name, p.local_addr]
                for p in self.data
            ],
            fmt=fmt,
        )
        return self


class PortManager:
    def all(self) -> PortCollection:
        ports: list[Port] = []
        for conn in psutil.net_connections(kind="inet"):
            if not conn.laddr:
                continue
            port_num = conn.laddr.port if hasattr(conn.laddr, "port") else conn.laddr[1]
            host = conn.laddr.ip if hasattr(conn.laddr, "ip") else conn.laddr[0]
            ports.append(
                Port(
                    port=port_num,
                    local_addr=f"{host}:{port_num}",
                    status=conn.status or "",
                    pid=conn.pid,
                    process_name=_process_name(conn.pid),
                )
            )
        return PortCollection(ports)
