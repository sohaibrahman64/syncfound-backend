from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4
import os

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.services.storage_service import get_storage_service


router = APIRouter(prefix="/api/v1", tags=["Image Upload"])


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}


def _build_storage_key(original_filename: str) -> str:
    extension = Path(original_filename or "").suffix.lower()
    if not extension:
        extension = ".bin"

    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    return f"images/{date_path}/{uuid4().hex}{extension}"


@router.post("/images/upload")
async def upload_image(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, WEBP, and GIF images are supported.",
        )

    max_image_size_mb = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
    max_image_size_bytes = max_image_size_mb * 1024 * 1024

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > max_image_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds the {max_image_size_mb} MB size limit.",
        )

    storage_key = _build_storage_key(file.filename)

    try:
        storage_service = get_storage_service()
        stored = storage_service.upload(
            data=content,
            key=storage_key,
            content_type=content_type,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload image: {exc}",
        ) from exc

    return {
        "message": "Image uploaded successfully.",
        "storage_backend": stored.backend,
        "key": stored.key,
        "url": stored.url,
        "content_type": content_type,
        "size_bytes": len(content),
    }


@router.delete("/images/remove")
def remove_image(url: str = Query(..., min_length=1, description="Stored image url/path")) -> dict:
    try:
        storage_service = get_storage_service()
        deleted = storage_service.delete_by_url(url=url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete image: {exc}",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )

    return {
        "message": "Image deleted successfully.",
        "url": url,
    }
