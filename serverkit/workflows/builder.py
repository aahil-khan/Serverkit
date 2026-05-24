"""Fluent builder for constructing workflows from chained calls."""

from __future__ import annotations

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


class WorkflowBuilder:
    """Chains resource filters into workflow steps."""

    def __init__(self, name: str) -> None:
        self._workflow = Workflow(name)
        self._current_resource: str | None = None
        self._log_path: str | None = None

    def processes(self) -> WorkflowBuilder:
        self._current_resource = "processes"
        self._log_path = None
        return self

    def logs(self, path: str) -> WorkflowBuilder:
        self._current_resource = "logs"
        self._log_path = path
        return self

    def memory_above(self, mb: float) -> WorkflowBuilder:
        self._workflow.add_step(ProcessFilterStep(memory_above=mb))
        return self

    def cpu_above(self, percent: float) -> WorkflowBuilder:
        self._workflow.add_step(ProcessFilterStep(cpu_above=percent))
        return self

    def named(self, name: str) -> WorkflowBuilder:
        self._workflow.add_step(ProcessFilterStep(named=name))
        return self

    def sort_by_memory(self) -> WorkflowBuilder:
        self._workflow.add_step(SortStep(field="memory"))
        return self

    def sort_by_cpu(self) -> WorkflowBuilder:
        self._workflow.add_step(SortStep(field="cpu"))
        return self

    def errors(self) -> WorkflowBuilder:
        self._workflow.add_step(
            LogFilterStep(path=self._log_path, level="error")
        )
        return self

    def warnings(self) -> WorkflowBuilder:
        self._workflow.add_step(
            LogFilterStep(path=self._log_path, level="warning")
        )
        return self

    def log_contains(self, keyword: str) -> WorkflowBuilder:
        self._workflow.add_step(
            LogFilterStep(path=self._log_path, contains=keyword)
        )
        return self

    def tail(self, n: int) -> WorkflowBuilder:
        self._workflow.add_step(TailStep(n=n))
        return self

    def summarize(self) -> WorkflowBuilder:
        self._workflow.add_step(SummaryStep())
        return self

    def export(self, path: str) -> WorkflowBuilder:
        self._workflow.add_step(ExportStep(path=path))
        return self

    def when_empty(self, key: str) -> WorkflowBuilder:
        """Skip the next step if context[key] is missing or empty."""
        self._workflow.add_step(ConditionalStep(when="context_empty", key=key))
        return self

    def when_missing(self, key: str) -> WorkflowBuilder:
        """Skip the next step if context[key] is not set."""
        self._workflow.add_step(ConditionalStep(when="key_missing", key=key))
        return self

    def then_run(self, workflow_name: str) -> WorkflowBuilder:
        """Chain another saved workflow after this one."""
        self._workflow.add_step(ChainStep(workflow=workflow_name))
        return self

    def save(self) -> Workflow:
        self._workflow.save()
        return self._workflow

    def build(self) -> Workflow:
        return self._workflow
