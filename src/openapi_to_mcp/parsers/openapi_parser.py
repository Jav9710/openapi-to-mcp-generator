"""
Parser de especificaciones OpenAPI 3.0 y 3.1.

Extrae y valida todos los componentes relevantes de una especificación
OpenAPI para su transformación a servidor MCP.
"""

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

from ..models import (
    OpenAPISpec,
    SecurityScheme,
    SecuritySchemeType,
    ServerInfo,
)

logger = logging.getLogger(__name__)

# Marcador sentinela para detectar referencias circulares durante resolución
_RESOLVING_MARKER = object()


class OpenAPIParserError(Exception):
    """Error durante el parsing de OpenAPI."""

    def __init__(
        self,
        message: str,
        context: str | None = None,
        suggestion: str | None = None,
        docs_url: str | None = None,
    ):
        """
        Error de parsing con contexto y sugerencias.

        Args:
            message: Mensaje principal del error
            context: Contexto adicional (qué estaba haciendo)
            suggestion: Sugerencia de cómo arreglar el error
            docs_url: URL de documentación relevante
        """
        self.message = message
        self.context = context
        self.suggestion = suggestion
        self.docs_url = docs_url

        # Construir mensaje completo
        full_message = message
        if context:
            full_message += f"\n  Contexto: {context}"
        if suggestion:
            full_message += f"\n  Sugerencia: {suggestion}"
        if docs_url:
            full_message += f"\n  Documentación: {docs_url}"

        super().__init__(full_message)


class OpenAPIParser:
    """
    Parser de especificaciones OpenAPI 3.0.x y 3.1.x.

    Extrae paths, operaciones, schemas, security schemes y metadatos
    de archivos YAML o JSON de OpenAPI.

    Example:
        parser = OpenAPIParser()
        spec = parser.parse("api-spec.yaml")
        print(f"API: {spec.title} v{spec.version}")
        print(f"Endpoints: {len(spec.paths)}")
    """

    SUPPORTED_VERSIONS = ["3.0", "3.1"]

    def __init__(self, strict_validation: bool = True):
        """
        Inicializa el parser.

        Args:
            strict_validation: Si es True, valida estrictamente contra el spec OpenAPI
        """
        self.strict_validation = strict_validation
        self._ref_cache: dict[str, Any] = {}

    def parse(self, spec_path: str | Path) -> OpenAPISpec:
        """
        Parsea un archivo de especificación OpenAPI.

        Args:
            spec_path: Ruta al archivo YAML o JSON

        Returns:
            OpenAPISpec con toda la información extraída

        Raises:
            OpenAPIParserError: Si hay errores de validación o parsing
        """
        spec_path = Path(spec_path)

        if not spec_path.exists():
            raise OpenAPIParserError(
                message=f"Archivo no encontrado: {spec_path}",
                context="Intentando cargar especificación OpenAPI",
                suggestion="Verifica que la ruta del archivo sea correcta y que el archivo exista",
            )

        logger.info(f"Parsing OpenAPI spec: {spec_path}")

        # Cargar el contenido
        raw_spec = self._load_spec_file(spec_path)

        # Validar versión
        self._validate_version(raw_spec)

        # Validar contra OpenAPI spec si está habilitado
        if self.strict_validation:
            self._validate_spec(spec_path)

        # Resolver referencias $ref
        resolved_spec = self._resolve_references(raw_spec, raw_spec)

        # Extraer componentes
        return self._extract_spec(resolved_spec)

    def parse_from_string(self, content: str, format: str = "yaml") -> OpenAPISpec:
        """
        Parsea una especificación OpenAPI desde string.

        Args:
            content: Contenido de la especificación
            format: Formato del contenido ('yaml' o 'json')

        Returns:
            OpenAPISpec parseado
        """
        if format.lower() == "json":
            raw_spec = json.loads(content)
        else:
            raw_spec = yaml.safe_load(content)

        self._validate_version(raw_spec)
        resolved_spec = self._resolve_references(raw_spec, raw_spec)
        return self._extract_spec(resolved_spec)

    def parse_from_dict(self, spec_dict: dict[str, Any]) -> OpenAPISpec:
        """
        Parsea una especificación OpenAPI desde diccionario.

        Args:
            spec_dict: Diccionario con la especificación

        Returns:
            OpenAPISpec parseado
        """
        self._validate_version(spec_dict)
        resolved_spec = self._resolve_references(spec_dict, spec_dict)
        return self._extract_spec(resolved_spec)

    def _load_spec_file(self, spec_path: Path) -> dict[str, Any]:
        """Carga el archivo de especificación."""
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()

            if spec_path.suffix.lower() in [".yaml", ".yml"]:
                return yaml.safe_load(content)
            elif spec_path.suffix.lower() == ".json":
                return json.loads(content)
            else:
                # Intentar YAML primero, luego JSON
                try:
                    return yaml.safe_load(content)
                except yaml.YAMLError:
                    return json.loads(content)

        except Exception as e:
            raise OpenAPIParserError(
                message=f"Error cargando archivo",
                context=f"Intentando leer {spec_path}",
                suggestion="Verifica que el archivo sea un YAML o JSON válido. Error original: " + str(e),
            )

    def _validate_version(self, spec: dict[str, Any]) -> None:
        """Valida que la versión de OpenAPI sea soportada."""
        openapi_version = spec.get("openapi", "")

        if not openapi_version:
            raise OpenAPIParserError(
                message="Campo 'openapi' no encontrado en la especificación",
                context="Validando versión de OpenAPI",
                suggestion="Asegúrate de que sea un archivo OpenAPI 3.0+ válido (no Swagger 2.0). "
                          "El archivo debe tener 'openapi: 3.0.x' o 'openapi: 3.1.x' en la raíz.",
                docs_url="https://spec.openapi.org/oas/latest.html#openapi-object",
            )

        major_minor = ".".join(openapi_version.split(".")[:2])

        if major_minor not in self.SUPPORTED_VERSIONS:
            raise OpenAPIParserError(
                message=f"Versión OpenAPI {openapi_version} no soportada",
                context=f"Versiones soportadas: {', '.join(self.SUPPORTED_VERSIONS)}",
                suggestion="Convierte tu especificación a OpenAPI 3.0 o 3.1. "
                          "Si tienes Swagger 2.0, usa herramientas como swagger2openapi para convertirlo.",
                docs_url="https://github.com/Mermade/oas-kit/tree/main/packages/swagger2openapi",
            )

        logger.debug(f"OpenAPI version: {openapi_version}")

    def _validate_spec(self, spec_path: Path) -> None:
        """Valida la especificación contra el schema OpenAPI."""
        try:
            spec_dict, spec_url = read_from_filename(str(spec_path))
            validate(spec_dict)
            logger.debug("Validación OpenAPI exitosa")
        except Exception as e:
            error_msg = str(e)
            # Extraer información útil del error si es posible
            suggestion = "Revisa la especificación OpenAPI y corrige los errores de validación. "
            if "required property" in error_msg.lower():
                suggestion += "Faltan propiedades requeridas. "
            elif "schema" in error_msg.lower():
                suggestion += "Verifica que los schemas estén correctamente definidos. "

            raise OpenAPIParserError(
                message="Validación OpenAPI fallida",
                context=error_msg[:200],  # Limitar contexto a 200 caracteres
                suggestion=suggestion + "Usa --skip-validation para omitir validación estricta si es necesario.",
                docs_url="https://spec.openapi.org/oas/latest.html",
            )

    def _resolve_references(
        self,
        obj: Any,
        root_spec: dict[str, Any],
        path: str = "#"
    ) -> Any:
        """
        Resuelve referencias $ref de forma recursiva.

        Args:
            obj: Objeto a resolver
            root_spec: Especificación raíz para resolver refs locales
            path: Path actual para debugging

        Returns:
            Objeto con referencias resueltas
        """
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                return self._resolve_ref(ref, root_spec)

            return {
                key: self._resolve_references(value, root_spec, f"{path}/{key}")
                for key, value in obj.items()
            }

        elif isinstance(obj, list):
            return [
                self._resolve_references(item, root_spec, f"{path}[{i}]")
                for i, item in enumerate(obj)
            ]

        return obj

    def _resolve_ref(self, ref: str, root_spec: dict[str, Any]) -> Any:
        """
        Resuelve una referencia $ref específica.

        Args:
            ref: String de referencia (ej: "#/components/schemas/User")
            root_spec: Especificación raíz

        Returns:
            Objeto referenciado resuelto
        """
        # Cache para evitar resolver la misma ref múltiples veces
        if ref in self._ref_cache:
            cached = self._ref_cache[ref]
            # Si encontramos el marcador de ciclo, devolver referencia sin resolver
            if cached is _RESOLVING_MARKER:
                return {"$ref": ref, "_circular": True}
            return cached

        if not ref.startswith("#/"):
            # Referencias externas no soportadas por ahora
            logger.warning(f"Referencia externa no soportada: {ref}")
            return {"$ref": ref, "_unresolved": True}

        # Navegar por el path
        path_parts = ref[2:].split("/")
        current = root_spec

        for part in path_parts:
            # Decodificar caracteres especiales de JSON Pointer
            part = part.replace("~1", "/").replace("~0", "~")

            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                logger.warning(f"Referencia no encontrada: {ref}")
                return {"$ref": ref, "_unresolved": True}

        # Marcar como "resolviendo" ANTES de resolver recursivamente
        # Esto previene recursión infinita en referencias circulares
        self._ref_cache[ref] = _RESOLVING_MARKER

        # Resolver recursivamente (para refs anidadas)
        resolved = self._resolve_references(current, root_spec, ref)
        self._ref_cache[ref] = resolved

        return resolved

    def _extract_spec(self, spec: dict[str, Any]) -> OpenAPISpec:
        """
        Extrae todos los componentes de la especificación.

        Args:
            spec: Especificación con refs resueltas

        Returns:
            OpenAPISpec con toda la información
        """
        info = spec.get("info", {})

        return OpenAPISpec(
            title=info.get("title", "Unknown API"),
            version=info.get("version", "0.0.0"),
            description=info.get("description"),
            servers=self._extract_servers(spec.get("servers", [])),
            paths=self._extract_paths(spec.get("paths", {})),
            components_schemas=self._extract_schemas(spec),
            security_schemes=self._extract_security_schemes(spec),
            global_security=spec.get("security", []),
            tags=spec.get("tags", []),
            openapi_version=spec.get("openapi", "3.0.0"),
        )

    def _extract_servers(self, servers: list[dict]) -> list[ServerInfo]:
        """Extrae información de servidores."""
        result = []
        for server in servers:
            result.append(ServerInfo(
                url=server.get("url", ""),
                description=server.get("description"),
                variables=server.get("variables", {}),
            ))
        return result

    def _extract_paths(self, paths: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extrae y normaliza operaciones por path.

        Preserva toda la información de cada operación incluyendo
        parámetros, requestBody, responses, security, etc.
        """
        result = {}

        for path, path_item in paths.items():
            if path.startswith("x-"):
                continue  # Ignorar extensiones

            result[path] = {}

            # Parámetros a nivel de path (aplican a todas las operaciones)
            path_params = path_item.get("parameters", [])

            # Procesar cada método HTTP
            for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method].copy()

                # Merge parámetros de path con parámetros de operación
                op_params = operation.get("parameters", [])
                merged_params = self._merge_parameters(path_params, op_params)
                operation["parameters"] = merged_params

                # Normalizar requestBody
                if "requestBody" in operation:
                    operation["requestBody"] = self._normalize_request_body(
                        operation["requestBody"]
                    )

                # Normalizar responses
                if "responses" in operation:
                    operation["responses"] = self._normalize_responses(
                        operation["responses"]
                    )

                result[path][method] = operation

        return result

    def _merge_parameters(
        self,
        path_params: list[dict],
        op_params: list[dict]
    ) -> list[dict]:
        """
        Combina parámetros de path y operación.

        Los parámetros de operación sobrescriben los de path con el mismo nombre.
        """
        params_dict = {}

        # Primero agregar parámetros de path
        for param in path_params:
            key = f"{param.get('name')}_{param.get('in')}"
            params_dict[key] = param

        # Luego sobrescribir con parámetros de operación
        for param in op_params:
            key = f"{param.get('name')}_{param.get('in')}"
            params_dict[key] = param

        return list(params_dict.values())

    def _normalize_request_body(self, request_body: dict[str, Any]) -> dict[str, Any]:
        """Normaliza el requestBody para extracción uniforme."""
        normalized = {
            "required": request_body.get("required", False),
            "description": request_body.get("description", ""),
            "content": {},
        }

        content = request_body.get("content", {})
        for media_type, media_config in content.items():
            normalized["content"][media_type] = {
                "schema": media_config.get("schema", {}),
                "example": media_config.get("example"),
                "examples": media_config.get("examples", {}),
            }

        return normalized

    def _normalize_responses(
        self,
        responses: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Normaliza las responses para extracción uniforme."""
        normalized = {}

        for status_code, response in responses.items():
            normalized[status_code] = {
                "description": response.get("description", ""),
                "content": {},
                "headers": response.get("headers", {}),
            }

            content = response.get("content", {})
            for media_type, media_config in content.items():
                normalized[status_code]["content"][media_type] = {
                    "schema": media_config.get("schema", {}),
                    "example": media_config.get("example"),
                    "examples": media_config.get("examples", {}),
                }

        return normalized

    def _extract_schemas(self, spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Extrae schemas de components."""
        components = spec.get("components", {})
        return components.get("schemas", {})

    def _extract_security_schemes(
        self,
        spec: dict[str, Any]
    ) -> dict[str, SecurityScheme]:
        """Extrae y parsea security schemes."""
        components = spec.get("components", {})
        raw_schemes = components.get("securitySchemes", {})
        result = {}

        for name, scheme in raw_schemes.items():
            scheme_type_str = scheme.get("type", "")

            try:
                scheme_type = SecuritySchemeType(scheme_type_str)
            except ValueError:
                logger.warning(f"Tipo de security scheme desconocido: {scheme_type_str}")
                continue

            result[name] = SecurityScheme(
                name=name,
                scheme_type=scheme_type,
                location=scheme.get("in"),
                param_name=scheme.get("name"),
                scheme=scheme.get("scheme"),
                bearer_format=scheme.get("bearerFormat"),
                flows=scheme.get("flows"),
                openid_connect_url=scheme.get("openIdConnectUrl"),
                description=scheme.get("description"),
            )

        return result

    def get_operation_count(self, spec: OpenAPISpec) -> int:
        """Cuenta el total de operaciones en la especificación."""
        count = 0
        for path_operations in spec.paths.values():
            count += len(path_operations)
        return count

    def get_operations_by_tag(
        self,
        spec: OpenAPISpec
    ) -> dict[str, list[tuple[str, str, dict]]]:
        """
        Agrupa operaciones por tag.

        Returns:
            Dict con tag como key y lista de (path, method, operation) como value
        """
        result: dict[str, list[tuple[str, str, dict]]] = {"untagged": []}

        for path, operations in spec.paths.items():
            for method, operation in operations.items():
                tags = operation.get("tags", [])

                if not tags:
                    result["untagged"].append((path, method, operation))
                else:
                    for tag in tags:
                        if tag not in result:
                            result[tag] = []
                        result[tag].append((path, method, operation))

        # Eliminar untagged si está vacío
        if not result["untagged"]:
            del result["untagged"]

        return result
