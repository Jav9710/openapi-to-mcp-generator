"""
Módulo de inteligencia artificial.

Integra Ollama para análisis de specs, generación de código,
documentación y validación usando modelos LLM locales.
"""

from .ollama_client import OllamaClient, get_ai_client

__all__ = ["OllamaClient", "get_ai_client"]
