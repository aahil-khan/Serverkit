from __future__ import annotations

import warnings

from serverkit.workflows.executors.sequential import SequentialExecutor


class ParallelExecutor(SequentialExecutor):
    """Deprecated: workflows share mutable context, so execution remains sequential."""

    def execute(self, workflow, server, *, dry_run: bool = False) -> dict:
        warnings.warn(
            "workflow.executor 'parallel' is deprecated: steps share one mutable "
            "context dict, so the engine always runs sequentially. Use "
            "'sequential' in ~/.serverkit/config.json.",
            UserWarning,
            stacklevel=2,
        )
        return super().execute(workflow, server, dry_run=dry_run)
