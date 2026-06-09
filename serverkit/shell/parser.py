"""Parse shell input strings into SDK calls (Dev 2)."""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING

from serverkit.exceptions import (
    LogFileNotFound,
    OptionalDependencyError,
    RemoteConnectionError,
    ServerKitError,
    WorkflowNotFound,
)
from serverkit.workflows.builder import WorkflowBuilder
from serverkit.workflows.manager import WorkflowManager

if TYPE_CHECKING:
    from serverkit.shell.state import ReplState

HELP_TEXT = """ServerKit shell — commands (see docs/DEV2_CONTRACTS.md)

  help                          Show this help
  exit                          Leave the shell

Processes (chain uses active target: local or connected remote):
  processes.all()
  processes.memory_above(N)
  processes.cpu_above(N)
  processes.named("name")
  processes.sort_by_memory().all()
  processes.sort_by_cpu().all()

Logs:
  logs("path").errors()         Summarize ERROR lines
  logs("path").warnings()
  logs("path").summarize()
  logs("path").tail(N)

Memory:
  memory                        RAM / swap summary

Workflows:
  workflow create NAME          Interactive builder (local save)
  workflow list                 Saved workflows in ~/.serverkit/workflows/
  workflow run NAME             Run on active target
  catalog                       Bundled template names
  import NAME                   Import catalog template by name
  run NAME [--dry-run]          Run saved workflow

Remote (requires: pip install serverkit[remote]):
  connect HOST [--user U] [--key PATH] [--port N]
  disconnect

Tab completion lists common SDK strings.
"""


def extract_number(text: str) -> float:
    match = re.search(r"\(\s*(\d+\.?\d*)\s*\)", text)
    return float(match.group(1)) if match else 0.0


def extract_string_arg(text: str, func_name: str) -> str | None:
    """Parse first string literal inside func_name(...)."""
    idx = text.find(f"{func_name}(")
    if idx < 0:
        return None
    start = idx + len(func_name) + 1
    rest = text[start:]
    m = re.match(r'\s*(["\'])(.*?)\1', rest, re.DOTALL)
    if m:
        return m.group(2)
    return None


def format_processes(procs: list) -> str:
    if not procs:
        return "No processes found."
    lines = [
        f"{p.name:<24} {p.memory_mb:>10.1f} MB  CPU: {p.cpu_percent:>6.1f}%  PID: {p.pid}"
        for p in procs
    ]
    return "\n".join(lines)


def _terminal_log_summary(state: "ReplState", path: str) -> str:
    lf = state.active.logs(path)
    return lf.summarize()


def _apply_log_chain(state: "ReplState", path: str, chain: str) -> str:
    """chain examples: .errors(), .warnings(), .tail(20), .summarize()."""
    lf = state.active.logs(path)
    tail = chain
    while tail:
        tail = tail.strip()
        if not tail:
            break
        if tail.startswith(".errors()"):
            lf = lf.errors()
            tail = tail[len(".errors()") :]
        elif tail.startswith(".warnings()"):
            lf = lf.warnings()
            tail = tail[len(".warnings()") :]
        elif tail.startswith(".summarize()"):
            return lf.summarize()
        elif tail.startswith(".summarise()"):
            return lf.summarise()
        elif tail.startswith(".tail("):
            close = tail.find(")")
            if close < 0:
                return "Malformed .tail( — missing closing )"
            chunk = tail[: close + 1]
            n = int(extract_number(chunk))
            lf = lf.tail(n)
            tail = tail[close + 1 :]
        elif tail.startswith(".display()"):
            return lf.display()
        elif tail.startswith(".all()"):
            lines = lf.all()
            return "\n".join(lines) if lines else "(no lines)"
        else:
            break
    return lf.summarize()


def apply_step_command(builder: WorkflowBuilder, step: str) -> str | None:
    """Map a builder step line to WorkflowBuilder methods. Returns error message or None."""
    parts = shlex.split(step.strip())
    if not parts:
        return "Empty step; try: processes, memory_above 500, summarize, save"
    cmd = parts[0].lower()
    try:
        if cmd == "processes":
            builder.processes()
        elif cmd == "logs" and len(parts) >= 2:
            builder.logs(parts[1])
        elif cmd == "memory_above" and len(parts) >= 2:
            builder.memory_above(float(parts[1]))
        elif cmd == "cpu_above" and len(parts) >= 2:
            builder.cpu_above(float(parts[1]))
        elif cmd == "named" and len(parts) >= 2:
            builder.named(parts[1])
        elif cmd == "sort_by_memory":
            builder.sort_by_memory()
        elif cmd == "sort_by_cpu":
            builder.sort_by_cpu()
        elif cmd == "errors":
            builder.errors()
        elif cmd == "warnings":
            builder.warnings()
        elif cmd == "log_contains" and len(parts) >= 2:
            builder.log_contains(parts[1])
        elif cmd == "tail" and len(parts) >= 2:
            builder.tail(int(parts[1]))
        elif cmd == "summarize":
            builder.summarize()
        else:
            return (
                f"Unknown step {cmd!r}. Try: processes, logs PATH, memory_above N, "
                "cpu_above N, named NAME, sort_by_memory, errors, warnings, tail N, summarize"
            )
    except Exception as exc:  # builder validation
        return f"Step failed: {exc}"
    return None


def run_workflow_builder(name: str, state: "ReplState") -> str:
    print(f"Workflow builder: {name}")
    print("Enter steps (see help). Type save when done, cancel to abort.")
    print(
        "Examples: processes | memory_above 500 | sort_by_memory | summarize\n"
        "          logs /var/log/syslog | errors | tail 20 | summarize"
    )
    builder = state.server.workflow(name)
    while True:
        try:
            raw = input("step> ").strip()
        except EOFError:
            return "Cancelled (EOF)."
        if not raw:
            continue
        if raw == "save":
            builder.save()
            return f"Workflow saved: {name}"
        if raw == "cancel":
            return "Cancelled."
        err = apply_step_command(builder, raw)
        if err:
            print(err)


def _parse_connect_args(rest: list[str]) -> tuple[str, str | None, str | None, int]:
    if not rest:
        raise ValueError("connect: host required")
    host = rest[0]
    user = None
    key_path = None
    port = 22
    i = 1
    while i < len(rest):
        if rest[i] == "--user" and i + 1 < len(rest):
            user = rest[i + 1]
            i += 2
        elif rest[i] == "--key" and i + 1 < len(rest):
            key_path = rest[i + 1]
            i += 2
        elif rest[i] == "--port" and i + 1 < len(rest):
            port = int(rest[i + 1])
            i += 2
        else:
            raise ValueError(f"connect: unknown argument {rest[i]!r}")
    return host, user, key_path, port


def parse_input(text: str, state: "ReplState") -> str | None:
    """Translate one line of shell input into a string to print, or None."""
    text = text.strip()
    if not text:
        return None

    # --- Meta / contracts (DEV2_CONTRACTS) ---
    if text == "help":
        return HELP_TEXT

    if text == "catalog":
        names = WorkflowManager().list_catalog()
        return "\n".join(names) if names else "(no catalog templates)"

    if text.startswith("import ") and not text.startswith("import_workflow"):
        name = text[len("import ") :].strip()
        if not name:
            return "Usage: import CATALOG_NAME"
        state.server.import_workflow(name)
        return f"Imported catalog workflow {name!r} to ~/.serverkit/workflows/"

    if text.startswith("run "):
        rest = shlex.split(text[len("run ") :])
        if not rest:
            return "Usage: run WORKFLOW_NAME [--dry-run]"
        dry = False
        name_parts: list[str] = []
        for tok in rest:
            if tok == "--dry-run":
                dry = True
            else:
                name_parts.append(tok)
        if not name_parts:
            return "Usage: run WORKFLOW_NAME [--dry-run]"
        wf_name = name_parts[0]
        result = state.active.run(wf_name, dry_run=dry)
        return _format_workflow_result(result)

    if text.startswith("connect "):
        try:
            from serverkit import Server

            rest = shlex.split(text[len("connect ") :])
            host, user, key_path, port = _parse_connect_args(rest)
            state.close_remote()
            state.remote = Server.connect(
                host, user=user, key_path=key_path, port=port, config=state.server._config
            )
            return f"Connected to {host!r} as {state.remote.user!r} (remote is active)."
        except OptionalDependencyError as exc:
            return f"{exc}\nInstall with: pip install serverkit[remote]"
        except RemoteConnectionError as exc:
            return f"Connection failed: {exc}"
        except ValueError as exc:
            return str(exc)

    if text == "disconnect":
        if state.remote is None:
            return "Not connected."
        host = getattr(state.remote, "host", "remote")
        state.close_remote()
        return f"Disconnected from {host!r}. Using local server."

    if text == "memory":
        snap = state.active.memory()
        return snap.summarize() + "\n\n" + snap.display()

    # --- PDF: processes ---
    if text == "processes.all()":
        procs = state.active.processes().all()
        return format_processes(procs)

    if text.startswith("processes.memory_above("):
        n = extract_number(text)
        procs = state.active.processes().memory_above(n).all()
        return format_processes(procs)

    if text.startswith("processes.cpu_above("):
        n = extract_number(text)
        procs = state.active.processes().cpu_above(n).all()
        return format_processes(procs)

    if text.startswith("processes.named("):
        name = extract_string_arg(text, "processes.named")
        if name is None:
            return "Usage: processes.named(\"name\")"
        procs = state.active.processes().named(name).all()
        return format_processes(procs)

    if text.startswith("processes.sort_by_memory()"):
        col = state.active.processes().sort_by_memory()
        if ".all()" in text:
            return format_processes(col.all())
        return col.summarize() + "\n\n" + col.display()

    if text.startswith("processes.sort_by_cpu()"):
        col = state.active.processes().sort_by_cpu()
        if ".all()" in text:
            return format_processes(col.all())
        return col.summarize() + "\n\n" + col.display()

    # --- PDF: logs ---
    if "logs(" in text:
        path = extract_string_arg(text, "logs")
        if path is None:
            return "Could not parse log path. Use logs(\"/path/to.log\")."
        idx = text.find(")")
        if idx < 0:
            return "Malformed logs(...)"
        chain = text[idx + 1 :].strip()
        try:
            if not chain:
                return _terminal_log_summary(state, path)
            return _apply_log_chain(state, path, chain)
        except LogFileNotFound as exc:
            return str(exc)

    # --- PDF: workflow ---
    if text.startswith("workflow create "):
        name = text[len("workflow create ") :].strip()
        if not name:
            return "Usage: workflow create NAME"
        return run_workflow_builder(name, state)

    if text == "workflow list":
        workflows = WorkflowManager().list()
        return "\n".join(workflows) if workflows else "No workflows saved."

    if text.startswith("workflow run "):
        name = text[len("workflow run ") :].strip()
        if not name:
            return "Usage: workflow run NAME"
        result = state.active.run(name)
        return _format_workflow_result(result)

    return f"Unknown command: {text}\nType help for a list of commands."


def _format_workflow_result(result: dict) -> str:
    if not result:
        return "(workflow finished — empty context)"
    # Prefer human-readable summary if present
    summary = result.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    lines = [f"{k}: {v!r}" for k, v in result.items() if not k.startswith("_")]
    return "\n".join(lines) if lines else repr(result)


def format_user_error(exc: BaseException) -> str:
    if isinstance(exc, ServerKitError):
        return str(exc)
    return f"Error: {exc}"
