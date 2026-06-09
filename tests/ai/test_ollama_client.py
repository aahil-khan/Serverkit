"""Unit tests for OllamaClient (mocked HTTP)."""

from __future__ import annotations

from serverkit.ai.ollama_client import OllamaClient


def test_ollama_ask_success(monkeypatch):
    class Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"response": "hello\n"}

    def fake_post(url, json=None, timeout=None, **kwargs):
        assert "/api/generate" in url
        assert json["model"] == "test-model"
        return Resp()

    import requests

    monkeypatch.setattr(requests, "post", fake_post)

    client = OllamaClient(model="test-model", base_url="http://localhost:11434")
    assert client.ask("ping").strip() == "hello"


def test_ollama_is_available_true(monkeypatch):
    class Resp:
        def raise_for_status(self) -> None:
            return None

    import requests

    monkeypatch.setattr(requests, "get", lambda url, timeout=None, **kw: Resp())
    assert OllamaClient(base_url="http://localhost:11434").is_available() is True


def test_ollama_is_available_false(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("nope")

    monkeypatch.setattr(requests, "get", boom)
    assert OllamaClient().is_available() is False
