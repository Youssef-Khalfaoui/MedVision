"""FastAPI dependencies — DB session + JWT auth."""

from fastapi import Depends, HTTPException, WebSocket, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.database import get_session
from app.models.doctor import Doctor
from app.config import get_settings

security = HTTPBearer()


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""
    async for session in get_session():
        yield session


async def get_current_doctor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Doctor:
    """Validate JWT and return the authenticated doctor."""
    token = credentials.credentials
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        doctor_id: int = int(payload.get("sub"))
        if doctor_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise credentials_exception
    return doctor


async def get_doctor_from_ws_token(
    websocket: WebSocket,
) -> int | None:
    """Extract and validate JWT from WebSocket query param ?token=... .

    Returns doctor_id or None (no exception — WS can close gracefully).
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        return None


async def get_doctor_from_query_or_header(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Doctor:
    """Authentifie un docteur via l'en-tete Authorization OU le query param ?token=.

    Necessaire pour les endpoints image/<img src> et PDF/download qui ne
    peuvent pas envoyer d'en-tete HTTP personnalise.
    """
    token = None
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:]
    else:
        token = request.query_params.get("token")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        doctor_id: int = int(payload.get("sub"))
        if doctor_id is None:
            raise credentials_exception
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise credentials_exception
    return doctor
