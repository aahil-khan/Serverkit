"""Shared display and export helpers for collections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from serverkit.output.exporters import export_data
from serverkit.output.tables import render_table

if TYPE_CHECKING:
    from serverkit.config import Config


def resolve_use_rich(use_rich: bool | None = None, config: Config | None = None) -> bool:
    """Use explicit flag, else ~/.serverkit/config.json output.use_rich."""
    if use_rich is not None:
        return use_rich
    from serverkit.config import Config as ConfigCls

    cfg = config or ConfigCls.load()
    return bool(cfg.get("output", "use_rich", default=True))


def display_table(
    title: str,
    columns: list[str],
    rows: list[list],
    *,
    use_rich: bool | None = None,
    config: Config | None = None,
) -> str:
    return render_table(
        title, columns, rows, use_rich=resolve_use_rich(use_rich, config)
    )


def export_table(
    path: str,
    columns: list[str],
    rows: list[list],
    fmt: str = "csv",
) -> None:
    export_data(path, columns, rows, fmt=fmt)
