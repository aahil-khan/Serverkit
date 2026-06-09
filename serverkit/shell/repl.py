"""Interactive REPL entry point (Dev 2)."""

from __future__ import annotations

from prompt_toolkit import PromptSession

from serverkit import Server
from serverkit.shell.autocomplete import SDKCompleter
from serverkit.shell.parser import format_user_error, parse_input
from serverkit.shell.state import ReplState


def run_shell() -> None:
    """Run the interactive ServerKit shell (PDF: shell/repl.py)."""
    server = Server()
    state = ReplState(server)
    session = PromptSession(completer=SDKCompleter())
    print("ServerKit shell v1.0")
    print('Type "help" for commands. Ctrl+C or "exit" to quit.')
    print()

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
