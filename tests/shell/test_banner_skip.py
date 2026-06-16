"""Tests for banner skip-on-keypress."""

from __future__ import annotations

from unittest.mock import patch

from serverkit.shell.banner import print_banner
from serverkit.shell.banner_skip import SkipWatcher, interruptible_sleep


def test_interruptible_sleep_returns_true_when_skipped():
    skip = SkipWatcher()
    skip._requested.set()
    assert interruptible_sleep(1.0, skip) is True


def test_interruptible_sleep_without_skip():
    assert interruptible_sleep(0, None) is False


def test_print_banner_skips_animation_on_keypress():
    with (
        patch("serverkit.shell.banner._color_enabled", return_value=True),
        patch("serverkit.shell.banner._pick_accent_color", return_value="1;36"),
        patch("serverkit.shell.banner.interruptible_sleep", return_value=True),
        patch("serverkit.shell.banner._hide_cursor"),
        patch("serverkit.shell.banner._show_cursor"),
        patch("serverkit.shell.banner._finish_on_skip") as finish,
    ):
        print_banner(color=True, animate=True)
    finish.assert_called_once()
