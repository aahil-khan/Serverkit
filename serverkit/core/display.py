"""Shared display and export helpers for collections."""

from __future__ import annotations

from serverkit.output.exporters import export_data
from serverkit.output.tables import render_table


def display_table(
    title: str,
    columns: list[str],
    rows: list[list],
    *,
    use_rich: bool = True,
) -> str:
    return render_table(title, columns, rows, use_rich=use_rich)


def export_table(
    path: str,
    columns: list[str],
    rows: list[list],
    fmt: str = "csv",
) -> None:
    export_data(path, columns, rows, fmt=fmt)
