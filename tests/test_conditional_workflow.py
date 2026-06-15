import serverkit.workflows.steps  # noqa: F401
from serverkit.workflows.executors.sequential import SequentialExecutor
from serverkit.workflows.steps import ConditionalStep, SummaryStep
from serverkit.workflows.workflow import Workflow


def test_conditional_skips_next_step(capsys):
    wf = Workflow("skip-test")
    wf.add_step(ConditionalStep(when="key_missing", key="processes"))
    wf.add_step(SummaryStep())

    class StubServer:
        pass

    SequentialExecutor().execute(wf, StubServer())
    out = capsys.readouterr().out
    assert "[skip]" in out
    assert "SummaryStep" in out
