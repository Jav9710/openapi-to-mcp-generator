"""
Transformador de schemas OpenAPI a Resources MCP.

Convierte los schemas definidos en components/schemas de OpenAPI
en recursos MCP que el LLM puede consultar para entender la
estructura de datos.
"""

import logging
import re
from typing import Any

from ..models import MCPResource, MCPTool, OpenAPISpec

logger = logging.getLogger(__name__)


class ResourceTransformerError(Exception):
    """Error durante la transformación a resources."""
    pass


class ResourceTransformer:
    """
    Transforma schemas OpenAPI en recursos MCP.

    Los recursos MCP permiten al LLM consultar información sobre
    los modelos de datos, schemas y entidades de la API.

    Tipos de recursos generados:
    - Schema resources: Documentación de cada schema
    - Entity resources: Endpoints GET que retornan entidades
    - Collection resources: Endpoints GET que retornan listas

    Example:
        transformer = ResourceTransformer(service_prefix="users_api")
        resources = transformer.transform(openapi_spec, tools)
        for resource in resources:
            print(f"{resource.uri}: {resource.description}")
    """

    def __init__(
        self,
        service_prefix: str,
        include_internal_schemas: bool = False,
        generate_entity_resources: bool = True,
    ):
        """
        Inicializa el transformador.

        Args:
            service_prefix: Prefijo para URIs de recursos
            include_internal_schemas: Si incluir schemas internos (_internal, etc.)
            generate_entity_resources: Si generar resources para endpoints GET
        """
        self.service_prefix = self._sanitize_prefix(service_prefix)
        self.include_internal_schemas = include_internal_schemas
        self.generate_entity_resources = generate_entity_resources
        self._resource_uris: set[str] = set()

    def transform(
        self,
        spec: OpenAPISpec,
        tools: list[MCPTool] | None = None
    ) -> list[MCPResource]:
        """
        Transforma schemas y endpoints en recursos MCP.

        Args:
            spec: Especificación OpenAPI parseada
            tools: Lista de tools para identificar endpoints consultables

        Returns:
            Lista de MCPResource generados
        """
        resources = []
        self._resource_uris.clear()

        # 1. Generar recursos para schemas
        schema_resources = self._transform_schemas(spec.components_schemas)
        resources.extend(schema_resources)
        logger.info(f"Schema resources generados: {len(schema_resources)}")

        # 2. Generar recursos para entidades (endpoints GET)
        if self.generate_entity_resources and tools:
            entity_resources = self._transform_entity_endpoints(tools, spec)
            resources.extend(entity_resources)
            logger.info(f"Entity resources generados: {len(entity_resources)}")

        # 3. Generar recurso de documentación de la API
        api_doc_resource = self._generate_api_documentation_resource(spec)
        resources.append(api_doc_resource)

        logger.info(f"Total resources generados: {len(resources)}")
        return resources

    def _transform_schemas(
        self,
        schemas: dict[str, dict[str, Any]]
    ) -> list[MCPResource]:
        """
        Transforma schemas de OpenAPI en recursos.

        Args:
            schemas: Diccionario de schemas

        Returns:
            Lista de MCPResource para schemas
        """
        resources = []

        for schema_name, schema_def in schemas.items():
            # Filtrar schemas internos
            if not self.include_internal_schemas:
                if schema_name.startswith("_") or "internal" in schema_name.lower():
                    logger.debug(f"Omitiendo schema interno: {schema_name}")
                    continue

            resource = self._transform_schema(schema_name, schema_def)
            if resource:
                resources.append(resource)

        return resources

    def _transform_schema(
        self,
        schema_name: str,
        schema_def: dict[str, Any]
    ) -> MCPResource | None:
        """
        Transforma un schema individual en recurso.

        Args:
            schema_name: Nombre del schema
            schema_def: Definición del schema

        Returns:
            MCPResource o None
        """
        # Generar URI única
        uri = self._generate_schema_uri(schema_name)

        # Generar descripción
        description = self._generate_schema_description(schema_name, schema_def)

        # Determinar nombre legible
        readable_name = self._humanize_name(schema_name)

        return MCPResource(
            uri=uri,
            name=readable_name,
            description=description,
            mime_type="application/json",
            schema_name=schema_name,
            schema_definition=schema_def,
            is_collection=self._is_collection_schema(schema_def),
        )

    def _transform_entity_endpoints(
        self,
        tools: list[MCPTool],
        spec: OpenAPISpec
    ) -> list[MCPResource]:
        """
        Genera recursos para endpoints GET que retornan entidades.

        Args:
            tools: Lista de tools generadas
            spec: Especificación OpenAPI

        Returns:
            Lista de MCPResource para entidades
        """
        resources = []

        for tool in tools:
            # Solo endpoints GET
            if tool.http_method.value != "get":
                continue

            # Determinar si es consulta de entidad o colección
            is_collection = not self._has_path_params(tool.endpoint_path)

            resource = self._create_entity_resource(tool, is_collection)
            if resource:
                resources.append(resource)

        return resources

    def _create_entity_resource(
        self,
        tool: MCPTool,
        is_collection: bool
    ) -> MCPResource | None:
        """
        Crea un recurso para un endpoint GET.

        Args:
            tool: Tool del endpoint GET
            is_collection: Si es una colección

        Returns:
            MCPResource o None
        """
        # Generar URI
        path_clean = self._path_to_resource_path(tool.endpoint_path)
        uri = f"{self.service_prefix}://entities/{path_clean}"

        # Asegurar unicidad
        if uri in self._resource_uris:
            return None
        self._resource_uris.add(uri)

        # Generar descripción
        if is_collection:
            description = f"Colección de recursos. {tool.description}"
        else:
            description = f"Recurso individual. {tool.description}"

        # Obtener schema de respuesta
        response_schema = tool.response_schema or {}

        return MCPResource(
            uri=uri,
            name=self._humanize_name(path_clean),
            description=description,
            mime_type="application/json",
            schema_definition=response_schema.get("schema", {}),
            endpoint_path=tool.endpoint_path,
            is_collection=is_collection,
        )

    def _generate_api_documentation_resource(
        self,
        spec: OpenAPISpec
    ) -> MCPResource:
        """
        Genera recurso con documentación general de la API.

        Args:
            spec: Especificación OpenAPI

        Returns:
            MCPResource con documentación
        """
        uri = f"{self.service_prefix}://documentation/api-info"

        # Construir contenido de documentación
        doc_content = {
            "title": spec.title,
            "version": spec.version,
            "description": spec.description,
            "servers": [
                {"url": s.url, "description": s.description}
                for s in spec.servers
            ],
            "tags": spec.tags,
            "total_endpoints": sum(len(ops) for ops in spec.paths.values()),
            "total_schemas": len(spec.components_schemas),
            "security_schemes": list(spec.security_schemes.keys()),
        }

        description = f"""
Documentación de la API {spec.title} v{spec.version}.

{spec.description or 'Sin descripción'}

Esta API tiene {doc_content['total_endpoints']} endpoints y {doc_content['total_schemas']} schemas definidos.
        """.strip()

        return MCPResource(
            uri=uri,
            name=f"Documentación {spec.title}",
            description=description,
            mime_type="application/json",
            schema_definition=doc_content,
        )

    def _generate_schema_uri(self, schema_name: str) -> str:
        """Genera URI única para un schema."""
        safe_name = self._sanitize_name(schema_name)
        uri = f"{self.service_prefix}://schemas/{safe_name}"

        # Asegurar unicidad
        base_uri = uri
        counter = 1
        while uri in self._resource_uris:
            uri = f"{base_uri}_{counter}"
            counter += 1

        self._resource_uris.add(uri)
        return uri

    def _generate_schema_description(
        self,
        schema_name: str,
        schema_def: dict[str, Any]
    ) -> str:
        """
        Genera descripción detallada para un schema.

        Args:
            schema_name: Nombre del schema
            schema_def: Definición del schema

        Returns:
            Descripción para el LLM
        """
        parts = []

        # Descripción del schema si existe
        if "description" in schema_def:
            parts.append(schema_def["description"])

        # Tipo de schema
        schema_type = schema_def.get("type", "object")
        parts.append(f"Tipo: {schema_type}")

        # Propiedades para objetos
        if schema_type == "object":
            properties = schema_def.get("properties", {})
            required = schema_def.get("required", [])

            if properties:
                props_desc = []
                for prop_name, prop_def in properties.items():
                    prop_type = prop_def.get("type", "any")
                    prop_desc = prop_def.get("description", "")
                    is_required = "requerido" if prop_name in required else "opcional"

                    props_desc.append(
                        f"- {prop_name} ({prop_type}, {is_required}): {prop_desc}"
                    )

                parts.append(f"Propiedades:\n" + "\n".join(props_desc[:10]))

                if len(properties) > 10:
                    parts.append(f"... y {len(properties) - 10} propiedades más")

        # Enum values
        if "enum" in schema_def:
            enum_values = schema_def["enum"]
            parts.append(f"Valores permitidos: {', '.join(str(v) for v in enum_values[:10])}")

        # Items para arrays
        if schema_type == "array" and "items" in schema_def:
            items = schema_def["items"]
            items_type = items.get("type", "object")
            items_ref = items.get("$ref", "")
            if items_ref:
                items_type = items_ref.split("/")[-1]
            parts.append(f"Array de: {items_type}")

        return "\n\n".join(parts) if parts else f"Schema {schema_name}"

    def _is_collection_schema(self, schema_def: dict[str, Any]) -> bool:
        """Determina si un schema representa una colección."""
        # Es array
        if schema_def.get("type") == "array":
            return True

        # Tiene propiedades típicas de paginación
        props = schema_def.get("properties", {})
        pagination_props = {"items", "data", "results", "records", "content"}
        if pagination_props.intersection(props.keys()):
            return True

        return False

    def _has_path_params(self, path: str) -> bool:
        """Verifica si el path tiene parámetros."""
        return "{" in path and "}" in path

    def _path_to_resource_path(self, path: str) -> str:
        """Convierte un path de API a path de recurso."""
        # Remover parámetros
        clean = re.sub(r"/\{[^}]+\}", "", path)
        # Limpiar
        clean = clean.strip("/").replace("/", "_")
        return self._sanitize_name(clean)

    def _sanitize_name(self, name: str) -> str:
        """Sanitiza nombre para uso en URIs."""
        # Convertir camelCase a snake_case
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
        name = name.lower()

        # Reemplazar caracteres no válidos
        name = re.sub(r"[^a-z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")

        return name

    def _sanitize_prefix(self, prefix: str) -> str:
        """Sanitiza prefijo del servicio."""
        return self._sanitize_name(prefix)

    def _humanize_name(self, name: str) -> str:
        """Convierte nombre técnico a legible."""
        # Reemplazar guiones bajos
        name = name.replace("_", " ")
        # Capitalizar palabras
        return " ".join(word.capitalize() for word in name.split())

    def get_resources_by_type(
        self,
        resources: list[MCPResource]
    ) -> dict[str, list[MCPResource]]:
        """
        Agrupa recursos por tipo.

        Args:
            resources: Lista de recursos

        Returns:
            Diccionario tipo -> lista de recursos
        """
        result: dict[str, list[MCPResource]] = {
            "schemas": [],
            "entities": [],
            "collections": [],
            "documentation": [],
        }

        for resource in resources:
            if "schemas" in resource.uri:
                result["schemas"].append(resource)
            elif "documentation" in resource.uri:
                result["documentation"].append(resource)
            elif resource.is_collection:
                result["collections"].append(resource)
            else:
                result["entities"].append(resource)

        return result

    def get_resources_summary(self, resources: list[MCPResource]) -> dict[str, Any]:
        """
        Genera resumen de los recursos generados.

        Args:
            resources: Lista de recursos

        Returns:
            Diccionario con estadísticas
        """
        by_type = self.get_resources_by_type(resources)

        return {
            "total": len(resources),
            "schemas": len(by_type["schemas"]),
            "entities": len(by_type["entities"]),
            "collections": len(by_type["collections"]),
            "documentation": len(by_type["documentation"]),
            "with_endpoints": sum(1 for r in resources if r.endpoint_path),
        }
