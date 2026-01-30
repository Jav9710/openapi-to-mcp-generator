"""
Generador de código de servidor MCP.

Genera código Python completo para un servidor MCP funcional
a partir de tools y resources transformados.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import (
    GenerationResult,
    MCPFramework,
    MCPResource,
    MCPServerConfig,
    MCPTool,
    OpenAPISpec,
    SecurityScheme,
)

logger = logging.getLogger(__name__)


class MCPServerGenerator:
    """
    Generador de código Python para servidor MCP.

    Genera un proyecto completo con:
    - Servidor MCP con todas las tools
    - Handlers para cada operación
    - Sistema de autenticación
    - Configuración y scripts de despliegue

    Example:
        generator = MCPServerGenerator(output_dir="./output")
        result = generator.generate(
            spec=openapi_spec,
            tools=tools,
            resources=resources,
            config=config
        )
        print(f"Servidor generado en: {result.output_path}")
    """

    def __init__(
        self,
        output_dir: str | Path,
        templates_dir: str | Path | None = None,
    ):
        """
        Inicializa el generador.

        Args:
            output_dir: Directorio donde generar el código
            templates_dir: Directorio de templates Jinja2 (opcional)
        """
        self.output_dir = Path(output_dir)
        self.templates_dir = Path(templates_dir) if templates_dir else None

        # Configurar Jinja2
        self._setup_jinja_env()

    def _setup_jinja_env(self):
        """Configura el entorno Jinja2 para templates."""
        if self.templates_dir and self.templates_dir.exists():
            loader = FileSystemLoader(str(self.templates_dir))
        else:
            # Usar templates inline
            loader = None

        self.jinja_env = Environment(
            loader=loader,
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        ) if loader else None

    def generate(
        self,
        spec: OpenAPISpec,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> GenerationResult:
        """
        Genera el servidor MCP completo.

        Args:
            spec: Especificación OpenAPI parseada
            tools: Lista de tools transformadas
            resources: Lista de resources transformados
            config: Configuración del servidor
            progress_callback: Callback opcional (description, current, total) para reportar progreso

        Returns:
            GenerationResult con información de la generación
        """
        warnings = []
        errors = []

        def report_progress(description: str, step: int, total: int):
            """Helper para reportar progreso."""
            if progress_callback:
                progress_callback(description, step, total)

        total_steps = 10
        current_step = 0

        try:
            # Crear estructura de directorios
            current_step += 1
            report_progress("Creando estructura de proyecto", current_step, total_steps)
            server_dir = self._create_project_structure(config.service_name)

            # Generar archivos
            current_step += 1
            report_progress("Generando servidor MCP", current_step, total_steps)
            self._generate_server_file(server_dir, tools, resources, config, spec)

            current_step += 1
            report_progress("Generando cliente HTTP", current_step, total_steps)
            self._generate_http_client(server_dir, config)

            current_step += 1
            report_progress("Generando módulo de autenticación", current_step, total_steps)
            self._generate_auth_module(server_dir, spec.security_schemes, config)

            current_step += 1
            report_progress("Generando configuración", current_step, total_steps)
            self._generate_config_file(server_dir, config)

            current_step += 1
            report_progress("Generando requirements.txt", current_step, total_steps)
            self._generate_requirements(server_dir, config)

            current_step += 1
            report_progress("Generando pyproject.toml", current_step, total_steps)
            self._generate_pyproject(server_dir, config)

            current_step += 1
            report_progress("Generando Dockerfile", current_step, total_steps)
            self._generate_dockerfile(server_dir, config)

            current_step += 1
            report_progress("Generando documentación", current_step, total_steps)
            self._generate_readme(server_dir, spec, tools, resources, config)

            # Generar schemas como módulo
            current_step += 1
            report_progress("Generando módulo de schemas", current_step, total_steps)
            self._generate_schemas_module(server_dir, spec.components_schemas)

            logger.info(f"Servidor MCP generado exitosamente en: {server_dir}")

            return GenerationResult(
                success=True,
                output_path=str(server_dir),
                tools_generated=tools,
                resources_generated=resources,
                warnings=warnings,
                config=config,
            )

        except Exception as e:
            logger.error(f"Error generando servidor: {e}", exc_info=True)
            errors.append(str(e))

            return GenerationResult(
                success=False,
                output_path=str(self.output_dir),
                errors=errors,
                warnings=warnings,
            )

    def generate_preview(
        self,
        spec: OpenAPISpec,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
    ) -> dict[str, str]:
        """
        Genera preview del código sin escribir archivos.

        Args:
            spec: Especificación OpenAPI parseada
            tools: Lista de tools transformadas
            resources: Lista de resources transformados
            config: Configuración del servidor

        Returns:
            Diccionario con nombre de archivo como clave y contenido como valor
        """
        files = {}

        try:
            # Generar servidor principal (el más importante)
            files["src/server.py"] = self._render_server_template(tools, resources, config, spec)

            # Requirements
            files["requirements.txt"] = self._generate_requirements_code_preview(config)

            # README básico con información del servidor
            readme_content = f"""# MCP Server: {config.service_name}

Servidor MCP generado automáticamente desde OpenAPI.

## API
- **Título**: {spec.title}
- **Versión**: {spec.version}
- **Base URL**: {config.base_url}

## Tools Generadas ({len(tools)})
{chr(10).join(f'- `{t.name}`: {t.description[:80]}...' if len(t.description) > 80 else f'- `{t.name}`: {t.description}' for t in tools[:10])}
{'...' if len(tools) > 10 else ''}

## Resources Generados ({len(resources)})
{chr(10).join(f'- `{r.uri}`: {r.description[:60]}...' if len(r.description) > 60 else f'- `{r.uri}`: {r.description}' for r in resources[:5])}
{'...' if len(resources) > 5 else ''}

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python -m src.server
```

---
*Generado con OpenAPI-to-MCP Generator*
"""
            files["README.md"] = readme_content

            # Config básico
            config_content = f'''"""
Configuración del servidor MCP.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración del servidor
SERVICE_NAME = "{config.service_name}"
BASE_URL = os.getenv("API_BASE_URL", "{config.base_url}")
API_KEY = os.getenv("API_KEY", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
'''
            files["src/config.py"] = config_content

        except Exception as e:
            logger.error(f"Error generando preview: {e}", exc_info=True)
            files["error.txt"] = f"Error generando código: {str(e)}"

        return files

    def _generate_requirements_code_preview(self, config: MCPServerConfig) -> str:
        """Genera requirements.txt en memoria."""
        if config.mcp_framework == MCPFramework.FASTMCP:
            return """# FastMCP Server Dependencies
fastmcp>=0.1.0
httpx>=0.25.0
pydantic>=2.0.0
python-dotenv>=1.0.0
"""
        else:
            return """# MCP Server Dependencies
mcp>=0.1.0
httpx>=0.25.0
pydantic>=2.0.0
python-dotenv>=1.0.0
"""

    def _create_project_structure(self, service_name: str) -> Path:
        """Crea la estructura de directorios del proyecto."""
        server_dir = self.output_dir / f"mcp_server_{service_name}"
        server_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectorios
        (server_dir / "src").mkdir(exist_ok=True)
        (server_dir / "tests").mkdir(exist_ok=True)
        (server_dir / "config").mkdir(exist_ok=True)

        return server_dir

    def _generate_server_file(
        self,
        server_dir: Path,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
        spec: OpenAPISpec,
    ):
        """Genera el archivo principal del servidor MCP."""
        server_code = self._render_server_template(tools, resources, config, spec)

        server_file = server_dir / "src" / "server.py"
        server_file.write_text(server_code, encoding="utf-8")

        # Crear __init__.py
        init_file = server_dir / "src" / "__init__.py"
        init_file.write_text(
            f'"""MCP Server para {config.service_name}"""\n\n__version__ = "1.0.0"\n',
            encoding="utf-8"
        )

        logger.debug(f"Servidor generado: {server_file}")

    def _render_server_template(
        self,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
        spec: OpenAPISpec,
    ) -> str:
        """Renderiza el template del servidor MCP según el framework seleccionado."""
        if config.mcp_framework == MCPFramework.FASTMCP:
            return self._render_fastmcp_template(tools, resources, config, spec)
        else:
            return self._render_standard_mcp_template(tools, resources, config, spec)

    def _render_fastmcp_template(
        self,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
        spec: OpenAPISpec,
    ) -> str:
        """Renderiza el template usando FastMCP."""
        # Generar código de tools con decoradores FastMCP
        tools_code = self._generate_fastmcp_tools_code(tools, config)

        # Generar código de resources con decoradores FastMCP
        resources_code = self._generate_fastmcp_resources_code(resources, config)

        server_template = f'''"""
MCP Server para {config.service_name}

Servidor generado automáticamente desde especificación OpenAPI.
API: {spec.title} v{spec.version}

Framework: FastMCP
Generated by OpenAPI-to-MCP Generator
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any

from fastmcp import FastMCP

from .http_client import HTTPClient
from .auth import AuthManager
from .config import load_config

# Configurar logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "{config.log_level}"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Cargar configuración
config = load_config()

# Inicializar servidor FastMCP
mcp = FastMCP("{config.service_name}")

# Inicializar cliente HTTP y autenticación
auth_manager = AuthManager(config)
http_client = HTTPClient(
    base_url=config.get("base_url", "{config.base_url}"),
    auth_manager=auth_manager,
    timeout=config.get("timeout", {config.timeout}),
    headers=config.get("headers", {{}})
)


# ============================================================================
# TOOLS - Operaciones de la API
# ============================================================================

{tools_code}


# ============================================================================
# RESOURCES - Datos y documentación
# ============================================================================

{resources_code}


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    """Punto de entrada principal del servidor."""
    logger.info(f"Iniciando FastMCP Server: {config.service_name}")
    logger.info(f"Base URL: {{config.get('base_url', '{config.base_url}')}}")
    mcp.run()


if __name__ == "__main__":
    main()
'''
        return server_template

    def _render_standard_mcp_template(
        self,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
        spec: OpenAPISpec,
    ) -> str:
        """Renderiza el template usando MCP estándar."""
        # Generar código de tools
        tools_code = self._generate_tools_code(tools, config)

        # Generar código de resources
        resources_code = self._generate_resources_code(resources, config)

        # Template principal del servidor
        server_template = f'''"""
MCP Server para {config.service_name}

Servidor generado automáticamente desde especificación OpenAPI.
API: {spec.title} v{spec.version}

Generated by OpenAPI-to-MCP Generator
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from .http_client import HTTPClient
from .auth import AuthManager
from .config import load_config

# Configurar logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "{config.log_level}"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Cargar configuración
config = load_config()

# Inicializar servidor MCP
server = Server("{config.service_name}")

# Inicializar cliente HTTP y autenticación
auth_manager = AuthManager(config)
http_client = HTTPClient(
    base_url=config.get("base_url", "{config.base_url}"),
    auth_manager=auth_manager,
    timeout=config.get("timeout", {config.timeout}),
    headers=config.get("headers", {{}})
)


# ============================================================================
# TOOLS - Operaciones de la API
# ============================================================================

{tools_code}


# ============================================================================
# RESOURCES - Datos y documentación
# ============================================================================

{resources_code}


# ============================================================================
# HANDLERS DEL SERVIDOR MCP
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista todas las herramientas disponibles."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Ejecuta una herramienta por nombre."""
    logger.info(f"Ejecutando tool: {{name}}")
    logger.debug(f"Argumentos: {{arguments}}")

    # Agregar correlation ID para tracing
    correlation_id = str(uuid.uuid4())
    http_client.set_correlation_id(correlation_id)

    try:
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise ValueError(f"Tool no encontrada: {{name}}")

        result = await handler(arguments)

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]

    except Exception as e:
        logger.error(f"Error en tool {{name}}: {{e}}")
        return [TextContent(
            type="text",
            text=json.dumps({{"error": str(e), "tool": name}})
        )]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """Lista todos los recursos disponibles."""
    return RESOURCES


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Lee el contenido de un recurso."""
    logger.info(f"Leyendo resource: {{uri}}")

    handler = RESOURCE_HANDLERS.get(uri)
    if handler:
        content = await handler()
        return json.dumps(content, indent=2, ensure_ascii=False)

    # Buscar en schemas
    if uri in SCHEMA_CONTENTS:
        return json.dumps(SCHEMA_CONTENTS[uri], indent=2, ensure_ascii=False)

    raise ValueError(f"Resource no encontrado: {{uri}}")


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

async def main():
    """Punto de entrada principal del servidor."""
    logger.info(f"Iniciando MCP Server: {config.service_name}")
    logger.info(f"Base URL: {{config.get('base_url', '{config.base_url}')}}")
    logger.info(f"Tools disponibles: {{len(TOOLS)}}")
    logger.info(f"Resources disponibles: {{len(RESOURCES)}}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
'''
        return server_template

    def _generate_tools_code(
        self,
        tools: list[MCPTool],
        config: MCPServerConfig
    ) -> str:
        """Genera el código para todas las tools."""
        tool_definitions = []
        tool_handlers = []
        handler_mapping = []

        for tool in tools:
            # Definición de la tool
            tool_def = self._generate_tool_definition(tool)
            tool_definitions.append(tool_def)

            # Handler de la tool
            handler = self._generate_tool_handler(tool)
            tool_handlers.append(handler)

            # Mapeo nombre -> handler
            handler_mapping.append(f'    "{tool.name}": handle_{tool.name},')

        code = f'''
# Definiciones de Tools
TOOLS = [
{chr(10).join(tool_definitions)}
]

# Handlers de Tools
{"".join(tool_handlers)}

# Mapeo de handlers
TOOL_HANDLERS = {{
{chr(10).join(handler_mapping)}
}}
'''
        return code

    def _generate_tool_definition(self, tool: MCPTool) -> str:
        """Genera la definición de una tool."""
        input_schema = json.dumps(tool.get_input_schema(), indent=8)

        # Escapar comillas en la descripción
        description = tool.description.replace('"', '\\"').replace('\n', '\\n')

        return f'''    Tool(
        name="{tool.name}",
        description="{description}",
        inputSchema={input_schema}
    ),'''

    def _generate_tool_handler(self, tool: MCPTool) -> str:
        """Genera el handler de una tool."""
        # Construir la llamada HTTP
        method = tool.http_method.value.upper()
        path = tool.endpoint_path

        # Determinar parámetros por ubicación
        path_params = [p for p in tool.parameters if p.location.value == "path"]
        query_params = [p for p in tool.parameters if p.location.value == "query"]
        header_params = [p for p in tool.parameters if p.location.value == "header"]

        # Generar código para construir path
        path_code = f'path = "{path}"'
        for param in path_params:
            path_code += f'\n    path = path.replace("{{{param.name}}}", str(args.get("{param.name}", "")))'

        # Generar código para query params
        query_code = 'query_params = {}'
        for param in query_params:
            query_code += f'''
    if "{param.name}" in args:
        query_params["{param.name}"] = args["{param.name}"]'''

        # Generar código para headers
        header_code = 'headers = {}'
        for param in header_params:
            header_code += f'''
    if "{param.name}" in args:
        headers["{param.name}"] = args["{param.name}"]'''

        # Generar código para body
        body_code = 'body = None'
        if tool.request_body_schema:
            body_code = 'body = args.get("body")'

        return f'''

async def handle_{tool.name}(args: dict[str, Any]) -> dict[str, Any]:
    """
    Handler para: {tool.name}
    {method} {path}
    """
    {path_code}
    {query_code}
    {header_code}
    {body_code}

    response = await http_client.request(
        method="{method}",
        path=path,
        params=query_params,
        headers=headers,
        json_body=body
    )

    return response
'''

    def _generate_fastmcp_tools_code(
        self,
        tools: list[MCPTool],
        config: MCPServerConfig
    ) -> str:
        """Genera el código de tools usando FastMCP con decoradores."""
        tool_handlers = []

        for tool in tools:
            handler = self._generate_fastmcp_tool_handler(tool)
            tool_handlers.append(handler)

        return "\n".join(tool_handlers)

    def _generate_fastmcp_tool_handler(self, tool: MCPTool) -> str:
        """Genera un handler de tool con decorador FastMCP."""
        method = tool.http_method.value.upper()
        path = tool.endpoint_path

        # Determinar parámetros por ubicación
        path_params = [p for p in tool.parameters if p.location.value == "path"]
        query_params = [p for p in tool.parameters if p.location.value == "query"]
        header_params = [p for p in tool.parameters if p.location.value == "header"]

        # Generar argumentos de la función
        func_params = []
        for param in tool.parameters:
            param_type = self._get_python_type(param.param_type)
            if param.required:
                func_params.append(f"{param.name}: {param_type}")
            else:
                default = repr(param.default) if param.default is not None else "None"
                func_params.append(f"{param.name}: {param_type} | None = {default}")

        # Agregar body si existe
        if tool.request_body_schema:
            func_params.append("body: dict | None = None")

        params_str = ", ".join(func_params) if func_params else ""

        # Generar código para construir path
        path_code = f'path = "{path}"'
        for param in path_params:
            path_code += f'\n    path = path.replace("{{{param.name}}}", str({param.name}))'

        # Generar código para query params
        query_code = 'query_params = {}'
        for param in query_params:
            query_code += f'''
    if {param.name} is not None:
        query_params["{param.name}"] = {param.name}'''

        # Generar código para headers
        header_code = 'headers = {}'
        for param in header_params:
            header_code += f'''
    if {param.name} is not None:
        headers["{param.name}"] = {param.name}'''

        # Descripción escapada
        description = tool.description.replace('"', '\\"').replace('\n', '\\n')

        return f'''
@mcp.tool(description="{description}")
async def {tool.name}({params_str}) -> str:
    """
    {tool.name}
    {method} {path}
    """
    {path_code}
    {query_code}
    {header_code}

    response = await http_client.request(
        method="{method}",
        path=path,
        params=query_params,
        headers=headers,
        json_body={"body" if tool.request_body_schema else "None"}
    )

    return json.dumps(response, indent=2, ensure_ascii=False)
'''

    def _get_python_type(self, json_type: str) -> str:
        """Convierte tipo JSON Schema a tipo Python."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return type_map.get(json_type, "Any")

    def _generate_fastmcp_resources_code(
        self,
        resources: list[MCPResource],
        config: MCPServerConfig
    ) -> str:
        """Genera el código de resources usando FastMCP con decoradores."""
        resource_handlers = []
        schema_contents = {}

        for resource in resources:
            if resource.endpoint_path:
                handler = self._generate_fastmcp_resource_handler(resource)
                resource_handlers.append(handler)
            else:
                # Contenido estático para schemas
                schema_contents[resource.uri] = resource.schema_definition

        # Generar código de schemas estáticos
        schemas_code = f"SCHEMA_CONTENTS = {json.dumps(schema_contents, indent=4)}\n" if schema_contents else ""

        # Agregar resource para schemas si hay alguno
        schema_resource = ""
        if schema_contents:
            schema_resource = '''
@mcp.resource("schemas://all")
async def get_all_schemas() -> str:
    """Retorna todos los schemas disponibles."""
    return json.dumps(SCHEMA_CONTENTS, indent=2, ensure_ascii=False)
'''

        return schemas_code + "\n".join(resource_handlers) + schema_resource

    def _generate_fastmcp_resource_handler(self, resource: MCPResource) -> str:
        """Genera un handler de resource con decorador FastMCP."""
        description = resource.description.replace('"', '\\"').replace('\n', '\\n')

        return f'''
@mcp.resource("{resource.uri}")
async def resource_{resource.uri.replace("://", "_").replace("/", "_").replace("-", "_")}() -> str:
    """
    {resource.name}
    {description}
    """
    response = await http_client.request(
        method="GET",
        path="{resource.endpoint_path}"
    )
    return json.dumps(response, indent=2, ensure_ascii=False)
'''

    def _generate_resources_code(
        self,
        resources: list[MCPResource],
        config: MCPServerConfig
    ) -> str:
        """Genera el código para todos los resources."""
        resource_definitions = []
        resource_handlers = []
        handler_mapping = []
        schema_contents = []

        for resource in resources:
            # Definición del resource
            res_def = self._generate_resource_definition(resource)
            resource_definitions.append(res_def)

            # Handler si tiene endpoint
            if resource.endpoint_path:
                handler = self._generate_resource_handler(resource)
                resource_handlers.append(handler)
                handler_name = resource.uri.replace("://", "_").replace("/", "_")
                handler_mapping.append(f'    "{resource.uri}": handle_resource_{handler_name},')
            else:
                # Contenido estático para schemas
                schema_contents.append(
                    f'    "{resource.uri}": {json.dumps(resource.schema_definition, indent=8)},'
                )

        code = f'''
# Definiciones de Resources
RESOURCES = [
{chr(10).join(resource_definitions)}
]

# Contenido estático de schemas
SCHEMA_CONTENTS = {{
{chr(10).join(schema_contents)}
}}

# Handlers de Resources
{"".join(resource_handlers)}

# Mapeo de handlers
RESOURCE_HANDLERS = {{
{chr(10).join(handler_mapping)}
}}
'''
        return code

    def _generate_resource_definition(self, resource: MCPResource) -> str:
        """Genera la definición de un resource."""
        description = resource.description.replace('"', '\\"').replace('\n', '\\n')

        return f'''    Resource(
        uri="{resource.uri}",
        name="{resource.name}",
        description="{description}",
        mimeType="{resource.mime_type}"
    ),'''

    def _generate_resource_handler(self, resource: MCPResource) -> str:
        """Genera el handler de un resource con endpoint."""
        handler_name = resource.uri.replace("://", "_").replace("/", "_")

        return f'''

async def handle_resource_{handler_name}() -> dict[str, Any]:
    """Handler para resource: {resource.uri}"""
    response = await http_client.request(
        method="GET",
        path="{resource.endpoint_path}"
    )
    return response
'''

    def _generate_http_client(self, server_dir: Path, config: MCPServerConfig):
        """Genera el módulo de cliente HTTP."""
        http_client_code = f'''"""
Cliente HTTP resiliente para comunicación con la API.

Incluye:
- Reintentos automáticos con backoff exponencial
- Manejo de rate limiting
- Headers corporativos (correlation ID, tracing)
- Timeout configurable
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HTTPClient:
    """Cliente HTTP async con reintentos y manejo de errores."""

    def __init__(
        self,
        base_url: str,
        auth_manager: Any,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        retry_statuses: list[int] | None = None,
        headers: dict[str, str] | None = None,
    ):
        """
        Inicializa el cliente HTTP.

        Args:
            base_url: URL base de la API
            auth_manager: Manejador de autenticación
            timeout: Timeout en segundos
            max_retries: Número máximo de reintentos
            backoff_factor: Factor de backoff exponencial
            retry_statuses: Códigos HTTP para reintentar
            headers: Headers adicionales por defecto
        """
        self.base_url = base_url.rstrip("/")
        self.auth_manager = auth_manager
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_statuses = retry_statuses or [429, 500, 502, 503, 504]
        self.default_headers = headers or {{}}
        self._correlation_id: str | None = None

        # Cliente httpx
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    def set_correlation_id(self, correlation_id: str):
        """Establece el correlation ID para tracing."""
        self._correlation_id = correlation_id

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        data: Any = None,
    ) -> dict[str, Any]:
        """
        Realiza una petición HTTP con reintentos.

        Args:
            method: Método HTTP
            path: Path del endpoint
            params: Query parameters
            headers: Headers adicionales
            json_body: Body JSON
            data: Body form data

        Returns:
            Respuesta parseada como dict

        Raises:
            httpx.HTTPError: Si la petición falla después de reintentos
        """
        # Construir headers
        request_headers = {{**self.default_headers}}
        if headers:
            request_headers.update(headers)

        # Agregar headers de autenticación
        auth_headers = await self.auth_manager.get_auth_headers()
        request_headers.update(auth_headers)

        # Agregar correlation ID
        if self._correlation_id:
            request_headers["{config.correlation_id_header}"] = self._correlation_id

        # Reintentos con backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Request {{method}} {{path}} (intento {{attempt + 1}}/{{self.max_retries + 1}})"
                )

                response = await self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    headers=request_headers,
                    json=json_body,
                    data=data,
                )

                # Verificar si debemos reintentar
                if response.status_code in self.retry_statuses:
                    if attempt < self.max_retries:
                        wait_time = self.backoff_factor * (2 ** attempt)

                        # Respetar Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_time = float(retry_after)
                            except ValueError:
                                pass

                        logger.warning(
                            f"Status {{response.status_code}}, reintentando en {{wait_time}}s"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                response.raise_for_status()

                # Parsear respuesta
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {{"content": response.text, "status_code": response.status_code}}

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {{e.response.status_code}} - {{e.response.text}}")
                last_exception = e

                if e.response.status_code not in self.retry_statuses:
                    raise

                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)

            except httpx.RequestError as e:
                logger.error(f"Request error: {{e}}")
                last_exception = e

                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)

        # Si llegamos aquí, fallaron todos los reintentos
        if last_exception:
            raise last_exception

        raise RuntimeError("Request failed after all retries")

    async def close(self):
        """Cierra el cliente HTTP."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
'''

        http_file = server_dir / "src" / "http_client.py"
        http_file.write_text(http_client_code, encoding="utf-8")

    def _generate_auth_module(
        self,
        server_dir: Path,
        security_schemes: dict[str, SecurityScheme],
        config: MCPServerConfig,
    ):
        """Genera el módulo de autenticación."""
        # Generar código para cada scheme
        scheme_handlers = []
        for name, scheme in security_schemes.items():
            handler = self._generate_auth_scheme_handler(name, scheme)
            scheme_handlers.append(handler)

        auth_code = f'''"""
Módulo de autenticación para el servidor MCP.

Soporta:
- API Keys (header, query, cookie)
- Bearer tokens (JWT)
- Basic authentication
- OAuth2 (client credentials, password)
"""

import base64
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AuthManager:
    """Manejador de autenticación multi-scheme."""

    def __init__(self, config: dict[str, Any]):
        """
        Inicializa el manejador de autenticación.

        Args:
            config: Configuración con credenciales
        """
        self.config = config
        self.auth_config = config.get("auth", {{}})
        self._token_cache: dict[str, Any] = {{}}
        self._token_expiry: dict[str, datetime] = {{}}

    async def get_auth_headers(self) -> dict[str, str]:
        """
        Obtiene los headers de autenticación según la configuración.

        Returns:
            Dict con headers de autenticación
        """
        headers = {{}}
        auth_type = self.auth_config.get("type", "none")

        if auth_type == "api_key":
            headers.update(await self._get_api_key_auth())
        elif auth_type == "bearer":
            headers.update(await self._get_bearer_auth())
        elif auth_type == "basic":
            headers.update(await self._get_basic_auth())
        elif auth_type == "oauth2":
            headers.update(await self._get_oauth2_auth())

        return headers

    async def _get_api_key_auth(self) -> dict[str, str]:
        """Obtiene headers para API Key auth."""
        api_key = self.auth_config.get("api_key") or os.getenv("API_KEY")
        header_name = self.auth_config.get("header_name", "X-API-Key")

        if not api_key:
            logger.warning("API Key no configurada")
            return {{}}

        return {{header_name: api_key}}

    async def _get_bearer_auth(self) -> dict[str, str]:
        """Obtiene headers para Bearer token auth."""
        token = self.auth_config.get("token") or os.getenv("AUTH_TOKEN")

        if not token:
            logger.warning("Bearer token no configurado")
            return {{}}

        return {{"Authorization": f"Bearer {{token}}"}}

    async def _get_basic_auth(self) -> dict[str, str]:
        """Obtiene headers para Basic auth."""
        username = self.auth_config.get("username") or os.getenv("AUTH_USERNAME")
        password = self.auth_config.get("password") or os.getenv("AUTH_PASSWORD")

        if not username or not password:
            logger.warning("Credenciales Basic auth no configuradas")
            return {{}}

        credentials = base64.b64encode(f"{{username}}:{{password}}".encode()).decode()
        return {{"Authorization": f"Basic {{credentials}}"}}

    async def _get_oauth2_auth(self) -> dict[str, str]:
        """Obtiene headers para OAuth2 auth."""
        # Verificar si tenemos un token válido en cache
        cache_key = "oauth2_token"
        if cache_key in self._token_cache:
            expiry = self._token_expiry.get(cache_key)
            if expiry and datetime.now() < expiry:
                return {{"Authorization": f"Bearer {{self._token_cache[cache_key]}}"}}

        # Obtener nuevo token
        token = await self._fetch_oauth2_token()
        if token:
            self._token_cache[cache_key] = token["access_token"]
            expires_in = token.get("expires_in", 3600)
            self._token_expiry[cache_key] = datetime.now() + timedelta(seconds=expires_in - 60)
            return {{"Authorization": f"Bearer {{token['access_token']}}"}}

        return {{}}

    async def _fetch_oauth2_token(self) -> dict[str, Any] | None:
        """Obtiene un token OAuth2 del servidor de autorización."""
        token_url = self.auth_config.get("token_url")
        client_id = self.auth_config.get("client_id") or os.getenv("OAUTH_CLIENT_ID")
        client_secret = self.auth_config.get("client_secret") or os.getenv("OAUTH_CLIENT_SECRET")
        scope = self.auth_config.get("scope", "")

        if not all([token_url, client_id, client_secret]):
            logger.error("Configuración OAuth2 incompleta")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={{
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": scope,
                    }},
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error obteniendo token OAuth2: {{e}}")
            return None

    def clear_cache(self):
        """Limpia la cache de tokens."""
        self._token_cache.clear()
        self._token_expiry.clear()


# Handlers específicos para cada scheme definido en OpenAPI
{chr(10).join(scheme_handlers) if scheme_handlers else "# No hay schemes adicionales definidos"}
'''

        auth_file = server_dir / "src" / "auth.py"
        auth_file.write_text(auth_code, encoding="utf-8")

    def _generate_auth_scheme_handler(
        self,
        name: str,
        scheme: SecurityScheme
    ) -> str:
        """Genera código para un scheme de seguridad específico."""
        return f'''
# Scheme: {name} ({scheme.scheme_type.value})
# {scheme.description or "Sin descripción"}
'''

    def _generate_config_file(self, server_dir: Path, config: MCPServerConfig):
        """Genera archivos de configuración."""
        # config.py
        config_module = f'''"""
Módulo de configuración del servidor MCP.

Carga configuración desde:
1. Archivo config.yaml
2. Variables de entorno
3. Valores por defecto
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def load_config() -> dict[str, Any]:
    """
    Carga la configuración del servidor.

    Returns:
        Dict con configuración
    """
    config = get_default_config()

    # Cargar desde archivo si existe
    config_file = Path(__file__).parent.parent / "config" / "config.yaml"
    if config_file.exists():
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f)
            if file_config:
                config = deep_merge(config, file_config)

    # Override con variables de entorno
    env_overrides = get_env_overrides()
    config = deep_merge(config, env_overrides)

    return config


def get_default_config() -> dict[str, Any]:
    """Retorna configuración por defecto."""
    return {{
        "service_name": "{config.service_name}",
        "base_url": "{config.base_url}",
        "timeout": {config.timeout},
        "environment": "{config.environment}",
        "log_level": "{config.log_level}",
        "enable_tracing": {str(config.enable_tracing).lower()},
        "correlation_id_header": "{config.correlation_id_header}",
        "retry": {{
            "max_retries": {config.retry_config.get("max_retries", 3)},
            "backoff_factor": {config.retry_config.get("backoff_factor", 0.5)},
            "retry_statuses": {config.retry_config.get("retry_statuses", [429, 500, 502, 503, 504])}
        }},
        "auth": {json.dumps(config.auth_config, indent=12)},
        "headers": {json.dumps(config.headers, indent=12)}
    }}


def get_env_overrides() -> dict[str, Any]:
    """Obtiene overrides desde variables de entorno."""
    overrides = {{}}

    if os.getenv("BASE_URL"):
        overrides["base_url"] = os.getenv("BASE_URL")

    if os.getenv("TIMEOUT"):
        overrides["timeout"] = int(os.getenv("TIMEOUT"))

    if os.getenv("LOG_LEVEL"):
        overrides["log_level"] = os.getenv("LOG_LEVEL")

    if os.getenv("ENVIRONMENT"):
        overrides["environment"] = os.getenv("ENVIRONMENT")

    return overrides


def deep_merge(base: dict, override: dict) -> dict:
    """Merge profundo de diccionarios."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result
'''

        config_py = server_dir / "src" / "config.py"
        config_py.write_text(config_module, encoding="utf-8")

        # config.yaml
        config_yaml = f'''# Configuración del servidor MCP
# {config.service_name}

service_name: {config.service_name}
base_url: {config.base_url}
timeout: {config.timeout}
environment: {config.environment}
log_level: {config.log_level}

# Configuración de reintentos
retry:
  max_retries: {config.retry_config.get("max_retries", 3)}
  backoff_factor: {config.retry_config.get("backoff_factor", 0.5)}
  retry_statuses:
    - 429
    - 500
    - 502
    - 503
    - 504

# Autenticación
# Descomenta y configura según el tipo de auth requerido
auth:
  type: none  # none, api_key, bearer, basic, oauth2

  # Para API Key:
  # type: api_key
  # api_key: "${{API_KEY}}"
  # header_name: X-API-Key

  # Para Bearer token:
  # type: bearer
  # token: "${{AUTH_TOKEN}}"

  # Para Basic auth:
  # type: basic
  # username: "${{AUTH_USERNAME}}"
  # password: "${{AUTH_PASSWORD}}"

  # Para OAuth2:
  # type: oauth2
  # token_url: https://auth.example.com/oauth/token
  # client_id: "${{OAUTH_CLIENT_ID}}"
  # client_secret: "${{OAUTH_CLIENT_SECRET}}"
  # scope: read write

# Headers adicionales
headers:
  User-Agent: MCP-Server-{config.service_name}/1.0
'''

        config_yaml_file = server_dir / "config" / "config.yaml"
        config_yaml_file.write_text(config_yaml, encoding="utf-8")

        # .env.example
        env_example = f'''# Variables de entorno para {config.service_name}

# URL base de la API
BASE_URL={config.base_url}

# Timeout en segundos
TIMEOUT={config.timeout}

# Nivel de logging
LOG_LEVEL={config.log_level}

# Ambiente
ENVIRONMENT={config.environment}

# Autenticación (según el tipo configurado)
API_KEY=
AUTH_TOKEN=
AUTH_USERNAME=
AUTH_PASSWORD=
OAUTH_CLIENT_ID=
OAUTH_CLIENT_SECRET=
'''

        env_file = server_dir / ".env.example"
        env_file.write_text(env_example, encoding="utf-8")

    def _generate_requirements(self, server_dir: Path, config: MCPServerConfig):
        """Genera archivo requirements.txt según el framework seleccionado."""
        if config.mcp_framework == MCPFramework.FASTMCP:
            mcp_dep = "fastmcp>=0.1.0"
            framework_comment = "# Framework: FastMCP (recomendado)"
        else:
            mcp_dep = "mcp>=1.0.0"
            framework_comment = "# Framework: MCP estándar"

        requirements = f'''# Dependencias del servidor MCP
{framework_comment}
{mcp_dep}
httpx>=0.25.0
pyyaml>=6.0
python-dotenv>=1.0.0
pydantic>=2.5.0
'''

        req_file = server_dir / "requirements.txt"
        req_file.write_text(requirements, encoding="utf-8")

    def _generate_pyproject(self, server_dir: Path, config: MCPServerConfig):
        """Genera pyproject.toml."""
        mcp_dep = "fastmcp>=0.1.0" if config.mcp_framework == MCPFramework.FASTMCP else "mcp>=1.0.0"

        pyproject = f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-server-{config.service_name}"
version = "1.0.0"
description = "MCP Server para {config.service_name}"
requires-python = ">=3.10"
dependencies = [
    "{mcp_dep}",
    "httpx>=0.25.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
]

[project.scripts]
{config.service_name}-mcp = "src.server:main"

[tool.hatch.build.targets.wheel]
packages = ["src"]
'''

        pyproject_file = server_dir / "pyproject.toml"
        pyproject_file.write_text(pyproject, encoding="utf-8")

    def _generate_dockerfile(self, server_dir: Path, config: MCPServerConfig):
        """Genera Dockerfile."""
        dockerfile = f'''# Dockerfile para MCP Server {config.service_name}
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY config/ ./config/

# Variables de entorno por defecto
ENV LOG_LEVEL={config.log_level}
ENV ENVIRONMENT={config.environment}

# Puerto no necesario para MCP stdio, pero útil para health checks
EXPOSE 8080

# Comando de ejecución
CMD ["python", "-m", "src.server"]
'''

        dockerfile_path = server_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile, encoding="utf-8")

        # docker-compose.yml
        docker_compose = f'''version: "3.8"

services:
  {config.service_name}-mcp:
    build: .
    container_name: mcp-{config.service_name}
    environment:
      - BASE_URL={config.base_url}
      - LOG_LEVEL={config.log_level}
      - ENVIRONMENT={config.environment}
      # Agregar credenciales según sea necesario
      # - API_KEY=${{API_KEY}}
      # - AUTH_TOKEN=${{AUTH_TOKEN}}
    volumes:
      - ./config:/app/config:ro
    restart: unless-stopped
'''

        compose_file = server_dir / "docker-compose.yml"
        compose_file.write_text(docker_compose, encoding="utf-8")

    def _generate_readme(
        self,
        server_dir: Path,
        spec: OpenAPISpec,
        tools: list[MCPTool],
        resources: list[MCPResource],
        config: MCPServerConfig,
    ):
        """Genera README.md."""
        # Tabla de tools
        tools_table = "| Tool | Método | Endpoint | Descripción |\n|------|--------|----------|-------------|\n"
        for tool in tools[:20]:  # Limitar a 20 para el README
            desc = tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
            tools_table += f"| `{tool.name}` | {tool.http_method.value.upper()} | `{tool.endpoint_path}` | {desc} |\n"

        if len(tools) > 20:
            tools_table += f"\n... y {len(tools) - 20} tools más.\n"

        framework_name = "FastMCP" if config.mcp_framework == MCPFramework.FASTMCP else "MCP estándar"
        framework_desc = "FastMCP (API simplificada con decoradores)" if config.mcp_framework == MCPFramework.FASTMCP else "MCP estándar (API de bajo nivel)"

        readme = f'''# MCP Server - {config.service_name}

Servidor MCP (Model Context Protocol) generado automáticamente para la API **{spec.title}** v{spec.version}.

**Framework:** {framework_desc}

## Descripción

{spec.description or "Sin descripción disponible."}

Este servidor expone las funcionalidades de la API como herramientas (tools) y recursos (resources) que pueden ser utilizados por LLMs a través del protocolo MCP.

## Características

- **Framework**: {framework_name}
- **{len(tools)} Tools**: Operaciones de la API como herramientas invocables
- **{len(resources)} Resources**: Schemas y datos consultables
- **Autenticación**: Soporte para API Key, Bearer, Basic y OAuth2
- **Reintentos**: Backoff exponencial automático
- **Tracing**: Correlation IDs para debugging

## Instalación

### Con pip

```bash
pip install -r requirements.txt
```

### Con Docker

```bash
docker build -t mcp-{config.service_name} .
```

## Configuración

1. Copia el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Edita `.env` con tus credenciales:
```bash
BASE_URL={config.base_url}
API_KEY=tu_api_key_aqui
```

3. O edita `config/config.yaml` para configuración más detallada.

## Ejecución

### Directamente con Python

```bash
python -m src.server
```

### Con Docker

```bash
docker-compose up
```

### Integración con Claude Desktop

Agrega esta configuración en tu `claude_desktop_config.json`:

```json
{{
  "mcpServers": {{
    "{config.service_name}": {{
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/ruta/a/mcp_server_{config.service_name}"
    }}
  }}
}}
```

## Tools Disponibles

{tools_table}

## Resources Disponibles

| URI | Nombre | Tipo |
|-----|--------|------|
'''
        for resource in resources[:10]:
            readme += f"| `{resource.uri}` | {resource.name} | {'Colección' if resource.is_collection else 'Entidad'} |\n"

        if len(resources) > 10:
            readme += f"\n... y {len(resources) - 10} resources más.\n"

        readme += f'''

## Estructura del Proyecto

```
mcp_server_{config.service_name}/
├── src/
│   ├── __init__.py
│   ├── server.py      # Servidor MCP principal
│   ├── http_client.py # Cliente HTTP resiliente
│   ├── auth.py        # Manejo de autenticación
│   └── config.py      # Carga de configuración
├── config/
│   └── config.yaml    # Configuración del servidor
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Autenticación

El servidor soporta múltiples métodos de autenticación. Configura en `config/config.yaml`:

### API Key
```yaml
auth:
  type: api_key
  header_name: X-API-Key
```
Y define `API_KEY` en variables de entorno.

### Bearer Token
```yaml
auth:
  type: bearer
```
Y define `AUTH_TOKEN` en variables de entorno.

### OAuth2
```yaml
auth:
  type: oauth2
  token_url: https://auth.example.com/oauth/token
  scope: read write
```
Y define `OAUTH_CLIENT_ID` y `OAUTH_CLIENT_SECRET` en variables de entorno.

## Desarrollo

### Tests

```bash
pytest tests/
```

### Logging

Ajusta el nivel de logging con la variable de entorno:

```bash
LOG_LEVEL=DEBUG python -m src.server
```

## Generado por

OpenAPI-to-MCP Generator

---

Servidor MCP generado desde: {spec.title} v{spec.version}
'''

        readme_file = server_dir / "README.md"
        readme_file.write_text(readme, encoding="utf-8")

    def _generate_schemas_module(
        self,
        server_dir: Path,
        schemas: dict[str, dict[str, Any]]
    ):
        """Genera módulo con definiciones de schemas."""
        schemas_code = '''"""
Definiciones de schemas de la API.

Contiene los schemas JSON Schema extraídos de la especificación OpenAPI.
"""

SCHEMAS = '''
        schemas_code += json.dumps(schemas, indent=4, ensure_ascii=False)

        schemas_file = server_dir / "src" / "schemas.py"
        schemas_file.write_text(schemas_code, encoding="utf-8")
