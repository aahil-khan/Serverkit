"""HTTP client for local Ollama API (Dev 2)."""

from __future__ import annotations

import json
import os
from typing import Any

from serverkit.exceptions import OptionalDependencyError

DEFAULT_MODEL = "phi3:mini"
OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _requests():
    try:
        import requests
    except ImportError as exc:
        raise OptionalDependencyError(
            "AI layer requires HTTP client. Install: pip install serverkit[ai]"
        ) from exc
    return requests


class OllamaClient:
    """Thin wrapper around Ollama's `/api/generate` endpoint."""

    def __init__(self, model: str | None = None, *, base_url: str | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self._base = (base_url or OLLAMA_BASE).rstrip("/")

    @property
    def generate_url(self) -> str:
        return f"{self._base}/api/generate"

    def ask(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        num_predict: int | None = None,
        stop: list[str] | None = None,
    ) -> str:
        requests = _requests()
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if stop:
            payload["stop"] = list(stop)
        opts: dict[str, Any] = {}
        if temperature is not None:
            opts["temperature"] = temperature
        if num_predict is not None:
            opts["num_predict"] = num_predict
        if opts:
            payload["options"] = opts
        try:
            resp = requests.post(self.generate_url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("response", ""))
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "Ollama not reachable. Start the daemon (e.g. `ollama serve`) "
                f"and ensure it listens on {self._base}."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Ollama request timed out: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned non-JSON: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    def is_available(self) -> bool:
        try:
            requests = _requests()
            requests.get(f"{self._base}/", timeout=2)
            return True
        except Exception:
            return False
