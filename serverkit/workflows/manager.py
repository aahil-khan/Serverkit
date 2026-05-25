"""Create, list, import, and run workflows."""

from __future__ import annotations

import json
import os
from importlib import resources

from serverkit.exceptions import WorkflowNotFound
from serverkit.workflows import workflow as workflow_module
from serverkit.workflows.builder import WorkflowBuilder
from serverkit.workflows.workflow import Workflow


class WorkflowManager:
    def create(self, name: str) -> WorkflowBuilder:
        return WorkflowBuilder(name)

    def run(
        self,
        name: str,
        *,
        dry_run: bool = False,
        executor: str | None = None,
        server=None,
    ) -> dict:
        path = os.path.join(workflow_module.WORKFLOW_DIR, f"{name}.json")
        if not os.path.exists(path):
            raise WorkflowNotFound(f"No workflow named {name!r}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        workflow = Workflow.from_dict(data)
        print(f"Running workflow: {workflow.name}")
        from serverkit import Server

        srv = server or Server()
        return workflow.run(srv, dry_run=dry_run, executor=executor)

    def list(self) -> list[str]:
        workflow_dir = workflow_module.WORKFLOW_DIR
        if not os.path.exists(workflow_dir):
            return []
        return sorted(
            f.replace(".json", "")
            for f in os.listdir(workflow_dir)
            if f.endswith(".json")
        )

    def list_versions(self, name: str) -> list[str]:
        versions_dir = os.path.join(workflow_module.WORKFLOW_DIR, name, "versions")
        if not os.path.exists(versions_dir):
            return []
        return sorted(os.listdir(versions_dir))

    def import_workflow(self, path: str) -> Workflow:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        workflow = Workflow.from_dict(data)
        workflow.save()
        return workflow

    def list_catalog(self) -> list[str]:
        """Return installable workflow template names from the bundled catalog."""
        catalog = resources.files("serverkit.workflows.catalog")
        return sorted(
            entry.name.removesuffix(".json")
            for entry in catalog.iterdir()
            if entry.name.endswith(".json")
        )

    def import_from_catalog(self, name: str) -> Workflow:
        """Load a bundled template by name and save it to the user workflow dir."""
        catalog_name = name if name.endswith(".json") else f"{name}.json"
        catalog = resources.files("serverkit.workflows.catalog")
        try:
            ref = catalog.joinpath(catalog_name)
            data = json.loads(ref.read_text(encoding="utf-8"))
        except (FileNotFoundError, TypeError, OSError) as exc:
            raise WorkflowNotFound(
                f"No catalog workflow named {name!r}. "
                f"Available: {', '.join(self.list_catalog()) or '(none)'}"
            ) from exc
        workflow = Workflow.from_dict(data)
        workflow.save()
        return workflow
