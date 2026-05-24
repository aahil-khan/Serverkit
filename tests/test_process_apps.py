from serverkit.processes.manager import ProcessCollection
from serverkit.processes.process import Process


def test_summarise_alias():
    assert ProcessCollection([Process(1, "a", 10, 1)]).summarise() == "a: 10.0 MB"


def test_group_by_name_sums_memory():
    procs = ProcessCollection(
        [
            Process(1, "cursor", 600, 10),
            Process(2, "cursor", 400, 5),
            Process(3, "nginx", 50, 1),
        ]
    )
    groups = procs.group_by_name()
    assert len(groups["cursor"].all()) == 2
    assert procs.summarize_by_name().startswith("cursor: 1000.0 MB")


def test_display_by_name_plain():
    text = ProcessCollection([Process(1, "python", 100, 1)]).display_by_name(
        use_rich=False
    )
    assert "Apps" in text
    assert "python" in text
