"""Severity colors for log and status output."""

SEVERITY_STYLES = {
    "ERROR": "bold red",
    "WARNING": "yellow",
    "INFO": "cyan",
    "DEBUG": "dim",
}


def style_for_line(line: str) -> str:
    upper = line.upper()
    for keyword, style in SEVERITY_STYLES.items():
        if keyword in upper:
            return style
    return ""
