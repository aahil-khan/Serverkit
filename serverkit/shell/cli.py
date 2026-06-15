"""Command-line interface for the ``serverkit`` console script."""

from __future__ import annotations

import argparse
import sys

from serverkit import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="serverkit",
        description="Interactive shell for ServerKit — Linux server operations.",
        epilog='Run with no flags to start the REPL. Type "help" inside the shell for commands.',
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Console script entry point."""
    build_parser().parse_args(argv)
    from serverkit.config import Config
    from serverkit.shell.repl import run_shell

    Config.load()
    run_shell()


if __name__ == "__main__":
    main(sys.argv[1:])
