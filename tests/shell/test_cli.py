"""Tests for the serverkit CLI entry point."""

from __future__ import annotations

import pytest

from serverkit import __version__
from serverkit.shell.cli import build_parser, main


def test_parser_help(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "serverkit" in out
    assert "--version" in out


def test_parser_version(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_main_version_skips_repl(monkeypatch):
    monkeypatch.setattr(
        "serverkit.config.Config.load",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Config.load should not run")),
    )
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_main_help_skips_repl(monkeypatch):
    monkeypatch.setattr(
        "serverkit.config.Config.load",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Config.load should not run")),
    )
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_main_starts_repl(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr("serverkit.config.Config.load", lambda: calls.append("config"))
    monkeypatch.setattr("serverkit.shell.repl.run_shell", lambda: calls.append("repl"))

    main([])
    assert calls == ["config", "repl"]
