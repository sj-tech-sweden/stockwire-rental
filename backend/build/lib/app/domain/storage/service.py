from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.config import settings


@dataclass
class StoredObject:
    storage_key: str
    stored_filename: str
    size_bytes: int


class StorageService:
    def __init__(self) -> None:
        self.backend = str(settings.storage_backend or "local").strip().lower()
        if self.backend not in {"local", "s3"}:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid storage backend")

    @property
    def max_upload_bytes(self) -> int:
        return max(1, int(settings.storage_max_upload_mb or 25)) * 1024 * 1024

    def make_storage_key(self, *, entity_type: str | None, category: str | None, original_filename: str) -> tuple[str, str]:
        ext = ""
        name = Path(original_filename or "file").name
        if "." in name:
            ext = "." + name.split(".")[-1].lower()
        stored_filename = f"{uuid4().hex}{ext}"

        safe_entity = (entity_type or "misc").strip().lower().replace(" ", "_")
        safe_category = (category or "general").strip().lower().replace(" ", "_")
        key = f"{safe_entity}/{safe_category}/{stored_filename}"
        return key, stored_filename

    def save_bytes(self, *, storage_key: str, payload: bytes, content_type: str | None = None) -> None:
        if self.backend == "local":
            self._save_local(storage_key=storage_key, payload=payload)
            return
        self._save_s3(storage_key=storage_key, payload=payload, content_type=content_type)

    def delete(self, *, storage_key: str) -> None:
        if self.backend == "local":
            self._delete_local(storage_key=storage_key)
            return
        self._delete_s3(storage_key=storage_key)

    def build_download_response(self, *, storage_key: str, content_type: str | None, download_filename: str) -> Response:
        if self.backend == "local":
            full_path = self._local_root() / storage_key
            if not full_path.exists() or not full_path.is_file():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
            return FileResponse(
                path=str(full_path),
                media_type=content_type or "application/octet-stream",
                filename=download_filename,
            )

        client, bucket, object_key = self._s3_client_and_key(storage_key)
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=max(60, int(settings.storage_s3_presign_expiry_seconds or 900)),
        )
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    def _local_root(self) -> Path:
        root = Path(settings.storage_local_path or "./data/uploads").expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _save_local(self, *, storage_key: str, payload: bytes) -> None:
        path = self._local_root() / storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def _delete_local(self, *, storage_key: str) -> None:
        path = self._local_root() / storage_key
        if path.exists():
            path.unlink(missing_ok=True)

    def _s3_client_and_key(self, storage_key: str):
        try:
            import boto3
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 backend requires boto3",
            ) from exc

        bucket = str(settings.storage_s3_bucket or "").strip()
        if not bucket:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 bucket is not configured")

        client = boto3.client(
            "s3",
            region_name=settings.storage_s3_region or None,
            endpoint_url=settings.storage_s3_endpoint_url or None,
            aws_access_key_id=settings.storage_s3_access_key_id or None,
            aws_secret_access_key=settings.storage_s3_secret_access_key or None,
        )
        prefix = str(settings.storage_s3_prefix or "").strip("/")
        object_key = f"{prefix}/{storage_key}" if prefix else storage_key
        return client, bucket, object_key

    def _save_s3(self, *, storage_key: str, payload: bytes, content_type: str | None = None) -> None:
        client, bucket, object_key = self._s3_client_and_key(storage_key)
        put_args = {
            "Bucket": bucket,
            "Key": object_key,
            "Body": payload,
        }
        if content_type:
            put_args["ContentType"] = content_type
        client.put_object(**put_args)

    def _delete_s3(self, *, storage_key: str) -> None:
        client, bucket, object_key = self._s3_client_and_key(storage_key)
        client.delete_object(Bucket=bucket, Key=object_key)
