"""Startup banner for the ServerKit REPL."""

from __future__ import annotations

import importlib.util
import platform
import random
import sys
import time

from serverkit import __version__
from serverkit.shell.style import (
    INDENT as _INDENT,
    LOGO_PALETTE as _LOGO_PALETTE,
    RESET as _RESET,
    ShellStyle,
    color_enabled as _color_enabled,
    paint as _paint,
    pick_accent_color as _pick_accent_color,
)

_INNER_WIDTH = 27
_TITLE = "S E R V E R K I T"
_SCRAMBLE_CHARS = "▓░█▄▀■□▪▫@#$%&*?0123456789"
_BOOT_STEPS = (
    "booting serverkit shell",
    "scanning optional modules",
    "linking repl interface",
)

_SWEEP_DELAY = 0.008
_SLAM_DELAY = 0.003
_DECODE_TICKS = 4
_STATIC_FILL_TICKS = 7
_FLICKER_TICKS = 3
_PULSE_CYCLES = 5
_PULSE_DELAY = 0.035
_INFO_CHAR_DELAY = 0.008
_PROGRESS_WIDTH = 18


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
_TITLE_LINE = _LOGO[2]


def _accent(text: str, *, accent: str, enabled: bool) -> str:
    return _paint(accent, text, enabled=enabled)


def _value(text: str, *, enabled: bool) -> str:
    return _paint("37", text, enabled=enabled)


def _dim(text: str, *, enabled: bool) -> str:
    return _paint("2", text, enabled=enabled)


def _info_line(label: str, value: str, *, accent: str, enabled: bool) -> str:
    return (
        f"{_INDENT}{_accent(label, accent=accent, enabled=enabled)}: "
        f"{_value(value, enabled=enabled)}"
    )


def _installed_extras() -> list[str]:
    extras: list[str] = []
    for label, module in (
        ("rich", "rich"),
        ("docker", "docker"),
        ("ssh", "paramiko"),
        ("ai", "requests"),
    ):
        if importlib.util.find_spec(module) is not None:
            extras.append(label)
    return extras


def _installed_extras_text() -> str:
    extras = _installed_extras()
    return ", ".join(extras) if extras else "base"


def _hint_line(*, accent: str, enabled: bool) -> str:
    help_word = _accent('"help"', accent=accent, enabled=enabled)
    menu_word = _accent('"menu"', accent=accent, enabled=enabled)
    exit_word = _accent('"exit"', accent=accent, enabled=enabled)
    prefix = _value("Type ", enabled=enabled)
    mid = _value(" for commands, ", enabled=enabled)
    menu_mid = _value(" for guided mode · ", enabled=enabled)
    suffix = _value(" to quit", enabled=enabled)
    return f"{_INDENT}{prefix}{help_word}{mid}{menu_word}{menu_mid}{exit_word}{suffix}"


def build_banner_lines(
    *,
    color: bool | None = None,
    accent_color: str | None = None,
) -> list[str]:
    """Return banner lines for the REPL startup screen."""
    enabled = _color_enabled() if color is None else color
    accent = accent_color or (_pick_accent_color() if enabled else "1;36")
    logo = [_accent(line, accent=accent, enabled=enabled) for line in _LOGO]
    info = [
        "",
        _info_line("Version", __version__, accent=accent, enabled=enabled),
        _info_line("Python", platform.python_version(), accent=accent, enabled=enabled),
        _info_line("Modules", _installed_extras_text(), accent=accent, enabled=enabled),
        "",
        _hint_line(accent=accent, enabled=enabled),
    ]
    return logo + info


def _hide_cursor() -> None:
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def _show_cursor() -> None:
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def _write_line(text: str) -> None:
    sys.stdout.write(f"\r\033[2K{text}{_RESET}\n")
    sys.stdout.flush()


def _rewrite_current(text: str) -> None:
    sys.stdout.write(f"\r\033[2K{text}{_RESET}")
    sys.stdout.flush()


def _typewrite(text: str, *, paint, delay: float) -> None:
    for char in text:
        sys.stdout.write(paint(char))
        sys.stdout.flush()
        time.sleep(delay)


def _boot_tag(state: str, *, accent: str) -> str:
    return _paint(accent, f"[{state}]", enabled=True)


def _animate_boot_prelude(*, accent: str) -> None:
    spinner = ("..", "//", "~~", "..")
    for step_index, message in enumerate(_BOOT_STEPS):
        is_last = step_index == len(_BOOT_STEPS) - 1
        cycles = 1 if is_last else 3
        for tick in range(cycles):
            state = " ok " if is_last else f" {spinner[tick % len(spinner)]} "
            line = f"{_INDENT}{_boot_tag(state, accent=accent)} {_dim(message, enabled=True)}"
            _rewrite_current(line)
            time.sleep(0.045)
        _write_line(f"{_INDENT}{_boot_tag(' ok ', accent=accent)} {_value(message, enabled=True)}")
        time.sleep(0.02)


def _animate_progress_bar(label: str, *, accent: str, clear_on_complete: bool = False) -> None:
    prefix = f"{_INDENT}{_dim(label, enabled=True)} "
    for filled in range(_PROGRESS_WIDTH + 1):
        bar_filled = "█" * filled
        bar_empty = "░" * (_PROGRESS_WIDTH - filled)
        bar = _accent(f"[{bar_filled}{bar_empty}]", accent=accent, enabled=True)
        _rewrite_current(f"{prefix}{bar}")
        time.sleep(0.008)
    if clear_on_complete:
        sys.stdout.write("\r\033[2K")
        sys.stdout.flush()
    else:
        _write_line(f"{prefix}{_accent('[██████████████████]', accent=accent, enabled=True)}")


def _sweep_line(plain: str, *, accent: str, delay: float = _SWEEP_DELAY) -> None:
    built = ""
    for index, char in enumerate(plain):
        color = _LOGO_PALETTE[index % len(_LOGO_PALETTE)]
        built += _paint(color, char, enabled=True)
        _rewrite_current(built)
        time.sleep(delay)
    _write_line(_paint(accent, plain, enabled=True))


def _static_fill_line(plain: str, *, accent: str) -> None:
    frame_end = plain.index("█") + 1
    inner_end = plain.rindex("█")
    frame = plain[:frame_end]
    back = plain[inner_end:]
    width = inner_end - frame_end

    for tick in range(_STATIC_FILL_TICKS, 0, -1):
        density = tick / _STATIC_FILL_TICKS
        inner = "".join(
            random.choice(_SCRAMBLE_CHARS) if random.random() < density else " "
            for _ in range(width)
        )
        color = _LOGO_PALETTE[(_STATIC_FILL_TICKS - tick) % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, f"{frame}{inner}{back}", enabled=True))
        time.sleep(0.014)

    for tick in range(_FLICKER_TICKS):
        noisy = "".join(
            char if char in " █" or random.random() > 0.5 else random.choice(_SCRAMBLE_CHARS)
            for char in plain
        )
        color = _LOGO_PALETTE[tick % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, noisy, enabled=True))
        time.sleep(0.016)
    _write_line(_paint(accent, plain, enabled=True))


def _render_decode_frame(
    frame: str,
    target: list[str],
    resolved: list[str],
    *,
    scramble_from: int,
    accent: str,
    back: str,
) -> str:
    view: list[str] = []
    for index, char in enumerate(target):
        if char == " ":
            view.append(" ")
        elif index < scramble_from:
            view.append(resolved[index])
        else:
            view.append(random.choice(_SCRAMBLE_CHARS))
    inner = "".join(view)
    parts: list[str] = []
    line = f"{frame}{inner}{back}"
    lock_boundary = len(frame) + scramble_from
    for index, char in enumerate(line):
        if char == " ":
            parts.append(char)
            continue
        color = accent if index < lock_boundary else random.choice(_LOGO_PALETTE)
        parts.append(_paint(color, char, enabled=True))
    return "".join(parts)


def _decode_title_line(plain: str, *, accent: str) -> None:
    frame_end = plain.index("█") + 1
    inner_end = plain.rindex("█")
    frame = plain[:frame_end]
    target = list(plain[frame_end:inner_end])
    back = plain[inner_end:]
    resolved = list(target)

    for index, final_char in enumerate(target):
        if final_char == " ":
            continue
        for _ in range(_DECODE_TICKS):
            rendered = _render_decode_frame(
                frame,
                target,
                resolved,
                scramble_from=index,
                accent=accent,
                back=back,
            )
            _rewrite_current(rendered)
            time.sleep(0.01)
        resolved[index] = final_char

    for tick in range(4):
        color = _LOGO_PALETTE[(tick + 3) % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, plain, enabled=True))
        time.sleep(0.022)
    _write_line(_paint(accent, plain, enabled=True))


def _pulse_logo(plain_lines: tuple[str, ...], *, accent: str) -> None:
    line_count = len(plain_lines)
    for cycle in range(_PULSE_CYCLES):
        color = _LOGO_PALETTE[cycle % len(_LOGO_PALETTE)]
        sys.stdout.write(f"\033[{line_count}A")
        for line in plain_lines:
            sys.stdout.write(f"\r\033[2K{_paint(color, line, enabled=True)}{_RESET}\n")
        sys.stdout.flush()
        time.sleep(_PULSE_DELAY)

    sys.stdout.write(f"\033[{line_count}A")
    for line in plain_lines:
        sys.stdout.write(f"\r\033[2K{_paint(accent, line, enabled=True)}{_RESET}\n")
    sys.stdout.flush()


def _ready_ping(*, accent: str) -> None:
    message = f"{_INDENT}▸ shell online"
    for cycle in range(4):
        color = _LOGO_PALETTE[(cycle + 2) % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, message, enabled=True))
        time.sleep(0.04)
    _write_line(_paint(accent, message, enabled=True))


def _animate_logo(*, accent: str) -> None:
    _hide_cursor()
    try:
        _animate_progress_bar("loading", accent=accent, clear_on_complete=True)
        _sweep_line(_LOGO[0], accent=accent)
        _static_fill_line(_LOGO[1], accent=accent)
        _decode_title_line(_TITLE_LINE, accent=accent)
        _static_fill_line(_LOGO[3], accent=accent)
        _sweep_line(_LOGO[4], accent=accent, delay=_SLAM_DELAY)
        _pulse_logo(_LOGO, accent=accent)
        _ready_ping(accent=accent)
    finally:
        _show_cursor()


def _typewrite_value(value: str, *, enabled: bool) -> None:
    _typewrite(value, paint=lambda char: _value(char, enabled=enabled), delay=_INFO_CHAR_DELAY)


def _animate_module_badges(modules: list[str], *, accent: str, enabled: bool) -> None:
    if not modules:
        _typewrite_value("base", enabled=enabled)
        return

    for index, module in enumerate(modules):
        if index:
            sys.stdout.write(_value(" ", enabled=enabled))
        badge = f"[{module}]"
        color = _LOGO_PALETTE[index % len(_LOGO_PALETTE)]
        _typewrite(
            badge,
            paint=lambda char, color=color: _paint(color, char, enabled=enabled),
            delay=0.006,
        )
        sys.stdout.flush()
        time.sleep(0.012)


def _animate_info(*, accent: str, enabled: bool) -> None:
    print()

    entries = (
        ("Version", __version__, False),
        ("Python", platform.python_version(), False),
        ("Modules", _installed_extras(), True),
    )
    for label, value, is_modules in entries:
        tag = _boot_tag(" ok ", accent=accent)
        prefix = f"{_INDENT}{tag} {_accent(label, accent=accent, enabled=enabled)}: "
        sys.stdout.write(prefix)
        sys.stdout.flush()
        time.sleep(0.025)
        if is_modules and isinstance(value, list):
            _animate_module_badges(value, accent=accent, enabled=enabled)
        elif isinstance(value, str):
            _typewrite_value(value, enabled=enabled)
        sys.stdout.write("\n")
        sys.stdout.flush()
        time.sleep(0.02)

    print()
    hint = _hint_line(accent=accent, enabled=enabled)
    _typewrite(hint, paint=lambda char: char, delay=0.004)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _print_animated(*, accent: str, enabled: bool) -> None:
    _animate_logo(accent=accent)
    _animate_info(accent=accent, enabled=enabled)


def print_banner(
    *,
    color: bool | None = None,
    animate: bool | None = None,
    style: ShellStyle | None = None,
) -> None:
    """Print the startup banner."""
    if style is not None:
        enabled = style.enabled if color is None else color
        accent = style.accent_code
    else:
        enabled = _color_enabled() if color is None else color
        accent = _pick_accent_color() if enabled else "1;36"
    should_animate = animate if animate is not None else enabled

    if should_animate and enabled:
        _print_animated(accent=accent, enabled=enabled)
    else:
        for line in build_banner_lines(color=enabled, accent_color=accent):
            print(line)
    print()
