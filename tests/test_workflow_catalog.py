"""Tests for bundled workflow catalog import."""

from __future__ import annotations

import json

import pytest

from serverkit import Server
from serverkit.exceptions import WorkflowNotFound
from serverkit.workflows import workflow as workflow_module


def test_list_catalog():
    from serverkit.workflows.manager import WorkflowManager

    names = WorkflowManager().list_catalog()
    assert "memory_audit" in names
    assert "nginx_health_check" in names


def test_import_from_catalog(workflow_dir, monkeypatch):
    monkeypatch.setattr(workflow_module, "WORKFLOW_DIR", workflow_dir)
    wf = Server().import_workflow("memory_audit")
    assert wf.name == "memory_audit"
    path = f"{workflow_dir}/memory_audit.json"
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["schema_version"] == 2
    assert any(s["type"] == "process_filter" for s in saved["steps"])


def test_import_unknown_catalog_raises():
    with pytest.raises(WorkflowNotFound):
        Server().import_workflow("nonexistent_template_xyz")
