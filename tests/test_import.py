"""Smoke test that the package layout imports cleanly."""

from serverkit import Server


def test_server_instantiates():
    server = Server()
    assert server is not None


def test_process_history_property_points_at_helper():
    from serverkit.processes.history import ProcessHistory

    assert Server().process_history is ProcessHistory
