"""Fluent builder for constructing workflows from chained calls."""

from __future__ import annotations

from serverkit.workflows.workflow import Workflow


class WorkflowBuilder:
    """Chains resource filters into workflow steps."""

    def __init__(self, name: str) -> None:
        self._workflow = Workflow(name)
        self._current_resource: str | None = None

    def processes(self) -> WorkflowBuilder:
        self._current_resource = "processes"
        return self

    def memory_above(self, mb: float) -> WorkflowBuilder:
        raise NotImplementedError

    def sort_by_memory(self) -> WorkflowBuilder:
        raise NotImplementedError

    def summarize(self) -> WorkflowBuilder:
        raise NotImplementedError

    def save(self) -> Workflow:
        raise NotImplementedError

    def build(self) -> Workflow:
        return self._workflow
