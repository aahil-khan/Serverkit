"""Unit tests for REPL startup banner."""

from __future__ import annotations

from serverkit import __version__
from serverkit.shell.banner import build_banner_lines


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
