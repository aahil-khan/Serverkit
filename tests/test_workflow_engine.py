import pytest

import serverkit.workflows.steps  # noqa: F401
from serverkit.workflows.executors.parallel import ParallelExecutor
from serverkit.workflows.steps import ProcessFilterStep, SummaryStep
from serverkit.workflows.validator import validate_workflow, WorkflowValidationError
from serverkit.workflows.workflow import Workflow


def test_validate_rejects_empty_workflow():
    with pytest.raises(WorkflowValidationError):
        validate_workflow(Workflow("empty"))


def test_parallel_executor_warns_and_runs_sequentially(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("serverkit.workflows.workflow.WORKFLOW_DIR", str(tmp_path))
    wf = Workflow("par")
    wf.add_step(ProcessFilterStep(memory_above=1))
    wf.add_step(SummaryStep())
    from serverkit import Server

    with pytest.warns(UserWarning, match="parallel"):
        ctx = ParallelExecutor().execute(wf, Server(), dry_run=False)
    assert "summary" in ctx
    assert "Running: SummaryStep" in capsys.readouterr().out


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
