import json

import pytest

from serverkit.config import Config, _bootstrap_user_config, _load_jsonc, _strip_jsonc
from serverkit.exceptions import ConfigurationError


def test_config_defaults():
    cfg = Config()
    assert cfg.get("workflow", "executor") == "sequential"


def test_config_merge(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"workflow": {"executor": "parallel"}}')
    cfg = Config.load(str(path))
    assert cfg.get("workflow", "executor") == "parallel"
    assert cfg.get("output", "use_rich") is True


def test_load_jsonc_ignores_line_comments():
    raw = """
    {
      // output section
      "output": { "use_rich": false },
      "workflow": { "executor": "sequential" }
    }
    """
    data = _load_jsonc(raw)
    assert data["output"]["use_rich"] is False


def test_strip_jsonc_preserves_urls_in_strings():
    raw = '{"remote": {"key_path": "https://example.com/key"}}'
    assert json.loads(_strip_jsonc(raw))["remote"]["key_path"] == "https://example.com/key"


def test_bootstrap_writes_commented_template(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr("serverkit.config.CONFIG_PATH", str(path))
    assert not path.exists()
    cfg = Config.load()
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "//" in text
    assert cfg.get("output", "use_rich") is True
    assert cfg.get("ollama", "model") == "phi3:mini"


def test_custom_missing_path_does_not_bootstrap(tmp_path):
    path = tmp_path / "missing.json"
    cfg = Config.load(str(path))
    assert not path.exists()
    assert cfg.get("workflow", "executor") == "sequential"


def test_load_invalid_jsonc_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not valid }")
    with pytest.raises(ConfigurationError):
        Config.load(str(path))


def test_bootstrap_helper_idempotent_content(tmp_path):
    path = tmp_path / "config.json"
    _bootstrap_user_config(str(path))
    first = path.read_text(encoding="utf-8")
    _bootstrap_user_config(str(path))
    assert path.read_text(encoding="utf-8") == first
