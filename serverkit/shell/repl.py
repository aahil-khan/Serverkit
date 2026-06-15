"""Interactive REPL entry point (Dev 2)."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from serverkit import Server
from serverkit.shell.autocomplete import SDKCompleter
from serverkit.shell.banner import print_banner
from serverkit.shell.lexer import ServerKitLexer
from serverkit.shell.mascot import ShellMascot
from serverkit.shell.menu import run_interactive_menu
from serverkit.shell.parser import format_user_error, parse_input
from serverkit.shell.state import ReplState
from serverkit.shell.style import ShellStyle, set_active_style

try:
    from prompt_toolkit.formatted_text import ANSI
except ImportError:  # pragma: no cover
    ANSI = None  # type: ignore[misc, assignment]

_PROMPT_STYLE = Style.from_dict(
    {
        "string": "ansigreen",
        "number": "ansiyellow",
        "keyword": "ansibrightmagenta bold",
        "method": "ansicyan",
    }
)


def _prompt_arg(style: ShellStyle, state: ReplState):
    text = style.prompt_text(state)
    if style.enabled and ANSI is not None:
        return ANSI(text)
    return text


def _create_session(style: ShellStyle) -> PromptSession:
    kwargs: dict = {"completer": SDKCompleter()}
    if style.enabled and style.ui.get("syntax_highlight", True):
        kwargs["lexer"] = ServerKitLexer()
        kwargs["style"] = _PROMPT_STYLE
    return PromptSession(**kwargs)


def run_shell() -> None:
    """Run the interactive ServerKit shell (PDF: shell/repl.py)."""
    style = ShellStyle()
    set_active_style(style)
    server = Server()
    state = ReplState(server, style=style)
    session = _create_session(style)
    mascot = ShellMascot.from_style(style)
    print_banner(style=style)

    def _mascot_after(command: str, *, outcome: str = "ok", result: str | None = None) -> None:
        if result is not None and style._looks_like_error(result):
            outcome = "err"
        mascot.react(command, outcome=outcome)

    try:
        while True:
            try:
                text = session.prompt(_prompt_arg(style, state))
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text.strip():
                continue
            stripped = text.strip()
            if stripped in ("exit", "quit"):
                break
            if stripped == "menu":
                try:
                    result = run_interactive_menu(state, session)
                    if result is not None:
                        print(style.format_shell_output(result))
                        print()
                        _mascot_after("menu", result=result)
                except Exception as exc:  # noqa: BLE001 — user-facing REPL
                    print(format_user_error(exc, style=style))
                    print()
                    _mascot_after("menu", outcome="err")
                continue
            try:
                result = parse_input(text, state, style=style)
                if result is not None:
                    print(style.format_shell_output(result))
                    print()
                _mascot_after(stripped, result=result)
            except Exception as exc:  # noqa: BLE001 — user-facing REPL
                print(format_user_error(exc, style=style))
                print()
                _mascot_after(stripped, outcome="err")
    finally:
        state.close_remote()
        style.farewell()


def main() -> None:
    """Console script: `serverkit`."""
    from serverkit.shell.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
