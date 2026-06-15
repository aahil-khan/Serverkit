"""Startup banner for the ServerKit REPL."""

from __future__ import annotations

import platform
import random
import sys

from serverkit import __version__
from serverkit.shell.banner_skip import SkipWatcher, interruptible_sleep
from serverkit.shell.style import (
    INDENT as _INDENT,
    LOGO_PALETTE as _LOGO_PALETTE,
    RESET as _RESET,
    ShellStyle,
    color_enabled as _color_enabled,
    installed_modules_label,
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
    text = installed_modules_label()
    return text.split(", ") if text != "base" else []


def _installed_extras_text() -> str:
    return installed_modules_label()


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


def _typewrite(text: str, *, paint, delay: float, skip: SkipWatcher | None = None) -> bool:
    for char in text:
        if skip and skip.skipped:
            return True
        sys.stdout.write(paint(char))
        sys.stdout.flush()
        if interruptible_sleep(delay, skip):
            return True
    return False


def _boot_tag(state: str, *, accent: str) -> str:
    return _paint(accent, f"[{state}]", enabled=True)


def _animate_boot_prelude(*, accent: str, skip: SkipWatcher | None = None) -> bool:
    spinner = ("..", "//", "~~", "..")
    for step_index, message in enumerate(_BOOT_STEPS):
        if skip and skip.skipped:
            return True
        is_last = step_index == len(_BOOT_STEPS) - 1
        cycles = 1 if is_last else 3
        for tick in range(cycles):
            if skip and skip.skipped:
                return True
            state = " ok " if is_last else f" {spinner[tick % len(spinner)]} "
            line = f"{_INDENT}{_boot_tag(state, accent=accent)} {_dim(message, enabled=True)}"
            _rewrite_current(line)
            if interruptible_sleep(0.045, skip):
                return True
        _write_line(f"{_INDENT}{_boot_tag(' ok ', accent=accent)} {_value(message, enabled=True)}")
        if interruptible_sleep(0.02, skip):
            return True
    return False


def _animate_progress_bar(
    label: str,
    *,
    accent: str,
    clear_on_complete: bool = False,
    skip: SkipWatcher | None = None,
) -> bool:
    prefix = f"{_INDENT}{_dim(label, enabled=True)} "
    for filled in range(_PROGRESS_WIDTH + 1):
        if skip and skip.skipped:
            return True
        bar_filled = "█" * filled
        bar_empty = "░" * (_PROGRESS_WIDTH - filled)
        bar = _accent(f"[{bar_filled}{bar_empty}]", accent=accent, enabled=True)
        _rewrite_current(f"{prefix}{bar}")
        if interruptible_sleep(0.008, skip):
            return True
    if clear_on_complete:
        sys.stdout.write("\r\033[2K")
        sys.stdout.flush()
    else:
        _write_line(f"{prefix}{_accent('[██████████████████]', accent=accent, enabled=True)}")
    return False


def _sweep_line(
    plain: str,
    *,
    accent: str,
    delay: float = _SWEEP_DELAY,
    skip: SkipWatcher | None = None,
) -> bool:
    built = ""
    for index, char in enumerate(plain):
        if skip and skip.skipped:
            return True
        color = _LOGO_PALETTE[index % len(_LOGO_PALETTE)]
        built += _paint(color, char, enabled=True)
        _rewrite_current(built)
        if interruptible_sleep(delay, skip):
            return True
    _write_line(_paint(accent, plain, enabled=True))
    return False


def _static_fill_line(plain: str, *, accent: str, skip: SkipWatcher | None = None) -> bool:
    frame_end = plain.index("█") + 1
    inner_end = plain.rindex("█")
    frame = plain[:frame_end]
    back = plain[inner_end:]
    width = inner_end - frame_end

    for tick in range(_STATIC_FILL_TICKS, 0, -1):
        if skip and skip.skipped:
            return True
        density = tick / _STATIC_FILL_TICKS
        inner = "".join(
            random.choice(_SCRAMBLE_CHARS) if random.random() < density else " "
            for _ in range(width)
        )
        color = _LOGO_PALETTE[(_STATIC_FILL_TICKS - tick) % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, f"{frame}{inner}{back}", enabled=True))
        if interruptible_sleep(0.014, skip):
            return True

    for tick in range(_FLICKER_TICKS):
        if skip and skip.skipped:
            return True
        noisy = "".join(
            char if char in " █" or random.random() > 0.5 else random.choice(_SCRAMBLE_CHARS)
            for char in plain
        )
        color = _LOGO_PALETTE[tick % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, noisy, enabled=True))
        if interruptible_sleep(0.016, skip):
            return True
    _write_line(_paint(accent, plain, enabled=True))
    return False


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


def _decode_title_line(plain: str, *, accent: str, skip: SkipWatcher | None = None) -> bool:
    frame_end = plain.index("█") + 1
    inner_end = plain.rindex("█")
    frame = plain[:frame_end]
    target = list(plain[frame_end:inner_end])
    back = plain[inner_end:]
    resolved = list(target)

    for index, final_char in enumerate(target):
        if skip and skip.skipped:
            return True
        if final_char == " ":
            continue
        for _ in range(_DECODE_TICKS):
            if skip and skip.skipped:
                return True
            rendered = _render_decode_frame(
                frame,
                target,
                resolved,
                scramble_from=index,
                accent=accent,
                back=back,
            )
            _rewrite_current(rendered)
            if interruptible_sleep(0.01, skip):
                return True
        resolved[index] = final_char

    for tick in range(4):
        if skip and skip.skipped:
            return True
        color = _LOGO_PALETTE[(tick + 3) % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, plain, enabled=True))
        if interruptible_sleep(0.022, skip):
            return True
    _write_line(_paint(accent, plain, enabled=True))
    return False


def _pulse_logo(
    plain_lines: tuple[str, ...],
    *,
    accent: str,
    skip: SkipWatcher | None = None,
) -> bool:
    line_count = len(plain_lines)
    for cycle in range(_PULSE_CYCLES):
        if skip and skip.skipped:
            return True
        color = _LOGO_PALETTE[cycle % len(_LOGO_PALETTE)]
        sys.stdout.write(f"\033[{line_count}A")
        for line in plain_lines:
            sys.stdout.write(f"\r\033[2K{_paint(color, line, enabled=True)}{_RESET}\n")
        sys.stdout.flush()
        if interruptible_sleep(_PULSE_DELAY, skip):
            return True

    sys.stdout.write(f"\033[{line_count}A")
    for line in plain_lines:
        sys.stdout.write(f"\r\033[2K{_paint(accent, line, enabled=True)}{_RESET}\n")
    sys.stdout.flush()
    return False


def _ready_ping(*, accent: str, skip: SkipWatcher | None = None) -> bool:
    message = f"{_INDENT}▸ shell online"
    for cycle in range(4):
        if skip and skip.skipped:
            return True
        color = _LOGO_PALETTE[(cycle + 2) % len(_LOGO_PALETTE)]
        _rewrite_current(_paint(color, message, enabled=True))
        if interruptible_sleep(0.04, skip):
            return True
    _write_line(_paint(accent, message, enabled=True))
    return False


def _finish_on_skip(*, accent: str, enabled: bool) -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    for line in build_banner_lines(color=enabled, accent_color=accent):
        print(line)
    if enabled:
        print(_paint(accent, f"{_INDENT}▸ shell online", enabled=True))
    else:
        print(f"{_INDENT}▸ shell online")


def _animate_logo(*, accent: str, skip: SkipWatcher | None = None) -> bool:
    _hide_cursor()
    try:
        steps = (
            lambda: _animate_progress_bar("loading", accent=accent, clear_on_complete=True, skip=skip),
            lambda: _sweep_line(_LOGO[0], accent=accent, skip=skip),
            lambda: _static_fill_line(_LOGO[1], accent=accent, skip=skip),
            lambda: _decode_title_line(_TITLE_LINE, accent=accent, skip=skip),
            lambda: _static_fill_line(_LOGO[3], accent=accent, skip=skip),
            lambda: _sweep_line(_LOGO[4], accent=accent, delay=_SLAM_DELAY, skip=skip),
            lambda: _pulse_logo(_LOGO, accent=accent, skip=skip),
            lambda: _ready_ping(accent=accent, skip=skip),
        )
        for step in steps:
            if step():
                return True
        return False
    finally:
        _show_cursor()


def _typewrite_value(value: str, *, enabled: bool, skip: SkipWatcher | None = None) -> bool:
    return _typewrite(
        value,
        paint=lambda char: _value(char, enabled=enabled),
        delay=_INFO_CHAR_DELAY,
        skip=skip,
    )


def _animate_module_badges(
    modules: list[str],
    *,
    accent: str,
    enabled: bool,
    skip: SkipWatcher | None = None,
) -> bool:
    if not modules:
        return _typewrite_value("base", enabled=enabled, skip=skip)

    for index, module in enumerate(modules):
        if skip and skip.skipped:
            return True
        if index:
            sys.stdout.write(_value(" ", enabled=enabled))
        badge = f"[{module}]"
        color = _LOGO_PALETTE[index % len(_LOGO_PALETTE)]
        if _typewrite(
            badge,
            paint=lambda char, color=color: _paint(color, char, enabled=enabled),
            delay=0.006,
            skip=skip,
        ):
            return True
        sys.stdout.flush()
        if interruptible_sleep(0.012, skip):
            return True
    return False


def _animate_info(*, accent: str, enabled: bool, skip: SkipWatcher | None = None) -> bool:
    print()

    entries = (
        ("Version", __version__, False),
        ("Python", platform.python_version(), False),
        ("Modules", _installed_extras(), True),
    )
    for label, value, is_modules in entries:
        if skip and skip.skipped:
            return True
        tag = _boot_tag(" ok ", accent=accent)
        prefix = f"{_INDENT}{tag} {_accent(label, accent=accent, enabled=enabled)}: "
        sys.stdout.write(prefix)
        sys.stdout.flush()
        if interruptible_sleep(0.025, skip):
            return True
        if is_modules and isinstance(value, list):
            if _animate_module_badges(value, accent=accent, enabled=enabled, skip=skip):
                return True
        elif isinstance(value, str):
            if _typewrite_value(value, enabled=enabled, skip=skip):
                return True
        sys.stdout.write("\n")
        sys.stdout.flush()
        if interruptible_sleep(0.02, skip):
            return True

    print()
    hint = _hint_line(accent=accent, enabled=enabled)
    if _typewrite(hint, paint=lambda char: char, delay=0.004, skip=skip):
        return True
    sys.stdout.write("\n")
    sys.stdout.flush()
    return False


def _print_animated(
    *,
    accent: str,
    enabled: bool,
    skip_on_key: bool = True,
) -> bool:
    skip = SkipWatcher() if skip_on_key else None
    if skip:
        skip.start()
        if enabled:
            sys.stdout.write(ShellStyle(accent=accent, enabled=True).skip_hint())
            sys.stdout.flush()
    try:
        if _animate_boot_prelude(accent=accent, skip=skip):
            _finish_on_skip(accent=accent, enabled=enabled)
            return True
        if _animate_logo(accent=accent, skip=skip):
            _finish_on_skip(accent=accent, enabled=enabled)
            return True
        if _animate_info(accent=accent, enabled=enabled, skip=skip):
            _finish_on_skip(accent=accent, enabled=enabled)
            return True
        return False
    finally:
        if skip:
            skip.stop()


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
    if style is not None:
        skip_on_key = style.ui.get("skip_animation_on_key", True)
        if animate is None:
            should_animate = style.ui.get("animate_banner", True) and enabled
    else:
        skip_on_key = True

    if should_animate and enabled:
        _print_animated(accent=accent, enabled=enabled, skip_on_key=skip_on_key)
    else:
        for line in build_banner_lines(color=enabled, accent_color=accent):
            print(line)
    print()
