"""Remote host output parsers."""

from __future__ import annotations

import pytest

from serverkit.remote.host_parsers import (
    disk_partitions_from_df,
    env_dict_from_printenv,
    file_entries_from_find_printf_output,
)


def test_disk_partitions_from_df():
    sample = """Filesystem     1024-blocks      Used Available Capacity Mounted on
/dev/root      100000      50000     45000      53% /
"""
    parts = disk_partitions_from_df(sample)
    assert len(parts) == 1
    assert parts[0].mountpoint == "/"
    assert parts[0].percent == 53.0


def test_env_dict_from_printenv():
    d = env_dict_from_printenv("A=1\nB=two\n")
    assert d == {"A": "1", "B": "two"}


def test_file_entries_from_find_printf_output():
    sample = "1048576\t/var/log/huge.log\n2048\t/tmp/small.txt\n"
    rows = file_entries_from_find_printf_output(sample, limit=10)
    assert len(rows) == 2
    assert rows[0].path == "/var/log/huge.log"
    assert rows[0].size_mb == pytest.approx(1.0, rel=1e-3)
