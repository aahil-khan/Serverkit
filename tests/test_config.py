from serverkit.config import Config


def test_config_defaults():
    cfg = Config()
    assert cfg.get("workflow", "executor") == "sequential"


def test_config_merge(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"workflow": {"executor": "parallel"}}')
    cfg = Config.load(str(path))
    assert cfg.get("workflow", "executor") == "parallel"
    assert cfg.get("output", "use_rich") is True
