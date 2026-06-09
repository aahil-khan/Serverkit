"""Natural-language → SDK actions via Ollama (Dev 2)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from serverkit.ai.ollama_client import DEFAULT_MODEL, OllamaClient
from serverkit.workflows.workflow import Workflow

if TYPE_CHECKING:
    from serverkit.logs.logfile import LogFile
    from serverkit.processes.manager import ProcessCollection


def strip_model_json(raw: str) -> str:
    """Remove markdown fences; isolate outermost JSON object if model adds chatter."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1].strip()
    return text


class Analyzer:
    """Intent routing, diagnostics context, and workflow JSON generation."""

    def __init__(
        self,
        server: Any,
        model: str | None = None,
        *,
        ollama: OllamaClient | None = None,
    ) -> None:
        self.server = server
        cfg_model: str | None = None
        cfg_base: str | None = None
        if hasattr(server, "_config") and server._config is not None:
            cfg_model = server._config.get("ollama", "model", default=None)
        resolved_model = model or cfg_model or DEFAULT_MODEL
        self._ollama = ollama or OllamaClient(model=resolved_model, base_url=cfg_base)

    def ask(self, query: str) -> str:
        q = query.lower()
        if "create a workflow" in q or "make a workflow" in q:
            return self._generate_workflow(query)
        if any(w in q for w in ("why", "diagnose", "what is causing")):
            return self._diagnose(query)
        return self._execute_intent(query)

    def _execute_intent(self, query: str) -> str:
        prompt = f"""You are a Linux server assistant. Convert the user query into a JSON SDK action.
Return ONLY valid JSON, no markdown, no explanation.

Schema:
{{"resource": "processes"|"logs", "path": "<required if resource is logs>", "filters": [{{"action": "<name>", "value": <optional>}}]}}

Resources:
- processes — filters run on ProcessCollection
- logs — requires "path" to log file; filters run on LogFile

Filter actions for processes: memory_above, cpu_above, named, sort_by_memory, sort_by_cpu
Filter actions for logs: errors, warnings, contains (value=substring), tail (value=number), summarize

Examples:
Query: show python processes using more than 1GB RAM
JSON: {{"resource": "processes", "filters": [{{"action": "named", "value": "python"}}, {{"action": "memory_above", "value": 1000}}]}}

Query: summarize errors in /var/log/syslog
JSON: {{"resource": "logs", "path": "/var/log/syslog", "filters": [{{"action": "errors"}}, {{"action": "summarize"}}]}}

Query: {query}
JSON:"""
        raw = self._ollama.ask(prompt)
        try:
            action = json.loads(strip_model_json(raw))
        except json.JSONDecodeError:
            return f"Could not parse model JSON.\nRaw response:\n{raw}"
        return self._run_action(action)

    def _run_action(self, action: dict[str, Any]) -> str:
        resource = action.get("resource")
        if resource == "processes":
            collection: ProcessCollection = self.server.processes()
            for f in action.get("filters") or []:
                collection = self._apply_process_filter(collection, f)
            return collection.summarize()
        if resource == "logs":
            path = action.get("path") or action.get("log_path")
            if not path:
                return "Missing logs path in JSON (expected 'path')."
            log: LogFile = self.server.logs(path)
            for f in action.get("filters") or []:
                log = self._apply_log_filter(log, f)
            return log.summarize()
        return f"Unsupported resource: {resource!r}"

    def _apply_process_filter(self, collection: ProcessCollection, f: dict[str, Any]):
        act = f.get("action")
        val = f.get("value")
        if act == "memory_above":
            return collection.memory_above(float(val))
        if act == "cpu_above":
            return collection.cpu_above(float(val))
        if act == "named":
            return collection.named(str(val))
        if act == "sort_by_memory":
            return collection.sort_by_memory()
        if act == "sort_by_cpu":
            return collection.sort_by_cpu()
        return collection

    def _apply_log_filter(self, log: LogFile, f: dict[str, Any]):
        act = f.get("action")
        val = f.get("value")
        if act == "errors":
            return log.errors()
        if act == "warnings":
            return log.warnings()
        if act == "contains":
            return log.contains(str(val))
        if act == "tail":
            return log.tail(int(val))
        if act == "summarize":
            return log
        return log

    def _diagnose(self, query: str) -> str:
        procs = self.server.processes().sort_by_memory().all()[:10]
        proc_summary = "\n".join(
            f"{p.name}: {p.memory_mb:.0f}MB, CPU {p.cpu_percent:.1f}%" for p in procs
        )
        prompt = f"""You are a Linux server diagnostician.
Top 10 processes by memory:
{proc_summary}

User question: {query}

Give a clear, concise diagnosis in 3-5 lines."""
        return self._ollama.ask(prompt)

    def _generate_workflow(self, query: str) -> str:
        prompt = f"""Convert this request into a ServerKit workflow JSON.
Return ONLY valid JSON, no markdown, no explanation.

Required shape:
{{
  "schema_version": 2,
  "name": "workflow_name",
  "created_at": null,
  "last_run": null,
  "steps": [
    {{ "type": "process_filter", "memory_above": 1000, "cpu_above": null, "named": null }},
    {{ "type": "sort", "field": "memory" }},
    {{ "type": "summary" }}
  ]
}}

Allowed step types: process_filter, sort, log_filter, tail, summary, export, chain, conditional
Use null for unused fields in process_filter.

Request: {query}
JSON:"""
        raw = self._ollama.ask(prompt)
        try:
            wf_data = json.loads(strip_model_json(raw))
            wf = Workflow.from_dict(wf_data)
            wf.save()
            return f"Workflow created and saved: {wf.name}"
        except Exception as exc:
            return f"Failed to generate workflow: {exc}\nRaw:\n{raw}"
