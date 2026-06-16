"""Natural-language → SDK actions via Ollama (Dev 2)."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from serverkit.ai.jsonutil import parse_model_json
from serverkit.ai.ollama_client import DEFAULT_MODEL, OllamaClient
from serverkit.exceptions import LogFileNotFound
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
        # Unquoted Windows path: C:\dir\leaf — \S+ stops at the space before "limit N"
        r"largest\s+files\s+(?:in|under|at)\s+([A-Za-z]:\S+)",
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


_MEMORY_OFF_TOPIC = re.compile(
    r"\b(weather|forecast|humidity|snow|rain|tornado|hurricane|celsius|fahrenheit)\b",
    re.I,
)
_MEMORY_PROCESS_LIST = re.compile(
    r"\b(list|show)\s+process(?:ed|es|ing)?\b|\b(process|apps)\s+list\b",
    re.I,
)


def _looks_memory_usage_query(query: str) -> bool:
    """True only for clear RAM/swap snapshot questions (deterministic path)."""
    low = query.strip().lower()
    if not low or len(low) > 200:
        return False
    if _MEMORY_OFF_TOPIC.search(low) or _MEMORY_PROCESS_LIST.search(low):
        return False
    if low in ("ram", "memory", "mem"):
        return True
    return bool(
        re.search(r"\b(show|display|current|system)\s+(memory|ram)\b", low)
        or re.search(r"\bwhat\s+is\s+(the\s+)?(memory|ram)\b", low)
        or re.search(r"\b(memory|ram)\s+(usage|status|summary|use|info|stats)\b", low)
        or re.search(r"\bhow\s+much\s+(ram|memory)\b", low)
    )


def _memory_model_intent_plausible(user_query: str) -> bool:
    """Block small-model JSON that picks resource=memory for unrelated text."""
    low = user_query.strip().lower()
    if not low:
        return False
    if _MEMORY_OFF_TOPIC.search(low) or _MEMORY_PROCESS_LIST.search(low):
        return False
    if _looks_memory_usage_query(low):
        return True
    if len(low) <= 20 and low.isalpha() and not re.search(r"\b(ram|memory|swap)\b", low):
        return False
    return bool(re.search(r"\b(ram|memory|swap)\b", low))


_OPS_HINT = re.compile(
    r"\b(processes?|process|disk|disks?|logs?|log file|cpu|memory|ram|ports?|network|"
    r"systemd|services?|docker|cron|workflow|snapshot|kill|partition|usage|percent|"
    r"ssh|mount|tail|grep|mb|gb)\b",
    re.I,
)


def _looks_conversational_only(query: str) -> bool:
    """Short greetings / thanks with no obvious server-ops keywords."""
    text = query.strip()
    if not text or len(text) > 180:
        return False
    if _OPS_HINT.search(text):
        return False
    low = text.lower()
    patterns = (
        r"^(hi|hello|hey|howdy)\b",
        r"^good\s+(morning|afternoon|evening)\b",
        r"\bhow\s+('?re|are)\s+you\b",
        r"^what'?s\s+up\b",
        r"^(thanks|thank\s+you|thx)\b",
        r"^(bye|goodbye)\b",
        r"^who\s+are\s+you\b",
        r"^how\s+('?s|is)\s+it\s+going\b",
    )
    return any(re.search(p, low) for p in patterns)


def _looks_time_or_date_query(query: str) -> bool:
    """Short questions about local wall clock / calendar (not log line timestamps)."""
    text = query.strip()
    if not text or len(text) > 180:
        return False
    if _OPS_HINT.search(text):
        return False
    low = text.lower()
    patterns = (
        r"\bwhat(?:'s| is)\s+the\s+time\b",
        r"\bwhat\s+time\s+is\s+it\b",
        r"\bcurrent\s+time\b",
        r"\btime\s+right\s+now\b",
        r"\btell\s+me\s+the\s+time\b",
        r"\bwhat(?:'s| is)\s+today'?s\s+date\b",
        r"\bwhat\s+day\s+is\s+it\b",
        r"\bcurrent\s+date\b",
        r"\bwhat\s+is\s+the\s+date\b",
        r"\bwhat'?s\s+the\s+date\b",
    )
    return any(re.search(p, low) for p in patterns)


def _looks_ask_soft_query(query: str) -> bool:
    """Greetings, small talk, or simple local time/date — not log/diagnostic phrasing."""
    return _looks_conversational_only(query) or _looks_time_or_date_query(query)


def _local_time_date_reply() -> str:
    now = datetime.now().astimezone()
    tz = now.tzname() or "local"
    return (
        f"This machine's local time is {now:%Y-%m-%d %H:%M:%S} ({tz}). "
        "I focus on diagnostics here — say if you want processes, disk, memory, or logs."
    )


def _looks_catalog_list_query(query: str) -> bool:
    """`list catalog` / `show catalog` without the word 'workflow' (REPL parity)."""
    low = query.strip().lower()
    if not low or len(low) > 80:
        return False
    if re.search(r"\b(import|create|run|delete)\b", low):
        return False
    if re.search(r"\b(list|show)\s+catalog\b", low):
        return True
    if low == "catalog":
        return True
    return False


def _looks_workflow_inventory_query(query: str) -> bool:
    """User wants saved workflow names and/or catalog templates (not create/run)."""
    low = query.strip().lower()
    if not low or len(low) > 220:
        return False
    if re.search(r"\b(create|make|generate|run|execute|delete|remove|save|export)\b", low):
        return False
    if "workflow" not in low and "workflows" not in low:
        return False
    if re.search(
        r"(?:\b(list|show|display|get|print|see|enumerate|what\s+are|names?\s+of)\b.*\bworkflows?\b|"
        r"\bworkflows?\b.*\b(list|show|names?|saved|available|there|i\s+have)\b|"
        r"\bworkflow\s+list\b|\bto\s+list\s+the\s+workflows\b)",
        low,
    ):
        return True
    if re.search(r"\b(list|show)\b.*\b(catalog|templates?)\b", low) and "workflow" in low:
        return True
    if re.search(r"\bworkflow\s+(catalog|templates?)\b", low):
        return True
    return False


def _workflow_inventory_reply() -> str:
    from serverkit.workflows.manager import WorkflowManager

    wm = WorkflowManager()
    saved = wm.list()
    catalog = wm.list_catalog()
    lines = [
        "Saved workflows (~/.serverkit/workflows/):",
        ", ".join(saved) if saved else "(none)",
        "",
        "Catalog templates (`import NAME` in the REPL):",
        ", ".join(catalog) if catalog else "(none)",
    ]
    return "\n".join(lines)


_INTENT_RESOURCES = frozenset(
    {
        "process_history",
        "disk",
        "processes",
        "logs",
        "memory",
        "ports",
        "cron",
        "users",
    }
)


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
        if _looks_workflow_inventory_query(query) or _looks_catalog_list_query(query):
            return _workflow_inventory_reply()
        if any(w in q for w in ("why", "diagnose", "what is causing")):
            return self._diagnose(query)
        if _looks_time_or_date_query(query):
            return _local_time_date_reply()
        if _looks_conversational_only(query):
            return self._conversational_reply(query)
        return self._execute_intent(query)

    def _conversational_reply(self, query: str) -> str:
        """Brief natural-language reply (not JSON intent) for greetings and small talk."""
        if _looks_time_or_date_query(query):
            return _local_time_date_reply()
        prompt = (
            "You are ServerKit, a friendly assistant for Linux server operations. "
            "The user's message is casual conversation, not a request for live system data. "
            "Reply in 1–3 short sentences: warm and professional. "
            "You may mention you can help with processes, logs, disk, memory, workflows, etc. "
            "Do not invent metrics, hostnames, or command output.\n\n"
            f"User: {query.strip()}"
        )
        try:
            out = self._ollama.ask(
                prompt,
                temperature=0.65,
                num_predict=180,
                stop=["```", "\n\nUser:", "\n\n## "],
            )
            return (out or "").strip() or "Hello! Ask me about this machine's processes, memory, disk, or logs."
        except RuntimeError as exc:
            return (
                "Hello! I'm here to help with server checks (processes, memory, disk, logs, …). "
                f"I can't reach the language model right now: {exc}"
            )
    def _intent_prompt(self, query: str) -> str:
        return f"""You are a Linux server assistant. Output ONE JSON object only. No markdown, no comments, no prose before or after.

Rules:
- Use double quotes for all keys and string values.
- Do not include MongoDB fields (_id, ObjectId), pipelines, or example databases.
- "filters" is an array of objects, each with "action" (string) and optional "value" (number or string).
- At most 6 filters. Keep the object small.

Schema:
{{"resource": "processes" | "logs" | "disk" | "process_history" | "memory" | "ports" | "cron" | "users", "path": "<only if resource is logs>", "delay_seconds": <optional number for process_history>, "filters": [{{"action": "...", "value": ..., "limit": <optional int>}}]}}

Process actions: memory_above, cpu_above, named, sort_by_memory, sort_by_cpu
Log actions: errors, warnings, contains, tail, summarize
Disk partition actions: usage_above, mount_contains, sort_by_used (chain then summarize)
Disk terminal action: largest_files with "value" = root path string, optional "limit" (number)
process_history: empty filters or omit; optional delay_seconds between two snapshots (default 0)
memory: use {{"resource": "memory", "filters": []}} for RAM/swap summary (no filters).
ports: filters may include {{"action": "listening"}} (LISTEN sockets only), and/or {{"action": "port", "value": 443}} (filter by port number). If filters empty, default is listening-only.
cron: empty filters for all parsed jobs, or {{"action": "suspicious_only"}} for flagged jobs only.
users: {{"resource": "users", "filters": [{{"action": "logged_in"}}]}} for `who`-style sessions, or add {{"action": "failed_logins"}} (reads secure/auth log tail on Linux).

Examples:
Query: who is logged in
JSON: {{"resource": "users", "filters": [{{"action": "logged_in"}}]}}

Query: show memory usage
JSON: {{"resource": "memory", "filters": []}}

Query: what ports are listening
JSON: {{"resource": "ports", "filters": [{{"action": "listening"}}]}}

Query: show port 443
JSON: {{"resource": "ports", "filters": [{{"action": "listening"}}, {{"action": "port", "value": 443}}]}}

Query: suspicious cron jobs
JSON: {{"resource": "cron", "filters": [{{"action": "suspicious_only"}}]}}

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
                },
                user_query=query,
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
                },
                user_query=query,
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
                },
                user_query=query,
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
                {"resource": "process_history", "delay_seconds": delay, "filters": []},
                user_query=query,
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
                },
                user_query=query,
            )
        path_lim = _extract_largest_files_path_and_limit(query)
        if path_lim is not None:
            root, lim = path_lim
            return self._run_action(
                {
                    "resource": "disk",
                    "filters": [{"action": "largest_files", "value": root, "limit": lim}],
                },
                user_query=query,
            )
        if (
            re.search(r"\blogged\s+in\s+users?\b", q)
            or re.search(r"\busers?\s+(currently\s+)?logged\s+in\b", q)
            or re.search(r"\bwho\s+(is\s+)?(logged\s+in|online)\b", q)
            or re.search(r"\bactive\s+(login\s+)?sessions?\b", q)
        ):
            return self._run_action(
                {"resource": "users", "filters": [{"action": "logged_in"}]},
                user_query=query,
            )
        if _looks_memory_usage_query(q):
            return self._run_action({"resource": "memory", "filters": []}, user_query=query)
        if re.search(r"\blisten(?:ing)?\s+ports?\b", q) or re.search(
            r"\bports?\s+(?:that\s+are\s+)?listen(?:ing)?\b", q
        ):
            return self._run_action(
                {"resource": "ports", "filters": [{"action": "listening"}]},
                user_query=query,
            )
        pm = re.search(r"\bport\s+(\d{1,5})\b", q)
        if pm:
            n = int(pm.group(1))
            if 1 <= n <= 65535:
                return self._run_action(
                    {
                        "resource": "ports",
                        "filters": [{"action": "listening"}, {"action": "port", "value": n}],
                    },
                    user_query=query,
                )
        if re.search(r"\b(suspicious|suspicoius|suspicoious)\s+cron\b", q) or (
            re.search(r"\bcron\b", q)
            and re.search(r"\b(suspicious|suspicoius|suspicoious)\b", q)
        ):
            return self._run_action(
                {"resource": "cron", "filters": [{"action": "suspicious_only"}]},
                user_query=query,
            )
        if re.search(r"\b(show|list|display)\s+cron\b", q) or re.search(r"\bcron\s+jobs?\b", q):
            return self._run_action({"resource": "cron", "filters": []}, user_query=query)
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
                if _looks_ask_soft_query(query):
                    return self._conversational_reply(query)
                return (
                    "Could not parse model JSON (even after retry). "
                    "Try a larger model in config `ollama.model`, or rephrase.\n\n"
                    f"First response:\n{raw}\n\nRetry:\n{raw2}"
                )
        return self._run_action(action, user_query=query)

    def _run_action(self, action: dict[str, Any], *, user_query: str = "") -> str:
        resource = action.get("resource")
        if resource is None or (isinstance(resource, str) and not resource.strip()):
            return self._conversational_reply(user_query.strip() or "Hello")
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
        if resource == "memory":
            if not _memory_model_intent_plausible(user_query):
                low = user_query.strip().lower()
                if _MEMORY_OFF_TOPIC.search(low):
                    return (
                        "That looks like a general or weather question, not a RAM/swap check on this host. "
                        "For memory use `ask show memory` or `ask what is the ram`; for processes use `ask list processes`."
                    )
                if _looks_ask_soft_query(user_query):
                    return self._conversational_reply(user_query)
                return (
                    "That line was interpreted as RAM/swap, but it does not look like a memory question "
                    "(small models often mispick). Try `ask show memory` or `ask list processes`."
                )
            return self._run_memory_action()
        if resource == "ports":
            return self._run_ports_action(action)
        if resource == "cron":
            return self._run_cron_action(action)
        if resource == "users":
            return self._run_users_action(action)
        if resource == "processes":
            collection: ProcessCollection = self.server.processes()
            for f in self._normalized_filters(action.get("filters")):
                collection = self._apply_process_filter(collection, f)
            return collection.summarize()
        if resource == "logs":
            path = action.get("path") or action.get("log_path")
            if not path:
                return "Missing logs path in JSON (expected 'path')."
            try:
                log: LogFile = self.server.logs(path)
            except LogFileNotFound:
                if _looks_ask_soft_query(user_query):
                    return self._conversational_reply(user_query)
                raise
            for f in self._normalized_filters(action.get("filters")):
                log = self._apply_log_filter(log, f)
            return log.summarize()
        if resource not in _INTENT_RESOURCES:
            if _looks_ask_soft_query(user_query):
                return self._conversational_reply(user_query)
            return (
                f"Unsupported resource: {resource!r}. "
                "Try `help` in the REPL, or ask about processes, logs, disk, memory, ports, cron, users, or process_history."
            )

    def _run_memory_action(self) -> str:
        if not hasattr(self.server, "memory"):
            return "memory() is not available on this target."
        return self.server.memory().summarize()

    def _run_ports_action(self, action: dict[str, Any]) -> str:
        if not hasattr(self.server, "ports"):
            return "ports() is not available on this target."
        coll = self.server.ports()
        filters = self._normalized_filters(action.get("filters"))
        if not filters:
            coll = coll.listening()
        else:
            for f in filters:
                act = f.get("action")
                if act == "listening":
                    coll = coll.listening()
                elif act == "port":
                    try:
                        coll = coll.port(int(f.get("value")))
                    except (TypeError, ValueError):
                        return "ports filter 'port' requires a numeric 'value'."
        out = coll.summarize().strip()
        if not out:
            return (
                "No sockets matched this query (nothing listening on that port, filtered out, "
                "or psutil returned no rows). Try `ask listening ports` for a broader view."
            )
        return out

    def _run_cron_action(self, action: dict[str, Any]) -> str:
        if not hasattr(self.server, "cron"):
            return "cron() is not available on this target."
        coll = self.server.cron()
        for f in self._normalized_filters(action.get("filters")):
            if f.get("action") == "suspicious_only":
                coll = coll.suspicious_only()
        out = coll.summarize().strip()
        if not out:
            return (
                "No cron jobs in this view (on Windows, /etc/crontab is usually missing; "
                "on Linux, empty can mean no suspicious flags or unreadable paths). "
                "Try `ask show cron` for all parsed jobs."
            )
        return out

    def _run_users_action(self, action: dict[str, Any]) -> str:
        if not hasattr(self.server, "users"):
            return "users() is not available on this target."
        from serverkit.exceptions import ExternalCommandNotFound

        mgr = self.server.users()
        filters = self._normalized_filters(action.get("filters"))
        if any(f.get("action") == "failed_logins" for f in filters):
            coll = mgr.failed_logins()
            disp = coll.display().strip()
            if not disp:
                return "(No failed-login lines matched in the scanned log tail.)"
            return disp
        try:
            coll = mgr.logged_in()
            out = coll.summarize().strip()
        except ExternalCommandNotFound as exc:
            return (
                "Logged-in users come from the `who` command (common on Linux/macOS). "
                "On typical Windows installs `who` is not available — use `connect` to a Unix host, "
                f"or run `users.logged_in().summarize()` where supported.\n({exc})"
            )
        if not out:
            return "(No rows from `who` — no interactive sessions reported.)"
        return out

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
                out = coll.largest_files(path, limit=lim).summarize().strip()
                if not out:
                    return (
                        f"No files returned for largest-file scan under {path!r} "
                        "(empty directory, permissions, or scan skipped files)."
                    )
                return out
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

Optional key: executor — string "sequential" (default) or "parallel".
Use "sequential" unless the user explicitly wants the legacy parallel mode.
Note: "parallel" is deprecated (still runs steps in order, emits a runtime warning).

Example steps for high-memory audit:
{{
  "schema_version": 2,
  "name": "high_memory_audit",
  "executor": "sequential",
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
            ex = wf.executor if wf.executor else "default (config workflow.executor)"
            note = ""
            if wf.executor == "parallel":
                note = " Note: executor is 'parallel' (deprecated — same step order as sequential, emits a warning at run)."
            return f"Workflow created and saved: {wf.name} (executor: {ex}).{note}"
        except Exception as exc:
            return f"Failed to generate workflow: {exc}\nRaw:\n{raw}"
