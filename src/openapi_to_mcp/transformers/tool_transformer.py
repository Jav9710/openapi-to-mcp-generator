"""
Transformador de operaciones OpenAPI a Tools MCP.

Convierte cada endpoint/operación de una API OpenAPI en una
herramienta MCP con su esquema de parámetros correspondiente.
"""

import logging
import re
from typing import Any

from ..models import (
    EndpointFilter,
    HttpMethod,
    MCPTool,
    OpenAPISpec,
    ParameterLocation,
    ToolParameter,
)

logger = logging.getLogger(__name__)


class ToolTransformerError(Exception):
    """Error durante la transformación a tools."""
    pass


class ToolTransformer:
    """
    Transforma operaciones OpenAPI en herramientas MCP.

    Cada operación (GET /users, POST /orders, etc.) se convierte
    en una tool MCP con:
    - Nombre único basado en operationId o path+method
    - Descripción clara para el LLM
    - Esquema JSON Schema de parámetros
    - Metadatos de seguridad y rate limiting

    Example:
        transformer = ToolTransformer(service_prefix="users_api")
        tools = transformer.transform(openapi_spec)
        for tool in tools:
            print(f"{tool.name}: {tool.description}")
    """

    # Mapeo de tipos OpenAPI a JSON Schema
    TYPE_MAPPING = {
        "integer": "integer",
        "number": "number",
        "string": "string",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
    }

    # Verbos descriptivos por método HTTP
    METHOD_VERBS = {
        "get": "obtener",
        "post": "crear",
        "put": "actualizar",
        "patch": "modificar",
        "delete": "eliminar",
        "head": "verificar",
        "options": "consultar opciones de",
    }

    def __init__(
        self,
        service_prefix: str,
        include_deprecated: bool = False,
        generate_descriptions: bool = True,
    ):
        """
        Inicializa el transformador.

        Args:
            service_prefix: Prefijo para nombres de tools (ej: "users_api")
            include_deprecated: Si incluir operaciones marcadas como deprecated
            generate_descriptions: Si generar descripciones automáticas cuando falten
        """
        self.service_prefix = self._sanitize_prefix(service_prefix)
        self.include_deprecated = include_deprecated
        self.generate_descriptions = generate_descriptions
        self._operation_names: set[str] = set()

    def transform(
        self,
        spec: OpenAPISpec,
        endpoint_filter: EndpointFilter | None = None
    ) -> list[MCPTool]:
        """
        Transforma las operaciones de la especificación en tools.

        Args:
            spec: Especificación OpenAPI parseada
            endpoint_filter: Filtro opcional para seleccionar endpoints específicos

        Returns:
            Lista de MCPTool generadas
        """
        tools = []
        self._operation_names.clear()
        filtered_count = 0

        for path, operations in spec.paths.items():
            for method, operation in operations.items():
                # Verificar deprecated
                if operation.get("deprecated", False) and not self.include_deprecated:
                    logger.debug(f"Omitiendo operación deprecated: {method} {path}")
                    continue

                # Aplicar filtro de endpoints si existe
                if endpoint_filter and not endpoint_filter.matches(method, path):
                    filtered_count += 1
                    logger.debug(f"Endpoint filtrado: {method.upper()} {path}")
                    continue

                try:
                    tool = self._transform_operation(
                        path=path,
                        method=method,
                        operation=operation,
                        global_security=spec.global_security,
                    )
                    tools.append(tool)
                    logger.debug(f"Tool generada: {tool.name}")

                except Exception as e:
                    logger.warning(
                        f"Error transformando {method} {path}: {e}",
                        exc_info=True
                    )

        if filtered_count > 0:
            logger.info(f"Endpoints filtrados: {filtered_count}")
        logger.info(f"Total tools generadas: {len(tools)}")
        return tools

    def _transform_operation(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        global_security: list[dict[str, list[str]]],
    ) -> MCPTool:
        """
        Transforma una operación individual en una tool.

        Args:
            path: Path del endpoint
            method: Método HTTP
            operation: Diccionario de la operación
            global_security: Requisitos de seguridad globales

        Returns:
            MCPTool generada
        """
        # Generar nombre único
        name = self._generate_tool_name(path, method, operation)

        # Generar descripción
        description = self._generate_description(path, method, operation)

        # Extraer parámetros
        parameters = self._extract_parameters(operation)

        # Extraer request body schema
        request_body_schema = self._extract_request_body_schema(operation)

        # Extraer response schema (para documentación)
        response_schema = self._extract_response_schema(operation)

        # Determinar requisitos de seguridad
        security = operation.get("security", global_security)

        # Extraer rate limit si existe (extensión x-rateLimit)
        rate_limit = operation.get("x-rateLimit") or operation.get("x-rate-limit")

        return MCPTool(
            name=name,
            description=description,
            parameters=parameters,
            http_method=HttpMethod(method.lower()),
            endpoint_path=path,
            operation_id=operation.get("operationId"),
            tags=operation.get("tags", []),
            request_body_schema=request_body_schema,
            response_schema=response_schema,
            security_requirements=security or [],
            rate_limit=rate_limit,
            deprecated=operation.get("deprecated", False),
        )

    def _generate_tool_name(
        self,
        path: str,
        method: str,
        operation: dict[str, Any]
    ) -> str:
        """
        Genera un nombre único para la tool.

        Prioriza operationId si existe, sino genera desde path+method.

        Args:
            path: Path del endpoint
            method: Método HTTP
            operation: Diccionario de operación

        Returns:
            Nombre único en formato snake_case
        """
        # Intentar usar operationId
        operation_id = operation.get("operationId")

        if operation_id:
            base_name = self._sanitize_name(operation_id)
        else:
            # Generar desde path y método
            base_name = self._path_to_name(path, method)

        # Agregar prefijo del servicio
        full_name = f"{self.service_prefix}_{base_name}"

        # Asegurar unicidad
        unique_name = self._ensure_unique_name(full_name)

        return unique_name

    def _path_to_name(self, path: str, method: str) -> str:
        """
        Convierte un path en nombre de tool.

        Ej: /users/{id}/orders -> get_users_by_id_orders
        """
        # Reemplazar parámetros de path
        name_path = re.sub(r"\{(\w+)\}", r"by_\1", path)

        # Limpiar y convertir a snake_case
        name_path = name_path.strip("/")
        name_path = re.sub(r"[^a-zA-Z0-9]", "_", name_path)
        name_path = re.sub(r"_+", "_", name_path)

        return f"{method.lower()}_{name_path}"

    def _sanitize_name(self, name: str) -> str:
        """Sanitiza un nombre a snake_case válido."""
        # Convertir camelCase a snake_case
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
        name = name.lower()

        # Reemplazar caracteres no válidos
        name = re.sub(r"[^a-z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")

        return name

    def _sanitize_prefix(self, prefix: str) -> str:
        """Sanitiza el prefijo del servicio."""
        return self._sanitize_name(prefix)

    def _ensure_unique_name(self, name: str) -> str:
        """Asegura que el nombre sea único agregando sufijo si es necesario."""
        original_name = name
        counter = 1

        while name in self._operation_names:
            name = f"{original_name}_{counter}"
            counter += 1

        self._operation_names.add(name)
        return name

    def _generate_description(
        self,
        path: str,
        method: str,
        operation: dict[str, Any]
    ) -> str:
        """
        Genera descripción para la tool.

        Combina summary y description de OpenAPI, o genera una automática.
        """
        parts = []

        # Usar summary si existe
        summary = operation.get("summary", "").strip()
        if summary:
            parts.append(summary)

        # Agregar description si es diferente al summary
        description = operation.get("description", "").strip()
        if description and description != summary:
            parts.append(description)

        # Si no hay descripción, generar una automática
        if not parts and self.generate_descriptions:
            verb = self.METHOD_VERBS.get(method.lower(), "operar sobre")
            resource = self._extract_resource_name(path)
            parts.append(f"Permite {verb} {resource}")

        # Agregar información de deprecated
        if operation.get("deprecated"):
            parts.append("[DEPRECATED] Esta operación está obsoleta.")

        # Agregar información de tags para contexto
        tags = operation.get("tags", [])
        if tags:
            parts.append(f"Categorías: {', '.join(tags)}")

        return "\n\n".join(parts) if parts else "Sin descripción disponible"

    def _extract_resource_name(self, path: str) -> str:
        """Extrae nombre del recurso desde el path."""
        # Remover parámetros y obtener última parte significativa
        clean_path = re.sub(r"/\{[^}]+\}", "", path)
        parts = [p for p in clean_path.split("/") if p]

        if parts:
            # Pluralizar/singularizar según contexto
            return parts[-1].replace("_", " ").replace("-", " ")

        return "recurso"

    def _extract_parameters(self, operation: dict[str, Any]) -> list[ToolParameter]:
        """
        Extrae y transforma parámetros de la operación.

        Args:
            operation: Diccionario de operación

        Returns:
            Lista de ToolParameter
        """
        parameters = []

        for param in operation.get("parameters", []):
            tool_param = self._transform_parameter(param)
            if tool_param:
                parameters.append(tool_param)

        return parameters

    def _transform_parameter(self, param: dict[str, Any]) -> ToolParameter | None:
        """
        Transforma un parámetro OpenAPI a ToolParameter.

        Args:
            param: Diccionario del parámetro

        Returns:
            ToolParameter o None si no se puede transformar
        """
        name = param.get("name")
        if not name:
            logger.warning("Parámetro sin nombre, omitiendo")
            return None

        # Determinar ubicación
        location_str = param.get("in", "query")
        try:
            location = ParameterLocation(location_str)
        except ValueError:
            logger.warning(f"Ubicación de parámetro desconocida: {location_str}")
            location = ParameterLocation.QUERY

        # Extraer schema
        schema = param.get("schema", {})
        param_type = schema.get("type", "string")
        param_format = schema.get("format")

        # Mapear tipo
        json_type = self.TYPE_MAPPING.get(param_type, "string")

        # Generar descripción
        description = param.get("description", "")
        if not description:
            description = f"Parámetro {name}"

        # Agregar información de formato si existe
        if param_format:
            description = f"{description} (formato: {param_format})"

        return ToolParameter(
            name=name,
            description=description,
            param_type=json_type,
            required=param.get("required", False),
            location=location,
            default=schema.get("default"),
            enum=schema.get("enum"),
            format=param_format,
            schema=self._extract_complex_schema(schema),
        )

    def _extract_complex_schema(self, schema: dict[str, Any]) -> dict[str, Any] | None:
        """Extrae schema complejo para arrays y objects."""
        schema_type = schema.get("type")

        if schema_type == "array":
            items = schema.get("items", {})
            return {
                "items": items,
                "minItems": schema.get("minItems"),
                "maxItems": schema.get("maxItems"),
            }

        elif schema_type == "object":
            return {
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
                "additionalProperties": schema.get("additionalProperties", True),
            }

        # Para tipos simples con constraints
        constraints = {}
        for key in ["minimum", "maximum", "minLength", "maxLength", "pattern"]:
            if key in schema:
                constraints[key] = schema[key]

        return constraints if constraints else None

    def _extract_request_body_schema(
        self,
        operation: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Extrae el schema del request body.

        Args:
            operation: Diccionario de operación

        Returns:
            Schema del body o None
        """
        request_body = operation.get("requestBody")
        if not request_body:
            return None

        content = request_body.get("content", {})

        # Priorizar application/json
        for media_type in ["application/json", "application/xml", "text/plain"]:
            if media_type in content:
                media_content = content[media_type]
                schema = media_content.get("schema", {})

                return {
                    "media_type": media_type,
                    "required": request_body.get("required", False),
                    "schema": schema,
                    "description": request_body.get("description", ""),
                }

        # Usar el primer content type disponible
        if content:
            first_type = next(iter(content))
            return {
                "media_type": first_type,
                "required": request_body.get("required", False),
                "schema": content[first_type].get("schema", {}),
                "description": request_body.get("description", ""),
            }

        return None

    def _extract_response_schema(
        self,
        operation: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Extrae el schema de la respuesta exitosa.

        Args:
            operation: Diccionario de operación

        Returns:
            Schema de respuesta o None
        """
        responses = operation.get("responses", {})

        # Buscar respuesta exitosa (2xx)
        for status_code in ["200", "201", "202", "204"]:
            if status_code in responses:
                response = responses[status_code]
                content = response.get("content", {})

                # Priorizar application/json
                for media_type in ["application/json", "application/xml"]:
                    if media_type in content:
                        return {
                            "status_code": status_code,
                            "media_type": media_type,
                            "schema": content[media_type].get("schema", {}),
                            "description": response.get("description", ""),
                        }

                # Respuesta sin body (ej: 204)
                if not content:
                    return {
                        "status_code": status_code,
                        "media_type": None,
                        "schema": None,
                        "description": response.get("description", ""),
                    }

        return None

    def get_tools_by_tag(self, tools: list[MCPTool]) -> dict[str, list[MCPTool]]:
        """
        Agrupa tools por tag.

        Args:
            tools: Lista de tools

        Returns:
            Diccionario tag -> lista de tools
        """
        result: dict[str, list[MCPTool]] = {}

        for tool in tools:
            if not tool.tags:
                if "other" not in result:
                    result["other"] = []
                result["other"].append(tool)
            else:
                for tag in tool.tags:
                    if tag not in result:
                        result[tag] = []
                    result[tag].append(tool)

        return result

    def get_tools_summary(self, tools: list[MCPTool]) -> dict[str, Any]:
        """
        Genera resumen de las tools generadas.

        Args:
            tools: Lista de tools

        Returns:
            Diccionario con estadísticas
        """
        methods_count = {}
        for tool in tools:
            method = tool.http_method.value
            methods_count[method] = methods_count.get(method, 0) + 1

        return {
            "total": len(tools),
            "by_method": methods_count,
            "by_tag": {
                tag: len(tag_tools)
                for tag, tag_tools in self.get_tools_by_tag(tools).items()
            },
            "deprecated": sum(1 for t in tools if t.deprecated),
            "with_body": sum(1 for t in tools if t.request_body_schema),
        }
