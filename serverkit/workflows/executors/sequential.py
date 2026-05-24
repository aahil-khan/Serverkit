from __future__ import annotations

from serverkit.workflows.executors.base import WorkflowExecutor


class SequentialExecutor(WorkflowExecutor):
    def execute(self, workflow, server, *, dry_run: bool = False) -> dict:
        from datetime import datetime, timezone

        context: dict = {"_server": server, "dry_run": dry_run}
        for step in workflow.steps:
            print(f" Running: {step.__class__.__name__}")
            if dry_run:
                print(f"   [dry-run] would run {step.to_dict()}")
                continue
            context = step.execute(context)
        workflow.last_run = datetime.now(timezone.utc).isoformat()
        return context
