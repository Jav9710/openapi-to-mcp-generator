"""
Enterprise Metrics and Analytics Module.

Provides comprehensive usage metrics and analytics:
- User activity metrics
- Spec and generation statistics
- Workspace analytics
- Time-series data for dashboards
- Performance monitoring
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, distinct

from .database import (
    db,
    User,
    Workspace,
    WorkspaceMember,
    ActivityLog,
    ApiKey,
    Webhook,
    NotificationChannel,
)

logger = logging.getLogger(__name__)


def get_overview_metrics() -> dict:
    """
    Get high-level platform metrics for admin dashboard.

    Returns:
        Dict with platform overview metrics
    """
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # User metrics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    users_last_week = User.query.filter(User.created_at >= week_ago).count()
    users_last_month = User.query.filter(User.created_at >= month_ago).count()

    # Workspace metrics
    total_workspaces = Workspace.query.count()
    workspaces_last_week = Workspace.query.filter(Workspace.created_at >= week_ago).count()

    # Activity metrics (from ActivityLog)
    total_activities = ActivityLog.query.count()
    activities_today = ActivityLog.query.filter(ActivityLog.created_at >= today).count()
    activities_week = ActivityLog.query.filter(ActivityLog.created_at >= week_ago).count()

    # Count by activity type
    uploads_week = ActivityLog.query.filter(
        ActivityLog.created_at >= week_ago,
        ActivityLog.action == "spec_uploaded"
    ).count()

    generations_week = ActivityLog.query.filter(
        ActivityLog.created_at >= week_ago,
        ActivityLog.action == "mcp_generated"
    ).count()

    # API keys and webhooks
    active_api_keys = ApiKey.query.filter_by(is_active=True).count()
    active_webhooks = Webhook.query.filter_by(is_active=True).count()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "new_last_week": users_last_week,
            "new_last_month": users_last_month,
        },
        "workspaces": {
            "total": total_workspaces,
            "new_last_week": workspaces_last_week,
        },
        "activity": {
            "total": total_activities,
            "today": activities_today,
            "last_week": activities_week,
            "uploads_week": uploads_week,
            "generations_week": generations_week,
        },
        "integrations": {
            "active_api_keys": active_api_keys,
            "active_webhooks": active_webhooks,
        },
        "timestamp": now.isoformat(),
    }


def get_user_metrics(days: int = 30) -> dict:
    """
    Get detailed user metrics.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with user metrics
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Users by role
    from .database import UserRole
    role_counts = db.session.query(
        User.role, func.count(User.id)
    ).group_by(User.role).all()

    # New users over time (daily)
    new_users_daily = db.session.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("count")
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).all()

    # Active users (logged in last 7 days)
    week_ago = now - timedelta(days=7)
    recently_active = User.query.filter(
        User.last_login >= week_ago,
        User.is_active == True
    ).count()

    # Users with most activities
    top_users = db.session.query(
        User.username,
        func.count(ActivityLog.id).label("activity_count")
    ).join(ActivityLog).filter(
        ActivityLog.created_at >= start_date
    ).group_by(User.id).order_by(
        func.count(ActivityLog.id).desc()
    ).limit(10).all()

    return {
        "period_days": days,
        "by_role": {role.value if hasattr(role, 'value') else str(role): count for role, count in role_counts},
        "new_users_daily": [{"date": str(date), "count": count} for date, count in new_users_daily],
        "recently_active": recently_active,
        "top_users": [{"username": u, "activity_count": c} for u, c in top_users],
    }


def get_activity_metrics(days: int = 30) -> dict:
    """
    Get detailed activity metrics.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with activity metrics
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Activities by type
    action_counts = db.session.query(
        ActivityLog.action, func.count(ActivityLog.id)
    ).filter(
        ActivityLog.created_at >= start_date
    ).group_by(ActivityLog.action).all()

    # Daily activity trend
    daily_activity = db.session.query(
        func.date(ActivityLog.created_at).label("date"),
        func.count(ActivityLog.id).label("count")
    ).filter(
        ActivityLog.created_at >= start_date
    ).group_by(
        func.date(ActivityLog.created_at)
    ).all()

    # Hourly distribution (for all time)
    hourly_distribution = db.session.query(
        func.strftime("%H", ActivityLog.created_at).label("hour"),
        func.count(ActivityLog.id).label("count")
    ).filter(
        ActivityLog.created_at >= start_date
    ).group_by(
        func.strftime("%H", ActivityLog.created_at)
    ).all()

    # Most active workspaces
    workspace_activity = db.session.query(
        Workspace.name,
        func.count(ActivityLog.id).label("activity_count")
    ).join(ActivityLog, ActivityLog.workspace_id == Workspace.id).filter(
        ActivityLog.created_at >= start_date
    ).group_by(Workspace.id).order_by(
        func.count(ActivityLog.id).desc()
    ).limit(10).all()

    return {
        "period_days": days,
        "by_action": {action: count for action, count in action_counts},
        "daily_trend": [{"date": str(date), "count": count} for date, count in daily_activity],
        "hourly_distribution": {hour: count for hour, count in hourly_distribution},
        "top_workspaces": [{"name": name, "activity_count": count} for name, count in workspace_activity],
    }


def get_workspace_metrics() -> dict:
    """
    Get workspace analytics.

    Returns:
        Dict with workspace metrics
    """
    # Workspaces by member count
    workspace_sizes = db.session.query(
        Workspace.id,
        Workspace.name,
        func.count(WorkspaceMember.id).label("member_count")
    ).outerjoin(WorkspaceMember).group_by(Workspace.id).all()

    # Size distribution
    size_distribution = {"1": 0, "2-5": 0, "6-10": 0, "10+": 0}
    for ws_id, name, count in workspace_sizes:
        if count == 1:
            size_distribution["1"] += 1
        elif count <= 5:
            size_distribution["2-5"] += 1
        elif count <= 10:
            size_distribution["6-10"] += 1
        else:
            size_distribution["10+"] += 1

    # Workspaces with most webhooks
    webhook_counts = db.session.query(
        Workspace.name,
        func.count(Webhook.id).label("webhook_count")
    ).join(Webhook).filter(
        Webhook.is_active == True
    ).group_by(Workspace.id).order_by(
        func.count(Webhook.id).desc()
    ).limit(5).all()

    # Workspaces with most notification channels
    notification_counts = db.session.query(
        Workspace.name,
        func.count(NotificationChannel.id).label("channel_count")
    ).join(NotificationChannel).filter(
        NotificationChannel.is_active == True
    ).group_by(Workspace.id).order_by(
        func.count(NotificationChannel.id).desc()
    ).limit(5).all()

    return {
        "total_workspaces": len(workspace_sizes),
        "size_distribution": size_distribution,
        "largest_workspaces": [
            {"name": name, "member_count": count}
            for ws_id, name, count in sorted(workspace_sizes, key=lambda x: x[2], reverse=True)[:10]
        ],
        "most_webhooks": [{"name": name, "count": count} for name, count in webhook_counts],
        "most_notifications": [{"name": name, "count": count} for name, count in notification_counts],
    }


def get_generation_metrics(days: int = 30) -> dict:
    """
    Get MCP generation metrics from activity logs.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with generation metrics
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Total generations
    total_generations = ActivityLog.query.filter(
        ActivityLog.action == "mcp_generated"
    ).count()

    generations_period = ActivityLog.query.filter(
        ActivityLog.action == "mcp_generated",
        ActivityLog.created_at >= start_date
    ).count()

    # Daily generations
    daily_generations = db.session.query(
        func.date(ActivityLog.created_at).label("date"),
        func.count(ActivityLog.id).label("count")
    ).filter(
        ActivityLog.action == "mcp_generated",
        ActivityLog.created_at >= start_date
    ).group_by(
        func.date(ActivityLog.created_at)
    ).all()

    # Framework distribution (parse from details if available)
    # This is a simplified version - in practice would need to parse the details JSON
    framework_counts = {"fastmcp": 0, "mcp": 0, "typescript": 0}

    return {
        "period_days": days,
        "total_all_time": total_generations,
        "total_period": generations_period,
        "daily_trend": [{"date": str(date), "count": count} for date, count in daily_generations],
        "by_framework": framework_counts,
        "avg_per_day": round(generations_period / days, 2) if days > 0 else 0,
    }


def get_api_usage_metrics(days: int = 30) -> dict:
    """
    Get API usage metrics.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with API metrics
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # API keys stats
    total_keys = ApiKey.query.count()
    active_keys = ApiKey.query.filter_by(is_active=True).count()

    # Recently used keys
    week_ago = now - timedelta(days=7)
    recently_used = ApiKey.query.filter(
        ApiKey.last_used >= week_ago,
        ApiKey.is_active == True
    ).count()

    # Keys by user
    keys_per_user = db.session.query(
        User.username,
        func.count(ApiKey.id).label("key_count")
    ).join(ApiKey).filter(
        ApiKey.is_active == True
    ).group_by(User.id).order_by(
        func.count(ApiKey.id).desc()
    ).limit(10).all()

    return {
        "period_days": days,
        "total_keys": total_keys,
        "active_keys": active_keys,
        "recently_used": recently_used,
        "keys_per_user": [{"username": u, "count": c} for u, c in keys_per_user],
    }


def get_security_metrics(days: int = 30) -> dict:
    """
    Get security-related metrics from audit logs.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with security metrics
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    try:
        from .audit import AuditLog, AuditSeverity

        # Failed logins
        failed_logins = AuditLog.query.filter(
            AuditLog.action == "login_failed",
            AuditLog.timestamp >= start_date
        ).count()

        # Successful logins
        successful_logins = AuditLog.query.filter(
            AuditLog.action == "login_success",
            AuditLog.timestamp >= start_date
        ).count()

        # High severity events
        high_severity = AuditLog.query.filter(
            AuditLog.severity.in_([AuditSeverity.HIGH.value, AuditSeverity.CRITICAL.value]),
            AuditLog.timestamp >= start_date
        ).count()

        # Password changes
        password_changes = AuditLog.query.filter(
            AuditLog.action == "password_changed",
            AuditLog.timestamp >= start_date
        ).count()

        # Daily failed logins trend
        daily_failed = db.session.query(
            func.date(AuditLog.timestamp).label("date"),
            func.count(AuditLog.id).label("count")
        ).filter(
            AuditLog.action == "login_failed",
            AuditLog.timestamp >= start_date
        ).group_by(
            func.date(AuditLog.timestamp)
        ).all()

        # IPs with most failed logins
        suspicious_ips = db.session.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label("fail_count")
        ).filter(
            AuditLog.action == "login_failed",
            AuditLog.timestamp >= start_date,
            AuditLog.ip_address.isnot(None)
        ).group_by(
            AuditLog.ip_address
        ).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()

        return {
            "period_days": days,
            "failed_logins": failed_logins,
            "successful_logins": successful_logins,
            "login_success_rate": round(successful_logins / (successful_logins + failed_logins) * 100, 2) if (successful_logins + failed_logins) > 0 else 100,
            "high_severity_events": high_severity,
            "password_changes": password_changes,
            "daily_failed_logins": [{"date": str(date), "count": count} for date, count in daily_failed],
            "suspicious_ips": [{"ip": ip, "fail_count": count} for ip, count in suspicious_ips if count >= 3],
        }

    except ImportError:
        return {
            "period_days": days,
            "error": "Audit module not available",
        }


def get_all_dashboard_metrics(days: int = 30) -> dict:
    """
    Get all metrics for admin dashboard.

    Args:
        days: Number of days for time-based metrics

    Returns:
        Complete dashboard data
    """
    return {
        "overview": get_overview_metrics(),
        "users": get_user_metrics(days),
        "activity": get_activity_metrics(days),
        "workspaces": get_workspace_metrics(),
        "generations": get_generation_metrics(days),
        "api_usage": get_api_usage_metrics(days),
        "security": get_security_metrics(days),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
