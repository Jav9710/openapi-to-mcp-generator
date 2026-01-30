"""
MCP Utility Scorer - Evalúa la utilidad de un OpenAPI para generar MCP.

Analiza la completitud de la especificación y genera un score de utilidad
para determinar qué tan efectivo será el MCP generado para los LLMs.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssuePriority(str, Enum):
    """Prioridad de un problema de completitud."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class EndpointIssue:
    """Problema en un endpoint específico."""
    method: str
    path: str
    missing_fields: list[str] = field(default_factory=list)
    suggested_values: dict[str, Any] = field(default_factory=dict)
    priority: IssuePriority = IssuePriority.MEDIUM

    @property
    def endpoint_key(self) -> str:
        return f"{self.method.upper()} {self.path}"

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "path": self.path,
            "endpoint_key": self.endpoint_key,
            "missing_fields": self.missing_fields,
            "suggested_values": self.suggested_values,
            "priority": self.priority.value,
        }


@dataclass
class CategoryScore:
    """Puntuación de una categoría específica."""
    name: str
    score: int  # 0-100
    total_items: int
    complete_items: int
    weight: float  # Peso en el score total

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": self.score,
            "total_items": self.total_items,
            "complete_items": self.complete_items,
            "weight": self.weight,
        }


@dataclass
class MCPUtilityScore:
    """Puntuación de utilidad para MCP."""
    overall_score: int = 0  # 0-100
    grade: str = "F"  # A, B, C, D, F

    # Desglose por categoría
    categories: dict[str, CategoryScore] = field(default_factory=dict)

    # Endpoints que necesitan atención
    incomplete_endpoints: list[EndpointIssue] = field(default_factory=list)

    # Recomendaciones generales
    recommendations: list[str] = field(default_factory=list)

    # Estadísticas
    total_endpoints: int = 0
    endpoints_needing_attention: int = 0

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "incomplete_endpoints": [e.to_dict() for e in self.incomplete_endpoints],
            "recommendations": self.recommendations,
            "total_endpoints": self.total_endpoints,
            "endpoints_needing_attention": self.endpoints_needing_attention,
        }


@dataclass
class EnrichmentData:
    """Datos para enriquecer un endpoint."""
    method: str
    path: str
    description: str | None = None
    summary: str | None = None
    operation_id: str | None = None
    tags: list[str] = field(default_factory=list)
    parameter_descriptions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "path": self.path,
            "description": self.description,
            "summary": self.summary,
            "operation_id": self.operation_id,
            "tags": self.tags,
            "parameter_descriptions": self.parameter_descriptions,
        }


class MCPUtilityScorer:
    """
    Evalúa la utilidad de una especificación OpenAPI para generar MCP.

    Analiza múltiples aspectos:
    - Descripciones de endpoints (crítico para LLMs)
    - OperationIds (nombres de tools)
    - Tags (organización)
    - Ejemplos (comprensión del formato)
    - Documentación de parámetros
    """

    # Pesos para cada categoría (deben sumar 1.0)
    CATEGORY_WEIGHTS = {
        "descriptions": 0.35,  # Más importante para LLMs
        "operation_ids": 0.25,
        "tags": 0.15,
        "parameters": 0.15,
        "examples": 0.10,
    }

    # Umbrales para grades
    GRADE_THRESHOLDS = {
        "A": 90,
        "B": 75,
        "C": 60,
        "D": 40,
        "F": 0,
    }

    def __init__(self):
        pass

    def calculate_score(self, spec: dict[str, Any]) -> MCPUtilityScore:
        """
        Calcula el score de utilidad MCP para una especificación.

        Args:
            spec: Diccionario con la especificación OpenAPI

        Returns:
            MCPUtilityScore con el análisis completo
        """
        result = MCPUtilityScore()

        if not spec or "paths" not in spec:
            result.recommendations.append("La especificación no tiene endpoints definidos")
            return result

        paths = spec.get("paths", {})

        # Recopilar datos de todos los endpoints
        endpoints_data = self._collect_endpoints_data(paths)
        result.total_endpoints = len(endpoints_data)

        if result.total_endpoints == 0:
            result.recommendations.append("No se encontraron endpoints para analizar")
            return result

        # Calcular scores por categoría
        result.categories["descriptions"] = self._score_descriptions(endpoints_data)
        result.categories["operation_ids"] = self._score_operation_ids(endpoints_data)
        result.categories["tags"] = self._score_tags(endpoints_data)
        result.categories["parameters"] = self._score_parameters(endpoints_data)
        result.categories["examples"] = self._score_examples(endpoints_data, spec)

        # Calcular score overall ponderado
        result.overall_score = self._calculate_weighted_score(result.categories)

        # Asignar grade
        result.grade = self._calculate_grade(result.overall_score)

        # Identificar endpoints incompletos
        result.incomplete_endpoints = self._identify_incomplete_endpoints(endpoints_data)
        result.endpoints_needing_attention = len(result.incomplete_endpoints)

        # Generar recomendaciones
        result.recommendations = self._generate_recommendations(result)

        return result

    def _collect_endpoints_data(self, paths: dict) -> list[dict]:
        """Recopila datos de todos los endpoints."""
        endpoints = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue

                endpoints.append({
                    "method": method,
                    "path": path,
                    "operation": operation,
                    "has_description": bool(operation.get("description")),
                    "has_summary": bool(operation.get("summary")),
                    "has_operation_id": bool(operation.get("operationId")),
                    "has_tags": bool(operation.get("tags")),
                    "tags": operation.get("tags", []),
                    "parameters": operation.get("parameters", []),
                    "request_body": operation.get("requestBody"),
                    "responses": operation.get("responses", {}),
                })

        return endpoints

    def _score_descriptions(self, endpoints: list[dict]) -> CategoryScore:
        """Evalúa la completitud de descripciones."""
        total = len(endpoints)
        complete = sum(1 for e in endpoints if e["has_description"] or e["has_summary"])

        score = int((complete / total) * 100) if total > 0 else 0

        return CategoryScore(
            name="Descripciones",
            score=score,
            total_items=total,
            complete_items=complete,
            weight=self.CATEGORY_WEIGHTS["descriptions"]
        )

    def _score_operation_ids(self, endpoints: list[dict]) -> CategoryScore:
        """Evalúa la presencia de operationIds."""
        total = len(endpoints)
        complete = sum(1 for e in endpoints if e["has_operation_id"])

        score = int((complete / total) * 100) if total > 0 else 0

        return CategoryScore(
            name="Operation IDs",
            score=score,
            total_items=total,
            complete_items=complete,
            weight=self.CATEGORY_WEIGHTS["operation_ids"]
        )

    def _score_tags(self, endpoints: list[dict]) -> CategoryScore:
        """Evalúa el uso de tags."""
        total = len(endpoints)
        complete = sum(1 for e in endpoints if e["has_tags"])

        score = int((complete / total) * 100) if total > 0 else 0

        return CategoryScore(
            name="Tags",
            score=score,
            total_items=total,
            complete_items=complete,
            weight=self.CATEGORY_WEIGHTS["tags"]
        )

    def _score_parameters(self, endpoints: list[dict]) -> CategoryScore:
        """Evalúa la documentación de parámetros."""
        total_params = 0
        documented_params = 0

        for endpoint in endpoints:
            for param in endpoint["parameters"]:
                if isinstance(param, dict):
                    total_params += 1
                    if param.get("description"):
                        documented_params += 1

            # Request body
            request_body = endpoint.get("request_body")
            if request_body and isinstance(request_body, dict):
                if request_body.get("description"):
                    documented_params += 1
                total_params += 1

        score = int((documented_params / total_params) * 100) if total_params > 0 else 100

        return CategoryScore(
            name="Parámetros",
            score=score,
            total_items=total_params,
            complete_items=documented_params,
            weight=self.CATEGORY_WEIGHTS["parameters"]
        )

    def _score_examples(self, endpoints: list[dict], spec: dict) -> CategoryScore:
        """Evalúa la presencia de ejemplos."""
        total = len(endpoints)
        with_examples = 0

        for endpoint in endpoints:
            has_example = False

            # Check request body examples
            request_body = endpoint.get("request_body")
            if request_body and isinstance(request_body, dict):
                content = request_body.get("content", {})
                for media_type in content.values():
                    if isinstance(media_type, dict):
                        if media_type.get("example") or media_type.get("examples"):
                            has_example = True
                            break

            # Check response examples
            for response in endpoint["responses"].values():
                if not isinstance(response, dict):
                    continue
                content = response.get("content", {})
                for media_type in content.values():
                    if isinstance(media_type, dict):
                        if media_type.get("example") or media_type.get("examples"):
                            has_example = True
                            break

            if has_example:
                with_examples += 1

        score = int((with_examples / total) * 100) if total > 0 else 0

        return CategoryScore(
            name="Ejemplos",
            score=score,
            total_items=total,
            complete_items=with_examples,
            weight=self.CATEGORY_WEIGHTS["examples"]
        )

    def _calculate_weighted_score(self, categories: dict[str, CategoryScore]) -> int:
        """Calcula el score ponderado total."""
        weighted_sum = sum(
            cat.score * cat.weight
            for cat in categories.values()
        )
        return int(weighted_sum)

    def _calculate_grade(self, score: int) -> str:
        """Determina el grade basado en el score."""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return "F"

    def _identify_incomplete_endpoints(self, endpoints: list[dict]) -> list[EndpointIssue]:
        """Identifica endpoints que necesitan atención."""
        incomplete = []

        for endpoint in endpoints:
            missing = []
            suggestions = {}

            # Check description/summary
            if not endpoint["has_description"] and not endpoint["has_summary"]:
                missing.append("description")
                suggestions["description"] = self._suggest_description(
                    endpoint["method"],
                    endpoint["path"]
                )

            # Check operationId
            if not endpoint["has_operation_id"]:
                missing.append("operationId")
                suggestions["operationId"] = self._suggest_operation_id(
                    endpoint["method"],
                    endpoint["path"]
                )

            # Check tags
            if not endpoint["has_tags"]:
                missing.append("tags")
                suggestions["tags"] = self._suggest_tags(endpoint["path"])

            # Check parameter descriptions
            undocumented_params = []
            for param in endpoint["parameters"]:
                if isinstance(param, dict) and not param.get("description"):
                    param_name = param.get("name", "unknown")
                    undocumented_params.append(param_name)

            if undocumented_params:
                missing.append("parameter_descriptions")
                suggestions["undocumented_parameters"] = undocumented_params

            if missing:
                # Determinar prioridad
                priority = IssuePriority.LOW
                if "description" in missing:
                    priority = IssuePriority.HIGH
                elif "operationId" in missing:
                    priority = IssuePriority.MEDIUM

                incomplete.append(EndpointIssue(
                    method=endpoint["method"],
                    path=endpoint["path"],
                    missing_fields=missing,
                    suggested_values=suggestions,
                    priority=priority
                ))

        # Ordenar por prioridad
        priority_order = {IssuePriority.HIGH: 0, IssuePriority.MEDIUM: 1, IssuePriority.LOW: 2}
        incomplete.sort(key=lambda x: priority_order[x.priority])

        return incomplete

    def _suggest_description(self, method: str, path: str) -> str:
        """Genera una sugerencia de descripción basada en el método y path."""
        # Extraer el recurso del path
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        resource = parts[-1] if parts else "resource"
        resource_singular = resource.rstrip("s") if resource.endswith("s") else resource

        method_actions = {
            "get": f"Retrieve {resource}",
            "post": f"Create a new {resource_singular}",
            "put": f"Update {resource_singular}",
            "patch": f"Partially update {resource_singular}",
            "delete": f"Delete {resource_singular}",
            "head": f"Check {resource} existence",
            "options": f"Get options for {resource}",
        }

        # Detectar si es un endpoint de detalle (con path param)
        if "{" in path:
            if method == "get":
                return f"Retrieve a specific {resource_singular} by ID"
            elif method == "put":
                return f"Update a specific {resource_singular}"
            elif method == "patch":
                return f"Partially update a specific {resource_singular}"
            elif method == "delete":
                return f"Delete a specific {resource_singular}"

        return method_actions.get(method, f"Perform {method.upper()} operation on {resource}")

    def _suggest_operation_id(self, method: str, path: str) -> str:
        """Genera un operationId sugerido."""
        # Limpiar el path
        parts = path.split("/")
        clean_parts = []

        for part in parts:
            if not part:
                continue
            if part.startswith("{") and part.endswith("}"):
                # Convertir {userId} -> ById
                param_name = part[1:-1]
                clean_parts.append(f"By{self._to_camel_case(param_name)}")
            else:
                clean_parts.append(self._to_camel_case(part))

        method_prefixes = {
            "get": "get",
            "post": "create",
            "put": "update",
            "patch": "patch",
            "delete": "delete",
            "head": "check",
            "options": "options",
        }

        prefix = method_prefixes.get(method, method)
        resource = "".join(clean_parts)

        return f"{prefix}{resource}"

    def _suggest_tags(self, path: str) -> list[str]:
        """Sugiere tags basados en el path."""
        parts = [p for p in path.split("/") if p and not p.startswith("{")]

        if not parts:
            return ["general"]

        # El primer segmento significativo suele ser el recurso principal
        main_resource = parts[0].lower()

        # Eliminar prefijos comunes de versión
        if main_resource in ["v1", "v2", "v3", "api"]:
            main_resource = parts[1].lower() if len(parts) > 1 else "general"

        return [main_resource]

    def _to_camel_case(self, text: str) -> str:
        """Convierte texto a CamelCase."""
        # Manejar snake_case y kebab-case
        words = re.split(r'[-_]', text)
        return "".join(word.capitalize() for word in words)

    def _generate_recommendations(self, score: MCPUtilityScore) -> list[str]:
        """Genera recomendaciones basadas en el análisis."""
        recommendations = []

        # Recomendaciones por categoría
        for name, category in score.categories.items():
            if category.score < 50:
                if name == "descriptions":
                    recommendations.append(
                        f"⚠️ Solo {category.complete_items}/{category.total_items} endpoints tienen descripción. "
                        "Las descripciones son críticas para que los LLMs entiendan cuándo usar cada tool."
                    )
                elif name == "operation_ids":
                    recommendations.append(
                        f"⚠️ Solo {category.complete_items}/{category.total_items} endpoints tienen operationId. "
                        "Sin operationId, los nombres de tools serán genéricos."
                    )
                elif name == "tags":
                    recommendations.append(
                        f"💡 Solo {category.complete_items}/{category.total_items} endpoints tienen tags. "
                        "Los tags ayudan a organizar y categorizar los tools."
                    )
                elif name == "parameters":
                    recommendations.append(
                        f"💡 Solo {category.complete_items}/{category.total_items} parámetros están documentados. "
                        "Documentar parámetros mejora la precisión de los LLMs."
                    )

        # Recomendación general basada en grade
        if score.grade in ["D", "F"]:
            recommendations.insert(0,
                "🔴 Esta especificación tiene baja utilidad para MCP. "
                "Se recomienda enriquecerla antes de generar el servidor."
            )
        elif score.grade == "C":
            recommendations.insert(0,
                "🟡 Esta especificación tiene utilidad moderada. "
                "Considera agregar información adicional para mejorar la experiencia."
            )
        elif score.grade in ["A", "B"]:
            recommendations.insert(0,
                "🟢 Esta especificación tiene buena utilidad para MCP."
            )

        return recommendations

    def apply_enrichment(self, spec: dict, enrichments: list[EnrichmentData]) -> dict:
        """
        Aplica datos de enriquecimiento a la especificación.

        Args:
            spec: Especificación OpenAPI original
            enrichments: Lista de datos de enriquecimiento por endpoint

        Returns:
            Nueva especificación con los datos aplicados
        """
        import copy
        enriched_spec = copy.deepcopy(spec)

        paths = enriched_spec.get("paths", {})

        for enrichment in enrichments:
            path = enrichment.path
            method = enrichment.method.lower()

            if path not in paths or method not in paths[path]:
                continue

            operation = paths[path][method]

            # Aplicar descripción
            if enrichment.description:
                operation["description"] = enrichment.description

            # Aplicar summary
            if enrichment.summary:
                operation["summary"] = enrichment.summary

            # Aplicar operationId
            if enrichment.operation_id:
                operation["operationId"] = enrichment.operation_id

            # Aplicar tags
            if enrichment.tags:
                operation["tags"] = enrichment.tags

            # Aplicar descripciones de parámetros
            if enrichment.parameter_descriptions:
                for param in operation.get("parameters", []):
                    if isinstance(param, dict):
                        param_name = param.get("name")
                        if param_name in enrichment.parameter_descriptions:
                            param["description"] = enrichment.parameter_descriptions[param_name]

        # Actualizar versión
        if "info" in enriched_spec:
            current_version = enriched_spec["info"].get("version", "1.0.0")
            enriched_spec["info"]["version"] = f"{current_version}-enriched"

        return enriched_spec

    def export_enriched_spec(self, spec: dict, format: str = "yaml") -> str:
        """
        Exporta la especificación enriquecida como string.

        Args:
            spec: Especificación enriquecida
            format: 'yaml' o 'json'

        Returns:
            String con la especificación formateada
        """
        import json
        import yaml

        if format.lower() == "json":
            return json.dumps(spec, indent=2, ensure_ascii=False)
        else:
            return yaml.dump(spec, allow_unicode=True, default_flow_style=False, sort_keys=False)
