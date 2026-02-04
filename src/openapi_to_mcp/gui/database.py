"""
Modelos de base de datos y configuracion SQLAlchemy.

Gestiona usuarios, workspaces, actividad, webhooks, API keys
y canales de notificacion para la plataforma colaborativa.
"""

import enum
import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class UserRole(enum.Enum):
    """Roles de usuario en la plataforma."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class WebhookEvent(enum.Enum):
    """Eventos que pueden disparar webhooks."""
    SPEC_UPLOADED = "spec_uploaded"
    SPEC_UPDATED = "spec_updated"
    MCP_GENERATED = "mcp_generated"
    MCP_FAILED = "mcp_failed"


class User(UserMixin, db.Model):
    """Usuario de la plataforma."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.EDITOR)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # Relaciones
    workspace_memberships = db.relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    api_keys = db.relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    activities = db.relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")

    def has_role(self, role: UserRole) -> bool:
        """Verifica si el usuario tiene al menos el rol indicado."""
        hierarchy = {UserRole.VIEWER: 0, UserRole.EDITOR: 1, UserRole.ADMIN: 2}
        return hierarchy.get(self.role, 0) >= hierarchy.get(role, 0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class Workspace(db.Model):
    """Workspace compartido para organizar specs."""
    __tablename__ = "workspaces"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    members = db.relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    webhooks = db.relationship("Webhook", back_populates="workspace", cascade="all, delete-orphan")
    notification_channels = db.relationship("NotificationChannel", back_populates="workspace",
                                            cascade="all, delete-orphan")

    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "members_count": len(self.members),
        }


class WorkspaceMember(db.Model):
    """Relacion usuario-workspace con rol."""
    __tablename__ = "workspace_members"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.EDITOR)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    user = db.relationship("User", back_populates="workspace_memberships")
    workspace = db.relationship("Workspace", back_populates="members")

    __table_args__ = (db.UniqueConstraint("user_id", "workspace_id"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "workspace_id": self.workspace_id,
            "role": self.role.value,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class ActivityLog(db.Model):
    """Registro de actividad de los usuarios."""
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # upload, generate, config_change, etc.
    resource_type = db.Column(db.String(50), nullable=True)  # spec, generation, webhook, etc.
    resource_name = db.Column(db.String(200), nullable=True)
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relaciones
    user = db.relationship("User", back_populates="activities")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "workspace_id": self.workspace_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Webhook(db.Model):
    """Webhook para integracion CI/CD."""
    __tablename__ = "webhooks"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    secret = db.Column(db.String(255), nullable=True)
    events = db.Column(db.JSON, nullable=False, default=list)  # Lista de WebhookEvent values
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_triggered = db.Column(db.DateTime, nullable=True)
    failure_count = db.Column(db.Integer, default=0)

    # Relaciones
    workspace = db.relationship("Workspace", back_populates="webhooks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "url": self.url,
            "events": self.events,
            "is_active": self.is_active,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "failure_count": self.failure_count,
        }


class ApiKey(db.Model):
    """API key para acceso programatico."""
    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False, unique=True)
    prefix = db.Column(db.String(10), nullable=False)  # Primeros caracteres para identificacion
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relaciones
    user = db.relationship("User", back_populates="api_keys")

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Genera una API key y retorna (key_completa, hash, prefijo)."""
        key = f"omcp_{secrets.token_urlsafe(32)}"
        prefix = key[:12]
        return key, prefix

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class NotificationChannel(db.Model):
    """Canal de notificacion (Slack, Discord, Email)."""
    __tablename__ = "notification_channels"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False)
    channel_type = db.Column(db.String(20), nullable=False)  # slack, discord, email
    name = db.Column(db.String(100), nullable=False)
    config = db.Column(db.JSON, nullable=False, default=dict)  # webhook_url, smtp settings, etc.
    events = db.Column(db.JSON, nullable=False, default=list)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    workspace = db.relationship("Workspace", back_populates="notification_channels")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "channel_type": self.channel_type,
            "name": self.name,
            "events": self.events,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RepoSync(db.Model):
    """Vinculacion de spec con repositorio Git."""
    __tablename__ = "repo_syncs"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False)
    provider = db.Column(db.String(20), nullable=False)  # github, gitlab
    repo_url = db.Column(db.String(500), nullable=False)
    branch = db.Column(db.String(100), default="main")
    file_path = db.Column(db.String(500), nullable=False)  # Ruta al spec en el repo
    access_token = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    last_sha = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "provider": self.provider,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "file_path": self.file_path,
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_db(app):
    """Inicializa la base de datos y crea tablas."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
