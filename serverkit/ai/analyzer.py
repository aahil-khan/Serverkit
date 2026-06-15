"""Natural-language → SDK actions via Ollama (Dev 2)."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from serverkit.ai.jsonutil import parse_model_json
from serverkit.ai.ollama_client import DEFAULT_MODEL, OllamaClient
from serverkit.workflows.workflow import Workflow

if TYPE_CHECKING:
    from serverkit.logs.logfile import LogFile
    from serverkit.processes.manager import ProcessCollection


def _extract_largest_files_path_and_limit(query: str) -> tuple[str, int] | None:
    """Match ``largest files in|under|at PATH`` with optional ``limit N`` / ``top N``."""
    ql = query.lower()
    if "largest" not in ql or "files" not in ql:
        return None
    for pattern in (
        r"largest\s+files\s+(?:in|under|at)\s+\"([^\"]+)\"",
        r"largest\s+files\s+(?:in|under|at)\s+'([^']+)'",
        r"largest\s+files\s+(?:in|under|at)\s+(/\S+)",
    ):
        m = re.search(pattern, query, re.IGNORECASE)
        if m:
            path = m.group(1).strip()
            if not path:
                return None
            lm = re.search(r"(?:limit|top)\s+(\d+)\b", ql)
            lim = int(lm.group(1)) if lm else 20
            return path, max(1, min(lim, 500))
    return None


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

    def _intent_prompt(self, query: str) -> str:
        return f"""You are a Linux server assistant. Output ONE JSON object only. No markdown, no comments, no prose before or after.

Rules:
- Use double quotes for all keys and string values.
- Do not include MongoDB fields (_id, ObjectId), pipelines, or example databases.
- "filters" is an array of objects, each with "action" (string) and optional "value" (number or string).
- At most 6 filters. Keep the object small.

Schema:
{{"resource": "processes" | "logs" | "disk" | "process_history", "path": "<only if resource is logs>", "delay_seconds": <optional number for process_history>, "filters": [{{"action": "...", "value": ..., "limit": <optional int>}}]}}

Process actions: memory_above, cpu_above, named, sort_by_memory, sort_by_cpu
Log actions: errors, warnings, contains, tail, summarize
Disk partition actions: usage_above, mount_contains, sort_by_used (chain then summarize)
Disk terminal action: largest_files with "value" = root path string, optional "limit" (number)
process_history: empty filters or omit; optional delay_seconds between two snapshots (default 0)

Examples:
Query: show python processes using more than 1GB RAM
JSON: {{"resource": "processes", "filters": [{{"action": "named", "value": "python"}}, {{"action": "memory_above", "value": 1000}}]}}

Query: list processes with cpu above 10 percent
JSON: {{"resource": "processes", "filters": [{{"action": "cpu_above", "value": 10}}]}}

Query: show disk partitions above 80 percent
JSON: {{"resource": "disk", "filters": [{{"action": "usage_above", "value": 80}}]}}

Query: largest files in /var/log limit 10
JSON: {{"resource": "disk", "filters": [{{"action": "largest_files", "value": "/var/log", "limit": 10}}]}}

Query: what processes changed in the last second
JSON: {{"resource": "process_history", "delay_seconds": 1, "filters": []}}

Query: {query}
Output JSON on one line only, max 320 characters, no markdown fences.
JSON:"""

    def _try_deterministic_intent(self, query: str) -> str | None:
        """Answer common process questions without LLM (avoids small-model JSON drift)."""
        q = query.lower()
        m = re.search(
            r"cpu\s*(?:above|over|>|greater\s+than)\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?\b",
            q,
        )
        if m:
            return self._run_action(
                {
                    "resource": "processes",
                    "filters": [{"action": "cpu_above", "value": float(m.group(1))}],
                }
            )
        m = re.search(
            r"(?:memory|ram)\s*(?:above|over|>|greater\s+than)\s*(\d+(?:\.\d+)?)\s*(?:mb|m\b|gb|gig)?\b",
            q,
        )
        if m:
            return self._run_action(
                {
                    "resource": "processes",
                    "filters": [{"action": "memory_above", "value": float(m.group(1))}],
                }
            )
        m = re.search(
            r"(?:processes|apps)\s+(?:named|called|for|matching)\s+['\"]?([a-z0-9._-]+)['\"]?",
            q,
        )
        if m:
            return self._run_action(
                {
                    "resource": "processes",
                    "filters": [{"action": "named", "value": m.group(1)}],
                }
            )
        if (
            "process history" in q
            or re.search(r"\bdiff\s+processes\b", q)
            or re.search(r"processes?\s+that\s+(?:appeared|disappeared)\b", q)
            or re.search(r"what\s+process(?:es)?\s+changed\b", q)
        ):
            delay = 0.0
            dm = re.search(
                r"(?:after|wait)\s+(\d+(?:\.\d+)?)\s*(?:s(?:ec(?:ond)?s?)?)?\b",
                q,
            )
            if dm:
                delay = float(dm.group(1))
            return self._run_action(
                {"resource": "process_history", "delay_seconds": delay, "filters": []}
            )
        m = re.search(
            r"(?:disks?|disk\s+usage|partitions?)\s+(?:usage\s+)?(?:above|over|>|greater\s+than)\s*(\d+(?:\.\d+)?)\s*(?:%|percent)?\b",
            q,
        )
        if m:
            return self._run_action(
                {
                    "resource": "disk",
                    "filters": [{"action": "usage_above", "value": float(m.group(1))}],
                }
            )
        path_lim = _extract_largest_files_path_and_limit(query)
        if path_lim is not None:
            root, lim = path_lim
            return self._run_action(
                {
                    "resource": "disk",
                    "filters": [{"action": "largest_files", "value": root, "limit": lim}],
                }
            )
        return None

    def _execute_intent(self, query: str) -> str:
        direct = self._try_deterministic_intent(query)
        if direct is not None:
            return direct
        prompt = self._intent_prompt(query)
        raw = self._ollama.ask(
            prompt,
            temperature=0.05,
            num_predict=360,
            stop=["```", "\n\nThe ", "\n\n## "],
        )
        action = parse_model_json(raw)
        if action is None:
            cpu_n = re.search(
                r"cpu\s*(?:above|over|>|greater\s+than)\s*(\d+(?:\.\d+)?)",
                query.lower(),
            )
            mem_n = re.search(
                r"(?:memory|ram)\s*(?:above|over|>|greater\s+than)\s*(\d+(?:\.\d+)?)",
                query.lower(),
            )
            if cpu_n:
                repair = (
                    "Output exactly this JSON and nothing else (no markdown, no prose): "
                    f'{{"resource":"processes","filters":[{{"action":"cpu_above","value":{float(cpu_n.group(1))}}}]}}'
                )
            elif mem_n:
                repair = (
                    "Output exactly this JSON and nothing else: "
                    f'{{"resource":"processes","filters":[{{"action":"memory_above","value":{float(mem_n.group(1))}}}]}}'
                )
            else:
                repair = (
                    "Your previous answer was not valid JSON. Reply with ONE JSON object only, "
                    "same schema as before, under 400 characters. No // comments. No MongoDB.\n"
                    f"User query: {query}\n"
                    f"Broken output (trimmed): {raw[:500]!r}\n"
                    'Correct example: {{"resource":"processes","filters":[{{"action":"cpu_above","value":10}}]}}'
                )
            raw2 = self._ollama.ask(
                repair,
                temperature=0.0,
                num_predict=120,
                stop=["```", "\n"],
            )
            action = parse_model_json(raw2)
            if action is None:
                fallback = self._try_deterministic_intent(query)
                if fallback is not None:
                    return fallback
                return (
                    "Could not parse model JSON (even after retry). "
                    "Try a larger model in config `ollama.model`, or rephrase.\n\n"
                    f"First response:\n{raw}\n\nRetry:\n{raw2}"
                )
        return self._run_action(action)

    def _run_action(self, action: dict[str, Any]) -> str:
        resource = action.get("resource")
        if resource == "process_history":
            delay = action.get("delay_seconds")
            if delay is None:
                delay = action.get("delay")
            try:
                delay_f = float(delay) if delay is not None else 0.0
            except (TypeError, ValueError):
                delay_f = 0.0
            return self._run_process_history(delay_f)
        if resource == "disk":
            return self._run_disk_action(action)
        if resource == "processes":
            collection: ProcessCollection = self.server.processes()
            for f in self._normalized_filters(action.get("filters")):
                collection = self._apply_process_filter(collection, f)
            return collection.summarize()
        if resource == "logs":
            path = action.get("path") or action.get("log_path")
            if not path:
                return "Missing logs path in JSON (expected 'path')."
            log: LogFile = self.server.logs(path)
            for f in self._normalized_filters(action.get("filters")):
                log = self._apply_log_filter(log, f)
            return log.summarize()
        return f"Unsupported resource: {resource!r}"

    def _run_process_history(self, delay_seconds: float) -> str:
        from serverkit.processes.history import ProcessHistory

        before = list(self.server.processes().all())
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        after = list(self.server.processes().all())
        diff = ProcessHistory.diff(before, after)
        return ProcessHistory.format_diff(diff)

    def _run_disk_action(self, action: dict[str, Any]) -> str:
        from serverkit.disk.manager import DiskCollection

        coll: DiskCollection = self.server.disk()
        filters = self._normalized_filters(action.get("filters"))
        for f in filters:
            act = f.get("action")
            if act == "largest_files":
                path = str(f.get("value") or "")
                if not path:
                    return "largest_files filter requires string path in 'value'."
                try:
                    lim = int(f.get("limit") or 20)
                except (TypeError, ValueError):
                    lim = 20
                lim = max(1, min(lim, 500))
                return coll.largest_files(path, limit=lim).summarize()
            coll = self._apply_disk_filter(coll, f)
        return coll.summarize()

    @staticmethod
    def _apply_disk_filter(coll: Any, f: dict[str, Any]) -> Any:
        act = f.get("action")
        val = f.get("value")
        if act == "usage_above":
            return coll.usage_above(float(val))
        if act == "mount_contains":
            return coll.mount_contains(str(val))
        if act == "sort_by_used":
            return coll.sort_by_used()
        return coll

    @staticmethod
    def _normalized_filters(filters: Any) -> list[dict[str, Any]]:
        if not isinstance(filters, list):
            return []
        out: list[dict[str, Any]] = []
        for item in filters:
            if isinstance(item, dict) and isinstance(item.get("action"), str):
                out.append(item)
        return out

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
        return self._ollama.ask(prompt, temperature=0.4, num_predict=400)

    def _workflow_prompt(self, query: str) -> str:
        return f"""Convert this request into ONE ServerKit workflow JSON object.
Return ONLY valid JSON. No markdown, no // comments, no text before or after.

Required keys: schema_version (2), name, created_at (null), last_run (null), steps (array).

Example steps for high-memory audit:
{{
  "schema_version": 2,
  "name": "high_memory_audit",
  "created_at": null,
  "last_run": null,
  "steps": [
    {{"type": "process_filter", "memory_above": 500, "cpu_above": null, "named": null}},
    {{"type": "sort", "field": "memory"}},
    {{"type": "summary"}}
  ]
}}

Step types allowed: process_filter, sort, log_filter, tail, summary, export, chain, conditional
process_filter fields: memory_above, cpu_above, named (use null for unused).

Request: {query}
JSON:"""

    def _generate_workflow(self, query: str) -> str:
        prompt = self._workflow_prompt(query)
        raw = self._ollama.ask(prompt, temperature=0.05, num_predict=700)
        wf_data = parse_model_json(raw)
        if wf_data is None:
            raw2 = self._ollama.ask(
                "Return only valid JSON for a workflow (schema_version 2, name, steps). "
                "No // comments. No keys except JSON. Under 800 bytes.\n"
                f"Broken output:\n{raw[:700]}",
                temperature=0.0,
                num_predict=600,
            )
            wf_data = parse_model_json(raw2)
            if wf_data is None:
                return f"Failed to parse workflow JSON.\nRaw:\n{raw}\n\nRetry:\n{raw2}"
        try:
            wf = Workflow.from_dict(wf_data)
            wf.save()
            return f"Workflow created and saved: {wf.name}"
        except Exception as exc:
            return f"Failed to generate workflow: {exc}\nRaw:\n{raw}"
