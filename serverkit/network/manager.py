from __future__ import annotations

import psutil

from serverkit.core.collection import FluentCollection
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.network.connection import Connection, NetworkInterface


def _addr_to_str(addr) -> str:
    if not addr:
        return ""
    host = addr.ip if hasattr(addr, "ip") else addr[0]
    port = addr.port if hasattr(addr, "port") else addr[1]
    return f"{host}:{port}"


class InterfaceCollection(FluentCollection[NetworkInterface]):
    def sort_by_traffic(self) -> InterfaceCollection:
        self.data = sorted(
            self.data,
            key=lambda i: i.bytes_sent_mb + i.bytes_recv_mb,
            reverse=True,
        )
        return self

    def summarize(self) -> str:
        return "\n".join(
            f"{i.name}: sent {i.bytes_sent_mb:.1f} MB, recv {i.bytes_recv_mb:.1f} MB"
            for i in self.data[:10]
        )

    def display(self, *, use_rich: bool | None = None) -> str:
        rows = [
            [i.name, f"{i.bytes_sent_mb:.1f}", f"{i.bytes_recv_mb:.1f}"]
            for i in self.data
        ]
        return display_table(
            "Network interfaces",
            ["Interface", "Sent MB", "Recv MB"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )


class ConnectionCollection(FluentCollection[Connection]):
    def listening(self) -> ConnectionCollection:
        self.data = [c for c in self.data if c.status == "LISTEN"]
        return self

    def established(self) -> ConnectionCollection:
        self.data = [c for c in self.data if c.status == "ESTABLISHED"]
        return self

    def on_port(self, port: int) -> ConnectionCollection:
        port_str = f":{port}"
        self.data = [
            c for c in self.data if port_str in c.local_addr or port_str in c.remote_addr
        ]
        return self

    def summarize(self) -> str:
        return "\n".join(
            f"{c.local_addr} -> {c.remote_addr} ({c.status}) pid={c.pid}"
            for c in self.data[:10]
        )

    def display(self, *, use_rich: bool | None = None, limit: int = 25) -> str:
        rows = [
            [c.local_addr, c.remote_addr, c.status, c.pid or ""]
            for c in self.data[:limit]
        ]
        return display_table(
            "Connections",
            ["Local", "Remote", "Status", "PID"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> None:
        export_table(
            path,
            ["local_addr", "remote_addr", "status", "pid"],
            [[c.local_addr, c.remote_addr, c.status, c.pid] for c in self.data],
            fmt=fmt,
        )


class NetworkManager:
    def interfaces(self) -> InterfaceCollection:
        counters = psutil.net_io_counters(pernic=True)
        items = [
            NetworkInterface(
                name,
                c.bytes_sent / 1024 / 1024,
                c.bytes_recv / 1024 / 1024,
            )
            for name, c in counters.items()
        ]
        return InterfaceCollection(items)

    def connections(self, kind: str = "inet") -> ConnectionCollection:
        conns: list[Connection] = []
        for c in psutil.net_connections(kind=kind):
            conns.append(
                Connection(
                    fd=c.fd if c.fd is not None else -1,
                    family=str(c.family),
                    type=str(c.type),
                    local_addr=_addr_to_str(c.laddr),
                    remote_addr=_addr_to_str(c.raddr),
                    status=c.status or "",
                    pid=c.pid,
                )
            )
        return ConnectionCollection(conns)
