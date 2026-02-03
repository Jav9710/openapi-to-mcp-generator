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
9. [Arquitectura](#arquitectura)
10. [Mapeo OpenAPI → MCP](#mapeo-openapi--mcp)
11. [Ejemplos](#ejemplos)
12. [Consideraciones](#consideraciones)
13. [Contribuir](#contribuir)

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

### Docker Compose

```bash
# Iniciar el servicio
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

**docker-compose.yml:**

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

### Variables de entorno Docker

| Variable | Descripción | Default |
|----------|-------------|---------|
| `PORT` | Puerto del servidor | 5000 |
| `OUTPUT_DIR` | Directorio de salida | /app/output |
| `WORKERS` | Workers de gunicorn | 2 |
| `THREADS` | Threads por worker | 4 |

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
│       ├── parsers/
│       │   └── openapi_parser.py
│       ├── transformers/
│       │   ├── tool_transformer.py
│       │   └── resource_transformer.py
│       ├── generators/
│       │   └── server_generator.py
│       └── gui/                   # Interfaz web
│           ├── web_app.py
│           ├── templates/
│           │   ├── index.html     # Selector de endpoints
│           │   └── upload.html    # Página de carga
│           └── static/
│               ├── style.css
│               └── app.js
├── Dockerfile
├── docker-compose.yml
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

1. **OAuth2 interactivo**: Flujos que requieren navegador necesitan configuración manual
2. **WebSockets/SSE**: Streaming no soportado actualmente
3. **File uploads**: Multipart form-data requiere manejo especial
4. **GraphQL**: No soportado, solo REST

### Buenas prácticas

1. **Usa operationId**: Define `operationId` en tu OpenAPI para nombres de tools más legibles
2. **Documenta**: Incluye `summary` y `description` en cada operación
3. **Versiona**: Usa prefijos de versión (`users_v2_*`) cuando las APIs evolucionan
4. **Filtra**: No expongas endpoints internos o de debug a los LLMs

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
- [ ] Diff viewer para comparar versiones

#### 📊 Estadísticas Avanzadas ✅
- [x] Dashboard con métricas de uso
- [x] Gráficos de endpoints más utilizados
- [x] Historial de especificaciones recientes (últimas 10)
- [ ] Tiempo promedio de generación

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

### Fase 3: Configuración Avanzada de MCP (v1.3)

#### ⚙️ Zona de Configuración por Especificación
Cada especificación tendrá su propia configuración de salida MCP:

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

- [ ] Toggle entre modo Editor y modo GUI
- [ ] Validación de configuración en tiempo real
- [ ] Perfiles de configuración reutilizables
- [ ] Importar/Exportar configuraciones
- [ ] Configuración heredada de plantillas

---

### Fase 4: Colaboración y Equipos (v2.0)

#### 👥 Gestión de Usuarios
- [ ] Sistema de autenticación (local/OAuth)
- [ ] Roles y permisos (admin, editor, viewer)
- [ ] Workspaces compartidos
- [ ] Actividad de equipo en tiempo real

#### 🔗 Integraciones
- [ ] Webhooks para CI/CD
- [ ] API REST para automatización
- [ ] Integración con GitHub/GitLab
- [ ] Sincronización con repositorios de specs
- [ ] Notificaciones (Slack, Discord, Email)

#### 📤 Export Avanzado
- [ ] Generación de código TypeScript (MCP SDK oficial)
- [ ] Templates personalizables
- [ ] Plugins de exportación
- [ ] Generación batch de múltiples specs

---

### Fase 5: Enterprise Features (v3.0)

#### 🔒 Seguridad Avanzada
- [ ] Auditoría de acciones
- [ ] Encriptación de specs sensibles
- [ ] SSO/SAML integration
- [ ] Políticas de retención de datos

#### 📈 Analytics y Monitoreo
- [ ] Dashboard de administración
- [ ] Métricas de uso por equipo
- [ ] Alertas configurables
- [ ] Reportes automáticos

#### 🌐 Escalabilidad
- [ ] Soporte multi-tenant
- [ ] Balanceo de carga
- [ ] Cache distribuido
- [ ] Base de datos persistente (PostgreSQL/MongoDB)

---

### Backlog (Sin priorizar)

| Feature | Descripción | Complejidad |
|---------|-------------|-------------|
| Importar desde Postman | Convertir colecciones Postman a OpenAPI | Media |
| Importar desde Insomnia | Soporte para formato Insomnia | Media |
| AI-assisted mapping | Sugerencias inteligentes para nombres de tools | Alta |
| Playground integrado | Probar tools generados directamente | Alta |
| CLI interactivo mejorado | TUI con rich/textual | Media |
| Soporte GraphQL | Generar MCP desde schemas GraphQL | Alta |
| Soporte gRPC | Generar MCP desde protobuf | Alta |
| Mobile app | App iOS/Android para gestión | Alta |
| VS Code extension | Extensión para editar specs | Media |
| Rate limiting | Control de uso de API | Baja |

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
