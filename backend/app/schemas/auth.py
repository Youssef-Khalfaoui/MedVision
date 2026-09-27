"""Auth schemas — request/response for doctor authentication."""

from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional


class DoctorRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    specialty: Optional[str] = None


class DoctorLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: int
    full_name: str


class DoctorMe(BaseModel):
    id: int
    email: str
    full_name: str
    specialty: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None
