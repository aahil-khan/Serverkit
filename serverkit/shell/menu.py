"""Interactive category menu for the ServerKit REPL."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from serverkit.shell import style as shell_style
from serverkit.shell.menu_tree import (
    AnyMenuNode,
    ChainStep,
    FixedCommand,
    MenuArg,
    MenuCategory,
    SetBase,
    TerminalAction,
    WizardCommand,
    filter_categories,
    filter_nodes,
)
from serverkit.shell.parser import parse_input

if TYPE_CHECKING:
    from prompt_toolkit import PromptSession

    from serverkit.shell.state import ReplState

try:
    from prompt_toolkit.formatted_text import ANSI
except ImportError:  # pragma: no cover
    ANSI = None  # type: ignore[misc, assignment]

_INDENT = shell_style.INDENT
_BOX_WIDTH = 54
_CMD_CHAR_DELAY = 0.007
_CMD_SWEEP_DELAY = 0.004

MenuAction = tuple[str, int | None]


@dataclass
class _NavFrame:
    title: str
    nodes: list[AnyMenuNode]
    command: str


def _target_label(state: ReplState) -> str:
    if state.remote is None:
        return "local"
    host = getattr(state.remote, "host", "remote")
    return f"remote: {host}"


def _quote_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _format_arg_value(arg: MenuArg, raw: str) -> str:
    text = raw.strip() if raw.strip() else arg.default
    if arg.kind == "number":
        return str(float(text) if "." in text else int(text))
    if arg.kind in ("text", "choice"):
        return text
    return _quote_string(text)


def build_suffix(step: ChainStep, values: dict[str, str]) -> str:
    formatted = {
        arg.name: _format_arg_value(arg, values.get(arg.name, arg.default))
        for arg in step.args
    }
    return step.suffix_template.format(**formatted)


def build_command(template: str, args: list[MenuArg], values: dict[str, str]) -> str:
    formatted = {
        arg.name: _format_arg_value(arg, values.get(arg.name, arg.default))
        for arg in args
    }
    return template.format(**formatted)


def _fit(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


def _pad_line(text: str, width: int) -> str:
    return text + " " * max(0, width - len(text))


def _read_nav_key() -> str | None:
    """Read a single navigation key in raw mode. Returns None if unavailable."""
    if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
        return None
    try:
        import termios
        import tty
    except ImportError:  # pragma: no cover — Windows
        return None

    fd = sys.stdin.fileno()
    try:
        old = termios.tcgetattr(fd)
    except termios.error:
        return None

    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                return "enter"
            if ch in ("b", "B"):
                return "back"
            if ch in ("q", "Q"):
                return "quit"
            if ch == "\x03":
                return "cancel"
            if ch in "123456789":
                return ch
            if ch in ("k", "K"):
                return "up"
            if ch in ("j", "J"):
                return "down"
            if ch != "\x1b":
                continue
            rest = sys.stdin.read(2)
            if rest == "[A":
                return "up"
            if rest == "[B":
                return "down"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


class _MenuUi:
    """Terminal styling aligned with the startup banner."""

    def __init__(self, style: shell_style.ShellStyle | None = None) -> None:
        self._style = style or shell_style.ShellStyle()
        self.enabled = self._style.enabled
        self.accent = self._style.accent_code
        self._last_command = ""
        self._alt_screen = False

    def enter(self) -> None:
        if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
            return
        sys.stdout.write("\033[?1049h")
        sys.stdout.flush()
        self._alt_screen = True

    def leave(self) -> None:
        if not self._alt_screen:
            return
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()
        self._alt_screen = False

    def _paint(self, code: str, text: str) -> str:
        return self._style.paint(code, text)

    def _accent(self, text: str) -> str:
        return self._style.accent(text)

    def _value(self, text: str) -> str:
        return self._style.value(text)

    def _dim(self, text: str) -> str:
        return self._style.dim(text)

    def _command_box_lines(self, command: str) -> list[str]:
        inner_w = _BOX_WIDTH - 4
        label = self._accent("▶ COMMAND")
        display = command if command else self._dim("(none)")
        display = _fit(display, inner_w)
        top = f"{_INDENT}╭{'─' * (_BOX_WIDTH - 2)}╮"
        label_line = f"{_INDENT}│ {label}{' ' * max(0, inner_w - len('▶ COMMAND'))} │"
        cmd_line = f"{_INDENT}│ {_pad_line(display, inner_w)} │"
        bottom = f"{_INDENT}╰{'─' * (_BOX_WIDTH - 2)}╯"
        if self.enabled:
            label_line = f"{_INDENT}│ {label}{shell_style.RESET}{' ' * max(0, inner_w - len('▶ COMMAND'))} │"
            if command:
                cmd_line = f"{_INDENT}│ {self._accent(display)}{' ' * max(0, inner_w - len(display))} │"
            else:
                cmd_line = f"{_INDENT}│ {display}{' ' * max(0, inner_w - len('(none)'))} │"
        return [top, label_line, cmd_line, bottom]

    def _render_command_box_animated(self, command: str) -> None:
        inner_w = _BOX_WIDTH - 4
        prev = self._last_command
        if command.startswith(prev) and prev:
            base = prev
            added = command[len(prev) :]
            delay = _CMD_CHAR_DELAY
        else:
            base = ""
            added = command
            delay = _CMD_SWEEP_DELAY

        top = f"{_INDENT}╭{'─' * (_BOX_WIDTH - 2)}╮"
        label = self._accent("▶ COMMAND")
        label_line = f"{_INDENT}│ {label}{shell_style.RESET}{' ' * max(0, inner_w - len('▶ COMMAND'))} │"
        bottom = f"{_INDENT}╰{'─' * (_BOX_WIDTH - 2)}╯"

        sys.stdout.write(f"{top}\n{label_line}\n")
        sys.stdout.flush()

        built = base
        for index, char in enumerate(added):
            built += char
            color = shell_style.LOGO_PALETTE[index % len(shell_style.LOGO_PALETTE)]
            shown = _fit(built, inner_w)
            line = f"{_INDENT}│ {self._paint(color, shown)}{' ' * max(0, inner_w - len(shown))} │"
            sys.stdout.write(f"\033[1A\r\033[2K{line}\n")
            sys.stdout.flush()
            time.sleep(delay)

        final = _fit(command, inner_w) if command else self._dim("(none)")
        if command:
            final_line = f"{_INDENT}│ {self._accent(final)}{' ' * max(0, inner_w - len(final))} │"
        else:
            final_line = f"{_INDENT}│ {final}{' ' * max(0, inner_w - len('(none)'))} │"
        sys.stdout.write(f"\033[1A\r\033[2K{final_line}\n{bottom}\n")
        sys.stdout.flush()
        self._last_command = command

    def _menu_body_lines(
        self,
        state: ReplState,
        nodes: list[AnyMenuNode],
        *,
        section: str,
        selected_index: int = 0,
    ) -> list[str]:
        lines: list[str] = [""]
        lines.append(
            f"{_INDENT}{self._dim('Target')}  {self._value(_target_label(state))}"
        )
        lines.append(
            f"{_INDENT}{self._dim('Section')}  {self._value(section)}"
        )
        lines.append("")
        lines.append(f"{_INDENT}{self._dim('── options ' + '─' * 38)}")
        lines.append("")

        for index, node in enumerate(nodes):
            number = index + 1
            is_selected = index == selected_index
            if is_selected:
                cursor = self._accent("▸ ")
                key = self._accent(f"[{number}]")
                label = self._accent(f" {node.label}")
            else:
                cursor = "  "
                key = self._dim(f"[{number}]")
                label = self._value(f" {node.label}")
            desc = f" {self._dim('— ' + node.description)}" if node.description else ""
            lines.append(f"{_INDENT}{cursor}{key}{label}{desc}")

        lines.append("")
        lines.append(
            f"{_INDENT}{self._dim('↑↓')} navigate"
            f"  {self._dim('Enter')} select"
            f"  {self._dim('1-9')} jump"
            f"  {self._dim('b')} back"
            f"  {self._dim('q')} quit"
        )
        lines.append("")
        return lines

    def _header_line(self) -> str:
        if self.enabled:
            tag = self._paint(self.accent, "[ ok ]")
            return f"{_INDENT}{tag}{self._value(' Guided menu')}"
        return f"{_INDENT}[ ok ] Guided menu"

    def draw(
        self,
        state: ReplState,
        command: str,
        nodes: list[AnyMenuNode],
        *,
        section: str,
        selected_index: int = 0,
        animate: bool = True,
    ) -> None:
        body = "\n".join(
            self._menu_body_lines(
                state,
                nodes,
                section=section,
                selected_index=selected_index,
            )
        )
        command_changed = command != self._last_command

        if self._alt_screen:
            sys.stdout.write("\033[H\033[2J")
            sys.stdout.write(self._header_line() + "\n\n")
        elif not self._alt_screen:
            box = "\n".join(self._command_box_lines(command))
            print(f"{self._header_line()}\n{box}\n{body}")
            self._last_command = command
            return

        if animate and command_changed and self.enabled:
            self._render_command_box_animated(command)
        else:
            sys.stdout.write("\n".join(self._command_box_lines(command)) + "\n")
            self._last_command = command

        sys.stdout.write(body + "\n")
        sys.stdout.flush()

    def _prompt_text(self, text: str) -> Any:
        if self.enabled and ANSI is not None:
            return ANSI(text)
        return text

    def _parse_typed_choice(self, choice: str | None, node_count: int) -> MenuAction:
        if choice is None or choice == "q":
            return ("quit", None)
        if choice == "b":
            return ("back", None)
        if not choice.isdigit():
            return ("invalid", None)
        index = int(choice)
        if index < 1 or index > node_count:
            return ("invalid", None)
        return ("select", index - 1)

    def read_selection(
        self,
        session: PromptSession,
        state: ReplState,
        command: str,
        nodes: list[AnyMenuNode],
        *,
        section: str,
        animate: bool,
    ) -> MenuAction:
        if not nodes:
            return ("quit", None)

        selected = 0
        self.draw(
            state,
            command,
            nodes,
            section=section,
            selected_index=selected,
            animate=animate,
        )

        while True:
            key = _read_nav_key()
            if key is None:
                return self._parse_typed_choice(self.prompt(session), len(nodes))

            if key == "up":
                selected = max(0, selected - 1)
                self.draw(
                    state,
                    command,
                    nodes,
                    section=section,
                    selected_index=selected,
                    animate=False,
                )
            elif key == "down":
                selected = min(len(nodes) - 1, selected + 1)
                self.draw(
                    state,
                    command,
                    nodes,
                    section=section,
                    selected_index=selected,
                    animate=False,
                )
            elif key == "enter":
                return ("select", selected)
            elif key == "back":
                return ("back", None)
            elif key in ("quit", "cancel"):
                return ("quit", None)
            elif key.isdigit():
                index = int(key) - 1
                if index < len(nodes):
                    return ("select", index)

    def prompt(self, session: PromptSession) -> str | None:
        label = self._accent("menu> ") if self.enabled else "menu> "
        try:
            return session.prompt(self._prompt_text(label)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None

    def message(self, text: str) -> None:
        line = f"{_INDENT}{self._value(text)}"
        if self._alt_screen:
            sys.stdout.write(line + "\n\n")
        else:
            print(line + "\n")
        sys.stdout.flush()

    def echo_executed(self, command: str) -> None:
        """Print the command that ran, on the main screen after the menu closes."""
        self._style.echo_command(command)


def prompt_args(
    session: PromptSession,
    args: list[MenuArg],
    *,
    ui: _MenuUi | None = None,
) -> dict[str, str] | None:
    values: dict[str, str] = {}
    for arg in args:
        hint = f" [{arg.default}]" if arg.default else ""
        if arg.kind == "choice" and arg.choices:
            choices = "/".join(arg.choices)
            label = f"{arg.label} ({choices}){hint}"
        else:
            label = f"{arg.label}{hint}"
        if ui and ui.enabled:
            prompt = f"{_INDENT}{ui._accent('?')} {ui._value(label)}: "
            try:
                raw = session.prompt(ui._prompt_text(prompt)).strip()
            except (EOFError, KeyboardInterrupt):
                return None
        else:
            try:
                raw = session.prompt(f"{label}: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
        if arg.kind == "choice" and arg.choices and raw and raw not in arg.choices:
            if ui:
                ui.message(f"Choose one of: {', '.join(arg.choices)}")
            else:
                print(f"Choose one of: {', '.join(arg.choices)}")
            return None
        values[arg.name] = raw if raw else arg.default
    return values


def _resolve_wizard(
    node: WizardCommand,
    session: PromptSession,
    *,
    ui: _MenuUi | None = None,
) -> str | None:
    values = prompt_args(session, node.args, ui=ui)
    if values is None:
        return None
    if node.template == "connect {host}":
        host = values.get("host", "").strip()
        user = values.get("user", "").strip()
        command = f"connect {host}"
        if user:
            command = f"{command} --user {user}"
        return command
    return build_command(node.template, node.args, values)


def run_interactive_menu(state: ReplState, session: PromptSession) -> str | None:
    """Run the guided menu until the user executes a command or quits."""
    ui = _MenuUi(state.style)
    ui.enter()
    stack: list[_NavFrame] = [
        _NavFrame("Categories", list(filter_categories(state)), "")
    ]
    executed_command: str | None = None
    result: str | None = None

    try:
        while stack:
            frame = stack[-1]
            action, index = ui.read_selection(
                session,
                state,
                frame.command,
                frame.nodes,
                section=frame.title,
                animate=True,
            )

            if action == "quit":
                break
            if action == "back":
                stack.pop()
                if stack:
                    ui._last_command = stack[-1].command
                else:
                    ui._last_command = ""
                continue
            if action == "invalid":
                ui.message("Enter a number, b, or q.")
                continue
            if action != "select" or index is None:
                continue

            node = frame.nodes[index]

            if isinstance(node, FixedCommand):
                executed_command = node.command
                result = parse_input(node.command, state)
                break

            if isinstance(node, WizardCommand):
                command = _resolve_wizard(node, session, ui=ui)
                if command is None:
                    continue
                executed_command = command
                result = parse_input(command, state)
                break

            if isinstance(node, TerminalAction):
                executed_command = frame.command + node.suffix
                result = parse_input(executed_command, state)
                break

            if isinstance(node, ChainStep):
                values = prompt_args(session, node.args, ui=ui) if node.args else {}
                if values is None and node.args:
                    continue
                command = frame.command + build_suffix(node, values or {})
                stack.append(
                    _NavFrame(node.label, filter_nodes(frame.nodes, state), command)
                )
                continue

            if isinstance(node, SetBase):
                values = prompt_args(session, node.args, ui=ui) if node.args else {}
                if values is None and node.args:
                    continue
                command = build_command(node.template, node.args, values or {})
                children = filter_nodes(node.children, state)
                stack.append(_NavFrame(node.label, children, command))
                continue

            if isinstance(node, MenuCategory):
                children = filter_nodes(node.children, state)
                stack.append(_NavFrame(node.label, children, frame.command))
                continue
    finally:
        ui.leave()

    if executed_command is not None:
        ui.echo_executed(executed_command)
    return result
