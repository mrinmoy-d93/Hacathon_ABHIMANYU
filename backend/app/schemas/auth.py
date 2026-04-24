"""Auth request/response schemas (FRS §7.1, FR-1.1, FR-1.2)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    location: str = Field(min_length=2, max_length=255)
    role: str = Field(pattern=r"^(family|field_worker|admin)$")


class RegisterResponse(BaseModel):
    user_id: str


class SendOtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")


class SendOtpResponse(BaseModel):
    otp_sent: bool
    demo_mode: bool = False


class VerifyOtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    otp: str = Field(min_length=6, max_length=6)
    police_id: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    phone: str
    location: str | None
    role: str


class VerifyOtpResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
