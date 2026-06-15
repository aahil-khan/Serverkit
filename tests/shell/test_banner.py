"""Unit tests for REPL startup banner."""

from __future__ import annotations

from unittest.mock import patch

from serverkit import __version__
from serverkit.shell.banner import (
    _LOGO_PALETTE,
    build_banner_lines,
    print_banner,
)


def test_build_banner_lines_contains_title():
    text = "\n".join(build_banner_lines(color=False))
    assert "S E R V E R K I T" in text


def test_build_banner_lines_has_framed_logo():
    lines = build_banner_lines(color=False)
    logo = lines[:5]
    assert len(logo) == 5
    widths = {len(line) for line in logo}
    assert len(widths) == 1
    assert logo[0].startswith("  ▄")
    assert logo[-1].startswith("  ▀")


def test_build_banner_lines_contains_serverkit_info():
    text = "\n".join(build_banner_lines(color=False))
    assert f"Version: {__version__}" in text
    assert "Python:" in text
    assert "Modules:" in text
    assert '"help"' in text
    assert '"exit"' in text


def test_build_banner_lines_uses_given_accent_color():
    lines = build_banner_lines(color=True, accent_color="1;35")
    assert any("\033[1;35m" in line for line in lines)


def test_print_banner_picks_random_palette_color():
    with patch("serverkit.shell.banner.random.choice", return_value="1;33") as choice:
        lines = build_banner_lines(color=True, accent_color=None)
    choice.assert_called_once_with(_LOGO_PALETTE)
    assert any("\033[1;33m" in line for line in lines)


def test_print_banner_skips_animation_when_disabled(capsys):
    with patch("serverkit.shell.banner.time.sleep") as sleep:
        print_banner(color=False, animate=False)
    sleep.assert_not_called()
    output = capsys.readouterr().out
    assert "S E R V E R K I T" in output
    assert f"Version: {__version__}" in output


def test_print_banner_runs_animation_when_enabled(capsys):
    with (
        patch("serverkit.shell.banner._color_enabled", return_value=True),
        patch("serverkit.shell.banner._pick_accent_color", return_value="1;36"),
        patch("serverkit.shell.banner.time.sleep") as sleep,
        patch("serverkit.shell.banner._hide_cursor") as hide,
        patch("serverkit.shell.banner._show_cursor") as show,
    ):
        print_banner(color=True, animate=True)
    sleep.assert_called()
    hide.assert_called_once()
    show.assert_called_once()
    output = capsys.readouterr().out
    assert "S E R V E R K I T" in output
    assert "Version" in output
    assert "Python" in output
    assert "Modules" in output
    assert "booting serverkit shell" in output
    assert "shell online" in output
