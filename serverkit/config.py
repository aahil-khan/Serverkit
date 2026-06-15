"""Load and save ~/.serverkit/config.json."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any

from serverkit.exceptions import ConfigurationError

CONFIG_DIR = os.path.expanduser("~/.serverkit/")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS: dict[str, Any] = {
    "output": {
        "use_rich": True,
        "theme": "default",
        "accent": None,
        "show_progress": False,
        "animate_banner": True,
        "skip_animation_on_key": True,
        "syntax_highlight": True,
        "mascot": False,
        "mascot_animate": True,
    },
    "workflow": {
        "executor": "sequential",
        "versioning": True,
    },
    "ollama": {
        "model": "phi3:mini",
    },
    "remote": {
        "default_user": None,
        "key_path": None,
        "port": 22,
    },
}


class Config:
    """Merged view of defaults and user config file."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = deepcopy(DEFAULTS)
        if data:
            self._merge(self._data, data)

    @classmethod
    def load(cls, path: str | None = None) -> Config:
        path = path or CONFIG_PATH
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, encoding="utf-8") as f:
                return cls(json.load(f))
        except (json.JSONDecodeError, OSError) as exc:
            raise ConfigurationError(f"Cannot read config: {path}") from exc

    def save(self, path: str | None = None) -> None:
        path = path or CONFIG_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self._data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    @staticmethod
    def _merge(base: dict, override: dict) -> None:
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                Config._merge(base[key], value)
            else:
                base[key] = value
