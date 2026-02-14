"""
Sistema de gestión OAuth2 para MCP servers generados.

Maneja tokens OAuth2 con refresh automático, múltiples backends
de almacenamiento, y propagación de contexto de autenticación
a los servidores MCP generados.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class TokenStoreBackend(str, Enum):
    """Backends disponibles para almacenamiento de tokens."""

    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"


@dataclass
class OAuth2Token:
    """Representa un token OAuth2."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    @property
    def expires_at(self) -> float:
        return self.created_at + self.expires_in

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """True si el token expira dentro del buffer."""
        return time.time() >= (self.expires_at - buffer_seconds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "id_token": self.id_token,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OAuth2Token:
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            id_token=data.get("id_token"),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class OAuth2Provider:
    """Configuración de un proveedor OAuth2."""

    name: str
    issuer: str
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: Optional[str] = None
    scopes: list[str] = field(default_factory=lambda: ["openid", "profile"])
    redirect_uri: Optional[str] = None

    @classmethod
    def from_discovery(
        cls,
        name: str,
        issuer: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None = None,
    ) -> OAuth2Provider:
        """Crea proveedor desde OpenID Connect Discovery."""
        discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        try:
            resp = httpx.get(discovery_url, timeout=10)
            resp.raise_for_status()
            config = resp.json()
            return cls(
                name=name,
                issuer=issuer,
                client_id=client_id,
                client_secret=client_secret,
                authorization_url=config["authorization_endpoint"],
                token_url=config["token_endpoint"],
                userinfo_url=config.get("userinfo_endpoint"),
                scopes=config.get("scopes_supported", ["openid", "profile"]),
                redirect_uri=redirect_uri,
            )
        except Exception as e:
            logger.error("OIDC discovery failed for %s: %s", issuer, e)
            raise ValueError(
                f"Failed to discover OIDC config for {issuer}: {e}"
            ) from e


# ==================== Token Stores ====================


class TokenStore(ABC):
    """Interfaz base para almacenamiento de tokens."""

    @abstractmethod
    def store(self, key: str, token: OAuth2Token) -> None:
        ...

    @abstractmethod
    def get(self, key: str) -> Optional[OAuth2Token]:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def list_keys(self) -> list[str]:
        ...


class MemoryTokenStore(TokenStore):
    """Almacenamiento de tokens en memoria."""

    def __init__(self):
        self._tokens: dict[str, OAuth2Token] = {}

    def store(self, key: str, token: OAuth2Token) -> None:
        self._tokens[key] = token

    def get(self, key: str) -> Optional[OAuth2Token]:
        token = self._tokens.get(key)
        if token and token.is_expired and not token.refresh_token:
            self.delete(key)
            return None
        return token

    def delete(self, key: str) -> None:
        self._tokens.pop(key, None)

    def list_keys(self) -> list[str]:
        return list(self._tokens.keys())


class RedisTokenStore(TokenStore):
    """Almacenamiento de tokens en Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis

            self._redis = redis.from_url(redis_url)
            self._prefix = "oauth2:token:"
        except ImportError:
            raise ImportError("redis package required: pip install redis")

    def store(self, key: str, token: OAuth2Token) -> None:
        data = json.dumps(token.to_dict())
        ttl = max(int(token.expires_at - time.time()) + 86400, 3600)
        self._redis.setex(f"{self._prefix}{key}", ttl, data)

    def get(self, key: str) -> Optional[OAuth2Token]:
        data = self._redis.get(f"{self._prefix}{key}")
        if data is None:
            return None
        return OAuth2Token.from_dict(json.loads(data))

    def delete(self, key: str) -> None:
        self._redis.delete(f"{self._prefix}{key}")

    def list_keys(self) -> list[str]:
        keys = self._redis.keys(f"{self._prefix}*")
        prefix_len = len(self._prefix)
        return [k.decode()[prefix_len:] for k in keys]


# ==================== OAuth2 Manager ====================


class OAuth2Manager:
    """
    Gestor centralizado de tokens OAuth2.

    Maneja el ciclo completo: authorization, token exchange,
    refresh automático y propagación a MCP servers.
    """

    def __init__(
        self,
        token_store: TokenStore | None = None,
        refresh_buffer_seconds: int = 300,
    ):
        self._providers: dict[str, OAuth2Provider] = {}
        self._store = token_store or MemoryTokenStore()
        self._refresh_buffer = refresh_buffer_seconds
        self._http = httpx.Client(timeout=30)

    def register_provider(self, provider: OAuth2Provider) -> None:
        """Registra un proveedor OAuth2."""
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[OAuth2Provider]:
        """Obtiene un proveedor registrado."""
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """Lista nombres de proveedores registrados."""
        return list(self._providers.keys())

    def get_authorization_url(
        self,
        provider_name: str,
        state: str | None = None,
        scopes: list[str] | None = None,
    ) -> str:
        """Genera URL de autorización OAuth2."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        params = {
            "client_id": provider.client_id,
            "response_type": "code",
            "redirect_uri": provider.redirect_uri or "",
            "scope": " ".join(scopes or provider.scopes),
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{provider.authorization_url}?{query}"

    def exchange_code(
        self,
        provider_name: str,
        code: str,
        user_id: str,
    ) -> OAuth2Token:
        """
        Intercambia authorization code por tokens.

        Almacena el token en el store y lo retorna.
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        resp = self._http.post(
            provider.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
                "redirect_uri": provider.redirect_uri or "",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        token = OAuth2Token.from_dict(data)
        store_key = self._make_key(provider_name, user_id)
        self._store.store(store_key, token)

        logger.info(
            "Token obtained for user %s from %s", user_id, provider_name
        )
        return token

    def get_token(
        self,
        provider_name: str,
        user_id: str,
        auto_refresh: bool = True,
    ) -> Optional[OAuth2Token]:
        """
        Obtiene un token válido, refrescándolo si es necesario.

        Args:
            provider_name: Nombre del proveedor OAuth2.
            user_id: Identificador del usuario.
            auto_refresh: Si debe refrescar automáticamente.

        Returns:
            Token válido o None si no hay token almacenado.
        """
        store_key = self._make_key(provider_name, user_id)
        token = self._store.get(store_key)

        if token is None:
            return None

        if auto_refresh and token.needs_refresh(self._refresh_buffer):
            if token.refresh_token:
                try:
                    token = self._refresh_token(provider_name, token)
                    self._store.store(store_key, token)
                except Exception as e:
                    logger.warning(
                        "Token refresh failed for %s/%s: %s",
                        provider_name,
                        user_id,
                        e,
                    )
                    if token.is_expired:
                        self._store.delete(store_key)
                        return None

        return token

    def revoke_token(self, provider_name: str, user_id: str) -> None:
        """Revoca y elimina un token."""
        store_key = self._make_key(provider_name, user_id)
        self._store.delete(store_key)

    def get_auth_header(
        self,
        provider_name: str,
        user_id: str,
    ) -> dict[str, str]:
        """
        Obtiene header de autorización listo para usar.

        Returns:
            Dict con header Authorization o vacío si no hay token.
        """
        token = self.get_token(provider_name, user_id)
        if token and not token.is_expired:
            return {"Authorization": f"{token.token_type} {token.access_token}"}
        return {}

    def generate_mcp_auth_context(
        self,
        provider_name: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Genera contexto de autenticación para inyectar en MCP servers.

        Este contexto permite que los servidores MCP generados
        propaguen automáticamente los tokens OAuth2 del usuario
        en las llamadas a APIs externas.
        """
        token = self.get_token(provider_name, user_id)
        if not token:
            return {"authenticated": False, "provider": provider_name}

        provider = self._providers.get(provider_name)
        return {
            "authenticated": True,
            "provider": provider_name,
            "token_type": token.token_type,
            "access_token": token.access_token,
            "expires_at": datetime.fromtimestamp(
                token.expires_at, tz=timezone.utc
            ).isoformat(),
            "scopes": token.scope.split() if token.scope else [],
            "issuer": provider.issuer if provider else None,
        }

    def _refresh_token(
        self,
        provider_name: str,
        token: OAuth2Token,
    ) -> OAuth2Token:
        """Refresca un token expirado o próximo a expirar."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        if not token.refresh_token:
            raise ValueError("No refresh token available")

        resp = self._http.post(
            provider.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        new_token = OAuth2Token.from_dict(data)
        if not new_token.refresh_token:
            new_token.refresh_token = token.refresh_token

        logger.info("Token refreshed for provider %s", provider_name)
        return new_token

    def _make_key(self, provider_name: str, user_id: str) -> str:
        """Genera clave única para token store."""
        return f"{provider_name}:{user_id}"

    def close(self) -> None:
        """Cierra conexiones HTTP."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ==================== Factory ====================

_manager: OAuth2Manager | None = None


def get_oauth2_manager() -> OAuth2Manager:
    """Obtiene la instancia global del OAuth2 Manager."""
    global _manager
    if _manager is None:
        from ..config.settings import get_settings

        settings = get_settings()

        # Configurar token store según settings
        if settings.oauth2.token_store_backend == "redis":
            store: TokenStore = RedisTokenStore(settings.redis.url)
        else:
            store = MemoryTokenStore()

        _manager = OAuth2Manager(
            token_store=store,
            refresh_buffer_seconds=settings.oauth2.refresh_buffer_seconds,
        )

        # Registrar proveedor si está configurado
        if settings.oauth2.enabled:
            try:
                provider = OAuth2Provider.from_discovery(
                    name="default",
                    issuer=settings.oauth2.issuer,
                    client_id=settings.oauth2.client_id,
                    client_secret=settings.oauth2.client_secret,
                    redirect_uri=settings.oauth2.redirect_uri,
                )
                _manager.register_provider(provider)
            except Exception as e:
                logger.warning("Failed to configure default OAuth2 provider: %s", e)

    return _manager


def reset_oauth2_manager() -> None:
    """Resetea el manager OAuth2 (útil para testing)."""
    global _manager
    if _manager:
        _manager.close()
    _manager = None
