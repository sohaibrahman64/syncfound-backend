from pydantic import BaseModel, Field


class RegisterDeviceTokenRequest(BaseModel):
    token: str = Field(..., max_length=512)
    provider: str = Field(..., description="fcm | apns")
    platform: str = Field(..., description="android | ios | web")
    device_id: str | None = Field(default=None, max_length=128)
    app_version: str | None = Field(default=None, max_length=40)


class RegisterDeviceTokenResponse(BaseModel):
    token_id: int
    is_active: bool


class DeactivateDeviceTokenRequest(BaseModel):
    token: str = Field(..., max_length=512)
