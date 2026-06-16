"""Unit tests for Analyzer (stub Ollama, mock server)."""

from __future__ import annotations

import json
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


def test_extract_largest_files_windows_unquoted_path():
    from serverkit.ai.analyzer import _extract_largest_files_path_and_limit

    got = _extract_largest_files_path_and_limit("largest files in C:\\Windows\\Temp limit 8")
    assert got is not None
    path, lim = got
    assert path.upper().startswith("C:")
    assert "Temp" in path
    assert lim == 8


def test_ask_weather_does_not_return_ram_summary():
    srv = _server_mock()
    stub = _StubOllama('{"resource": "memory", "filters": []}')
    a = Analyzer(srv, ollama=stub)
    out = a.ask("what is the weather")
    assert "RAM:" not in out
    assert "weather question" in out.lower() or "mispick" in out.lower()


def test_ask_list_processes_when_model_returns_memory_json():
    srv = _server_mock()
    stub = _StubOllama('{"resource": "memory", "filters": []}')
    a = Analyzer(srv, ollama=stub)
    out = a.ask("list processes")
    assert "RAM:" not in out
    assert "python" in out.lower() or "nginx" in out.lower()


def test_ask_show_ram_still_returns_memory():
    snap = MagicMock()
    snap.summarize.return_value = "RAM: ok"
    srv = _server_mock()
    srv.memory = MagicMock(return_value=snap)
    a = Analyzer(srv, ollama=_StubOllama("SHOULD_NOT"))
    out = a.ask("show ram")
    assert "RAM: ok" in out


def test_largest_files_empty_scan_message():
    srv = MagicMock()
    srv._config = Config()
    fe = MagicMock()
    fe.summarize.return_value = ""
    dc = MagicMock()
    dc.largest_files.return_value = fe
    srv.disk.return_value = dc
    a = Analyzer(srv, ollama=MagicMock())
    out = a._run_action(
        {"resource": "disk", "filters": [{"action": "largest_files", "value": "/tmp", "limit": 3}]},
        user_query="largest files in /tmp",
    )
    assert "No files returned" in out


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


def test_ask_conversational_how_are_you_skips_intent_json():
    stub = _StubOllama("I'm doing well — how can I help with this server?")
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("how are you")
    assert "well" in out.lower() or "help" in out.lower()
    assert len(stub.prompts) == 1
    assert "Output ONE JSON object" not in stub.prompts[0]


def test_ask_what_is_the_time_skips_llm():
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("what is the time")
    assert "SHOULD_NOT" not in out
    assert stub.prompts == []
    assert "local time" in out.lower()
    assert any(ch.isdigit() for ch in out)


def test_ask_list_workflows_skips_llm():
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("list workflows")
    assert "SHOULD_NOT" not in out
    assert stub.prompts == []
    assert "Saved workflows" in out
    assert "Catalog templates" in out


def test_ask_to_list_the_workflows_skips_llm():
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("to list the workflows")
    assert stub.prompts == []
    assert "Saved workflows" in out


def test_ask_list_catalog_skips_llm():
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("list catalog")
    assert stub.prompts == []
    assert "Catalog templates" in out


def test_ask_show_memory_skips_llm():
    snap = MagicMock()
    snap.summarize.return_value = "RAM: 1/8 GB (12.0%)"
    srv = _server_mock()
    srv.memory = MagicMock(return_value=snap)
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("show memory")
    assert "SHOULD_NOT" not in out
    assert stub.prompts == []
    assert out == "RAM: 1/8 GB (12.0%)"
    srv.memory.assert_called_once()


def test_ask_listening_ports_skips_llm():
    pc = MagicMock()
    pc.listening.return_value = pc
    pc.summarize.return_value = ":80 LISTEN"
    srv = _server_mock()
    srv.ports = MagicMock(return_value=pc)
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("listening ports")
    assert stub.prompts == []
    assert ":80" in out
    pc.listening.assert_called_once()


def test_ask_port_number_skips_llm():
    pc = MagicMock()
    pc.listening.return_value = pc
    pc.port.return_value = pc
    pc.summarize.return_value = ":443 LISTEN"
    srv = _server_mock()
    srv.ports = MagicMock(return_value=pc)
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("port 443")
    assert stub.prompts == []
    assert "443" in out
    pc.port.assert_called_once_with(443)


def test_ask_suspicious_cron_skips_llm():
    cc = MagicMock()
    cc.suspicious_only.return_value = cc
    cc.summarize.return_value = "(no suspicious jobs)"
    srv = _server_mock()
    srv.cron = MagicMock(return_value=cc)
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("suspicious cron")
    assert stub.prompts == []
    assert "suspicious" in out.lower() or "jobs" in out.lower()
    cc.suspicious_only.assert_called_once()


def test_ask_suspicoius_cron_typo_still_skips_llm():
    cc = MagicMock()
    cc.suspicious_only.return_value = cc
    cc.summarize.return_value = "CronJob(...)"
    srv = _server_mock()
    srv.cron = MagicMock(return_value=cc)
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("suspicoius cron")
    assert stub.prompts == []
    assert "CronJob" in out or "cron" in out.lower()
    cc.suspicious_only.assert_called_once()


def test_ask_logged_in_users_skips_llm():
    sess = MagicMock()
    sess.summarize.return_value = "UserSession(user='u', tty='pts/0', host='-', login_at='1')"
    mgr = MagicMock()
    mgr.logged_in.return_value = sess
    srv = _server_mock()
    srv.users = MagicMock(return_value=mgr)
    stub = _StubOllama("SHOULD_NOT_BE_USED")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("logged in users")
    assert stub.prompts == []
    assert "UserSession" in out or "u" in out
    mgr.logged_in.assert_called_once()


def test_run_action_ports_empty_shows_hint():
    pc = MagicMock()
    pc.listening.return_value = pc
    pc.port.return_value = pc
    pc.summarize.return_value = ""
    srv = MagicMock()
    srv._config = Config()
    srv.ports.return_value = pc
    a = Analyzer(srv, ollama=MagicMock())
    out = a._run_action(
        {"resource": "ports", "filters": [{"action": "listening"}, {"action": "port", "value": 443}]},
        user_query="port 443",
    )
    assert "No sockets matched" in out


def test_run_action_memory_ports_users_json():
    pc = MagicMock()
    pc.listening.return_value = pc
    pc.summarize.return_value = "ports ok"
    snap = MagicMock()
    snap.summarize.return_value = "mem ok"
    sess = MagicMock()
    sess.summarize.return_value = "user ok"
    mgr = MagicMock()
    mgr.logged_in.return_value = sess
    srv = MagicMock()
    srv._config = Config()
    srv.ports.return_value = pc
    srv.memory.return_value = snap
    srv.users.return_value = mgr
    stub = MagicMock()
    a = Analyzer(srv, ollama=stub)
    assert (
        a._run_action(
            {"resource": "memory", "filters": []},
            user_query="show memory",
        )
        == "mem ok"
    )
    assert (
        a._run_action({"resource": "ports", "filters": [{"action": "listening"}]}, user_query="x")
        == "ports ok"
    )
    assert (
        a._run_action({"resource": "users", "filters": [{"action": "logged_in"}]}, user_query="x")
        == "user ok"
    )


def test_ask_empty_resource_json_falls_back_to_chat():
    class _TwoShot(_StubOllama):
        def __init__(self) -> None:
            super().__init__("")
            self._n = 0

        def ask(self, prompt: str, **kwargs) -> str:
            self.prompts.append(prompt)
            self._n += 1
            if self._n == 1:
                return '{"resource": "", "filters": []}'
            return "Hey there!"

    stub = _TwoShot()
    a = Analyzer(_server_mock(), ollama=stub)
    out = a.ask("just saying hi")
    assert "Hey" in out or "there" in out


def test_run_action_logs_not_found_falls_back_when_user_line_is_time_question(monkeypatch):
    from serverkit.exceptions import LogFileNotFound

    srv = MagicMock()
    srv._config = Config()
    srv.logs.side_effect = LogFileNotFound("Log not found: /var/log")

    stub = MagicMock()
    stub.ask.return_value = "SHOULD_NOT_USE_LLM_FOR_TIME"

    a = Analyzer(srv, ollama=stub)
    out = a._run_action(
        {"resource": "logs", "path": "/var/log", "filters": []},
        user_query="what is the time",
    )
    assert "SHOULD_NOT" not in out
    assert "local time" in out.lower()
    stub.ask.assert_not_called()
    srv.logs.assert_called_once_with("/var/log")


def test_run_action_logs_not_found_falls_back_when_user_line_is_chatty(monkeypatch):
    from serverkit.exceptions import LogFileNotFound

    srv = MagicMock()
    srv._config = Config()
    srv.logs.side_effect = LogFileNotFound("Log not found: /var/log/auth.log")

    stub = MagicMock()
    stub.ask.return_value = "Hey! Ask me about processes, memory, or disk on this machine."

    a = Analyzer(srv, ollama=stub)
    out = a._run_action(
        {"resource": "logs", "path": "/var/log/auth.log", "filters": []},
        user_query="how are you",
    )
    assert "Hey" in out or "processes" in out.lower()
    stub.ask.assert_called()
    srv.logs.assert_called_once_with("/var/log/auth.log")


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
      "executor": "parallel",
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
    assert "parallel" in out
    assert "deprecated" in out.lower()
    assert (wf_dir / "ai_mem_test.json").exists()
    saved = json.loads((wf_dir / "ai_mem_test.json").read_text(encoding="utf-8"))
    assert saved.get("executor") == "parallel"


def test_analyzer_deterministic_disk_usage():
    srv = MagicMock()
    srv._config = Config()
    dc = MagicMock()
    dc.usage_above.return_value = dc
    dc.summarize.return_value = "disk summary"
    srv.disk.return_value = dc
    stub = _StubOllama("SHOULD_NOT")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("show disks above 50 percent")
    assert out == "disk summary"
    dc.usage_above.assert_called_once_with(50.0)
    assert stub.prompts == []


def test_analyzer_deterministic_largest_files():
    srv = MagicMock()
    srv._config = Config()
    fe = MagicMock()
    fe.summarize.return_value = "files here"
    dc = MagicMock()
    dc.largest_files.return_value = fe
    srv.disk.return_value = dc
    a = Analyzer(srv, ollama=_StubOllama("SHOULD_NOT"))
    out = a.ask('largest files in "/tmp" limit 5')
    assert out == "files here"
    dc.largest_files.assert_called_once_with("/tmp", limit=5)


def test_analyzer_process_history_deterministic(monkeypatch):
    srv = MagicMock()
    srv._config = Config()
    srv.processes.side_effect = [
        ProcessCollection([Process(1, "a", 10, 1)]),
        ProcessCollection([Process(1, "a", 50, 2), Process(3, "new", 1, 0)]),
    ]
    monkeypatch.setattr("serverkit.ai.analyzer.time.sleep", lambda _s: None)
    stub = _StubOllama("SHOULD_NOT")
    a = Analyzer(srv, ollama=stub)
    out = a.ask("diff processes wait 1 sec")
    assert "Appeared" in out
    assert "Changed" in out
    assert stub.prompts == []


def test_analyzer_disk_intent_json():
    srv = MagicMock()
    srv._config = Config()
    dc = MagicMock()
    dc.usage_above.return_value = dc
    dc.summarize.return_value = "from json"
    srv.disk.return_value = dc
    json_line = '{"resource": "disk", "filters": [{"action": "usage_above", "value": 88}]}'
    a = Analyzer(srv, ollama=_StubOllama(json_line))
    out = a.ask("show disk situation")
    assert out == "from json"
    dc.usage_above.assert_called_once_with(88.0)


def test_server_ask_delegates(monkeypatch):
    from serverkit import Server

    monkeypatch.setattr(
        "serverkit.ai.analyzer.Analyzer.ask",
        lambda self, q: f"stub:{q}",
    )
    s = Server()
    assert s.ask("ping") == "stub:ping"
