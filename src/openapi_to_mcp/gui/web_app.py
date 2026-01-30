"""
Aplicación web Flask para selección visual de endpoints.

Proporciona una interfaz gráfica para:
- Subir archivos OpenAPI (YAML/JSON)
- Visualizar endpoints del OpenAPI
- Seleccionar endpoints con lista dual (source/target)
- Filtrar por tags y búsqueda
- Generar servidor MCP con la selección
- Descargar el servidor generado como ZIP
"""

import io
import json
import logging
import os
import shutil
import tempfile
import threading
import uuid
import webbrowser
import zipfile
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    send_file,
    send_from_directory,
    session,
)

logger = logging.getLogger(__name__)

# Variables globales para compartir datos entre requests
_current_spec = None
_current_spec_path = None
_output_dir = None
_standalone_mode = False

# Almacenamiento de specs por sesión (para modo standalone)
_session_specs = {}


def create_app(
    spec=None,
    spec_path: str = None,
    output_dir: str = "./output",
    standalone: bool = False,
) -> Flask:
    """
    Crea la aplicación Flask.

    Args:
        spec: Especificación OpenAPI parseada (None para modo standalone)
        spec_path: Ruta al archivo spec
        output_dir: Directorio de salida
        standalone: Si True, permite subir archivos OpenAPI

    Returns:
        Aplicación Flask configurada
    """
    global _current_spec, _current_spec_path, _output_dir, _standalone_mode
    _current_spec = spec
    _current_spec_path = spec_path
    _output_dir = output_dir
    _standalone_mode = standalone or (spec is None)

    # Configurar rutas de templates y static
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )

    app.config["SECRET_KEY"] = os.urandom(24)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

    # Registrar rutas
    register_routes(app)

    return app


def register_routes(app: Flask):
    """Registra las rutas de la aplicación."""

    @app.route("/")
    def index():
        """Página principal."""
        if _standalone_mode and _current_spec is None:
            # Modo standalone sin spec cargado: mostrar página de upload
            return render_template("upload.html")
        else:
            # Modo con spec: mostrar selector de endpoints
            return render_template(
                "index.html",
                spec_title=_current_spec.title,
                spec_version=_current_spec.version,
                spec_description=_current_spec.description or "",
                standalone_mode=_standalone_mode,
            )

    @app.route("/selector")
    def selector():
        """Página de selección de endpoints (para uso después de upload)."""
        session_id = request.args.get("session")

        if session_id and session_id in _session_specs:
            spec_data = _session_specs[session_id]
            return render_template(
                "index.html",
                spec_title=spec_data["spec"].title,
                spec_version=spec_data["spec"].version,
                spec_description=spec_data["spec"].description or "",
                standalone_mode=True,
                session_id=session_id,
            )
        elif _current_spec:
            return render_template(
                "index.html",
                spec_title=_current_spec.title,
                spec_version=_current_spec.version,
                spec_description=_current_spec.description or "",
                standalone_mode=_standalone_mode,
            )
        else:
            return render_template("upload.html")

    @app.route("/api/upload", methods=["POST"])
    def upload_spec():
        """Sube y parsea un archivo OpenAPI."""
        from ..parsers.openapi_parser import OpenAPIParser, OpenAPIParserError

        if "file" not in request.files:
            return jsonify({"success": False, "error": "No se envió archivo"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"success": False, "error": "Nombre de archivo vacío"}), 400

        # Verificar extensión
        allowed_extensions = {".yaml", ".yml", ".json"}
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            return jsonify({
                "success": False,
                "error": f"Extensión no válida. Usa: {', '.join(allowed_extensions)}"
            }), 400

        try:
            # Guardar archivo temporalmente
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir) / file.filename
            file.save(str(temp_path))

            # Parsear
            parser = OpenAPIParser(strict_validation=False)
            spec = parser.parse(str(temp_path))

            # Generar session ID
            session_id = str(uuid.uuid4())[:8]

            # Guardar en memoria
            _session_specs[session_id] = {
                "spec": spec,
                "spec_path": str(temp_path),
                "temp_dir": temp_dir,
                "filename": file.filename,
            }

            # Obtener estadísticas
            from ..endpoint_selector import EndpointSelector
            selector = EndpointSelector(spec, include_deprecated=True)
            stats = selector.get_stats()

            # Validación rápida
            from ..validators import OpenAPIValidator
            validator = OpenAPIValidator(check_best_practices=True)
            validation = validator.validate_file(str(temp_path))

            return jsonify({
                "success": True,
                "session_id": session_id,
                "spec_info": {
                    "title": spec.title,
                    "version": spec.version,
                    "description": spec.description,
                    "endpoints_count": stats["total"],
                    "tags": list(stats["by_tag"].keys()),
                },
                "validation": {
                    "valid": validation.valid,
                    "error_count": validation.error_count,
                    "warning_count": validation.warning_count,
                    "suggestion_count": len(validation.suggestions),
                },
                "redirect_url": f"/selector?session={session_id}",
            })

        except OpenAPIParserError as e:
            return jsonify({
                "success": False,
                "error": f"Error parseando OpenAPI: {str(e)}"
            }), 400

        except Exception as e:
            logger.exception("Error en upload")
            return jsonify({
                "success": False,
                "error": f"Error procesando archivo: {str(e)}"
            }), 500

    @app.route("/api/load-url", methods=["POST"])
    def load_from_url():
        """Carga y parsea un OpenAPI desde una URL."""
        import requests
        from ..parsers.openapi_parser import OpenAPIParser, OpenAPIParserError

        data = request.json
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"success": False, "error": "URL no proporcionada"}), 400

        # Validar URL básica
        if not url.startswith(("http://", "https://")):
            return jsonify({
                "success": False,
                "error": "URL inválida. Debe comenzar con http:// o https://"
            }), 400

        try:
            # Descargar contenido
            headers = {
                "Accept": "application/json, application/yaml, application/x-yaml, text/yaml, text/plain",
                "User-Agent": "OpenAPI-to-MCP-Generator/1.0",
            }

            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()

            # Determinar tipo de contenido
            content_type = response.headers.get("Content-Type", "").lower()
            content = response.text

            # Determinar extensión basada en contenido o URL
            if "json" in content_type or url.endswith(".json"):
                ext = ".json"
            else:
                ext = ".yaml"

            # Extraer nombre del archivo de la URL
            url_path = url.split("?")[0]  # Remover query params
            filename = url_path.split("/")[-1] or "openapi"
            if not filename.endswith((".yaml", ".yml", ".json")):
                filename = f"{filename}{ext}"

            # Guardar temporalmente
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir) / filename

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Parsear
            parser = OpenAPIParser(strict_validation=False)
            spec = parser.parse(str(temp_path))

            # Generar session ID
            session_id = str(uuid.uuid4())[:8]

            # Guardar en memoria
            _session_specs[session_id] = {
                "spec": spec,
                "spec_path": str(temp_path),
                "temp_dir": temp_dir,
                "filename": filename,
                "source_url": url,
            }

            # Obtener estadísticas
            from ..endpoint_selector import EndpointSelector
            selector = EndpointSelector(spec, include_deprecated=True)
            stats = selector.get_stats()

            # Validación rápida
            from ..validators import OpenAPIValidator
            validator = OpenAPIValidator(check_best_practices=True)
            validation = validator.validate_file(str(temp_path))

            return jsonify({
                "success": True,
                "session_id": session_id,
                "spec_info": {
                    "title": spec.title,
                    "version": spec.version,
                    "description": spec.description,
                    "endpoints_count": stats["total"],
                    "tags": list(stats["by_tag"].keys()),
                },
                "validation": {
                    "valid": validation.valid,
                    "error_count": validation.error_count,
                    "warning_count": validation.warning_count,
                    "suggestion_count": len(validation.suggestions),
                },
                "redirect_url": f"/selector?session={session_id}",
            })

        except requests.exceptions.Timeout:
            return jsonify({
                "success": False,
                "error": "Timeout: La URL tardó demasiado en responder"
            }), 400

        except requests.exceptions.ConnectionError:
            return jsonify({
                "success": False,
                "error": "Error de conexión: No se pudo conectar a la URL"
            }), 400

        except requests.exceptions.HTTPError as e:
            return jsonify({
                "success": False,
                "error": f"Error HTTP: {e.response.status_code} - {e.response.reason}"
            }), 400

        except OpenAPIParserError as e:
            return jsonify({
                "success": False,
                "error": f"Error parseando OpenAPI: {str(e)}"
            }), 400

        except Exception as e:
            logger.exception("Error cargando desde URL")
            return jsonify({
                "success": False,
                "error": f"Error procesando URL: {str(e)}"
            }), 500

    @app.route("/api/endpoints")
    def get_endpoints():
        """Retorna lista de endpoints en formato JSON."""
        from ..endpoint_selector import EndpointSelector

        spec = _get_current_spec(request)
        if not spec:
            return jsonify({"error": "No hay spec cargado"}), 400

        selector = EndpointSelector(spec, include_deprecated=True)
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
        spec = _get_current_spec(request)
        if not spec:
            return jsonify({"error": "No hay spec cargado"}), 400

        return jsonify({
            "title": spec.title,
            "version": spec.version,
            "description": spec.description,
            "servers": [
                {"url": s.url, "description": s.description}
                for s in spec.servers
            ],
            "tags": spec.tags,
            "security_schemes": list(spec.security_schemes.keys()),
        })

    @app.route("/api/validate")
    def validate_spec():
        """Valida la especificación OpenAPI cargada y retorna diagnósticos."""
        from ..validators import OpenAPIValidator

        session_id = request.args.get("session")
        spec_path = None

        if session_id and session_id in _session_specs:
            spec_path = _session_specs[session_id].get("spec_path")
        elif _global_spec_path:
            spec_path = _global_spec_path

        if not spec_path:
            return jsonify({"error": "No hay spec cargado"}), 400

        validator = OpenAPIValidator(check_best_practices=True)
        result = validator.validate_file(spec_path)

        return jsonify(result.to_dict())

    @app.route("/api/validate-content", methods=["POST"])
    def validate_content():
        """Valida contenido de especificación sin cargarlo."""
        from ..validators import OpenAPIValidator

        data = request.json
        content = data.get("content", "")
        format_type = data.get("format", "yaml")

        if not content:
            return jsonify({"error": "No se proporcionó contenido"}), 400

        validator = OpenAPIValidator(check_best_practices=True)
        result = validator.validate_content(content, format_type)

        return jsonify(result.to_dict())

    @app.route("/api/stats")
    def get_stats():
        """Retorna estadísticas detalladas de la especificación."""
        from ..endpoint_selector import EndpointSelector

        spec = _get_current_spec(request)
        if not spec:
            return jsonify({"error": "No hay spec cargado"}), 400

        selector = EndpointSelector(spec, include_deprecated=True)
        endpoints = selector.get_all_endpoints()
        stats = selector.get_stats()

        # Estadísticas por método HTTP
        methods_count = {"GET": 0, "POST": 0, "PUT": 0, "PATCH": 0, "DELETE": 0, "HEAD": 0, "OPTIONS": 0}
        for ep in endpoints:
            method = ep.method.upper()
            if method in methods_count:
                methods_count[method] += 1

        # Estadísticas por tag
        tags_count = {}
        for ep in endpoints:
            for tag in ep.tags:
                tags_count[tag] = tags_count.get(tag, 0) + 1

        # Endpoints deprecated
        deprecated_count = sum(1 for ep in endpoints if ep.deprecated)

        # Parámetros más comunes
        param_types = {"path": 0, "query": 0, "header": 0, "body": 0}
        for ep in endpoints:
            for param in ep.parameters:
                param_in = param.get("in", "").lower()
                if param_in in param_types:
                    param_types[param_in] += 1
            if ep.request_body:
                param_types["body"] += 1

        # Security schemes
        security_schemes = list(spec.security_schemes.keys()) if spec.security_schemes else []

        return jsonify({
            "total_endpoints": len(endpoints),
            "total_paths": stats.get("total_paths", len(set(ep.path for ep in endpoints))),
            "methods": methods_count,
            "methods_chart": [
                {"method": k, "count": v, "color": _get_method_color(k)}
                for k, v in methods_count.items() if v > 0
            ],
            "tags": tags_count,
            "tags_chart": [
                {"tag": k, "count": v}
                for k, v in sorted(tags_count.items(), key=lambda x: -x[1])[:10]
            ],
            "deprecated_count": deprecated_count,
            "param_types": param_types,
            "security_schemes": security_schemes,
            "api_info": {
                "title": spec.title,
                "version": spec.version,
                "description": spec.description,
                "servers": [s.url for s in spec.servers] if spec.servers else [],
            }
        })

    def _get_method_color(method):
        """Retorna color para método HTTP."""
        colors = {
            "GET": "#22c55e",
            "POST": "#3b82f6",
            "PUT": "#f59e0b",
            "PATCH": "#8b5cf6",
            "DELETE": "#ef4444",
            "HEAD": "#6b7280",
            "OPTIONS": "#6b7280",
        }
        return colors.get(method.upper(), "#6b7280")

    @app.route("/api/filter", methods=["POST"])
    def filter_endpoints():
        """Filtra endpoints por patrones."""
        from ..endpoint_selector import EndpointSelector

        spec = _get_current_spec(request)
        if not spec:
            return jsonify({"error": "No hay spec cargado"}), 400

        data = request.json
        include_patterns = data.get("include", [])
        exclude_patterns = data.get("exclude", [])

        selector = EndpointSelector(spec, include_deprecated=True)
        filtered = selector.filter_by_patterns(include_patterns, exclude_patterns)

        return jsonify({
            "endpoints": [ep.to_dict() for ep in filtered],
            "total": len(filtered),
        })

    @app.route("/api/preview", methods=["POST"])
    def preview_code():
        """Genera preview del código MCP sin guardarlo."""
        from ..endpoint_selector import EndpointSelector
        from ..generators.server_generator import MCPServerGenerator
        from ..models import MCPServerConfig, MCPFramework, EndpointFilter
        from ..transformers.tool_transformer import ToolTransformer
        from ..transformers.resource_transformer import ResourceTransformer
        import io

        spec = _get_current_spec(request)
        if not spec:
            return jsonify({"success": False, "error": "No hay spec cargado"}), 400

        data = request.json
        selected_endpoints = data.get("selected", [])
        service_name = data.get("service_name", "api")
        service_prefix = data.get("service_prefix", service_name)
        base_url = data.get("base_url") or spec.get_base_url()
        mcp_framework = data.get("mcp_framework", "fastmcp")

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
            )

            # Transformar
            tool_transformer = ToolTransformer(
                service_prefix=service_prefix,
                base_url=base_url,
            )
            tools = tool_transformer.transform(spec, endpoint_filter=endpoint_filter)

            resource_transformer = ResourceTransformer(service_prefix=service_prefix)
            resources = resource_transformer.transform(spec)

            # Generar código en memoria
            generator = MCPServerGenerator(output_dir=None)
            code_preview = generator.generate_preview(spec, tools, resources, config)

            return jsonify({
                "success": True,
                "files": code_preview,
                "stats": {
                    "tools_count": len(tools),
                    "resources_count": len(resources),
                    "files_count": len(code_preview),
                }
            })

        except Exception as e:
            logger.exception("Error en preview")
            return jsonify({
                "success": False,
                "error": f"Error generando preview: {str(e)}"
            }), 500

    @app.route("/api/generate", methods=["POST"])
    def generate_server():
        """Genera el servidor MCP con los endpoints seleccionados."""
        from ..endpoint_selector import EndpointSelector
        from ..generators.server_generator import MCPServerGenerator
        from ..models import MCPServerConfig, MCPFramework, EndpointFilter
        from ..transformers.tool_transformer import ToolTransformer
        from ..transformers.resource_transformer import ResourceTransformer

        spec = _get_current_spec(request)
        if not spec:
            return jsonify({"success": False, "error": "No hay spec cargado"}), 400

        data = request.json
        selected_endpoints = data.get("selected", [])
        service_name = data.get("service_name", "api")
        service_prefix = data.get("service_prefix", service_name)
        base_url = data.get("base_url") or spec.get_base_url()
        mcp_framework = data.get("mcp_framework", "fastmcp")
        environment = data.get("environment", "production")
        download_zip = data.get("download_zip", False)

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

            # Crear directorio temporal para generación
            if download_zip:
                temp_output = tempfile.mkdtemp()
                output_dir = temp_output
            else:
                output_dir = _output_dir

            # Transformar
            tool_transformer = ToolTransformer(
                service_prefix=service_prefix,
                include_deprecated=True,
            )
            tools = tool_transformer.transform(spec, endpoint_filter=endpoint_filter)

            resource_transformer = ResourceTransformer(service_prefix=service_prefix)
            resources = resource_transformer.transform(spec, tools)

            # Generar
            generator = MCPServerGenerator(output_dir=output_dir)
            result = generator.generate(
                spec=spec,
                tools=tools,
                resources=resources,
                config=config,
            )

            if download_zip and result.success:
                # Crear ZIP
                zip_filename = f"mcp_server_{service_name}.zip"
                zip_id = str(uuid.uuid4())[:8]

                # Guardar referencia para descarga
                _session_specs[f"zip_{zip_id}"] = {
                    "output_path": result.output_path,
                    "temp_dir": temp_output,
                    "zip_filename": zip_filename,
                }

                return jsonify({
                    "success": result.success,
                    "output_path": result.output_path,
                    "tools_count": len(result.tools_generated),
                    "resources_count": len(result.resources_generated),
                    "warnings": result.warnings,
                    "errors": result.errors,
                    "download_url": f"/api/download/{zip_id}",
                    "zip_filename": zip_filename,
                })
            else:
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

    @app.route("/api/download/<zip_id>")
    def download_zip(zip_id: str):
        """Descarga el servidor generado como ZIP."""
        key = f"zip_{zip_id}"

        if key not in _session_specs:
            return jsonify({"error": "Descarga no encontrada o expirada"}), 404

        zip_data = _session_specs[key]
        output_path = zip_data["output_path"]
        zip_filename = zip_data["zip_filename"]

        try:
            # Crear ZIP en memoria
            memory_file = io.BytesIO()

            with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
                base_path = Path(output_path)

                for file_path in base_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(base_path.parent)
                        zf.write(file_path, arcname)

            memory_file.seek(0)

            # Limpiar temp dir después de enviar
            def cleanup():
                import time
                time.sleep(5)
                if key in _session_specs:
                    temp_dir = _session_specs[key].get("temp_dir")
                    if temp_dir and Path(temp_dir).exists():
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    del _session_specs[key]

            thread = threading.Thread(target=cleanup)
            thread.daemon = True
            thread.start()

            return send_file(
                memory_file,
                mimetype="application/zip",
                as_attachment=True,
                download_name=zip_filename,
            )

        except Exception as e:
            logger.exception("Error creando ZIP")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/shutdown", methods=["POST"])
    def shutdown():
        """Apaga el servidor Flask."""
        func = request.environ.get("werkzeug.server.shutdown")
        if func:
            func()
        return jsonify({"status": "shutting_down"})


def _get_current_spec(req):
    """Obtiene el spec actual basado en la sesión o el global."""
    session_id = req.args.get("session") or (req.json or {}).get("session_id")

    if session_id and session_id in _session_specs:
        return _session_specs[session_id]["spec"]

    return _current_spec


def run_gui(
    spec=None,
    spec_path: str = None,
    output_dir: str = "./output",
    port: int = 5000,
    open_browser: bool = True,
    standalone: bool = False,
):
    """
    Inicia la GUI web.

    Args:
        spec: Especificación OpenAPI parseada (None para modo standalone)
        spec_path: Ruta al archivo spec
        output_dir: Directorio de salida
        port: Puerto del servidor
        open_browser: Si abrir el navegador automáticamente
        standalone: Si True, permite subir archivos
    """
    app = create_app(
        spec=spec,
        spec_path=spec_path,
        output_dir=output_dir,
        standalone=standalone,
    )

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


def run_standalone(port: int = 5000, output_dir: str = "./output"):
    """
    Inicia la GUI en modo standalone (sin spec precargado).

    Args:
        port: Puerto del servidor
        output_dir: Directorio de salida por defecto
    """
    run_gui(
        spec=None,
        spec_path=None,
        output_dir=output_dir,
        port=port,
        open_browser=True,
        standalone=True,
    )
