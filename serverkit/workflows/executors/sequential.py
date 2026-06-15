from __future__ import annotations

from serverkit.workflows.executors.base import WorkflowExecutor


class SequentialExecutor(WorkflowExecutor):
    def execute(self, workflow, server, *, dry_run: bool = False) -> dict:
        from datetime import datetime, timezone

        from serverkit.shell.style import get_active_style

        style = get_active_style()
        context: dict = {"_server": server, "dry_run": dry_run}
        steps = list(workflow.steps)
        total = len(steps)
        for index, step in enumerate(steps, start=1):
            name = step.__class__.__name__
            if context.pop("_skip_next", False):
                print(style.workflow_skip(index, total, name))
                continue
            print(style.workflow_running(index, total, name))
            if dry_run:
                print(style.workflow_dry_run(str(step.to_dict())))
                continue
            context = step.execute(context)
            print(style.workflow_done(index, total, name))
        workflow.last_run = datetime.now(timezone.utc).isoformat()
        return context
