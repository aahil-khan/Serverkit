"""Create, list, import, and run workflows."""

from __future__ import annotations

import os

from serverkit.workflows.builder import WorkflowBuilder
from serverkit.workflows.workflow import WORKFLOW_DIR, Workflow


class WorkflowManager:
    def create(self, name: str) -> WorkflowBuilder:
        return WorkflowBuilder(name)

    def run(self, name: str) -> dict:
        raise NotImplementedError

    def list(self) -> list[str]:
        if not os.path.exists(WORKFLOW_DIR):
            return []
        return [
            f.replace(".json", "")
            for f in os.listdir(WORKFLOW_DIR)
            if f.endswith(".json")
        ]

    def import_workflow(self, path: str) -> Workflow:
        raise NotImplementedError
