"""Tests for the cosmetic REPL cat mascot."""

from __future__ import annotations

from unittest.mock import patch

from serverkit.shell.mascot import (
    ShellMascot,
    _IDLE,
    _STARTLED,
    _pick_pose,
    _pick_quip,
    _render,
)
from serverkit.shell.style import ShellStyle


def test_mascot_disabled_by_default():
    style = ShellStyle(accent="1;36", enabled=True)
    mascot = ShellMascot.from_style(style)
    assert mascot.active is False


def test_mascot_disabled_when_config_off():
    style = ShellStyle(accent="1;36", enabled=True)
    style.ui["mascot"] = False
    mascot = ShellMascot.from_style(style)
    assert mascot.active is False


def test_mascot_inactive_without_tty():
    style = ShellStyle(accent="1;36", enabled=True)
    with patch("serverkit.shell.mascot.ShellMascot._tty_ok", return_value=False):
        mascot = ShellMascot.from_style(style)
    assert mascot.active is False


def test_pick_pose_reacts_to_errors():
    assert _pick_pose("logs()", "err", animate=False) == _STARTLED


def test_pick_quip_topic_for_memory():
    quip = _pick_quip("memory", "ok")
    assert quip  # from memory topic pool


def test_render_includes_cat_and_quip():
    style = ShellStyle(accent="1;36", enabled=False)
    text = _render(_IDLE, 4, "purr~", style=style)
    assert "/\\_/\\" in text
    assert "purr~" in text


def test_react_prints_single_cat(capsys):
    style = ShellStyle(accent="1;36", enabled=False)
    mascot = ShellMascot(enabled=True, style=style, animate=False)
    with patch.object(ShellMascot, "_tty_ok", return_value=True):
        mascot._enabled = True
        mascot.react("processes.all()", outcome="ok")
    out = capsys.readouterr().out
    assert out.count("/\\_/\\") == 1
    assert "( o.o )" in out or "( ^.^ )" in out


def test_react_skips_clear(capsys):
    style = ShellStyle(accent="1;36", enabled=False)
    mascot = ShellMascot(enabled=True, style=style, animate=False)
    with patch.object(ShellMascot, "_tty_ok", return_value=True):
        mascot._enabled = True
        mascot.react("clear")
    assert capsys.readouterr().out == ""


def test_react_skips_empty_command(capsys):
    style = ShellStyle(accent="1;36", enabled=False)
    mascot = ShellMascot(enabled=True, style=style, animate=False)
    with patch.object(ShellMascot, "_tty_ok", return_value=True):
        mascot._enabled = True
        mascot.react("   ")
    assert capsys.readouterr().out == ""
