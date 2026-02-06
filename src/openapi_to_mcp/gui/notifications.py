"""
Sistema de notificaciones multi-canal.

Soporta envio de notificaciones a Slack, Discord y Email para
eventos importantes como generacion de servidores MCP, errores, etc.
"""

import json
import logging
import smtplib
import threading
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Clase base abstracta para canales de notificacion."""

    @abstractmethod
    def send(self, title: str, message: str, **kwargs) -> bool:
        """Envia una notificacion."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Prueba la conexion del canal."""
        pass


class SlackNotifier(NotificationChannel):
    """Notificador para Slack via webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str, **kwargs) -> bool:
        """Envia mensaje a Slack."""
        color = kwargs.get("color", "#3b82f6")  # Default azul
        if kwargs.get("is_error"):
            color = "#dc2626"  # Rojo para errores
        elif kwargs.get("is_success"):
            color = "#16a34a"  # Verde para exito

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "OpenAPI to MCP Generator",
                    "ts": int(__import__("time").time()),
                }
            ]
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Prueba el webhook de Slack."""
        return self.send("Test", "Conexion de prueba desde OpenAPI to MCP Generator")


class DiscordNotifier(NotificationChannel):
    """Notificador para Discord via webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str, **kwargs) -> bool:
        """Envia mensaje a Discord."""
        color = 0x3B82F6  # Default azul
        if kwargs.get("is_error"):
            color = 0xDC2626  # Rojo
        elif kwargs.get("is_success"):
            color = 0x16A34A  # Verde

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                    "footer": {"text": "OpenAPI to MCP Generator"},
                }
            ]
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Prueba el webhook de Discord."""
        return self.send("Test", "Conexion de prueba desde OpenAPI to MCP Generator")


class EmailNotifier(NotificationChannel):
    """Notificador via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_address: str,
        to_addresses: list[str],
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_address = from_address
        self.to_addresses = to_addresses
        self.use_tls = use_tls

    def send(self, title: str, message: str, **kwargs) -> bool:
        """Envia email."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[OpenAPI to MCP] {title}"
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)

            # Version texto plano
            text_part = MIMEText(message, "plain", "utf-8")
            msg.attach(text_part)

            # Version HTML
            html_content = f"""
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #1f2937;">{title}</h2>
                    <p style="color: #4b5563; white-space: pre-wrap;">{message}</p>
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                    <p style="color: #9ca3af; font-size: 12px;">
                        Enviado por OpenAPI to MCP Generator
                    </p>
                </div>
            </body>
            </html>
            """
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, self.to_addresses, msg.as_string())

            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Prueba la conexion SMTP."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            return True
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False


def create_notifier(channel_config: dict) -> NotificationChannel | None:
    """
    Factory para crear un notificador basado en configuracion.

    Args:
        channel_config: Dict con type y configuracion especifica del canal

    Returns:
        Instancia del notificador o None si el tipo es invalido
    """
    channel_type = channel_config.get("type", "").lower()

    if channel_type == "slack":
        return SlackNotifier(channel_config.get("webhook_url", ""))

    elif channel_type == "discord":
        return DiscordNotifier(channel_config.get("webhook_url", ""))

    elif channel_type == "email":
        return EmailNotifier(
            smtp_host=channel_config.get("smtp_host", ""),
            smtp_port=channel_config.get("smtp_port", 587),
            smtp_user=channel_config.get("smtp_user", ""),
            smtp_password=channel_config.get("smtp_password", ""),
            from_address=channel_config.get("from_address", ""),
            to_addresses=channel_config.get("to_addresses", []),
            use_tls=channel_config.get("use_tls", True),
        )

    return None


def send_notification_async(
    channel_config: dict,
    title: str,
    message: str,
    **kwargs
):
    """Envia notificacion en background."""
    def _send():
        notifier = create_notifier(channel_config)
        if notifier:
            notifier.send(title, message, **kwargs)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


def dispatch_to_all_channels(workspace_id: int, title: str, message: str, **kwargs):
    """
    Envia notificacion a todos los canales activos de un workspace.

    Args:
        workspace_id: ID del workspace
        title: Titulo de la notificacion
        message: Contenido del mensaje
        **kwargs: Argumentos adicionales (is_error, is_success, etc.)
    """
    from .database import NotificationChannel as NCModel

    channels = NCModel.query.filter_by(workspace_id=workspace_id, is_active=True).all()

    for channel in channels:
        config = {
            "type": channel.channel_type,
            **channel.config,
        }
        send_notification_async(config, title, message, **kwargs)
