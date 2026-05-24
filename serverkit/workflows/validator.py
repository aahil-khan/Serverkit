from __future__ import annotations

from typing import TYPE_CHECKING

from serverkit.exceptions import WorkflowValidationError
from serverkit.workflows.factory import StepFactory

if TYPE_CHECKING:
    from serverkit.workflows.workflow import Workflow


REQUIRED_FIELDS = {
    "process_filter": [],
    "sort": ["field"],
    "log_filter": [],
    "tail": ["n"],
    "summary": [],
    "export": ["path"],
    "chain": ["workflow"],
    "conditional": ["when", "key"],
}


def validate_workflow(workflow: Workflow) -> None:
    if not workflow.name:
        raise WorkflowValidationError("Workflow name is required")
    if not workflow.steps:
        raise WorkflowValidationError("Workflow must have at least one step")
    for step in workflow.steps:
        data = step.to_dict()
        step_type = data.get("type")
        if step_type not in REQUIRED_FIELDS:
            raise WorkflowValidationError(f"Unknown step type: {step_type}")
        for field in REQUIRED_FIELDS[step_type]:
            if field not in data or data[field] is None:
                raise WorkflowValidationError(
                    f"Step {step_type} missing required field: {field}"
                )


def validate_step_dict(data: dict) -> None:
    if "type" not in data:
        raise WorkflowValidationError("Step missing type")
    StepFactory.create(data)
