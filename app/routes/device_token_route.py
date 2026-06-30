from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_device_token_model import UserDeviceToken
from app.models.user_model import User
from app.schemas.device_token_schema import (
    DeactivateDeviceTokenRequest,
    RegisterDeviceTokenRequest,
    RegisterDeviceTokenResponse,
)
from app.services.firebase_service import verify_firebase_id_token


router = APIRouter(prefix="/api/v1", tags=["Device Tokens"])

_VALID_PROVIDERS = {"fcm", "apns"}
_VALID_PLATFORMS = {"android", "ios", "web"}


def _get_authenticated_user(authorization: str, db: Session) -> User:
    token_prefix = "Bearer "
    if not authorization or not authorization.startswith(token_prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    firebase_token = authorization[len(token_prefix):].strip()
    if not firebase_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase token.",
        )

    try:
        decoded_token = verify_firebase_id_token(firebase_token)
    except (ValueError, firebase_exceptions.FirebaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token.",
        ) from exc

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain a valid uid.",
        )

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


@router.put("/users/me/device-tokens", response_model=RegisterDeviceTokenResponse)
def register_device_token(
    payload: RegisterDeviceTokenRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    if payload.provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join(sorted(_VALID_PROVIDERS))}.",
        )

    if payload.platform not in _VALID_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform. Must be one of: {', '.join(sorted(_VALID_PLATFORMS))}.",
        )

    now_utc = datetime.now(timezone.utc)

    existing = db.query(UserDeviceToken).filter(UserDeviceToken.token == payload.token).first()
    if existing is not None:
        existing.user_id = user.id
        existing.provider = payload.provider
        existing.platform = payload.platform
        existing.app_version = payload.app_version
        existing.device_id = payload.device_id
        existing.is_active = True
        existing.last_seen_at = now_utc
        existing.updated_at = now_utc
        db.commit()
        db.refresh(existing)
        return RegisterDeviceTokenResponse(token_id=existing.id, is_active=existing.is_active)

    if payload.device_id:
        (
            db.query(UserDeviceToken)
            .filter(
                UserDeviceToken.user_id == user.id,
                UserDeviceToken.device_id == payload.device_id,
                UserDeviceToken.is_active.is_(True),
            )
            .update({"is_active": False, "updated_at": now_utc}, synchronize_session=False)
        )

    row = UserDeviceToken(
        user_id=user.id,
        provider=payload.provider,
        token=payload.token,
        platform=payload.platform,
        app_version=payload.app_version,
        device_id=payload.device_id,
        is_active=True,
        last_seen_at=now_utc,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return RegisterDeviceTokenResponse(token_id=row.id, is_active=row.is_active)


@router.delete("/users/me/device-tokens", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_device_token(
    payload: DeactivateDeviceTokenRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    now_utc = datetime.now(timezone.utc)
    updated = (
        db.query(UserDeviceToken)
        .filter(
            UserDeviceToken.user_id == user.id,
            UserDeviceToken.token == payload.token,
        )
        .update({"is_active": False, "updated_at": now_utc}, synchronize_session=False)
    )
    db.commit()

    if updated == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")
