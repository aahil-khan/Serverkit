"""Tests for shared shell styling."""

from __future__ import annotations

from unittest.mock import patch

from serverkit.shell.parser import HELP_TEXT, build_help_text
from serverkit.shell.style import ShellStyle


class _State:
    remote = None


def test_shell_style_plain_prompt():
    style = ShellStyle(accent="1;36", enabled=False)
    assert style.prompt_text(_State()) == "local > "


def test_shell_style_colored_prompt():
    style = ShellStyle(accent="1;36", enabled=True)
    text = style.prompt_text(_State())
    assert "local" in text
    assert "▸" in text


def test_format_error_and_success():
    style = ShellStyle(accent="1;36", enabled=True)
    assert "boom" in style.format_error("boom")
    assert "[ err ]" in style.format_error("boom")
    assert "connected" in style.format_success("connected")


def test_format_shell_output_tags_parser_errors():
    style = ShellStyle(accent="1;36", enabled=True)
    out = style.format_shell_output("Unknown command: logs\nType help for a list of commands.")
    assert "[ err ]" in out
    assert "Unknown command: logs" in out


def test_format_shell_output_skips_styled_success():
    style = ShellStyle(accent="1;36", enabled=True)
    ok = style.format_success("connected")
    assert style.format_shell_output(ok) == ok


def test_format_shell_output_colorizes_normal_output():
    style = ShellStyle(accent="1;36", enabled=True)
    out = style.format_shell_output("ERROR something failed\nplain line")
    assert "\033[" in out
    assert "ERROR" in out


def test_build_help_text_plain_when_disabled():
    assert build_help_text(None) == HELP_TEXT
    style = ShellStyle(enabled=False)
    assert build_help_text(style) == HELP_TEXT


def test_build_help_text_styled_header():
    style = ShellStyle(accent="1;36", enabled=True)
    text = build_help_text(style)
    assert "help" in text
    assert "Shell" in text
    assert "processes.all()" in text


def test_resolve_accent_from_theme():
    with (
        patch("serverkit.config.Config.load") as load,
        patch("serverkit.shell.style.random.choice", return_value="1;33") as choice,
    ):
        load.return_value.get = lambda *keys, default=None: default
        style = ShellStyle(enabled=True)
    assert style.accent_code == "1;33"
    choice.assert_called_once()
