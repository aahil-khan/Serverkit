"""Tests for the interactive REPL menu."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from serverkit import Server
from serverkit.shell.menu import (
    build_command,
    build_suffix,
    run_interactive_menu,
)
from serverkit.shell.menu_tree import (
    ChainStep,
    MenuArg,
    MenuCategory,
    WizardCommand,
    filter_categories,
    filter_nodes,
    node_available,
)
from serverkit.shell.state import ReplState


class _MiniState:
    def __init__(self, active=None, remote=None):
        self.server = active
        self.remote = remote
        self.active = active if active is not None else MagicMock()


def test_build_suffix_formats_number_and_string():
    step = ChainStep(
        "Memory above",
        '.memory_above({n})',
        [MenuArg("n", "MB", "number", "500")],
    )
    assert build_suffix(step, {"n": "250"}) == ".memory_above(250)"


def test_build_suffix_quotes_string_args():
    step = ChainStep(
        "Named",
        ".named({name})",
        [MenuArg("name", "Name", "string", "python")],
    )
    assert build_suffix(step, {"name": "nginx"}) == '.named("nginx")'


def test_build_command_text_args_are_unquoted():
    args = [MenuArg("question", "Q", "text", "show processes")]
    assert build_command("ask {question}", args, {"question": "list ports"}) == "ask list ports"


def test_build_command_wizard_service():
    args = [
        MenuArg("unit", "Unit", "text", "nginx.service"),
        MenuArg("action", "Action", "choice", "status", ("status", "start")),
    ]
    command = build_command("service {unit} {action}", args, {"unit": "nginx", "action": "status"})
    assert command == "service nginx status"


def test_filter_categories_hides_docker_without_method():
    active = MagicMock(spec=["processes", "memory", "logs"])
    state = ReplState(active)  # type: ignore[arg-type]
    state.remote = None
    labels = [cat.label for cat in filter_categories(state)]
    assert "Processes" in labels
    assert "Docker" not in labels


def test_filter_categories_hides_docker_without_extra():
    state = ReplState(Server())
    state.remote = None
    with patch("serverkit.shell.menu_tree._has_extra", return_value=False):
        labels = [cat.label for cat in filter_categories(state)]
    assert "Docker" not in labels


def test_filter_categories_shows_docker_on_remote_without_local_extra():
    state = ReplState(Server())
    state.remote = MagicMock(spec=["docker"])
    with patch("serverkit.shell.menu_tree._has_extra", return_value=False):
        labels = [cat.label for cat in filter_categories(state)]
    assert "Docker" in labels


def test_node_available_respects_wizard_available():
    wizard = WizardCommand("Import", "import {name}", available=lambda s: s.remote is None)
    local = ReplState(Server())
    local.remote = None
    remote = ReplState(Server())
    remote.remote = MagicMock()
    assert node_available(wizard, local) is True
    assert node_available(wizard, remote) is False


def test_filter_nodes_drops_unavailable_wizard():
    wizard = WizardCommand("Import", "import {name}", available=lambda s: s.remote is None)
    state = ReplState(Server())
    state.remote = MagicMock()
    assert filter_nodes([wizard], state) == []


def test_run_interactive_menu_executes_fixed_command():
    state = ReplState(Server())
    session = MagicMock()
    session.prompt.side_effect = ["1", "1"]

    with patch("serverkit.shell.menu.filter_categories") as categories:
        categories.return_value = [
            MenuCategory(
                "Memory",
                children=[__import__("serverkit.shell.menu_tree", fromlist=["FixedCommand"]).FixedCommand("Summary", "memory")],
            )
        ]
        with patch("serverkit.shell.menu.parse_input", return_value="RAM ok") as parse:
            result = run_interactive_menu(state, session)

    assert result == "RAM ok"
    parse.assert_called_once_with("memory", state)


def test_run_interactive_menu_builds_chain_and_executes():
    state = ReplState(Server())
    session = MagicMock()
    session.prompt.side_effect = ["1", "1", "1", "", "2"]

    from serverkit.shell.menu_tree import FixedCommand, SetBase, TerminalAction

    chain = [
        ChainStep("Memory above", ".memory_above({n})", [MenuArg("n", "MB", "number", "500")]),
        TerminalAction("Summarize", ".summarize()"),
    ]
    categories = [
        MenuCategory(
            "Processes",
            children=[SetBase("Build", "processes()", children=chain)],
        )
    ]

    with patch("serverkit.shell.menu.filter_categories", return_value=categories):
        with patch("serverkit.shell.menu.parse_input", return_value="done") as parse:
            result = run_interactive_menu(state, session)

    assert result == "done"
    parse.assert_called_once_with("processes().memory_above(500).summarize()", state)


def test_run_interactive_menu_keyboard_navigation():
    session = MagicMock()

    from serverkit.shell.menu_tree import FixedCommand

    categories = [
        MenuCategory(
            "Memory",
            children=[
                FixedCommand("Summary", "memory"),
                FixedCommand("Details", "memory --verbose"),
            ],
        )
    ]

    with patch("serverkit.shell.style.color_enabled", return_value=True):
        state = ReplState(Server())
        with patch("serverkit.shell.menu.time.sleep"):
            with patch(
                "serverkit.shell.menu._read_nav_key",
                side_effect=["enter", "down", "enter"],
            ):
                with patch("serverkit.shell.menu.filter_categories", return_value=categories):
                    with patch(
                        "serverkit.shell.menu.parse_input",
                        return_value="verbose",
                    ) as parse:
                        result = run_interactive_menu(state, session)

    assert result == "verbose"
    parse.assert_called_once_with("memory --verbose", state)


def test_run_interactive_menu_no_color_uses_keyboard_navigation():
    """NO_COLOR disables ANSI styling but keeps the full interactive menu."""
    session = MagicMock()

    from serverkit.shell.menu_tree import FixedCommand
    from serverkit.shell.style import ShellStyle

    categories = [
        MenuCategory(
            "Memory",
            children=[
                FixedCommand("Summary", "memory"),
                FixedCommand("Details", "memory --verbose"),
            ],
        )
    ]

    style = ShellStyle(enabled=False)
    state = ReplState(Server(), style=style)
    with patch("serverkit.shell.menu.time.sleep"):
        with patch(
            "serverkit.shell.menu._read_nav_key",
            side_effect=["enter", "down", "enter"],
        ):
            with patch("serverkit.shell.menu.filter_categories", return_value=categories):
                with patch(
                    "serverkit.shell.menu.parse_input",
                    return_value="verbose",
                ) as parse:
                    result = run_interactive_menu(state, session)

    assert result == "verbose"
    parse.assert_called_once_with("memory --verbose", state)


def test_run_interactive_menu_quit_returns_none():
    state = ReplState(Server())
    session = MagicMock()
    session.prompt.return_value = "q"

    with patch("serverkit.shell.menu.filter_categories", return_value=[]):
        assert run_interactive_menu(state, session) is None
