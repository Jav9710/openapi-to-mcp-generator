"""
Sistema de webhooks para integracion CI/CD.

Permite registrar URLs de webhook que se disparan ante eventos
como upload de specs, generacion de servidores MCP, etc.
Incluye firma HMAC para verificacion y reintentos automaticos.
"""

import hashlib
import hmac
import json
import logging
import threading
from datetime import datetime, timezone

import requests

from .database import db, Webhook, WebhookEvent

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
TIMEOUT_SECONDS = 10


def dispatch_webhook_event(workspace_id: int, event: str, payload: dict):
    """
    Dispara todos los webhooks activos del workspace para un evento dado.

    Args:
        workspace_id: ID del workspace
        event: Nombre del evento (valor de WebhookEvent)
        payload: Datos del evento a enviar
    """
    webhooks = Webhook.query.filter_by(
        workspace_id=workspace_id,
        is_active=True,
    ).all()

    for webhook in webhooks:
        if event in (webhook.events or []):
            # Enviar en background para no bloquear el request
            thread = threading.Thread(
                target=_send_webhook,
                args=(webhook.id, webhook.url, webhook.secret, event, payload),
                daemon=True,
            )
            thread.start()


def _send_webhook(webhook_id: int, url: str, secret: str | None, event: str, payload: dict):
    """Envia un webhook con reintentos y firma HMAC."""
    from flask import current_app

    body = json.dumps({
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }, ensure_ascii=False)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event,
        "User-Agent": "OpenAPI-to-MCP-Webhook/1.0",
    }

    # Firmar con HMAC-SHA256 si hay secret
    if secret:
        signature = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                data=body,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
            )

            if response.status_code < 300:
                logger.info(f"Webhook {webhook_id} sent successfully: {event}")
                _update_webhook_status(webhook_id, success=True)
                return

            logger.warning(
                f"Webhook {webhook_id} returned {response.status_code} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Webhook {webhook_id} failed: {e} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

        if attempt < MAX_RETRIES:
            import time
            time.sleep(RETRY_DELAY_SECONDS * attempt)

    # Todos los reintentos fallaron
    logger.error(f"Webhook {webhook_id} failed after {MAX_RETRIES} attempts")
    _update_webhook_status(webhook_id, success=False)


def _update_webhook_status(webhook_id: int, success: bool):
    """Actualiza el estado del webhook tras un envio."""
    try:
        webhook = db.session.get(Webhook, webhook_id)
        if webhook:
            webhook.last_triggered = datetime.now(timezone.utc)
            if success:
                webhook.failure_count = 0
            else:
                webhook.failure_count = (webhook.failure_count or 0) + 1
                # Desactivar despues de 10 fallos consecutivos
                if webhook.failure_count >= 10:
                    webhook.is_active = False
                    logger.warning(f"Webhook {webhook_id} disabled after {webhook.failure_count} failures")
            db.session.commit()
    except Exception as e:
        logger.error(f"Error updating webhook status: {e}")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verifica la firma HMAC de un webhook entrante.

    Args:
        payload: Body del request en bytes
        signature: Valor del header X-Webhook-Signature
        secret: Secret compartido

    Returns:
        True si la firma es valida
    """
    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    received = signature[7:]  # Remover "sha256="
    return hmac.compare_digest(expected, received)
