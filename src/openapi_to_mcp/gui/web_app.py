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
from datetime import datetime, timedelta
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

# Configuración de cleanup
SESSION_TIMEOUT_HOURS = 2  # Limpiar sesiones después de 2 horas
CLEANUP_INTERVAL_MINUTES = 15  # Ejecutar cleanup cada 15 minutos


def create_standalone_app():
    """
    Crea la aplicación Flask para modo standalone (Docker/Gunicorn).

    Lee la configuración de variables de entorno:
    - OUTPUT_DIR: Directorio de salida (default: /app/output)
    - PORT: Puerto del servidor (solo informativo, gunicorn lo maneja)

    Returns:
        Aplicación Flask configurada para modo standalone
    """
    output_dir = os.environ.get("OUTPUT_DIR", "/app/output")

    logger.info(f"Creating standalone app with output_dir={output_dir}")

    return create_app(
        spec=None,
        spec_path=None,
        output_dir=output_dir,
        standalone=True,
    )


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

    # Configurar base de datos
    db_path = Path(output_dir) / "openapi_mcp.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicializar DB y Auth
    from .database import init_db
    from .auth import init_auth, create_default_admin
    init_db(app)
    init_auth(app)
    create_default_admin(app)

    # Registrar rutas
    register_routes(app)

    # Iniciar cleanup automático de sesiones en modo standalone
    if standalone or (spec is None):
        start_background_cleanup()

    return app


def cleanup_old_sessions():
    """
    Limpia sesiones y archivos temporales viejos.
    Ejecuta en background cada CLEANUP_INTERVAL_MINUTES.
    """
    import time

    while True:
        try:
            time.sleep(CLEANUP_INTERVAL_MINUTES * 60)

            now = datetime.now()
            timeout = timedelta(hours=SESSION_TIMEOUT_HOURS)
            sessions_to_delete = []

            for session_id, session_data in _session_specs.items():
                created_at = session_data.get("created_at")
                if created_at and (now - created_at) > timeout:
                    sessions_to_delete.append(session_id)

            # Limpiar sesiones viejas
            for session_id in sessions_to_delete:
                session_data = _session_specs.get(session_id)
                if session_data:
                    # Limpiar directorio temporal si existe
                    temp_dir = session_data.get("temp_dir")
                    if temp_dir and Path(temp_dir).exists():
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        logger.info(f"Cleaned up session {session_id} temp dir: {temp_dir}")

                    # Eliminar de memoria
                    del _session_specs[session_id]
                    logger.info(f"Removed expired session: {session_id}")

        except Exception as e:
            logger.exception(f"Error in session cleanup: {e}")


def start_background_cleanup():
    """Inicia el thread de cleanup en background."""
    cleanup_thread = threading.Thread(target=cleanup_old_sessions, daemon=True)
    cleanup_thread.start()
    logger.info(f"Started background session cleanup (interval: {CLEANUP_INTERVAL_MINUTES}min, timeout: {SESSION_TIMEOUT_HOURS}h)")


def register_routes(app: Flask):
    """Registra las rutas de la aplicación."""

    # ========== Auth Routes ==========

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Pagina de login."""
        from flask_login import login_user, current_user
        from .auth import authenticate_user

        if current_user.is_authenticated:
            return redirect("/")

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = authenticate_user(username, password)
            if user:
                login_user(user)
                next_page = request.args.get("next", "/")
                return redirect(next_page)
            else:
                return render_template("login.html", error="Usuario o contrasena incorrectos")

        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """Pagina de registro."""
        from flask_login import login_user
        from .auth import register_user

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            password_confirm = request.form.get("password_confirm", "")

            if not username or not email or not password:
                return render_template("register.html", error="Todos los campos son obligatorios")

            if len(password) < 6:
                return render_template("register.html", error="La contrasena debe tener al menos 6 caracteres")

            if password != password_confirm:
                return render_template("register.html", error="Las contrasenas no coinciden")

            try:
                user = register_user(username, email, password)
                login_user(user)
                return redirect("/")
            except ValueError as e:
                return render_template("register.html", error=str(e))

        return render_template("register.html")

    @app.route("/logout")
    def logout():
        """Cerrar sesion."""
        from flask_login import logout_user
        logout_user()
        return redirect("/login")

    # ========== App Routes ==========

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
                "created_at": datetime.now(),
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
                "created_at": datetime.now(),
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
        elif _current_spec_path:
            spec_path = _current_spec_path

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

    @app.route("/api/mcp-score")
    def get_mcp_score():
        """Calcula el MCP Utility Score para la especificación cargada."""
        from ..validators import MCPUtilityScorer
        import yaml

        session_id = request.args.get("session")
        spec_path = None
        raw_spec = None

        if session_id and session_id in _session_specs:
            spec_path = _session_specs[session_id].get("spec_path")
        elif _current_spec_path:
            spec_path = _current_spec_path

        if not spec_path:
            return jsonify({"error": "No hay spec cargado"}), 400

        # Cargar spec como dict para el scorer
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()
                if spec_path.endswith(".json"):
                    raw_spec = json.loads(content)
                else:
                    raw_spec = yaml.safe_load(content)
        except Exception as e:
            return jsonify({"error": f"Error cargando spec: {str(e)}"}), 500

        scorer = MCPUtilityScorer()
        score = scorer.calculate_score(raw_spec)

        return jsonify(score.to_dict())

    @app.route("/api/enrichment/suggestions")
    def get_enrichment_suggestions():
        """Obtiene sugerencias de enriquecimiento para endpoints incompletos."""
        from ..validators import MCPUtilityScorer
        import yaml

        session_id = request.args.get("session")
        spec_path = None

        if session_id and session_id in _session_specs:
            spec_path = _session_specs[session_id].get("spec_path")
        elif _current_spec_path:
            spec_path = _current_spec_path

        if not spec_path:
            return jsonify({"error": "No hay spec cargado"}), 400

        # Cargar spec
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()
                if spec_path.endswith(".json"):
                    raw_spec = json.loads(content)
                else:
                    raw_spec = yaml.safe_load(content)
        except Exception as e:
            return jsonify({"error": f"Error cargando spec: {str(e)}"}), 500

        scorer = MCPUtilityScorer()
        score = scorer.calculate_score(raw_spec)

        # Retornar solo los endpoints incompletos con sugerencias
        return jsonify({
            "endpoints": [e.to_dict() for e in score.incomplete_endpoints],
            "total_incomplete": len(score.incomplete_endpoints),
            "overall_score": score.overall_score,
            "grade": score.grade,
        })

    @app.route("/api/enrichment/apply", methods=["POST"])
    def apply_enrichment():
        """Aplica datos de enriquecimiento a la especificación."""
        from ..validators import MCPUtilityScorer, EnrichmentData
        import yaml

        session_id = request.args.get("session") or (request.json or {}).get("session_id")
        spec_path = None

        if session_id and session_id in _session_specs:
            spec_path = _session_specs[session_id].get("spec_path")
        elif _current_spec_path:
            spec_path = _current_spec_path

        if not spec_path:
            return jsonify({"error": "No hay spec cargado"}), 400

        data = request.json
        enrichments_data = data.get("enrichments", [])

        if not enrichments_data:
            return jsonify({"error": "No se proporcionaron datos de enriquecimiento"}), 400

        # Cargar spec original
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()
                if spec_path.endswith(".json"):
                    raw_spec = json.loads(content)
                else:
                    raw_spec = yaml.safe_load(content)
        except Exception as e:
            return jsonify({"error": f"Error cargando spec: {str(e)}"}), 500

        # Convertir enrichments
        enrichments = []
        for e in enrichments_data:
            enrichments.append(EnrichmentData(
                method=e.get("method", ""),
                path=e.get("path", ""),
                description=e.get("description"),
                summary=e.get("summary"),
                operation_id=e.get("operation_id"),
                tags=e.get("tags", []),
                parameter_descriptions=e.get("parameter_descriptions", {}),
            ))

        # Aplicar enriquecimiento
        scorer = MCPUtilityScorer()
        enriched_spec = scorer.apply_enrichment(raw_spec, enrichments)

        # Calcular nuevo score
        new_score = scorer.calculate_score(enriched_spec)

        # Guardar spec enriquecido temporalmente
        enriched_session_id = str(uuid.uuid4())[:8]
        temp_dir = tempfile.mkdtemp()

        # Determinar formato
        is_json = spec_path.endswith(".json")
        ext = ".json" if is_json else ".yaml"
        enriched_filename = f"enriched_spec{ext}"
        enriched_path = Path(temp_dir) / enriched_filename

        with open(enriched_path, "w", encoding="utf-8") as f:
            if is_json:
                json.dump(enriched_spec, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(enriched_spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # Parsear el nuevo spec
        from ..parsers.openapi_parser import OpenAPIParser
        parser = OpenAPIParser(strict_validation=False)
        parsed_spec = parser.parse(str(enriched_path))

        # Guardar en sesión
        _session_specs[enriched_session_id] = {
            "spec": parsed_spec,
            "spec_path": str(enriched_path),
            "temp_dir": temp_dir,
            "filename": enriched_filename,
            "enriched_from": session_id,
            "raw_spec": enriched_spec,
            "created_at": datetime.now(),
        }

        return jsonify({
            "success": True,
            "session_id": enriched_session_id,
            "new_score": new_score.to_dict(),
            "changes_applied": len(enrichments),
            "redirect_url": f"/selector?session={enriched_session_id}",
        })

    @app.route("/api/enrichment/export", methods=["POST"])
    def export_enriched_spec():
        """Exporta la especificación enriquecida como archivo descargable."""
        from ..validators import MCPUtilityScorer
        import yaml

        session_id = request.args.get("session") or (request.json or {}).get("session_id")

        if not session_id or session_id not in _session_specs:
            return jsonify({"error": "Sesión no encontrada"}), 400

        session_data = _session_specs[session_id]
        raw_spec = session_data.get("raw_spec")

        if not raw_spec:
            # Cargar desde archivo
            spec_path = session_data.get("spec_path")
            if not spec_path:
                return jsonify({"error": "No hay spec disponible"}), 400

            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()
                if spec_path.endswith(".json"):
                    raw_spec = json.loads(content)
                else:
                    raw_spec = yaml.safe_load(content)

        data = request.json or {}
        format_type = data.get("format", "yaml")

        scorer = MCPUtilityScorer()
        content = scorer.export_enriched_spec(raw_spec, format_type)

        # Crear archivo en memoria
        memory_file = io.BytesIO(content.encode("utf-8"))
        memory_file.seek(0)

        ext = ".json" if format_type == "json" else ".yaml"
        filename = f"openapi_enriched{ext}"

        return send_file(
            memory_file,
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=filename,
        )

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

        # Parámetros más comunes (obtenidos directamente del spec)
        param_types = {"path": 0, "query": 0, "header": 0, "body": 0}
        for path, operations in spec.paths.items():
            for method, operation in operations.items():
                if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                    # Contar parámetros
                    params = operation.get("parameters", [])
                    for param in params:
                        param_in = param.get("in", "").lower()
                        if param_in in param_types:
                            param_types[param_in] += 1
                    # Contar request body
                    if operation.get("requestBody"):
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
            )
            tools = tool_transformer.transform(spec, endpoint_filter=endpoint_filter)

            resource_transformer = ResourceTransformer(service_prefix=service_prefix)
            resources = resource_transformer.transform(spec)

            # Generar código en directorio temporal
            temp_dir = tempfile.mkdtemp()
            generator = MCPServerGenerator(output_dir=temp_dir)
            code_preview = generator.generate_preview(spec, tools, resources, config)

            # Programar cleanup del directorio temporal
            def cleanup_preview_temp():
                import time
                time.sleep(300)  # 5 minutos - suficiente para que el cliente procese el response
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up preview temp dir: {temp_dir}")

            cleanup_thread = threading.Thread(target=cleanup_preview_temp)
            cleanup_thread.daemon = True
            cleanup_thread.start()

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
                    "created_at": datetime.now(),
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
