from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class FirebaseLoginRequest(BaseModel):
    phone_number: str = Field(min_length=10)
    firebaseToken: str = Field(min_length=10)


class FirebaseUserResponse(BaseModel):
    id: int
    firebase_uid: str
    mobile: str
    email: str | None = None
    full_name: str | None = None
    photo_url: str | None = None
    email_verified: bool = False
    is_active: bool = True
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class FirebaseLoginResponse(BaseModel):
    message: str
    user: FirebaseUserResponse


class UpdateEmailRequest(BaseModel):
    email: EmailStr


class UpdateEmailResponse(BaseModel):
    message: str
    user: FirebaseUserResponse


class LinkedInCallbackRequest(BaseModel):
    username: str = Field(min_length=1)


class LinkedInCallbackResponse(BaseModel):
    authorization_url: str
