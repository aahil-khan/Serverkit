"""Interactive REPL entry point (Dev 2)."""

from __future__ import annotations

from prompt_toolkit import PromptSession

from serverkit import Server
from serverkit.shell.autocomplete import SDKCompleter
from serverkit.shell.banner import print_banner
from serverkit.shell.menu import run_interactive_menu
from serverkit.shell.parser import format_user_error, parse_input
from serverkit.shell.state import ReplState
from serverkit.shell.style import ShellStyle, set_active_style

try:
    from prompt_toolkit.formatted_text import ANSI
except ImportError:  # pragma: no cover
    ANSI = None  # type: ignore[misc, assignment]


def _prompt_arg(style: ShellStyle, state: ReplState):
    text = style.prompt_text(state)
    if style.enabled and ANSI is not None:
        return ANSI(text)
    return text


def run_shell() -> None:
    """Run the interactive ServerKit shell (PDF: shell/repl.py)."""
    style = ShellStyle()
    set_active_style(style)
    server = Server()
    state = ReplState(server, style=style)
    session = PromptSession(completer=SDKCompleter())
    print_banner(style=style)

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
                        print(style.colorize_output(result))
                        print()
                except Exception as exc:  # noqa: BLE001 — user-facing REPL
                    print(format_user_error(exc, style=style))
                    print()
                continue
            try:
                result = parse_input(text, state, style=style)
                if result is not None:
                    print(style.colorize_output(result))
                    print()
            except Exception as exc:  # noqa: BLE001 — user-facing REPL
                print(format_user_error(exc, style=style))
                print()
    finally:
        state.close_remote()
        style.farewell()


def main() -> None:
    """Console script: `serverkit`."""
    run_shell()


if __name__ == "__main__":
    main()
