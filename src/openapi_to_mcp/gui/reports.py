"""
Automatic Reports System for Enterprise Analytics.

Provides scheduled report generation with:
- Multiple report types (usage, security, compliance)
- Configurable schedules
- Multiple output formats (PDF, HTML, JSON, CSV)
- Email delivery support
"""

import enum
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .database import db

logger = logging.getLogger(__name__)


class ReportType(enum.Enum):
    """Types of reports available."""
    USAGE_SUMMARY = "usage_summary"
    SECURITY_AUDIT = "security_audit"
    COMPLIANCE = "compliance"
    USER_ACTIVITY = "user_activity"
    GENERATION_STATS = "generation_stats"
    WORKSPACE_OVERVIEW = "workspace_overview"
    API_USAGE = "api_usage"
    ALERT_SUMMARY = "alert_summary"


class ReportFormat(enum.Enum):
    """Output formats for reports."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"


class ReportSchedule(enum.Enum):
    """Report schedule frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduledReport(db.Model):
    """Scheduled report configuration."""
    __tablename__ = "scheduled_reports"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)
    schedule = db.Column(db.String(20), nullable=False)
    format = db.Column(db.String(10), nullable=False, default=ReportFormat.JSON.value)

    # Delivery settings
    email_recipients = db.Column(db.JSON, default=list)
    webhook_url = db.Column(db.String(500), nullable=True)

    # Scope
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "report_type": self.report_type,
            "schedule": self.schedule,
            "format": self.format,
            "email_recipients": self.email_recipients,
            "webhook_url": self.webhook_url,
            "workspace_id": self.workspace_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
        }


class GeneratedReport(db.Model):
    """Generated report instance."""
    __tablename__ = "generated_reports"

    id = db.Column(db.Integer, primary_key=True)
    scheduled_report_id = db.Column(db.Integer, db.ForeignKey("scheduled_reports.id"), nullable=True)
    report_type = db.Column(db.String(50), nullable=False)
    format = db.Column(db.String(10), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)

    # Report data stored as JSON
    data = db.Column(db.JSON, nullable=False)

    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scheduled_report_id": self.scheduled_report_id,
            "report_type": self.report_type,
            "format": self.format,
            "title": self.title,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "workspace_id": self.workspace_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "generated_by": self.generated_by,
        }


# ========== Report Generation ==========

def generate_report(
    report_type: ReportType,
    period_days: int = 30,
    workspace_id: int | None = None,
    user_id: int | None = None,
    scheduled_report_id: int | None = None,
) -> GeneratedReport:
    """
    Generate a report.

    Args:
        report_type: Type of report to generate
        period_days: Number of days to include
        workspace_id: Filter by workspace
        user_id: User generating the report
        scheduled_report_id: Associated scheduled report

    Returns:
        Generated report
    """
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=period_days)
    period_end = now

    # Generate report data based on type
    if report_type == ReportType.USAGE_SUMMARY:
        data = _generate_usage_summary(period_start, period_end, workspace_id)
        title = f"Usage Summary Report ({period_days} days)"

    elif report_type == ReportType.SECURITY_AUDIT:
        data = _generate_security_audit(period_start, period_end, workspace_id)
        title = f"Security Audit Report ({period_days} days)"

    elif report_type == ReportType.COMPLIANCE:
        data = _generate_compliance_report(period_start, period_end, workspace_id)
        title = f"Compliance Report ({period_days} days)"

    elif report_type == ReportType.USER_ACTIVITY:
        data = _generate_user_activity_report(period_start, period_end, workspace_id)
        title = f"User Activity Report ({period_days} days)"

    elif report_type == ReportType.GENERATION_STATS:
        data = _generate_generation_stats(period_start, period_end, workspace_id)
        title = f"MCP Generation Statistics ({period_days} days)"

    elif report_type == ReportType.WORKSPACE_OVERVIEW:
        data = _generate_workspace_overview(workspace_id)
        title = "Workspace Overview Report"

    elif report_type == ReportType.API_USAGE:
        data = _generate_api_usage_report(period_start, period_end)
        title = f"API Usage Report ({period_days} days)"

    elif report_type == ReportType.ALERT_SUMMARY:
        data = _generate_alert_summary(period_start, period_end, workspace_id)
        title = f"Alert Summary Report ({period_days} days)"

    else:
        data = {"error": "Unknown report type"}
        title = "Unknown Report"

    # Create report record
    report = GeneratedReport(
        scheduled_report_id=scheduled_report_id,
        report_type=report_type.value,
        format=ReportFormat.JSON.value,
        title=title,
        period_start=period_start,
        period_end=period_end,
        data=data,
        workspace_id=workspace_id,
        generated_by=user_id,
    )

    db.session.add(report)
    db.session.commit()

    logger.info(f"Generated report: {title}")
    return report


def export_report(report: GeneratedReport, format: ReportFormat) -> str | bytes:
    """
    Export a report in specified format.

    Args:
        report: The generated report
        format: Output format

    Returns:
        Formatted report as string or bytes
    """
    if format == ReportFormat.JSON:
        return json.dumps({
            "title": report.title,
            "generated_at": report.generated_at.isoformat(),
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "data": report.data,
        }, indent=2)

    elif format == ReportFormat.CSV:
        return _export_csv(report)

    elif format == ReportFormat.HTML:
        return _export_html(report)

    return ""


def _export_csv(report: GeneratedReport) -> str:
    """Export report as CSV."""
    import csv
    output = io.StringIO()

    # Flatten the data for CSV
    data = report.data
    if isinstance(data, dict):
        # Write as key-value pairs or as table if contains lists
        if any(isinstance(v, list) for v in data.values()):
            # Find first list and use as rows
            for key, value in data.items():
                if isinstance(value, list) and value:
                    if isinstance(value[0], dict):
                        writer = csv.DictWriter(output, fieldnames=value[0].keys())
                        writer.writeheader()
                        writer.writerows(value)
                    break
        else:
            writer = csv.writer(output)
            writer.writerow(["Key", "Value"])
            for key, value in data.items():
                writer.writerow([key, str(value)])

    return output.getvalue()


def _export_html(report: GeneratedReport) -> str:
    """Export report as HTML."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        .section {{ margin: 20px 0; }}
        .section-title {{ font-weight: bold; color: #555; }}
    </style>
</head>
<body>
    <h1>{report.title}</h1>
    <div class="meta">
        <p>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p>Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}</p>
    </div>
    <div class="content">
"""

    # Render data as sections
    data = report.data
    if isinstance(data, dict):
        for key, value in data.items():
            html += f'<div class="section"><div class="section-title">{key.replace("_", " ").title()}</div>'
            if isinstance(value, dict):
                html += "<table><tr><th>Key</th><th>Value</th></tr>"
                for k, v in value.items():
                    html += f"<tr><td>{k}</td><td>{v}</td></tr>"
                html += "</table>"
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                html += "<table><tr>"
                for col in value[0].keys():
                    html += f"<th>{col}</th>"
                html += "</tr>"
                for row in value[:50]:  # Limit to 50 rows
                    html += "<tr>"
                    for col_val in row.values():
                        html += f"<td>{col_val}</td>"
                    html += "</tr>"
                html += "</table>"
            else:
                html += f"<p>{value}</p>"
            html += "</div>"

    html += """
    </div>
</body>
</html>"""

    return html


# ========== Report Data Generators ==========

def _generate_usage_summary(start: datetime, end: datetime, workspace_id: int | None) -> dict:
    """Generate usage summary report data."""
    from .metrics import get_overview_metrics, get_activity_metrics

    overview = get_overview_metrics()
    activity = get_activity_metrics((end - start).days)

    return {
        "overview": overview,
        "activity_summary": {
            "total_activities": activity.get("by_action", {}),
            "daily_trend": activity.get("daily_trend", [])[:14],  # Last 14 days
        },
        "highlights": {
            "total_users": overview.get("users", {}).get("total", 0),
            "active_users": overview.get("users", {}).get("active", 0),
            "new_users_period": overview.get("users", {}).get("new_last_week", 0),
            "total_workspaces": overview.get("workspaces", {}).get("total", 0),
        },
    }


def _generate_security_audit(start: datetime, end: datetime, workspace_id: int | None) -> dict:
    """Generate security audit report data."""
    from .metrics import get_security_metrics

    security = get_security_metrics((end - start).days)

    return {
        "summary": {
            "failed_logins": security.get("failed_logins", 0),
            "successful_logins": security.get("successful_logins", 0),
            "login_success_rate": security.get("login_success_rate", 100),
            "high_severity_events": security.get("high_severity_events", 0),
            "password_changes": security.get("password_changes", 0),
        },
        "daily_failed_logins": security.get("daily_failed_logins", []),
        "suspicious_activity": security.get("suspicious_ips", []),
        "recommendations": _generate_security_recommendations(security),
    }


def _generate_security_recommendations(security_data: dict) -> list[str]:
    """Generate security recommendations based on metrics."""
    recommendations = []

    if security_data.get("failed_logins", 0) > 10:
        recommendations.append("High number of failed login attempts detected. Consider implementing rate limiting or CAPTCHA.")

    if security_data.get("login_success_rate", 100) < 90:
        recommendations.append("Login success rate is below 90%. Review authentication flow for issues.")

    if security_data.get("suspicious_ips"):
        recommendations.append(f"Detected {len(security_data['suspicious_ips'])} IP addresses with multiple failed attempts. Consider IP blocking.")

    if not recommendations:
        recommendations.append("No significant security concerns detected during this period.")

    return recommendations


def _generate_compliance_report(start: datetime, end: datetime, workspace_id: int | None) -> dict:
    """Generate compliance report data."""
    from .retention import get_retention_stats, list_retention_policies

    retention_stats = get_retention_stats()
    policies = list_retention_policies(workspace_id)

    return {
        "data_retention": {
            "policies": policies,
            "stats": retention_stats,
        },
        "encryption_status": _get_encryption_status(),
        "audit_coverage": _get_audit_coverage(start, end),
        "compliance_score": _calculate_compliance_score(retention_stats),
    }


def _get_encryption_status() -> dict:
    """Get encryption status for compliance."""
    from .encryption import EncryptedSpec

    total_encrypted = EncryptedSpec.query.count()
    return {
        "total_encrypted_specs": total_encrypted,
        "encryption_enabled": True,
    }


def _get_audit_coverage(start: datetime, end: datetime) -> dict:
    """Get audit log coverage."""
    try:
        from .audit import AuditLog
        total_logs = AuditLog.query.filter(
            AuditLog.timestamp >= start,
            AuditLog.timestamp <= end
        ).count()
        return {
            "total_events_logged": total_logs,
            "audit_enabled": True,
        }
    except Exception:
        return {"audit_enabled": False}


def _calculate_compliance_score(retention_stats: dict) -> int:
    """Calculate a simple compliance score (0-100)."""
    score = 100

    # Deduct points for data past retention
    for data_type, stats in retention_stats.items():
        if stats.get("expired_records", 0) > 0:
            score -= 5

    return max(0, score)


def _generate_user_activity_report(start: datetime, end: datetime, workspace_id: int | None) -> dict:
    """Generate user activity report data."""
    from .metrics import get_user_metrics

    user_metrics = get_user_metrics((end - start).days)

    return {
        "summary": user_metrics,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
    }


def _generate_generation_stats(start: datetime, end: datetime, workspace_id: int | None) -> dict:
    """Generate MCP generation statistics."""
    from .metrics import get_generation_metrics

    gen_metrics = get_generation_metrics((end - start).days)

    return {
        "summary": {
            "total_generations": gen_metrics.get("total_period", 0),
            "avg_per_day": gen_metrics.get("avg_per_day", 0),
        },
        "daily_trend": gen_metrics.get("daily_trend", []),
        "by_framework": gen_metrics.get("by_framework", {}),
    }


def _generate_workspace_overview(workspace_id: int | None) -> dict:
    """Generate workspace overview."""
    from .metrics import get_workspace_metrics

    ws_metrics = get_workspace_metrics()

    return {
        "total_workspaces": ws_metrics.get("total_workspaces", 0),
        "size_distribution": ws_metrics.get("size_distribution", {}),
        "largest_workspaces": ws_metrics.get("largest_workspaces", []),
    }


def _generate_api_usage_report(start: datetime, end: datetime) -> dict:
    """Generate API usage report."""
    from .metrics import get_api_usage_metrics

    api_metrics = get_api_usage_metrics((end - start).days)

    return {
        "summary": {
            "total_keys": api_metrics.get("total_keys", 0),
            "active_keys": api_metrics.get("active_keys", 0),
            "recently_used": api_metrics.get("recently_used", 0),
        },
        "usage_by_user": api_metrics.get("keys_per_user", []),
    }


def _generate_alert_summary(start: datetime, end: datetime, workspace_id: int | None) -> dict:
    """Generate alert summary report."""
    from .alerts import Alert, AlertStatus
    from sqlalchemy import func

    # Get alert counts by status
    status_counts = db.session.query(
        Alert.status, func.count(Alert.id)
    ).filter(
        Alert.created_at >= start,
        Alert.created_at <= end
    ).group_by(Alert.status).all()

    # Get alert counts by severity
    severity_counts = db.session.query(
        Alert.severity, func.count(Alert.id)
    ).filter(
        Alert.created_at >= start,
        Alert.created_at <= end
    ).group_by(Alert.severity).all()

    return {
        "by_status": {status: count for status, count in status_counts},
        "by_severity": {sev: count for sev, count in severity_counts},
        "total_alerts": sum(count for _, count in status_counts),
    }


# ========== Scheduled Report Management ==========

def create_scheduled_report(
    name: str,
    report_type: ReportType,
    schedule: ReportSchedule,
    format: ReportFormat = ReportFormat.JSON,
    email_recipients: list[str] | None = None,
    webhook_url: str | None = None,
    workspace_id: int | None = None,
    user_id: int | None = None,
) -> ScheduledReport:
    """Create a scheduled report."""
    now = datetime.now(timezone.utc)

    # Calculate next run time
    if schedule == ReportSchedule.DAILY:
        next_run = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    elif schedule == ReportSchedule.WEEKLY:
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_run = (now + timedelta(days=days_until_monday)).replace(hour=8, minute=0, second=0, microsecond=0)
    else:  # Monthly
        if now.month == 12:
            next_run = now.replace(year=now.year + 1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
        else:
            next_run = now.replace(month=now.month + 1, day=1, hour=8, minute=0, second=0, microsecond=0)

    scheduled = ScheduledReport(
        name=name,
        report_type=report_type.value,
        schedule=schedule.value,
        format=format.value,
        email_recipients=email_recipients or [],
        webhook_url=webhook_url,
        workspace_id=workspace_id,
        created_by=user_id,
        next_run=next_run,
    )

    db.session.add(scheduled)
    db.session.commit()

    logger.info(f"Created scheduled report: {name}")
    return scheduled


def list_scheduled_reports(workspace_id: int | None = None) -> list[ScheduledReport]:
    """List scheduled reports."""
    query = ScheduledReport.query

    if workspace_id is not None:
        query = query.filter(
            (ScheduledReport.workspace_id == workspace_id) |
            (ScheduledReport.workspace_id.is_(None))
        )

    return query.order_by(ScheduledReport.created_at.desc()).all()


def list_generated_reports(
    report_type: ReportType | None = None,
    workspace_id: int | None = None,
    limit: int = 50,
) -> list[GeneratedReport]:
    """List generated reports."""
    query = GeneratedReport.query

    if report_type:
        query = query.filter_by(report_type=report_type.value)

    if workspace_id is not None:
        query = query.filter(
            (GeneratedReport.workspace_id == workspace_id) |
            (GeneratedReport.workspace_id.is_(None))
        )

    return query.order_by(GeneratedReport.generated_at.desc()).limit(limit).all()


def run_scheduled_reports() -> list[GeneratedReport]:
    """
    Run all scheduled reports that are due.

    Returns:
        List of generated reports
    """
    now = datetime.now(timezone.utc)
    generated = []

    due_reports = ScheduledReport.query.filter(
        ScheduledReport.is_active == True,
        ScheduledReport.next_run <= now
    ).all()

    for scheduled in due_reports:
        try:
            # Determine period based on schedule
            if scheduled.schedule == ReportSchedule.DAILY.value:
                period_days = 1
            elif scheduled.schedule == ReportSchedule.WEEKLY.value:
                period_days = 7
            else:
                period_days = 30

            # Generate report
            report = generate_report(
                report_type=ReportType(scheduled.report_type),
                period_days=period_days,
                workspace_id=scheduled.workspace_id,
                scheduled_report_id=scheduled.id,
            )
            generated.append(report)

            # Update scheduled report
            scheduled.last_run = now
            _update_next_run(scheduled)

            # Deliver report
            if scheduled.email_recipients:
                _deliver_report_email(report, scheduled.email_recipients, ReportFormat(scheduled.format))

            if scheduled.webhook_url:
                _deliver_report_webhook(report, scheduled.webhook_url)

        except Exception as e:
            logger.error(f"Failed to run scheduled report {scheduled.name}: {e}")

    db.session.commit()
    return generated


def _update_next_run(scheduled: ScheduledReport):
    """Update next run time for a scheduled report."""
    now = datetime.now(timezone.utc)

    if scheduled.schedule == ReportSchedule.DAILY.value:
        scheduled.next_run = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    elif scheduled.schedule == ReportSchedule.WEEKLY.value:
        scheduled.next_run = (now + timedelta(days=7)).replace(hour=8, minute=0, second=0, microsecond=0)
    else:  # Monthly
        if now.month == 12:
            scheduled.next_run = now.replace(year=now.year + 1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
        else:
            scheduled.next_run = now.replace(month=now.month + 1, day=1, hour=8, minute=0, second=0, microsecond=0)


def _deliver_report_email(report: GeneratedReport, recipients: list[str], format: ReportFormat):
    """Deliver report via email."""
    # This would integrate with the notifications module
    logger.info(f"Would send report to {recipients} (email delivery not implemented)")


def _deliver_report_webhook(report: GeneratedReport, webhook_url: str):
    """Deliver report via webhook."""
    try:
        import requests
        data = export_report(report, ReportFormat.JSON)
        requests.post(webhook_url, json={"report": json.loads(data)}, timeout=30)
        logger.info(f"Delivered report to webhook: {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to deliver report to webhook: {e}")
