from datetime import datetime, timezone
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from firebase_admin import exceptions as firebase_exceptions
import requests
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User, UserAuthentication
from app.schemas.auth_schema import (
    FirebaseLoginRequest,
    FirebaseLoginResponse,
    LinkedInCallbackRequest,
    LinkedInCallbackResponse,
    UpdateEmailRequest,
    UpdateEmailResponse,
)
from app.services.firebase_service import verify_firebase_id_token


router = APIRouter(prefix="/api/v1", tags=["Authentication"])


def fetch_linkedin_profile(access_token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.get("https://api.linkedin.com/v2/me", headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch LinkedIn profile.",
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response received from LinkedIn profile API.",
        ) from exc


@router.post("/auth/firebase-login", response_model=FirebaseLoginResponse)
def firebase_login(payload: FirebaseLoginRequest, db: Session = Depends(get_db)):
    try:
        decoded_token = verify_firebase_id_token(payload.firebaseToken)
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

    mobile = decoded_token.get("phone_number")
    email = decoded_token.get("email")
    full_name = decoded_token.get("name")
    photo_url = decoded_token.get("picture")
    email_verified = bool(decoded_token.get("email_verified", False))
    sign_in_provider = decoded_token.get("firebase", {}).get("sign_in_provider", "firebase")

    now = datetime.now(timezone.utc)

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            mobile=mobile,
            email=email,
            full_name=full_name,
            photo_url=photo_url,
            email_verified=email_verified,
            is_active=True,
            last_login_at=now,
        )
        db.add(user)
        db.flush()
    else:
        user.email = email
        user.full_name = full_name
        user.photo_url = photo_url
        user.email_verified = email_verified
        user.last_login_at = now

    provider_uid = decoded_token.get("sub", firebase_uid)
    user_authentication = (
        db.query(UserAuthentication)
        .filter(
            UserAuthentication.provider == sign_in_provider,
            UserAuthentication.provider_uid == provider_uid,
        )
        .first()
    )

    if user_authentication is None:
        user_authentication = UserAuthentication(
            user_id=user.id,
            provider=sign_in_provider,
            provider_uid=provider_uid,
            last_sign_in_at=now,
        )
        db.add(user_authentication)
    else:
        user_authentication.user_id = user.id
        user_authentication.last_sign_in_at = now

    db.commit()
    db.refresh(user)

    return FirebaseLoginResponse(
        message="Firebase login successful.",
        user=user,
    )


@router.patch("/users/me/email", response_model=UpdateEmailResponse)
def update_my_email(
    payload: UpdateEmailRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    requested_email = payload.email.strip().lower()
    existing_user = db.query(User).filter(User.email == requested_email, User.id != user.id).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already in use.",
        )

    user.email = requested_email
    user.email_verified = False

    db.commit()
    db.refresh(user)

    return UpdateEmailResponse(
        message="Email updated successfully.",
        user=user,
    )


@router.post("/auth/linkedin", response_model=LinkedInCallbackResponse)
def linkedin_auth(payload: LinkedInCallbackRequest):
    linkedin_base_url = "https://www.linkedin.com/oauth/v2"
    csrf_token = secrets.token_urlsafe(32)

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": csrf_token,
        "scope": "openid profile email w_member_social",
    }

    try:
        response = requests.get(f"{linkedin_base_url}/authorization", params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate LinkedIn authorization URL.",
        ) from exc

    return LinkedInCallbackResponse(authorization_url=response.url)


@router.get("/linkedin-callback")
def linkedin_callback(code: str = Query(..., min_length=1)):
    linkedin_base_url = "https://www.linkedin.com/oauth/v2"

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/linkedin-callback")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LinkedIn credentials are not configured.",
        )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(f"{linkedin_base_url}/accessToken", data=data, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange LinkedIn authorization code.",
        ) from exc

    try:
        token_data = response.json()
    except ValueError:
        token_data = {"response": response.text}

    access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LinkedIn access token not found in response.",
        )

    profile_data = fetch_linkedin_profile(access_token)
    return {
        "token": token_data,
        "profile": profile_data,
    }
