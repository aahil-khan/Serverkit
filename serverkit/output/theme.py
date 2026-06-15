"""Severity colors for log and status output."""

from __future__ import annotations

SEVERITY_STYLES = {
    "ERROR": "bold red",
    "WARNING": "yellow",
    "INFO": "cyan",
    "DEBUG": "dim",
}

SEVERITY_ANSI = {
    "ERROR": "1;31",
    "WARNING": "1;33",
    "INFO": "1;36",
    "DEBUG": "2",
}


def style_for_line(line: str) -> str:
    """Rich style name for a log line, or empty string."""
    upper = line.upper()
    for keyword, style in SEVERITY_STYLES.items():
        if keyword in upper:
            return style
    return ""


def ansi_for_line(line: str) -> str:
    """ANSI color code for a log line, or empty string."""
    upper = line.upper()
    for keyword, code in SEVERITY_ANSI.items():
        if keyword in upper:
            return code
    return ""


def colorize_line(line: str, *, enabled: bool = True) -> str:
    if not enabled:
        return line
    code = ansi_for_line(line)
    if not code:
        return line
    return f"\033[{code}m{line}\033[0m"
