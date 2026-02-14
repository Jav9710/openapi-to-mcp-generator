"""Adaptador de almacenamiento local (filesystem)."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base import StorageAdapter, StorageHealth, StorageObject


class LocalStorageAdapter(StorageAdapter):
    """Almacenamiento basado en filesystem local."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or os.path.join("output", "storage"))
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _bucket_path(self, bucket: str) -> Path:
        path = self.base_path / bucket
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _object_path(self, bucket: str, key: str) -> Path:
        path = self._bucket_path(bucket) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def health_check(self) -> StorageHealth:
        try:
            buckets = [
                d.name
                for d in self.base_path.iterdir()
                if d.is_dir()
            ]
            return StorageHealth(
                healthy=True,
                endpoint=str(self.base_path),
                buckets=buckets,
            )
        except Exception as e:
            return StorageHealth(
                healthy=False,
                endpoint=str(self.base_path),
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
        path = self._object_path(bucket, key)
        path.write_bytes(data)

        if metadata:
            import json

            meta_path = path.parent / f"{path.name}.meta.json"
            meta_path.write_text(
                json.dumps(
                    {"content_type": content_type, "metadata": metadata},
                    indent=2,
                ),
                encoding="utf-8",
            )

        return key

    def get_object(self, bucket: str, key: str) -> bytes:
        path = self._object_path(bucket, key)
        if not path.exists():
            raise FileNotFoundError(
                f"Object not found: {bucket}/{key}"
            )
        return path.read_bytes()

    def delete_object(self, bucket: str, key: str) -> None:
        path = self._object_path(bucket, key)
        if path.exists():
            path.unlink()
        meta_path = path.parent / f"{path.name}.meta.json"
        if meta_path.exists():
            meta_path.unlink()

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[StorageObject]:
        bucket_path = self._bucket_path(bucket)
        results: list[StorageObject] = []

        search_path = bucket_path / prefix if prefix else bucket_path

        if not search_path.exists():
            return results

        for path in search_path.rglob("*"):
            if path.is_file() and not path.name.endswith(".meta.json"):
                rel_key = str(path.relative_to(bucket_path)).replace(
                    "\\", "/"
                )
                stat = path.stat()
                results.append(
                    StorageObject(
                        bucket=bucket,
                        key=rel_key,
                        size=stat.st_size,
                        content_type="application/octet-stream",
                        last_modified=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ),
                    )
                )

        return results

    def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_hours: int = 24,
    ) -> str:
        return f"file://{self._object_path(bucket, key)}"

    def list_buckets(self) -> list[str]:
        return [
            d.name
            for d in self.base_path.iterdir()
            if d.is_dir()
        ]
