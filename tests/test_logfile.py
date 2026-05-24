"""Milestone 4: LogFile + LogManager."""

from pathlib import Path

import pytest

from serverkit import Server
from serverkit.logs.logfile import LogFile
from serverkit.logs.manager import LogManager

SAMPLE_LOG = """\
2024-01-01 INFO Started
2024-01-01 WARNING Disk almost full
2024-01-01 ERROR Connection timeout
2024-01-01 ERROR Database down
2024-01-01 INFO Retrying connection
"""


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    path = tmp_path / "app.log"
    path.write_text(SAMPLE_LOG, encoding="utf-8")
    return path


def test_errors_filters_lines(log_path: Path):
    lines = LogFile(str(log_path)).errors().all()
    assert len(lines) == 2
    assert all("ERROR" in line for line in lines)


def test_chain_errors_then_contains(log_path: Path):
    lines = LogFile(str(log_path)).errors().contains("Database").all()
    assert len(lines) == 1
    assert "Database down" in lines[0]


def test_tail_returns_last_n_lines(log_path: Path):
    lines = LogFile(str(log_path)).tail(2).all()
    assert len(lines) == 2
    assert "ERROR Database down" in lines[0] or "Database down" in lines[0]


def test_summarize_counts_from_full_file_not_filtered_view(log_path: Path):
    summary = LogFile(str(log_path)).errors().summarize()
    assert summary == "Total: 5 lines | Errors: 2 | Warnings: 1"


def test_manager_and_server_open_same_path(log_path: Path):
    via_manager = LogManager().open(str(log_path)).warnings().all()
    via_server = Server().logs(str(log_path)).warnings().all()
    assert len(via_manager) == 1
    assert via_manager == via_server
