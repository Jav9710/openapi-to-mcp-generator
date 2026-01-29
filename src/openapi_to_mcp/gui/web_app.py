"""
Aplicación web Flask para selección visual de endpoints.

Proporciona una interfaz gráfica para:
- Visualizar endpoints del OpenAPI
- Seleccionar endpoints con lista dual (source/target)
- Filtrar por tags y búsqueda
- Generar servidor MCP con la selección
"""

import json
import logging
import os
import threading
import webbrowser
from pathlib import Path
from typing import Any

from flask import Flask, render_template, jsonify, request, send_from_directory

logger = logging.getLogger(__name__)

# Variables globales para compartir datos entre requests
_current_spec = None
_current_spec_path = None
_output_dir = None


def create_app(spec, spec_path: str, output_dir: str) -> Flask:
    """
    Crea la aplicación Flask.

    Args:
        spec: Especificación OpenAPI parseada
        spec_path: Ruta al archivo spec
        output_dir: Directorio de salida

    Returns:
        Aplicación Flask configurada
    """
    global _current_spec, _current_spec_path, _output_dir
    _current_spec = spec
    _current_spec_path = spec_path
    _output_dir = output_dir

    # Configurar rutas de templates y static
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    app.config["SECRET_KEY"] = os.urandom(24)

    # Registrar rutas
    register_routes(app)

    return app


def register_routes(app: Flask):
    """Registra las rutas de la aplicación."""

    @app.route("/")
    def index():
        """Página principal con la interfaz de selección."""
        return render_template(
            "index.html",
            spec_title=_current_spec.title,
            spec_version=_current_spec.version,
            spec_description=_current_spec.description or "",
        )

    @app.route("/api/endpoints")
    def get_endpoints():
        """Retorna lista de endpoints en formato JSON."""
        from ..endpoint_selector import EndpointSelector

        selector = EndpointSelector(_current_spec, include_deprecated=True)
        endpoints = selector.get_all_endpoints()

        return jsonify({
            "endpoints": [ep.to_dict() for ep in endpoints],
            "stats": selector.get_stats(),
            "by_tags": {
                tag: [ep.to_dict() for ep in eps]
                for tag, eps in selector.get_endpoints_by_tags().items()
            },
        })

    @app.route("/api/spec-info")
    def get_spec_info():
        """Retorna información general del spec."""
        return jsonify({
            "title": _current_spec.title,
            "version": _current_spec.version,
            "description": _current_spec.description,
            "servers": [
                {"url": s.url, "description": s.description}
                for s in _current_spec.servers
            ],
            "tags": _current_spec.tags,
            "security_schemes": list(_current_spec.security_schemes.keys()),
        })

    @app.route("/api/filter", methods=["POST"])
    def filter_endpoints():
        """Filtra endpoints por patrones."""
        from ..endpoint_selector import EndpointSelector

        data = request.json
        include_patterns = data.get("include", [])
        exclude_patterns = data.get("exclude", [])

        selector = EndpointSelector(_current_spec, include_deprecated=True)
        filtered = selector.filter_by_patterns(include_patterns, exclude_patterns)

        return jsonify({
            "endpoints": [ep.to_dict() for ep in filtered],
            "total": len(filtered),
        })

    @app.route("/api/generate", methods=["POST"])
    def generate_server():
        """Genera el servidor MCP con los endpoints seleccionados."""
        from ..endpoint_selector import EndpointSelector
        from ..generators.server_generator import MCPServerGenerator
        from ..models import MCPServerConfig, MCPFramework, EndpointFilter
        from ..transformers.tool_transformer import ToolTransformer
        from ..transformers.resource_transformer import ResourceTransformer

        data = request.json
        selected_endpoints = data.get("selected", [])
        service_name = data.get("service_name", "api")
        service_prefix = data.get("service_prefix", service_name)
        base_url = data.get("base_url") or _current_spec.get_base_url()
        mcp_framework = data.get("mcp_framework", "fastmcp")
        environment = data.get("environment", "production")

        try:
            # Crear filtro
            endpoint_filter = EndpointFilter(selected_endpoints=selected_endpoints)

            # Configuración
            framework = MCPFramework.FASTMCP if mcp_framework == "fastmcp" else MCPFramework.MCP
            config = MCPServerConfig(
                service_name=service_name,
                service_prefix=service_prefix,
                base_url=base_url,
                mcp_framework=framework,
                environment=environment,
            )

            # Transformar
            tool_transformer = ToolTransformer(
                service_prefix=service_prefix,
                include_deprecated=True,
            )
            tools = tool_transformer.transform(_current_spec, endpoint_filter=endpoint_filter)

            resource_transformer = ResourceTransformer(service_prefix=service_prefix)
            resources = resource_transformer.transform(_current_spec, tools)

            # Generar
            generator = MCPServerGenerator(output_dir=_output_dir)
            result = generator.generate(
                spec=_current_spec,
                tools=tools,
                resources=resources,
                config=config,
            )

            return jsonify({
                "success": result.success,
                "output_path": result.output_path,
                "tools_count": len(result.tools_generated),
                "resources_count": len(result.resources_generated),
                "warnings": result.warnings,
                "errors": result.errors,
            })

        except Exception as e:
            logger.exception("Error generando servidor")
            return jsonify({
                "success": False,
                "error": str(e),
            }), 500

    @app.route("/api/shutdown", methods=["POST"])
    def shutdown():
        """Apaga el servidor Flask."""
        func = request.environ.get("werkzeug.server.shutdown")
        if func:
            func()
        return jsonify({"status": "shutting_down"})


def run_gui(
    spec,
    spec_path: str,
    output_dir: str,
    port: int = 5000,
    open_browser: bool = True,
):
    """
    Inicia la GUI web.

    Args:
        spec: Especificación OpenAPI parseada
        spec_path: Ruta al archivo spec
        output_dir: Directorio de salida
        port: Puerto del servidor
        open_browser: Si abrir el navegador automáticamente
    """
    app = create_app(spec, spec_path, output_dir)

    url = f"http://localhost:{port}"

    if open_browser:
        # Abrir navegador después de un breve delay
        def open_browser_delayed():
            import time
            time.sleep(1)
            webbrowser.open(url)

        thread = threading.Thread(target=open_browser_delayed)
        thread.daemon = True
        thread.start()

    print(f"\n  Servidor GUI corriendo en: {url}")
    print("  Presiona Ctrl+C para detener\n")

    # Ejecutar Flask
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )
