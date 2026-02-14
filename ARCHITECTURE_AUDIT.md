# Auditoría Técnica: OpenAPI to MCP Generator

**Fecha**: 2026-02-08
**Versión Analizada**: master (post-Phase 5)
**Auditor**: Arquitecto de Software Senior

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Inventario de Features Faltantes](#2-inventario-de-features-faltantes)
3. [Evaluación del README.md](#3-evaluación-del-readmemd)
4. [Propuestas de Features de IA](#4-propuestas-de-features-de-ia)
5. [Ecosistema de Testing con Ollama](#5-ecosistema-de-testing-con-ollama)
6. [Integración con MinIO](#6-integración-con-minio)
7. [Generación Dinámica de MCPs Personalizados](#7-generación-dinámica-de-mcps-personalizados)
8. [Arquitectura Multi-Agente](#8-arquitectura-multi-agente)
9. [Sistema de Autenticación OAuth2 a Nivel MCP](#9-sistema-de-autenticación-oauth2-a-nivel-mcp)
10. [Dependencias y Configuración Faltante](#10-dependencias-y-configuración-faltante)
11. [Plan de Implementación Priorizado](#11-plan-de-implementación-priorizado)

---

## 1. Resumen Ejecutivo

### Estado Actual
El repositorio es una plataforma **enterprise-grade** funcional con ~15,757 líneas de código Python que cubre:
- ✅ Parsing OpenAPI 3.0/3.1
- ✅ Transformación a MCP Tools/Resources
- ✅ Generación de código (FastMCP, MCP, TypeScript)
- ✅ GUI web con features empresariales (audit, encryption, alerts, metrics)
- ✅ Multi-database support (SQLite, PostgreSQL, MongoDB)

### Gaps Críticos Identificados

| Categoría | Gap | Impacto | Prioridad |
|-----------|-----|---------|-----------|
| **Persistencia** | No hay storage de artefactos (solo memoria/filesystem) | Alto | P0 |
| **IA** | Sin integración con LLMs para asistencia | Alto | P0 |
| **Runtime** | MCPs se generan pero no se ejecutan/testean | Alto | P1 |
| **OAuth2** | Sin inyección automática de tokens en MCPs | Medio | P1 |
| **Multi-tenant** | Sin aislamiento real de workspaces | Medio | P2 |
| **Versionado** | Sin Git integration para MCPs generados | Medio | P2 |

---

## 2. Inventario de Features Faltantes

### 2.1 Features Incompletos (Marcados pero no implementados)

```
Fase 4:
- [ ] Plugins de exportación (templates solo Jinja2)

Fase 5:
- [ ] SSO/SAML integration
- [ ] Soporte multi-tenant (modelos existen, lógica de aislamiento falta)
- [ ] Balanceo de carga
- [ ] Cache distribuido (Redis)
```

### 2.2 Módulos Ausentes Críticos

#### 2.2.1 Runtime de MCPs
**Ubicación esperada**: `src/openapi_to_mcp/runtime/`

```
runtime/
├── __init__.py
├── mcp_runner.py        # Ejecutar MCPs generados
├── mcp_tester.py        # Testing automatizado de tools
├── health_checker.py    # Health checks de MCPs desplegados
└── process_manager.py   # Gestión de procesos MCP
```

**Estado**: No existe. Los MCPs se generan pero el usuario debe ejecutarlos manualmente.

#### 2.2.2 Storage de Artefactos
**Ubicación esperada**: `src/openapi_to_mcp/storage/`

```
storage/
├── __init__.py
├── artifact_store.py    # Abstracción de storage
├── adapters/
│   ├── local_adapter.py
│   ├── minio_adapter.py
│   └── s3_adapter.py
└── versioning.py        # Versionado de artefactos
```

**Estado**: No existe. Los ZIPs se generan en `/tmp` y se borran.

#### 2.2.3 Integración IA
**Ubicación esperada**: `src/openapi_to_mcp/ai/`

```
ai/
├── __init__.py
├── llm_client.py        # Cliente abstracción LLM
├── adapters/
│   ├── ollama_adapter.py
│   ├── openai_adapter.py
│   └── anthropic_adapter.py
├── assistants/
│   ├── spec_analyzer.py      # Análisis de specs
│   ├── naming_suggester.py   # Sugerencias de nombres
│   ├── doc_generator.py      # Generación de docs
│   └── code_optimizer.py     # Optimización de código
└── embeddings/
    ├── spec_embedder.py
    └── similarity_search.py
```

**Estado**: No existe. Hay un item en backlog "AI-assisted mapping" sin implementar.

#### 2.2.4 Sistema de Tokens OAuth2
**Ubicación esperada**: `src/openapi_to_mcp/auth/oauth2/`

```
auth/oauth2/
├── __init__.py
├── token_manager.py     # Gestión de tokens
├── token_injector.py    # Inyección en requests
├── refresh_handler.py   # Auto-refresh
├── providers/
│   ├── generic_oauth2.py
│   ├── auth0_provider.py
│   ├── okta_provider.py
│   └── azure_ad_provider.py
└── storage/
    ├── memory_store.py
    ├── redis_store.py
    └── db_store.py
```

**Estado**: `auth/__init__.py` existe pero está vacío. No hay OAuth2 implementation.

### 2.3 Configuración Ausente

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `config/ollama.yaml` | Configuración Ollama | No existe |
| `config/minio.yaml` | Configuración MinIO | No existe |
| `config/oauth2.yaml` | Proveedores OAuth2 | No existe |
| `alembic.ini` | Migraciones DB | No existe (aunque se referencia en db_config.py) |
| `.env.example` | Variables de entorno | No existe |

### 2.4 Tests Faltantes

```
tests/
├── test_parser.py          # ✅ Existe (248 líneas)
├── test_transformers.py    # ✅ Existe (395 líneas)
├── test_generators.py      # ❌ No existe
├── test_validators.py      # ❌ No existe
├── test_gui/               # ❌ No existe
│   ├── test_web_app.py
│   ├── test_auth.py
│   ├── test_audit.py
│   └── test_encryption.py
├── test_integration/       # ❌ No existe
│   ├── test_e2e_generation.py
│   └── test_mcp_execution.py
└── fixtures/               # ❌ No existe
    ├── sample_specs/
    └── expected_outputs/
```

**Cobertura actual estimada**: ~15-20% (solo parser y transformers)

---

## 3. Evaluación del README.md

### 3.1 Análisis de Completitud

| Sección | Estado | Observaciones |
|---------|--------|---------------|
| Instalación | ✅ Completa | Bien documentada |
| Inicio Rápido | ✅ Completa | Ejemplos claros |
| Modos de Uso | ✅ Completa | 5 modos documentados |
| Docker | ✅ Completa | docker-compose incluido |
| Arquitectura | ⚠️ Parcial | Falta diagrama de componentes enterprise |
| API REST | ❌ Falta | No documenta los ~50 endpoints de la API |
| Configuración DB | ❌ Falta | No documenta DATABASE_TYPE, DB_* variables |
| Features Enterprise | ❌ Falta | Audit, Encryption, Alerts no documentados |
| Troubleshooting | ❌ Falta | No hay guía de resolución de problemas |

### 3.2 Secciones Recomendadas a Agregar

```markdown
## API REST Reference (Nueva sección)

### Endpoints de Autenticación
- `POST /api/login` - Iniciar sesión
- `POST /api/register` - Registrar usuario
- `POST /api/logout` - Cerrar sesión

### Endpoints de Specs
- `POST /api/upload` - Subir especificación
- `POST /api/load-url` - Cargar desde URL
- `GET /api/specs` - Listar especificaciones
- `GET /api/specs/:id/versions` - Versiones de spec

### Endpoints de Generación
- `POST /api/generate` - Generar MCP
- `GET /api/download/:id` - Descargar ZIP

### Endpoints Enterprise
- `GET /api/audit/logs` - Logs de auditoría
- `GET /api/metrics/dashboard` - Métricas
- `GET /api/alerts` - Alertas activas
- `GET /api/reports/scheduled` - Reportes programados
- `GET /api/health` - Health check

## Configuración de Base de Datos (Nueva sección)

### Variables de Entorno
| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_TYPE` | sqlite, postgresql, mongodb | sqlite |
| `DATABASE_URL` | URL completa de conexión | - |
| `DB_HOST` | Host de la base de datos | localhost |
| `DB_PORT` | Puerto | 5432/27017 |
| `DB_NAME` | Nombre de la base de datos | openapi_mcp |
| `DB_USER` | Usuario | postgres |
| `DB_PASSWORD` | Contraseña | - |

### Ejemplo PostgreSQL
```bash
export DATABASE_TYPE=postgresql
export DATABASE_URL=postgresql://user:pass@localhost:5432/openapi_mcp
```

## Features Enterprise (Nueva sección)

### Auditoría
45 tipos de eventos auditados con 4 niveles de severidad.

### Encriptación
AES-256 con Fernet, derivación de clave PBKDF2 (480K iteraciones).

### Retención de Datos
Políticas configurables por tipo de dato con cleanup automático.

### Alertas
10 tipos de alertas con thresholds configurables y notificaciones.

### Reportes
8 tipos de reportes en 3 formatos (JSON, CSV, HTML) con scheduling.
```

---

## 4. Propuestas de Features de IA

### 4.1 Generación Automática de Especificaciones MCP

**Objetivo**: Dado un endpoint real, generar automáticamente su especificación OpenAPI.

```python
# src/openapi_to_mcp/ai/assistants/spec_generator.py

class SpecGenerator:
    """Genera OpenAPI specs desde endpoints reales usando LLM."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate_from_endpoint(
        self,
        url: str,
        method: str,
        sample_request: dict | None = None,
        sample_response: dict | None = None,
    ) -> dict:
        """
        Genera spec OpenAPI analizando request/response reales.

        Args:
            url: URL del endpoint (e.g., "https://api.example.com/users")
            method: Método HTTP
            sample_request: Ejemplo de request body
            sample_response: Ejemplo de response

        Returns:
            OpenAPI path object generado
        """
        prompt = f"""Analiza este endpoint REST y genera su especificación OpenAPI 3.1:

URL: {method} {url}
Request Body: {json.dumps(sample_request, indent=2) if sample_request else "None"}
Response: {json.dumps(sample_response, indent=2) if sample_response else "None"}

Genera:
1. operationId descriptivo
2. summary y description
3. parameters (path, query)
4. requestBody schema
5. responses con schemas

Responde SOLO con el YAML del path object."""

        response = await self.llm.complete(prompt)
        return yaml.safe_load(response)
```

### 4.2 Análisis Semántico de Requests

**Objetivo**: Analizar requests entrantes al MCP para sugerir el tool más apropiado.

```python
# src/openapi_to_mcp/ai/assistants/request_analyzer.py

class RequestAnalyzer:
    """Analiza requests en lenguaje natural para mapear a tools."""

    async def analyze_intent(
        self,
        user_request: str,
        available_tools: list[MCPTool],
    ) -> list[ToolSuggestion]:
        """
        Dado un request en lenguaje natural, sugiere tools relevantes.

        Returns:
            Lista ordenada por relevancia de ToolSuggestion
        """
        tools_summary = "\n".join([
            f"- {t.name}: {t.description}"
            for t in available_tools
        ])

        prompt = f"""Usuario solicita: "{user_request}"

Tools disponibles:
{tools_summary}

Identifica los tools más relevantes y en qué orden ejecutarlos.
Responde en JSON: [{{"tool": "name", "confidence": 0.95, "reason": "..."}}]"""

        response = await self.llm.complete(prompt)
        return [ToolSuggestion(**s) for s in json.loads(response)]
```

### 4.3 Optimización de Código Generado

**Objetivo**: Mejorar el código Python/TypeScript generado.

```python
# src/openapi_to_mcp/ai/assistants/code_optimizer.py

class CodeOptimizer:
    """Optimiza código generado usando LLM."""

    async def optimize(
        self,
        code: str,
        language: str = "python",
        focus: list[str] = ["performance", "readability"],
    ) -> OptimizationResult:
        """
        Analiza y optimiza código generado.

        Args:
            code: Código a optimizar
            language: python o typescript
            focus: Áreas de optimización

        Returns:
            OptimizationResult con código mejorado y explicación
        """
        prompt = f"""Optimiza este código {language} enfocándote en: {', '.join(focus)}

```{language}
{code}
```

Proporciona:
1. Código optimizado
2. Lista de cambios realizados
3. Métricas de mejora estimadas

Responde en JSON."""

        response = await self.llm.complete(prompt)
        return OptimizationResult.from_json(response)
```

### 4.4 Validación Inteligente de Features

**Objetivo**: Validar que los features solicitados por usuarios son implementables.

```python
# src/openapi_to_mcp/ai/assistants/feature_validator.py

class FeatureValidator:
    """Valida viabilidad de features personalizados."""

    async def validate_feature(
        self,
        feature_request: str,
        base_spec: OpenAPISpec,
        existing_tools: list[MCPTool],
    ) -> FeatureValidation:
        """
        Valida si un feature es implementable dado el spec base.

        Returns:
            FeatureValidation con viabilidad, requisitos, y plan
        """
        spec_summary = self._summarize_spec(base_spec)

        prompt = f"""Evalúa la viabilidad de este feature para un servidor MCP:

Feature solicitado: "{feature_request}"

OpenAPI Spec base:
{spec_summary}

Tools existentes: {[t.name for t in existing_tools]}

Evalúa:
1. ¿Es implementable con los endpoints disponibles?
2. ¿Qué endpoints adicionales se necesitan?
3. ¿Requiere lógica custom?
4. Complejidad estimada (simple/media/alta)
5. Plan de implementación paso a paso

Responde en JSON estructurado."""

        response = await self.llm.complete(prompt)
        return FeatureValidation.from_json(response)
```

### 4.5 Documentación Automática

**Objetivo**: Generar documentación rica para MCPs generados.

```python
# src/openapi_to_mcp/ai/assistants/doc_generator.py

class DocGenerator:
    """Genera documentación automática para MCPs."""

    async def generate_readme(
        self,
        mcp_tools: list[MCPTool],
        mcp_resources: list[MCPResource],
        config: MCPServerConfig,
    ) -> str:
        """Genera README.md completo para el MCP generado."""

    async def generate_examples(
        self,
        tool: MCPTool,
        num_examples: int = 3,
    ) -> list[Example]:
        """Genera ejemplos de uso para un tool."""

    async def generate_faq(
        self,
        spec: OpenAPISpec,
        tools: list[MCPTool],
    ) -> str:
        """Genera FAQ basado en la API."""
```

---

## 5. Ecosistema de Testing con Ollama

### 5.1 Configuración en Settings

**Archivo**: `config/ollama.yaml`

```yaml
# Configuración de Ollama para el ecosistema MCP
ollama:
  # Conexión
  host: ${OLLAMA_HOST:localhost}
  port: ${OLLAMA_PORT:11434}
  timeout: 120

  # Modelos por caso de uso
  models:
    # Modelo principal para análisis de specs
    spec_analysis:
      name: "llama3.2:3b"
      context_length: 8192
      temperature: 0.3

    # Modelo para generación de código
    code_generation:
      name: "codellama:7b"
      context_length: 16384
      temperature: 0.2

    # Modelo para documentación
    documentation:
      name: "llama3.2:3b"
      context_length: 4096
      temperature: 0.7

    # Modelo ligero para validación rápida
    validation:
      name: "llama3.2:1b"
      context_length: 2048
      temperature: 0.1

  # Configuración de fallback
  fallback:
    enabled: true
    model: "llama3.2:1b"

  # Rate limiting
  rate_limit:
    requests_per_minute: 30
    concurrent_requests: 3

  # Health check
  health_check:
    enabled: true
    interval_seconds: 60
    endpoint: "/api/tags"
```

**Archivo**: `src/openapi_to_mcp/config/settings.py`

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class OllamaSettings(BaseSettings):
    """Configuración de Ollama."""

    host: str = Field(default="localhost", env="OLLAMA_HOST")
    port: int = Field(default=11434, env="OLLAMA_PORT")
    timeout: int = Field(default=120, env="OLLAMA_TIMEOUT")

    # Modelos
    model_spec_analysis: str = Field(default="llama3.2:3b")
    model_code_generation: str = Field(default="codellama:7b")
    model_documentation: str = Field(default="llama3.2:3b")
    model_validation: str = Field(default="llama3.2:1b")

    # Rate limiting
    rate_limit_rpm: int = Field(default=30)
    concurrent_requests: int = Field(default=3)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    class Config:
        env_prefix = "OLLAMA_"


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Base de datos
    database_type: str = Field(default="sqlite")
    database_url: str | None = None

    # Ollama
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")
    minio_secure: bool = Field(default=False)

    # OAuth2
    oauth2_issuer: str | None = None
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

### 5.2 Cliente Ollama

**Archivo**: `src/openapi_to_mcp/ai/llm_client.py`

```python
import httpx
import asyncio
from typing import AsyncIterator
from .adapters.base import LLMAdapter

class OllamaAdapter(LLMAdapter):
    """Adaptador para Ollama local."""

    def __init__(self, settings: OllamaSettings):
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout,
        )
        self._semaphore = asyncio.Semaphore(settings.concurrent_requests)

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> str:
        """Genera completion."""
        async with self._semaphore:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": model or self.settings.model_spec_analysis,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs,
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def stream(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Genera completion con streaming."""
        async with self._semaphore:
            async with self.client.stream(
                "POST",
                "/api/generate",
                json={
                    "model": model or self.settings.model_spec_analysis,
                    "prompt": prompt,
                    "stream": True,
                    **kwargs,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]

    async def health_check(self) -> bool:
        """Verifica conectividad con Ollama."""
        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Lista modelos disponibles."""
        response = await self.client.get("/api/tags")
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
```

### 5.3 Endpoints de Prueba

**Archivo**: `src/openapi_to_mcp/gui/web_app.py` (añadir)

```python
# ========== Ollama/AI Routes ==========

@app.route("/api/ai/health")
def ai_health_check():
    """Health check de servicios de IA."""
    from .ai.llm_client import get_llm_client

    client = get_llm_client()
    ollama_healthy = await client.health_check()
    models = await client.list_models() if ollama_healthy else []

    return jsonify({
        "ollama": {
            "healthy": ollama_healthy,
            "endpoint": client.settings.base_url,
            "models_available": models,
        },
    })

@app.route("/api/ai/analyze-spec", methods=["POST"])
async def ai_analyze_spec():
    """Analiza spec con IA."""
    from flask_login import current_user
    from .ai.assistants.spec_analyzer import SpecAnalyzer

    if not current_user.is_authenticated:
        return jsonify({"error": "Auth required"}), 401

    data = request.json
    spec_content = data.get("spec")

    analyzer = SpecAnalyzer()
    analysis = await analyzer.analyze(spec_content)

    return jsonify({
        "summary": analysis.summary,
        "suggestions": analysis.suggestions,
        "quality_score": analysis.quality_score,
        "naming_improvements": analysis.naming_improvements,
    })

@app.route("/api/ai/suggest-tools", methods=["POST"])
async def ai_suggest_tools():
    """Sugiere tools basado en descripción."""
    data = request.json
    description = data.get("description")
    spec = data.get("spec")

    suggester = ToolSuggester()
    suggestions = await suggester.suggest(description, spec)

    return jsonify({"suggestions": [s.to_dict() for s in suggestions]})
```

### 5.4 Scripts de Validación

**Archivo**: `scripts/validate_ollama.py`

```python
#!/usr/bin/env python3
"""Script para validar la instalación de Ollama."""

import asyncio
import sys
from rich.console import Console
from rich.table import Table

console = Console()

async def main():
    from openapi_to_mcp.ai.llm_client import get_llm_client
    from openapi_to_mcp.config.settings import get_settings

    settings = get_settings()
    client = get_llm_client()

    console.print("\n[bold]Validando Ollama...[/bold]\n")

    # 1. Health check
    console.print("1. Conectando a Ollama...", end=" ")
    healthy = await client.health_check()
    if healthy:
        console.print("[green]✓ OK[/green]")
    else:
        console.print("[red]✗ FAILED[/red]")
        console.print(f"   No se puede conectar a {settings.ollama.base_url}")
        sys.exit(1)

    # 2. Listar modelos
    console.print("2. Listando modelos...", end=" ")
    models = await client.list_models()
    console.print(f"[green]✓ {len(models)} modelos[/green]")

    # 3. Verificar modelos requeridos
    required = [
        settings.ollama.model_spec_analysis,
        settings.ollama.model_code_generation,
    ]

    console.print("3. Verificando modelos requeridos:")
    missing = []
    for model in required:
        if model in models:
            console.print(f"   - {model}: [green]✓[/green]")
        else:
            console.print(f"   - {model}: [red]✗ No instalado[/red]")
            missing.append(model)

    if missing:
        console.print("\n[yellow]Instalar modelos faltantes:[/yellow]")
        for m in missing:
            console.print(f"   ollama pull {m}")

    # 4. Test de generación
    console.print("\n4. Test de generación...", end=" ")
    try:
        response = await client.complete(
            "Responde solo con 'OK'",
            model=settings.ollama.model_validation,
        )
        if "OK" in response:
            console.print("[green]✓ OK[/green]")
        else:
            console.print(f"[yellow]⚠ Respuesta: {response[:50]}[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")

    # Resumen
    console.print("\n[bold green]Ollama configurado correctamente![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Integración con MinIO

### 6.1 Estructura de Buckets

```
minio/
├── openapi-specs/              # Especificaciones OpenAPI originales
│   ├── {workspace_id}/
│   │   ├── {spec_id}/
│   │   │   ├── v1.yaml
│   │   │   ├── v2.yaml
│   │   │   └── metadata.json
│   │   └── ...
│   └── public/                 # Specs públicos de ejemplo
│
├── mcp-artifacts/              # MCPs generados
│   ├── {workspace_id}/
│   │   ├── {generation_id}/
│   │   │   ├── mcp_server.zip
│   │   │   ├── manifest.json
│   │   │   ├── checksum.sha256
│   │   │   └── logs/
│   │   │       └── generation.log
│   │   └── ...
│   └── templates/              # Templates personalizados
│
├── reports/                    # Reportes generados
│   ├── {workspace_id}/
│   │   ├── {report_id}.json
│   │   ├── {report_id}.csv
│   │   └── {report_id}.html
│   └── scheduled/
│
└── backups/                    # Backups automáticos
    ├── db/
    │   └── {date}/
    └── specs/
        └── {date}/
```

### 6.2 Políticas de Retención

```python
# src/openapi_to_mcp/storage/policies.py

RETENTION_POLICIES = {
    "openapi-specs": {
        # Specs se mantienen indefinidamente por defecto
        "default_retention_days": None,  # Indefinido
        "versioning": True,
        "max_versions": 100,
    },

    "mcp-artifacts": {
        # MCPs generados se retienen 90 días por defecto
        "default_retention_days": 90,
        "versioning": True,
        "max_versions": 20,
        # Excepto los marcados como "production"
        "exceptions": {
            "tag:production": None,  # Indefinido
            "tag:release": 365,      # 1 año
        },
    },

    "reports": {
        # Reportes se retienen según su tipo
        "default_retention_days": 30,
        "versioning": False,
        "exceptions": {
            "type:compliance": 2555,  # 7 años
            "type:security_audit": 365,
        },
    },

    "backups": {
        "default_retention_days": 30,
        "versioning": False,
        "lifecycle_rules": [
            {"prefix": "daily/", "expiration_days": 7},
            {"prefix": "weekly/", "expiration_days": 30},
            {"prefix": "monthly/", "expiration_days": 365},
        ],
    },
}
```

### 6.3 Estrategia de Versionado

```python
# src/openapi_to_mcp/storage/versioning.py

class ArtifactVersion:
    """Representa una versión de artefacto en MinIO."""

    def __init__(
        self,
        version_id: str,
        artifact_type: str,  # "spec", "mcp", "report"
        semantic_version: str,  # "1.0.0", "1.1.0"
        created_at: datetime,
        created_by: int,  # user_id
        metadata: dict,
    ):
        self.version_id = version_id
        self.artifact_type = artifact_type
        self.semantic_version = semantic_version
        self.created_at = created_at
        self.created_by = created_by
        self.metadata = metadata


class VersioningStrategy:
    """Estrategia de versionado para artefactos."""

    @staticmethod
    def calculate_next_version(
        current: str,
        change_type: str,  # "major", "minor", "patch"
    ) -> str:
        """Calcula siguiente versión semántica."""
        major, minor, patch = map(int, current.split("."))

        if change_type == "major":
            return f"{major + 1}.0.0"
        elif change_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"

    @staticmethod
    def detect_change_type(
        old_spec: dict,
        new_spec: dict,
    ) -> str:
        """Detecta tipo de cambio entre specs."""
        # Cambios breaking (nuevo major):
        # - Endpoints eliminados
        # - Parámetros requeridos agregados
        # - Cambios de tipo incompatibles

        old_paths = set(old_spec.get("paths", {}).keys())
        new_paths = set(new_spec.get("paths", {}).keys())

        if old_paths - new_paths:  # Endpoints eliminados
            return "major"

        if new_paths - old_paths:  # Endpoints agregados
            return "minor"

        return "patch"  # Solo cambios menores
```

### 6.4 Adaptador MinIO

```python
# src/openapi_to_mcp/storage/adapters/minio_adapter.py

from minio import Minio
from minio.error import S3Error
import io

class MinIOAdapter:
    """Adaptador para almacenamiento en MinIO."""

    def __init__(self, settings: Settings):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        """Crea buckets si no existen."""
        buckets = ["openapi-specs", "mcp-artifacts", "reports", "backups"]
        for bucket in buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                self._apply_lifecycle_policy(bucket)

    async def store_spec(
        self,
        workspace_id: int,
        spec_id: str,
        content: str,
        version: str,
        metadata: dict,
    ) -> str:
        """Almacena una especificación OpenAPI."""
        object_name = f"{workspace_id}/{spec_id}/{version}.yaml"

        data = content.encode("utf-8")
        self.client.put_object(
            "openapi-specs",
            object_name,
            io.BytesIO(data),
            len(data),
            content_type="application/yaml",
            metadata=metadata,
        )

        return object_name

    async def store_mcp(
        self,
        workspace_id: int,
        generation_id: str,
        zip_data: bytes,
        manifest: dict,
    ) -> str:
        """Almacena un MCP generado."""
        base_path = f"{workspace_id}/{generation_id}"

        # Almacenar ZIP
        self.client.put_object(
            "mcp-artifacts",
            f"{base_path}/mcp_server.zip",
            io.BytesIO(zip_data),
            len(zip_data),
            content_type="application/zip",
        )

        # Almacenar manifest
        manifest_data = json.dumps(manifest).encode("utf-8")
        self.client.put_object(
            "mcp-artifacts",
            f"{base_path}/manifest.json",
            io.BytesIO(manifest_data),
            len(manifest_data),
            content_type="application/json",
        )

        return base_path

    async def get_spec(
        self,
        workspace_id: int,
        spec_id: str,
        version: str = "latest",
    ) -> str:
        """Obtiene una especificación."""
        if version == "latest":
            # Listar versiones y obtener la más reciente
            objects = self.client.list_objects(
                "openapi-specs",
                prefix=f"{workspace_id}/{spec_id}/",
            )
            versions = sorted([o.object_name for o in objects], reverse=True)
            if not versions:
                raise FileNotFoundError(f"Spec {spec_id} not found")
            object_name = versions[0]
        else:
            object_name = f"{workspace_id}/{spec_id}/{version}.yaml"

        response = self.client.get_object("openapi-specs", object_name)
        return response.read().decode("utf-8")

    async def get_mcp_download_url(
        self,
        workspace_id: int,
        generation_id: str,
        expires_hours: int = 24,
    ) -> str:
        """Genera URL pre-firmada para descarga."""
        return self.client.presigned_get_object(
            "mcp-artifacts",
            f"{workspace_id}/{generation_id}/mcp_server.zip",
            expires=timedelta(hours=expires_hours),
        )
```

### 6.5 Endpoints de Acceso

```python
# Añadir a web_app.py

# ========== Storage Routes ==========

@app.route("/api/storage/specs/<spec_id>/versions")
def list_spec_versions(spec_id):
    """Lista versiones de una spec."""
    from .storage import get_storage

    storage = get_storage()
    versions = storage.list_versions("openapi-specs", spec_id)

    return jsonify({"versions": versions})

@app.route("/api/storage/specs/<spec_id>/download/<version>")
def download_spec(spec_id, version):
    """Descarga una versión de spec."""
    from .storage import get_storage

    storage = get_storage()
    url = storage.get_presigned_url("openapi-specs", spec_id, version)

    return redirect(url)

@app.route("/api/storage/mcps/<generation_id>/download")
def download_mcp(generation_id):
    """Descarga un MCP generado."""
    from flask_login import current_user
    from .storage import get_storage

    storage = get_storage()
    ws_id = get_user_workspace(current_user.id)

    url = storage.get_mcp_download_url(ws_id, generation_id)
    return redirect(url)

@app.route("/api/storage/health")
def storage_health():
    """Health check de MinIO."""
    from .storage import get_storage

    storage = get_storage()
    healthy = storage.health_check()

    return jsonify({
        "healthy": healthy,
        "endpoint": storage.endpoint,
        "buckets": storage.list_buckets() if healthy else [],
    })
```

---

## 7. Generación Dinámica de MCPs Personalizados

### 7.1 Formato de Input de Features

```yaml
# feature_request.yaml

# Información básica
name: "customer_support_mcp"
description: "MCP personalizado para soporte al cliente"
base_spec: "petstore-api"  # ID o path del spec base

# Features personalizados solicitados
features:
  - id: "feature_001"
    type: "aggregation"
    description: "Obtener cliente con todos sus pedidos"
    source_endpoints:
      - "GET /customers/{id}"
      - "GET /customers/{id}/orders"
    output:
      name: "get_customer_with_orders"
      description: "Obtiene cliente con historial completo de pedidos"

  - id: "feature_002"
    type: "transformation"
    description: "Crear pedido con validación de inventario"
    source_endpoint: "POST /orders"
    transformations:
      - step: "validate_inventory"
        call: "GET /products/{product_id}/stock"
        condition: "stock >= quantity"
      - step: "create_order"
        call: "POST /orders"

  - id: "feature_003"
    type: "filtering"
    description: "Listar solo productos disponibles"
    source_endpoint: "GET /products"
    filters:
      - field: "stock"
        operator: "gt"
        value: 0
      - field: "status"
        operator: "eq"
        value: "active"

  - id: "feature_004"
    type: "custom_logic"
    description: "Calcular tiempo estimado de entrega"
    inputs:
      - name: "shipping_address"
        type: "object"
        required: true
      - name: "products"
        type: "array"
        required: true
    logic: |
      # Python code que se inyectará
      warehouse = await self.get_nearest_warehouse(shipping_address)
      total_weight = sum(p.weight * p.quantity for p in products)
      return calculate_delivery_time(warehouse, shipping_address, total_weight)

# Configuración de generación
generation_config:
  framework: "fastmcp"
  include_tests: true
  include_docs: true
  auth_passthrough: true  # Propagar auth del usuario
```

### 7.2 Proceso de Templating

```python
# src/openapi_to_mcp/customization/feature_processor.py

from dataclasses import dataclass
from enum import Enum

class FeatureType(Enum):
    AGGREGATION = "aggregation"
    TRANSFORMATION = "transformation"
    FILTERING = "filtering"
    CUSTOM_LOGIC = "custom_logic"

@dataclass
class ProcessedFeature:
    """Feature procesado listo para generación."""
    id: str
    type: FeatureType
    tool_code: str
    tool_schema: dict
    dependencies: list[str]
    tests: list[str]

class FeatureProcessor:
    """Procesa features personalizados para generación."""

    def __init__(self, base_spec: OpenAPISpec, llm_client: LLMClient):
        self.base_spec = base_spec
        self.llm = llm_client
        self.template_env = self._setup_jinja()

    async def process_feature(
        self,
        feature: dict,
    ) -> ProcessedFeature:
        """Procesa un feature individual."""

        feature_type = FeatureType(feature["type"])

        if feature_type == FeatureType.AGGREGATION:
            return await self._process_aggregation(feature)
        elif feature_type == FeatureType.TRANSFORMATION:
            return await self._process_transformation(feature)
        elif feature_type == FeatureType.FILTERING:
            return await self._process_filtering(feature)
        elif feature_type == FeatureType.CUSTOM_LOGIC:
            return await self._process_custom_logic(feature)

    async def _process_aggregation(self, feature: dict) -> ProcessedFeature:
        """Genera código para agregación de endpoints."""

        endpoints = feature["source_endpoints"]
        output = feature["output"]

        # Obtener schemas de los endpoints
        schemas = []
        for ep in endpoints:
            method, path = ep.split(" ", 1)
            operation = self.base_spec.get_operation(path, method)
            schemas.append(operation.response_schema)

        # Generar código con template
        code = self.template_env.get_template("aggregation.py.j2").render(
            tool_name=output["name"],
            description=output["description"],
            endpoints=endpoints,
            schemas=schemas,
        )

        # Generar schema del tool
        schema = await self._generate_tool_schema(output, schemas)

        # Generar tests
        tests = await self._generate_tests(output["name"], schema)

        return ProcessedFeature(
            id=feature["id"],
            type=FeatureType.AGGREGATION,
            tool_code=code,
            tool_schema=schema,
            dependencies=endpoints,
            tests=tests,
        )

    async def _process_custom_logic(self, feature: dict) -> ProcessedFeature:
        """Procesa feature con lógica custom."""

        # Validar código con LLM
        validation = await self._validate_custom_code(feature["logic"])
        if not validation.is_safe:
            raise ValueError(f"Código inseguro: {validation.issues}")

        # Optimizar código
        optimized = await self.llm.optimize_code(feature["logic"])

        # Generar wrapper
        code = self.template_env.get_template("custom_logic.py.j2").render(
            tool_name=feature["id"],
            description=feature["description"],
            inputs=feature["inputs"],
            logic=optimized,
        )

        return ProcessedFeature(
            id=feature["id"],
            type=FeatureType.CUSTOM_LOGIC,
            tool_code=code,
            tool_schema=self._inputs_to_schema(feature["inputs"]),
            dependencies=[],
            tests=await self._generate_tests(feature["id"]),
        )
```

### 7.3 Validación de Especificaciones

```python
# src/openapi_to_mcp/customization/validator.py

class FeatureValidator:
    """Valida features personalizados."""

    def __init__(self, base_spec: OpenAPISpec):
        self.base_spec = base_spec

    def validate(self, feature_request: dict) -> ValidationResult:
        """Valida un request de features completo."""

        errors = []
        warnings = []

        # 1. Validar que el spec base existe
        if not self._spec_exists(feature_request.get("base_spec")):
            errors.append("Spec base no encontrado")

        # 2. Validar cada feature
        for feature in feature_request.get("features", []):
            feature_errors = self._validate_feature(feature)
            errors.extend(feature_errors)

        # 3. Validar dependencias circulares
        if self._has_circular_deps(feature_request.get("features", [])):
            errors.append("Dependencias circulares detectadas")

        # 4. Validar configuración de generación
        gen_config = feature_request.get("generation_config", {})
        if gen_config.get("framework") not in ["fastmcp", "mcp", "typescript"]:
            errors.append("Framework no soportado")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_feature(self, feature: dict) -> list[str]:
        """Valida un feature individual."""
        errors = []

        feature_type = feature.get("type")

        if feature_type in ["aggregation", "transformation"]:
            # Validar que los endpoints existen
            for ep in feature.get("source_endpoints", []):
                method, path = ep.split(" ", 1)
                if not self.base_spec.has_operation(path, method):
                    errors.append(f"Endpoint no encontrado: {ep}")

        if feature_type == "custom_logic":
            # Validar inputs
            for inp in feature.get("inputs", []):
                if "name" not in inp or "type" not in inp:
                    errors.append(f"Input inválido en {feature.get('id')}")

        return errors
```

### 7.4 Mecanismo de Merge con MCP Base

```python
# src/openapi_to_mcp/customization/merger.py

class MCPMerger:
    """Combina MCP base con features personalizados."""

    def __init__(self, base_mcp_path: Path):
        self.base_path = base_mcp_path
        self.base_code = self._load_base_code()

    def merge(
        self,
        custom_features: list[ProcessedFeature],
        config: dict,
    ) -> MergedMCP:
        """
        Combina el MCP base con features personalizados.

        Args:
            custom_features: Features procesados
            config: Configuración de merge

        Returns:
            MCP combinado listo para empaquetar
        """

        # 1. Parsear código base
        base_ast = ast.parse(self.base_code)

        # 2. Encontrar punto de inserción (después de imports, antes de main)
        insert_point = self._find_insert_point(base_ast)

        # 3. Insertar cada feature
        for feature in custom_features:
            feature_ast = ast.parse(feature.tool_code)
            base_ast.body.insert(insert_point, feature_ast)
            insert_point += 1

        # 4. Actualizar imports si es necesario
        self._update_imports(base_ast, custom_features)

        # 5. Generar código final
        merged_code = ast.unparse(base_ast)

        # 6. Formatear con black
        merged_code = black.format_str(merged_code, mode=black.FileMode())

        return MergedMCP(
            server_code=merged_code,
            tools=[f.tool_schema for f in custom_features],
            tests=self._collect_tests(custom_features),
            manifest=self._generate_manifest(custom_features, config),
        )

    def _find_insert_point(self, tree: ast.AST) -> int:
        """Encuentra dónde insertar código nuevo."""

        # Buscar después de imports y antes de if __name__ == "__main__"
        for i, node in enumerate(tree.body):
            if isinstance(node, ast.If):
                # Probablemente es if __name__ == "__main__"
                return i

        return len(tree.body)
```

---

## 8. Arquitectura Multi-Agente

### 8.1 Protocolo de Comunicación

```python
# src/openapi_to_mcp/agents/protocol.py

from enum import Enum
from pydantic import BaseModel
from typing import Any

class MessageType(Enum):
    """Tipos de mensajes entre agentes."""

    # Planificación
    PLAN_REQUEST = "plan_request"
    PLAN_RESPONSE = "plan_response"
    PLAN_APPROVAL = "plan_approval"
    PLAN_REJECTION = "plan_rejection"

    # Ejecución
    TASK_ASSIGNMENT = "task_assignment"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Versionado
    VERSION_CREATE = "version_create"
    VERSION_TAG = "version_tag"
    ROLLBACK_REQUEST = "rollback_request"

    # Control
    ABORT = "abort"
    HEALTH_CHECK = "health_check"

class AgentMessage(BaseModel):
    """Mensaje entre agentes."""

    id: str
    type: MessageType
    sender: str  # agent_id
    receiver: str  # agent_id or "broadcast"
    payload: dict[str, Any]
    timestamp: datetime
    correlation_id: str | None = None  # Para relacionar request/response

class AgentState(Enum):
    """Estados de un agente."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"
```

### 8.2 Agente de Arquitectura

```python
# src/openapi_to_mcp/agents/architect_agent.py

class ArchitectAgent:
    """
    Agente de arquitectura que planifica implementaciones.

    Responsabilidades:
    - Analizar features solicitados
    - Diseñar plan de implementación
    - Coordinar con agente de codificación
    - Validar resultados
    """

    def __init__(
        self,
        llm_client: LLMClient,
        message_bus: MessageBus,
    ):
        self.llm = llm_client
        self.bus = message_bus
        self.state = AgentState.IDLE
        self.current_plan: ImplementationPlan | None = None

    async def process_feature_request(
        self,
        request: FeatureRequest,
    ) -> ImplementationPlan:
        """
        Crea plan de implementación para features solicitados.

        Args:
            request: Request con features a implementar

        Returns:
            Plan de implementación estructurado
        """

        self.state = AgentState.PLANNING

        # 1. Analizar complejidad
        complexity = await self._analyze_complexity(request)

        # 2. Identificar dependencias
        deps = await self._identify_dependencies(request)

        # 3. Ordenar features topológicamente
        ordered = self._topological_sort(request.features, deps)

        # 4. Generar plan con LLM
        plan_prompt = self._build_plan_prompt(request, complexity, ordered)
        plan_response = await self.llm.complete(
            plan_prompt,
            model=self.llm.settings.model_spec_analysis,
        )

        # 5. Parsear y validar plan
        plan = ImplementationPlan.from_llm_response(plan_response)
        plan = await self._validate_plan(plan, request)

        self.current_plan = plan
        self.state = AgentState.IDLE

        return plan

    def _build_plan_prompt(
        self,
        request: FeatureRequest,
        complexity: ComplexityAnalysis,
        ordered_features: list[Feature],
    ) -> str:
        """Construye prompt para planificación."""

        return f"""Eres un arquitecto de software experto en MCP (Model Context Protocol).

## Contexto
Base Spec: {request.base_spec}
Features solicitados: {len(request.features)}
Complejidad estimada: {complexity.level}

## Features a implementar (en orden de dependencias)
{self._format_features(ordered_features)}

## Instrucciones
Genera un plan de implementación detallado que incluya:

1. **Fase de Preparación**
   - Archivos a crear/modificar
   - Dependencias a instalar
   - Configuración necesaria

2. **Fase de Implementación** (por feature)
   - Código a generar
   - Tests a crear
   - Validaciones requeridas

3. **Fase de Integración**
   - Cómo combinar con MCP base
   - Conflictos potenciales
   - Orden de merge

4. **Fase de Versionado**
   - Versión semántica sugerida
   - Changelog entries
   - Tags a crear

Responde en formato JSON estructurado."""

    async def coordinate_execution(
        self,
        plan: ImplementationPlan,
    ) -> ExecutionResult:
        """Coordina la ejecución del plan con el agente de codificación."""

        self.state = AgentState.EXECUTING
        results = []

        for phase in plan.phases:
            # Enviar tareas al agente de codificación
            for task in phase.tasks:
                message = AgentMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.TASK_ASSIGNMENT,
                    sender="architect",
                    receiver="coder",
                    payload={"task": task.to_dict()},
                    timestamp=datetime.now(timezone.utc),
                    correlation_id=plan.id,
                )

                await self.bus.publish(message)

                # Esperar resultado
                response = await self.bus.wait_for(
                    correlation_id=message.id,
                    timeout=300,  # 5 minutos por tarea
                )

                if response.type == MessageType.TASK_FAILED:
                    # Manejar fallo
                    await self._handle_task_failure(task, response)
                    if task.critical:
                        return ExecutionResult(
                            success=False,
                            error=response.payload.get("error"),
                            completed_tasks=results,
                        )
                else:
                    results.append(response.payload)

        self.state = AgentState.COMPLETED
        return ExecutionResult(success=True, completed_tasks=results)
```

### 8.3 Agente de Codificación

```python
# src/openapi_to_mcp/agents/coder_agent.py

class CoderAgent:
    """
    Agente de codificación que ejecuta modificaciones al código.

    Responsabilidades:
    - Generar código según especificaciones
    - Ejecutar modificaciones
    - Crear tests
    - Reportar progreso
    """

    def __init__(
        self,
        llm_client: LLMClient,
        message_bus: MessageBus,
        git_manager: GitManager,
    ):
        self.llm = llm_client
        self.bus = message_bus
        self.git = git_manager
        self.state = AgentState.IDLE

    async def start(self):
        """Inicia el agente y escucha tareas."""

        await self.bus.subscribe(
            message_types=[MessageType.TASK_ASSIGNMENT],
            receiver="coder",
            callback=self._handle_task,
        )

    async def _handle_task(self, message: AgentMessage):
        """Procesa una tarea asignada."""

        self.state = AgentState.EXECUTING
        task = Task.from_dict(message.payload["task"])

        try:
            # 1. Crear branch para la tarea
            branch_name = f"feature/{task.id}"
            self.git.create_branch(branch_name)

            # 2. Reportar inicio
            await self._report_progress(message.id, 0, "Iniciando...")

            # 3. Ejecutar tarea según tipo
            if task.type == TaskType.GENERATE_CODE:
                result = await self._generate_code(task)
            elif task.type == TaskType.MODIFY_CODE:
                result = await self._modify_code(task)
            elif task.type == TaskType.CREATE_TEST:
                result = await self._create_test(task)

            # 4. Commit cambios
            self.git.commit(f"feat({task.id}): {task.description}")

            # 5. Reportar éxito
            await self.bus.publish(AgentMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TASK_COMPLETED,
                sender="coder",
                receiver="architect",
                payload={
                    "task_id": task.id,
                    "result": result,
                    "branch": branch_name,
                    "commit": self.git.get_head_commit(),
                },
                timestamp=datetime.now(timezone.utc),
                correlation_id=message.id,
            ))

        except Exception as e:
            # Rollback y reportar error
            self.git.reset_to_main()
            await self._report_failure(message.id, str(e))

        finally:
            self.state = AgentState.IDLE

    async def _generate_code(self, task: Task) -> dict:
        """Genera código nuevo según especificación."""

        spec = task.payload["specification"]
        output_path = task.payload["output_path"]

        # Generar con LLM
        code = await self.llm.generate_code(
            specification=spec,
            language=task.payload.get("language", "python"),
            style_guide=task.payload.get("style_guide"),
        )

        # Validar código generado
        validation = await self._validate_code(code)
        if not validation.valid:
            code = await self._fix_code(code, validation.issues)

        # Escribir archivo
        Path(output_path).write_text(code)

        return {
            "path": output_path,
            "lines": len(code.splitlines()),
            "validated": validation.valid,
        }

    async def _modify_code(self, task: Task) -> dict:
        """Modifica código existente."""

        file_path = task.payload["file_path"]
        modifications = task.payload["modifications"]

        # Leer código actual
        current_code = Path(file_path).read_text()

        # Aplicar modificaciones con LLM
        modified = await self.llm.apply_modifications(
            code=current_code,
            modifications=modifications,
        )

        # Validar que no se rompió nada
        if not await self._validate_syntax(modified):
            raise ValueError("Modificación produjo código inválido")

        # Escribir cambios
        Path(file_path).write_text(modified)

        return {
            "path": file_path,
            "changes": len(modifications),
        }
```

### 8.4 Estrategia de Rollback

```python
# src/openapi_to_mcp/agents/rollback.py

class RollbackStrategy:
    """Estrategia de rollback para fallos en la ejecución."""

    def __init__(self, git_manager: GitManager, storage: StorageAdapter):
        self.git = git_manager
        self.storage = storage

    async def create_checkpoint(
        self,
        plan_id: str,
        phase: str,
    ) -> Checkpoint:
        """Crea checkpoint antes de fase crítica."""

        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            phase=phase,
            git_commit=self.git.get_head_commit(),
            timestamp=datetime.now(timezone.utc),
        )

        # Guardar estado en storage
        await self.storage.store_checkpoint(checkpoint)

        return checkpoint

    async def rollback_to_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> RollbackResult:
        """Restaura estado a un checkpoint."""

        try:
            # 1. Reset git al commit del checkpoint
            self.git.reset_hard(checkpoint.git_commit)

            # 2. Limpiar artefactos generados después del checkpoint
            await self._cleanup_artifacts_after(checkpoint.timestamp)

            # 3. Restaurar DB si es necesario
            await self._restore_db_state(checkpoint)

            return RollbackResult(
                success=True,
                checkpoint=checkpoint,
                message=f"Rollback exitoso a {checkpoint.id}",
            )

        except Exception as e:
            return RollbackResult(
                success=False,
                error=str(e),
            )

    async def rollback_phase(
        self,
        plan_id: str,
        phase: str,
    ) -> RollbackResult:
        """Rollback de una fase completa."""

        # Encontrar checkpoint de inicio de fase
        checkpoints = await self.storage.get_checkpoints(plan_id)
        phase_checkpoint = next(
            (c for c in checkpoints if c.phase == phase),
            None,
        )

        if not phase_checkpoint:
            return RollbackResult(
                success=False,
                error=f"No se encontró checkpoint para fase {phase}",
            )

        return await self.rollback_to_checkpoint(phase_checkpoint)
```

### 8.5 Sistema de Versionado

```python
# src/openapi_to_mcp/agents/versioning.py

class VersioningManager:
    """Gestiona versionado desde MCP base hasta features completos."""

    def __init__(
        self,
        git_manager: GitManager,
        storage: StorageAdapter,
    ):
        self.git = git_manager
        self.storage = storage

    async def initialize_version(
        self,
        base_mcp_id: str,
        feature_request: FeatureRequest,
    ) -> VersionChain:
        """
        Inicializa cadena de versiones para un MCP personalizado.

        Returns:
            VersionChain con versión base y metadata
        """

        # 1. Obtener versión actual del MCP base
        base_version = await self._get_base_version(base_mcp_id)

        # 2. Crear tag para punto de inicio
        start_tag = f"{feature_request.name}/v0.0.0-base"
        self.git.create_tag(start_tag, f"Base para {feature_request.name}")

        # 3. Inicializar changelog
        changelog = Changelog()
        changelog.add_entry(
            version="0.0.0",
            type="base",
            description=f"Versión base desde {base_mcp_id}",
        )

        return VersionChain(
            id=str(uuid.uuid4()),
            name=feature_request.name,
            base_mcp_id=base_mcp_id,
            base_version=base_version,
            current_version="0.0.0",
            changelog=changelog,
            versions=[],
        )

    async def create_version(
        self,
        chain: VersionChain,
        change_type: str,  # "major", "minor", "patch"
        features_completed: list[str],
        description: str,
    ) -> Version:
        """
        Crea nueva versión después de completar features.

        Args:
            chain: Cadena de versiones
            change_type: Tipo de cambio semántico
            features_completed: IDs de features completados
            description: Descripción del cambio

        Returns:
            Nueva versión creada
        """

        # 1. Calcular nueva versión
        new_version_str = VersioningStrategy.calculate_next_version(
            chain.current_version,
            change_type,
        )

        # 2. Crear commit de versión
        commit = self.git.commit(
            f"release: v{new_version_str}\n\n{description}"
        )

        # 3. Crear tag
        tag = f"{chain.name}/v{new_version_str}"
        self.git.create_tag(tag, description)

        # 4. Actualizar changelog
        chain.changelog.add_entry(
            version=new_version_str,
            type=change_type,
            description=description,
            features=features_completed,
        )

        # 5. Crear versión
        version = Version(
            version=new_version_str,
            commit=commit,
            tag=tag,
            features=features_completed,
            created_at=datetime.now(timezone.utc),
        )

        chain.versions.append(version)
        chain.current_version = new_version_str

        # 6. Persistir
        await self.storage.update_version_chain(chain)

        return version

    async def finalize_version(
        self,
        chain: VersionChain,
    ) -> FinalVersion:
        """
        Finaliza la cadena de versiones (versión 1.0.0).

        Marca el MCP como production-ready.
        """

        final_version = await self.create_version(
            chain=chain,
            change_type="major",
            features_completed=["all"],
            description="Primera versión estable con todos los features",
        )

        # Merge a main
        self.git.merge_to_main(chain.name)

        # Tag de release
        self.git.create_tag(
            f"{chain.name}/v1.0.0-release",
            "Release oficial",
            signed=True,
        )

        return FinalVersion(
            version=final_version,
            release_tag=f"{chain.name}/v1.0.0-release",
            artifacts_url=await self._generate_release_artifacts(chain),
        )
```

---

## 9. Sistema de Autenticación OAuth2 a Nivel MCP

### 9.1 Almacenamiento de Tokens

```python
# src/openapi_to_mcp/auth/oauth2/token_store.py

from abc import ABC, abstractmethod
from typing import Optional
import redis.asyncio as redis

class TokenStore(ABC):
    """Interfaz abstracta para almacenamiento de tokens."""

    @abstractmethod
    async def store(
        self,
        user_id: str,
        provider: str,
        tokens: OAuth2Tokens,
    ) -> None:
        """Almacena tokens para un usuario."""
        pass

    @abstractmethod
    async def get(
        self,
        user_id: str,
        provider: str,
    ) -> Optional[OAuth2Tokens]:
        """Obtiene tokens de un usuario."""
        pass

    @abstractmethod
    async def delete(
        self,
        user_id: str,
        provider: str,
    ) -> None:
        """Elimina tokens de un usuario."""
        pass


class MemoryTokenStore(TokenStore):
    """Almacenamiento en memoria (development)."""

    def __init__(self):
        self._tokens: dict[str, OAuth2Tokens] = {}

    def _key(self, user_id: str, provider: str) -> str:
        return f"{user_id}:{provider}"

    async def store(self, user_id: str, provider: str, tokens: OAuth2Tokens):
        self._tokens[self._key(user_id, provider)] = tokens

    async def get(self, user_id: str, provider: str) -> Optional[OAuth2Tokens]:
        return self._tokens.get(self._key(user_id, provider))

    async def delete(self, user_id: str, provider: str):
        key = self._key(user_id, provider)
        if key in self._tokens:
            del self._tokens[key]


class RedisTokenStore(TokenStore):
    """Almacenamiento en Redis (production)."""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.prefix = "oauth2:tokens:"

    def _key(self, user_id: str, provider: str) -> str:
        return f"{self.prefix}{user_id}:{provider}"

    async def store(self, user_id: str, provider: str, tokens: OAuth2Tokens):
        key = self._key(user_id, provider)
        data = tokens.to_json()

        # TTL basado en expiración del token
        ttl = tokens.expires_in or 3600

        await self.redis.setex(key, ttl, data)

    async def get(self, user_id: str, provider: str) -> Optional[OAuth2Tokens]:
        key = self._key(user_id, provider)
        data = await self.redis.get(key)

        if data:
            return OAuth2Tokens.from_json(data)
        return None

    async def delete(self, user_id: str, provider: str):
        await self.redis.delete(self._key(user_id, provider))


class DatabaseTokenStore(TokenStore):
    """Almacenamiento en base de datos (persistent)."""

    def __init__(self, db_session):
        self.db = db_session

    async def store(self, user_id: str, provider: str, tokens: OAuth2Tokens):
        from .models import UserToken

        # Encriptar tokens sensibles
        encrypted = self._encrypt_tokens(tokens)

        existing = await self.db.query(UserToken).filter_by(
            user_id=user_id,
            provider=provider,
        ).first()

        if existing:
            existing.access_token = encrypted.access_token
            existing.refresh_token = encrypted.refresh_token
            existing.expires_at = tokens.expires_at
        else:
            token = UserToken(
                user_id=user_id,
                provider=provider,
                access_token=encrypted.access_token,
                refresh_token=encrypted.refresh_token,
                expires_at=tokens.expires_at,
            )
            self.db.add(token)

        await self.db.commit()
```

### 9.2 Auto-Refresh de Tokens

```python
# src/openapi_to_mcp/auth/oauth2/refresh_handler.py

class TokenRefreshHandler:
    """Maneja refresh automático de tokens expirados."""

    def __init__(
        self,
        token_store: TokenStore,
        providers: dict[str, OAuth2Provider],
    ):
        self.store = token_store
        self.providers = providers
        self._refresh_buffer = 300  # 5 minutos antes de expirar

    async def get_valid_token(
        self,
        user_id: str,
        provider: str,
    ) -> str:
        """
        Obtiene token válido, refrescando si es necesario.

        Returns:
            Access token válido

        Raises:
            TokenExpiredError: Si no se puede refrescar
        """

        tokens = await self.store.get(user_id, provider)

        if not tokens:
            raise NoTokenError(f"No hay tokens para {user_id}@{provider}")

        # Verificar si necesita refresh
        if self._needs_refresh(tokens):
            tokens = await self._refresh(user_id, provider, tokens)

        return tokens.access_token

    def _needs_refresh(self, tokens: OAuth2Tokens) -> bool:
        """Verifica si el token necesita refresh."""

        if not tokens.expires_at:
            return False

        expiry = tokens.expires_at - timedelta(seconds=self._refresh_buffer)
        return datetime.now(timezone.utc) >= expiry

    async def _refresh(
        self,
        user_id: str,
        provider_name: str,
        tokens: OAuth2Tokens,
    ) -> OAuth2Tokens:
        """Refresca tokens expirados."""

        if not tokens.refresh_token:
            raise TokenExpiredError("No hay refresh token disponible")

        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} no configurado")

        try:
            new_tokens = await provider.refresh_token(tokens.refresh_token)

            # Actualizar store
            await self.store.store(user_id, provider_name, new_tokens)

            logger.info(f"Token refrescado para {user_id}@{provider_name}")
            return new_tokens

        except OAuth2Error as e:
            # Token de refresh también expiró
            await self.store.delete(user_id, provider_name)
            raise TokenExpiredError(f"Refresh falló: {e}")
```

### 9.3 Inyección de Headers

```python
# src/openapi_to_mcp/auth/oauth2/token_injector.py

class TokenInjector:
    """Inyecta tokens OAuth2 en requests HTTP."""

    def __init__(
        self,
        refresh_handler: TokenRefreshHandler,
        header_config: dict[str, str] = None,
    ):
        self.refresh_handler = refresh_handler
        self.header_config = header_config or {
            "default": "Authorization: Bearer {token}",
        }

    async def inject(
        self,
        request: httpx.Request,
        user_context: UserContext,
    ) -> httpx.Request:
        """
        Inyecta token en el request.

        Args:
            request: Request HTTP a modificar
            user_context: Contexto del usuario con provider info

        Returns:
            Request con headers de autenticación
        """

        if not user_context.requires_auth:
            return request

        # Obtener token válido
        token = await self.refresh_handler.get_valid_token(
            user_id=user_context.user_id,
            provider=user_context.oauth_provider,
        )

        # Determinar formato de header
        header_format = self.header_config.get(
            user_context.oauth_provider,
            self.header_config["default"],
        )

        # Parsear y aplicar header
        header_name, header_value = self._parse_header_format(
            header_format,
            token,
        )

        # Modificar request
        request.headers[header_name] = header_value

        return request

    def _parse_header_format(
        self,
        format_str: str,
        token: str,
    ) -> tuple[str, str]:
        """Parsea formato de header."""

        # Formato: "Header-Name: value template with {token}"
        name, template = format_str.split(":", 1)
        value = template.strip().format(token=token)

        return name.strip(), value


# Middleware para httpx
class OAuth2Middleware:
    """Middleware que inyecta tokens automáticamente."""

    def __init__(self, injector: TokenInjector):
        self.injector = injector
        self._context: UserContext | None = None

    def set_context(self, context: UserContext):
        """Establece contexto de usuario para requests."""
        self._context = context

    async def __call__(
        self,
        request: httpx.Request,
    ) -> httpx.Request:
        """Procesa request antes de enviar."""

        if self._context:
            return await self.injector.inject(request, self._context)

        return request
```

### 9.4 Propagación de Contexto

```python
# src/openapi_to_mcp/auth/oauth2/context.py

from contextvars import ContextVar
from dataclasses import dataclass

# Context variable para propagar usuario a través de la cadena
_user_context: ContextVar[Optional["UserContext"]] = ContextVar(
    "user_context",
    default=None,
)

@dataclass
class UserContext:
    """Contexto de usuario para autenticación."""

    user_id: str
    oauth_provider: str | None = None
    requires_auth: bool = True
    scopes: list[str] = None
    extra: dict = None

    @classmethod
    def get_current(cls) -> Optional["UserContext"]:
        """Obtiene contexto actual."""
        return _user_context.get()

    @classmethod
    def set_current(cls, context: "UserContext"):
        """Establece contexto actual."""
        _user_context.set(context)


class UserContextMiddleware:
    """Middleware Flask para establecer contexto de usuario."""

    def __init__(self, app, token_store: TokenStore):
        self.app = app
        self.token_store = token_store
        app.before_request(self._set_context)
        app.after_request(self._clear_context)

    async def _set_context(self):
        """Establece contexto antes de cada request."""

        from flask import g
        from flask_login import current_user

        if current_user.is_authenticated:
            # Determinar provider OAuth del usuario
            provider = await self._get_user_provider(current_user.id)

            context = UserContext(
                user_id=str(current_user.id),
                oauth_provider=provider,
                requires_auth=provider is not None,
            )

            UserContext.set_current(context)
            g.user_context = context

    def _clear_context(self, response):
        """Limpia contexto después de request."""
        _user_context.set(None)
        return response

    async def _get_user_provider(self, user_id: int) -> str | None:
        """Obtiene provider OAuth asociado al usuario."""

        # Verificar si hay tokens almacenados
        for provider in ["auth0", "okta", "azure_ad"]:
            tokens = await self.token_store.get(str(user_id), provider)
            if tokens:
                return provider

        return None


# Uso en código generado de MCP
class MCPToolWithAuth:
    """Base para tools MCP con autenticación OAuth2."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> dict:
        """Hace request con autenticación automática."""

        # Obtener contexto actual
        context = UserContext.get_current()

        if context and context.requires_auth:
            # El middleware de httpx inyectará el token
            pass

        response = await self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
```

---

## 10. Dependencias y Configuración Faltante

### 10.1 Dependencias a Agregar

```toml
# pyproject.toml - agregar a [project.optional-dependencies]

# IA/LLM
ai = [
    "ollama>=0.1.0",           # Cliente Ollama oficial
    "tiktoken>=0.5.0",          # Tokenización
    "sentence-transformers>=2.2.0",  # Embeddings
]

# Storage
storage = [
    "minio>=7.2.0",             # Cliente MinIO
    "boto3>=1.34.0",            # AWS S3 compatible
]

# Cache
cache = [
    "redis>=5.0.0",             # Redis async
    "hiredis>=2.3.0",           # Parser optimizado
]

# Auth
auth = [
    "authlib>=1.3.0",           # OAuth2 client
    "python-jose[cryptography]>=3.3.0",  # JWT
    "passlib[bcrypt]>=1.7.0",   # Password hashing
]

# Agentes
agents = [
    "celery>=5.3.0",            # Task queue
    "kombu>=5.3.0",             # Message broker
]

# Full enterprise
enterprise = [
    "openapi-to-mcp[ai,storage,cache,auth,agents]",
]
```

### 10.2 Archivos de Configuración a Crear

```bash
# Crear estructura de configuración
mkdir -p config

# Archivos necesarios
touch config/ollama.yaml
touch config/minio.yaml
touch config/oauth2.yaml
touch config/redis.yaml
touch config/agents.yaml
touch .env.example
touch alembic.ini
```

### 10.3 Variables de Entorno (.env.example)

```bash
# Database
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@localhost:5432/openapi_mcp

# Ollama
OLLAMA_HOST=localhost
OLLAMA_PORT=11434

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# Redis
REDIS_URL=redis://localhost:6379/0

# OAuth2
OAUTH2_ISSUER=https://your-domain.auth0.com
OAUTH2_CLIENT_ID=your-client-id
OAUTH2_CLIENT_SECRET=your-client-secret

# Encryption
ENCRYPTION_KEY=your-32-byte-key-here

# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=production

# Workers
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 10.4 Comandos de Instalación

```bash
# Instalación básica con todas las features enterprise
pip install -e ".[enterprise]"

# O instalación modular
pip install -e ".[gui,postgresql,ai,storage]"

# Servicios externos requeridos
# Docker Compose para desarrollo
docker-compose -f docker-compose.dev.yml up -d

# Contenido de docker-compose.dev.yml
```

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: openapi_mcp
      POSTGRES_PASSWORD: development
      POSTGRES_DB: openapi_mcp
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

volumes:
  postgres_data:
  redis_data:
  minio_data:
  ollama_data:
```

---

## 11. Plan de Implementación Priorizado

### Fase 1: Infraestructura Base (2-3 semanas)

| Tarea | Prioridad | Complejidad | Dependencias |
|-------|-----------|-------------|--------------|
| Crear `config/settings.py` con Pydantic | P0 | Baja | - |
| Agregar `.env.example` | P0 | Baja | - |
| Crear `docker-compose.dev.yml` | P0 | Baja | - |
| Implementar `storage/adapters/minio_adapter.py` | P0 | Media | MinIO |
| Crear `alembic.ini` y migraciones | P0 | Media | PostgreSQL |
| Agregar tests para enterprise features | P1 | Media | - |

### Fase 2: Integración IA (3-4 semanas)

| Tarea | Prioridad | Complejidad | Dependencias |
|-------|-----------|-------------|--------------|
| Implementar `ai/llm_client.py` | P0 | Media | Ollama |
| Crear `ai/adapters/ollama_adapter.py` | P0 | Media | Ollama |
| Implementar `ai/assistants/spec_analyzer.py` | P1 | Alta | LLM Client |
| Crear endpoints `/api/ai/*` | P1 | Media | LLM Client |
| Agregar UI para sugerencias IA | P2 | Media | Endpoints |

### Fase 3: OAuth2 y Autenticación (2-3 semanas)

| Tarea | Prioridad | Complejidad | Dependencias |
|-------|-----------|-------------|--------------|
| Implementar `auth/oauth2/token_store.py` | P0 | Media | Redis |
| Crear `auth/oauth2/providers/*.py` | P0 | Media | - |
| Implementar `auth/oauth2/token_injector.py` | P1 | Media | Token Store |
| Integrar con código generado de MCPs | P1 | Alta | Injector |
| Agregar UI para configuración OAuth | P2 | Media | - |

### Fase 4: Sistema Multi-Agente (4-6 semanas)

| Tarea | Prioridad | Complejidad | Dependencias |
|-------|-----------|-------------|--------------|
| Implementar `agents/protocol.py` | P0 | Baja | - |
| Crear `agents/message_bus.py` | P0 | Media | Redis/Celery |
| Implementar `agents/architect_agent.py` | P1 | Alta | LLM, Message Bus |
| Implementar `agents/coder_agent.py` | P1 | Alta | Git, LLM |
| Crear `agents/versioning.py` | P1 | Media | Git |
| Implementar `agents/rollback.py` | P2 | Media | Storage |

### Fase 5: Features Personalizados (3-4 semanas)

| Tarea | Prioridad | Complejidad | Dependencias |
|-------|-----------|-------------|--------------|
| Implementar `customization/feature_processor.py` | P1 | Alta | LLM |
| Crear `customization/validator.py` | P1 | Media | - |
| Implementar `customization/merger.py` | P1 | Alta | AST |
| Agregar UI para definición de features | P2 | Media | - |
| Crear templates para feature types | P2 | Media | Jinja2 |

---

## Conclusión

Este análisis identifica gaps significativos en:

1. **Persistencia**: Necesidad crítica de MinIO para artefactos
2. **IA**: Oportunidad de diferenciación con Ollama integrado
3. **Runtime**: Los MCPs se generan pero no se ejecutan/testean
4. **Auth**: OAuth2 no está implementado para MCPs generados
5. **Escalabilidad**: Multi-tenant y cache distribuido pendientes

La implementación recomendada sigue un orden que minimiza dependencias:
1. Infraestructura base (settings, storage, DB migrations)
2. IA con Ollama (asistencia al usuario)
3. OAuth2 (autenticación transparente)
4. Multi-agente (automatización avanzada)
5. Features personalizados (valor diferencial)

**Esfuerzo estimado total**: 14-20 semanas para implementación completa.
