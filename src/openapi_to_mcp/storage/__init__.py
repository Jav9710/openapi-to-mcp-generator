"""
Módulo de almacenamiento de artefactos.

Proporciona una capa de abstracción sobre diferentes backends
de almacenamiento (local, MinIO/S3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapters.base import StorageAdapter

_storage: StorageAdapter | None = None


def get_storage() -> StorageAdapter:
    """Obtiene la instancia global del storage adapter."""
    global _storage
    if _storage is None:
        from ..config.settings import get_settings

        settings = get_settings()

        if settings.enable_storage:
            try:
                from .adapters.minio_adapter import MinIOStorageAdapter

                _storage = MinIOStorageAdapter(settings.minio)
            except ImportError:
                from .adapters.local_adapter import LocalStorageAdapter

                _storage = LocalStorageAdapter()
        else:
            from .adapters.local_adapter import LocalStorageAdapter

            _storage = LocalStorageAdapter()

    return _storage


def reset_storage() -> None:
    """Resetea el storage (útil para testing)."""
    global _storage
    _storage = None


__all__ = ["get_storage", "reset_storage"]
