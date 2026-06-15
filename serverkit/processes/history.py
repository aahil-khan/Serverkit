from __future__ import annotations

from dataclasses import dataclass

from serverkit.processes.process import Process


@dataclass
class ProcessHistoryDiff:
    appeared: list[Process]
    disappeared: list[Process]
    changed: list[tuple[Process, Process]]


class ProcessHistory:
    @staticmethod
    def format_diff(diff: ProcessHistoryDiff, *, limit: int = 25) -> str:
        """Human-readable summary for REPL / ``Analyzer`` output."""
        lines: list[str] = []
        if diff.appeared:
            lines.append("Appeared:")
            for p in diff.appeared[:limit]:
                lines.append(
                    f"  + pid {p.pid} {p.name} {p.memory_mb:.0f}MB CPU {p.cpu_percent:.1f}%"
                )
        if diff.disappeared:
            lines.append("Disappeared:")
            for p in diff.disappeared[:limit]:
                lines.append(
                    f"  - pid {p.pid} {p.name} {p.memory_mb:.0f}MB CPU {p.cpu_percent:.1f}%"
                )
        if diff.changed:
            lines.append("Changed (same pid, different metrics):")
            for b, a in diff.changed[:limit]:
                lines.append(
                    f"  ~ pid {a.pid} {a.name}: memory {b.memory_mb:.0f}→{a.memory_mb:.0f} MB, "
                    f"CPU {b.cpu_percent:.1f}→{a.cpu_percent:.1f}%"
                )
        if not lines:
            return "No process changes between snapshots (same PIDs and metrics)."
        return "\n".join(lines)

    @staticmethod
    def diff(before: list[Process], after: list[Process]) -> ProcessHistoryDiff:
        before_map = {p.pid: p for p in before}
        after_map = {p.pid: p for p in after}
        appeared = [after_map[pid] for pid in after_map if pid not in before_map]
        disappeared = [before_map[pid] for pid in before_map if pid not in after_map]
        changed = []
        for pid in before_map:
            if pid in after_map:
                b, a = before_map[pid], after_map[pid]
                if b.memory_mb != a.memory_mb or b.cpu_percent != a.cpu_percent:
                    changed.append((b, a))
        return ProcessHistoryDiff(appeared, disappeared, changed)
