"""
Enterprise Audit Logging System.

Provides comprehensive audit logging for security and compliance:
- Tracks all user actions with detailed context
- Records IP addresses, user agents, and request metadata
- Supports filtering, searching, and exporting audit logs
- Integrates with data retention policies
"""

import enum
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from flask import current_app, g, request
from flask_login import current_user

from .database import db

logger = logging.getLogger(__name__)


class AuditAction(enum.Enum):
    """Audit action types for comprehensive tracking."""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"

    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"

    # API Keys
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_USED = "api_key_used"

    # Workspace Management
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_UPDATED = "workspace_updated"
    WORKSPACE_DELETED = "workspace_deleted"
    WORKSPACE_MEMBER_ADDED = "workspace_member_added"
    WORKSPACE_MEMBER_REMOVED = "workspace_member_removed"
    WORKSPACE_MEMBER_ROLE_CHANGED = "workspace_member_role_changed"

    # Spec Operations
    SPEC_UPLOADED = "spec_uploaded"
    SPEC_UPDATED = "spec_updated"
    SPEC_DELETED = "spec_deleted"
    SPEC_VIEWED = "spec_viewed"
    SPEC_DOWNLOADED = "spec_downloaded"
    SPEC_ENCRYPTED = "spec_encrypted"
    SPEC_DECRYPTED = "spec_decrypted"

    # MCP Generation
    MCP_GENERATED = "mcp_generated"
    MCP_GENERATION_FAILED = "mcp_generation_failed"
    MCP_DOWNLOADED = "mcp_downloaded"

    # Webhooks
    WEBHOOK_CREATED = "webhook_created"
    WEBHOOK_UPDATED = "webhook_updated"
    WEBHOOK_DELETED = "webhook_deleted"
    WEBHOOK_TRIGGERED = "webhook_triggered"

    # Notifications
    NOTIFICATION_CHANNEL_CREATED = "notification_channel_created"
    NOTIFICATION_CHANNEL_UPDATED = "notification_channel_updated"
    NOTIFICATION_CHANNEL_DELETED = "notification_channel_deleted"

    # Repository Sync
    REPO_SYNC_CREATED = "repo_sync_created"
    REPO_SYNC_UPDATED = "repo_sync_updated"
    REPO_SYNC_DELETED = "repo_sync_deleted"
    REPO_SYNC_TRIGGERED = "repo_sync_triggered"

    # Admin Actions
    SETTINGS_CHANGED = "settings_changed"
    DATA_EXPORTED = "data_exported"
    AUDIT_LOG_EXPORTED = "audit_log_exported"
    DATA_RETENTION_APPLIED = "data_retention_applied"


class AuditSeverity(enum.Enum):
    """Severity levels for audit events."""
    LOW = "low"           # Routine operations
    MEDIUM = "medium"     # Notable actions
    HIGH = "high"         # Sensitive operations
    CRITICAL = "critical" # Security-related actions


class AuditLog(db.Model):
    """Comprehensive audit log for enterprise security."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # User info (nullable for system actions)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=True)  # Denormalized for historical accuracy

    # Action details
    action = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default=AuditSeverity.LOW.value)

    # Resource info
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(100), nullable=True)
    resource_name = db.Column(db.String(200), nullable=True)

    # Workspace context
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True, index=True)

    # Request metadata
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.String(500), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_path = db.Column(db.String(500), nullable=True)

    # Additional context
    details = db.Column(db.JSON, nullable=True)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)

    # Retention
    expires_at = db.Column(db.DateTime, nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "severity": self.severity,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "workspace_id": self.workspace_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
        }


# Severity mapping for actions
ACTION_SEVERITY = {
    # Critical - security related
    AuditAction.LOGIN_FAILED: AuditSeverity.HIGH,
    AuditAction.PASSWORD_CHANGED: AuditSeverity.HIGH,
    AuditAction.PASSWORD_RESET_REQUESTED: AuditSeverity.HIGH,
    AuditAction.USER_ROLE_CHANGED: AuditSeverity.HIGH,
    AuditAction.USER_DELETED: AuditSeverity.CRITICAL,
    AuditAction.API_KEY_CREATED: AuditSeverity.HIGH,
    AuditAction.API_KEY_REVOKED: AuditSeverity.HIGH,
    AuditAction.WORKSPACE_DELETED: AuditSeverity.HIGH,
    AuditAction.SPEC_DELETED: AuditSeverity.HIGH,
    AuditAction.SPEC_ENCRYPTED: AuditSeverity.HIGH,
    AuditAction.SPEC_DECRYPTED: AuditSeverity.HIGH,
    AuditAction.SETTINGS_CHANGED: AuditSeverity.HIGH,
    AuditAction.DATA_RETENTION_APPLIED: AuditSeverity.CRITICAL,

    # Medium - notable actions
    AuditAction.LOGIN_SUCCESS: AuditSeverity.MEDIUM,
    AuditAction.USER_CREATED: AuditSeverity.MEDIUM,
    AuditAction.USER_UPDATED: AuditSeverity.MEDIUM,
    AuditAction.WORKSPACE_CREATED: AuditSeverity.MEDIUM,
    AuditAction.WORKSPACE_MEMBER_ADDED: AuditSeverity.MEDIUM,
    AuditAction.WORKSPACE_MEMBER_REMOVED: AuditSeverity.MEDIUM,
    AuditAction.SPEC_UPLOADED: AuditSeverity.MEDIUM,
    AuditAction.MCP_GENERATED: AuditSeverity.MEDIUM,
    AuditAction.MCP_GENERATION_FAILED: AuditSeverity.MEDIUM,
    AuditAction.WEBHOOK_CREATED: AuditSeverity.MEDIUM,
    AuditAction.DATA_EXPORTED: AuditSeverity.MEDIUM,
    AuditAction.AUDIT_LOG_EXPORTED: AuditSeverity.MEDIUM,

    # Low - routine
    AuditAction.LOGOUT: AuditSeverity.LOW,
    AuditAction.SPEC_VIEWED: AuditSeverity.LOW,
    AuditAction.API_KEY_USED: AuditSeverity.LOW,
}


def get_request_metadata() -> dict:
    """Extract metadata from current request."""
    try:
        return {
            "ip_address": request.remote_addr or request.headers.get("X-Forwarded-For", "").split(",")[0].strip(),
            "user_agent": request.headers.get("User-Agent", "")[:500],
            "request_method": request.method,
            "request_path": request.path[:500],
        }
    except RuntimeError:
        # Not in request context
        return {}


def log_audit(
    action: AuditAction,
    resource_type: str | None = None,
    resource_id: str | None = None,
    resource_name: str | None = None,
    workspace_id: int | None = None,
    details: dict | None = None,
    success: bool = True,
    error_message: str | None = None,
    user_id: int | None = None,
    username: str | None = None,
) -> AuditLog | None:
    """
    Log an audit event.

    Args:
        action: The action being performed
        resource_type: Type of resource (spec, user, workspace, etc.)
        resource_id: ID of the resource
        resource_name: Human-readable name of the resource
        workspace_id: Associated workspace ID
        details: Additional context as dict
        success: Whether the action succeeded
        error_message: Error message if failed
        user_id: Override user ID (for system actions)
        username: Override username

    Returns:
        Created AuditLog entry or None if failed
    """
    try:
        # Get user info
        if user_id is None and current_user and current_user.is_authenticated:
            user_id = current_user.id
            username = current_user.username

        # Get request metadata
        metadata = get_request_metadata()

        # Determine severity
        severity = ACTION_SEVERITY.get(action, AuditSeverity.LOW)

        # Calculate expiration based on retention policy
        retention_days = current_app.config.get("AUDIT_LOG_RETENTION_DAYS", 365)
        expires_at = None
        if retention_days > 0:
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

        # Create audit entry
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action.value,
            severity=severity.value,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            workspace_id=workspace_id,
            ip_address=metadata.get("ip_address"),
            user_agent=metadata.get("user_agent"),
            request_method=metadata.get("request_method"),
            request_path=metadata.get("request_path"),
            details=details,
            success=success,
            error_message=error_message,
            expires_at=expires_at,
        )

        db.session.add(audit_entry)
        db.session.commit()

        logger.debug(f"Audit logged: {action.value} by {username} on {resource_type}:{resource_id}")
        return audit_entry

    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        db.session.rollback()
        return None


def audit_action(action: AuditAction, resource_type: str | None = None):
    """
    Decorator to automatically log audit events for a function.

    Usage:
        @audit_action(AuditAction.SPEC_UPLOADED, "spec")
        def upload_spec():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                log_audit(action=action, resource_type=resource_type, success=True)
                return result
            except Exception as e:
                log_audit(
                    action=action,
                    resource_type=resource_type,
                    success=False,
                    error_message=str(e)
                )
                raise
        return wrapper
    return decorator


def query_audit_logs(
    user_id: int | None = None,
    workspace_id: int | None = None,
    action: AuditAction | None = None,
    severity: AuditSeverity | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    success: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """
    Query audit logs with filtering.

    Returns:
        Tuple of (list of AuditLog entries, total count)
    """
    query = AuditLog.query

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    if workspace_id is not None:
        query = query.filter(AuditLog.workspace_id == workspace_id)

    if action is not None:
        query = query.filter(AuditLog.action == action.value)

    if severity is not None:
        query = query.filter(AuditLog.severity == severity.value)

    if resource_type is not None:
        query = query.filter(AuditLog.resource_type == resource_type)

    if start_date is not None:
        query = query.filter(AuditLog.timestamp >= start_date)

    if end_date is not None:
        query = query.filter(AuditLog.timestamp <= end_date)

    if success is not None:
        query = query.filter(AuditLog.success == success)

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return logs, total


def export_audit_logs(
    format: str = "json",
    **filters
) -> str | bytes:
    """
    Export audit logs in specified format.

    Args:
        format: Export format (json, csv)
        **filters: Filters to apply (same as query_audit_logs)

    Returns:
        Exported data as string or bytes
    """
    logs, _ = query_audit_logs(limit=10000, **filters)

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "timestamp", "username", "action", "severity", "resource_type",
            "resource_id", "resource_name", "ip_address", "success", "error_message"
        ])
        writer.writeheader()

        for log in logs:
            writer.writerow({
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                "username": log.username or "",
                "action": log.action,
                "severity": log.severity,
                "resource_type": log.resource_type or "",
                "resource_id": log.resource_id or "",
                "resource_name": log.resource_name or "",
                "ip_address": log.ip_address or "",
                "success": "Yes" if log.success else "No",
                "error_message": log.error_message or "",
            })

        return output.getvalue()

    else:  # json
        import json
        return json.dumps([log.to_dict() for log in logs], indent=2)


def cleanup_expired_audit_logs() -> int:
    """
    Remove audit logs that have passed their retention period.

    Returns:
        Number of deleted records
    """
    now = datetime.now(timezone.utc)
    count = AuditLog.query.filter(
        AuditLog.expires_at.isnot(None),
        AuditLog.expires_at < now
    ).delete()
    db.session.commit()

    if count > 0:
        logger.info(f"Cleaned up {count} expired audit log entries")

    return count


def get_audit_summary(days: int = 30) -> dict:
    """
    Get audit summary statistics.

    Args:
        days: Number of days to include in summary

    Returns:
        Summary statistics dict
    """
    from datetime import timedelta
    from sqlalchemy import func

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total events
    total = AuditLog.query.filter(AuditLog.timestamp >= cutoff).count()

    # Events by severity
    severity_counts = db.session.query(
        AuditLog.severity, func.count(AuditLog.id)
    ).filter(
        AuditLog.timestamp >= cutoff
    ).group_by(AuditLog.severity).all()

    # Events by action (top 10)
    action_counts = db.session.query(
        AuditLog.action, func.count(AuditLog.id)
    ).filter(
        AuditLog.timestamp >= cutoff
    ).group_by(AuditLog.action).order_by(
        func.count(AuditLog.id).desc()
    ).limit(10).all()

    # Failed actions
    failed = AuditLog.query.filter(
        AuditLog.timestamp >= cutoff,
        AuditLog.success == False
    ).count()

    # Most active users
    user_counts = db.session.query(
        AuditLog.username, func.count(AuditLog.id)
    ).filter(
        AuditLog.timestamp >= cutoff,
        AuditLog.username.isnot(None)
    ).group_by(AuditLog.username).order_by(
        func.count(AuditLog.id).desc()
    ).limit(5).all()

    return {
        "period_days": days,
        "total_events": total,
        "failed_events": failed,
        "success_rate": round((total - failed) / total * 100, 2) if total > 0 else 100,
        "by_severity": {s: c for s, c in severity_counts},
        "top_actions": {a: c for a, c in action_counts},
        "most_active_users": {u: c for u, c in user_counts},
    }
