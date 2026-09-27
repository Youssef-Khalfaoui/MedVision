"""Auth router — register, login, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext

from app.dependencies import get_db, get_current_doctor
from app.models.doctor import Doctor
from app.schemas.auth import (
    DoctorRegister, DoctorLogin, TokenResponse, DoctorMe, DoctorUpdate
)
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _create_access_token(doctor_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(doctor_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/register", status_code=201)
async def register(body: DoctorRegister, db: AsyncSession = Depends(get_db)):
    """Register a new doctor."""
    result = await db.execute(select(Doctor).where(Doctor.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    doctor = Doctor(
        email=body.email,
        password_hash=pwd_context.hash(body.password),
        full_name=body.full_name,
        specialty=body.specialty,
    )
    db.add(doctor)
    await db.flush()

    token = _create_access_token(doctor.id)
    return TokenResponse(
        access_token=token,
        doctor_id=doctor.id,
        full_name=doctor.full_name,
    )


@router.post("/login")
async def login(body: DoctorLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and return JWT token."""
    result = await db.execute(select(Doctor).where(Doctor.email == body.email))
    doctor = result.scalar_one_or_none()
    if not doctor or not pwd_context.verify(body.password, doctor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = _create_access_token(doctor.id)
    return TokenResponse(
        access_token=token,
        doctor_id=doctor.id,
        full_name=doctor.full_name,
    )


@router.get("/me")
async def me(doctor: Doctor = Depends(get_current_doctor)):
    """Return the authenticated doctor's profile."""
    return DoctorMe.model_validate(doctor)


@router.put("/me")
async def update_me(
    body: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """Update the authenticated doctor's profile. All fields optional."""
    if body.full_name is not None:
        doctor.full_name = body.full_name
    if body.specialty is not None:
        doctor.specialty = body.specialty
    if body.date_of_birth is not None:
        doctor.date_of_birth = body.date_of_birth
    if body.phone is not None:
        doctor.phone = body.phone
    if body.address is not None:
        doctor.address = body.address
    if body.password:
        doctor.password_hash = pwd_context.hash(body.password)

    await db.flush()
    return DoctorMe.model_validate(doctor)
