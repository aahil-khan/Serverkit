"""Unit tests for Dev 2 shell parser and completer (no live SSH)."""

from __future__ import annotations

from unittest.mock import MagicMock

from serverkit.config import Config
from serverkit.processes.process import Process
from serverkit.processes.manager import ProcessCollection
from serverkit.shell.autocomplete import SDKCompleter
from serverkit.shell.parser import (
    apply_step_command,
    extract_number,
    extract_string_arg,
    format_processes,
    parse_input,
)
from serverkit.workflows.builder import WorkflowBuilder


class _MiniState:
    """Minimal stand-in for ReplState in parser unit tests."""

    def __init__(self, active: object, server: object | None = None) -> None:
        self.active = active
        self.server = server if server is not None else active
        self.remote = None

    def close_remote(self) -> None:
        return None


def _fake_processes():
    return ProcessCollection(
        [
            Process(1, "python", 1200.0, 12.0),
            Process(2, "nginx", 80.0, 0.5),
        ]
    )


def test_extract_number():
    assert extract_number("processes.memory_above(500)") == 500.0
    assert extract_number("processes.memory_above(12.5)") == 12.5


def test_extract_string_arg_logs():
    assert extract_string_arg('logs("/tmp/a.log").errors()', "logs") == "/tmp/a.log"
    assert extract_string_arg("logs('b').warnings()", "logs") == "b"


def test_format_processes_empty():
    assert "No processes" in format_processes([])


def test_parse_help():
    active = MagicMock()
    out = parse_input("help", _MiniState(active))
    assert "processes.all()" in out


def test_parse_unknown():
    active = MagicMock()
    out = parse_input("not_a_command", _MiniState(active))
    assert "Unknown command" in out


def test_parse_processes_all():
    active = MagicMock()
    active.processes.side_effect = _fake_processes
    out = parse_input("processes.all()", _MiniState(active))
    assert "python" in out
    assert "1200" in out


def test_parse_processes_memory_above():
    active = MagicMock()
    active.processes.side_effect = _fake_processes
    out = parse_input("processes.memory_above(500)", _MiniState(active))
    assert "python" in out
    assert "nginx" not in out


def test_apply_step_command_unknown():
    b = WorkflowBuilder("t")
    msg = apply_step_command(b, "nope")
    assert msg is not None and "Unknown" in msg


def test_apply_step_command_processes_summarize():
    b = WorkflowBuilder("t2")
    assert apply_step_command(b, "processes") is None
    assert apply_step_command(b, "memory_above 100") is None
    assert apply_step_command(b, "summarize") is None


def test_sdk_completer_yields_processes_prefix():
    comp = SDKCompleter()
    doc = MagicMock()
    doc.text_before_cursor = "proc"
    names = [c.text for c in comp.get_completions(doc, None)]
    assert any(n.startswith("processes") for n in names)


def test_sdk_completer_nested_logs():
    comp = SDKCompleter()
    doc = MagicMock()
    doc.text_before_cursor = "logs"
    names = [c.text for c in comp.get_completions(doc, None)]
    assert any("logs(" in n for n in names)


def test_parse_ask_invokes_analyzer(monkeypatch):
    from serverkit import Server
    from serverkit.shell.state import ReplState

    monkeypatch.setattr(
        "serverkit.ai.analyzer.Analyzer.ask",
        lambda self, q: f"stub:{q}",
    )
    state = ReplState(Server())
    out = parse_input("ask list hungry processes", state)
    assert out == "stub:list hungry processes"


def test_parse_import_calls_server():
    class S:
        _config = Config()

        def import_workflow(self, name: str) -> None:
            self.last = name

    srv = S()
    out = parse_input("import memory_audit", _MiniState(srv, server=srv))
    assert "Imported" in out
    assert srv.last == "memory_audit"
