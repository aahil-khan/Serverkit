"""Workflow definition, persistence, and execution."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from serverkit.workflows.step import WorkflowStep

WORKFLOW_DIR = os.path.expanduser("~/.serverkit/workflows/")


class Workflow:
    """Named pipeline of steps, saved as JSON under ~/.serverkit/workflows/."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.steps: list[WorkflowStep] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_run: str | None = None

    def add_step(self, step: WorkflowStep) -> Workflow:
        self.steps.append(step)
        return self

    def run(self) -> dict:
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> Workflow:
        raise NotImplementedError

    def export(self, path: str) -> None:
        raise NotImplementedError
