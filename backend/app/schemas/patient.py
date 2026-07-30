"""Patient schemas — request/response."""

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class PatientCreate(BaseModel):
    id: str
    full_name: str
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None

class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None


class PatientResponse(BaseModel):
    id: str
    full_name: str
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    created_at: datetime
    created_by: int

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    id: str
    full_name: str
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
