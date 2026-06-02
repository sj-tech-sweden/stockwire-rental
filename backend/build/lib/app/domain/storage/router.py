from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_editor
from app.domain.auth.models import User
from app.domain.settings.models import AppSetting
from app.domain.storage.models import AssetFile
from app.domain.storage.schemas import AssetFileRead
from app.domain.storage.service import StorageService

router = APIRouter(prefix="/storage", tags=["storage"])

ALLOWED_ENTITY_TYPES = {"company", "job", "product", "device", "maintenance"}
COMPANY_PROFILE_KEY = "company.profile"
LOGO_VARIANT_TO_FIELD = {
    "default": "logo_file_id",
    "light-wide": "logo_light_wide_file_id",
    "light-small": "logo_light_small_file_id",
    "dark-wide": "logo_dark_wide_file_id",
    "dark-small": "logo_dark_small_file_id",
}


def _to_schema(file_row: AssetFile) -> AssetFileRead:
    return AssetFileRead(
        id=file_row.id,
        entity_type=file_row.entity_type,
        entity_id=file_row.entity_id,
        category=file_row.category,
        original_filename=file_row.original_filename,
        content_type=file_row.content_type,
        size_bytes=file_row.size_bytes,
        storage_backend=file_row.storage_backend,
        created_by_user_id=file_row.created_by_user_id,
        created_at=file_row.created_at,
        download_url=f"/api/v1/storage/files/{file_row.id}/download",
    )


def _validate_entity(entity_type: str | None, entity_id: int | None) -> tuple[str | None, int | None]:
    if entity_type is None:
        if entity_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="entity_id requires entity_type")
        return None, None

    normalized = entity_type.strip().lower()
    if normalized not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported entity_type")

    if normalized != "company" and entity_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="entity_id is required for this entity_type")

    return normalized, entity_id


def _read_company_profile_raw(db: Session) -> dict:
    setting = db.execute(select(AppSetting).where(AppSetting.key == COMPANY_PROFILE_KEY)).scalar_one_or_none()
    if not setting:
        return {}
    try:
        parsed = json.loads(setting.value_json or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _resolve_company_logo_file(db: Session) -> AssetFile | None:
    profile = _read_company_profile_raw(db)
    if not isinstance(profile, dict):
        return None

    for key in ("logo_light_wide_file_id", "logo_file_id"):
        logo_file_id = profile.get(key)
        if not isinstance(logo_file_id, int) or logo_file_id <= 0:
            continue
        row = db.get(AssetFile, logo_file_id)
        if not row or row.is_deleted:
            continue
        if row.entity_type and str(row.entity_type).strip().lower() != "company":
            continue
        return row
    return None


def _resolve_company_logo_file_for_variant(db: Session, variant: str) -> AssetFile | None:
    profile = _read_company_profile_raw(db)
    if not isinstance(profile, dict):
        return None

    field = LOGO_VARIANT_TO_FIELD.get(str(variant).strip().lower())
    if not field:
        return None

    logo_file_id = profile.get(field)
    if not isinstance(logo_file_id, int) or logo_file_id <= 0:
        return None

    row = db.get(AssetFile, logo_file_id)
    if not row or row.is_deleted:
        return None
    if row.entity_type and str(row.entity_type).strip().lower() != "company":
        return None
    return row


def _resolve_logo_download_url(db: Session, file_id: int | None) -> str | None:
    if not isinstance(file_id, int) or file_id <= 0:
        return None
    row = db.get(AssetFile, file_id)
    if not row or row.is_deleted:
        return None
    if row.entity_type and str(row.entity_type).strip().lower() != "company":
        return None
    return f"/api/v1/storage/files/{row.id}/download"


@router.get("/public/company-profile")
def get_public_company_profile(db: Session = Depends(get_db)):
    profile = _read_company_profile_raw(db)
    logo_file = _resolve_company_logo_file(db)

    def file_id(key: str) -> int | None:
        if not isinstance(profile, dict):
            return None
        value = profile.get(key)
        return value if isinstance(value, int) and value > 0 else None

    return {
        "company_name": profile.get("company_name") if isinstance(profile, dict) else None,
        "default_language": (profile.get("default_language") if isinstance(profile, dict) else None) or "en",
        "logo_url": "/api/v1/storage/public/company-logo" if logo_file else None,
        "logo_light_wide_url": "/api/v1/storage/public/company-logo/light-wide" if file_id("logo_light_wide_file_id") else None,
        "logo_light_small_url": "/api/v1/storage/public/company-logo/light-small" if file_id("logo_light_small_file_id") else None,
        "logo_dark_wide_url": "/api/v1/storage/public/company-logo/dark-wide" if file_id("logo_dark_wide_file_id") else None,
        "logo_dark_small_url": "/api/v1/storage/public/company-logo/dark-small" if file_id("logo_dark_small_file_id") else None,
    }


@router.get("/public/company-logo")
def download_public_company_logo(db: Session = Depends(get_db)):
    row = _resolve_company_logo_file(db)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found")

    storage = StorageService()
    return storage.build_download_response(
        storage_key=row.storage_key,
        content_type=row.content_type,
        download_filename=row.original_filename,
    )


@router.get("/public/company-logo/{variant}")
def download_public_company_logo_variant(variant: str, db: Session = Depends(get_db)):
    row = _resolve_company_logo_file_for_variant(db, variant)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found")

    storage = StorageService()
    return storage.build_download_response(
        storage_key=row.storage_key,
        content_type=row.content_type,
        download_filename=row.original_filename,
    )


@router.post("/files", response_model=AssetFileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    entity_type: str | None = Form(default=None),
    entity_id: int | None = Form(default=None),
    category: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_editor),
    current_user: User = Depends(get_current_user),
) -> AssetFileRead:
    entity_type, entity_id = _validate_entity(entity_type, entity_id)

    storage = StorageService()
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(payload) > storage.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {storage.max_upload_bytes // (1024 * 1024)}MB limit",
        )

    storage_key, stored_filename = storage.make_storage_key(
        entity_type=entity_type,
        category=category,
        original_filename=file.filename or "file",
    )
    storage.save_bytes(storage_key=storage_key, payload=payload, content_type=file.content_type)

    row = AssetFile(
        entity_type=entity_type,
        entity_id=entity_id,
        category=(category or "general").strip().lower() if category else None,
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        size_bytes=len(payload),
        storage_backend=storage.backend,
        storage_key=storage_key,
        created_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_schema(row)


@router.get("/files", response_model=list[AssetFileRead])
def list_files(
    entity_type: str | None = None,
    entity_id: int | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AssetFileRead]:
    stmt: Select[tuple[AssetFile]] = select(AssetFile).where(AssetFile.is_deleted.is_(False))
    if entity_type:
        normalized = entity_type.strip().lower()
        if normalized not in ALLOWED_ENTITY_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported entity_type")
        stmt = stmt.where(AssetFile.entity_type == normalized)
    if entity_id is not None:
        stmt = stmt.where(AssetFile.entity_id == entity_id)
    if category:
        stmt = stmt.where(AssetFile.category == category.strip().lower())

    rows = db.execute(stmt.order_by(AssetFile.created_at.desc())).scalars().all()
    return [_to_schema(r) for r in rows]


@router.get("/files/{file_id}", response_model=AssetFileRead)
def get_file_meta(file_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> AssetFileRead:
    row = db.get(AssetFile, file_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return _to_schema(row)


@router.get("/files/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.get(AssetFile, file_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = StorageService()
    return storage.build_download_response(
        storage_key=row.storage_key,
        content_type=row.content_type,
        download_filename=row.original_filename,
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: int, db: Session = Depends(get_db), _: User = Depends(require_editor)):
    row = db.get(AssetFile, file_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = StorageService()
    storage.delete(storage_key=row.storage_key)

    row.is_deleted = True
    db.add(row)
    db.commit()
    return None
