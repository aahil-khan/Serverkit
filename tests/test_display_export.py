from serverkit.logs.logfile import LogFile
from serverkit.processes.manager import ProcessCollection
from serverkit.processes.process import Process


def test_process_collection_export_csv(tmp_path):
    procs = ProcessCollection([Process(1, "python", 100.0, 5.0, username="dev")])
    path = tmp_path / "procs.csv"
    procs.export(str(path))
    text = path.read_text()
    assert "python" in text
    assert "memory_mb" in text


def test_logfile_export_json(tmp_path):
    log = tmp_path / "x.log"
    log.write_text("ERROR one\nINFO two\n", encoding="utf-8")
    out = tmp_path / "errors.json"
    LogFile(str(log)).errors().export(str(out), fmt="json")
    data = __import__("json").loads(out.read_text())
    assert len(data) == 1


def test_process_display_plain():
    text = ProcessCollection([Process(1, "a", 10, 1)]).display(use_rich=False)
    assert "Processes" in text
    assert "a" in text
