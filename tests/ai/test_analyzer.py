"""Unit tests for Analyzer (stub Ollama, mock server)."""

from __future__ import annotations

from unittest.mock import MagicMock

from serverkit.config import Config
from serverkit.processes.process import Process
from serverkit.processes.manager import ProcessCollection
from serverkit.ai.analyzer import Analyzer
from serverkit.ai.jsonutil import parse_model_json


def test_parse_model_json_fenced():
    raw = """```json
{"resource": "processes", "filters": []}
```"""
    out = parse_model_json(raw)
    assert out == {"resource": "processes", "filters": []}


def test_parse_model_json_prefix_chatter():
    raw = 'Sure thing. {"resource": "processes", "filters": []}'
    out = parse_model_json(raw)
    assert out == {"resource": "processes", "filters": []}


class _StubOllama:
    def __init__(self, response: str) -> None:
        self._response = response
        self.prompts: list[str] = []

    def ask(self, prompt: str, **kwargs) -> str:
        self.prompts.append(prompt)
        return self._response


def _server_mock():
    srv = MagicMock()
    srv._config = Config()

    def _procs():
        return ProcessCollection(
            [
                Process(1, "python", 900.0, 1.0),
                Process(2, "nginx", 50.0, 0.1),
            ]
        )

    srv.processes.side_effect = _procs
    return srv


def test_analyzer_deterministic_cpu_skips_llm():
    srv = _server_mock()
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("list processes with cpu above 0.5 percent")
    assert "SHOULD_NOT" not in out
    assert stub.prompts == []
    assert "python" in out


def test_analyzer_intent_processes_json():
    json_line = '{"resource": "processes", "filters": [{"action": "memory_above", "value": 500}]}'
    stub = _StubOllama(json_line)
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("show heavy processes")
    assert "python" in out
    assert "nginx" not in out


def test_analyzer_diagnose_branch():
    stub = _StubOllama("Likely cause: many browser tabs.")
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("why is memory high? diagnose")
    assert "Likely cause" in out
    assert "python" in stub.prompts[0]


def test_analyzer_workflow_branch(monkeypatch, tmp_path):
    import serverkit.workflows.workflow as wf_mod

    wf_dir = tmp_path / "wf"
    wf_dir.mkdir()
    monkeypatch.setattr(wf_mod, "WORKFLOW_DIR", str(wf_dir) + "/")

    wf_json = """{
      "schema_version": 2,
      "name": "ai_mem_test",
      "created_at": null,
      "last_run": null,
      "steps": [
        { "type": "process_filter", "memory_above": 200, "cpu_above": null, "named": null },
        { "type": "sort", "field": "memory" },
        { "type": "summary" }
      ]
    }"""
    stub = _StubOllama(wf_json)
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("please make a workflow for high memory processes")
    assert "ai_mem_test" in out
    assert (wf_dir / "ai_mem_test.json").exists()


def test_server_ask_delegates(monkeypatch):
    from serverkit import Server

    monkeypatch.setattr(
        "serverkit.ai.analyzer.Analyzer.ask",
        lambda self, q: f"stub:{q}",
    )
    s = Server()
    assert s.ask("ping") == "stub:ping"
