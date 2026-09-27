"""Schemas pour Exam (minimal Round 2) et ExamClinicalContext."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime



class ExamCreate(BaseModel):
    patient_id: str
    exam_date: datetime


class ExamRead(BaseModel):
    id: int
    patient_id: str
    exam_date: datetime
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}



class ClinicalContextUpsert(BaseModel):
    fever: Optional[bool] = None
    cough: Optional[bool] = None
    chest_pain: Optional[bool] = None
    shortness_of_breath: Optional[bool] = None
    oxygen_saturation: Optional[float] = Field(None, ge=0, le=100)
    body_temperature: Optional[float] = Field(None, ge=30.0, le=45.0)
    recorded_at: Optional[datetime] = None


class ClinicalContextRead(BaseModel):
    exam_id: int
    fever: Optional[bool] = None
    cough: Optional[bool] = None
    chest_pain: Optional[bool] = None
    shortness_of_breath: Optional[bool] = None
    oxygen_saturation: Optional[float] = None
    body_temperature: Optional[float] = None
    recorded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
