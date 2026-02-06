"""
Data Retention Policies for Enterprise Compliance.

Provides configurable data retention with:
- Policy definitions for different data types
- Automatic cleanup based on retention periods
- Compliance reporting and audit trails
- Configurable per-workspace retention rules
"""

import enum
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .database import db

logger = logging.getLogger(__name__)


class DataType(enum.Enum):
    """Types of data subject to retention policies."""
    AUDIT_LOGS = "audit_logs"
    SPECS = "specs"
    GENERATIONS = "generations"
    SESSIONS = "sessions"
    ENCRYPTED_SPECS = "encrypted_specs"
    ACTIVITY_LOGS = "activity_logs"
    API_KEYS = "api_keys"
    WEBHOOKS = "webhooks"
    NOTIFICATIONS = "notifications"


class RetentionAction(enum.Enum):
    """Actions to take when data exceeds retention period."""
    DELETE = "delete"           # Permanently delete
    ARCHIVE = "archive"         # Move to archive storage
    ANONYMIZE = "anonymize"     # Remove PII but keep aggregate data


# Default retention periods (in days)
DEFAULT_RETENTION = {
    DataType.AUDIT_LOGS: 365,        # 1 year
    DataType.SPECS: 730,             # 2 years
    DataType.GENERATIONS: 180,       # 6 months
    DataType.SESSIONS: 1,            # 1 day
    DataType.ENCRYPTED_SPECS: 730,   # 2 years
    DataType.ACTIVITY_LOGS: 90,      # 3 months
    DataType.API_KEYS: 365,          # 1 year (inactive)
    DataType.WEBHOOKS: 365,          # 1 year (inactive)
    DataType.NOTIFICATIONS: 30,      # 1 month
}


class RetentionPolicy(db.Model):
    """Configurable retention policy."""
    __tablename__ = "retention_policies"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)
    data_type = db.Column(db.String(50), nullable=False)
    retention_days = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20), nullable=False, default=RetentionAction.DELETE.value)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Unique constraint per workspace and data type
    __table_args__ = (db.UniqueConstraint("workspace_id", "data_type"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "data_type": self.data_type,
            "retention_days": self.retention_days,
            "action": self.action,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RetentionExecution(db.Model):
    """Record of retention policy executions."""
    __tablename__ = "retention_executions"

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey("retention_policies.id"), nullable=True)
    data_type = db.Column(db.String(50), nullable=False)
    workspace_id = db.Column(db.Integer, nullable=True)
    executed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    records_processed = db.Column(db.Integer, default=0)
    records_deleted = db.Column(db.Integer, default=0)
    records_archived = db.Column(db.Integer, default=0)
    records_anonymized = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    duration_ms = db.Column(db.Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "data_type": self.data_type,
            "workspace_id": self.workspace_id,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "records_processed": self.records_processed,
            "records_deleted": self.records_deleted,
            "records_archived": self.records_archived,
            "records_anonymized": self.records_anonymized,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }


def get_retention_policy(
    data_type: DataType,
    workspace_id: int | None = None
) -> tuple[int, RetentionAction]:
    """
    Get retention policy for a data type.

    Args:
        data_type: Type of data
        workspace_id: Optional workspace ID for workspace-specific policies

    Returns:
        Tuple of (retention_days, action)
    """
    # Check for workspace-specific policy first
    if workspace_id:
        policy = RetentionPolicy.query.filter_by(
            workspace_id=workspace_id,
            data_type=data_type.value,
            is_active=True
        ).first()
        if policy:
            return policy.retention_days, RetentionAction(policy.action)

    # Check for global policy
    policy = RetentionPolicy.query.filter_by(
        workspace_id=None,
        data_type=data_type.value,
        is_active=True
    ).first()
    if policy:
        return policy.retention_days, RetentionAction(policy.action)

    # Return default
    return DEFAULT_RETENTION.get(data_type, 365), RetentionAction.DELETE


def set_retention_policy(
    data_type: DataType,
    retention_days: int,
    action: RetentionAction = RetentionAction.DELETE,
    workspace_id: int | None = None,
    user_id: int | None = None,
) -> RetentionPolicy:
    """
    Set or update a retention policy.

    Args:
        data_type: Type of data
        retention_days: Number of days to retain (0 = never delete)
        action: Action to take when retention period exceeded
        workspace_id: Optional workspace ID for workspace-specific policy
        user_id: User making the change

    Returns:
        Created or updated RetentionPolicy
    """
    existing = RetentionPolicy.query.filter_by(
        workspace_id=workspace_id,
        data_type=data_type.value
    ).first()

    if existing:
        existing.retention_days = retention_days
        existing.action = action.value
        existing.is_active = True
        db.session.commit()
        return existing

    policy = RetentionPolicy(
        workspace_id=workspace_id,
        data_type=data_type.value,
        retention_days=retention_days,
        action=action.value,
        created_by=user_id,
    )
    db.session.add(policy)
    db.session.commit()

    logger.info(f"Created retention policy: {data_type.value} = {retention_days} days")
    return policy


def list_retention_policies(workspace_id: int | None = None) -> list[dict]:
    """
    List all retention policies with defaults filled in.

    Args:
        workspace_id: Filter by workspace

    Returns:
        List of policy dicts for all data types
    """
    result = []

    for dt in DataType:
        policy = RetentionPolicy.query.filter_by(
            workspace_id=workspace_id,
            data_type=dt.value,
            is_active=True
        ).first()

        if policy:
            result.append(policy.to_dict())
        else:
            # Return default
            result.append({
                "id": None,
                "workspace_id": workspace_id,
                "data_type": dt.value,
                "retention_days": DEFAULT_RETENTION.get(dt, 365),
                "action": RetentionAction.DELETE.value,
                "is_active": True,
                "is_default": True,
            })

    return result


def apply_retention_policy(
    data_type: DataType,
    workspace_id: int | None = None,
    dry_run: bool = False
) -> dict:
    """
    Apply retention policy to a data type.

    Args:
        data_type: Type of data to clean up
        workspace_id: Optional workspace filter
        dry_run: If True, only count records without deleting

    Returns:
        Dict with execution results
    """
    import time
    start_time = time.time()

    retention_days, action = get_retention_policy(data_type, workspace_id)

    # Skip if retention is 0 (never delete)
    if retention_days == 0:
        return {
            "data_type": data_type.value,
            "skipped": True,
            "reason": "Retention policy set to never delete",
        }

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    records_processed = 0
    records_deleted = 0
    records_archived = 0
    records_anonymized = 0
    error_message = None

    try:
        if data_type == DataType.AUDIT_LOGS:
            records_processed, records_deleted = _cleanup_audit_logs(cutoff_date, workspace_id, dry_run)

        elif data_type == DataType.ACTIVITY_LOGS:
            records_processed, records_deleted = _cleanup_activity_logs(cutoff_date, workspace_id, dry_run)

        elif data_type == DataType.SESSIONS:
            records_processed, records_deleted = _cleanup_sessions(cutoff_date, dry_run)

        elif data_type == DataType.ENCRYPTED_SPECS:
            records_processed, records_deleted = _cleanup_encrypted_specs(cutoff_date, workspace_id, dry_run)

        elif data_type == DataType.API_KEYS:
            records_processed, records_deleted = _cleanup_api_keys(cutoff_date, dry_run)

    except Exception as e:
        error_message = str(e)
        logger.error(f"Retention policy execution failed for {data_type.value}: {e}")

    duration_ms = int((time.time() - start_time) * 1000)

    # Record execution (unless dry run)
    if not dry_run:
        policy = RetentionPolicy.query.filter_by(
            workspace_id=workspace_id,
            data_type=data_type.value,
            is_active=True
        ).first()

        execution = RetentionExecution(
            policy_id=policy.id if policy else None,
            data_type=data_type.value,
            workspace_id=workspace_id,
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=records_archived,
            records_anonymized=records_anonymized,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        db.session.add(execution)
        db.session.commit()

        # Log audit event
        try:
            from .audit import log_audit, AuditAction
            log_audit(
                action=AuditAction.DATA_RETENTION_APPLIED,
                resource_type=data_type.value,
                details={
                    "retention_days": retention_days,
                    "records_processed": records_processed,
                    "records_deleted": records_deleted,
                }
            )
        except Exception:
            pass

    return {
        "data_type": data_type.value,
        "workspace_id": workspace_id,
        "retention_days": retention_days,
        "cutoff_date": cutoff_date.isoformat(),
        "records_processed": records_processed,
        "records_deleted": records_deleted,
        "records_archived": records_archived,
        "records_anonymized": records_anonymized,
        "error_message": error_message,
        "duration_ms": duration_ms,
        "dry_run": dry_run,
    }


def apply_all_retention_policies(
    workspace_id: int | None = None,
    dry_run: bool = False
) -> list[dict]:
    """
    Apply all active retention policies.

    Args:
        workspace_id: Optional workspace filter
        dry_run: If True, only count without deleting

    Returns:
        List of execution results
    """
    results = []
    for dt in DataType:
        result = apply_retention_policy(dt, workspace_id, dry_run)
        results.append(result)
    return results


def get_retention_stats() -> dict:
    """Get statistics about data subject to retention."""
    from .audit import AuditLog
    from .database import ActivityLog, ApiKey
    from .encryption import EncryptedSpec

    now = datetime.now(timezone.utc)

    stats = {}
    for dt in DataType:
        retention_days, _ = get_retention_policy(dt)
        cutoff = now - timedelta(days=retention_days)

        if dt == DataType.AUDIT_LOGS:
            total = AuditLog.query.count()
            expired = AuditLog.query.filter(AuditLog.timestamp < cutoff).count()
        elif dt == DataType.ACTIVITY_LOGS:
            total = ActivityLog.query.count()
            expired = ActivityLog.query.filter(ActivityLog.created_at < cutoff).count()
        elif dt == DataType.ENCRYPTED_SPECS:
            total = EncryptedSpec.query.count()
            expired = EncryptedSpec.query.filter(EncryptedSpec.encrypted_at < cutoff).count()
        elif dt == DataType.API_KEYS:
            total = ApiKey.query.filter_by(is_active=False).count()
            expired = ApiKey.query.filter(
                ApiKey.is_active == False,
                ApiKey.created_at < cutoff
            ).count()
        else:
            total = 0
            expired = 0

        stats[dt.value] = {
            "total_records": total,
            "expired_records": expired,
            "retention_days": retention_days,
        }

    return stats


def get_execution_history(
    data_type: DataType | None = None,
    limit: int = 100
) -> list[RetentionExecution]:
    """
    Get retention execution history.

    Args:
        data_type: Filter by data type
        limit: Maximum records to return

    Returns:
        List of RetentionExecution records
    """
    query = RetentionExecution.query

    if data_type:
        query = query.filter_by(data_type=data_type.value)

    return query.order_by(RetentionExecution.executed_at.desc()).limit(limit).all()


# ========== Cleanup Functions ==========

def _cleanup_audit_logs(cutoff: datetime, workspace_id: int | None, dry_run: bool) -> tuple[int, int]:
    """Clean up old audit logs."""
    from .audit import AuditLog

    query = AuditLog.query.filter(AuditLog.timestamp < cutoff)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    count = query.count()
    if not dry_run and count > 0:
        query.delete()
        db.session.commit()
        logger.info(f"Deleted {count} old audit log entries")

    return count, count if not dry_run else 0


def _cleanup_activity_logs(cutoff: datetime, workspace_id: int | None, dry_run: bool) -> tuple[int, int]:
    """Clean up old activity logs."""
    from .database import ActivityLog

    query = ActivityLog.query.filter(ActivityLog.created_at < cutoff)
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    count = query.count()
    if not dry_run and count > 0:
        query.delete()
        db.session.commit()
        logger.info(f"Deleted {count} old activity log entries")

    return count, count if not dry_run else 0


def _cleanup_sessions(cutoff: datetime, dry_run: bool) -> tuple[int, int]:
    """Clean up old sessions from memory."""
    # This is handled by the existing session cleanup
    # Just return 0 for now
    return 0, 0


def _cleanup_encrypted_specs(cutoff: datetime, workspace_id: int | None, dry_run: bool) -> tuple[int, int]:
    """Clean up old encrypted specs that haven't been accessed."""
    from .encryption import EncryptedSpec

    # Only delete specs that haven't been accessed recently
    query = EncryptedSpec.query.filter(
        EncryptedSpec.last_accessed.is_(None) | (EncryptedSpec.last_accessed < cutoff),
        EncryptedSpec.encrypted_at < cutoff
    )
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)

    count = query.count()
    if not dry_run and count > 0:
        query.delete()
        db.session.commit()
        logger.info(f"Deleted {count} old encrypted specs")

    return count, count if not dry_run else 0


def _cleanup_api_keys(cutoff: datetime, dry_run: bool) -> tuple[int, int]:
    """Clean up old revoked API keys."""
    from .database import ApiKey

    # Only delete revoked/inactive keys
    query = ApiKey.query.filter(
        ApiKey.is_active == False,
        ApiKey.created_at < cutoff
    )

    count = query.count()
    if not dry_run and count > 0:
        query.delete()
        db.session.commit()
        logger.info(f"Deleted {count} old revoked API keys")

    return count, count if not dry_run else 0
