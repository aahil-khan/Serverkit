import json

import serverkit.workflows.steps  # noqa: F401
from serverkit.workflows.builder import WorkflowBuilder


def test_log_workflow_builder_json(workflow_dir):
    (
        WorkflowBuilder("log_audit")
        .logs("app.log")
        .errors()
        .tail(50)
        .summarize()
        .save()
    )
    data = json.loads((workflow_dir / "log_audit.json").read_text())
    types = [s["type"] for s in data["steps"]]
    assert types == ["log_filter", "tail", "summary"]
