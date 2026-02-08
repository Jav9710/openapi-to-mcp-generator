"""
Configurable Alerts System for Enterprise Monitoring.

Provides alerting capabilities with:
- Configurable alert rules
- Multiple notification channels
- Threshold-based triggers
- Alert history and acknowledgment
"""

import enum
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .database import db

logger = logging.getLogger(__name__)


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(enum.Enum):
    """Types of alerts that can be configured."""
    FAILED_LOGINS = "failed_logins"           # Too many failed login attempts
    HIGH_ERROR_RATE = "high_error_rate"       # High rate of errors
    UNUSUAL_ACTIVITY = "unusual_activity"     # Unusual activity patterns
    API_RATE_LIMIT = "api_rate_limit"         # API rate limit approaching
    STORAGE_USAGE = "storage_usage"           # Storage usage threshold
    INACTIVE_USERS = "inactive_users"         # Users inactive for period
    WEBHOOK_FAILURES = "webhook_failures"     # Webhook delivery failures
    ENCRYPTION_EVENTS = "encryption_events"   # Encryption/decryption events
    ADMIN_ACTIONS = "admin_actions"           # Admin actions taken
    NEW_USER_SPIKE = "new_user_spike"         # Unusual number of new users


class AlertStatus(enum.Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"


class AlertRule(db.Model):
    """Configurable alert rule."""
    __tablename__ = "alert_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default=AlertSeverity.WARNING.value)

    # Threshold configuration
    threshold_value = db.Column(db.Integer, nullable=False)
    threshold_period_minutes = db.Column(db.Integer, default=60)  # Time window for threshold

    # Notification settings
    notification_channels = db.Column(db.JSON, default=list)  # List of channel IDs
    cooldown_minutes = db.Column(db.Integer, default=30)  # Minimum time between alerts

    # Scope
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_triggered = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "threshold_value": self.threshold_value,
            "threshold_period_minutes": self.threshold_period_minutes,
            "notification_channels": self.notification_channels,
            "cooldown_minutes": self.cooldown_minutes,
            "workspace_id": self.workspace_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
        }


class Alert(db.Model):
    """Generated alert instance."""
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("alert_rules.id"), nullable=True)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON, nullable=True)

    status = db.Column(db.String(20), nullable=False, default=AlertStatus.ACTIVE.value)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    snoozed_until = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "status": self.status,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
        }


# ========== Alert Rule Management ==========

def create_alert_rule(
    name: str,
    alert_type: AlertType,
    threshold_value: int,
    severity: AlertSeverity = AlertSeverity.WARNING,
    threshold_period_minutes: int = 60,
    notification_channels: list[int] | None = None,
    cooldown_minutes: int = 30,
    workspace_id: int | None = None,
    user_id: int | None = None,
    description: str | None = None,
) -> AlertRule:
    """Create a new alert rule."""
    rule = AlertRule(
        name=name,
        description=description,
        alert_type=alert_type.value,
        severity=severity.value,
        threshold_value=threshold_value,
        threshold_period_minutes=threshold_period_minutes,
        notification_channels=notification_channels or [],
        cooldown_minutes=cooldown_minutes,
        workspace_id=workspace_id,
        created_by=user_id,
    )
    db.session.add(rule)
    db.session.commit()

    logger.info(f"Created alert rule: {name} ({alert_type.value})")
    return rule


def update_alert_rule(rule_id: int, **kwargs) -> AlertRule | None:
    """Update an existing alert rule."""
    rule = db.session.get(AlertRule, rule_id)
    if not rule:
        return None

    for key, value in kwargs.items():
        if hasattr(rule, key) and key not in ("id", "created_at", "created_by"):
            if key == "alert_type" and isinstance(value, AlertType):
                value = value.value
            elif key == "severity" and isinstance(value, AlertSeverity):
                value = value.value
            setattr(rule, key, value)

    db.session.commit()
    return rule


def delete_alert_rule(rule_id: int) -> bool:
    """Delete an alert rule."""
    rule = db.session.get(AlertRule, rule_id)
    if not rule:
        return False

    db.session.delete(rule)
    db.session.commit()
    logger.info(f"Deleted alert rule: {rule.name}")
    return True


def list_alert_rules(
    workspace_id: int | None = None,
    is_active: bool | None = None,
) -> list[AlertRule]:
    """List alert rules."""
    query = AlertRule.query

    if workspace_id is not None:
        query = query.filter(
            (AlertRule.workspace_id == workspace_id) | (AlertRule.workspace_id.is_(None))
        )

    if is_active is not None:
        query = query.filter_by(is_active=is_active)

    return query.order_by(AlertRule.created_at.desc()).all()


# ========== Alert Generation ==========

def create_alert(
    alert_type: AlertType,
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.WARNING,
    details: dict | None = None,
    rule_id: int | None = None,
    workspace_id: int | None = None,
) -> Alert:
    """Create a new alert."""
    alert = Alert(
        rule_id=rule_id,
        alert_type=alert_type.value,
        severity=severity.value,
        title=title,
        message=message,
        details=details,
        workspace_id=workspace_id,
    )
    db.session.add(alert)
    db.session.commit()

    logger.warning(f"Alert created: [{severity.value}] {title}")

    # Send notifications
    if rule_id:
        rule = db.session.get(AlertRule, rule_id)
        if rule and rule.notification_channels:
            _send_alert_notifications(alert, rule.notification_channels)

    return alert


def acknowledge_alert(alert_id: int, user_id: int) -> Alert | None:
    """Acknowledge an alert."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return None

    alert.status = AlertStatus.ACKNOWLEDGED.value
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user_id
    db.session.commit()

    return alert


def resolve_alert(alert_id: int, user_id: int) -> Alert | None:
    """Resolve an alert."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return None

    alert.status = AlertStatus.RESOLVED.value
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = user_id
    db.session.commit()

    return alert


def snooze_alert(alert_id: int, minutes: int) -> Alert | None:
    """Snooze an alert for specified minutes."""
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return None

    alert.status = AlertStatus.SNOOZED.value
    alert.snoozed_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    db.session.commit()

    return alert


def list_alerts(
    workspace_id: int | None = None,
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    alert_type: AlertType | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Alert], int]:
    """List alerts with filtering."""
    query = Alert.query

    if workspace_id is not None:
        query = query.filter(
            (Alert.workspace_id == workspace_id) | (Alert.workspace_id.is_(None))
        )

    if status is not None:
        query = query.filter_by(status=status.value)

    if severity is not None:
        query = query.filter_by(severity=severity.value)

    if alert_type is not None:
        query = query.filter_by(alert_type=alert_type.value)

    total = query.count()
    alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()

    return alerts, total


def get_active_alert_count() -> dict:
    """Get count of active alerts by severity."""
    from sqlalchemy import func

    counts = db.session.query(
        Alert.severity, func.count(Alert.id)
    ).filter(
        Alert.status == AlertStatus.ACTIVE.value
    ).group_by(Alert.severity).all()

    return {sev: count for sev, count in counts}


# ========== Alert Checking ==========

def check_alert_rules() -> list[Alert]:
    """
    Check all active alert rules and generate alerts if thresholds exceeded.

    Returns:
        List of newly created alerts
    """
    now = datetime.now(timezone.utc)
    new_alerts = []

    rules = AlertRule.query.filter_by(is_active=True).all()

    for rule in rules:
        # Check cooldown
        if rule.last_triggered:
            cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
            if now < cooldown_end:
                continue

        # Check threshold
        alert_type = AlertType(rule.alert_type)
        threshold_exceeded, current_value, details = _check_threshold(
            alert_type,
            rule.threshold_value,
            rule.threshold_period_minutes,
            rule.workspace_id
        )

        if threshold_exceeded:
            alert = create_alert(
                alert_type=alert_type,
                title=f"{rule.name}: Threshold Exceeded",
                message=f"Current value ({current_value}) exceeds threshold ({rule.threshold_value})",
                severity=AlertSeverity(rule.severity),
                details=details,
                rule_id=rule.id,
                workspace_id=rule.workspace_id,
            )
            new_alerts.append(alert)

            # Update last triggered
            rule.last_triggered = now
            db.session.commit()

    return new_alerts


def _check_threshold(
    alert_type: AlertType,
    threshold: int,
    period_minutes: int,
    workspace_id: int | None,
) -> tuple[bool, int, dict]:
    """
    Check if an alert threshold is exceeded.

    Returns:
        Tuple of (exceeded, current_value, details)
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=period_minutes)
    details = {}

    if alert_type == AlertType.FAILED_LOGINS:
        try:
            from .audit import AuditLog
            count = AuditLog.query.filter(
                AuditLog.action == "login_failed",
                AuditLog.timestamp >= start_time
            ).count()
            details = {"period_minutes": period_minutes}
            return count >= threshold, count, details
        except Exception:
            return False, 0, {}

    elif alert_type == AlertType.HIGH_ERROR_RATE:
        try:
            from .audit import AuditLog
            count = AuditLog.query.filter(
                AuditLog.success == False,
                AuditLog.timestamp >= start_time
            ).count()
            details = {"period_minutes": period_minutes}
            return count >= threshold, count, details
        except Exception:
            return False, 0, {}

    elif alert_type == AlertType.NEW_USER_SPIKE:
        from .database import User
        count = User.query.filter(User.created_at >= start_time).count()
        details = {"period_minutes": period_minutes}
        return count >= threshold, count, details

    elif alert_type == AlertType.WEBHOOK_FAILURES:
        from .database import Webhook
        count = Webhook.query.filter(
            Webhook.failure_count >= threshold
        ).count()
        details = {"webhooks_failing": count}
        return count > 0, count, details

    elif alert_type == AlertType.INACTIVE_USERS:
        from .database import User
        inactive_since = now - timedelta(days=threshold)  # threshold = days inactive
        count = User.query.filter(
            User.is_active == True,
            (User.last_login.is_(None)) | (User.last_login < inactive_since)
        ).count()
        details = {"inactive_days": threshold}
        return count > 0, count, details

    return False, 0, {}


def _send_alert_notifications(alert: Alert, channel_ids: list[int]):
    """Send alert to notification channels."""
    try:
        from .notifications import send_notification
        from .database import NotificationChannel

        for channel_id in channel_ids:
            channel = db.session.get(NotificationChannel, channel_id)
            if channel and channel.is_active:
                send_notification(
                    channel=channel,
                    title=f"[{alert.severity.upper()}] {alert.title}",
                    message=alert.message,
                    event_type="alert",
                )
    except Exception as e:
        logger.error(f"Failed to send alert notifications: {e}")


# ========== Default Alert Rules ==========

def create_default_alert_rules():
    """Create default alert rules if none exist."""
    if AlertRule.query.count() > 0:
        return

    defaults = [
        {
            "name": "Failed Login Attempts",
            "alert_type": AlertType.FAILED_LOGINS,
            "threshold_value": 5,
            "threshold_period_minutes": 15,
            "severity": AlertSeverity.WARNING,
            "description": "Alert when too many failed login attempts occur",
        },
        {
            "name": "High Error Rate",
            "alert_type": AlertType.HIGH_ERROR_RATE,
            "threshold_value": 10,
            "threshold_period_minutes": 60,
            "severity": AlertSeverity.ERROR,
            "description": "Alert when error rate is unusually high",
        },
        {
            "name": "New User Spike",
            "alert_type": AlertType.NEW_USER_SPIKE,
            "threshold_value": 10,
            "threshold_period_minutes": 60,
            "severity": AlertSeverity.INFO,
            "description": "Alert when many new users register in short time",
        },
    ]

    for rule_data in defaults:
        create_alert_rule(**rule_data)

    logger.info("Created default alert rules")
