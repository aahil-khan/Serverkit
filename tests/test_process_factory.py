"""Milestone 2a: ProcessFactory (mocked psutil — no real OS required)."""

from unittest.mock import MagicMock

import psutil

from serverkit.processes.factory import ProcessFactory


def test_create_maps_psutil_fields_to_process():
    mock_proc = MagicMock(spec=psutil.Process)
    mock_proc.pid = 42
    mock_proc.oneshot.return_value.__enter__ = MagicMock(return_value=None)
    mock_proc.oneshot.return_value.__exit__ = MagicMock(return_value=False)
    mock_proc.name.return_value = "myapp"
    mock_proc.memory_info.return_value = MagicMock(rss=150 * 1024 * 1024)
    mock_proc.cpu_percent.return_value = 7.5

    process = ProcessFactory.create(mock_proc)

    assert process is not None
    assert process.pid == 42
    assert process.name == "myapp"
    assert process.memory_mb == 150.0
    assert process.cpu_percent == 7.5


def test_create_returns_none_when_process_vanished():
    mock_proc = MagicMock(spec=psutil.Process)
    mock_proc.oneshot.side_effect = psutil.NoSuchProcess(99)

    assert ProcessFactory.create(mock_proc) is None


def test_create_returns_none_on_permission_denied():
    mock_proc = MagicMock(spec=psutil.Process)
    mock_proc.oneshot.side_effect = psutil.AccessDenied(99)

    assert ProcessFactory.create(mock_proc) is None
