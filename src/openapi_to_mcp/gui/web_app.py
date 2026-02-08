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
import time
import uuid
import webbrowser
import zipfile
from datetime import datetime, timedelta, timezone
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

    # Configurar base de datos (supports SQLite, PostgreSQL, MongoDB)
    from .db_config import configure_flask_app, get_db_config
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    configure_flask_app(app, output_dir)
    db_config = get_db_config()
    logger.info(f"Database configured: {db_config.db_type.value}")

    # Inicializar DB y Auth
    from .database import init_db
    from .auth import init_auth, create_default_admin
    init_db(app)
    init_auth(app)
    create_default_admin(app)

    # Inicializar SocketIO para actividad en tiempo real
    try:
        from flask_socketio import SocketIO
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
        logger.info("SocketIO initialized for real-time activity")
    except ImportError:
        socketio = None
        logger.warning("flask-socketio not installed, real-time activity disabled")

    # Registrar rutas
    register_routes(app)

    # Registrar eventos SocketIO
    if socketio:
        _register_socketio_events(socketio)

    # Iniciar cleanup automático de sesiones en modo standalone
    if standalone or (spec is None):
        start_background_cleanup()

    return app


def _register_socketio_events(socketio):
    """Registra eventos de SocketIO para actividad en tiempo real."""
    from flask_socketio import join_room, leave_room

    @socketio.on("join_workspace")
    def handle_join(data):
        ws_id = data.get("workspace_id")
        if ws_id:
            join_room(f"workspace_{ws_id}")

    @socketio.on("leave_workspace")
    def handle_leave(data):
        ws_id = data.get("workspace_id")
        if ws_id:
            leave_room(f"workspace_{ws_id}")


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
        from .audit import log_audit, AuditAction

        if current_user.is_authenticated:
            return redirect("/")

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = authenticate_user(username, password)
            if user:
                login_user(user)
                log_audit(
                    action=AuditAction.LOGIN_SUCCESS,
                    resource_type="user",
                    resource_id=str(user.id),
                    resource_name=user.username,
                    user_id=user.id,
                    username=user.username,
                )
                next_page = request.args.get("next", "/")
                return redirect(next_page)
            else:
                log_audit(
                    action=AuditAction.LOGIN_FAILED,
                    resource_type="user",
                    resource_name=username,
                    success=False,
                    error_message="Invalid credentials",
                )
                return render_template("login.html", error="Usuario o contrasena incorrectos")

        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """Pagina de registro."""
        from flask_login import login_user
        from .auth import register_user
        from .audit import log_audit, AuditAction

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
                log_audit(
                    action=AuditAction.USER_CREATED,
                    resource_type="user",
                    resource_id=str(user.id),
                    resource_name=user.username,
                    user_id=user.id,
                    username=user.username,
                    details={"email": email},
                )
                return redirect("/")
            except ValueError as e:
                return render_template("register.html", error=str(e))

        return render_template("register.html")

    @app.route("/logout")
    def logout():
        """Cerrar sesion."""
        from flask_login import logout_user, current_user
        from .audit import log_audit, AuditAction

        if current_user.is_authenticated:
            log_audit(
                action=AuditAction.LOGOUT,
                resource_type="user",
                resource_id=str(current_user.id),
                resource_name=current_user.username,
            )
        logout_user()
        return redirect("/login")

    # ========== Workspace Routes ==========

    @app.route("/api/workspaces", methods=["GET"])
    def list_workspaces():
        """Lista los workspaces del usuario actual."""
        from flask_login import current_user
        from .database import Workspace, WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        memberships = WorkspaceMember.query.filter_by(user_id=current_user.id).all()
        ws_ids = [m.workspace_id for m in memberships]
        workspaces = Workspace.query.filter(Workspace.id.in_(ws_ids)).all()
        return jsonify({"workspaces": [w.to_dict() for w in workspaces]})

    @app.route("/api/workspaces", methods=["POST"])
    def create_workspace():
        """Crea un nuevo workspace."""
        from flask_login import current_user
        from .database import db, Workspace, WorkspaceMember, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "El nombre es requerido"}), 400

        ws = Workspace(name=name, description=data.get("description", ""), created_by=current_user.id)
        db.session.add(ws)
        db.session.flush()

        member = WorkspaceMember(user_id=current_user.id, workspace_id=ws.id, role=UserRole.ADMIN)
        db.session.add(member)
        db.session.commit()

        _log_activity(current_user.id, ws.id, "workspace_created", "workspace", ws.name)
        return jsonify({"success": True, "workspace": ws.to_dict()})

    @app.route("/api/workspaces/<int:ws_id>", methods=["PUT"])
    def update_workspace(ws_id):
        """Actualiza un workspace."""
        from flask_login import current_user
        from .database import db, Workspace

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        ws = db.session.get(Workspace, ws_id)
        if not ws:
            return jsonify({"error": "Workspace no encontrado"}), 404

        data = request.json
        if "name" in data:
            ws.name = data["name"].strip()
        if "description" in data:
            ws.description = data["description"]
        db.session.commit()
        return jsonify({"success": True, "workspace": ws.to_dict()})

    @app.route("/api/workspaces/<int:ws_id>", methods=["DELETE"])
    def delete_workspace(ws_id):
        """Elimina un workspace."""
        from flask_login import current_user
        from .database import db, Workspace, WorkspaceMember, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        ws = db.session.get(Workspace, ws_id)
        if not ws:
            return jsonify({"error": "Workspace no encontrado"}), 404

        membership = WorkspaceMember.query.filter_by(
            user_id=current_user.id, workspace_id=ws_id
        ).first()
        if not membership or membership.role != UserRole.ADMIN:
            return jsonify({"error": "Solo el admin del workspace puede eliminarlo"}), 403

        db.session.delete(ws)
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/api/workspaces/<int:ws_id>/members", methods=["GET"])
    def list_workspace_members(ws_id):
        """Lista los miembros de un workspace."""
        from flask_login import current_user
        from .database import WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        members = WorkspaceMember.query.filter_by(workspace_id=ws_id).all()
        return jsonify({"members": [m.to_dict() for m in members]})

    @app.route("/api/workspaces/<int:ws_id>/members", methods=["POST"])
    def add_workspace_member(ws_id):
        """Agrega un miembro a un workspace."""
        from flask_login import current_user
        from .database import db, User, WorkspaceMember, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json
        username = data.get("username", "").strip()
        role = data.get("role", "editor")

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        existing = WorkspaceMember.query.filter_by(user_id=user.id, workspace_id=ws_id).first()
        if existing:
            return jsonify({"error": "El usuario ya es miembro"}), 400

        member = WorkspaceMember(user_id=user.id, workspace_id=ws_id, role=UserRole(role))
        db.session.add(member)
        db.session.commit()

        _log_activity(current_user.id, ws_id, "member_added", "workspace", f"{username} como {role}")
        return jsonify({"success": True, "member": member.to_dict()})

    @app.route("/api/workspaces/<int:ws_id>/members/<int:user_id>", methods=["DELETE"])
    def remove_workspace_member(ws_id, user_id):
        """Elimina un miembro de un workspace."""
        from flask_login import current_user
        from .database import db, WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        member = WorkspaceMember.query.filter_by(user_id=user_id, workspace_id=ws_id).first()
        if not member:
            return jsonify({"error": "Miembro no encontrado"}), 404

        db.session.delete(member)
        db.session.commit()
        return jsonify({"success": True})

    # ========== Activity Routes ==========

    @app.route("/api/activity", methods=["GET"])
    def get_activity():
        """Obtiene el log de actividad."""
        from flask_login import current_user
        from .database import ActivityLog

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        ws_id = request.args.get("workspace_id", type=int)
        limit = request.args.get("limit", 50, type=int)

        query = ActivityLog.query
        if ws_id:
            query = query.filter_by(workspace_id=ws_id)

        activities = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
        return jsonify({"activities": [a.to_dict() for a in activities]})

    def _log_activity(user_id, workspace_id, action, resource_type=None, resource_name=None, details=None):
        """Helper para registrar actividad y emitir via SocketIO si disponible."""
        from .database import db, ActivityLog
        activity = ActivityLog(
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            resource_type=resource_type,
            resource_name=resource_name,
            details=details,
        )
        db.session.add(activity)
        db.session.commit()

        # Emitir evento en tiempo real via SocketIO
        try:
            from flask_socketio import emit
            socketio = app.extensions.get("socketio")
            if socketio:
                socketio.emit("activity", activity.to_dict(), room=f"workspace_{workspace_id}")
        except Exception:
            pass  # SocketIO es opcional

        # Disparar webhooks asociados al evento
        try:
            from .webhooks import dispatch_webhook_event
            dispatch_webhook_event(workspace_id, action, {
                "resource_type": resource_type,
                "resource_name": resource_name,
                "details": details,
                "user_id": user_id,
            })
        except Exception:
            pass  # Webhooks son opcionales

    # ========== Webhook Routes ==========

    @app.route("/api/webhooks", methods=["GET"])
    def list_webhooks():
        """Lista webhooks del workspace."""
        from flask_login import current_user
        from .database import Webhook, WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        ws_id = request.args.get("workspace_id", type=int)
        if not ws_id:
            membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
            ws_id = membership.workspace_id if membership else None

        if not ws_id:
            return jsonify({"webhooks": []})

        webhooks = Webhook.query.filter_by(workspace_id=ws_id).all()
        return jsonify({"webhooks": [w.to_dict() for w in webhooks]})

    @app.route("/api/webhooks", methods=["POST"])
    def create_webhook():
        """Crea un nuevo webhook."""
        from flask_login import current_user
        from .database import db, Webhook, WorkspaceMember, UserRole
        import secrets

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        data = request.json
        url = data.get("url", "").strip()
        if not url or not url.startswith(("http://", "https://")):
            return jsonify({"error": "URL invalida"}), 400

        events = data.get("events", [])
        if not events:
            return jsonify({"error": "Debe seleccionar al menos un evento"}), 400

        ws_id = data.get("workspace_id")
        if not ws_id:
            membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
            ws_id = membership.workspace_id if membership else None

        if not ws_id:
            return jsonify({"error": "Workspace no encontrado"}), 400

        secret = secrets.token_hex(32)
        webhook = Webhook(
            workspace_id=ws_id,
            url=url,
            secret=secret,
            events=events,
            description=data.get("description", ""),
        )
        db.session.add(webhook)
        db.session.commit()

        result = webhook.to_dict()
        result["secret"] = secret  # Solo se muestra al crear
        return jsonify({"success": True, "webhook": result})

    @app.route("/api/webhooks/<int:webhook_id>", methods=["PUT"])
    def update_webhook(webhook_id):
        """Actualiza un webhook."""
        from flask_login import current_user
        from .database import db, Webhook, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        webhook = db.session.get(Webhook, webhook_id)
        if not webhook:
            return jsonify({"error": "Webhook no encontrado"}), 404

        data = request.json
        if "url" in data:
            webhook.url = data["url"].strip()
        if "events" in data:
            webhook.events = data["events"]
        if "description" in data:
            webhook.description = data["description"]
        if "is_active" in data:
            webhook.is_active = data["is_active"]

        db.session.commit()
        return jsonify({"success": True, "webhook": webhook.to_dict()})

    @app.route("/api/webhooks/<int:webhook_id>", methods=["DELETE"])
    def delete_webhook(webhook_id):
        """Elimina un webhook."""
        from flask_login import current_user
        from .database import db, Webhook, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        webhook = db.session.get(Webhook, webhook_id)
        if not webhook:
            return jsonify({"error": "Webhook no encontrado"}), 404

        db.session.delete(webhook)
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/api/webhooks/<int:webhook_id>/test", methods=["POST"])
    def test_webhook(webhook_id):
        """Envia un evento de prueba al webhook."""
        from flask_login import current_user
        from .database import db, Webhook, UserRole
        from .webhooks import _send_webhook

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        webhook = db.session.get(Webhook, webhook_id)
        if not webhook:
            return jsonify({"error": "Webhook no encontrado"}), 404

        # Enviar evento de prueba sincrono
        try:
            import requests as req
            import json as _json
            import hashlib
            import hmac as _hmac
            from datetime import datetime as _dt, timezone as _tz

            body = _json.dumps({
                "event": "test",
                "timestamp": _dt.now(_tz.utc).isoformat(),
                "data": {"message": "Webhook test from OpenAPI to MCP Generator"},
            })

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": "test",
            }

            if webhook.secret:
                sig = _hmac.new(webhook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={sig}"

            resp = req.post(webhook.url, data=body, headers=headers, timeout=10)
            return jsonify({
                "success": resp.status_code < 300,
                "status_code": resp.status_code,
                "response": resp.text[:500],
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ========== API Keys Routes ==========

    @app.route("/api/keys", methods=["GET"])
    def list_api_keys():
        """Lista las API keys del usuario."""
        from flask_login import current_user
        from .api_keys import list_user_keys

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        return jsonify({"keys": list_user_keys(current_user.id)})

    @app.route("/api/keys", methods=["POST"])
    def create_api_key():
        """Genera una nueva API key."""
        from flask_login import current_user
        from .api_keys import generate_api_key

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json or {}
        name = data.get("name", "default")
        raw_key, record = generate_api_key(current_user.id, name)

        result = record.to_dict()
        result["key"] = raw_key  # Solo se muestra una vez
        return jsonify({"success": True, "api_key": result})

    @app.route("/api/keys/<int:key_id>", methods=["DELETE"])
    def revoke_api_key_route(key_id):
        """Revoca una API key."""
        from flask_login import current_user
        from .api_keys import revoke_api_key

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        if revoke_api_key(key_id, current_user.id):
            return jsonify({"success": True})
        return jsonify({"error": "API key no encontrada"}), 404

    # ========== API v1 (Programmatic Access) ==========

    @app.route("/api/v1/specs", methods=["GET"])
    def api_v1_list_specs():
        """Lista specs disponibles en sesion."""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        specs = []
        for sid, data in _session_specs.items():
            if not sid.startswith("zip_") and "spec" in data:
                specs.append({
                    "session_id": sid,
                    "title": data["spec"].title,
                    "version": data["spec"].version,
                    "filename": data.get("filename"),
                    "created_at": data["created_at"].isoformat() if data.get("created_at") else None,
                })
        return jsonify({"specs": specs})

    @app.route("/api/v1/specs", methods=["POST"])
    def api_v1_upload_spec():
        """Sube un spec via API (JSON body con content)."""
        from flask_login import current_user
        from ..parsers.openapi_parser import OpenAPIParser, OpenAPIParserError

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json or {}
        content = data.get("content", "")
        filename = data.get("filename", "openapi.yaml")

        if not content:
            return jsonify({"error": "content es requerido"}), 400

        try:
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir) / filename
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)

            parser = OpenAPIParser(strict_validation=False)
            spec = parser.parse(str(temp_path))

            session_id = str(uuid.uuid4())[:8]
            _session_specs[session_id] = {
                "spec": spec,
                "spec_path": str(temp_path),
                "temp_dir": temp_dir,
                "filename": filename,
                "created_at": datetime.now(),
            }

            from ..endpoint_selector import EndpointSelector
            selector = EndpointSelector(spec, include_deprecated=True)
            stats = selector.get_stats()

            return jsonify({
                "success": True,
                "session_id": session_id,
                "title": spec.title,
                "version": spec.version,
                "endpoints_count": stats["total"],
            })

        except OpenAPIParserError as e:
            return jsonify({"error": f"Error parseando spec: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/generate", methods=["POST"])
    def api_v1_generate():
        """Genera servidor MCP via API."""
        from flask_login import current_user
        from ..endpoint_selector import EndpointSelector
        from ..generators.server_generator import MCPServerGenerator
        from ..models import MCPServerConfig, MCPFramework, EndpointFilter
        from ..transformers.tool_transformer import ToolTransformer
        from ..transformers.resource_transformer import ResourceTransformer

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json or {}
        session_id = data.get("session_id")

        if not session_id or session_id not in _session_specs:
            return jsonify({"error": "session_id invalido"}), 400

        spec = _session_specs[session_id]["spec"]
        selected = data.get("selected", [])
        service_name = data.get("service_name", "api")
        service_prefix = data.get("service_prefix", service_name)
        base_url = data.get("base_url") or spec.get_base_url()
        mcp_framework = data.get("mcp_framework", "fastmcp")

        try:
            endpoint_filter = EndpointFilter(selected_endpoints=selected)
            framework_map = {"fastmcp": MCPFramework.FASTMCP, "mcp": MCPFramework.MCP, "typescript": MCPFramework.TYPESCRIPT}
            framework = framework_map.get(mcp_framework, MCPFramework.FASTMCP)
            config = MCPServerConfig(
                service_name=service_name,
                service_prefix=service_prefix,
                base_url=base_url,
                mcp_framework=framework,
            )

            tool_transformer = ToolTransformer(service_prefix=service_prefix)
            tools = tool_transformer.transform(spec, endpoint_filter=endpoint_filter)

            resource_transformer = ResourceTransformer(service_prefix=service_prefix)
            resources = resource_transformer.transform(spec, tools)

            temp_output = tempfile.mkdtemp()
            generator = MCPServerGenerator(output_dir=temp_output)
            result = generator.generate(spec=spec, tools=tools, resources=resources, config=config)

            if result.success:
                zip_id = str(uuid.uuid4())[:8]
                _session_specs[f"zip_{zip_id}"] = {
                    "output_path": result.output_path,
                    "temp_dir": temp_output,
                    "zip_filename": f"mcp_server_{service_name}.zip",
                    "created_at": datetime.now(),
                }

                return jsonify({
                    "success": True,
                    "tools_count": len(result.tools_generated),
                    "resources_count": len(result.resources_generated),
                    "download_url": f"/api/download/{zip_id}",
                    "warnings": result.warnings,
                })
            else:
                return jsonify({
                    "success": False,
                    "errors": result.errors,
                }), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/webhooks", methods=["GET"])
    def api_v1_list_webhooks():
        """Lista webhooks via API."""
        from flask_login import current_user
        from .database import Webhook, WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
        ws_id = membership.workspace_id if membership else None
        if not ws_id:
            return jsonify({"webhooks": []})

        webhooks = Webhook.query.filter_by(workspace_id=ws_id).all()
        return jsonify({"webhooks": [w.to_dict() for w in webhooks]})

    # ========== GitHub Integration Routes ==========

    @app.route("/api/integrations/github/repos", methods=["GET"])
    def github_list_repos():
        """Lista repositorios de GitHub del usuario."""
        from flask_login import current_user
        from .integrations import GitHubIntegration

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        token = request.headers.get("X-GitHub-Token") or request.args.get("token")
        if not token:
            return jsonify({"error": "Token de GitHub requerido (header X-GitHub-Token)"}), 400

        try:
            gh = GitHubIntegration(token)
            repos = gh.list_repos()
            return jsonify({"repos": [r.to_dict() for r in repos]})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/integrations/github/branches", methods=["GET"])
    def github_list_branches():
        """Lista branches de un repositorio GitHub."""
        from flask_login import current_user
        from .integrations import GitHubIntegration

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        token = request.headers.get("X-GitHub-Token")
        repo = request.args.get("repo")
        if not token or not repo:
            return jsonify({"error": "Token y repo son requeridos"}), 400

        try:
            gh = GitHubIntegration(token)
            branches = gh.list_branches(repo)
            return jsonify({"branches": branches})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/integrations/github/files", methods=["GET"])
    def github_find_files():
        """Busca archivos OpenAPI en un repositorio GitHub."""
        from flask_login import current_user
        from .integrations import GitHubIntegration

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        token = request.headers.get("X-GitHub-Token")
        repo = request.args.get("repo")
        branch = request.args.get("branch")
        if not token or not repo:
            return jsonify({"error": "Token y repo son requeridos"}), 400

        try:
            gh = GitHubIntegration(token)
            files = gh.find_openapi_files(repo, branch)
            return jsonify({"files": [f.to_dict() for f in files]})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/integrations/github/fetch", methods=["POST"])
    def github_fetch_spec():
        """Descarga e importa un spec desde GitHub."""
        from flask_login import current_user
        from .integrations import GitHubIntegration
        from ..parsers.openapi_parser import OpenAPIParser

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json or {}
        token = request.headers.get("X-GitHub-Token") or data.get("token")
        repo = data.get("repo")
        file_path = data.get("file_path")
        branch = data.get("branch")

        if not token or not repo or not file_path:
            return jsonify({"error": "Token, repo y file_path son requeridos"}), 400

        try:
            gh = GitHubIntegration(token)
            content = gh.fetch_file_content(repo, file_path, branch)

            # Guardar y parsear
            filename = file_path.split("/")[-1]
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir) / filename
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)

            parser = OpenAPIParser(strict_validation=False)
            spec = parser.parse(str(temp_path))

            session_id = str(uuid.uuid4())[:8]
            _session_specs[session_id] = {
                "spec": spec,
                "spec_path": str(temp_path),
                "temp_dir": temp_dir,
                "filename": filename,
                "source_repo": repo,
                "source_branch": branch,
                "source_file": file_path,
                "created_at": datetime.now(),
            }

            from ..endpoint_selector import EndpointSelector
            selector = EndpointSelector(spec, include_deprecated=True)
            stats = selector.get_stats()

            return jsonify({
                "success": True,
                "session_id": session_id,
                "title": spec.title,
                "version": spec.version,
                "endpoints_count": stats["total"],
                "redirect_url": f"/selector?session={session_id}",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    # ========== GitLab Integration Routes ==========

    @app.route("/api/integrations/gitlab/repos", methods=["GET"])
    def gitlab_list_repos():
        """Lista proyectos de GitLab del usuario."""
        from flask_login import current_user
        from .integrations import GitLabIntegration

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        token = request.headers.get("X-GitLab-Token") or request.args.get("token")
        base_url = request.args.get("base_url")
        if not token:
            return jsonify({"error": "Token de GitLab requerido (header X-GitLab-Token)"}), 400

        try:
            gl = GitLabIntegration(token, base_url) if base_url else GitLabIntegration(token)
            repos = gl.list_repos()
            return jsonify({"repos": [r.to_dict() for r in repos]})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/integrations/gitlab/branches", methods=["GET"])
    def gitlab_list_branches():
        """Lista branches de un proyecto GitLab."""
        from flask_login import current_user
        from .integrations import GitLabIntegration

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        token = request.headers.get("X-GitLab-Token")
        project = request.args.get("project")
        base_url = request.args.get("base_url")
        if not token or not project:
            return jsonify({"error": "Token y project son requeridos"}), 400

        try:
            gl = GitLabIntegration(token, base_url) if base_url else GitLabIntegration(token)
            branches = gl.list_branches(project)
            return jsonify({"branches": branches})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/integrations/gitlab/files", methods=["GET"])
    def gitlab_find_files():
        """Busca archivos OpenAPI en un proyecto GitLab."""
        from flask_login import current_user
        from .integrations import GitLabIntegration

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        token = request.headers.get("X-GitLab-Token")
        project = request.args.get("project")
        branch = request.args.get("branch")
        base_url = request.args.get("base_url")
        if not token or not project:
            return jsonify({"error": "Token y project son requeridos"}), 400

        try:
            gl = GitLabIntegration(token, base_url) if base_url else GitLabIntegration(token)
            files = gl.find_openapi_files(project, branch)
            return jsonify({"files": [f.to_dict() for f in files]})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/integrations/gitlab/fetch", methods=["POST"])
    def gitlab_fetch_spec():
        """Descarga e importa un spec desde GitLab."""
        from flask_login import current_user
        from .integrations import GitLabIntegration
        from ..parsers.openapi_parser import OpenAPIParser

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        data = request.json or {}
        token = request.headers.get("X-GitLab-Token") or data.get("token")
        project = data.get("project")
        file_path = data.get("file_path")
        branch = data.get("branch")
        base_url = data.get("base_url")

        if not token or not project or not file_path:
            return jsonify({"error": "Token, project y file_path son requeridos"}), 400

        try:
            gl = GitLabIntegration(token, base_url) if base_url else GitLabIntegration(token)
            content = gl.fetch_file_content(project, file_path, branch)

            filename = file_path.split("/")[-1]
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir) / filename
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)

            parser = OpenAPIParser(strict_validation=False)
            spec = parser.parse(str(temp_path))

            session_id = str(uuid.uuid4())[:8]
            _session_specs[session_id] = {
                "spec": spec,
                "spec_path": str(temp_path),
                "temp_dir": temp_dir,
                "filename": filename,
                "source_project": project,
                "source_branch": branch,
                "source_file": file_path,
                "created_at": datetime.now(),
            }

            from ..endpoint_selector import EndpointSelector
            selector = EndpointSelector(spec, include_deprecated=True)
            stats = selector.get_stats()

            return jsonify({
                "success": True,
                "session_id": session_id,
                "title": spec.title,
                "version": spec.version,
                "endpoints_count": stats["total"],
                "redirect_url": f"/selector?session={session_id}",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    # ========== Repository Sync Routes ==========

    @app.route("/api/repo-syncs", methods=["GET"])
    def list_repo_syncs():
        """Lista configuraciones de sincronizacion."""
        from flask_login import current_user
        from .database import RepoSync, WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
        ws_id = membership.workspace_id if membership else None
        if not ws_id:
            return jsonify({"syncs": []})

        syncs = RepoSync.query.filter_by(workspace_id=ws_id).all()
        return jsonify({"syncs": [s.to_dict() for s in syncs]})

    @app.route("/api/repo-syncs", methods=["POST"])
    def create_repo_sync():
        """Crea una nueva configuracion de sincronizacion."""
        from flask_login import current_user
        from .database import db, RepoSync, WorkspaceMember, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        data = request.json or {}
        provider = data.get("provider", "github")
        repo_url = data.get("repo_url", "").strip()
        branch = data.get("branch", "main")
        file_path = data.get("file_path", "").strip()
        access_token = data.get("access_token", "").strip()

        if not repo_url or not file_path:
            return jsonify({"error": "repo_url y file_path son requeridos"}), 400

        membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
        ws_id = membership.workspace_id if membership else None
        if not ws_id:
            return jsonify({"error": "Workspace no encontrado"}), 400

        sync = RepoSync(
            workspace_id=ws_id,
            provider=provider,
            repo_url=repo_url,
            branch=branch,
            file_path=file_path,
            access_token=access_token,
        )
        db.session.add(sync)
        db.session.commit()

        return jsonify({"success": True, "sync": sync.to_dict()})

    @app.route("/api/repo-syncs/<int:sync_id>", methods=["PUT"])
    def update_repo_sync(sync_id):
        """Actualiza una configuracion de sincronizacion."""
        from flask_login import current_user
        from .database import db, RepoSync, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        sync = db.session.get(RepoSync, sync_id)
        if not sync:
            return jsonify({"error": "Sync no encontrado"}), 404

        data = request.json or {}
        if "branch" in data:
            sync.branch = data["branch"]
        if "file_path" in data:
            sync.file_path = data["file_path"]
        if "access_token" in data:
            sync.access_token = data["access_token"]
        if "is_active" in data:
            sync.is_active = data["is_active"]

        db.session.commit()
        return jsonify({"success": True, "sync": sync.to_dict()})

    @app.route("/api/repo-syncs/<int:sync_id>", methods=["DELETE"])
    def delete_repo_sync(sync_id):
        """Elimina una configuracion de sincronizacion."""
        from flask_login import current_user
        from .database import db, RepoSync, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        sync = db.session.get(RepoSync, sync_id)
        if not sync:
            return jsonify({"error": "Sync no encontrado"}), 404

        db.session.delete(sync)
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/api/repo-syncs/<int:sync_id>/check", methods=["POST"])
    def check_repo_sync_now(sync_id):
        """Verifica si hay cambios en el repositorio."""
        from flask_login import current_user
        from .database import db, RepoSync
        from .integrations import check_repo_sync
        from datetime import datetime, timezone

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        sync = db.session.get(RepoSync, sync_id)
        if not sync:
            return jsonify({"error": "Sync no encontrado"}), 404

        config = {
            "provider": sync.provider,
            "repo_url": sync.repo_url,
            "branch": sync.branch,
            "file_path": sync.file_path,
            "access_token": sync.access_token,
            "last_sha": sync.last_sha,
        }

        change = check_repo_sync(config)
        if change:
            sync.last_sha = change["sha"]
            sync.last_sync = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({
                "changed": True,
                "new_sha": change["sha"],
                "content_preview": change["content"][:500] if change.get("content") else None,
            })

        return jsonify({"changed": False})

    # ========== Notification Channel Routes ==========

    @app.route("/api/notifications/channels", methods=["GET"])
    def list_notification_channels():
        """Lista canales de notificacion del workspace."""
        from flask_login import current_user
        from .database import NotificationChannel, WorkspaceMember

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
        ws_id = membership.workspace_id if membership else None
        if not ws_id:
            return jsonify({"channels": []})

        channels = NotificationChannel.query.filter_by(workspace_id=ws_id).all()
        return jsonify({"channels": [c.to_dict() for c in channels]})

    @app.route("/api/notifications/channels", methods=["POST"])
    def create_notification_channel():
        """Crea un nuevo canal de notificacion."""
        from flask_login import current_user
        from .database import db, NotificationChannel, WorkspaceMember, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        data = request.json or {}
        channel_type = data.get("type", "").lower()
        name = data.get("name", "").strip()
        config = data.get("config", {})

        if channel_type not in ("slack", "discord", "email"):
            return jsonify({"error": "Tipo de canal invalido (slack, discord, email)"}), 400
        if not name:
            return jsonify({"error": "Nombre es requerido"}), 400

        membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
        ws_id = membership.workspace_id if membership else None
        if not ws_id:
            return jsonify({"error": "Workspace no encontrado"}), 400

        channel = NotificationChannel(
            workspace_id=ws_id,
            name=name,
            channel_type=channel_type,
            config=config,
        )
        db.session.add(channel)
        db.session.commit()

        return jsonify({"success": True, "channel": channel.to_dict()})

    @app.route("/api/notifications/channels/<int:channel_id>", methods=["PUT"])
    def update_notification_channel(channel_id):
        """Actualiza un canal de notificacion."""
        from flask_login import current_user
        from .database import db, NotificationChannel, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        channel = db.session.get(NotificationChannel, channel_id)
        if not channel:
            return jsonify({"error": "Canal no encontrado"}), 404

        data = request.json or {}
        if "name" in data:
            channel.name = data["name"]
        if "config" in data:
            channel.config = data["config"]
        if "is_active" in data:
            channel.is_active = data["is_active"]

        db.session.commit()
        return jsonify({"success": True, "channel": channel.to_dict()})

    @app.route("/api/notifications/channels/<int:channel_id>", methods=["DELETE"])
    def delete_notification_channel(channel_id):
        """Elimina un canal de notificacion."""
        from flask_login import current_user
        from .database import db, NotificationChannel, UserRole

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401
        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Permisos insuficientes"}), 403

        channel = db.session.get(NotificationChannel, channel_id)
        if not channel:
            return jsonify({"error": "Canal no encontrado"}), 404

        db.session.delete(channel)
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/api/notifications/channels/<int:channel_id>/test", methods=["POST"])
    def test_notification_channel(channel_id):
        """Envia una notificacion de prueba."""
        from flask_login import current_user
        from .database import NotificationChannel
        from .notifications import create_notifier

        if not current_user.is_authenticated:
            return jsonify({"error": "Autenticacion requerida"}), 401

        channel = db.session.get(NotificationChannel, channel_id)
        if not channel:
            return jsonify({"error": "Canal no encontrado"}), 404

        config = {"type": channel.channel_type, **channel.config}
        notifier = create_notifier(config)

        if notifier:
            success = notifier.send(
                "Test de Notificacion",
                "Esta es una notificacion de prueba desde OpenAPI to MCP Generator.",
            )
            return jsonify({"success": success})

        return jsonify({"error": "No se pudo crear el notificador"}), 400

    # ========== Admin Routes ==========

    @app.route("/admin")
    def admin_panel():
        """Panel de administracion."""
        from flask_login import current_user
        from .auth import admin_required as _admin_check
        from .database import UserRole

        if not current_user.is_authenticated:
            return redirect("/login")
        if not current_user.has_role(UserRole.ADMIN):
            return redirect("/")
        return render_template("admin.html")

    @app.route("/api/admin/users")
    def admin_list_users():
        """Lista todos los usuarios (solo admin)."""
        from flask_login import current_user
        from .database import User, UserRole

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Permisos insuficientes"}), 403

        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify({"users": [u.to_dict() for u in users]})

    @app.route("/api/admin/users/<int:user_id>/role", methods=["PUT"])
    def admin_change_role(user_id):
        """Cambia el rol de un usuario."""
        from flask_login import current_user
        from .database import db, User, UserRole

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Permisos insuficientes"}), 403

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if user.username == "admin":
            return jsonify({"error": "No se puede cambiar el rol del admin principal"}), 400

        data = request.json
        new_role = data.get("role")
        try:
            user.role = UserRole(new_role)
            db.session.commit()
            return jsonify({"success": True})
        except (ValueError, KeyError):
            return jsonify({"error": "Rol invalido"}), 400

    @app.route("/api/admin/users/<int:user_id>/status", methods=["PUT"])
    def admin_toggle_status(user_id):
        """Activa/desactiva un usuario."""
        from flask_login import current_user
        from .database import db, User, UserRole

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Permisos insuficientes"}), 403

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if user.username == "admin":
            return jsonify({"error": "No se puede desactivar el admin principal"}), 400

        data = request.json
        user.is_active = data.get("is_active", True)
        db.session.commit()
        return jsonify({"success": True})

    # ========== Audit Log Routes ==========

    @app.route("/api/audit/logs")
    def get_audit_logs():
        """Get audit logs with filtering (admin only)."""
        from flask_login import current_user
        from .database import UserRole
        from .audit import query_audit_logs, AuditAction, AuditSeverity

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        # Parse filters from query params
        user_id = request.args.get("user_id", type=int)
        workspace_id = request.args.get("workspace_id", type=int)
        action = request.args.get("action")
        severity = request.args.get("severity")
        resource_type = request.args.get("resource_type")
        success = request.args.get("success")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Parse dates
        start_date = None
        end_date = None
        if request.args.get("start_date"):
            try:
                start_date = datetime.fromisoformat(request.args.get("start_date"))
            except ValueError:
                pass
        if request.args.get("end_date"):
            try:
                end_date = datetime.fromisoformat(request.args.get("end_date"))
            except ValueError:
                pass

        # Convert string params to enums
        action_enum = None
        if action:
            try:
                action_enum = AuditAction(action)
            except ValueError:
                pass

        severity_enum = None
        if severity:
            try:
                severity_enum = AuditSeverity(severity)
            except ValueError:
                pass

        success_bool = None
        if success is not None:
            success_bool = success.lower() == "true"

        logs, total = query_audit_logs(
            user_id=user_id,
            workspace_id=workspace_id,
            action=action_enum,
            severity=severity_enum,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            success=success_bool,
            limit=min(limit, 500),
            offset=offset,
        )

        return jsonify({
            "logs": [log.to_dict() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset,
        })

    @app.route("/api/audit/summary")
    def get_audit_summary():
        """Get audit summary statistics (admin only)."""
        from flask_login import current_user
        from .database import UserRole
        from .audit import get_audit_summary

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        summary = get_audit_summary(days=min(days, 365))
        return jsonify(summary)

    @app.route("/api/audit/export")
    def export_audit_logs():
        """Export audit logs (admin only)."""
        from flask_login import current_user
        from .database import UserRole
        from .audit import export_audit_logs as do_export, log_audit, AuditAction

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        format = request.args.get("format", "json")
        if format not in ("json", "csv"):
            return jsonify({"error": "Invalid format. Use 'json' or 'csv'"}), 400

        # Get filters
        user_id = request.args.get("user_id", type=int)
        workspace_id = request.args.get("workspace_id", type=int)

        data = do_export(format=format, user_id=user_id, workspace_id=workspace_id)

        # Log the export action
        log_audit(
            action=AuditAction.AUDIT_LOG_EXPORTED,
            resource_type="audit_log",
            details={"format": format, "user_id": user_id, "workspace_id": workspace_id}
        )

        if format == "csv":
            return send_file(
                io.BytesIO(data.encode("utf-8")),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
        else:
            return send_file(
                io.BytesIO(data.encode("utf-8")),
                mimetype="application/json",
                as_attachment=True,
                download_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

    @app.route("/api/audit/actions")
    def get_audit_actions():
        """Get available audit action types."""
        from .audit import AuditAction, AuditSeverity

        return jsonify({
            "actions": [a.value for a in AuditAction],
            "severities": [s.value for s in AuditSeverity],
        })

    # ========== Encryption Routes ==========

    @app.route("/api/encryption/encrypt", methods=["POST"])
    def encrypt_spec_route():
        """Encrypt a specification."""
        from flask_login import current_user
        from .database import UserRole
        from .encryption import encrypt_spec, EncryptionError
        from .audit import log_audit, AuditAction

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Editor access required"}), 403

        data = request.json
        spec_id = data.get("spec_id")
        content = data.get("content")
        password = data.get("password")
        workspace_id = data.get("workspace_id")
        filename = data.get("filename")
        title = data.get("title")
        version = data.get("version")

        if not spec_id or not content or not password:
            return jsonify({"error": "spec_id, content, and password are required"}), 400

        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400

        try:
            encrypted_spec = encrypt_spec(
                spec_id=spec_id,
                content=content,
                password=password,
                workspace_id=workspace_id,
                user_id=current_user.id,
                filename=filename,
                title=title,
                version=version,
            )

            log_audit(
                action=AuditAction.SPEC_ENCRYPTED,
                resource_type="spec",
                resource_id=spec_id,
                resource_name=title or filename,
                workspace_id=workspace_id,
            )

            return jsonify({
                "success": True,
                "spec_id": spec_id,
                "encrypted_at": encrypted_spec.encrypted_at.isoformat(),
            })

        except EncryptionError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Encryption failed")
            return jsonify({"error": f"Encryption failed: {str(e)}"}), 500

    @app.route("/api/encryption/decrypt", methods=["POST"])
    def decrypt_spec_route():
        """Decrypt a specification."""
        from flask_login import current_user
        from .database import UserRole
        from .encryption import decrypt_spec, DecryptionError
        from .audit import log_audit, AuditAction

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Editor access required"}), 403

        data = request.json
        spec_id = data.get("spec_id")
        password = data.get("password")

        if not spec_id or not password:
            return jsonify({"error": "spec_id and password are required"}), 400

        try:
            content = decrypt_spec(spec_id, password)

            log_audit(
                action=AuditAction.SPEC_DECRYPTED,
                resource_type="spec",
                resource_id=spec_id,
            )

            return jsonify({
                "success": True,
                "spec_id": spec_id,
                "content": content,
            })

        except DecryptionError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Decryption failed")
            return jsonify({"error": f"Decryption failed: {str(e)}"}), 500

    @app.route("/api/encryption/list")
    def list_encrypted_specs_route():
        """List encrypted specifications."""
        from flask_login import current_user
        from .database import UserRole
        from .encryption import list_encrypted_specs

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        workspace_id = request.args.get("workspace_id", type=int)

        specs = list_encrypted_specs(workspace_id=workspace_id)
        return jsonify({
            "specs": [s.to_dict() for s in specs],
            "count": len(specs),
        })

    @app.route("/api/encryption/status/<spec_id>")
    def get_encryption_status_route(spec_id):
        """Get encryption status for a spec."""
        from flask_login import current_user
        from .encryption import get_encryption_status

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        status = get_encryption_status(spec_id)
        if status:
            return jsonify(status)
        else:
            return jsonify({"encrypted": False, "spec_id": spec_id})

    @app.route("/api/encryption/rotate", methods=["POST"])
    def rotate_encryption_key_route():
        """Rotate encryption key for a spec."""
        from flask_login import current_user
        from .database import UserRole
        from .encryption import rotate_encryption_key

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        if not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Editor access required"}), 403

        data = request.json
        spec_id = data.get("spec_id")
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not spec_id or not old_password or not new_password:
            return jsonify({"error": "spec_id, old_password, and new_password are required"}), 400

        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters"}), 400

        success = rotate_encryption_key(spec_id, old_password, new_password)
        if success:
            return jsonify({"success": True, "spec_id": spec_id})
        else:
            return jsonify({"error": "Key rotation failed. Check passwords."}), 400

    @app.route("/api/encryption/delete/<spec_id>", methods=["DELETE"])
    def delete_encrypted_spec_route(spec_id):
        """Delete an encrypted specification."""
        from flask_login import current_user
        from .database import UserRole
        from .encryption import delete_encrypted_spec

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        if not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        deleted = delete_encrypted_spec(spec_id)
        if deleted:
            return jsonify({"success": True, "spec_id": spec_id})
        else:
            return jsonify({"error": "Encrypted spec not found"}), 404

    # ========== Data Retention Routes ==========

    @app.route("/api/retention/policies")
    def list_retention_policies_route():
        """List all retention policies."""
        from flask_login import current_user
        from .database import UserRole
        from .retention import list_retention_policies

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        workspace_id = request.args.get("workspace_id", type=int)
        policies = list_retention_policies(workspace_id)
        return jsonify({"policies": policies})

    @app.route("/api/retention/policies", methods=["POST"])
    def set_retention_policy_route():
        """Set or update a retention policy."""
        from flask_login import current_user
        from .database import UserRole
        from .retention import set_retention_policy, DataType, RetentionAction

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data = request.json
        data_type_str = data.get("data_type")
        retention_days = data.get("retention_days")
        action_str = data.get("action", "delete")
        workspace_id = data.get("workspace_id")

        if not data_type_str or retention_days is None:
            return jsonify({"error": "data_type and retention_days are required"}), 400

        try:
            data_type = DataType(data_type_str)
            action = RetentionAction(action_str)
        except ValueError:
            return jsonify({"error": "Invalid data_type or action"}), 400

        policy = set_retention_policy(
            data_type=data_type,
            retention_days=retention_days,
            action=action,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        return jsonify({"success": True, "policy": policy.to_dict()})

    @app.route("/api/retention/apply", methods=["POST"])
    def apply_retention_route():
        """Apply retention policies."""
        from flask_login import current_user
        from .database import UserRole
        from .retention import apply_retention_policy, apply_all_retention_policies, DataType

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data = request.json
        data_type_str = data.get("data_type")
        workspace_id = data.get("workspace_id")
        dry_run = data.get("dry_run", False)

        if data_type_str:
            try:
                data_type = DataType(data_type_str)
            except ValueError:
                return jsonify({"error": "Invalid data_type"}), 400

            result = apply_retention_policy(data_type, workspace_id, dry_run)
            return jsonify(result)
        else:
            results = apply_all_retention_policies(workspace_id, dry_run)
            return jsonify({"results": results})

    @app.route("/api/retention/stats")
    def get_retention_stats_route():
        """Get retention statistics."""
        from flask_login import current_user
        from .database import UserRole
        from .retention import get_retention_stats

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        stats = get_retention_stats()
        return jsonify({"stats": stats})

    @app.route("/api/retention/history")
    def get_retention_history_route():
        """Get retention execution history."""
        from flask_login import current_user
        from .database import UserRole
        from .retention import get_execution_history, DataType

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data_type_str = request.args.get("data_type")
        limit = request.args.get("limit", 100, type=int)

        data_type = None
        if data_type_str:
            try:
                data_type = DataType(data_type_str)
            except ValueError:
                pass

        history = get_execution_history(data_type, min(limit, 500))
        return jsonify({"history": [h.to_dict() for h in history]})

    @app.route("/api/retention/data-types")
    def get_data_types_route():
        """Get available data types for retention policies."""
        from .retention import DataType, RetentionAction, DEFAULT_RETENTION

        return jsonify({
            "data_types": [dt.value for dt in DataType],
            "actions": [a.value for a in RetentionAction],
            "defaults": {dt.value: days for dt, days in DEFAULT_RETENTION.items()},
        })

    # ========== Metrics & Dashboard Routes ==========

    @app.route("/api/metrics/overview")
    def get_overview_metrics_route():
        """Get platform overview metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_overview_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        return jsonify(get_overview_metrics())

    @app.route("/api/metrics/users")
    def get_user_metrics_route():
        """Get user metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_user_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        return jsonify(get_user_metrics(min(days, 365)))

    @app.route("/api/metrics/activity")
    def get_activity_metrics_route():
        """Get activity metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_activity_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        return jsonify(get_activity_metrics(min(days, 365)))

    @app.route("/api/metrics/workspaces")
    def get_workspace_metrics_route():
        """Get workspace metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_workspace_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        return jsonify(get_workspace_metrics())

    @app.route("/api/metrics/generations")
    def get_generation_metrics_route():
        """Get MCP generation metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_generation_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        return jsonify(get_generation_metrics(min(days, 365)))

    @app.route("/api/metrics/api-usage")
    def get_api_usage_metrics_route():
        """Get API usage metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_api_usage_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        return jsonify(get_api_usage_metrics(min(days, 365)))

    @app.route("/api/metrics/security")
    def get_security_metrics_route():
        """Get security metrics."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_security_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        return jsonify(get_security_metrics(min(days, 365)))

    @app.route("/api/metrics/dashboard")
    def get_dashboard_metrics_route():
        """Get all dashboard metrics in one call."""
        from flask_login import current_user
        from .database import UserRole
        from .metrics import get_all_dashboard_metrics

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        days = request.args.get("days", 30, type=int)
        return jsonify(get_all_dashboard_metrics(min(days, 365)))

    # ========== Alerts Routes ==========

    @app.route("/api/alerts/rules", methods=["GET"])
    def list_alert_rules_route():
        """List alert rules."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import list_alert_rules

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        workspace_id = request.args.get("workspace_id", type=int)
        is_active = request.args.get("is_active")
        if is_active is not None:
            is_active = is_active.lower() == "true"

        rules = list_alert_rules(workspace_id, is_active)
        return jsonify({"rules": [r.to_dict() for r in rules]})

    @app.route("/api/alerts/rules", methods=["POST"])
    def create_alert_rule_route():
        """Create a new alert rule."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import create_alert_rule, AlertType, AlertSeverity

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data = request.json
        try:
            alert_type = AlertType(data.get("alert_type"))
            severity = AlertSeverity(data.get("severity", "warning"))
        except ValueError:
            return jsonify({"error": "Invalid alert_type or severity"}), 400

        rule = create_alert_rule(
            name=data.get("name"),
            alert_type=alert_type,
            threshold_value=data.get("threshold_value", 5),
            severity=severity,
            threshold_period_minutes=data.get("threshold_period_minutes", 60),
            notification_channels=data.get("notification_channels", []),
            cooldown_minutes=data.get("cooldown_minutes", 30),
            workspace_id=data.get("workspace_id"),
            user_id=current_user.id,
            description=data.get("description"),
        )

        return jsonify({"success": True, "rule": rule.to_dict()})

    @app.route("/api/alerts/rules/<int:rule_id>", methods=["PUT"])
    def update_alert_rule_route(rule_id):
        """Update an alert rule."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import update_alert_rule

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data = request.json
        rule = update_alert_rule(rule_id, **data)
        if rule:
            return jsonify({"success": True, "rule": rule.to_dict()})
        return jsonify({"error": "Rule not found"}), 404

    @app.route("/api/alerts/rules/<int:rule_id>", methods=["DELETE"])
    def delete_alert_rule_route(rule_id):
        """Delete an alert rule."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import delete_alert_rule

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        if delete_alert_rule(rule_id):
            return jsonify({"success": True})
        return jsonify({"error": "Rule not found"}), 404

    @app.route("/api/alerts", methods=["GET"])
    def list_alerts_route():
        """List alerts."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import list_alerts, AlertStatus, AlertSeverity, AlertType

        if not current_user.is_authenticated or not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Access denied"}), 403

        workspace_id = request.args.get("workspace_id", type=int)
        status_str = request.args.get("status")
        severity_str = request.args.get("severity")
        type_str = request.args.get("type")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        status = AlertStatus(status_str) if status_str else None
        severity = AlertSeverity(severity_str) if severity_str else None
        alert_type = AlertType(type_str) if type_str else None

        alerts, total = list_alerts(
            workspace_id=workspace_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
            limit=min(limit, 500),
            offset=offset,
        )

        return jsonify({
            "alerts": [a.to_dict() for a in alerts],
            "total": total,
        })

    @app.route("/api/alerts/<int:alert_id>/acknowledge", methods=["POST"])
    def acknowledge_alert_route(alert_id):
        """Acknowledge an alert."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import acknowledge_alert

        if not current_user.is_authenticated or not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Access denied"}), 403

        alert = acknowledge_alert(alert_id, current_user.id)
        if alert:
            return jsonify({"success": True, "alert": alert.to_dict()})
        return jsonify({"error": "Alert not found"}), 404

    @app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
    def resolve_alert_route(alert_id):
        """Resolve an alert."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import resolve_alert

        if not current_user.is_authenticated or not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Access denied"}), 403

        alert = resolve_alert(alert_id, current_user.id)
        if alert:
            return jsonify({"success": True, "alert": alert.to_dict()})
        return jsonify({"error": "Alert not found"}), 404

    @app.route("/api/alerts/<int:alert_id>/snooze", methods=["POST"])
    def snooze_alert_route(alert_id):
        """Snooze an alert."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import snooze_alert

        if not current_user.is_authenticated or not current_user.has_role(UserRole.EDITOR):
            return jsonify({"error": "Access denied"}), 403

        data = request.json
        minutes = data.get("minutes", 60)
        alert = snooze_alert(alert_id, minutes)
        if alert:
            return jsonify({"success": True, "alert": alert.to_dict()})
        return jsonify({"error": "Alert not found"}), 404

    @app.route("/api/alerts/check", methods=["POST"])
    def check_alerts_route():
        """Manually trigger alert checking."""
        from flask_login import current_user
        from .database import UserRole
        from .alerts import check_alert_rules

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        new_alerts = check_alert_rules()
        return jsonify({
            "success": True,
            "new_alerts": len(new_alerts),
            "alerts": [a.to_dict() for a in new_alerts],
        })

    @app.route("/api/alerts/count")
    def get_alert_count_route():
        """Get count of active alerts."""
        from flask_login import current_user
        from .alerts import get_active_alert_count

        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        return jsonify(get_active_alert_count())

    @app.route("/api/alerts/types")
    def get_alert_types_route():
        """Get available alert types."""
        from .alerts import AlertType, AlertSeverity, AlertStatus

        return jsonify({
            "types": [t.value for t in AlertType],
            "severities": [s.value for s in AlertSeverity],
            "statuses": [s.value for s in AlertStatus],
        })

    # ========== Reports Routes ==========

    @app.route("/api/reports/scheduled", methods=["GET"])
    def list_scheduled_reports_route():
        """List scheduled reports."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import list_scheduled_reports

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        workspace_id = request.args.get("workspace_id", type=int)
        reports = list_scheduled_reports(workspace_id)
        return jsonify({"reports": [r.to_dict() for r in reports]})

    @app.route("/api/reports/scheduled", methods=["POST"])
    def create_scheduled_report_route():
        """Create a new scheduled report."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import (
            create_scheduled_report, ReportType, ReportSchedule, ReportFormat
        )

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data = request.json
        try:
            report_type = ReportType(data.get("report_type"))
            schedule = ReportSchedule(data.get("schedule"))
            format = ReportFormat(data.get("format", "json"))
        except ValueError:
            return jsonify({"error": "Invalid report_type, schedule, or format"}), 400

        if not data.get("name"):
            return jsonify({"error": "Report name is required"}), 400

        scheduled = create_scheduled_report(
            name=data.get("name"),
            report_type=report_type,
            schedule=schedule,
            format=format,
            email_recipients=data.get("email_recipients", []),
            webhook_url=data.get("webhook_url"),
            workspace_id=data.get("workspace_id"),
            user_id=current_user.id,
        )

        return jsonify({"success": True, "report": scheduled.to_dict()})

    @app.route("/api/reports/scheduled/<int:report_id>", methods=["DELETE"])
    def delete_scheduled_report_route(report_id):
        """Delete a scheduled report."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import ScheduledReport

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        scheduled = db.session.get(ScheduledReport, report_id)
        if not scheduled:
            return jsonify({"error": "Scheduled report not found"}), 404

        db.session.delete(scheduled)
        db.session.commit()
        return jsonify({"success": True})

    @app.route("/api/reports/generate", methods=["POST"])
    def generate_report_route():
        """Generate a report on demand."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import generate_report, ReportType

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        data = request.json
        try:
            report_type = ReportType(data.get("report_type"))
        except ValueError:
            return jsonify({"error": "Invalid report_type"}), 400

        period_days = data.get("period_days", 30)
        workspace_id = data.get("workspace_id")

        report = generate_report(
            report_type=report_type,
            period_days=min(period_days, 365),
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        return jsonify({
            "success": True,
            "report": report.to_dict(),
            "data": report.data,
        })

    @app.route("/api/reports/generated", methods=["GET"])
    def list_generated_reports_route():
        """List generated reports."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import list_generated_reports, ReportType

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        report_type_str = request.args.get("report_type")
        workspace_id = request.args.get("workspace_id", type=int)
        limit = request.args.get("limit", 50, type=int)

        report_type = None
        if report_type_str:
            try:
                report_type = ReportType(report_type_str)
            except ValueError:
                pass

        reports = list_generated_reports(
            report_type=report_type,
            workspace_id=workspace_id,
            limit=min(limit, 200),
        )

        return jsonify({"reports": [r.to_dict() for r in reports]})

    @app.route("/api/reports/generated/<int:report_id>", methods=["GET"])
    def get_generated_report_route(report_id):
        """Get a specific generated report with data."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import GeneratedReport

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        report = db.session.get(GeneratedReport, report_id)
        if not report:
            return jsonify({"error": "Report not found"}), 404

        return jsonify({
            "report": report.to_dict(),
            "data": report.data,
        })

    @app.route("/api/reports/generated/<int:report_id>/export", methods=["GET"])
    def export_report_route(report_id):
        """Export a generated report in specified format."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import GeneratedReport, export_report, ReportFormat

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        format_str = request.args.get("format", "json")
        try:
            format = ReportFormat(format_str)
        except ValueError:
            return jsonify({"error": "Invalid format"}), 400

        report = db.session.get(GeneratedReport, report_id)
        if not report:
            return jsonify({"error": "Report not found"}), 404

        content = export_report(report, format)

        if format == ReportFormat.JSON:
            return app.response_class(
                response=content,
                status=200,
                mimetype="application/json"
            )
        elif format == ReportFormat.CSV:
            return app.response_class(
                response=content,
                status=200,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"}
            )
        elif format == ReportFormat.HTML:
            return app.response_class(
                response=content,
                status=200,
                mimetype="text/html"
            )

    @app.route("/api/reports/run-scheduled", methods=["POST"])
    def run_scheduled_reports_route():
        """Manually run all due scheduled reports."""
        from flask_login import current_user
        from .database import UserRole
        from .reports import run_scheduled_reports

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        generated = run_scheduled_reports()
        return jsonify({
            "success": True,
            "reports_generated": len(generated),
            "reports": [r.to_dict() for r in generated],
        })

    @app.route("/api/reports/types")
    def get_report_types_route():
        """Get available report types."""
        from .reports import ReportType, ReportSchedule, ReportFormat

        return jsonify({
            "types": [t.value for t in ReportType],
            "schedules": [s.value for s in ReportSchedule],
            "formats": [f.value for f in ReportFormat],
        })

    # ========== Database Health & Info Routes ==========

    @app.route("/api/health")
    def health_check():
        """Health check endpoint."""
        from .db_config import check_database_health

        db_health = check_database_health()
        status_code = 200 if db_health["healthy"] else 503

        return jsonify({
            "status": "healthy" if db_health["healthy"] else "unhealthy",
            "database": db_health,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), status_code

    @app.route("/api/database/info")
    def database_info_route():
        """Get database configuration and status (admin only)."""
        from flask_login import current_user
        from .database import UserRole
        from .db_config import get_db_config, check_database_health, get_env_documentation

        if not current_user.is_authenticated or not current_user.has_role(UserRole.ADMIN):
            return jsonify({"error": "Admin access required"}), 403

        config = get_db_config()
        health = check_database_health()

        return jsonify({
            "type": config.db_type.value,
            "is_postgresql": config.is_postgresql(),
            "is_mongodb": config.is_mongodb(),
            "is_sqlite": config.is_sqlite(),
            "health": health,
            "pool_config": config.get_pool_config() if config.is_postgresql() else None,
            "env_documentation": get_env_documentation(),
        })

    @app.route("/api/database/types")
    def database_types_route():
        """Get available database types."""
        from .db_config import DatabaseType, get_db_config

        return jsonify({
            "types": [t.value for t in DatabaseType],
            "current": get_db_config().db_type.value,
        })

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

            # Registrar actividad de upload
            try:
                from flask_login import current_user
                if current_user.is_authenticated:
                    from .database import WorkspaceMember
                    membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
                    ws_id = membership.workspace_id if membership else None
                    if ws_id:
                        _log_activity(
                            current_user.id, ws_id, "spec_uploaded",
                            "spec", spec.title or file.filename,
                            f"{stats['total']} endpoints"
                        )
            except Exception:
                pass

            # Enterprise audit logging
            try:
                from .audit import log_audit, AuditAction
                log_audit(
                    action=AuditAction.SPEC_UPLOADED,
                    resource_type="spec",
                    resource_id=session_id,
                    resource_name=spec.title or file.filename,
                    details={
                        "filename": file.filename,
                        "endpoints_count": stats["total"],
                        "version": spec.version,
                    }
                )
            except Exception:
                pass

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
            framework_map = {"fastmcp": MCPFramework.FASTMCP, "mcp": MCPFramework.MCP, "typescript": MCPFramework.TYPESCRIPT}
            framework = framework_map.get(mcp_framework, MCPFramework.FASTMCP)
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
            gen_start_time = time.time()

            # Crear filtro
            endpoint_filter = EndpointFilter(selected_endpoints=selected_endpoints)

            # Configuración
            framework_map = {"fastmcp": MCPFramework.FASTMCP, "mcp": MCPFramework.MCP, "typescript": MCPFramework.TYPESCRIPT}
            framework = framework_map.get(mcp_framework, MCPFramework.FASTMCP)
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
            import time as _time
            gen_start = _time.time()
            generator = MCPServerGenerator(output_dir=output_dir)
            result = generator.generate(
                spec=spec,
                tools=tools,
                resources=resources,
                config=config,
            )
            generation_time = round((_time.time() - gen_start) * 1000)

            # Registrar actividad de generacion
            if result.success:
                try:
                    from flask_login import current_user
                    if current_user.is_authenticated:
                        from .database import WorkspaceMember
                        membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
                        ws_id = membership.workspace_id if membership else None
                        if ws_id:
                            _log_activity(
                                current_user.id, ws_id, "mcp_generated",
                                "server", service_name,
                                f"{len(result.tools_generated)} tools, {mcp_framework}, {generation_time}ms"
                            )
                except Exception:
                    pass

            # Enterprise audit logging
            try:
                from .audit import log_audit, AuditAction
                log_audit(
                    action=AuditAction.MCP_GENERATED if result.success else AuditAction.MCP_GENERATION_FAILED,
                    resource_type="mcp_server",
                    resource_name=service_name,
                    success=result.success,
                    details={
                        "framework": mcp_framework,
                        "tools_count": len(result.tools_generated) if result.success else 0,
                        "endpoints_count": len(selected_endpoints),
                        "generation_time_ms": generation_time,
                    },
                    error_message="; ".join(result.errors) if result.errors else None,
                )
            except Exception:
                pass

            generation_time = round((time.time() - gen_start_time) * 1000)

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
                    "generation_time": generation_time,
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
                    "generation_time": generation_time,
                })

        except Exception as e:
            logger.exception("Error generando servidor")
            # Registrar fallo
            try:
                from flask_login import current_user
                if current_user.is_authenticated:
                    from .database import WorkspaceMember
                    membership = WorkspaceMember.query.filter_by(user_id=current_user.id).first()
                    ws_id = membership.workspace_id if membership else None
                    if ws_id:
                        _log_activity(
                            current_user.id, ws_id, "mcp_failed",
                            "server", service_name, str(e)
                        )
            except Exception:
                pass
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
