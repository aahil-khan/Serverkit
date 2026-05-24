import pytest

import serverkit.workflows.steps  # noqa: F401
from serverkit.workflows.steps import ProcessFilterStep, SummaryStep
from serverkit.workflows.validator import validate_workflow, WorkflowValidationError
from serverkit.workflows.workflow import Workflow


def test_validate_rejects_empty_workflow():
    with pytest.raises(WorkflowValidationError):
        validate_workflow(Workflow("empty"))


def test_dry_run_does_not_mutate(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("serverkit.workflows.workflow.WORKFLOW_DIR", str(tmp_path))
    wf = Workflow("dry")
    wf.add_step(ProcessFilterStep(memory_above=99999))
    wf.add_step(SummaryStep())
    from serverkit import Server

    ctx = wf.run(Server(), dry_run=True)
    assert ctx.get("dry_run") is True
    captured = capsys.readouterr()
    assert "dry-run" in captured.out
