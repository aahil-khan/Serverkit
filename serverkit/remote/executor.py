"""Command execution protocol for local vs remote backends."""

from __future__ import annotations

from typing import Protocol


class CommandExecutor(Protocol):
    """Run shell commands and return stdout text."""

    def run(self, command: str, *, check: bool = True) -> str:
        """Execute command; raise on failure when check=True."""
