"""Startup banner for the ServerKit REPL."""

from __future__ import annotations

import importlib.util
import os
import platform
import sys

from serverkit import __version__

_INNER_WIDTH = 27
_INDENT = "  "
_TITLE = "S E R V E R K I T"

_RESET = "\033[0m"
_LOGO_COLOR = "1;36"
_LABEL_COLOR = "1;32"
_VALUE_COLOR = "37"


def _build_logo() -> tuple[str, ...]:
    pad_left = (_INNER_WIDTH - len(_TITLE)) // 2
    pad_right = _INNER_WIDTH - len(_TITLE) - pad_left
    title_inner = f"{' ' * pad_left}{_TITLE}{' ' * pad_right}"
    empty_inner = " " * _INNER_WIDTH
    bar = _INDENT + "▄" * (_INNER_WIDTH + 2)
    bottom = _INDENT + "▀" * (_INNER_WIDTH + 2)
    return (
        bar,
        f"{_INDENT}█{empty_inner}█",
        f"{_INDENT}█{title_inner}█",
        f"{_INDENT}█{empty_inner}█",
        bottom,
    )


_LOGO = _build_logo()


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _paint(code: str, text: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}{_RESET}"


def _label(text: str, *, enabled: bool) -> str:
    return _paint(_LABEL_COLOR, text, enabled=enabled)


def _value(text: str, *, enabled: bool) -> str:
    return _paint(_VALUE_COLOR, text, enabled=enabled)



def _info_line(label: str, value: str, *, enabled: bool) -> str:
    return f"{_INDENT}{_label(label, enabled=enabled)}: {_value(value, enabled=enabled)}"


def _installed_extras() -> str:
    extras: list[str] = []
    for label, module in (
        ("rich", "rich"),
        ("docker", "docker"),
        ("ssh", "paramiko"),
        ("ai", "requests"),
    ):
        if importlib.util.find_spec(module) is not None:
            extras.append(label)
    return ", ".join(extras) if extras else "base"


def _hint_line(*, enabled: bool) -> str:
    help_word = _label('"help"', enabled=enabled)
    exit_word = _label('"exit"', enabled=enabled)
    prefix = _value("Type ", enabled=enabled)
    mid = _value(" for commands · ", enabled=enabled)
    suffix = _value(" to quit", enabled=enabled)
    return f"{_INDENT}{prefix}{help_word}{mid}{exit_word}{suffix}"


def build_banner_lines(*, color: bool | None = None) -> list[str]:
    """Return banner lines for the REPL startup screen."""
    enabled = _color_enabled() if color is None else color
    logo = [_paint(_LOGO_COLOR, line, enabled=enabled) for line in _LOGO]
    info = [
        "",
        _info_line("Version", __version__, enabled=enabled),
        _info_line("Python", platform.python_version(), enabled=enabled),
        _info_line("Modules", _installed_extras(), enabled=enabled),
        "",
        _hint_line(enabled=enabled),
    ]
    return logo + info


def print_banner(*, color: bool | None = None) -> None:
    """Print the startup banner."""
    enabled = _color_enabled() if color is None else color
    for line in build_banner_lines(color=enabled):
        print(line)
    print()
