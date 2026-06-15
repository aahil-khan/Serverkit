"""Shared terminal styling for the ServerKit REPL."""

from __future__ import annotations

import importlib.util
import os
import random
import sys
from typing import TYPE_CHECKING

from serverkit.output.theme import colorize_line

if TYPE_CHECKING:
    from serverkit.shell.state import ReplState

INDENT = "  "
RESET = "\033[0m"
VALUE_COLOR = "37"
DIM_COLOR = "2"
ERROR_COLOR = "1;31"
WARN_COLOR = "1;33"
OK_COLOR = "1;32"

LOGO_PALETTE = (
    "1;31",
    "1;32",
    "1;33",
    "1;34",
    "1;35",
    "1;36",
    "91",
    "92",
    "93",
    "94",
    "95",
    "96",
)

THEME_ACCENTS: dict[str, str | None] = {
    "default": None,
    "cyan": "1;36",
    "green": "1;32",
    "magenta": "1;35",
    "yellow": "1;33",
    "blue": "1;34",
    "red": "1;31",
}

RICH_BORDER: dict[str, str] = {
    "1;36": "cyan",
    "1;32": "green",
    "1;35": "magenta",
    "1;33": "yellow",
    "1;34": "blue",
    "1;31": "red",
}

_active_style: ShellStyle | None = None


def installed_modules_label() -> str:
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


def load_ui_flags() -> dict[str, bool]:
    from serverkit.config import Config

    cfg = Config.load()
    return {
        "animate_banner": bool(cfg.get("output", "animate_banner", default=True)),
        "skip_animation_on_key": bool(
            cfg.get("output", "skip_animation_on_key", default=True)
        ),
        "syntax_highlight": bool(cfg.get("output", "syntax_highlight", default=True)),
        "mascot": bool(cfg.get("output", "mascot", default=True)),
        "mascot_animate": bool(cfg.get("output", "mascot_animate", default=True)),
    }


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def resolve_accent(*, config_accent: str | None = None, config_theme: str | None = None) -> str:
    if config_accent and config_accent in LOGO_PALETTE:
        return config_accent
    if config_theme:
        mapped = THEME_ACCENTS.get(config_theme.lower())
        if mapped:
            return mapped
    return random.choice(LOGO_PALETTE)


def paint(code: str, text: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}{RESET}"


def set_active_style(style: ShellStyle | None) -> None:
    global _active_style
    _active_style = style


def get_active_style() -> ShellStyle:
    if _active_style is not None:
        return _active_style
    return ShellStyle(enabled=False)


class ShellStyle:
    """Session-scoped colors and formatted output helpers."""

    def __init__(
        self,
        *,
        accent: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.enabled = color_enabled() if enabled is None else enabled
        if accent is not None:
            self.accent_code = accent
        elif self.enabled:
            from serverkit.config import Config

            cfg = Config.load()
            self.accent_code = resolve_accent(
                config_accent=cfg.get("output", "accent"),
                config_theme=cfg.get("output", "theme"),
            )
        else:
            self.accent_code = "1;36"
        self.ui = load_ui_flags()

    def paint(self, code: str, text: str) -> str:
        return paint(code, text, enabled=self.enabled)

    def accent(self, text: str) -> str:
        return paint(self.accent_code, text, enabled=self.enabled)

    def value(self, text: str) -> str:
        return paint(VALUE_COLOR, text, enabled=self.enabled)

    def dim(self, text: str) -> str:
        return paint(DIM_COLOR, text, enabled=self.enabled)

    def error(self, text: str) -> str:
        return paint(ERROR_COLOR, text, enabled=self.enabled)

    def success(self, text: str) -> str:
        return paint(OK_COLOR, text, enabled=self.enabled)

    def tag(self, state: str, message: str = "") -> str:
        label = f"[ {state.strip()} ]"
        styled = self.accent(label) if state.strip() == "ok" else self.error(label)
        if not message:
            return styled
        return f"{styled} {self.value(message)}"

    def target_label(self, state: ReplState) -> str:
        if state.remote is None:
            return "local"
        host = getattr(state.remote, "host", "remote")
        return f"remote: {host}"

    def prompt_text(self, state: ReplState) -> str:
        target = self.target_label(state)
        if self.enabled:
            return f"{self.dim(target)} {self.accent('▸')} {self.accent('> ')}"
        return f"{target} > "

    def builder_header(self, name: str) -> None:
        if not self.enabled:
            print(f"\nWorkflow builder: {name}")
            print("Enter steps (see help). Type save when done, cancel to abort.")
            return
        box_w = 54
        inner_w = box_w - 4
        title_label = "workflow builder "
        top_inner = f"╭─ {title_label}"
        print(
            f"\n{INDENT}{self.accent(top_inner + '─' * (box_w - len(top_inner) - 1) + '╮')}"
        )
        building_text = f"Building: {name}"
        if len(building_text) > inner_w:
            building_text = building_text[: inner_w - 1] + "…"
        print(
            f"{INDENT}│ {self.value(building_text)}{RESET}"
            f"{' ' * max(0, inner_w - len(building_text))} │"
        )
        print(f"{INDENT}{self.accent('╰' + '─' * (box_w - 2) + '╯')}")
        print(f"{INDENT}{self.dim('Enter steps · save to finish · cancel to abort')}")

    def builder_examples(self) -> None:
        examples = (
            "processes | memory_above 500 | sort_by_memory | summarize",
            "logs /var/log/syslog | errors | tail 20 | summarize",
            "export /tmp/report.txt",
        )
        for line in examples:
            print(f"{INDENT}{self.dim('·')} {self.value(line)}")

    def builder_prompt(self) -> str:
        if self.enabled:
            return f"{INDENT}{self.accent('step> ')}"
        return "step> "

    def builder_step_ok(self, step: str) -> None:
        print(f"{INDENT}{self.tag('ok', f'added {step}')}")

    def skip_hint(self) -> str:
        if not self.enabled:
            return ""
        return f"{INDENT}{self.dim('(type any key to skip animation)')}\n"

    def echo_command(self, command: str) -> None:
        line = f"{INDENT}{self.accent('▸ ')}{self.value(command)}"
        print(f"\n{line}\n")

    def format_error(self, message: str) -> str:
        if not self.enabled:
            return message if message.startswith("Error:") else f"Error: {message}"
        lines = message.splitlines()
        head = f"{INDENT}{self.tag('err', lines[0])}"
        if len(lines) == 1:
            return head
        tail = "\n".join(f"{INDENT}{self.dim(line)}" for line in lines[1:])
        return f"{head}\n{tail}"

    _ERROR_PREFIXES = (
        "Unknown command:",
        "Usage:",
        "Malformed ",
        "Could not parse",
        "Cannot chain",
        "error_rate:",
        "Empty step",
        "Step failed:",
        "Cancelled",
        "Not connected",
        "Connection failed:",
        "Error:",
    )

    def _already_styled(self, text: str) -> bool:
        return "[ ok ]" in text or "[ err ]" in text

    def _looks_like_error(self, text: str) -> bool:
        lines = text.splitlines()
        if not lines:
            return False
        first = lines[0].strip()
        if any(first.startswith(prefix) for prefix in self._ERROR_PREFIXES):
            return True
        if len(lines) <= 3:
            lower = text.lower()
            if any(
                marker in lower
                for marker in (
                    "not found",
                    "no workflow named",
                    "install with: pip install",
                )
            ):
                return True
        return False

    def format_shell_output(self, text: str) -> str:
        """Apply error tags or log colorization to parser/REPL text output."""
        if not text or not self.enabled:
            return text
        if self._already_styled(text):
            return text
        if self._looks_like_error(text):
            return self.format_error(text)
        return self.colorize_output(text)

    def format_success(self, message: str) -> str:
        if not self.enabled:
            return message
        return f"{INDENT}{self.tag('ok', message)}"

    def farewell(self) -> None:
        if not self.enabled:
            print(f"{INDENT}Goodbye.")
            return
        print(f"\n{INDENT}{self.tag('ok', 'shell offline')}\n")

    def help_header(self) -> str:
        box_w = 54
        inner_w = box_w - 4
        if not self.enabled:
            return f"{INDENT}-- ServerKit help --\n"
        title_label = "help "
        top_inner = f"╭─ {title_label}"
        top = (
            f"{INDENT}{self.accent(top_inner + '─' * (box_w - len(top_inner) - 1) + '╮')}"
        )
        title_text = "ServerKit shell — command reference"
        title_line = (
            f"{INDENT}│ {self.value(title_text)}{RESET}"
            f"{' ' * max(0, inner_w - len(title_text))} │"
        )
        bottom = f"{INDENT}{self.accent('╰' + '─' * (box_w - 2) + '╯')}"
        return f"{top}\n{title_line}\n{bottom}\n"

    def colorize_output(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        return "\n".join(colorize_line(line, enabled=True) for line in text.splitlines())

    def rich_border(self) -> str:
        return RICH_BORDER.get(self.accent_code, "cyan")

    def workflow_running(self, index: int, total: int, name: str) -> str:
        return f"{INDENT}{self.accent(f'[{index}/{total}]')} {self.dim('[ .. ]')} {self.value(name)}"

    def workflow_done(self, index: int, total: int, name: str) -> str:
        return f"{INDENT}{self.accent(f'[{index}/{total}]')} {self.tag('ok', name)}"

    def workflow_skip(self, index: int, total: int, name: str) -> str:
        return f"{INDENT}{self.dim(f'[{index}/{total}]')} {self.dim('[skip]')} {self.dim(name)}"

    def workflow_dry_run(self, detail: str) -> str:
        return f"{INDENT}  {self.dim('[dry-run]')} {self.dim(detail)}"


def pick_accent_color() -> str:
    return resolve_accent()
