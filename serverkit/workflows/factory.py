"""Step type registry for workflow deserialization."""

from __future__ import annotations

from serverkit.workflows.step import WorkflowStep


class StepFactory:
    """Maps step type strings to WorkflowStep classes."""

    _registry: dict[str, type[WorkflowStep]] = {}

    @classmethod
    def register(cls, step_type: str, step_class: type[WorkflowStep]) -> None:
        cls._registry[step_type] = step_class

    @classmethod
    def create(cls, data: dict) -> WorkflowStep:
        step_type = data["type"]
        klass = cls._registry.get(step_type)
        if not klass:
            raise ValueError(f"Unknown step type: {step_type}")
        return klass.from_dict(data)
