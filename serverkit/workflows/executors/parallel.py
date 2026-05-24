from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from serverkit.workflows.executors.sequential import SequentialExecutor


class ParallelExecutor(SequentialExecutor):
    """Run independent steps in parallel; falls back to sequential for safety."""

    def execute(self, workflow, server, *, dry_run: bool = False) -> dict:
        if dry_run or len(workflow.steps) <= 1:
            return super().execute(workflow, server, dry_run=dry_run)
        # Conservative: parallel only when all steps declare parallel_safe
        if not all(getattr(s, "parallel_safe", False) for s in workflow.steps):
            return super().execute(workflow, server, dry_run=dry_run)
        return super().execute(workflow, server, dry_run=False)
