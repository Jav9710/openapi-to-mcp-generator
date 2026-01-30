"""
Validador detallado de especificaciones OpenAPI.

Proporciona validación en tiempo real con errores, warnings y sugerencias.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Severidad de un problema de validación."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class ValidationIssue:
    """Representa un problema encontrado durante la validación."""
    severity: IssueSeverity
    message: str
    path: str = ""  # JSON path al elemento problemático
    line: int | None = None  # Línea en el archivo original (si está disponible)
    suggestion: str | None = None  # Sugerencia para corregir el problema
    code: str = ""  # Código único del error (ej: "MISSING_OPERATION_ID")

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "suggestion": self.suggestion,
            "code": self.code,
        }


@dataclass
class ValidationResult:
    """Resultado de la validación de una especificación."""
    valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]

    @property
    def suggestions(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.SUGGESTION]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "suggestion_count": len(self.suggestions),
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }


class OpenAPIValidator:
    """
    Validador completo de especificaciones OpenAPI.

    Realiza múltiples tipos de validación:
    - Estructura básica (requerida para OpenAPI)
    - Mejores prácticas (operationId, descripciones, etc.)
    - Seguridad (esquemas de autenticación)
    - MCP-específico (endpoints compatibles con tools)
    """

    def __init__(self, check_best_practices: bool = True):
        """
        Inicializa el validador.

        Args:
            check_best_practices: Si incluir verificaciones de mejores prácticas
        """
        self.check_best_practices = check_best_practices

    def validate_file(self, file_path: str | Path) -> ValidationResult:
        """
        Valida un archivo de especificación OpenAPI.

        Args:
            file_path: Ruta al archivo YAML o JSON

        Returns:
            ValidationResult con todos los problemas encontrados
        """
        file_path = Path(file_path)
        result = ValidationResult()

        # Verificar que el archivo existe
        if not file_path.exists():
            result.valid = False
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Archivo no encontrado: {file_path}",
                code="FILE_NOT_FOUND"
            ))
            return result

        # Cargar y parsear el archivo
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if file_path.suffix.lower() in [".yaml", ".yml"]:
                spec = yaml.safe_load(content)
            else:
                spec = json.loads(content)

        except yaml.YAMLError as e:
            result.valid = False
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Error de sintaxis YAML: {str(e)}",
                code="YAML_SYNTAX_ERROR"
            ))
            return result
        except json.JSONDecodeError as e:
            result.valid = False
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Error de sintaxis JSON: {str(e)}",
                line=e.lineno,
                code="JSON_SYNTAX_ERROR"
            ))
            return result

        return self.validate_spec(spec)

    def validate_content(self, content: str, format: str = "yaml") -> ValidationResult:
        """
        Valida contenido de especificación desde string.

        Args:
            content: Contenido de la especificación
            format: 'yaml' o 'json'

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        try:
            if format.lower() == "json":
                spec = json.loads(content)
            else:
                spec = yaml.safe_load(content)
        except Exception as e:
            result.valid = False
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message=f"Error de sintaxis: {str(e)}",
                code="SYNTAX_ERROR"
            ))
            return result

        return self.validate_spec(spec)

    def validate_spec(self, spec: dict[str, Any]) -> ValidationResult:
        """
        Valida una especificación OpenAPI como diccionario.

        Args:
            spec: Diccionario con la especificación

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not spec:
            result.valid = False
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message="La especificación está vacía",
                code="EMPTY_SPEC"
            ))
            return result

        # Validaciones estructurales (errores)
        self._validate_structure(spec, result)

        # Validaciones de OpenAPI spec
        self._validate_openapi_compliance(spec, result)

        # Validaciones de mejores prácticas (warnings/suggestions)
        if self.check_best_practices:
            self._validate_best_practices(spec, result)

        # Validaciones específicas para MCP
        self._validate_mcp_compatibility(spec, result)

        # Calcular estadísticas
        result.stats = self._calculate_stats(spec)

        # Si hay errores, marcar como inválido
        if result.error_count > 0:
            result.valid = False

        return result

    def _validate_structure(self, spec: dict, result: ValidationResult):
        """Valida la estructura básica requerida."""
        # openapi version
        if "openapi" not in spec:
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message="Falta el campo 'openapi' con la versión",
                path="openapi",
                code="MISSING_OPENAPI_VERSION",
                suggestion="Agrega 'openapi: \"3.0.3\"' o 'openapi: \"3.1.0\"' al inicio del archivo"
            ))
        else:
            version = str(spec.get("openapi", ""))
            if not version.startswith(("3.0", "3.1")):
                result.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    message=f"Versión de OpenAPI no soportada: {version}. Se requiere 3.0.x o 3.1.x",
                    path="openapi",
                    code="UNSUPPORTED_VERSION",
                    suggestion="Usa 'openapi: \"3.0.3\"' o 'openapi: \"3.1.0\"'"
                ))

        # info
        if "info" not in spec:
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message="Falta la sección 'info'",
                path="info",
                code="MISSING_INFO",
                suggestion="Agrega la sección 'info' con 'title' y 'version'"
            ))
        else:
            info = spec.get("info", {})
            if "title" not in info:
                result.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    message="Falta 'title' en la sección info",
                    path="info.title",
                    code="MISSING_TITLE"
                ))
            if "version" not in info:
                result.issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    message="Falta 'version' en la sección info",
                    path="info.version",
                    code="MISSING_VERSION"
                ))

        # paths
        if "paths" not in spec:
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                message="Falta la sección 'paths'",
                path="paths",
                code="MISSING_PATHS",
                suggestion="Agrega la sección 'paths' con al menos un endpoint"
            ))
        elif not spec.get("paths"):
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                message="La sección 'paths' está vacía",
                path="paths",
                code="EMPTY_PATHS"
            ))

    def _validate_openapi_compliance(self, spec: dict, result: ValidationResult):
        """Valida cumplimiento con OpenAPI spec."""
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Validar path parameters
            path_params = re.findall(r"\{(\w+)\}", path)

            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    result.issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        message=f"Operación inválida (no es un objeto)",
                        path=f"paths.{path}.{method}",
                        code="INVALID_OPERATION"
                    ))
                    continue

                # Verificar que los path parameters estén definidos
                op_params = operation.get("parameters", [])
                defined_path_params = [
                    p.get("name") for p in op_params
                    if isinstance(p, dict) and p.get("in") == "path"
                ]

                for param in path_params:
                    if param not in defined_path_params:
                        result.issues.append(ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            message=f"Path parameter '{{{param}}}' no está definido en la operación",
                            path=f"paths.{path}.{method}.parameters",
                            code="UNDEFINED_PATH_PARAM",
                            suggestion=f"Agrega el parámetro: {{ name: {param}, in: path, required: true }}"
                        ))

                # Verificar responses
                if "responses" not in operation:
                    result.issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        message="Falta la sección 'responses'",
                        path=f"paths.{path}.{method}.responses",
                        code="MISSING_RESPONSES",
                        suggestion="Agrega al menos una respuesta (ej: 200, default)"
                    ))

    def _validate_best_practices(self, spec: dict, result: ValidationResult):
        """Valida mejores prácticas de OpenAPI."""
        paths = spec.get("paths", {})
        info = spec.get("info", {})

        # Info description
        if "description" not in info:
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.SUGGESTION,
                message="Considera agregar una descripción a la API",
                path="info.description",
                code="MISSING_API_DESCRIPTION",
                suggestion="Agrega 'description' en la sección info para documentar tu API"
            ))

        # Servers
        if "servers" not in spec or not spec.get("servers"):
            result.issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                message="No hay servidores definidos",
                path="servers",
                code="MISSING_SERVERS",
                suggestion="Agrega la sección 'servers' con la URL base de tu API"
            ))

        operation_ids = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue

                op_path = f"paths.{path}.{method}"

                # operationId
                if "operationId" not in operation:
                    result.issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        message=f"Falta 'operationId' en {method.upper()} {path}",
                        path=f"{op_path}.operationId",
                        code="MISSING_OPERATION_ID",
                        suggestion="Agrega un operationId único para generar nombres de tools legibles"
                    ))
                else:
                    op_id = operation["operationId"]
                    if op_id in operation_ids:
                        result.issues.append(ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            message=f"operationId duplicado: '{op_id}'",
                            path=f"{op_path}.operationId",
                            code="DUPLICATE_OPERATION_ID"
                        ))
                    operation_ids.append(op_id)

                # summary/description
                if "summary" not in operation and "description" not in operation:
                    result.issues.append(ValidationIssue(
                        severity=IssueSeverity.SUGGESTION,
                        message=f"Considera agregar 'summary' o 'description' a {method.upper()} {path}",
                        path=f"{op_path}",
                        code="MISSING_OPERATION_DOCS",
                        suggestion="Las descripciones ayudan a los LLMs a entender cuándo usar cada tool"
                    ))

                # Parámetros sin descripción
                for i, param in enumerate(operation.get("parameters", [])):
                    if isinstance(param, dict) and "description" not in param:
                        param_name = param.get("name", f"[{i}]")
                        result.issues.append(ValidationIssue(
                            severity=IssueSeverity.SUGGESTION,
                            message=f"Parámetro '{param_name}' sin descripción",
                            path=f"{op_path}.parameters[{i}].description",
                            code="MISSING_PARAM_DESCRIPTION"
                        ))

    def _validate_mcp_compatibility(self, spec: dict, result: ValidationResult):
        """Valida compatibilidad específica con MCP."""
        paths = spec.get("paths", {})

        # Verificar endpoints que podrían tener problemas con MCP
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ["get", "post", "put", "patch", "delete"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue

                # File uploads
                request_body = operation.get("requestBody", {})
                content = request_body.get("content", {}) if isinstance(request_body, dict) else {}

                if "multipart/form-data" in content:
                    result.issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        message=f"File upload detectado en {method.upper()} {path}",
                        path=f"paths.{path}.{method}.requestBody",
                        code="FILE_UPLOAD_DETECTED",
                        suggestion="Los file uploads pueden requerir manejo especial en MCP"
                    ))

                # Streaming responses
                responses = operation.get("responses", {})
                for status, response in responses.items():
                    if not isinstance(response, dict):
                        continue
                    resp_content = response.get("content", {})
                    if "text/event-stream" in resp_content or "application/octet-stream" in resp_content:
                        result.issues.append(ValidationIssue(
                            severity=IssueSeverity.INFO,
                            message=f"Streaming response detectado en {method.upper()} {path}",
                            path=f"paths.{path}.{method}.responses.{status}",
                            code="STREAMING_RESPONSE"
                        ))

        # Security schemes
        security_schemes = spec.get("components", {}).get("securitySchemes", {})
        if security_schemes:
            for name, scheme in security_schemes.items():
                if not isinstance(scheme, dict):
                    continue

                scheme_type = scheme.get("type", "")

                if scheme_type == "oauth2":
                    flows = scheme.get("flows", {})
                    if "authorizationCode" in flows or "implicit" in flows:
                        result.issues.append(ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            message=f"OAuth2 con flujo interactivo detectado: {name}",
                            path=f"components.securitySchemes.{name}",
                            code="INTERACTIVE_OAUTH",
                            suggestion="Los flujos OAuth2 interactivos requieren configuración manual"
                        ))

    def _calculate_stats(self, spec: dict) -> dict[str, Any]:
        """Calcula estadísticas de la especificación."""
        paths = spec.get("paths", {})
        methods_count = {"get": 0, "post": 0, "put": 0, "patch": 0, "delete": 0, "head": 0, "options": 0}
        tags = set()
        total_endpoints = 0
        deprecated_count = 0

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in methods_count.keys():
                if method in path_item:
                    methods_count[method] += 1
                    total_endpoints += 1

                    operation = path_item[method]
                    if isinstance(operation, dict):
                        if operation.get("deprecated"):
                            deprecated_count += 1
                        for tag in operation.get("tags", []):
                            tags.add(tag)

        return {
            "total_endpoints": total_endpoints,
            "total_paths": len(paths),
            "methods": methods_count,
            "tags": list(tags),
            "tags_count": len(tags),
            "deprecated_count": deprecated_count,
            "has_security": bool(spec.get("components", {}).get("securitySchemes")),
            "has_servers": bool(spec.get("servers")),
            "openapi_version": spec.get("openapi", "unknown"),
        }
