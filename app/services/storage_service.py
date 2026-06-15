from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol
import os
from urllib.parse import urlparse


DEFAULT_LOCAL_UPLOAD_DIR = "uploads"


def _detect_storage_backend() -> str:
    backend = os.getenv("STORAGE_BACKEND", "auto").strip().lower()
    if backend in {"local", "gcs"}:
        return backend

    if os.getenv("K_SERVICE") or os.getenv("GCP_PROJECT"):
        return "gcs"

    return "local"


def is_local_storage_enabled() -> bool:
    return _detect_storage_backend() == "local"


def get_local_upload_dir() -> Path:
    return Path(os.getenv("LOCAL_UPLOAD_DIR", DEFAULT_LOCAL_UPLOAD_DIR))


@dataclass
class StoredObject:
    key: str
    url: str
    backend: str


class StorageService(Protocol):
    def upload(self, *, data: bytes, key: str, content_type: Optional[str] = None) -> StoredObject:
        ...

    def delete_by_url(self, *, url: str) -> bool:
        ...


class LocalDiskStorage:
    def __init__(self, *, base_dir: Path, public_base_url: str = "/uploads") -> None:
        self.base_dir = base_dir
        self.public_base_url = public_base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, *, data: bytes, key: str, content_type: Optional[str] = None) -> StoredObject:
        safe_key = key.replace("\\", "/").lstrip("/")
        destination = self.base_dir / safe_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

        return StoredObject(
            key=safe_key,
            url=f"{self.public_base_url}/{safe_key}",
            backend="local",
        )

    def delete_by_url(self, *, url: str) -> bool:
        normalized_url = (url or "").strip()
        if not normalized_url:
            raise ValueError("Image url is required.")

        parsed = urlparse(normalized_url)
        path = parsed.path if parsed.scheme else normalized_url
        expected_prefix = f"{self.public_base_url}/"
        if not path.startswith(expected_prefix):
            raise ValueError("Invalid local upload url. Expected path to start with /uploads/.")

        relative_key = path[len(expected_prefix):].lstrip("/")
        if not relative_key:
            raise ValueError("Invalid local upload url. Missing object key.")

        relative_path = Path(relative_key)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("Invalid local upload url. Path traversal is not allowed.")

        target = (self.base_dir / relative_path).resolve()
        base = self.base_dir.resolve()
        if base not in target.parents and target != base:
            raise ValueError("Invalid local upload url. Target path is outside uploads directory.")

        if not target.exists() or not target.is_file():
            return False

        target.unlink()
        return True


class GCSStorage:
    def __init__(self, *, bucket_name: str, prefix: str = "") -> None:
        try:
            from google.cloud import storage as gcs_storage
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-storage is not installed. Add it to requirements to use GCS uploads."
            ) from exc

        self.client = gcs_storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")

    def upload(self, *, data: bytes, key: str, content_type: Optional[str] = None) -> StoredObject:
        safe_key = key.replace("\\", "/").lstrip("/")
        full_key = f"{self.prefix}/{safe_key}" if self.prefix else safe_key

        blob = self.bucket.blob(full_key)
        blob.upload_from_string(data, content_type=content_type)

        return StoredObject(
            key=full_key,
            url=f"https://storage.googleapis.com/{self.bucket_name}/{full_key}",
            backend="gcs",
        )

    def delete_by_url(self, *, url: str) -> bool:
        normalized_url = (url or "").strip()
        if not normalized_url:
            raise ValueError("Image url is required.")

        parsed = urlparse(normalized_url)
        path = parsed.path if parsed.scheme else normalized_url

        object_key = ""
        expected_storage_prefix = f"/storage.googleapis.com/{self.bucket_name}/"
        if path.startswith(expected_storage_prefix):
            object_key = path[len(expected_storage_prefix):].lstrip("/")
        elif path.startswith(f"/{self.bucket_name}/"):
            object_key = path[len(f"/{self.bucket_name}/"):].lstrip("/")
        else:
            object_key = path.lstrip("/")

        if not object_key:
            raise ValueError("Invalid GCS url. Missing object key.")

        blob = self.bucket.blob(object_key)
        if not blob.exists():
            return False

        blob.delete()
        return True


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is not None:
        return _storage_service

    backend = _detect_storage_backend()
    if backend == "gcs":
        bucket_name = os.getenv("GCS_BUCKET_NAME", "").strip()
        if not bucket_name:
            raise RuntimeError("GCS_BUCKET_NAME is required when STORAGE_BACKEND is gcs or auto-detected as gcs.")

        prefix = os.getenv("GCS_OBJECT_PREFIX", "")
        _storage_service = GCSStorage(bucket_name=bucket_name, prefix=prefix)
        return _storage_service

    local_dir = get_local_upload_dir()
    _storage_service = LocalDiskStorage(base_dir=local_dir)
    return _storage_service


def initialize_storage() -> None:
    get_storage_service()
