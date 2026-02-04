"""
Gestion de API keys para acceso programatico.

Permite generar, listar y revocar API keys para autenticacion
sin sesion (uso en scripts, CI/CD, etc.).
"""

import secrets
import logging
from datetime import datetime, timezone

from flask_bcrypt import generate_password_hash

from .database import db, ApiKey

logger = logging.getLogger(__name__)

API_KEY_PREFIX_LENGTH = 12


def generate_api_key(user_id: int, name: str = "default") -> tuple[str, ApiKey]:
    """
    Genera una nueva API key para un usuario.

    Args:
        user_id: ID del usuario
        name: Nombre descriptivo de la key

    Returns:
        Tupla (raw_key, api_key_record). El raw_key solo se muestra una vez.
    """
    raw_key = f"omcp_{secrets.token_hex(32)}"
    prefix = raw_key[:API_KEY_PREFIX_LENGTH]
    key_hash = generate_password_hash(raw_key).decode("utf-8")

    api_key = ApiKey(
        user_id=user_id,
        name=name,
        prefix=prefix,
        key_hash=key_hash,
    )
    db.session.add(api_key)
    db.session.commit()

    logger.info(f"API key created for user {user_id}: {prefix}...")
    return raw_key, api_key


def revoke_api_key(key_id: int, user_id: int) -> bool:
    """
    Revoca una API key.

    Args:
        key_id: ID de la API key
        user_id: ID del usuario (para verificacion)

    Returns:
        True si se revoco correctamente
    """
    api_key = db.session.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user_id:
        return False

    api_key.is_active = False
    db.session.commit()
    logger.info(f"API key {key_id} revoked by user {user_id}")
    return True


def list_user_keys(user_id: int) -> list[dict]:
    """Lista las API keys de un usuario (sin el hash)."""
    keys = ApiKey.query.filter_by(user_id=user_id).all()
    return [k.to_dict() for k in keys]
