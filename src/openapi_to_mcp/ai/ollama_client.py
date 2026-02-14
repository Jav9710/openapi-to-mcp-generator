"""
Cliente Ollama para integración con LLMs locales.

Proporciona métodos de alto nivel para las tareas de IA
del generador MCP: análisis de specs, generación de código,
documentación y validación.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

from ..config.settings import OllamaSettings, get_settings

logger = logging.getLogger(__name__)


class AITaskType(str, Enum):
    """Tipos de tarea IA disponibles."""

    SPEC_ANALYSIS = "spec_analysis"
    CODE_GENERATION = "code_generation"
    DOCUMENTATION = "documentation"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    SECURITY_AUDIT = "security_audit"


@dataclass
class AIResponse:
    """Respuesta de una tarea IA."""

    task_type: AITaskType
    model: str
    content: str
    tokens_used: int = 0
    duration_ms: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OllamaHealth:
    """Estado de salud de Ollama."""

    healthy: bool
    version: Optional[str] = None
    models: list[str] = field(default_factory=list)
    error: Optional[str] = None


class RateLimiter:
    """Rate limiter simple basado en ventana de tiempo."""

    def __init__(self, max_rpm: int = 30):
        self.max_rpm = max_rpm
        self._requests: list[float] = []

    def acquire(self) -> bool:
        """Intenta adquirir permiso. Retorna True si permitido."""
        now = time.time()
        self._requests = [t for t in self._requests if now - t < 60]
        if len(self._requests) >= self.max_rpm:
            return False
        self._requests.append(now)
        return True

    def wait_if_needed(self) -> None:
        """Espera si es necesario antes de hacer una request."""
        while not self.acquire():
            time.sleep(1.0)


class OllamaClient:
    """Cliente para interactuar con Ollama API."""

    def __init__(self, settings: OllamaSettings | None = None):
        self.settings = settings or get_settings().ollama
        self._client = httpx.Client(
            base_url=self.settings.base_url,
            timeout=httpx.Timeout(self.settings.timeout),
        )
        self._rate_limiter = RateLimiter(self.settings.rate_limit_rpm)

    def health_check(self) -> OllamaHealth:
        """Verifica conectividad con Ollama."""
        try:
            resp = self._client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return OllamaHealth(healthy=True, models=models)
        except Exception as e:
            return OllamaHealth(healthy=False, error=str(e))

    def list_models(self) -> list[dict[str, Any]]:
        """Lista modelos disponibles en Ollama."""
        try:
            resp = self._client.get("/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception:
            return []

    def pull_model(self, model_name: str) -> bool:
        """Descarga un modelo en Ollama."""
        try:
            resp = self._client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=httpx.Timeout(600),
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Error pulling model %s: %s", model_name, e)
            return False

    def _generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        format_json: bool = False,
    ) -> dict[str, Any]:
        """Llamada base a Ollama generate API."""
        self._rate_limiter.wait_if_needed()

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        resp = self._client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()

    def _model_for_task(self, task_type: AITaskType) -> str:
        """Selecciona el modelo apropiado según el tipo de tarea."""
        mapping = {
            AITaskType.SPEC_ANALYSIS: self.settings.model_spec_analysis,
            AITaskType.CODE_GENERATION: self.settings.model_code_generation,
            AITaskType.DOCUMENTATION: self.settings.model_documentation,
            AITaskType.VALIDATION: self.settings.model_validation,
            AITaskType.OPTIMIZATION: self.settings.model_code_generation,
            AITaskType.SECURITY_AUDIT: self.settings.model_spec_analysis,
        }
        return mapping.get(task_type, self.settings.model_spec_analysis)

    # ==================== Tareas de Alto Nivel ====================

    def analyze_spec(self, spec_content: str) -> AIResponse:
        """
        Analiza una especificación OpenAPI y genera recomendaciones.

        Returns:
            AIResponse con análisis JSON incluyendo:
            - quality_score (0-100)
            - issues encontrados
            - mejoras sugeridas
            - endpoints prioritarios para MCP
        """
        system = (
            "You are an expert API architect specialized in OpenAPI specifications "
            "and Model Context Protocol (MCP). Analyze the given OpenAPI spec and "
            "provide a structured assessment."
        )
        prompt = f"""Analyze this OpenAPI specification and provide a JSON response with:
1. "quality_score": overall quality score 0-100
2. "summary": brief description of the API
3. "total_endpoints": number of endpoints
4. "issues": list of issues found (each with "severity", "path", "message")
5. "improvements": list of suggested improvements
6. "mcp_recommendations": {{
     "priority_endpoints": endpoints best suited for MCP tools,
     "resource_candidates": endpoints suitable as MCP resources,
     "suggested_tools": recommended MCP tool names
   }}
7. "security_assessment": brief security analysis

OpenAPI Spec:
```yaml
{spec_content[:8000]}
```"""
        return self._execute_task(
            AITaskType.SPEC_ANALYSIS, system, prompt, format_json=True
        )

    def generate_mcp_enhancements(
        self,
        spec_summary: str,
        tool_names: list[str],
    ) -> AIResponse:
        """
        Sugiere mejoras para un servidor MCP generado.

        Returns:
            AIResponse con sugerencias de mejoras de código.
        """
        system = (
            "You are an expert MCP (Model Context Protocol) developer. "
            "Suggest enhancements for generated MCP servers to improve "
            "usability for LLM agents."
        )
        prompt = f"""Given an MCP server with these tools: {', '.join(tool_names)}

API Summary: {spec_summary}

Provide a JSON response with:
1. "error_handling": suggested error handling improvements
2. "tool_descriptions": improved descriptions for each tool
3. "parameter_validation": validation rules to add
4. "caching_strategy": caching recommendations
5. "rate_limiting": rate limiting suggestions
6. "batch_operations": potential batch operation tools
"""
        return self._execute_task(
            AITaskType.CODE_GENERATION, system, prompt, format_json=True
        )

    def generate_documentation(
        self,
        spec_content: str,
        server_name: str,
    ) -> AIResponse:
        """
        Genera documentación para un servidor MCP.

        Returns:
            AIResponse con documentación en Markdown.
        """
        system = (
            "You are a technical writer specializing in API documentation. "
            "Generate clear, comprehensive documentation in Markdown format."
        )
        prompt = f"""Generate documentation for the MCP server "{server_name}"
based on this OpenAPI spec:

```yaml
{spec_content[:6000]}
```

Include:
1. Overview and purpose
2. Setup instructions
3. Available tools with examples
4. Available resources
5. Authentication setup
6. Error handling
7. Usage examples with different LLM clients
"""
        return self._execute_task(
            AITaskType.DOCUMENTATION,
            system,
            prompt,
            temperature=0.5,
        )

    def validate_mcp_output(
        self,
        generated_code: str,
        spec_summary: str,
    ) -> AIResponse:
        """
        Valida código MCP generado contra la spec original.

        Returns:
            AIResponse con resultado de validación JSON.
        """
        system = (
            "You are a code reviewer specializing in Python and MCP servers. "
            "Validate generated code for correctness and best practices."
        )
        prompt = f"""Validate this generated MCP server code against the original API spec.

API Summary: {spec_summary}

Generated Code (excerpt):
```python
{generated_code[:6000]}
```

Provide a JSON response with:
1. "valid": true/false
2. "score": quality score 0-100
3. "issues": list of issues found
4. "missing_endpoints": any spec endpoints not covered
5. "security_concerns": security issues found
6. "suggestions": improvement suggestions
"""
        return self._execute_task(
            AITaskType.VALIDATION, system, prompt, format_json=True
        )

    def security_audit(self, spec_content: str) -> AIResponse:
        """
        Realiza auditoría de seguridad de una spec OpenAPI.

        Returns:
            AIResponse con hallazgos de seguridad JSON.
        """
        system = (
            "You are a security expert specializing in API security, "
            "OWASP guidelines, and OAuth2/OpenID Connect."
        )
        prompt = f"""Perform a security audit on this OpenAPI specification:

```yaml
{spec_content[:8000]}
```

Provide a JSON response with:
1. "risk_level": "low", "medium", "high", or "critical"
2. "authentication_assessment": analysis of auth schemes
3. "vulnerabilities": list of potential vulnerabilities
4. "owasp_compliance": OWASP API Security Top 10 check
5. "recommendations": prioritized security recommendations
6. "data_exposure_risks": sensitive data exposure analysis
"""
        return self._execute_task(
            AITaskType.SECURITY_AUDIT, system, prompt, format_json=True
        )

    def optimize_spec(self, spec_content: str) -> AIResponse:
        """
        Sugiere optimizaciones para una spec OpenAPI.

        Returns:
            AIResponse con sugerencias de optimización.
        """
        system = (
            "You are an API performance expert. Analyze the spec and suggest "
            "optimizations for better performance and developer experience."
        )
        prompt = f"""Analyze this OpenAPI spec and suggest optimizations:

```yaml
{spec_content[:8000]}
```

Provide a JSON response with:
1. "pagination": endpoints that should have pagination
2. "caching": endpoints suitable for caching
3. "batching": endpoints that could be batched
4. "compression": recommendations for response compression
5. "query_optimization": query parameter improvements
6. "schema_improvements": schema optimization suggestions
"""
        return self._execute_task(
            AITaskType.OPTIMIZATION, system, prompt, format_json=True
        )

    # ==================== Internals ====================

    def _execute_task(
        self,
        task_type: AITaskType,
        system: str,
        prompt: str,
        temperature: float = 0.7,
        format_json: bool = False,
    ) -> AIResponse:
        """Ejecuta una tarea IA con manejo de errores."""
        model = self._model_for_task(task_type)
        start = time.time()

        try:
            result = self._generate(
                model=model,
                prompt=prompt,
                system=system,
                temperature=temperature,
                format_json=format_json,
            )

            duration_ms = int((time.time() - start) * 1000)
            content = result.get("response", "")

            # Intentar parsear JSON si se esperaba
            if format_json:
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    pass  # Mantener como string

            return AIResponse(
                task_type=task_type,
                model=model,
                content=content,
                tokens_used=result.get("eval_count", 0),
                duration_ms=duration_ms,
                metadata={
                    "total_duration": result.get("total_duration", 0),
                    "load_duration": result.get("load_duration", 0),
                },
            )

        except httpx.ConnectError:
            return AIResponse(
                task_type=task_type,
                model=model,
                content="",
                duration_ms=int((time.time() - start) * 1000),
                success=False,
                error="Cannot connect to Ollama. Ensure it is running.",
            )
        except httpx.HTTPStatusError as e:
            return AIResponse(
                task_type=task_type,
                model=model,
                content="",
                duration_ms=int((time.time() - start) * 1000),
                success=False,
                error=f"Ollama API error: {e.response.status_code}",
            )
        except Exception as e:
            logger.exception("AI task %s failed", task_type.value)
            return AIResponse(
                task_type=task_type,
                model=model,
                content="",
                duration_ms=int((time.time() - start) * 1000),
                success=False,
                error=str(e),
            )

    def close(self) -> None:
        """Cierra el cliente HTTP."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Singleton
_client: OllamaClient | None = None


def get_ai_client() -> OllamaClient:
    """Obtiene la instancia global del cliente IA."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


def reset_ai_client() -> None:
    """Resetea el cliente IA (útil para testing)."""
    global _client
    if _client is not None:
        _client.close()
    _client = None
