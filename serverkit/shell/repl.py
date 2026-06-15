"""Interactive REPL entry point (Dev 2)."""

from __future__ import annotations

from prompt_toolkit import PromptSession

from serverkit import Server
from serverkit.shell.autocomplete import SDKCompleter
from serverkit.shell.banner import print_banner
from serverkit.shell.menu import run_interactive_menu
from serverkit.shell.parser import format_user_error, parse_input
from serverkit.shell.state import ReplState


def run_shell() -> None:
    """Run the interactive ServerKit shell (PDF: shell/repl.py)."""
    server = Server()
    state = ReplState(server)
    session = PromptSession(completer=SDKCompleter())
    print_banner()

    try:
        while True:
            try:
                text = session.prompt("> ")
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
                        print(result)
                        print()
                except Exception as exc:  # noqa: BLE001 — user-facing REPL
                    print(format_user_error(exc))
                    print()
                continue
            try:
                result = parse_input(text, state)
                if result is not None:
                    print(result)
                    print()
            except Exception as exc:  # noqa: BLE001 — user-facing REPL
                print(format_user_error(exc))
                print()
    finally:
        state.close_remote()


def main() -> None:
    """Console script: `serverkit`."""
    run_shell()


if __name__ == "__main__":
    main()
