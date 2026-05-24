from serverkit.processes.aliases import app_name
from serverkit.processes.manager import ProcessCollection
from serverkit.processes.process import Process


def test_app_name_maps_firefox_children():
    assert app_name("Isolated Web Co") == "firefox"
    assert app_name("cursor") == "cursor"


def test_group_by_name_with_aliases():
    procs = ProcessCollection(
        [
            Process(1, "firefox", 400, 1),
            Process(2, "Isolated Web Co", 600, 1),
        ]
    )
    groups = procs.group_by_name(use_aliases=True)
    assert len(groups) == 1
    assert "firefox" in groups
    assert sum(p.memory_mb for p in groups["firefox"].all()) == 1000.0
