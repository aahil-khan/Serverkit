"""SDK-aware tab completion (Dev 2) — deterministic static dictionary, no AI."""

from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion

# Completions from a static map (PDF). Keys: line prefix → candidate suffixes.
_SDK_COMPLETIONS: dict[str, list[str]] = {
    "": [
        "ask ",
        "processes",
        "logs",
        "workflow",
        "run",
        "import",
        "catalog",
        "connect",
        "disconnect",
        "memory",
        "help",
        "exit",
    ],
    "processes": [
        "processes.all()",
        "processes.named(",
        "processes.memory_above(",
        "processes.cpu_above(",
        "processes.sort_by_memory().all()",
        "processes.sort_by_cpu().all()",
    ],
    "logs": [
        'logs("/var/log/syslog").errors()',
        'logs("app.log").warnings()',
        'logs("app.log").summarize()',
        'logs("app.log").tail(20)',
    ],
    "workflow": [
        "workflow create ",
        "workflow list",
        "workflow run ",
    ],
    "run": [
        "run ",
    ],
    "import": [
        "import ",
    ],
    "connect": [
        "connect ",
    ],
}


def _longest_matching_prefix(text: str) -> str:
    best = ""
    for prefix in _SDK_COMPLETIONS:
        if not prefix:
            continue
        if text.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    return best


class SDKCompleter(Completer):
    """Complete common ServerKit shell tokens (offline, no introspection)."""

    def get_completions(self, document, complete_event):  # noqa: ARG002
        text = document.text_before_cursor
        prefix = _longest_matching_prefix(text)
        candidates = _SDK_COMPLETIONS.get(prefix, _SDK_COMPLETIONS[""])
        for candidate in candidates:
            if candidate.startswith(text):
                yield Completion(candidate, start_position=-len(text))
