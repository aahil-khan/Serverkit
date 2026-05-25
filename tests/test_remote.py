"""Unit tests for remote SSH adapters (mocked paramiko)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from serverkit.exceptions import OptionalDependencyError, RemoteConnectionError
from serverkit.logs.logfile import LogFile
from serverkit.remote.connection import SSHConnection
from serverkit.remote.parsers import (
    memory_from_free_m,
    memory_from_psutil_json,
    processes_from_ps_aux,
    processes_from_psutil_json,
)
from serverkit.remote.server import RemoteServer


PS_AUX_SAMPLE = """USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
root 1 0.0 0.1 100 200 ? Ss Jan01 0:01 systemd
www 99 1.5 2.0 5000 8000 ? S Jan01 0:05 nginx
"""

FREE_SAMPLE = """              total        used        free      shared  buff/cache   available
Mem:           7936        2048        4096         100        1792        5500
Swap:          2048         256        1792
"""


def test_processes_from_psutil_json():
    payload = json.dumps(
        {
            "processes": [
                {
                    "pid": 42,
                    "name": "nginx",
                    "memory_mb": 12.5,
                    "cpu_percent": 1.2,
                    "ppid": 1,
                    "username": "www",
                }
            ]
        }
    )
    procs = processes_from_psutil_json(payload)
    assert len(procs) == 1
    assert procs[0].name == "nginx"
    assert procs[0].pid == 42


def test_processes_from_ps_aux():
    procs = processes_from_ps_aux(PS_AUX_SAMPLE)
    names = {p.name for p in procs}
    assert "nginx" in names or "nginx" in str(names)


def test_memory_from_free_m():
    data = memory_from_free_m(FREE_SAMPLE)
    assert data["total_mb"] == 7936
    assert data["used_mb"] == 2048


def test_memory_from_psutil_json():
    payload = json.dumps(
        {
            "memory": {
                "total_mb": 8000,
                "used_mb": 2000,
                "available_mb": 6000,
                "percent": 25.0,
                "swap_total_mb": 1000,
                "swap_used_mb": 100,
                "swap_percent": 10.0,
            }
        }
    )
    data = memory_from_psutil_json(payload)
    assert data["percent"] == 25.0


def test_logfile_from_lines():
    log = LogFile.from_lines(["ERROR one", "INFO two"], path="/var/log/app.log")
    assert len(log.errors().all()) == 1


class _MockChannel:
    def recv_exit_status(self):
        return 0


def _mock_stdout(text: str):
    stdout = MagicMock()
    stdout.channel = _MockChannel()
    stdout.read.return_value = text.encode("utf-8")
    return stdout


def _mock_stderr():
    stderr = MagicMock()
    stderr.read.return_value = b""
    return stderr


@pytest.fixture
def mock_connection():
    client = MagicMock()
    conn = SSHConnection(client, host="vm1.example", user="deploy")

    def run_side_effect(command, check=True):
        if "import psutil" in command and "echo ok" in command:
            return "ok\n"
        if "import json, psutil" in command:
            return json.dumps(
                {
                    "processes": [
                        {
                            "pid": 10,
                            "name": "python3",
                            "memory_mb": 50.0,
                            "cpu_percent": 2.0,
                            "ppid": 1,
                            "username": "root",
                        }
                    ],
                    "memory": {
                        "total_mb": 4096,
                        "used_mb": 1024,
                        "available_mb": 3000,
                        "percent": 25.0,
                        "swap_total_mb": 512,
                        "swap_used_mb": 0,
                        "swap_percent": 0.0,
                    },
                }
            )
        if command.strip() == "ps aux":
            return PS_AUX_SAMPLE
        if command.strip() == "free -m":
            return FREE_SAMPLE
        if command.startswith("tail") or command.startswith("cat"):
            return "ERROR remote failure\nINFO ok\n"
        return ""

    conn.run = MagicMock(side_effect=run_side_effect)
    return conn


def test_remote_server_processes_psutil(mock_connection):
    srv = RemoteServer(mock_connection)
    coll = srv.processes()
    assert len(coll.all()) >= 1
    assert coll.all()[0].name == "python3"


def test_remote_server_processes_ps_aux_fallback(mock_connection):
    mock_connection.run = MagicMock(
        side_effect=lambda cmd, check=True: (
            PS_AUX_SAMPLE if cmd.strip() == "ps aux" else ""
        )
    )
    srv = RemoteServer(mock_connection)
    srv._has_remote_psutil = lambda: False  # type: ignore[method-assign]
    coll = srv.processes()
    assert len(coll.all()) >= 1


def test_remote_server_memory_and_logs(mock_connection):
    srv = RemoteServer(mock_connection)
    mem = srv.memory()
    assert mem.total_mb == 4096
    log = srv.logs("/var/log/syslog")
    assert len(log.errors().all()) >= 1


def test_ssh_run_failure_raises():
    client = MagicMock()
    client.exec_command.return_value = (
        None,
        _mock_stdout(""),
        _mock_stderr(),
    )
    client.exec_command.return_value[1].channel.recv_exit_status = MagicMock(return_value=1)
    conn = SSHConnection(client, host="h", user="u")
    with pytest.raises(RemoteConnectionError):
        conn.run("false", check=True)


def test_optional_dependency_without_paramiko():
    with patch.dict("sys.modules", {"paramiko": None}):
        import importlib

        import serverkit.remote.connection as mod

        importlib.reload(mod)
        with pytest.raises(OptionalDependencyError):
            mod._paramiko()
