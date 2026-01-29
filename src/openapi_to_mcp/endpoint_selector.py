"""
Selector de endpoints para el generador OpenAPI-to-MCP.

Proporciona funcionalidades para:
- Extraer y mostrar endpoints de una especificación OpenAPI
- Selección interactiva en CLI con questionary
- Filtrado por patrones glob
- Agrupación por tags
"""

import fnmatch
import logging
from dataclasses import dataclass
from typing import Any

from .models import EndpointFilter, HttpMethod, OpenAPISpec

logger = logging.getLogger(__name__)


@dataclass
class EndpointInfo:
    """Información de un endpoint para mostrar en la selección."""
    method: str
    path: str
    operation_id: str | None
    summary: str
    description: str
    tags: list[str]
    deprecated: bool

    @property
    def key(self) -> str:
        """Clave única del endpoint: 'METHOD /path'."""
        return f"{self.method.upper()} {self.path}"

    @property
    def display_name(self) -> str:
        """Nombre para mostrar: '[METHOD] /path - Summary'."""
        summary = self.summary[:50] + "..." if len(self.summary) > 50 else self.summary
        deprecated_mark = " [DEPRECATED]" if self.deprecated else ""
        return f"[{self.method.upper()}] {self.path} - {summary}{deprecated_mark}"

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            "method": self.method.upper(),
            "path": self.path,
            "key": self.key,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "description": self.description,
            "tags": self.tags,
            "deprecated": self.deprecated,
            "display_name": self.display_name,
        }


class EndpointSelector:
    """
    Selector de endpoints con soporte para CLI interactivo y GUI.

    Example:
        selector = EndpointSelector(spec)

        # Obtener todos los endpoints
        endpoints = selector.get_all_endpoints()

        # Filtrar por patrón
        filtered = selector.filter_by_patterns(["/users*"], ["/internal/*"])

        # Selección interactiva en terminal
        selected = selector.interactive_select()
    """

    def __init__(self, spec: OpenAPISpec, include_deprecated: bool = False):
        """
        Inicializa el selector.

        Args:
            spec: Especificación OpenAPI parseada
            include_deprecated: Si incluir endpoints marcados como deprecated
        """
        self.spec = spec
        self.include_deprecated = include_deprecated
        self._endpoints: list[EndpointInfo] | None = None

    def get_all_endpoints(self) -> list[EndpointInfo]:
        """
        Extrae todos los endpoints de la especificación.

        Returns:
            Lista de EndpointInfo con información de cada endpoint
        """
        if self._endpoints is not None:
            return self._endpoints

        endpoints = []

        for path, path_item in self.spec.paths.items():
            for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]

                # Filtrar deprecated si corresponde
                if operation.get("deprecated", False) and not self.include_deprecated:
                    continue

                endpoint = EndpointInfo(
                    method=method,
                    path=path,
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary", "Sin descripción"),
                    description=operation.get("description", ""),
                    tags=operation.get("tags", []),
                    deprecated=operation.get("deprecated", False),
                )
                endpoints.append(endpoint)

        # Ordenar por path y luego por método
        method_order = {"get": 0, "post": 1, "put": 2, "patch": 3, "delete": 4, "head": 5, "options": 6}
        endpoints.sort(key=lambda e: (e.path, method_order.get(e.method.lower(), 99)))

        self._endpoints = endpoints
        return endpoints

    def get_endpoints_by_tags(self) -> dict[str, list[EndpointInfo]]:
        """
        Agrupa endpoints por tags.

        Returns:
            Diccionario {tag: [endpoints]}
        """
        endpoints = self.get_all_endpoints()
        by_tags: dict[str, list[EndpointInfo]] = {}

        for endpoint in endpoints:
            if endpoint.tags:
                for tag in endpoint.tags:
                    if tag not in by_tags:
                        by_tags[tag] = []
                    by_tags[tag].append(endpoint)
            else:
                # Sin tag
                if "Sin categoría" not in by_tags:
                    by_tags["Sin categoría"] = []
                by_tags["Sin categoría"].append(endpoint)

        return dict(sorted(by_tags.items()))

    def filter_by_patterns(
        self,
        include_patterns: list[str],
        exclude_patterns: list[str]
    ) -> list[EndpointInfo]:
        """
        Filtra endpoints por patrones glob.

        Args:
            include_patterns: Patrones para incluir (si vacío, incluye todos)
            exclude_patterns: Patrones para excluir

        Returns:
            Lista de endpoints que coinciden con los patrones
        """
        endpoints = self.get_all_endpoints()
        result = []

        for endpoint in endpoints:
            # Verificar exclusiones
            excluded = any(
                fnmatch.fnmatch(endpoint.path, pattern)
                for pattern in exclude_patterns
            )
            if excluded:
                continue

            # Verificar inclusiones
            if include_patterns:
                included = any(
                    fnmatch.fnmatch(endpoint.path, pattern)
                    for pattern in include_patterns
                )
                if not included:
                    continue

            result.append(endpoint)

        return result

    def create_filter_from_selection(self, selected_keys: list[str]) -> EndpointFilter:
        """
        Crea un EndpointFilter desde una lista de claves seleccionadas.

        Args:
            selected_keys: Lista de claves ["GET /users", "POST /orders"]

        Returns:
            EndpointFilter con los endpoints seleccionados
        """
        return EndpointFilter(selected_endpoints=selected_keys)

    def create_filter_from_patterns(
        self,
        include_patterns: list[str],
        exclude_patterns: list[str]
    ) -> EndpointFilter:
        """
        Crea un EndpointFilter desde patrones.

        Args:
            include_patterns: Patrones de inclusión
            exclude_patterns: Patrones de exclusión

        Returns:
            EndpointFilter configurado
        """
        return EndpointFilter(
            include_patterns=list(include_patterns),
            exclude_patterns=list(exclude_patterns)
        )

    def interactive_select(self) -> EndpointFilter:
        """
        Permite selección interactiva de endpoints en la terminal.

        Requiere que questionary esté instalado.

        Returns:
            EndpointFilter con los endpoints seleccionados
        """
        try:
            import questionary
            from questionary import Style
        except ImportError:
            logger.error("questionary no está instalado. Instálalo con: pip install questionary")
            raise ImportError(
                "Para usar el modo interactivo, instala questionary: pip install questionary"
            )

        endpoints = self.get_all_endpoints()

        if not endpoints:
            logger.warning("No se encontraron endpoints en la especificación")
            return EndpointFilter()

        # Estilo personalizado
        custom_style = Style([
            ("qmark", "fg:cyan bold"),
            ("question", "fg:white bold"),
            ("answer", "fg:green"),
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan"),
            ("selected", "fg:green"),
        ])

        # Preguntar el modo de selección
        mode = questionary.select(
            "¿Cómo deseas seleccionar los endpoints?",
            choices=[
                {"name": "Selección manual (checkboxes)", "value": "manual"},
                {"name": "Por patrones (glob)", "value": "patterns"},
                {"name": "Por tags (grupos)", "value": "tags"},
                {"name": "Todos los endpoints", "value": "all"},
            ],
            style=custom_style,
        ).ask()

        if mode is None:
            # Usuario canceló
            return EndpointFilter()

        if mode == "all":
            return EndpointFilter()  # Sin filtro = todos

        if mode == "patterns":
            return self._interactive_patterns(custom_style)

        if mode == "tags":
            return self._interactive_by_tags(custom_style)

        # Modo manual (checkboxes)
        return self._interactive_manual(custom_style)

    def _interactive_manual(self, style) -> EndpointFilter:
        """Selección manual con checkboxes."""
        import questionary

        endpoints = self.get_all_endpoints()

        choices = [
            {
                "name": endpoint.display_name,
                "value": endpoint.key,
                "checked": True,  # Todos seleccionados por defecto
            }
            for endpoint in endpoints
        ]

        selected = questionary.checkbox(
            f"Selecciona los endpoints a incluir ({len(endpoints)} disponibles):",
            choices=choices,
            style=style,
        ).ask()

        if selected is None:
            return EndpointFilter()

        return EndpointFilter(selected_endpoints=selected)

    def _interactive_by_tags(self, style) -> EndpointFilter:
        """Selección por tags."""
        import questionary

        by_tags = self.get_endpoints_by_tags()

        # Primero seleccionar tags
        tag_choices = [
            {
                "name": f"{tag} ({len(endpoints)} endpoints)",
                "value": tag,
                "checked": True,
            }
            for tag, endpoints in by_tags.items()
        ]

        selected_tags = questionary.checkbox(
            "Selecciona los tags a incluir:",
            choices=tag_choices,
            style=style,
        ).ask()

        if not selected_tags:
            return EndpointFilter()

        # Recopilar endpoints de los tags seleccionados
        selected_keys = []
        for tag in selected_tags:
            for endpoint in by_tags.get(tag, []):
                if endpoint.key not in selected_keys:
                    selected_keys.append(endpoint.key)

        # Permitir ajuste fino
        if questionary.confirm(
            f"Se seleccionaron {len(selected_keys)} endpoints. ¿Deseas ajustar la selección?",
            default=False,
            style=style,
        ).ask():
            choices = [
                {
                    "name": endpoint.display_name,
                    "value": endpoint.key,
                    "checked": endpoint.key in selected_keys,
                }
                for endpoint in self.get_all_endpoints()
            ]

            selected_keys = questionary.checkbox(
                "Ajusta la selección:",
                choices=choices,
                style=style,
            ).ask() or []

        return EndpointFilter(selected_endpoints=selected_keys)

    def _interactive_patterns(self, style) -> EndpointFilter:
        """Selección por patrones glob."""
        import questionary

        include_patterns = []
        exclude_patterns = []

        # Patrones de inclusión
        while True:
            pattern = questionary.text(
                "Patrón de inclusión (vacío para terminar):",
                style=style,
            ).ask()

            if not pattern:
                break

            include_patterns.append(pattern)

            # Mostrar preview
            filtered = self.filter_by_patterns(include_patterns, exclude_patterns)
            print(f"  → Coinciden {len(filtered)} endpoints")

        # Patrones de exclusión
        if questionary.confirm(
            "¿Deseas agregar patrones de exclusión?",
            default=False,
            style=style,
        ).ask():
            while True:
                pattern = questionary.text(
                    "Patrón de exclusión (vacío para terminar):",
                    style=style,
                ).ask()

                if not pattern:
                    break

                exclude_patterns.append(pattern)

                # Mostrar preview
                filtered = self.filter_by_patterns(include_patterns, exclude_patterns)
                print(f"  → Quedan {len(filtered)} endpoints")

        # Mostrar resultado final
        filtered = self.filter_by_patterns(include_patterns, exclude_patterns)
        print(f"\nEndpoints seleccionados ({len(filtered)}):")
        for ep in filtered[:10]:
            print(f"  • {ep.display_name}")
        if len(filtered) > 10:
            print(f"  ... y {len(filtered) - 10} más")

        if not questionary.confirm(
            "¿Confirmar selección?",
            default=True,
            style=style,
        ).ask():
            return EndpointFilter()

        return EndpointFilter(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Obtiene estadísticas de los endpoints.

        Returns:
            Diccionario con estadísticas
        """
        endpoints = self.get_all_endpoints()
        by_tags = self.get_endpoints_by_tags()

        methods_count = {}
        for ep in endpoints:
            method = ep.method.upper()
            methods_count[method] = methods_count.get(method, 0) + 1

        return {
            "total": len(endpoints),
            "by_method": methods_count,
            "by_tag": {tag: len(eps) for tag, eps in by_tags.items()},
            "deprecated": sum(1 for ep in endpoints if ep.deprecated),
        }
