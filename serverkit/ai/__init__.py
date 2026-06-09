"""Local AI layer via Ollama (Dev 2)."""

from serverkit.ai.analyzer import Analyzer, strip_model_json
from serverkit.ai.ollama_client import DEFAULT_MODEL, OllamaClient

__all__ = [
    "Analyzer",
    "DEFAULT_MODEL",
    "OllamaClient",
    "strip_model_json",
]
