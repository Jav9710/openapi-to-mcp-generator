"""
Modelos de datos para el generador OpenAPI-to-MCP.

Define las estructuras de datos intermedias utilizadas durante
la transformación de OpenAPI a MCP.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class HttpMethod(Enum):
    """Métodos HTTP soportados."""
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    PATCH = "patch"
    HEAD = "head"
    OPTIONS = "options"


class ParameterLocation(Enum):
    """Ubicaciones de parámetros en OpenAPI."""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"


class SecuritySchemeType(Enum):
    """Tipos de esquemas de seguridad."""
    API_KEY = "apiKey"
    HTTP = "http"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"


class MCPFramework(Enum):
    """Framework MCP a utilizar para el servidor generado."""
    FASTMCP = "fastmcp"  # FastMCP - API simplificada con decoradores (recomendado)
    MCP = "mcp"          # MCP estándar - API de bajo nivel


@dataclass
class ToolParameter:
    """
    Representa un parámetro de una herramienta MCP.

    Attributes:
        name: Nombre del parámetro
        description: Descripción para el LLM
        param_type: Tipo JSON Schema (string, integer, etc.)
        required: Si el parámetro es obligatorio
        location: Ubicación en la petición HTTP (path, query, header, body)
        default: Valor por defecto
        enum: Lista de valores permitidos
        schema: Esquema JSON completo para tipos complejos
    """
    name: str
    description: str
    param_type: str
    required: bool = False
    location: ParameterLocation = ParameterLocation.QUERY
    default: Any = None
    enum: list[str] | None = None
    schema: dict[str, Any] | None = None
    format: str | None = None

    def to_json_schema(self) -> dict[str, Any]:
        """Convierte el parámetro a JSON Schema."""
        schema: dict[str, Any] = {
            "type": self.param_type,
            "description": self.description,
        }

        if self.default is not None:
            schema["default"] = self.default
        if self.enum:
            schema["enum"] = self.enum
        if self.format:
            schema["format"] = self.format
        if self.schema:
            # Merge con schema adicional para tipos complejos
            schema.update(self.schema)

        return schema


@dataclass
class MCPTool:
    """
    Representa una herramienta MCP generada.

    Attributes:
        name: Nombre único de la herramienta (formato: microservice_operation)
        description: Descripción completa para el LLM
        parameters: Lista de parámetros de entrada
        http_method: Método HTTP de la operación original
        endpoint_path: Ruta del endpoint (ej: /users/{id})
        operation_id: ID de operación OpenAPI original
        tags: Tags/categorías de la operación
        request_body_schema: Schema del cuerpo de la petición
        response_schema: Schema de la respuesta esperada
        security_requirements: Requisitos de seguridad
        rate_limit: Límite de tasa si está definido
    """
    name: str
    description: str
    parameters: list[ToolParameter]
    http_method: HttpMethod
    endpoint_path: str
    operation_id: str | None = None
    tags: list[str] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    security_requirements: list[dict[str, list[str]]] = field(default_factory=list)
    rate_limit: dict[str, Any] | None = None
    deprecated: bool = False

    def get_input_schema(self) -> dict[str, Any]:
        """
        Genera el esquema JSON Schema completo para los parámetros de entrada.

        Returns:
            Esquema JSON Schema compatible con MCP
        """
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        # Agregar request body como parámetro si existe
        if self.request_body_schema:
            properties["body"] = {
                "type": "object",
                "description": "Cuerpo de la petición",
                **self.request_body_schema
            }
            if self.request_body_schema.get("required"):
                required.append("body")

        schema = {
            "type": "object",
            "properties": properties,
        }

        if required:
            schema["required"] = required

        return schema


@dataclass
class MCPResource:
    """
    Representa un recurso MCP generado.

    Attributes:
        uri: URI única del recurso (ej: microservice://entities/users)
        name: Nombre legible del recurso
        description: Descripción para el LLM
        mime_type: Tipo MIME del contenido
        schema_name: Nombre del schema OpenAPI original
        schema_definition: Definición completa del schema
        endpoint_path: Endpoint GET para obtener el recurso (si existe)
        is_collection: Si el recurso representa una colección
    """
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    schema_name: str | None = None
    schema_definition: dict[str, Any] = field(default_factory=dict)
    endpoint_path: str | None = None
    is_collection: bool = False

    def get_schema_info(self) -> dict[str, Any]:
        """Retorna información del schema para documentación."""
        return {
            "name": self.schema_name,
            "definition": self.schema_definition,
            "mime_type": self.mime_type,
        }


@dataclass
class SecurityScheme:
    """
    Representa un esquema de seguridad.

    Attributes:
        name: Nombre del esquema
        scheme_type: Tipo (apiKey, http, oauth2, openIdConnect)
        location: Ubicación del token/key (header, query, cookie)
        param_name: Nombre del parámetro/header
        scheme: Esquema HTTP (bearer, basic) para type=http
        bearer_format: Formato del token bearer (JWT, etc.)
        flows: Flujos OAuth2 si aplica
        openid_connect_url: URL de descubrimiento OIDC
    """
    name: str
    scheme_type: SecuritySchemeType
    location: str | None = None
    param_name: str | None = None
    scheme: str | None = None
    bearer_format: str | None = None
    flows: dict[str, Any] | None = None
    openid_connect_url: str | None = None
    description: str | None = None

    def get_auth_header_template(self) -> str | None:
        """Genera template para header de autorización."""
        if self.scheme_type == SecuritySchemeType.HTTP:
            if self.scheme == "bearer":
                return "Bearer {token}"
            elif self.scheme == "basic":
                return "Basic {credentials}"
        elif self.scheme_type == SecuritySchemeType.API_KEY:
            return "{api_key}"
        return None


@dataclass
class ServerInfo:
    """Información del servidor de la API."""
    url: str
    description: str | None = None
    variables: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_resolved_url(self, env_vars: dict[str, str] | None = None) -> str:
        """Resuelve la URL con las variables."""
        url = self.url
        env_vars = env_vars or {}

        for var_name, var_config in self.variables.items():
            value = env_vars.get(var_name, var_config.get("default", ""))
            url = url.replace(f"{{{var_name}}}", value)

        return url


@dataclass
class OpenAPISpec:
    """
    Representación parseada de una especificación OpenAPI.

    Attributes:
        title: Título de la API
        version: Versión de la API
        description: Descripción de la API
        servers: Lista de servidores
        paths: Operaciones por path
        components_schemas: Schemas definidos en components
        security_schemes: Esquemas de seguridad disponibles
        global_security: Requisitos de seguridad globales
        tags: Tags definidos globalmente
        openapi_version: Versión de OpenAPI (3.0.x, 3.1.x)
    """
    title: str
    version: str
    description: str | None = None
    servers: list[ServerInfo] = field(default_factory=list)
    paths: dict[str, dict[str, Any]] = field(default_factory=dict)
    components_schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    security_schemes: dict[str, SecurityScheme] = field(default_factory=dict)
    global_security: list[dict[str, list[str]]] = field(default_factory=list)
    tags: list[dict[str, Any]] = field(default_factory=list)
    openapi_version: str = "3.0.0"

    def get_base_url(self, environment: str = "default") -> str:
        """Obtiene la URL base según el ambiente."""
        if not self.servers:
            return "http://localhost:8080"

        # Buscar servidor que coincida con el ambiente
        for server in self.servers:
            if environment in (server.description or "").lower():
                return server.get_resolved_url()

        return self.servers[0].get_resolved_url()


@dataclass
class MCPServerConfig:
    """
    Configuración para el servidor MCP generado.

    Attributes:
        service_name: Nombre del microservicio
        service_prefix: Prefijo para nombres de tools/resources
        base_url: URL base de la API
        mcp_framework: Framework MCP a usar (fastmcp o mcp)
        auth_config: Configuración de autenticación
        timeout: Timeout para peticiones HTTP (segundos)
        retry_config: Configuración de reintentos
        headers: Headers adicionales por defecto
        environment: Ambiente (dev, staging, prod)
    """
    service_name: str
    service_prefix: str
    base_url: str
    mcp_framework: MCPFramework = MCPFramework.FASTMCP
    auth_config: dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    retry_config: dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3,
        "backoff_factor": 0.5,
        "retry_statuses": [429, 500, 502, 503, 504]
    })
    headers: dict[str, str] = field(default_factory=dict)
    environment: str = "production"
    log_level: str = "INFO"
    enable_tracing: bool = True
    correlation_id_header: str = "X-Correlation-ID"

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "service_name": self.service_name,
            "service_prefix": self.service_prefix,
            "base_url": self.base_url,
            "mcp_framework": self.mcp_framework.value,
            "auth_config": self.auth_config,
            "timeout": self.timeout,
            "retry_config": self.retry_config,
            "headers": self.headers,
            "environment": self.environment,
            "log_level": self.log_level,
            "enable_tracing": self.enable_tracing,
            "correlation_id_header": self.correlation_id_header,
        }


@dataclass
class GenerationResult:
    """
    Resultado de la generación del servidor MCP.

    Attributes:
        success: Si la generación fue exitosa
        output_path: Ruta donde se generó el código
        tools_generated: Lista de tools generadas
        resources_generated: Lista de resources generados
        warnings: Advertencias durante la generación
        errors: Errores encontrados
        config: Configuración utilizada
    """
    success: bool
    output_path: str
    tools_generated: list[MCPTool] = field(default_factory=list)
    resources_generated: list[MCPResource] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    config: MCPServerConfig | None = None

    def get_summary(self) -> str:
        """Genera resumen de la generación."""
        lines = [
            f"Generación {'exitosa' if self.success else 'fallida'}",
            f"Output: {self.output_path}",
            f"Tools generadas: {len(self.tools_generated)}",
            f"Resources generados: {len(self.resources_generated)}",
        ]

        if self.warnings:
            lines.append(f"Advertencias: {len(self.warnings)}")
        if self.errors:
            lines.append(f"Errores: {len(self.errors)}")

        return "\n".join(lines)


@dataclass
class EndpointFilter:
    """
    Filtro para seleccionar endpoints específicos a incluir en el servidor MCP.

    Soporta patrones glob para inclusión/exclusión y selección explícita.

    Attributes:
        include_patterns: Patrones glob para incluir (ej: ["/v1/api/users*", "/orders/*"])
        exclude_patterns: Patrones glob para excluir (ej: ["/internal/*", "*/admin/*"])
        selected_endpoints: Lista explícita de endpoints seleccionados (ej: ["GET /users", "POST /orders"])

    Example:
        # Incluir todos los endpoints de users excepto admin
        filter = EndpointFilter(
            include_patterns=["/v1/api/users*"],
            exclude_patterns=["*/admin/*"]
        )

        # Selección explícita desde GUI
        filter = EndpointFilter(
            selected_endpoints=["GET /users", "POST /users", "GET /users/{id}"]
        )
    """
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    selected_endpoints: list[str] = field(default_factory=list)

    def matches(self, method: str, path: str) -> bool:
        """
        Verifica si un endpoint coincide con los filtros configurados.

        La lógica de filtrado es:
        1. Si hay selected_endpoints, solo esos pasan (modo explícito)
        2. Si hay include_patterns, el path debe coincidir con al menos uno
        3. Si hay exclude_patterns, el path no debe coincidir con ninguno
        4. Si no hay filtros, todos los endpoints pasan

        Args:
            method: Método HTTP (GET, POST, etc.)
            path: Ruta del endpoint (/users/{id})

        Returns:
            True si el endpoint debe incluirse
        """
        import fnmatch

        endpoint_key = f"{method.upper()} {path}"

        # Modo selección explícita (desde GUI)
        if self.selected_endpoints:
            return endpoint_key in self.selected_endpoints

        # Si no hay patrones, incluir todo
        if not self.include_patterns and not self.exclude_patterns:
            return True

        # Verificar exclusiones primero
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False

        # Si hay patrones de inclusión, debe coincidir con al menos uno
        if self.include_patterns:
            return any(fnmatch.fnmatch(path, pattern) for pattern in self.include_patterns)

        # Si solo hay exclusiones y no coincidió, incluir
        return True

    def is_empty(self) -> bool:
        """Verifica si el filtro está vacío (sin restricciones)."""
        return (
            not self.include_patterns
            and not self.exclude_patterns
            and not self.selected_endpoints
        )

    def get_summary(self) -> str:
        """Genera un resumen legible del filtro."""
        parts = []

        if self.selected_endpoints:
            parts.append(f"Seleccionados: {len(self.selected_endpoints)} endpoints")
        if self.include_patterns:
            parts.append(f"Incluir: {', '.join(self.include_patterns)}")
        if self.exclude_patterns:
            parts.append(f"Excluir: {', '.join(self.exclude_patterns)}")

        return " | ".join(parts) if parts else "Sin filtros (todos los endpoints)"
