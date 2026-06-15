"""REPL session state: local Server and optional RemoteServer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from serverkit.core.server import Server
    from serverkit.remote.server import RemoteServer
    from serverkit.shell.style import ShellStyle


class ReplState:
    """Holds the local SDK server and an optional active remote facade."""

    def __init__(self, server: Server, *, style: ShellStyle | None = None) -> None:
        self.server = server
        self.remote: RemoteServer | None = None
        if style is None:
            from serverkit.shell.style import ShellStyle as _ShellStyle

            style = _ShellStyle()
        self.style = style

    @property
    def active(self) -> Any:
        """Use for read-only SDK chains (processes, logs, memory, run, …)."""
        return self.remote if self.remote is not None else self.server

    def close_remote(self) -> None:
        if self.remote is not None:
            self.remote.close()
            self.remote = None
