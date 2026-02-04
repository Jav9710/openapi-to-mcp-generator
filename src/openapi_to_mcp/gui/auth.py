"""
Sistema de autenticacion y autorizacion.

Gestiona login, registro, sesiones y permisos basados en roles.
"""

import logging
from datetime import datetime, timezone
from functools import wraps

from flask import redirect, url_for, flash, request, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user

from .database import db, User, UserRole, Workspace, WorkspaceMember

logger = logging.getLogger(__name__)

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesion para acceder a esta pagina."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.request_loader
def load_user_from_request(req):
    """Carga usuario desde API key en header X-API-Key."""
    api_key = req.headers.get("X-API-Key")
    if not api_key:
        return None

    from .database import ApiKey
    key_hash = bcrypt.generate_password_hash(api_key).decode("utf-8")

    # Buscar por prefijo primero para eficiencia
    prefix = api_key[:12]
    api_key_record = ApiKey.query.filter_by(prefix=prefix, is_active=True).first()

    if api_key_record and bcrypt.check_password_hash(api_key_record.key_hash, api_key):
        api_key_record.last_used = datetime.now(timezone.utc)
        db.session.commit()
        return api_key_record.user

    return None


def init_auth(app):
    """Inicializa Flask-Login y bcrypt con la app."""
    bcrypt.init_app(app)
    login_manager.init_app(app)
    app.config["SECRET_KEY"] = app.config.get("SECRET_KEY", "change-me-in-production")


def create_default_admin(app):
    """Crea el usuario admin por defecto si no existe ninguno."""
    with app.app_context():
        if User.query.count() == 0:
            admin = User(
                username="admin",
                email="admin@localhost",
                password_hash=bcrypt.generate_password_hash("admin").decode("utf-8"),
                role=UserRole.ADMIN,
            )
            db.session.add(admin)

            # Crear workspace por defecto
            workspace = Workspace(name="Default", description="Workspace por defecto", created_by=1)
            db.session.add(workspace)
            db.session.flush()

            member = WorkspaceMember(user_id=admin.id, workspace_id=workspace.id, role=UserRole.ADMIN)
            db.session.add(member)

            db.session.commit()
            logger.info("Usuario admin creado (user: admin, pass: admin)")


def register_user(username: str, email: str, password: str, role: UserRole = UserRole.EDITOR) -> User:
    """Registra un nuevo usuario."""
    if User.query.filter_by(username=username).first():
        raise ValueError("El nombre de usuario ya existe")
    if User.query.filter_by(email=email).first():
        raise ValueError("El email ya esta registrado")

    user = User(
        username=username,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
    )
    db.session.add(user)

    # Agregar al workspace por defecto
    default_ws = Workspace.query.first()
    if default_ws:
        member = WorkspaceMember(user_id=user.id, workspace_id=default_ws.id, role=role)
        db.session.add(member)

    db.session.commit()
    return user


def authenticate_user(username: str, password: str) -> User | None:
    """Autentica un usuario por username/password."""
    user = User.query.filter_by(username=username, is_active=True).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        return user
    return None


# === Decoradores de permisos ===

def role_required(min_role: UserRole):
    """Decorador que requiere un rol minimo."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({"error": "Autenticacion requerida"}), 401
                return redirect(url_for("login"))

            if not current_user.has_role(min_role):
                if request.is_json:
                    return jsonify({"error": "Permisos insuficientes"}), 403
                flash("No tienes permisos para esta accion.", "error")
                return redirect(url_for("index"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorador que requiere rol admin."""
    return role_required(UserRole.ADMIN)(f)


def editor_required(f):
    """Decorador que requiere rol editor o superior."""
    return role_required(UserRole.EDITOR)(f)
