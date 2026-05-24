"""Smoke test that the package layout imports cleanly."""

from serverkit import Server


def test_server_instantiates():
    server = Server()
    assert server is not None
