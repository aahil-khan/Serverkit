from __future__ import annotations

import os

from serverkit.core.display import display_table, resolve_use_rich


class EnvSnapshot:
    def __init__(self, data: dict[str, str] | None = None) -> None:
        self._data = dict(data or os.environ)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._data.get(key, default)

    def path_entries(self) -> list[str]:
        return self._data.get("PATH", "").split(os.pathsep)

    def contains(self, substring: str) -> EnvSnapshot:
        filtered = {k: v for k, v in self._data.items() if substring in v}
        return EnvSnapshot(filtered)

    def keys_matching(self, pattern: str) -> EnvSnapshot:
        needle = pattern.lower()
        filtered = {k: v for k, v in self._data.items() if needle in k.lower()}
        return EnvSnapshot(filtered)

    def all(self) -> dict[str, str]:
        return dict(self._data)

    def summarize(self) -> str:
        return f"{len(self._data)} environment variables"

    def summarise(self) -> str:
        return self.summarize()

    def display(self, *, use_rich: bool | None = None, limit: int = 30) -> str:
        items = sorted(self._data.items())[:limit]
        rows = [[k, v[:80]] for k, v in items]
        return display_table(
            "Environment",
            ["Variable", "Value"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def __repr__(self) -> str:
        return f"EnvSnapshot({len(self._data)} vars)"
