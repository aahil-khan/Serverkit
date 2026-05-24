"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from serverkit.processes.process import Process


@pytest.fixture
def fake_processes() -> list[Process]:
    return [
        Process(1, "python", 1200.0, 12.0),
        Process(2, "postgres", 800.0, 4.0),
        Process(3, "nginx", 120.0, 0.5),
    ]


@pytest.fixture
def workflow_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr("serverkit.workflows.workflow.WORKFLOW_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def mock_psutil_process():
    """Build a mock psutil.Process with configurable fields."""

    def _make(
        pid: int = 1,
        name: str = "python",
        rss: int = 100 * 1024 * 1024,
        cpu: float = 5.0,
    ):
        proc = MagicMock()
        proc.pid = pid
        proc.oneshot.return_value.__enter__ = MagicMock(return_value=None)
        proc.oneshot.return_value.__exit__ = MagicMock(return_value=False)
        proc.name.return_value = name
        proc.memory_info.return_value = MagicMock(rss=rss)
        proc.cpu_percent.return_value = cpu
        proc.username.return_value = "testuser"
        proc.ppid.return_value = 0
        proc.children.return_value = []
        return proc

    return _make
