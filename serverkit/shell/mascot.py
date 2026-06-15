"""Purely cosmetic REPL mascot — a cat that reacts to your commands."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serverkit.shell.style import ShellStyle

_INDENT = "  "

# Three-line ASCII cat poses (width ~7).
_IDLE = (" /\\_/\\ ", "( o.o )", " > ^ < ")
_HAPPY = (" /\\_/\\ ", "( ^.^ )", " > ω < ")
_STARTLED = (" /\\_/\\ ", "( O.O )", " >x<  ")
_SLEEPY = (" /\\_/\\ ", "( -.- )", " u   u ")
_WALK_A = (" /\\_/\\ ", "( o.o )", " /   \\ ")
_WALK_B = (" /\\_/\\ ", "( o.o )", " \\   / ")
_POKE = (" /\\_/\\ ", "( >.< )", " d   b ")
_CURIOUS = (" /\\_/\\ ", "( o.O )", " ?   ? ")

_OK_QUIPS = (
    "purr~",
    "mrow!",
    "*tail swish*",
    "approved by cat",
    "nice typing",
    "* kneads keyboard *",
)
_ERR_QUIPS = (
    "mrow?!",
    "* startled jump *",
    "that wasn't in the manual",
    "ask again, human",
    "* knocked cup off desk *",
    "hiss?",
)
_TOPIC_QUIPS: dict[str, tuple[str, ...]] = {
    "memory": ("RAM is warm", "good nap spot", "memory = soft pillow"),
    "process": ("so many mice to chase", "PID parade", "busy little processes"),
    "log": ("reading the scroll", "found a hair in the log", "* squints at lines *"),
    "connect": ("remote cat mode", "SSH = Secret Scratching Hideout", "packing tiny suitcase"),
    "disk": ("disk = round thing to sit on", "spinny plate detected"),
    "docker": ("box! I fits", "container = perfect box", "* sits in container *"),
    "workflow": ("herding steps", "orchestrated nap schedule"),
    "ask": ("consulting the oracle", "AI = Automatic Intuition?", "whiskers tingling"),
    "help": ("I know nothing (officially)", "read the scrolls, human"),
    "menu": ("guided treat menu", "pick a fish"),
    "port": ("knocking on ports", "who goes there?"),
    "service": ("systemd snooze button", "restart = wake-up call"),
    "clear": ("fresh litter box", "screen = clean sunbeam"),
    "clr": ("fresh litter box", "screen = clean sunbeam"),
}


def _topic_quip(command: str) -> str | None:
    lower = command.lower()
    for key, quips in _TOPIC_QUIPS.items():
        if key in lower:
            return random.choice(quips)
    return None


def _pick_pose(
    command: str,
    outcome: str,
    *,
    animate: bool,
) -> tuple[str, str, str]:
    lower = command.lower()
    if outcome == "err":
        return _STARTLED
    if lower in ("exit", "quit"):
        return _SLEEPY
    if lower in ("help", "menu"):
        return _CURIOUS
    if "ask" in lower:
        return _POKE
    if outcome == "ok" and random.random() < 0.35:
        return _HAPPY
    if animate:
        return random.choice((_WALK_A, _WALK_B))
    return _IDLE


def _pick_quip(command: str, outcome: str) -> str:
    topic = _topic_quip(command)
    if topic:
        return topic
    pool = _ERR_QUIPS if outcome == "err" else _OK_QUIPS
    return random.choice(pool)


def _render(pose: tuple[str, str, str], offset: int, quip: str, *, style: ShellStyle | None) -> str:
    lines = [f"{_INDENT}{' ' * offset}{row.rstrip()}" for row in pose]
    quip_line = f"{_INDENT}{' ' * offset}{quip}"
    if style is not None and style.enabled:
        lines = [style.accent(line) for line in lines]
        quip_line = style.dim(quip_line)
    return "\n".join(lines + [quip_line])


class ShellMascot:
    """A small cat that reacts once after each REPL command."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        style: ShellStyle | None = None,
        animate: bool = True,
    ) -> None:
        self._style = style
        self._enabled = enabled and self._tty_ok()
        self._animate = animate

    @staticmethod
    def _tty_ok() -> bool:
        import sys

        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    @classmethod
    def from_style(cls, style: ShellStyle) -> ShellMascot:
        return cls(
            enabled=bool(style.ui.get("mascot", False)),
            style=style,
            animate=bool(style.ui.get("mascot_animate", True)),
        )

    @property
    def active(self) -> bool:
        return self._enabled

    def react(self, command: str, *, outcome: str = "ok") -> None:
        """Show one cat pose and quip after a REPL command."""
        if not self._enabled or not command.strip():
            return
        stripped = command.strip()
        if stripped.lower() in ("clear", "clr"):
            return
        quip = _pick_quip(stripped, outcome)
        pose = _pick_pose(stripped, outcome, animate=self._animate)
        offset = min(max(len(stripped), 4), 52)
        print(_render(pose, offset, quip, style=self._style))
        print()
