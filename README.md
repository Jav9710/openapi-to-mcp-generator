# OpenAPI to MCP Generator

Generador automático de servidores MCP (Model Context Protocol) a partir de especificaciones OpenAPI 3.0/3.1. Permite que los LLMs interactúen con los microservicios de tu empresa de forma estandarizada.

## Características Principales

### Core Features
- **Parser OpenAPI completo**: Soporta OpenAPI 3.0.x y 3.1.x con validación estricta
- **Transformación automática**: Convierte endpoints en Tools y schemas en Resources
- **Selección de endpoints**: Elige qué endpoints incluir mediante CLI, modo interactivo o GUI web
- **Soporte FastMCP y MCP**: Genera servidores con FastMCP (recomendado) o MCP estándar
- **Autenticación flexible**: Soporta API Key, Bearer Token, Basic Auth y OAuth2
- **Cliente HTTP resiliente**: Reintentos automáticos con backoff exponencial
- **Despliegue Docker**: Imagen Docker lista para producción con Gunicorn

### UI/UX Features ✨
- **🌙 Dark/Light Mode**: Tema oscuro/claro con detección automática del sistema
- **📋 Toast Notifications**: Sistema de notificaciones elegante y no intrusivo
- **📂 Drag & Drop**: Arrastra archivos OpenAPI para cargarlos instantáneamente
- **🕒 Recent Specs**: Historial de las últimas 10 especificaciones cargadas
- **💾 Export/Import Config**: Exporta e importa configuraciones de selección de endpoints
- **🔖 Presets**: Guarda y reutiliza selecciones de endpoints como presets
- **📊 Progress Bars**: Barras de progreso detalladas con 10 pasos visibles
- **⚡ Auto Cleanup**: Limpieza automática de archivos temporales y sesiones expiradas
- **📚 Spec Library**: Biblioteca completa de especificaciones con versionado
- **🔄 Version Control**: Historial de versiones con timeline visual y diff viewer
- **⭐ Favorites & Tags**: Sistema de favoritos y etiquetado para organizar specs
- **🔍 Advanced Search**: Búsqueda y filtrado avanzado de especificaciones
- **📈 Generation Tracking**: Registro de todas las generaciones MCP realizadas
- **⚙️ Advanced Configuration**: Configuración avanzada por especificación
- **📝 Dual Mode Editor**: Formulario GUI y editor YAML/JSON con toggle
- **🎨 Configuration Profiles**: Perfiles reutilizables (Development, Production, etc.)
- **✅ Real-time Validation**: Validación en tiempo real con errores y advertencias
- **💾 Config Import/Export**: Exporta e importa configuraciones en YAML

### Enterprise Features
- **🔒 Auditoría completa**: 45 tipos de eventos con 4 niveles de severidad
- **🔐 Encriptación**: AES-256 con Fernet y derivación PBKDF2 para specs sensibles
- **📊 Dashboard admin**: Métricas de uso, actividad por equipo, generaciones
- **🚨 Alertas configurables**: 10 tipos de alertas con thresholds y notificaciones
- **📋 Reportes automáticos**: 8 tipos de reportes en JSON/CSV/HTML con scheduling
- **🗃️ Data Retention**: Políticas de retención para 9 tipos de datos con cleanup automático
- **🌐 Multi-Database**: Soporte para SQLite, PostgreSQL y MongoDB

### AI & Cloud Features
- **🤖 Ollama Integration**: Análisis inteligente de specs, generación de docs, auditoría de seguridad IA
- **📦 MinIO Storage**: Almacenamiento S3-compatible para specs, artefactos MCP y reportes
- **🔐 OAuth2 Management**: Gestión centralizada de tokens con OIDC Discovery y refresh automático
- **⚙️ Feature Toggles**: Activa/desactiva módulos independientemente (AI, Storage, OAuth2)
- **🐳 Dev Infrastructure**: docker-compose con PostgreSQL, Redis, MinIO y Ollama

### Developer Experience
- **🎯 Smart Error Messages**: Errores con contexto, sugerencias de solución y links a docs
- **🔍 Carga desde URL**: Importa especificaciones OpenAPI desde URLs remotas
- **📦 Descarga como ZIP**: Genera y descarga servidores MCP comprimidos
- **🚀 Live Preview**: Vista previa del código generado sin guardarlo

---

## Tabla de Contenidos

1. [Instalación](#instalación)
2. [Inicio Rápido](#inicio-rápido)
3. [Modos de Uso](#modos-de-uso)
   - [CLI Básico](#modo-1-cli-básico)
   - [CLI con Filtros](#modo-2-cli-con-filtros-de-endpoints)
   - [CLI Interactivo](#modo-3-cli-interactivo)
   - [GUI Web](#modo-4-gui-web)
   - [Modo Standalone](#modo-5-modo-standalone-web)
4. [Despliegue Docker](#despliegue-docker)
5. [Frameworks MCP](#frameworks-mcp)
6. [Configuración](#configuración)
7. [Procesamiento Batch](#procesamiento-batch)
8. [Integración con Claude Desktop](#integración-con-claude-desktop)
9. [Enterprise Features](#enterprise-features-1)
   - [Configuración de Entorno](#configuración-de-entorno)
   - [Integración IA (Ollama)](#integración-ia-ollama)
   - [Almacenamiento (MinIO)](#almacenamiento-minio)
   - [OAuth2 Authentication](#oauth2-authentication)
   - [Auditoría de Acciones](#auditoría-de-acciones)
   - [Encriptación de Specs](#encriptación-de-specs)
   - [Alertas Configurables](#alertas-configurables)
   - [Reportes Automáticos](#reportes-automáticos)
   - [Dashboard de Métricas](#dashboard-de-métricas)
   - [Políticas de Retención](#políticas-de-retención-de-datos)
   - [Configuración de Base de Datos](#configuración-de-base-de-datos)
10. [API Reference](#api-reference)
11. [Arquitectura](#arquitectura)
12. [Mapeo OpenAPI → MCP](#mapeo-openapi--mcp)
13. [Ejemplos](#ejemplos)
14. [Consideraciones](#consideraciones)
15. [Contribuir](#contribuir)

---

## Instalación

### Requisitos

- Python >= 3.10
- pip o pipx

### Instalación básica

```bash
# Clonar el repositorio
git clone https://github.com/enterprise/openapi-to-mcp.git
cd openapi-to-mcp-generator

# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Linux/Mac:
source .venv/bin/activate
# Windows:
.\.venv\Scripts\activate

# Instalar el paquete
pip install -e .
```

### Instalación con características opcionales

```bash
# Instalar con modo interactivo CLI (questionary)
pip install -e ".[interactive]"

# Instalar con GUI web (Flask + requests + gunicorn)
pip install -e ".[gui]"

# Instalar con IA (Ollama integration)
pip install -e ".[ai]"

# Instalar con almacenamiento MinIO
pip install -e ".[storage]"

# Instalar con PostgreSQL
pip install -e ".[postgresql]"

# Instalar con Redis (cache, token store, message broker)
pip install -e ".[redis]"

# Instalar con OAuth2
pip install -e ".[oauth2]"

# Instalar todas las características
pip install -e ".[all]"

# Instalar con herramientas de desarrollo
pip install -e ".[dev]"
```

### Verificar instalación

```bash
openapi-to-mcp --version
# Output: openapi-to-mcp, version 1.0.0

openapi-to-mcp --help
```

---

## Inicio Rápido

### 1. Preparar tu especificación OpenAPI

Asegúrate de tener un archivo OpenAPI válido (YAML o JSON):

```yaml
# mi-api.yaml
openapi: "3.0.3"
info:
  title: Mi API
  version: "1.0.0"
paths:
  /users:
    get:
      summary: Listar usuarios
      responses:
        "200":
          description: Lista de usuarios
```

### 2. Generar el servidor MCP

```bash
openapi-to-mcp generate mi-api.yaml --service-name mi_api
```

### 3. Ejecutar el servidor generado

```bash
cd output/mcp_server_mi_api
pip install -r requirements.txt
python -m src.server
```

### Alternativa: Usar la GUI Web

```bash
# Opción 1: Con archivo local
openapi-to-mcp gui mi-api.yaml

# Opción 2: Modo standalone (subir archivo o cargar desde URL)
openapi-to-mcp gui
# o
openapi-to-mcp serve
```

---

## Modos de Uso

### Modo 1: CLI Básico

El modo más simple para generar un servidor MCP con todos los endpoints:

```bash
openapi-to-mcp generate <spec_path> --service-name <nombre> [opciones]
```

**Opciones principales:**

| Opción | Descripción |
|--------|-------------|
| `--service-name, -n` | Nombre del servicio (requerido) |
| `--output, -o` | Directorio de salida (default: ./output) |
| `--service-prefix, -p` | Prefijo para tools/resources |
| `--base-url, -u` | URL base de la API |
| `--environment, -e` | Ambiente: development, staging, production |
| `--mcp-framework` | Framework: fastmcp (default) o mcp |
| `--include-deprecated` | Incluir endpoints deprecated |
| `--skip-validation` | Omitir validación estricta |
| `--verbose, -v` | Logging detallado |

**Ejemplo completo:**

```bash
openapi-to-mcp generate ./specs/users-api.yaml \
    --service-name user_management \
    --service-prefix users \
    --base-url https://api.example.com/v2 \
    --environment production \
    --mcp-framework fastmcp \
    --output ./servers
```

---

### Modo 2: CLI con Filtros de Endpoints

Filtra qué endpoints incluir usando patrones glob:

```bash
# Incluir solo endpoints que coincidan con patrones
openapi-to-mcp generate api.yaml -n myservice \
    --include-endpoints "/v1/api/users*" \
    --include-endpoints "/v1/api/orders*"

# Excluir endpoints específicos
openapi-to-mcp generate api.yaml -n myservice \
    --exclude-endpoints "/internal/*" \
    --exclude-endpoints "*/admin/*"

# Combinar inclusión y exclusión
openapi-to-mcp generate api.yaml -n myservice \
    -i "/api/*" \
    -x "/api/internal/*" \
    -x "/api/debug/*"
```

**Patrones soportados:**

| Patrón | Descripción | Ejemplo |
|--------|-------------|---------|
| `*` | Cualquier secuencia de caracteres | `/users*` → `/users`, `/users/123` |
| `?` | Un solo carácter | `/user?` → `/users`, `/usera` |
| `**` | Cualquier profundidad | `/api/**` → `/api/v1/users` |

---

### Modo 3: CLI Interactivo

Selecciona endpoints de forma interactiva en la terminal:

```bash
# Requiere: pip install questionary
openapi-to-mcp generate api.yaml -n myservice --interactive
```

**Flujo interactivo:**

```
┌─────────────────────────────────────────────────────────────┐
│ ¿Cómo deseas seleccionar los endpoints?                    │
│                                                             │
│ > Selección manual (checkboxes)                            │
│   Por patrones (glob)                                      │
│   Por tags (grupos)                                        │
│   Todos los endpoints                                      │
└─────────────────────────────────────────────────────────────┘
```

**Opciones de selección:**

1. **Selección manual**: Lista con checkboxes para marcar/desmarcar
2. **Por patrones**: Ingresa patrones glob interactivamente
3. **Por tags**: Selecciona grupos de endpoints por sus tags OpenAPI
4. **Todos**: Incluir todos los endpoints sin filtro

---

### Modo 4: GUI Web

Interfaz gráfica web para selección visual de endpoints con un archivo pre-cargado:

```bash
# Requiere: pip install flask
openapi-to-mcp gui api.yaml
```

**Opciones:**

```bash
openapi-to-mcp gui <spec_path> [opciones]

# Opciones disponibles:
  --port, -p      Puerto del servidor web (default: 5000)
  --no-browser    No abrir el navegador automáticamente
  --output, -o    Directorio de salida (default: ./output)
```

**Ejemplo:**

```bash
openapi-to-mcp gui ./specs/large-api.yaml --port 8080
```

---

### Modo 5: Modo Standalone (Web)

Ejecuta la GUI sin necesidad de un archivo pre-cargado. Permite:

- **Subir archivos**: Arrastra y suelta o selecciona desde el explorador
- **Cargar desde URL**: Ingresa la URL directa a una especificación OpenAPI
- **Descargar como ZIP**: Genera el servidor y descárgalo comprimido

```bash
# Opción 1: Comando gui sin argumentos
openapi-to-mcp gui

# Opción 2: Comando serve dedicado
openapi-to-mcp serve --port 5000 --output ./output
```

**Interfaz de Upload:**

```
┌─────────────────────────────────────────────────────────────────┐
│            OpenAPI to MCP Generator                              │
│                                                                  │
│     ┌─────────────────────────────────────────────────────┐     │
│     │              Carga tu especificación                 │     │
│     │                                                      │     │
│     │    [  Archivo  ]  [    URL    ]                     │     │
│     │                                                      │     │
│     │    ┌────────────────────────────────────────────┐   │     │
│     │    │                                            │   │     │
│     │    │       Arrastra tu archivo aquí             │   │     │
│     │    │                  o                         │   │     │
│     │    │      [ Seleccionar Archivo ]               │   │     │
│     │    │                                            │   │     │
│     │    │  Formatos: .yaml, .yml, .json              │   │     │
│     │    └────────────────────────────────────────────┘   │     │
│     │                                                      │     │
│     │    ─── O cargar desde URL ───                       │     │
│     │                                                      │     │
│     │    [ https://api.example.com/openapi.json ] [Cargar]│     │
│     │                                                      │     │
│     │    Ejemplos: [Petstore API] [GitHub API]            │     │
│     └─────────────────────────────────────────────────────┘     │
│                                                                  │
│     ┌─────────┐  ┌─────────┐  ┌─────────┐                       │
│     │Selección│  │ FastMCP │  │Descarga │                       │
│     │ Visual  │  │  / MCP  │  │  ZIP    │                       │
│     └─────────┘  └─────────┘  └─────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

**Interfaz de Selección de Endpoints:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  OpenAPI to MCP Generator                    API: Petstore v1.0        │
├─────────────────────────────────────────────────────────────────────────┤
│  [Vista: Lista ▼] [Buscar: ____________] [Patrón: /users/*] [Agregar]  │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─── Disponibles (15) ────┐         ┌─── Seleccionados (5) ───┐       │
│  │ □ [GET] /users          │   >>    │ ☑ [GET] /orders         │       │
│  │ □ [POST] /users         │         │ ☑ [POST] /orders        │       │
│  │ □ [GET] /users/{id}     │   <<    │ ☑ [GET] /orders/{id}    │       │
│  │ □ [PUT] /users/{id}     │         │ ☑ [PUT] /orders/{id}    │       │
│  │ □ [DELETE] /users/{id}  │         │ ☑ [DELETE] /orders/{id} │       │
│  └─────────────────────────┘         └─────────────────────────┘       │
│                                                                         │
│  ┌─ Configuración ─────────────────────────────────────────────────┐   │
│  │ Nombre: [myservice    ] Prefijo: [myservice] URL: [          ]  │   │
│  │ Framework: [FastMCP ▼]  Ambiente: [Production ▼]                │   │
│  │ [✓] Descargar como ZIP                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [Cancelar]                                    [Generar Servidor MCP]   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Características de la GUI:**

- **Carga flexible**: Archivo local o URL remota
- **Vista Lista/Tags**: Alternar entre vista plana y agrupada por tags
- **Búsqueda**: Filtrar endpoints en tiempo real
- **Patrones rápidos**: Agregar múltiples endpoints con un patrón glob
- **Drag & Drop**: Arrastrar endpoints entre listas
- **Doble clic**: Mover un endpoint rápidamente
- **Configuración**: Ajustar nombre, prefijo, URL, framework y ambiente
- **Descarga ZIP**: Obtener el servidor generado como archivo comprimido
- **URLs de ejemplo**: Cargar rápidamente APIs populares (Petstore, GitHub)

---

## Despliegue Docker

### Construcción de imagen

```bash
# Construir la imagen
docker build -t openapi-to-mcp .

# Ejecutar el contenedor
docker run -p 5000:5000 openapi-to-mcp
```

### Docker Compose - Producción

```bash
# Iniciar el servicio
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

**docker-compose.yml** (producción - solo la app):

```yaml
version: '3.8'

services:
  openapi-to-mcp:
    build: .
    ports:
      - "5000:5000"
    environment:
      - PORT=5000
      - WORKERS=2
      - THREADS=4
    volumes:
      - mcp-output:/app/output
    restart: unless-stopped

volumes:
  mcp-output:
```

### Docker Compose - Desarrollo (Full Stack)

Incluye todos los servicios enterprise: PostgreSQL, Redis, MinIO y Ollama.

```bash
# Levantar todos los servicios de desarrollo
docker-compose -f docker-compose.dev.yml up -d

# Verificar que todo esté corriendo
docker-compose -f docker-compose.dev.yml ps

# Ver logs de un servicio específico
docker-compose -f docker-compose.dev.yml logs -f ollama
```

**Servicios incluidos:**

| Servicio | Puerto | Descripción | Console |
|----------|--------|-------------|---------|
| **PostgreSQL 16** | 5432 | Base de datos relacional | - |
| **Redis 7** | 6379 | Cache, token store, message broker | - |
| **MinIO** | 9000 / 9001 | Almacenamiento S3-compatible | `http://localhost:9001` |
| **Ollama** | 11434 | LLM local para análisis IA | - |

MinIO crea automáticamente 4 buckets al iniciar: `openapi-specs`, `mcp-artifacts`, `reports`, `backups`.

**Configurar la app para usar los servicios:**

```env
# .env
DATABASE_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=openapi_mcp
DB_USER=openapi_mcp
DB_PASSWORD=development

ENABLE_AI=true
ENABLE_STORAGE=true

REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
OLLAMA_HOST=localhost
```

### Variables de entorno Docker

| Variable | Descripción | Default |
|----------|-------------|---------|
| `PORT` | Puerto del servidor | 5000 |
| `OUTPUT_DIR` | Directorio de salida | /app/output |
| `WORKERS` | Workers de gunicorn | 2 |
| `THREADS` | Threads por worker | 4 |
| `DATABASE_TYPE` | Tipo de BD (sqlite/postgresql/mongodb) | sqlite |
| `ENABLE_AI` | Activar integración Ollama | false |
| `ENABLE_STORAGE` | Activar almacenamiento MinIO | false |
| `ENABLE_OAUTH2` | Activar gestión OAuth2 | false |

### Producción con Nginx

```nginx
server {
    listen 80;
    server_name openapi-mcp.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Frameworks MCP

El generador soporta dos frameworks para crear el servidor MCP:

### FastMCP (Recomendado)

API simplificada con decoradores. Ideal para la mayoría de casos.

```bash
openapi-to-mcp generate api.yaml -n myservice --mcp-framework fastmcp
```

**Código generado:**

```python
from fastmcp import FastMCP

mcp = FastMCP("myservice")

@mcp.tool(description="Listar usuarios")
async def myservice_list_users(page: int = 1, limit: int = 10) -> str:
    response = await http_client.request(
        method="GET",
        path="/users",
        params={"page": page, "limit": limit}
    )
    return json.dumps(response)

if __name__ == "__main__":
    mcp.run()
```

### MCP Estándar

API de bajo nivel con más control. Para casos avanzados.

```bash
openapi-to-mcp generate api.yaml -n myservice --mcp-framework mcp
```

**Comparación:**

| Característica | FastMCP | MCP Estándar |
|---------------|---------|--------------|
| Sintaxis | Decoradores simples | API explícita |
| Curva de aprendizaje | Baja | Media |
| Flexibilidad | Media | Alta |
| Código generado | Más conciso | Más verbose |
| Recomendado para | Mayoría de casos | Personalización avanzada |

---

## Configuración

### Archivo de configuración del servidor generado

```yaml
# config/config.yaml
service_name: user_management
base_url: https://api.enterprise.com/v2
timeout: 30
environment: production
log_level: INFO

retry:
  max_retries: 3
  backoff_factor: 0.5
  retry_statuses:
    - 429
    - 500
    - 502
    - 503
    - 504

auth:
  type: bearer  # none, api_key, bearer, basic, oauth2
```

### Variables de entorno

```bash
# .env
BASE_URL=https://api.enterprise.com/v2
TIMEOUT=30
LOG_LEVEL=INFO
ENVIRONMENT=production

# Autenticación
API_KEY=your_api_key
AUTH_TOKEN=your_bearer_token
```

---

## Procesamiento Batch

Genera servidores para múltiples microservicios:

```yaml
# batch-config.yaml
output_dir: ./output

services:
  - name: users
    spec: ./specs/users-api.yaml
    base_url: https://users.api.com

  - name: orders
    spec: ./specs/orders-api.yaml
    base_url: https://orders.api.com
```

```bash
openapi-to-mcp batch ./batch-config.yaml
```

---

## Integración con Claude Desktop

### Configuración básica

```json
{
  "mcpServers": {
    "user_management": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/mcp_server_user_management",
      "env": {
        "BASE_URL": "https://api.enterprise.com/v2",
        "AUTH_TOKEN": "your_token"
      }
    }
  }
}
```

---

## Enterprise Features

### Configuración de Entorno

El sistema usa Pydantic Settings para configuración centralizada. Copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

**Feature Toggles** - Activa solo los módulos que necesites:

```env
ENABLE_AI=true       # Integración Ollama (análisis IA)
ENABLE_STORAGE=true  # MinIO (almacenamiento S3)
ENABLE_OAUTH2=true   # OAuth2 token management
ENABLE_AGENTS=true   # Multi-agent architecture (futuro)
```

**Levantar servicios de desarrollo:**

```bash
# Inicia PostgreSQL, Redis, MinIO y Ollama
docker-compose -f docker-compose.dev.yml up -d

# Verificar estado
curl http://localhost:5000/api/features
```

Respuesta de `/api/features`:
```json
{
  "ai": {"enabled": true, "ollama_url": "http://localhost:11434"},
  "storage": {"enabled": true, "endpoint": "localhost:9000"},
  "oauth2": {"enabled": false, "configured": false},
  "agents": {"enabled": false},
  "database": {"type": "sqlite"}
}
```

### Integración IA (Ollama)

Usa modelos LLM locales via Ollama para 6 tipos de tareas:

| Tarea | Modelo Default | Endpoint |
|-------|---------------|----------|
| Análisis de Spec | `llama3.2:3b` | `POST /api/ai/analyze-spec` |
| Generación de Docs | `llama3.2:3b` | `POST /api/ai/generate-docs` |
| Auditoría de Seguridad | `llama3.2:3b` | `POST /api/ai/security-audit` |
| Validación de Código | `llama3.2:1b` | `POST /api/ai/validate` |
| Optimización de Spec | `codellama:7b` | `POST /api/ai/optimize` |
| Mejoras MCP | `codellama:7b` | `POST /api/ai/enhance-mcp` |

**Ejemplo - Analizar una spec con IA:**

```bash
curl -X POST http://localhost:5000/api/ai/analyze-spec \
  -H "Content-Type: application/json" \
  -d '{"spec_content": "openapi: 3.0.3\ninfo:\n  title: My API..."}'
```

Respuesta:
```json
{
  "analysis": {
    "quality_score": 78,
    "summary": "REST API with user management endpoints",
    "total_endpoints": 12,
    "issues": [
      {"severity": "warning", "path": "/users", "message": "Missing pagination"}
    ],
    "mcp_recommendations": {
      "priority_endpoints": ["/users", "/orders"],
      "suggested_tools": ["list_users", "create_order"]
    }
  },
  "model": "llama3.2:3b",
  "tokens_used": 1250,
  "duration_ms": 3400
}
```

**Configuración de modelos:**

```env
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL_SPEC_ANALYSIS=llama3.2:3b
OLLAMA_MODEL_CODE_GENERATION=codellama:7b
OLLAMA_MODEL_DOCUMENTATION=llama3.2:3b
OLLAMA_MODEL_VALIDATION=llama3.2:1b
OLLAMA_RATE_LIMIT_RPM=30
```

### Almacenamiento (MinIO)

Almacenamiento S3-compatible para artefactos con 4 buckets dedicados:

| Bucket | Contenido | Uso |
|--------|-----------|-----|
| `openapi-specs` | Especificaciones OpenAPI | Versionado de specs |
| `mcp-artifacts` | Servidores MCP generados (ZIP) | Distribución de artefactos |
| `reports` | Reportes generados (JSON/CSV/HTML) | Auditoría y compliance |
| `backups` | Backups de base de datos | Disaster recovery |

**Ejemplo - Subir un archivo:**

```bash
curl -X POST http://localhost:5000/api/storage/upload \
  -F "file=@mi-api.yaml" \
  -F "bucket=openapi-specs" \
  -F "key=project1/v1/api.yaml"
```

**Ejemplo - Listar objetos:**

```bash
curl http://localhost:5000/api/storage/objects/openapi-specs?prefix=project1/
```

**Fallback local**: Si MinIO no está disponible o `ENABLE_STORAGE=false`, el sistema usa almacenamiento en filesystem local automáticamente (`output/storage/`).

**Configuración:**

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

### OAuth2 Authentication

Gestión centralizada de tokens OAuth2 para propagar autenticación a los servidores MCP generados.

**Flujo:**

```
1. Registrar proveedor → GET /api/auth/oauth2/authorize/{provider}
2. Usuario autoriza     → Redirect a authorization_url
3. Callback con code    → GET /api/auth/oauth2/callback?code=...
4. Token almacenado     → Auto-refresh antes de expiración
5. MCP Context          → GET /api/auth/oauth2/mcp-context/{provider}/{user}
```

**Características:**
- OIDC Discovery automático (`.well-known/openid-configuration`)
- Token stores: Memory (default) o Redis (producción)
- Refresh automático con buffer configurable (300s antes de expiración)
- Contexto de auth inyectable en servidores MCP generados

**Configuración:**

```env
OAUTH2_ISSUER=https://your-domain.auth0.com
OAUTH2_CLIENT_ID=your-client-id
OAUTH2_CLIENT_SECRET=your-client-secret
OAUTH2_REDIRECT_URI=http://localhost:5000/api/auth/oauth2/callback
OAUTH2_TOKEN_STORE=redis
OAUTH2_REFRESH_BUFFER=300
```

### Auditoría de Acciones

Sistema completo de audit logging con 26 tipos de eventos y 4 niveles de severidad.

**Tipos de eventos auditados:**

| Categoría | Eventos | Severidad |
|-----------|---------|-----------|
| **Autenticación** | LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, PASSWORD_CHANGED | LOW - HIGH |
| **Usuarios** | USER_CREATED, USER_UPDATED, USER_DELETED, ROLE_CHANGED | MEDIUM - HIGH |
| **Specs** | SPEC_UPLOADED, SPEC_UPDATED, SPEC_DELETED, SPEC_ENCRYPTED | LOW - MEDIUM |
| **Generación** | MCP_GENERATED, CONFIG_CHANGED | LOW |
| **Integraciones** | WEBHOOK_CREATED, DATA_EXPORTED, API_KEY_CREATED | MEDIUM |
| **Admin** | SETTINGS_CHANGED, WORKSPACE_CREATED, RETENTION_EXECUTED | HIGH - CRITICAL |

**Ejemplo - Consultar logs de auditoría:**

```bash
# Obtener logs filtrados por severidad y rango de fechas
curl "http://localhost:5000/api/audit/logs?severity=HIGH&days=7&limit=50"

# Exportar logs en CSV
curl "http://localhost:5000/api/audit/export?format=csv&start_date=2025-01-01"

# Resumen de auditoría (estadísticas)
curl "http://localhost:5000/api/audit/summary?workspace_id=1"
```

Respuesta de `/api/audit/summary`:
```json
{
  "total_events": 1523,
  "by_severity": {"LOW": 890, "MEDIUM": 412, "HIGH": 198, "CRITICAL": 23},
  "top_actions": [
    {"action": "SPEC_UPLOADED", "count": 342},
    {"action": "MCP_GENERATED", "count": 289}
  ],
  "active_users": 12
}
```

Cada registro incluye: usuario, workspace, IP, user agent, path del request y metadatos adicionales.

### Encriptación de Specs

Encriptación AES-256 para proteger especificaciones OpenAPI sensibles.

| Aspecto | Detalle |
|---------|---------|
| **Algoritmo** | AES-256 via Fernet (symmetric) |
| **Derivación de clave** | PBKDF2-SHA256, 480,000 iteraciones (OWASP) |
| **Salt** | 16 bytes aleatorios por spec |
| **Integridad** | Hash SHA-256 del contenido original |
| **Rotación** | Soporte para re-encriptar con nueva clave |

```bash
# Encriptar una spec
curl -X POST http://localhost:5000/api/encryption/encrypt \
  -H "Content-Type: application/json" \
  -d '{"spec_id": 1, "password": "mi-clave-segura"}'

# Desencriptar
curl -X POST http://localhost:5000/api/encryption/decrypt \
  -H "Content-Type: application/json" \
  -d '{"spec_id": 1, "password": "mi-clave-segura"}'

# Rotar clave
curl -X POST http://localhost:5000/api/encryption/rotate \
  -H "Content-Type: application/json" \
  -d '{"spec_id": 1, "old_password": "clave-vieja", "new_password": "clave-nueva"}'
```

### Alertas Configurables

Sistema de alertas con 10 tipos, thresholds configurables y notificaciones multi-canal.

**Tipos de alerta disponibles:**

| Tipo | Descripción | Ejemplo de Threshold |
|------|-------------|---------------------|
| `FAILED_LOGINS` | Intentos de login fallidos | > 5 en 15 min |
| `HIGH_ERROR_RATE` | Tasa de errores elevada | > 10 en 5 min |
| `UNUSUAL_ACTIVITY` | Actividad inusual detectada | > 100 en 1 hora |
| `API_RATE_LIMIT` | Límite de API alcanzado | > 1000 en 1 hora |
| `STORAGE_USAGE` | Uso de almacenamiento alto | > 80% capacidad |
| `INACTIVE_USERS` | Usuarios inactivos | Sin actividad 30 días |
| `WEBHOOK_FAILURES` | Fallos en webhooks | > 3 en 1 hora |
| `ENCRYPTION_EVENTS` | Eventos de encriptación | > 10 en 5 min |
| `ADMIN_ACTIONS` | Acciones administrativas | Cualquier acción |
| `NEW_USER_SPIKE` | Pico de nuevos usuarios | > 10 en 1 hora |

**Ciclo de vida:** ACTIVE -> ACKNOWLEDGED -> RESOLVED (o SNOOZED temporalmente)

```bash
# Crear regla de alerta
curl -X POST http://localhost:5000/api/alerts/rules \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "FAILED_LOGINS",
    "severity": "HIGH",
    "threshold": 5,
    "period_minutes": 15,
    "channels": ["email", "webhook"],
    "cooldown_minutes": 60,
    "workspace_id": 1
  }'

# Listar alertas activas
curl "http://localhost:5000/api/alerts?status=ACTIVE&severity=HIGH"

# Reconocer una alerta
curl -X POST http://localhost:5000/api/alerts/42/acknowledge

# Resolver una alerta
curl -X POST http://localhost:5000/api/alerts/42/resolve
```

### Reportes Automáticos

8 tipos de reportes en 3 formatos con scheduling automático.

**Tipos de reporte:**

| Tipo | Contenido | Formatos |
|------|-----------|----------|
| `USAGE_SUMMARY` | Resumen de uso de la plataforma | JSON, CSV, HTML |
| `SECURITY_AUDIT` | Auditoría de seguridad con eventos y riesgos | JSON, CSV, HTML |
| `COMPLIANCE` | Cumplimiento de políticas y retención | JSON, CSV, HTML |
| `USER_ACTIVITY` | Actividad por usuario con métricas | JSON, CSV, HTML |
| `GENERATION_STATS` | Estadísticas de generación MCP | JSON, CSV, HTML |
| `WORKSPACE_OVERVIEW` | Vista general de workspaces | JSON, CSV, HTML |
| `API_USAGE` | Uso de API keys y endpoints | JSON, CSV, HTML |
| `ALERT_SUMMARY` | Resumen de alertas y resoluciones | JSON, CSV, HTML |

**Scheduling:** Diario, Semanal o Mensual con entrega por email o webhook.

```bash
# Generar reporte manualmente
curl -X POST http://localhost:5000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"report_type": "SECURITY_AUDIT", "period_days": 30, "workspace_id": 1}'

# Programar reporte automático
curl -X POST http://localhost:5000/api/reports/scheduled \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "USAGE_SUMMARY",
    "format": "HTML",
    "schedule": "WEEKLY",
    "workspace_id": 1,
    "delivery_email": "admin@empresa.com"
  }'

# Exportar reporte en formato específico
curl "http://localhost:5000/api/reports/generated/15/export?format=csv"

# Listar reportes generados
curl "http://localhost:5000/api/reports/generated?workspace_id=1&limit=20"
```

### Dashboard de Métricas

Dashboard de administración con métricas en tiempo real.

**Categorías de métricas:**

| Categoría | Datos | Endpoint |
|-----------|-------|----------|
| **Overview** | Usuarios totales, workspaces activos, specs cargadas | `GET /api/metrics/overview` |
| **Usuarios** | Distribución por rol, nuevos por día, más activos | `GET /api/metrics/users` |
| **Actividad** | Acciones por tipo, distribución horaria, trending | `GET /api/metrics/activity` |
| **Generación** | MCPs por día, por framework, tendencias | `GET /api/metrics/generations` |
| **Seguridad** | Logins fallidos, eventos críticos, IPs sospechosas | `GET /api/metrics/security` |
| **Workspaces** | Distribución por tamaño, webhooks activos | `GET /api/metrics/workspaces` |
| **Dashboard completo** | Todas las métricas agregadas | `GET /api/metrics/dashboard` |

```bash
# Dashboard completo
curl http://localhost:5000/api/metrics/dashboard

# Métricas de seguridad
curl http://localhost:5000/api/metrics/security
```

Respuesta de `/api/metrics/security`:
```json
{
  "failed_logins_24h": 3,
  "successful_logins_24h": 47,
  "high_severity_events": 5,
  "critical_events": 0,
  "suspicious_ips": ["192.168.1.100"],
  "by_severity": {"LOW": 120, "MEDIUM": 34, "HIGH": 5, "CRITICAL": 0}
}
```

### Políticas de Retención de Datos

Sistema configurable de retención para 9 tipos de datos con cleanup automático.

**Retención por defecto:**

| Tipo de Dato | Retención Default | Acciones Disponibles |
|-------------|-------------------|---------------------|
| `AUDIT_LOGS` | 365 días | DELETE, ARCHIVE, ANONYMIZE |
| `SPECS` | 730 días | DELETE, ARCHIVE |
| `GENERATIONS` | 180 días | DELETE, ARCHIVE |
| `SESSIONS` | 1 día | DELETE |
| `ENCRYPTED_SPECS` | 365 días | DELETE |
| `ACTIVITY_LOGS` | 180 días | DELETE, ANONYMIZE |
| `API_KEYS` | 365 días (inactivas) | DELETE |
| `WEBHOOKS` | 365 días (inactivos) | DELETE |
| `NOTIFICATIONS` | 90 días | DELETE |

```bash
# Configurar política de retención
curl -X POST http://localhost:5000/api/retention/policies \
  -H "Content-Type: application/json" \
  -d '{
    "data_type": "AUDIT_LOGS",
    "retention_days": 180,
    "action": "ARCHIVE",
    "workspace_id": 1
  }'

# Ejecutar cleanup (dry-run primero)
curl -X POST http://localhost:5000/api/retention/execute \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": 1, "dry_run": true}'

# Ver estadísticas de retención
curl "http://localhost:5000/api/retention/stats?workspace_id=1"

# Historial de ejecuciones
curl "http://localhost:5000/api/retention/history?workspace_id=1"
```

### Configuración de Base de Datos

Soporte para 3 tipos de base de datos con configuración via variables de entorno.

| Base de Datos | Uso Recomendado | Connection Pooling |
|--------------|-----------------|-------------------|
| **SQLite** | Desarrollo, pruebas, instalaciones pequeñas | No (archivo local) |
| **PostgreSQL** | Producción, equipos, alta concurrencia | Pool de 5, max overflow 10 |
| **MongoDB** | Almacenamiento de documentos, logs de alto volumen | Nativo |

**SQLite (default):**
```env
DATABASE_TYPE=sqlite
# Usa archivo local en output/instance/app.db
```

**PostgreSQL:**
```env
DATABASE_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=openapi_mcp
DB_USER=postgres
DB_PASSWORD=your-password
# O usando URL directa:
# DATABASE_URL=postgresql://user:pass@localhost:5432/openapi_mcp
```

**MongoDB:**
```env
DATABASE_TYPE=mongodb
DATABASE_URL=mongodb://user:pass@localhost:27017/openapi_mcp
```

```bash
# Verificar salud de la base de datos
curl http://localhost:5000/api/health

# Información detallada
curl http://localhost:5000/api/database/info
```

Respuesta de `/api/database/info`:
```json
{
  "type": "postgresql",
  "url_masked": "postgresql://***@localhost:5432/openapi_mcp",
  "healthy": true,
  "server_version": "16.1",
  "database_size": "24 MB"
}
```

---

## API Reference

### Endpoints por Módulo

#### Core (siempre disponibles)

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check general |
| `GET` | `/api/features` | Estado de feature toggles |
| `GET` | `/api/database/info` | Información de base de datos |
| `GET` | `/api/database/types` | Tipos de DB disponibles |

#### AI (`ENABLE_AI=true`)

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/ai/health` | Estado de Ollama |
| `GET` | `/api/ai/models` | Modelos disponibles |
| `POST` | `/api/ai/analyze-spec` | Analizar spec OpenAPI |
| `POST` | `/api/ai/generate-docs` | Generar documentación |
| `POST` | `/api/ai/security-audit` | Auditoría de seguridad IA |
| `POST` | `/api/ai/validate` | Validar código MCP |
| `POST` | `/api/ai/optimize` | Optimizar spec |
| `POST` | `/api/ai/enhance-mcp` | Sugerir mejoras MCP |

#### Storage (`ENABLE_STORAGE=true`)

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/storage/health` | Estado del storage |
| `GET` | `/api/storage/buckets` | Listar buckets |
| `GET` | `/api/storage/objects/{bucket}` | Listar objetos |
| `POST` | `/api/storage/upload` | Subir archivo |
| `GET` | `/api/storage/download/{bucket}/{key}` | Descargar objeto |
| `DELETE` | `/api/storage/delete/{bucket}/{key}` | Eliminar objeto |
| `GET` | `/api/storage/presigned/{bucket}/{key}` | URL pre-firmada |

#### OAuth2 (`ENABLE_OAUTH2=true`)

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/auth/oauth2/providers` | Proveedores registrados |
| `GET` | `/api/auth/oauth2/authorize/{provider}` | URL de autorización |
| `GET` | `/api/auth/oauth2/callback` | Callback OAuth2 |
| `GET` | `/api/auth/oauth2/token/{provider}/{user}` | Estado de token |
| `GET` | `/api/auth/oauth2/mcp-context/{provider}/{user}` | Contexto auth MCP |

#### Auditoría

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/audit/logs` | Consultar logs (filtros: user, severity, action, days) |
| `GET` | `/api/audit/export` | Exportar logs en JSON o CSV |
| `GET` | `/api/audit/summary` | Estadísticas de auditoría |

#### Alertas

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/alerts` | Listar alertas (filtros: status, severity, type) |
| `POST` | `/api/alerts/rules` | Crear regla de alerta |
| `GET` | `/api/alerts/rules` | Listar reglas activas |
| `DELETE` | `/api/alerts/rules/{id}` | Eliminar regla |
| `POST` | `/api/alerts/{id}/acknowledge` | Reconocer alerta |
| `POST` | `/api/alerts/{id}/resolve` | Resolver alerta |
| `POST` | `/api/alerts/{id}/snooze` | Silenciar temporalmente |
| `POST` | `/api/alerts/check` | Ejecutar verificación de reglas |

#### Reportes

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/reports/generate` | Generar reporte manualmente |
| `GET` | `/api/reports/generated` | Listar reportes generados |
| `GET` | `/api/reports/generated/{id}` | Obtener reporte específico |
| `GET` | `/api/reports/generated/{id}/export` | Exportar en formato (json/csv/html) |
| `POST` | `/api/reports/scheduled` | Crear reporte programado |
| `GET` | `/api/reports/scheduled` | Listar reportes programados |
| `DELETE` | `/api/reports/scheduled/{id}` | Eliminar programación |
| `POST` | `/api/reports/run-scheduled` | Ejecutar reportes pendientes |
| `GET` | `/api/reports/types` | Tipos de reporte disponibles |

#### Métricas

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/metrics/overview` | Métricas generales de la plataforma |
| `GET` | `/api/metrics/users` | Métricas de usuarios |
| `GET` | `/api/metrics/activity` | Métricas de actividad |
| `GET` | `/api/metrics/generations` | Métricas de generación MCP |
| `GET` | `/api/metrics/security` | Métricas de seguridad |
| `GET` | `/api/metrics/workspaces` | Métricas de workspaces |
| `GET` | `/api/metrics/dashboard` | Dashboard completo (todas las métricas) |

#### Retención

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/retention/policies` | Listar políticas de retención |
| `POST` | `/api/retention/policies` | Crear/actualizar política |
| `DELETE` | `/api/retention/policies/{id}` | Eliminar política |
| `POST` | `/api/retention/execute` | Ejecutar cleanup (soporta dry_run) |
| `GET` | `/api/retention/stats` | Estadísticas de retención |
| `GET` | `/api/retention/history` | Historial de ejecuciones |

#### Encriptación

| Method | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/encryption/encrypt` | Encriptar spec con password |
| `POST` | `/api/encryption/decrypt` | Desencriptar spec |
| `POST` | `/api/encryption/rotate` | Rotar clave de encriptación |
| `POST` | `/api/encryption/verify` | Verificar password sin desencriptar |

---

## Arquitectura

### Flujo de generación

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenAPI Specification                         │
│                    (YAML/JSON 3.0/3.1)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OpenAPI Parser                              │
│  - Validación de spec                                           │
│  - Resolución de $refs                                          │
│  - Extracción de paths, schemas, security                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Endpoint Selector                             │
│  - Filtrado por patrones CLI                                    │
│  - Selección interactiva                                        │
│  - Selección via GUI web                                        │
│  - Carga desde archivo o URL                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    Tool Transformer     │     │  Resource Transformer   │
└─────────────────────────┘     └─────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Generator                          │
│  - Genera código server.py (FastMCP o MCP)                      │
│  - Crea http_client.py, auth.py, config.py                      │
│  - Genera requirements.txt, Dockerfile, README                  │
│  - Opcionalmente crea ZIP para descarga                         │
└─────────────────────────────────────────────────────────────────┘
```

### Estructura del proyecto

```
openapi-to-mcp-generator/
├── src/
│   └── openapi_to_mcp/
│       ├── models.py              # Modelos de datos
│       ├── cli.py                 # Interfaz de comandos
│       ├── endpoint_selector.py   # Selector de endpoints
│       ├── config/                # ⚙️ Configuración centralizada
│       │   ├── __init__.py
│       │   └── settings.py        # Pydantic Settings (Ollama, MinIO, OAuth2)
│       ├── ai/                    # 🤖 Integración IA
│       │   ├── __init__.py
│       │   └── ollama_client.py   # Cliente Ollama (6 tareas IA)
│       ├── auth/                  # 🔐 Autenticación
│       │   ├── __init__.py
│       │   └── oauth2.py          # OAuth2 Manager + Token Stores
│       ├── storage/               # 📦 Almacenamiento
│       │   ├── __init__.py
│       │   └── adapters/
│       │       ├── base.py        # Interfaz StorageAdapter
│       │       ├── local_adapter.py
│       │       └── minio_adapter.py
│       ├── parsers/
│       │   └── openapi_parser.py
│       ├── transformers/
│       │   ├── tool_transformer.py
│       │   └── resource_transformer.py
│       ├── generators/
│       │   └── server_generator.py
│       └── gui/                   # Interfaz web
│           ├── web_app.py         # 80+ API endpoints
│           ├── db_config.py       # Multi-database config
│           ├── database.py        # SQLAlchemy models
│           ├── audit.py           # Audit logging
│           ├── encryption.py      # AES-256 encryption
│           ├── retention.py       # Data retention
│           ├── metrics.py         # Usage metrics
│           ├── alerts.py          # Configurable alerts
│           ├── reports.py         # Automatic reports
│           ├── templates/
│           │   ├── index.html     # Selector de endpoints
│           │   ├── upload.html    # Página de carga
│           │   ├── admin.html     # Dashboard admin
│           │   └── login.html     # Autenticación
│           └── static/
│               ├── style.css
│               └── app.js
├── .env.example                   # Variables de entorno
├── Dockerfile
├── docker-compose.yml             # Producción
├── docker-compose.dev.yml         # Desarrollo (PostgreSQL, Redis, MinIO, Ollama)
├── docker-entrypoint.sh
├── examples/
├── tests/
└── pyproject.toml
```

---

## Mapeo OpenAPI → MCP

### Operaciones → Tools

| OpenAPI | MCP Tool |
|---------|----------|
| `GET /users` | `prefix_list_users` |
| `POST /users` | `prefix_create_user` |
| `GET /users/{id}` | `prefix_get_user_by_id` |
| `PUT /users/{id}` | `prefix_update_user` |
| `DELETE /users/{id}` | `prefix_delete_user` |

### Parámetros → JSON Schema

| OpenAPI | MCP Input Schema |
|---------|------------------|
| `path: id` | `{"id": {"type": "integer", "description": "..."}}` |
| `query: search` | `{"search": {"type": "string", ...}}` |
| `header: X-Custom` | `{"x_custom": {"type": "string", ...}}` |
| `requestBody` | `{"body": {"type": "object", ...}}` |

---

## Ejemplos

### Uso programático

```python
from openapi_to_mcp import (
    OpenAPIParser,
    ToolTransformer,
    ResourceTransformer,
    MCPServerGenerator,
    MCPServerConfig,
    MCPFramework,
    EndpointFilter,
)

# 1. Parsear especificación
parser = OpenAPIParser()
spec = parser.parse("api.yaml")

# 2. Filtrar endpoints
endpoint_filter = EndpointFilter(
    include_patterns=["/users/*", "/orders/*"],
    exclude_patterns=["/internal/*"]
)

# 3. Transformar y generar
transformer = ToolTransformer(service_prefix="myapi")
tools = transformer.transform(spec, endpoint_filter=endpoint_filter)

config = MCPServerConfig(
    service_name="my_service",
    mcp_framework=MCPFramework.FASTMCP,
)

generator = MCPServerGenerator(output_dir="./output")
result = generator.generate(spec, tools, resources, config)
```

### Comandos CLI útiles

```bash
# Validar especificación OpenAPI
openapi-to-mcp validate ./api.yaml

# Vista previa de tools y resources
openapi-to-mcp preview ./api.yaml --service-prefix myapi

# Modo verbose para debugging
openapi-to-mcp -v generate ./api.yaml -n myservice

# Iniciar servidor web standalone
openapi-to-mcp serve --port 8080
```

---

## Consideraciones

### Limitaciones conocidas

1. **WebSockets/SSE**: Streaming no soportado actualmente
2. **File uploads**: Multipart form-data requiere manejo especial
3. **GraphQL**: No soportado, solo REST
4. **Ollama requerido**: Las features de IA necesitan Ollama ejecutándose localmente
5. **SAML/LDAP**: Solo OAuth2/OIDC soportado actualmente (SAML en backlog)

### Buenas prácticas

1. **Usa operationId**: Define `operationId` en tu OpenAPI para nombres de tools más legibles
2. **Documenta**: Incluye `summary` y `description` en cada operación
3. **Versiona**: Usa prefijos de versión (`users_v2_*`) cuando las APIs evolucionan
4. **Filtra**: No expongas endpoints internos o de debug a los LLMs
5. **Feature Toggles**: Activa solo los módulos que necesites en `.env`
6. **Token Security**: En producción, usa Redis como token store (`OAUTH2_TOKEN_STORE=redis`)
7. **MinIO en producción**: Configura `MINIO_SECURE=true` y credenciales seguras

---

## 🗺️ Roadmap

### Fase 1: Mejoras de Experiencia de Usuario (v1.1) ✅ COMPLETADA

#### 🌙 Modo Oscuro/Claro ✅
- [x] Toggle de tema en la interfaz web
- [x] Persistencia de preferencia en localStorage
- [x] Detección automática de preferencia del sistema

#### ✅ Validación en Tiempo Real ✅
- [x] Validación del OpenAPI spec mientras se carga
- [x] Indicadores visuales de errores y warnings
- [x] Sugerencias de corrección automática
- [x] Panel de diagnóstico con detalles de problemas

#### 👁️ Preview en Vivo ✅
- [x] Vista previa del código MCP generado antes de descargar
- [x] Syntax highlighting para Python
- [x] Navegación por archivos generados
- [x] Diff viewer para comparar versiones

#### 📊 Estadísticas Avanzadas ✅
- [x] Dashboard con métricas de uso
- [x] Gráficos de endpoints más utilizados
- [x] Historial de especificaciones recientes (últimas 10)
- [x] Tiempo promedio de generación

#### 🎯 Performance & DX ✅ NUEVO
- [x] Cleanup automático de archivos temporales
- [x] Limpieza de sesiones expiradas (>2 horas)
- [x] Progress bars detallados (10 pasos)
- [x] Mensajes de error mejorados con contexto y sugerencias
- [x] Links a documentación en errores

#### 🎨 UI/UX Improvements ✅ NUEVO
- [x] Toast notifications (success, error, warning, info)
- [x] Drag & drop para upload de archivos
- [x] Recent specs list con reload rápido
- [x] Export/Import de configuración de selección
- [x] Gestión de presets (guardar/cargar selecciones)
- [x] Mobile responsive design

---

### Fase 2: Gestión de Especificaciones (v1.2) ✅ COMPLETADA

#### 📁 Administrador de Especificaciones OpenAPI ✅
- [x] Biblioteca de especificaciones cargadas
- [x] Organización por proyectos/carpetas
- [x] Búsqueda y filtrado de especificaciones
- [x] Etiquetado y categorización
- [x] Favoritos y accesos rápidos

#### 🔄 Versionado de Especificaciones ✅
Sistema completo de control de versiones para OpenAPI specs:

| Característica | Descripción | Estado |
|---------------|-------------|---------|
| **Historial de versiones** | Registro automático de cada versión cargada | ✅ |
| **Timeline visual** | Línea de tiempo interactiva con todas las versiones | ✅ |
| **Diff entre versiones** | Comparación visual de cambios entre versiones | ✅ |
| **Restaurar versiones** | Capacidad de volver a versiones anteriores | ✅ |
| **Notas de cambio** | Comentarios y descripciones por versión | ✅ |

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Petstore API - Historial de Versiones                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ●───●───●───●───◉  (Timeline)                                  │
│  v1  v2  v3  v4  v5                                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ v5 (actual) - 2024-01-15 14:32                          │   │
│  │ ├─ 🔧 MCP generado: 2024-01-15 14:35                    │   │
│  │ ├─ Endpoints: 24 (+3 desde v4)                          │   │
│  │ └─ Nota: "Agregados endpoints de autenticación OAuth"   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ v4 - 2024-01-10 09:15                                   │   │
│  │ ├─ 🔧 MCP generado: 2024-01-10 09:20                    │   │
│  │ ├─ 🔧 MCP generado: 2024-01-12 16:45                    │   │
│  │ ├─ Endpoints: 21                                        │   │
│  │ └─ Nota: "Refactoring de rutas de usuarios"             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Ver Diff v4 ↔ v5]  [Restaurar v4]  [Exportar Historial]      │
└─────────────────────────────────────────────────────────────────┘
```

#### 🔧 Registro de Generaciones MCP ✅
- [x] Indicador visual de versiones con MCP generado
- [x] Fecha y hora exacta de cada generación
- [x] Configuración utilizada en cada generación
- [x] Enlace de descarga del ZIP generado (si está disponible)
- [x] Estadísticas de generación (tools, resources, tiempo)

---

### Fase 3: Configuración Avanzada de MCP (v1.3) ✅ COMPLETADA

#### ⚙️ Zona de Configuración por Especificación ✅
Cada especificación tiene su propia configuración de salida MCP:

**Modo Editor (YAML/JSON):**
```yaml
# Configuración directa en formato YAML
service_name: "petstore_api"
mcp_framework: "fastmcp"
output_format: "python"
service_prefix: "petstore"
generate_resources: true
auth_config:
  type: "bearer"
  token_env: "PETSTORE_API_KEY"
endpoint_filters:
  include: ["/pets/*", "/store/*"]
  exclude: ["/internal/*"]
```

**Modo GUI (Formulario visual):**
```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ Configuración MCP - Petstore API                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Información General                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Nombre del servicio: [petstore_api_________]            │   │
│  │ Prefijo:             [petstore_____________]            │   │
│  │ Framework:           [FastMCP ▼]                        │   │
│  │ Formato salida:      ○ Python  ○ TypeScript (futuro)    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Autenticación                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Tipo:     [Bearer Token ▼]                              │   │
│  │ Variable: [PETSTORE_API_KEY___]                         │   │
│  │ □ Requerido para todos los endpoints                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Generación                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☑ Generar Resources                                     │   │
│  │ ☑ Incluir validación de parámetros                      │   │
│  │ ☑ Generar documentación inline                          │   │
│  │ □ Modo estricto (fallar en warnings)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Modo Editor YAML]  [Guardar Config]  [Restaurar Defaults]    │
└─────────────────────────────────────────────────────────────────┘
```

- [x] Toggle entre modo Editor y modo GUI
- [x] Validación de configuración en tiempo real
- [x] Perfiles de configuración reutilizables (4 perfiles por defecto)
- [x] Importar/Exportar configuraciones (YAML/JSON)
- [x] Aplicar perfiles a especificaciones existentes

---

### Fase 4: Colaboración y Equipos (v2.0) ✅

#### 👥 Gestión de Usuarios
- [x] Sistema de autenticación (local/OAuth)
- [x] Roles y permisos (admin, editor, viewer)
- [x] Workspaces compartidos
- [x] Actividad de equipo en tiempo real

#### 🔗 Integraciones
- [x] Webhooks para CI/CD
- [x] API REST para automatización
- [x] Integración con GitHub/GitLab
- [x] Sincronización con repositorios de specs
- [x] Notificaciones (Slack, Discord, Email)

#### 📤 Export Avanzado
- [x] Generación de código TypeScript (MCP SDK oficial)
- [x] Templates personalizables (Jinja2)
- [ ] Plugins de exportación
- [x] Generación batch de múltiples specs

---

### Fase 5: Enterprise Features (v3.0) ✅

#### 🔒 Seguridad Avanzada
- [x] Auditoría de acciones (45 tipos de eventos, 4 niveles de severidad)
- [x] Encriptación de specs sensibles (AES-256 con Fernet, PBKDF2)
- [x] OAuth2/OIDC integration (OIDC Discovery, token management, refresh automático)
- [x] Políticas de retención de datos (9 tipos de datos, cleanup automático)

#### 📈 Analytics y Monitoreo
- [x] Dashboard de administración (métricas completas)
- [x] Métricas de uso por equipo (usuarios, actividad, workspaces)
- [x] Alertas configurables (10 tipos, thresholds, notificaciones)
- [x] Reportes automáticos (8 tipos, 3 formatos, scheduling)

#### 🌐 Escalabilidad
- [ ] Soporte multi-tenant
- [ ] Balanceo de carga
- [x] Cache distribuido (Redis como backend de cache y token store)
- [x] Base de datos persistente (PostgreSQL/MongoDB via db_config)

---

### Fase 6: AI & Cloud Infrastructure (v4.0) ✅

#### 🤖 Integración Ollama (LLM Local)
- [x] Cliente Ollama con rate limiting y manejo de errores
- [x] Análisis inteligente de specs OpenAPI (quality score, issues, recomendaciones MCP)
- [x] Generación automática de documentación MCP
- [x] Auditoría de seguridad asistida por IA (OWASP compliance)
- [x] Validación de código MCP generado
- [x] Optimización de specs (paginación, caching, batching)
- [x] Sugerencias de mejoras para servidores MCP
- [x] Modelos configurables por tipo de tarea (spec analysis, code gen, docs, validation)
- [x] 7 endpoints de IA (`/api/ai/*`)

#### 📦 Almacenamiento MinIO (S3-Compatible)
- [x] Adaptador MinIO con abstracción de storage
- [x] Adaptador local (filesystem) como fallback
- [x] Buckets dedicados: specs, artifacts, reports, backups
- [x] URLs pre-firmadas para descargas seguras
- [x] Helpers de alto nivel: store_spec, store_mcp_artifact, store_report
- [x] 7 endpoints de storage (`/api/storage/*`)

#### 🔐 OAuth2 Token Management
- [x] Gestor centralizado de tokens OAuth2
- [x] OIDC Discovery automático
- [x] Token stores: Memory y Redis
- [x] Refresh automático de tokens
- [x] Propagación de contexto auth a servidores MCP
- [x] 5 endpoints OAuth2 (`/api/auth/oauth2/*`)

#### ⚙️ Infraestructura
- [x] Configuración centralizada con Pydantic Settings
- [x] Feature toggles: `ENABLE_AI`, `ENABLE_STORAGE`, `ENABLE_OAUTH2`, `ENABLE_AGENTS`
- [x] `.env.example` con todas las variables de entorno
- [x] `docker-compose.dev.yml` (PostgreSQL, Redis, MinIO, Ollama)
- [x] Endpoint de estado de features (`/api/features`)

---

### Backlog (Sin priorizar)

| Feature | Descripción | Complejidad |
|---------|-------------|-------------|
| Importar desde Postman | Convertir colecciones Postman a OpenAPI | Media |
| Importar desde Insomnia | Soporte para formato Insomnia | Media |
| ~~AI-assisted mapping~~ | ~~Sugerencias inteligentes para nombres de tools~~ | ✅ Fase 6 |
| Playground integrado | Probar tools generados directamente | Alta |
| CLI interactivo mejorado | TUI con rich/textual | Media |
| Soporte GraphQL | Generar MCP desde schemas GraphQL | Alta |
| Soporte gRPC | Generar MCP desde protobuf | Alta |
| Mobile app | App iOS/Android para gestión | Alta |
| VS Code extension | Extensión para editar specs | Media |
| ~~Rate limiting~~ | ~~Control de uso de API~~ | ✅ Fase 6 (Ollama) |
| Multi-Agent Architecture | Agentes Architect + Coder para planificación IA | Alta |
| Dynamic MCP Generation | Generación dinámica con features IA personalizadas | Alta |
| Soporte multi-tenant | Aislamiento completo por organización | Alta |
| SAML/LDAP Integration | SSO con proveedores enterprise (SAML, Active Directory) | Media |

---

### Contribuir al Roadmap

¿Tienes ideas para nuevas features?

1. Abre un [Issue](https://github.com/tu-repo/openapi-to-mcp-generator/issues) con la etiqueta `enhancement`
2. Describe el caso de uso y beneficios
3. Si es posible, incluye mockups o diagramas
4. Vota 👍 en features existentes para priorizar

---

## Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Instala dependencias de desarrollo: `pip install -e ".[dev]"`
4. Ejecuta tests: `pytest`
5. Commit cambios (`git commit -am 'Agregar funcionalidad'`)
6. Push a la rama (`git push origin feature/nueva-funcionalidad`)
7. Abre un Pull Request

---

## Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

Desarrollado para automatizar la integración de microservicios empresariales con LLMs mediante MCP.

**Stack tecnológico:** Python 3.10+ | Flask | SQLAlchemy | Pydantic | Ollama | MinIO | Redis | OAuth2/OIDC
