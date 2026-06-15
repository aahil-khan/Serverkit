"""Rich table rendering with plain-text fallback."""

from __future__ import annotations

from typing import Any, Sequence

from serverkit.exceptions import OptionalDependencyError


def render_table(
    title: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    use_rich: bool = True,
) -> str:
    if use_rich:
        try:
            from rich.console import Console
            from rich.table import Table
        except ImportError as exc:
            raise OptionalDependencyError(
                "Install rich: pip install serverkit[rich]"
            ) from exc
        from serverkit.shell.style import get_active_style

        style = get_active_style()
        border = style.rich_border()
        table = Table(
            title=title,
            border_style=border,
            header_style=f"bold {border}",
            title_style=border,
            row_styles=["", "dim"],
        )
        for col in columns:
            table.add_column(col, style="white")
        for row in rows:
            table.add_row(*[str(cell) for cell in row])
        console = Console(record=True, width=120)
        with console.capture() as capture:
            console.print(table)
        return capture.get().rstrip()

    lines = [title, " | ".join(columns), "-" * 40]
    for row in rows:
        lines.append(" | ".join(str(cell) for cell in row))
    return "\n".join(lines)
