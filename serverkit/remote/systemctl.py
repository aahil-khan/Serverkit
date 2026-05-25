"""systemctl over SSH."""

from __future__ import annotations

from serverkit.core.collection import FluentCollection
from serverkit.exceptions import ServiceNotFound
from serverkit.remote.connection import SSHConnection
from serverkit.remote.parsers import parse_systemctl_units
from serverkit.systemctl.service import Service


class RemoteSystemctlManager:
    """SystemctlManager-compatible API using a remote SSH executor."""

    def __init__(self, connection: SSHConnection) -> None:
        self._conn = connection

    def _run_systemctl(self, *args: str) -> str:
        cmd = "systemctl " + " ".join(args)
        try:
            return self._conn.run(cmd, check=True)
        except Exception as exc:
            raise ServiceNotFound(str(exc)) from exc

    def list_units(self) -> FluentCollection[Service]:
        from serverkit.systemctl.manager import ServiceCollection

        out = self._run_systemctl(
            "list-units", "--type=service", "--no-pager", "--no-legend"
        )
        return ServiceCollection(parse_systemctl_units(out))

    def status(self, name: str) -> str:
        return self._run_systemctl("status", name)

    def start(self, name: str) -> None:
        self._conn.run(f"systemctl start {name}", check=True)

    def stop(self, name: str) -> None:
        self._conn.run(f"systemctl stop {name}", check=True)

    def restart(self, name: str) -> None:
        self._conn.run(f"systemctl restart {name}", check=True)
