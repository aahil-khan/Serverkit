"""Unit tests per workflow step type."""

from pathlib import Path

import pytest

import serverkit.workflows.steps  # noqa: F401
from serverkit.logs.logfile import LogFile
from serverkit.processes.manager import ProcessCollection
from serverkit.processes.process import Process
from serverkit.workflows.steps import (
    ChainStep,
    ConditionalStep,
    ExportStep,
    LogFilterStep,
    ProcessFilterStep,
    SortStep,
    SummaryStep,
    TailStep,
)
from serverkit.workflows.workflow import Workflow


@pytest.fixture
def log_path(tmp_path: Path) -> str:
    p = tmp_path / "app.log"
    p.write_text("INFO ok\nERROR bad\nWARNING hmm\n", encoding="utf-8")
    return str(p)


def test_process_filter_step():
    ctx = ProcessFilterStep(memory_above=100).execute(
        {"processes": ProcessCollection([Process(1, "a", 200, 1), Process(2, "b", 50, 1)])}
    )
    assert len(ctx["processes"].all()) == 1


def test_sort_step():
    ctx = SortStep(field="memory").execute(
        {"processes": ProcessCollection([Process(1, "a", 50, 1), Process(2, "b", 200, 1)])}
    )
    assert ctx["processes"].all()[0].name == "b"


def test_log_filter_step(log_path: str):
    ctx = LogFilterStep(path=log_path, level="error").execute({})
    assert "ERROR" in ctx["log_file"].all()[0]


def test_tail_step(log_path: str):
    ctx = TailStep(n=1).execute({"log_path": log_path})
    assert len(ctx["log_lines"]) == 1


def test_summary_step():
    ctx = SummaryStep().execute(
        {"processes": ProcessCollection([Process(1, "a", 100, 1)])}
    )
    assert "summary" in ctx


def test_export_step(tmp_path: Path):
    out = tmp_path / "out.txt"
    ExportStep(str(out)).execute({"summary": "hello"})
    assert out.read_text() == "hello"


def test_conditional_step():
    ctx = ConditionalStep(when="key_missing", key="missing").execute({})
    assert ctx.get("_skip_next") is True


def test_step_to_dict_round_trip():
    step = ProcessFilterStep(memory_above=500, named="python")
    restored = ProcessFilterStep.from_dict(step.to_dict())
    assert restored.memory_above == 500
    assert restored.named == "python"


def test_workflow_save_load_round_trip(workflow_dir, tmp_path: Path):
    wf = Workflow("roundtrip")
    wf.add_step(ProcessFilterStep(cpu_above=10))
    wf.add_step(SortStep(field="cpu"))
    wf.add_step(SummaryStep())
    wf.save(versioned=False)
    loaded = Workflow.from_dict(
        __import__("json").loads((workflow_dir / "roundtrip.json").read_text())
    )
    assert len(loaded.steps) == 3
    assert loaded.steps[0].cpu_above == 10
