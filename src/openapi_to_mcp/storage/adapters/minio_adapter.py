"""Adaptador de almacenamiento MinIO/S3."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import StorageAdapter, StorageHealth, StorageObject


class MinIOStorageAdapter(StorageAdapter):
    """Almacenamiento basado en MinIO (S3-compatible)."""

    def __init__(self, settings):
        from minio import Minio

        self.settings = settings
        self.client = Minio(
            endpoint=settings.endpoint,
            access_key=settings.access_key,
            secret_key=settings.secret_key,
            secure=settings.secure,
            region=settings.region,
        )

        # Buckets a inicializar
        self._required_buckets = [
            settings.bucket_specs,
            settings.bucket_artifacts,
            settings.bucket_reports,
            settings.bucket_backups,
        ]

    def _ensure_bucket(self, bucket: str) -> None:
        """Crea el bucket si no existe."""
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket, location=self.settings.region)

    def ensure_buckets(self) -> None:
        """Crea todos los buckets requeridos."""
        for bucket in self._required_buckets:
            self._ensure_bucket(bucket)

    def health_check(self) -> StorageHealth:
        try:
            buckets = [b.name for b in self.client.list_buckets()]
            return StorageHealth(
                healthy=True,
                endpoint=self.settings.endpoint,
                buckets=buckets,
            )
        except Exception as e:
            return StorageHealth(
                healthy=False,
                endpoint=self.settings.endpoint,
                error=str(e),
            )

    def store_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        self._ensure_bucket(bucket)

        stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=stream,
            length=len(data),
            content_type=content_type,
            metadata=metadata,
        )
        return key

    def get_object(self, bucket: str, key: str) -> bytes:
        response = None
        try:
            response = self.client.get_object(bucket, key)
            return response.read()
        finally:
            if response:
                response.close()
                response.release_conn()

    def delete_object(self, bucket: str, key: str) -> None:
        self.client.remove_object(bucket, key)

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[StorageObject]:
        results: list[StorageObject] = []

        if not self.client.bucket_exists(bucket):
            return results

        objects = self.client.list_objects(
            bucket, prefix=prefix, recursive=True
        )
        for obj in objects:
            results.append(
                StorageObject(
                    bucket=bucket,
                    key=obj.object_name,
                    size=obj.size or 0,
                    content_type=obj.content_type or "application/octet-stream",
                    last_modified=obj.last_modified or datetime.now(timezone.utc),
                    version_id=obj.version_id,
                )
            )

        return results

    def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_hours: int = 24,
    ) -> str:
        return self.client.presigned_get_object(
            bucket,
            key,
            expires=timedelta(hours=expires_hours),
        )

    def list_buckets(self) -> list[str]:
        return [b.name for b in self.client.list_buckets()]

    def get_bucket_stats(self, bucket: str) -> dict:
        """Obtiene estadísticas de un bucket."""
        objects = self.list_objects(bucket)
        total_size = sum(o.size for o in objects)
        return {
            "bucket": bucket,
            "total_objects": len(objects),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
