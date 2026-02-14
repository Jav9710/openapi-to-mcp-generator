"""Interfaz base para adaptadores de almacenamiento."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StorageObject:
    """Representa un objeto almacenado."""

    bucket: str
    key: str
    size: int
    content_type: str
    last_modified: datetime
    metadata: dict[str, str] = field(default_factory=dict)
    version_id: Optional[str] = None


@dataclass
class StorageHealth:
    """Estado de salud del storage."""

    healthy: bool
    endpoint: str
    buckets: list[str] = field(default_factory=list)
    error: Optional[str] = None


class StorageAdapter(ABC):
    """Interfaz abstracta para almacenamiento de artefactos."""

    @abstractmethod
    def health_check(self) -> StorageHealth:
        """Verifica conectividad con el storage."""
        ...

    @abstractmethod
    def store_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Almacena un objeto.

        Returns:
            Key del objeto almacenado.
        """
        ...

    @abstractmethod
    def get_object(self, bucket: str, key: str) -> bytes:
        """Obtiene contenido de un objeto."""
        ...

    @abstractmethod
    def delete_object(self, bucket: str, key: str) -> None:
        """Elimina un objeto."""
        ...

    @abstractmethod
    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[StorageObject]:
        """Lista objetos en un bucket con prefijo opcional."""
        ...

    @abstractmethod
    def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_hours: int = 24,
    ) -> str:
        """Genera URL pre-firmada para descarga."""
        ...

    @abstractmethod
    def list_buckets(self) -> list[str]:
        """Lista todos los buckets disponibles."""
        ...

    # Helpers de alto nivel

    def store_spec(
        self,
        workspace_id: int,
        spec_id: str,
        content: str,
        version: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Almacena una especificación OpenAPI."""
        key = f"{workspace_id}/{spec_id}/{version}.yaml"
        meta = metadata or {}
        meta["artifact_type"] = "spec"
        meta["version"] = version
        return self.store_object(
            "openapi-specs",
            key,
            content.encode("utf-8"),
            content_type="application/yaml",
            metadata=meta,
        )

    def store_mcp_artifact(
        self,
        workspace_id: int,
        generation_id: str,
        zip_data: bytes,
        manifest: dict | None = None,
    ) -> str:
        """Almacena un MCP generado como ZIP."""
        import json

        base_path = f"{workspace_id}/{generation_id}"
        self.store_object(
            "mcp-artifacts",
            f"{base_path}/mcp_server.zip",
            zip_data,
            content_type="application/zip",
            metadata={"artifact_type": "mcp"},
        )

        if manifest:
            self.store_object(
                "mcp-artifacts",
                f"{base_path}/manifest.json",
                json.dumps(manifest, indent=2).encode("utf-8"),
                content_type="application/json",
            )

        return base_path

    def store_report(
        self,
        workspace_id: int,
        report_id: str,
        content: str,
        format: str = "json",
    ) -> str:
        """Almacena un reporte generado."""
        content_types = {
            "json": "application/json",
            "csv": "text/csv",
            "html": "text/html",
        }
        key = f"{workspace_id}/{report_id}.{format}"
        return self.store_object(
            "reports",
            key,
            content.encode("utf-8"),
            content_type=content_types.get(format, "application/octet-stream"),
        )

    def get_mcp_download_url(
        self,
        workspace_id: int,
        generation_id: str,
        expires_hours: int = 24,
    ) -> str:
        """Genera URL pre-firmada para descargar un MCP."""
        return self.get_presigned_url(
            "mcp-artifacts",
            f"{workspace_id}/{generation_id}/mcp_server.zip",
            expires_hours=expires_hours,
        )
