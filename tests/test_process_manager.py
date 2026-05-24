"""Milestone 2b: ProcessManager against the live process table."""

import os

from serverkit import Server
from serverkit.processes.manager import ProcessManager
from serverkit.processes.process import Process


def test_manager_returns_nonempty_collection():
    collection = ProcessManager().all()
    processes = collection.all()

    assert len(processes) > 0
    assert all(isinstance(p, Process) for p in processes)
    assert all(p.pid > 0 for p in processes)
    assert all(p.memory_mb >= 0 for p in processes)


def test_server_processes_delegates_to_manager():
    """Milestone 3 preview: Server is a thin facade over ProcessManager."""
    processes = Server().processes().all()
    assert len(processes) > 0
    assert any(p.pid == os.getpid() for p in processes)
