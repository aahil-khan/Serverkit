"""Export tabular data to CSV, JSON, or HTML."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Sequence


def export_data(
    path: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    fmt: str = "csv",
) -> None:
    fmt = fmt.lower()
    out = Path(path)

    if fmt == "json":
        records = [dict(zip(columns, row)) for row in rows]
        out.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return

    if fmt == "csv":
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        return

    if fmt == "html":
        head = "".join(f"<th>{c}</th>" for c in columns)
        body_rows = []
        for row in rows:
            cells = "".join(f"<td>{cell}</td>" for cell in row)
            body_rows.append(f"<tr>{cells}</tr>")
        html = (
            "<table border='1'><thead><tr>"
            f"{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
        )
        out.write_text(html, encoding="utf-8")
        return

    raise ValueError(f"Unsupported export format: {fmt}")
